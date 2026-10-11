"""Focused typed recorded codec and assembly; full C §8.5 fixture codec is incomplete."""

from datetime import datetime
from typing import Protocol

from pydantic import model_validator

from ..core import models as m
from ..core.certificates import case_contract_hash, economic_fingerprint
from ..core.errors import ContractViolation
from ..core.ports import ContextBuilder
from ..core.serialization import semantic_hash


class CostProjection(Protocol):
    def cost_input(self, context: m.EvidenceContext, canonical_id: str) -> m.ResolvedCostInput: ...


class EstimateBuilder(Protocol):
    def construct(
        self,
        cost: m.ResolvedCostInput,
        *,
        supplier_id: str,
        standard: m.ResolvedStandards,
        assumptions: m.EvidenceRecord,
        as_of: datetime,
    ) -> m.SupplierEstimate: ...


class RecordedCostAssumption(m.FrozenModel):
    supplier_id: str
    canonical_id: str
    assumption: m.EvidenceRecord


class OfflineRecordedInputs(m.FrozenModel):
    """Input-only boundary: contains no assessments/actions/labels/desired winners."""

    prepared: m.PreparedEvidence
    case: m.CaseContract
    server: m.ServerState
    documents: tuple[m.DocumentRecord, ...]
    as_of: datetime
    state: m.NegotiationState
    budget: m.DecisionBudget
    target_supplier_id: str
    previous_assessment: m.SupplierAssessment | None = None
    cost_policy: m.CostPolicy
    estimate_mode: str
    cost_assumptions: tuple[RecordedCostAssumption, ...]
    packages: tuple[m.Package, ...]
    expected_context_version: str | None = None

    @model_validator(mode="after")
    def recorded_shape(self):
        if self.as_of.utcoffset() is None or self.as_of.utcoffset().total_seconds() != 0:
            raise ValueError("recorded as_of must be UTC")
        if self.estimate_mode not in ("disabled_explicit", "nominal_explicit"):
            raise ValueError("offline input supports disabled or one explicit nominal scenario")
        if self.estimate_mode == "disabled_explicit" and self.cost_assumptions:
            raise ValueError("disabled inputs must not carry estimate assumptions")
        if len(self.packages) > 20 or len({p.fingerprint for p in self.packages}) != len(self.packages):
            raise ValueError("recorded packages must be a bounded distinct tuple")
        if (
            self.state.case != self.case
            or self.state.server != self.server
            or self.target_supplier_id not in self.case.supplier_ids
        ):
            raise ValueError("recorded case/server/state/target do not agree")
        if self.server.status != "open" or self.server.case_id != self.case.case_id:
            raise ValueError("recorded commercial decision needs declared open session")
        if len({a.supplier_id for a in self.cost_assumptions}) != len(self.cost_assumptions):
            raise ValueError("one explicit estimate per supplier in the bounded slice")
        return self


def load_recorded_json(raw: str | bytes) -> OfflineRecordedInputs:
    """Strict input decoding only; no inference, source selection or answer computation."""
    return OfflineRecordedInputs.model_validate_json(raw)


def _current(record, as_of):
    t = record.temporal
    return (
        t.status == "current"
        and all(x is None or x <= as_of for x in (t.observed_at, t.published_at))
        and all(x is None or x <= as_of.date() for x in (t.data_as_of, t.valid_from))
        and (t.valid_to is None or t.valid_to >= as_of.date())
    )


