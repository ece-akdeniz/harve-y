"""Explicit source-cost assumptions projected into attributed supplier estimates."""

from datetime import datetime

from ..core.errors import ContractViolation
from ..core.models import (
    EstimateRecord,
    EvidenceRecord,
    ResolvedCostInput,
    ResolvedStandards,
    SourceRef,
    SupplierEstimate,
)
from ..core.serialization import semantic_hash


def _basis_key(basis):
    return basis.currency, basis.price_unit, basis.part_ids, basis.quantity_basis


def _current(temporal, as_of):
    return temporal.status == "current" and all(
        value is None or value <= as_of for value in (temporal.observed_at, temporal.published_at)
    ) and all(value is None or value <= as_of.date() for value in (
        temporal.data_as_of, temporal.valid_from,
    )) and (temporal.valid_to is None or temporal.valid_to >= as_of.date())


class SourceCostEstimateBuilder:
    def construct(
        self, cost: ResolvedCostInput, *, supplier_id: str, standard: ResolvedStandards,
        assumptions: EvidenceRecord, as_of: datetime,
    ) -> SupplierEstimate:
        """Admit a declared full-cost mapping, never infer it from a supplier assertion.

        The caller supplies the resolver-backed cost projection and an explicit internal
        assumption revision. This service verifies their joins, not source authenticity.
        No rates, ppm, extra costs, bounds or probabilities are inferred.
        """
        if not isinstance(cost, ResolvedCostInput) or not isinstance(standard, ResolvedStandards):
            raise TypeError("estimate requires validated cost input and standards")
        if not isinstance(assumptions, EvidenceRecord):
            raise TypeError("estimate assumptions require a validated evidence record")
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ContractViolation("invalid_schema: estimate as_of requires an aware clock")
        if not supplier_id or supplier_id != supplier_id.strip():
            raise ContractViolation("invalid_schema: supplier identity is required")
        if not cost.source_refs or any(i.severity == "error" for i in cost.issues):
            raise ContractViolation("missing_source: cost projection is unavailable")
        if not _current(cost.temporal, as_of) or not _current(assumptions.temporal, as_of):
            raise ContractViolation("stale_source: cost and assumptions must be explicitly current")
        if assumptions.kind not in {"estimate", "hypothesis"} or not isinstance(assumptions.payload, EstimateRecord):
            raise ContractViolation("unsupported_claim: explicit internal estimate assumptions are required")
        payload = assumptions.payload
        if payload.method_id != "source-cost-v1":
            raise ContractViolation("unsupported_capability: source-cost-v1 mapping required")
        basis = cost.unit_cost.basis
        if len(basis.part_ids) != 1:
            raise ContractViolation("unknown_basis: source-cost estimate supports one part")
        if assumptions.scope.supplier_ids != (supplier_id,) or assumptions.scope.part_ids != basis.part_ids:
            raise ContractViolation("scope_mismatch: assumptions require explicit single supplier and part targets")
        for scope in (cost.scope, assumptions.scope):
            if scope.supplier_ids and supplier_id not in scope.supplier_ids:
                raise ContractViolation("scope_mismatch: supplier outside cost/assumption scope")
            if scope.part_ids and set(scope.part_ids) != set(basis.part_ids):
                raise ContractViolation("scope_mismatch: cost and assumptions must refer to the same part")
            if scope.level == "basket":
                raise ContractViolation("unknown_basis: basket estimate mapping is unsupported")
        if assumptions.scope.case_id != cost.scope.case_id:
            raise ContractViolation("scope_mismatch: cost and assumptions require the same declared case scope")
        if not all(ref in payload.assumptions for ref in cost.source_refs):
            raise ContractViolation("missing_source: assumptions must cite the exact cost-source revision")
        named = {value.name: value for value in payload.values}
        required = {"full_cost", "interest_rate", "usual_rate", "ppm", "extra_per_unit"}
        if set(named) != required:
            raise ContractViolation("missing_source: all five supplier quantities require explicit assumptions")
        full = named["full_cost"]
        extra = named["extra_per_unit"]
        if _basis_key(full.basis) != _basis_key(basis) or _basis_key(extra.basis) != _basis_key(basis):
            raise ContractViolation("unknown_basis: assumed costs must use the observed price basis")
        if full.value != cost.unit_cost.amount:
            raise ContractViolation("source_conflict: declared full-cost mapping disagrees with observed unit cost")
        if full.range_low is None or full.range_high is None:
            raise ContractViolation("missing_source: full-cost bounds must be explicitly declared")
        if named["ppm"].value != named["ppm"].value.to_integral_value():
            raise ContractViolation("invalid_schema: ppm assumption must be integral")
        for name in ("interest_rate", "usual_rate", "ppm", "extra_per_unit"):
            value = named[name]
            if value.range_low is not None and (value.range_low != value.value or value.range_high != value.value):
                raise ContractViolation("unsupported_capability: non-cost ranges require explicit scenarios")
        if not {"payment_days", "incoterm"}.issubset(t.field for t in standard.bindings):
            raise ContractViolation("missing_source: cash-value reference standards require payment and incoterm")
        projection = standard.model_dump(mode="json", exclude={"version_hash"})
        for key in ("bindings", "field_origins"):
            projection[key] = sorted(projection[key], key=lambda x: x["field"])
        if semantic_hash(projection) != standard.version_hash:
            raise ContractViolation("invalid_schema: reference standards hash mismatch")
        refs = tuple(dict.fromkeys((*cost.source_refs, *payload.assumptions,
                                  SourceRef(record_id=assumptions.record_id, canonical_id=assumptions.canonical_id))))
        estimate = SupplierEstimate(
            estimate_id="pending", supplier_id=supplier_id, basis=basis, full_cost=cost.unit_cost,
            full_cost_low=type(cost.unit_cost)(amount=full.range_low, basis=basis),
            full_cost_high=type(cost.unit_cost)(amount=full.range_high, basis=basis),
            interest_rate=named["interest_rate"].value, usual_rate=named["usual_rate"].value,
            ppm=int(named["ppm"].value), extra_per_unit=extra.value, standard=standard,
            assumption_refs=refs, method_id="source-cost-v1",
            uncertainty_kind="unknown" if full.range_low == full.range_high else "scenario_range",
        )
        identity = semantic_hash({"schema_version": estimate.schema_version,
                                  "estimate": estimate.model_dump(mode="json", exclude={"estimate_id"}),
                                  "cost_input": cost, "assumption_record": assumptions})
        # Only the derived identity is replaced; all commercial fields were validated above.
        return estimate.model_copy(update={"estimate_id": f"sha256:{identity}"})
