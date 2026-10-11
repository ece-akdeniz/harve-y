"""Internal evidence projections. They neither calculate official costs nor verify outward claims."""

from ..core.errors import ContractViolation
from ..core.models import CostFact, EvidenceContext, ResolvedCostInput, SourceRef
from .resolver import LayeredEvidenceResolver


class EvidenceProjections:
    def cost_input(self, context: EvidenceContext, canonical_id: str) -> ResolvedCostInput:
        """Project one admissible canonical cost revision, preserving its declared price basis.

        Resolver issues are retained as context gaps; this initial consumer fails closed
        on error gaps because their affected identity cannot always be recovered from
        the selected records alone. No fallback to shadowed records or supplier reports.
        """
        if not isinstance(context, EvidenceContext):
            raise TypeError("cost projection requires a validated EvidenceContext")
        if not isinstance(canonical_id, str) or not canonical_id.strip() or canonical_id != canonical_id.strip():
            raise ContractViolation("invalid_schema: canonical cost identifier must be nonempty and unpadded")
        if any(issue.severity == "error" for issue in context.gaps):
            raise ContractViolation("inadmissible_evidence: context has blocking resolution gaps")
        matches = tuple(record for record in context.records if record.canonical_id == canonical_id)
        if len(matches) != 1:
            raise ContractViolation("missing_source: exactly one resolved cost revision is required")
        record = matches[0]
        for conflict in context.conflicts:
            if conflict.canonical_id == canonical_id and (
                conflict.blocking or conflict.winning_record_id != record.record_id
            ):
                raise ContractViolation("source_conflict: selected cost disagrees with source resolution")
        selected, _, issues = LayeredEvidenceResolver().resolve(
            (record,), case_id=context.case_id, supplier_ids=context.supplier_ids, part_ids=context.part_ids,
        )
        if issues or selected != (record,):
            raise ContractViolation("scope_mismatch: cost source is outside the admitted scope or layers")
        if record.kind != "canonical" or not isinstance(record.payload, CostFact):
            raise ContractViolation("unsupported_claim: cost must be a canonical CostFact, not a supplier assertion")
        temporal = record.temporal
        if temporal.status != "current":
            raise ContractViolation("inadmissible_evidence: cost freshness must be explicitly current")
        as_of = context.as_of
        if any(value is not None and value > as_of for value in (temporal.observed_at, temporal.published_at)):
            raise ContractViolation("future_source: source observation or publication is in the future")
        if temporal.data_as_of is not None and temporal.data_as_of > as_of.date():
            raise ContractViolation("future_source: source data date is in the future")
        if temporal.valid_from is not None and temporal.valid_from > as_of.date():
            raise ContractViolation("future_source: cost source is not yet valid")
        if temporal.valid_to is not None and temporal.valid_to < as_of.date():
            raise ContractViolation("stale_source: cost source validity has expired")
        price = record.payload.unit_cost
        if price.basis.part_ids != (record.payload.part,) or record.scope.level == "basket":
            raise ContractViolation("unknown_basis: part-specific cost requires an unambiguous single-part basis")
        return ResolvedCostInput(
            unit_cost=price, source_refs=(SourceRef(record_id=record.record_id, canonical_id=canonical_id),),
            scope=record.scope, temporal=temporal,
            issues=tuple(issue for issue in context.gaps if issue.severity == "warning"),
        )