class OfflineContextAssembler:
    def __init__(
        self, *, context_builder: ContextBuilder, projections: CostProjection, estimate_builder: EstimateBuilder
    ):
        self.context_builder = context_builder
        self.projections = projections
        self.estimate_builder = estimate_builder

    def assemble(self, inputs: OfflineRecordedInputs) -> m.DecisionSnapshot:
        inputs = load_recorded_json(inputs.model_dump_json())
        if case_contract_hash(inputs.case) != inputs.case.contract_hash:
            raise ContractViolation("invalid_schema: recorded case hash does not match its inputs")
        evidence = self.context_builder.build_context(
            inputs.prepared, inputs.case, inputs.server, inputs.documents, inputs.as_of
        )
        if any(c.blocking for c in evidence.conflicts) or any(i.severity == "error" for i in evidence.gaps):
            raise ContractViolation("source_conflict: evidence resolution blocks context assembly")
        if inputs.expected_context_version is not None and evidence.context_version != inputs.expected_context_version:
            raise ContractViolation("stale_state: recorded context revision does not match assembled evidence")
        admitted = {r.record_id: r for r in evidence.records}
        standards = []
        for thread in inputs.server.threads:
            standard = thread.standards
            projection = standard.model_dump(mode="json", exclude={"version_hash"})
            for key in ("bindings", "field_origins"):
                projection[key] = sorted(projection[key], key=lambda x: x["field"])
            if semantic_hash(projection) != standard.version_hash:
                raise ContractViolation("invalid_schema: recorded standards version mismatch")
            for origin in standard.field_origins:
                term = next(t for t in standard.bindings if t.field == origin.field)
                for ref in origin.source_refs:
                    record = admitted.get(ref.record_id)
                    if record is None or (ref.canonical_id is not None and ref.canonical_id != record.canonical_id):
                        raise ContractViolation("missing_source: standards citation is not an admitted original source")
                    if not _current(record, inputs.as_of):
                        raise ContractViolation("stale_source: standard quote is not declared current")
                    payload = record.payload
                    if (
                        origin.source_kind != "quote"
                        or record.kind != "canonical"
                        or not isinstance(payload, m.QuoteFact)
                        or payload.supplier != thread.supplier_id
                        or term not in payload.observed_terms
                        or set(payload.part_ids) != {p.part_id for p in inputs.case.parts}
                    ):
                        raise ContractViolation(
                            "scope_mismatch: recorded standard lacks matching declared canonical quote terms"
                        )
                    if payload.validity is not None:
                        quote = record.model_copy(update={"temporal": payload.validity})
                        if not _current(quote, inputs.as_of):
                            raise ContractViolation("stale_source: quote-specific validity blocks standards")
            standards.append(m.SupplierStandards(supplier_id=thread.supplier_id, standards=standard))
        estimates = []
        for request in inputs.cost_assumptions:
            assumption = request.assumption
            for ref in assumption.payload.assumptions if isinstance(assumption.payload, m.EstimateRecord) else ():
                record = admitted.get(ref.record_id)
                if record is None or (ref.canonical_id is not None and record.canonical_id != ref.canonical_id):
                    raise ContractViolation("missing_source: assumption references missing or shadowed source")
            standard = next((s.standards for s in standards if s.supplier_id == request.supplier_id), None)
            if standard is None:
                raise ContractViolation("missing_source: estimate supplier has no applicable standards")
            estimates.append(
                self.estimate_builder.construct(
                    self.projections.cost_input(evidence, request.canonical_id),
                    supplier_id=request.supplier_id,
                    standard=standard,
                    assumptions=assumption,
                    as_of=inputs.as_of,
                )
            )
        enabled = inputs.estimate_mode == "nominal_explicit"
        if enabled and not estimates:
            raise ContractViolation("missing_source: explicit estimate mode requires declared assumptions")
        policy = m.ScenarioPolicy(
            mode=inputs.estimate_mode,
            required_supplier_ids=tuple(e.supplier_id for e in estimates),
            scenarios=(
                m.EstimateScenario(scenario_id="offline:nominal", estimate_ids=tuple(e.estimate_id for e in estimates)),
            )
            if enabled
            else (),
        )
        economic = m.EconomicContext(
            case=inputs.case,
            standards_by_supplier=tuple(standards),
            estimates=tuple(estimates),
            scenario_policy=policy,
            cost_policy=inputs.cost_policy,
            fingerprint="0" * 64,
            issues=(),
        )
        economic = economic.model_copy(update={"fingerprint": economic_fingerprint(economic)})
        ref = m.SnapshotRef(
            run_id=inputs.state.run_id,
            session_id=inputs.server.session_id,
            state_version=inputs.state.version,
            context_version=evidence.context_version,
            config_hash=inputs.state.config_hash,
            case_contract_hash=inputs.case.contract_hash,
        )
        context = m.NegotiationContext(
            snapshot=ref,
            case=inputs.case,
            evidence=evidence,
            economic=economic,
            capabilities=("used-action-v1", "offline-declared-inputs-v1"),
            as_of=inputs.as_of,
        )
        thread = next((t for t in inputs.server.threads if t.supplier_id == inputs.target_supplier_id), None)
        if thread is None:
            raise ContractViolation("scope_mismatch: target has no identified conversation")
        return m.DecisionSnapshot(
            context=context,
            state=inputs.state,
            target_supplier_id=inputs.target_supplier_id,
            conversation=thread.conversation,
            budget=inputs.budget,
        )
