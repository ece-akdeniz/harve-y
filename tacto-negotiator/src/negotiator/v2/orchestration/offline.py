"""One injected offline decision, with reproducible diagnostics and exact message bytes."""

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Literal, TypeVar

from pydantic import TypeAdapter, ValidationError, model_serializer

from ..core import models as m
from ..core.certificates import candidate_id, case_contract_hash, economic_fingerprint, verify_batch
from ..core.errors import ContractViolation
from ..core.ports import (
    ActionRenderer,
    ActionSelectionPolicy,
    ActionValidator,
    CandidateGenerator,
    CandidateResearch,
    Clock,
    EconomicEvaluator,
    StrategyProposalPolicy,
    SupplierInterpreter,
)
from ..core.serialization import canonical_json, semantic_hash
from .budgets import DecisionModelLedger, ModelCallTrace

T = TypeVar("T")


class OfflineStage(m.FrozenModel):
    name: Literal[
        "snapshot", "interpretation", "proposal", "generation", "evaluation", "selection", "rendering", "validation"
    ]
    status: Literal["completed", "failed"]
    issues: tuple[m.Issue, ...]
    elapsed_s: Decimal | None = None

    @model_serializer(mode="wrap")
    def preserve_historic_projection(self, handler):
        result = handler(self)
        if "elapsed_s" not in self.model_fields_set:
            result.pop("elapsed_s", None)
        return result


class OfflineDecisionTrace(m.FrozenModel):
    """Local diagnostic artifact, never a durable DecisionRecord or execution permit."""

    snapshot: m.SnapshotRef
    snapshot_bytes: bytes
    recorded_input_bytes: bytes
    input_hash: str
    components: tuple[str, ...]
    stages: tuple[OfflineStage, ...]
    assessment: m.SupplierAssessment | None = None
    intents: m.IntentBatch | None = None
    generations: tuple[m.GenerationResult, ...]
    evaluations: m.EvaluationBatch | None = None
    decision: m.NegotiationDecision | None = None
    rendered: m.RenderedAction | None = None
    validation: m.ValidationResult | None = None
    validated_message_bytes: bytes | None = None
    issues: tuple[m.Issue, ...]
    outcome: m.DecisionOutcome
    trace_hash: str
    model_calls: tuple[ModelCallTrace, ...] = ()
    model_token_limit: int | None = None

    def verify(self):
        if semantic_hash(self.model_dump(mode="json", exclude={"trace_hash"})) != self.trace_hash:
            raise ContractViolation("invalid_schema: offline trace digest mismatch")
        if hashlib.sha256(self.recorded_input_bytes or self.snapshot_bytes).hexdigest() != self.input_hash:
            raise ContractViolation("invalid_schema: offline input bytes mismatch")
        if self.validated_message_bytes is not None:
            if (
                self.validation is None
                or self.validation.kind != "valid"
                or hashlib.sha256(
                    self.validated_message_bytes,
                ).hexdigest()
                != self.validation.action.payload_hash
            ):
                raise ContractViolation("invalid_schema: trace bytes do not match validation certificate")


def _issue(error, component):
    code = str(error).split(":", 1)[0]
    if isinstance(error, TimeoutError):
        code = "deadline_exhausted"
    if code not in m.IssueCode.__args__:
        code = "invalid_schema"
    return m.Issue(
        code=code, severity="error", component=component, refs=(), detail="boundary failure; exception content withheld"
    )


def _citation(citation, snapshot):
    if isinstance(citation, m.SourceRef):
        record = next((r for r in snapshot.context.evidence.records if r.record_id == citation.record_id), None)
        if record is None or (citation.canonical_id is not None and citation.canonical_id != record.canonical_id):
            raise ContractViolation("missing_source: cited source revision is not in resolved context")
        return
    message = next((msg for msg in snapshot.conversation.messages if msg.message_id == citation.message_id), None)
    if (
        message is None
        or citation.session_id != message.session_id
        or citation.thread_id != message.thread_id
        or message.body[citation.start : citation.end] != citation.quote
        or citation.end > len(message.body)
    ):
        raise ContractViolation("ungrounded_output: citation is not an exact scoped message span")


def _assessment(assessment, snapshot):
    if assessment.snapshot != snapshot.context.snapshot or assessment.supplier_id != snapshot.target_supplier_id:
        raise ContractViolation("stale_state: interpretation returned another snapshot/recipient")
    observations = {o.observation_id for o in assessment.observations}
    for item in (
        *assessment.observations,
        *assessment.reported_constraints,
        *assessment.uncertainties,
        *assessment.questions,
    ):
        for citation in item.citations:
            _citation(citation, snapshot)
    for constraint in assessment.reported_constraints:
        if not set(constraint.condition_observation_refs) <= observations:
            raise ContractViolation("ungrounded_output: constraint condition refers to absent observation")
    for uncertainty in assessment.uncertainties:
        if not set(uncertainty.related_observation_refs) <= observations:
            raise ContractViolation("ungrounded_output: uncertainty refers to absent observation")
    for hypothesis in assessment.hypotheses:
        for citation in (
            *hypothesis.supporting_refs,
            *hypothesis.contradicting_refs,
            *(hypothesis.numeric_effect.citations if hypothesis.numeric_effect else ()),
        ):
            _citation(citation, snapshot)


class NoAdditionalResearch:
    """Explicit unavailable lookahead seam; no hidden simulation or new batches."""

    async def evaluate_intents(self, intents: m.IntentBatch, budget: m.DecisionBudget) -> m.EvaluationBatch:
        raise ContractViolation("unsupported_capability: additional candidate research disabled in offline slice")


class OfflineDecisionCoordinator:
    def __init__(
        self,
        *,
        interpreter: SupplierInterpreter,
        proposal: StrategyProposalPolicy,
        generator: CandidateGenerator,
        evaluator: EconomicEvaluator,
        selector: ActionSelectionPolicy,
        renderer_factory: Callable[[m.EvaluationBatch], ActionRenderer],
        validator: ActionValidator,
        payload_encoder: Callable[[m.MessagePayload], bytes],
        clock: Clock,
        research: CandidateResearch | None = None,
        model_token_limit: int | None = None,
    ):
        self.interpreter = interpreter
        self.proposal = proposal
        self.generator = generator
        self.evaluator = evaluator
        self.selector = selector
        self.renderer_factory = renderer_factory
        self.validator = validator
        self.payload_encoder = payload_encoder
        self.clock = clock
        self.model_token_limit = model_token_limit
        if research is not None:
            raise ContractViolation("unsupported_capability: registering research batches remains incomplete")
        self.research = NoAdditionalResearch()

    async def decide(self, snapshot: m.DecisionSnapshot) -> m.DecisionOutcome:
        return (await self.run_once(snapshot)).outcome

    async def run_once(
        self,
        snapshot: m.DecisionSnapshot,
        *,
        previous_assessment: m.SupplierAssessment | None = None,
        recorded_input_bytes: bytes = b"",
    ) -> OfflineDecisionTrace:
        consumer = next((c for c in (self.interpreter, self.proposal, self.selector)
                         if hasattr(c, "decision_scope")), None)
        if consumer is None:
            return await self._run_once(snapshot, previous_assessment=previous_assessment,
                                        recorded_input_bytes=recorded_input_bytes)
        if self.model_token_limit is None:
            raise ContractViolation("unsupported_capability: explicit total model token budget required")
        ledger = DecisionModelLedger(budget=snapshot.budget, clock=self.clock, token_limit=self.model_token_limit)
        with consumer.decision_scope(ledger):
            trace = await self._run_once(snapshot, previous_assessment=previous_assessment,
                                         recorded_input_bytes=recorded_input_bytes)
        trace = trace.model_copy(update={"model_calls": tuple(ledger.traces),
                                        "model_token_limit": ledger.token_limit})
        trace = trace.model_copy(update={"trace_hash": semantic_hash(
            trace.model_dump(mode="json", exclude={"trace_hash"}),
        )})
        trace.verify()
        return trace

    async def _run_once(
        self,
        snapshot: m.DecisionSnapshot,
        *,
        previous_assessment: m.SupplierAssessment | None = None,
        recorded_input_bytes: bytes = b"",
    ) -> OfflineDecisionTrace:
        raw_snapshot = canonical_json(snapshot)
        ref = snapshot.context.snapshot
        stages = []
        issues = []
        generations = []
        assessment = intents = batch = decision = rendered = validation = payload = None
        phase = "snapshot"
        started = self.clock.monotonic()
        phase_started = started

        def remaining():
            utc = (snapshot.budget.deadline_at - self.clock.utcnow()).total_seconds()
            compute = float(snapshot.budget.compute_limit_s) - (self.clock.monotonic() - started)
            return min(utc, compute)

        def available():
            if remaining() <= 0:
                raise ContractViolation("deadline_exhausted: offline decision budget exhausted")

        async def bounded(call: Callable[[], Awaitable[T]]) -> T:
            available()
            return await asyncio.wait_for(call(), timeout=remaining())

        def completed():
            nonlocal phase_started
            stage_issues = ()
            if phase == "interpretation" and assessment is not None and assessment.status == "fallback":
                codes = [code for code in assessment.unknowns if code in m.IssueCode.__args__]
                stage_issues = tuple(m.Issue(code=code, severity="warning", component="interpretation",
                                            refs=(), detail="consumer rejected interpretation; fallback used")
                                     for code in codes)
                issues.extend(stage_issues)
            stages.append(OfflineStage(name=phase, status="completed", issues=stage_issues,
                                       elapsed_s=Decimal(str(max(0, self.clock.monotonic() - phase_started)))))
            phase_started = self.clock.monotonic()

        def begin(name):
            nonlocal phase, phase_started
            phase = name
            phase_started = self.clock.monotonic()

        try:
            snapshot = m.DecisionSnapshot.model_validate_json(raw_snapshot)
            if snapshot.state.version != ref.state_version:
                raise ContractViolation("stale_state: decision state version differs from snapshot")
            context = snapshot.context
            if (
                case_contract_hash(context.case) != ref.case_contract_hash
                or context.evidence.as_of != context.as_of
                or context.as_of > self.clock.utcnow()
                or "sha256:" + semantic_hash(context.evidence.model_dump(mode="json", exclude={"context_version"}))
                != ref.context_version
                or economic_fingerprint(context.economic) != context.economic.fingerprint
            ):
                raise ContractViolation("stale_state: stale or edited context projection")
            if any(i.severity == "error" for i in (*context.evidence.gaps, *context.economic.issues)) or any(
                c.blocking for c in context.evidence.conflicts
            ):
                raise ContractViolation("source_conflict: snapshot has unresolved evidence/economic errors")
            if snapshot.state.runtime_status not in ("ready", "deciding") or any(
                o.status in ("prepared", "submitted", "uncertain") for o in snapshot.state.operations
            ):
                raise ContractViolation("operation_pending: decision has unresolved ownership")
            if previous_assessment is not None and (
                previous_assessment.supplier_id != snapshot.target_supplier_id
                or previous_assessment.snapshot.run_id != ref.run_id
                or previous_assessment.snapshot.session_id != ref.session_id
                or previous_assessment.snapshot.state_version > ref.state_version
            ):
                raise ContractViolation("stale_state: previous assessment belongs to another/future state")
            available()
            completed()
            begin("interpretation")
            assessment = await bounded(
                lambda: self.interpreter.interpret(
                    context,
                    snapshot.conversation,
                    previous_assessment,
                    snapshot.budget,
                )
            )
            assessment = m.SupplierAssessment.model_validate_json(assessment.model_dump_json())
            _assessment(assessment, snapshot)
            completed()
            begin("proposal")
            intents = await bounded(
                lambda: self.proposal.propose_strategies(
                    context,
                    assessment,
                    snapshot.state,
                    snapshot.budget,
                    self.research,
                )
            )
            intents = m.IntentBatch.model_validate_json(intents.model_dump_json())
            issues.extend(intents.issues)
            if intents.snapshot != ref or not intents.intents or len(intents.intents) > snapshot.budget.candidate_limit:
                raise ContractViolation("invalid_schema: proposal returned empty/oversized/stale intent batch")
            for intent in intents.intents:
                if intent.supplier_id != snapshot.target_supplier_id:
                    raise ContractViolation("scope_mismatch: proposed intent targets another supplier")
                if not set(intent.observation_refs) <= {o.observation_id for o in assessment.observations}:
                    raise ContractViolation("ungrounded_output: intent references unknown observation")
                for citation in (*intent.evidence_refs, *intent.proposal_citations):
                    _citation(citation, snapshot)
            if any(i.severity == "error" for i in intents.issues):
                raise ContractViolation("infeasible: proposal contains unresolved errors")
            completed()
            begin("generation")
            for intent in intents.intents:
                available()
                generated = self.generator.generate_candidates(intent, context, snapshot.state, snapshot.budget)
                generated = m.GenerationResult.model_validate_json(generated.model_dump_json())
                generations.append(generated)
                issues.extend(generated.rejections)
                if generated.intent_id != intent.intent_id or any(
                    c.intent_id != intent.intent_id
                    or c.supplier_id != snapshot.target_supplier_id
                    or c.snapshot != ref
                    or c.candidate_id != candidate_id(c)
                    for c in generated.candidates
                ):
                    raise ContractViolation("invalid_schema: generator returned forged candidate/snapshot")
            candidates = tuple(c for g in generations for c in g.candidates)
            if not candidates or len(candidates) > min(20, snapshot.budget.candidate_limit):
                raise ContractViolation("infeasible: no candidates or global candidate budget exceeded")
            completed()
            begin("evaluation")
            available()
            batch = self.evaluator.evaluate_candidates(candidates, context)
            batch = m.EvaluationBatch.model_validate_json(batch.model_dump_json())
            verify_batch(batch)
            if batch.snapshot != ref or {i.candidate.candidate_id: i.candidate for i in batch.items} != {
                c.candidate_id: c for c in candidates
            }:
                raise ContractViolation("invalid_schema: evaluator changed registered candidate membership")
            issues.extend(i for item in batch.items for i in item.issues)
            completed()
            begin("selection")
            decision = await bounded(
                lambda: self.selector.select_action(
                    batch,
                    assessment,
                    snapshot.state,
                    snapshot.budget,
                    self.research,
                )
            )
            decision = m.NegotiationDecision.model_validate_json(decision.model_dump_json())
            selected = next((i for i in batch.items if i.candidate.candidate_id == decision.candidate_id), None)
            if (
                selected is None
                or selected.disposition != "approved"
                or decision.snapshot != ref
                or decision.approved_batch_hash != batch.batch_hash
                or decision.evaluation_id != selected.evaluation_id
            ):
                raise ContractViolation("invalid_schema: selection is not an approved registered batch member")
            for citation in decision.citations:
                _citation(citation, snapshot)
            completed()
            begin("rendering")
            available()
            rendered = self.renderer_factory(batch).render(decision, selected, (), context)
            rendered = m.RenderedAction.model_validate_json(rendered.model_dump_json())
            contents = selected.candidate.contents
            expected_packages = contents.packages if isinstance(contents, m.OfferAction) else ()
            if (
                rendered.snapshot != ref
                or rendered.supplier_id != snapshot.target_supplier_id
                or rendered.decision_ref != "sha256:" + semantic_hash(decision)
                or rendered.kind != contents.kind
                or rendered.payload.packages != expected_packages
            ):
                raise ContractViolation("invalid_schema: renderer edited the selected action")
            completed()
            begin("validation")
            available()
            validation = self.validator.validate_action(rendered, context, snapshot.state, snapshot.budget)
            validation = TypeAdapter(m.ValidationResult).validate_json(validation.model_dump_json())
            if validation.kind == "invalid":
                issues.extend(validation.report.issues)
                raise ContractViolation("infeasible: independent used-action validation rejected selection")
            certificate = validation.action
            if (
                certificate.rendered != rendered
                or certificate.report.snapshot != ref
                or certificate.economic_fingerprint != context.economic.fingerprint
                or certificate.expires_at <= self.clock.utcnow()
                or certificate.expires_at > snapshot.budget.deadline_at
            ):
                raise ContractViolation("stale_state: validation certificate is expired or inconsistent")
            wire = self.payload_encoder(rendered.payload)
            if hashlib.sha256(wire).hexdigest() != certificate.payload_hash:
                raise ContractViolation("invalid_schema: exact bytes differ from validated message")
            available()
            payload = wire
            completed()
            outcome = m.SelectedOutcome(kind="selected", decision=decision)
        except (ContractViolation, ValidationError, TimeoutError) as error:
            failure = _issue(error, "orchestration.offline:" + phase)
            issues.append(failure)
            stages.append(OfflineStage(name=phase, status="failed", issues=(failure,),
                                       elapsed_s=Decimal(str(max(0, self.clock.monotonic() - phase_started)))))
            outcome = m.CannotDecideOutcome(kind="cannot_decide", snapshot=ref, issues=tuple(issues))
        trace = OfflineDecisionTrace(
            snapshot=ref,
            snapshot_bytes=raw_snapshot,
            recorded_input_bytes=recorded_input_bytes,
            input_hash=hashlib.sha256(recorded_input_bytes or raw_snapshot).hexdigest(),
            components=tuple(
                type(component).__module__ + "." + type(component).__qualname__
                for component in (
                    self.interpreter,
                    self.proposal,
                    self.generator,
                    self.evaluator,
                    self.selector,
                    self.validator,
                )
            ),
            stages=tuple(stages),
            assessment=assessment,
            intents=intents,
            generations=tuple(generations),
            evaluations=batch,
            decision=decision,
            rendered=rendered,
            validation=validation,
            validated_message_bytes=payload,
            issues=tuple(issues),
            outcome=outcome,
            trace_hash="0" * 64,
        )
        trace = trace.model_copy(
            update={"trace_hash": semantic_hash(trace.model_dump(mode="json", exclude={"trace_hash"}))}
        )
        trace.verify()
        return trace
