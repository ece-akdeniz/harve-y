"""Typed declared inputs -> layered evidence -> replaceable ports -> exact validated bytes."""

import hashlib
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from negotiator.v2.adapters.official import OfficialArithmetic
from negotiator.v2.adapters.offline import (
    OfflineContextAssembler,
    OfflineRecordedInputs,
    RecordedCostAssumption,
    load_recorded_json,
)
from negotiator.v2.core import models as m
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.core.serialization import canonical_json, semantic_hash
from negotiator.v2.economics.estimates import SourceCostEstimateBuilder
from negotiator.v2.economics.finite import SuppliedCandidateGenerator
from negotiator.v2.economics.official import OfficialEconomicEvaluator
from negotiator.v2.evidence.claims import EvidenceProjections
from negotiator.v2.evidence.context import LayeredContextBuilder, prepared_hash
from negotiator.v2.execution.render import TemplateActionRenderer, render_hash
from negotiator.v2.execution.validation import FinalActionValidator, payload_bytes
from negotiator.v2.factory import run_recorded_decision
from negotiator.v2.intelligence.testing import InputEchoTestInterpreter
from negotiator.v2.orchestration.offline import OfflineDecisionCoordinator, OfflineDecisionTrace
from negotiator.v2.strategy.testing import MinimumCostTestSelector, SuppliedIntentTestPolicy
from tests.v2.contracts.test_cost_projection import AS_OF
from tests.v2.contracts.test_evidence_economics import assumption, source, standards
from tests.v2.contracts.test_layered_resolver import changed
from tests.v2.contracts.test_strategy_boundary import boundary
from tests.v2.fakes import FakeClock


def reprepare(prepared, records):
    p = changed(prepared, records=records)
    digest = prepared_hash(p)
    return changed(p, integrity_hash=digest, artifact_id="sha256:" + digest)


def recorded(relationship, amount=47, body="Please review our terms.", *, disabled=False):
    context, state, budget, packages = boundary(relationship, 43)
    release, override = source(relationship, 43), source(relationship, amount, "case")
    std = standards()
    quote = changed(
        release,
        record_id="quote:applicable-1",
        canonical_id="quote:terms",
        payload=m.QuoteFact(
            kind="quote",
            supplier="sup:F",
            part_ids=release.payload.unit_cost.basis.part_ids,
            price=release.payload.unit_cost,
            observed_terms=std.bindings,
        ),
    )
    manifest = m.SourceManifest(
        source_id="synthetic:offline", content_hash="0" * 64, files=(), declared_version="declared-test-input/1"
    )
    manifest = changed(manifest, content_hash=semantic_hash(manifest.model_dump(mode="json", exclude={"content_hash"})))
    prepared = m.PreparedEvidence(
        artifact_id="sha256:" + "0" * 64,
        integrity_hash="0" * 64,
        base_manifest=manifest,
        records=(release, override, quote),
        indexes=(),
        parser_versions=("typed-recorded-test/1",),
        prepared_at=AS_OF,
    )
    prepared = reprepare(prepared, prepared.records)
    cost = m.ResolvedCostInput(
        unit_cost=override.payload.unit_cost,
        scope=override.scope,
        temporal=override.temporal,
        source_refs=(m.SourceRef(record_id=override.record_id, canonical_id=override.canonical_id),),
        issues=(),
    )
    declared = assumption(cost, override)
    thread = state.server.threads[0]
    msg = m.ConversationMessage(
        session_id=state.server.session_id,
        thread_id=thread.thread_id,
        message_id="message:test",
        supplier_id="sup:F",
        speaker="supplier",
        body=body,
        observed_sheets=(),
        attachments=(),
        claim_results=(),
        received_at=AS_OF,
        content_hash=hashlib.sha256(body.encode()).hexdigest(),
    )
    conversation = changed(thread.conversation, messages=(msg,), version_hash=semantic_hash((msg,)))
    thread = changed(thread, standards=std, conversation=conversation)
    server = changed(state.server, threads=(thread,), observed_at=AS_OF)
    state = changed(state, server=server)
    inputs = OfflineRecordedInputs(
        prepared=prepared,
        case=context.case,
        server=server,
        documents=(),
        as_of=AS_OF,
        state=state,
        budget=budget,
        target_supplier_id="sup:F",
        cost_policy=context.economic.cost_policy,
        estimate_mode="disabled_explicit" if disabled else "nominal_explicit",
        cost_assumptions=()
        if disabled
        else (RecordedCostAssumption(supplier_id="sup:F", canonical_id="cost:310010", assumption=declared),),
        packages=packages,
    )
    return load_recorded_json(inputs.model_dump_json())


def services(
    inputs,
    *,
    clock=None,
    interpreter=None,
    proposal=None,
    generator=None,
    selector=None,
    validator=None,
    renderer_factory=None,
):
    clock = clock or FakeClock()
    evaluator = OfficialEconomicEvaluator(oracle=OfficialArithmetic())
    assembler = OfflineContextAssembler(
        context_builder=LayeredContextBuilder(),
        projections=EvidenceProjections(),
        estimate_builder=SourceCostEstimateBuilder(),
    )
    coordinator = OfflineDecisionCoordinator(
        interpreter=interpreter or InputEchoTestInterpreter(supplier_id="sup:F"),
        proposal=proposal or SuppliedIntentTestPolicy(supplier_id="sup:F"),
        generator=generator or SuppliedCandidateGenerator(packages=inputs.packages),
        evaluator=evaluator,
        selector=selector or MinimumCostTestSelector(),
        renderer_factory=renderer_factory or (lambda batch: TemplateActionRenderer(batch=batch)),
        validator=validator or FinalActionValidator(evaluator=evaluator, clock=clock),
        payload_encoder=payload_bytes,
        clock=clock,
    )
    return assembler, coordinator


async def run(inputs, **overrides):
    assembler, coordinator = services(inputs, **overrides)
    return await run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator)


@pytest.mark.asyncio
async def test_complete_typed_offline_decision_and_reproducible_trace(relationship):
    inputs = recorded(relationship)
    original = inputs.model_dump_json()
    trace = await run(inputs)
    assert trace.outcome.kind == "selected"
    assert trace.validation.kind == "valid"
    assert [s.name for s in trace.stages] == [
        "snapshot",
        "interpretation",
        "proposal",
        "generation",
        "evaluation",
        "selection",
        "rendering",
        "validation",
    ]
    assert all(s.status == "completed" for s in trace.stages)
    assert trace.rendered.payload.packages == (inputs.packages[1],)
    assert trace.assessment.status == "fallback"
    assert trace.assessment.observations[0].citations[0].quote == inputs.server.threads[0].conversation.messages[0].body
    assert trace.validated_message_bytes == payload_bytes(trace.rendered.payload)
    assert trace.validation.action.payload_hash == hashlib.sha256(trace.validated_message_bytes).hexdigest()
    assert trace.recorded_input_bytes == canonical_json(inputs)
    assert trace == await run(inputs)
    reloaded = OfflineDecisionTrace.model_validate_json(trace.model_dump_json())
    assert reloaded == trace
    reloaded.verify()
    assert inputs.model_dump_json() == original


@pytest.mark.asyncio
async def test_evidence_reversal_survives_assembly_and_complete_coordinator(relationship):
    one, two = await run(recorded(relationship, 43)), await run(recorded(relationship, 47))
    assert one.rendered.payload.packages[0] != two.rendered.payload.packages[0]
    assert one.evaluations.items[0].economic[0].assumption_refs != two.evaluations.items[0].economic[0].assumption_refs
    for trace, price in ((one, Decimal("45")), (two, Decimal("49"))):
        assert next(t.value for t in trace.rendered.payload.packages[0].bindings if t.field == "unit_price") == price
        assert trace.validation.kind == "valid"
        parsed = load_recorded_json(trace.recorded_input_bytes)
        assert parsed.prepared.records[1].record_id in {
            ref.record_id for item in trace.evaluations.items for r in item.economic for ref in r.assumption_refs
        }


@pytest.mark.asyncio
async def test_irrelevant_wording_reaches_interpreter_without_changing_economics(relationship):
    a, b = (
        await run(recorded(relationship, body="Hello.")),
        await run(recorded(relationship, body="Thank you, have a pleasant day!")),
    )
    assert a.assessment != b.assessment and a.trace_hash != b.trace_hash
    assert a.rendered.payload.packages == b.rendered.payload.packages
    assert [i.economic for i in a.evaluations.items] == [i.economic for i in b.evaluations.items]
    assert a.validation.action.economic_fingerprint == b.validation.action.economic_fingerprint


@pytest.mark.asyncio
async def test_disabled_estimates_control_is_unchanged(relationship):
    a, b = await run(recorded(relationship, 43, disabled=True)), await run(recorded(relationship, 47, disabled=True))
    assert a.rendered.payload.packages == b.rendered.payload.packages
    assert [i.economic for i in a.evaluations.items] == [i.economic for i in b.evaluations.items]


@pytest.mark.parametrize(
    "fault",
    ["conflict", "missing_quote", "missing_assumption_ref", "stale_cost", "scope", "stale_context", "prepared_hash"],
)
def test_assembly_fails_closed_on_evidence_and_attribution_faults(relationship, fault):
    inputs = recorded(relationship)
    records = inputs.prepared.records
    if fault == "conflict":
        records += (source(relationship, 48, "case"),)
    elif fault == "missing_quote":
        records = records[:-1]
    elif fault == "missing_assumption_ref":
        req = inputs.cost_assumptions[0]
        a = changed(
            req.assumption, payload=changed(req.assumption.payload, assumptions=(m.SourceRef(record_id="missing"),))
        )
        inputs = changed(inputs, cost_assumptions=(changed(req, assumption=a),))
    elif fault == "stale_cost":
        records = (records[0], changed(records[1], temporal=changed(records[1].temporal, status="stale")), records[2])
    elif fault == "scope":
        records = (
            records[0],
            changed(records[1], scope=changed(records[1].scope, supplier_ids=("sup:other",))),
            records[2],
        )
    elif fault == "stale_context":
        inputs = changed(inputs, expected_context_version="context:obsolete")
    if fault == "prepared_hash":
        inputs = changed(inputs, prepared=changed(inputs.prepared, integrity_hash="b" * 64))
    else:
        inputs = changed(inputs, prepared=reprepare(inputs.prepared, records))
    assembler, _ = services(inputs)
    with pytest.raises(ContractViolation):
        assembler.assemble(inputs)


def test_codec_rejects_invalid_server_and_answer_fields(relationship):
    inputs = recorded(relationship)
    raw = json.loads(inputs.model_dump_json())
    raw["desired_action"] = {"unit_price": 49}
    with pytest.raises(ValidationError):
        load_recorded_json(json.dumps(raw))
    raw = json.loads(inputs.model_dump_json())
    raw["server"]["status"] = "ended"
    with pytest.raises(ValidationError):
        load_recorded_json(json.dumps(raw))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["state_version", "context_version", "conversation", "expired_budget", "economic_hash"]
)
async def test_coordinator_rejects_inconsistent_or_stale_snapshots(relationship, fault):
    inputs = recorded(relationship)
    assembler, coordinator = services(inputs)
    snapshot = assembler.assemble(inputs)
    if fault == "state_version":
        snapshot = snapshot.model_copy(update={"state": changed(snapshot.state, version=1)})
    elif fault == "context_version":
        context = snapshot.context.model_copy(
            update={"snapshot": changed(snapshot.context.snapshot, context_version="obsolete")}
        )
        snapshot = snapshot.model_copy(update={"context": context})
    elif fault == "conversation":
        snapshot = snapshot.model_copy(
            update={"conversation": snapshot.conversation.model_copy(update={"thread_id": "wrong"})}
        )
    elif fault == "expired_budget":
        snapshot = changed(snapshot, budget=changed(snapshot.budget, deadline_at=AS_OF))
    elif fault == "economic_hash":
        ec = changed(snapshot.context.economic, fingerprint="b" * 64)
        snapshot = changed(snapshot, context=changed(snapshot.context, economic=ec))
    trace = await coordinator.run_once(snapshot)
    assert trace.outcome.kind == "cannot_decide"
    assert trace.stages[-1].status == "failed"
    assert trace.validation is None and trace.validated_message_bytes is None


@pytest.mark.asyncio
async def test_forged_candidates_and_expired_validation_are_traced(relationship):
    inputs = recorded(relationship)

    class ForgedGenerator(SuppliedCandidateGenerator):
        def generate_candidates(self, intent, context, state, budget):
            result = super().generate_candidates(intent, context, state, budget)
            c = changed(result.candidates[0], candidate_id="forged")
            return changed(result, candidates=(c,))

    forged = await run(inputs, generator=ForgedGenerator(packages=inputs.packages))
    assert forged.outcome.kind == "cannot_decide" and forged.stages[-1].name == "generation"
    assert forged.generations[0].candidates[0].candidate_id == "forged"

    class ExpiredValidator:
        def validate_action(self, action, context, state, budget):
            original = FinalActionValidator(
                evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=FakeClock()
            )
            result = original.validate_action(action, context, state, budget)
            return changed(result, action=changed(result.action, expires_at=AS_OF))

    expired = await run(inputs, validator=ExpiredValidator())
    assert expired.outcome.kind == "cannot_decide" and expired.stages[-1].name == "validation"
    assert expired.validation is not None and expired.validated_message_bytes is None


@pytest.mark.asyncio
async def test_rejected_candidate_and_rejected_rendered_action_remain_in_trace(relationship):
    inputs = recorded(relationship)
    policy = changed(inputs.cost_policy, ceiling=m.Money(amount=Decimal("410000")))
    trace = await run(changed(inputs, cost_policy=policy))
    assert trace.outcome.kind == "selected"
    assert any(item.disposition == "rejected" for item in trace.evaluations.items)
    assert any(i.code == "infeasible" for i in trace.issues)
    assert trace.validation.kind == "valid"

    class PrivateRenderer(TemplateActionRenderer):
        def render(self, decision, selected, claims, context):
            action = super().render(decision, selected, claims, context)
            action = changed(action, payload=changed(action.payload, body="Our private budget is 500000."))
            return changed(action, render_hash=render_hash(action))

    rejection = await run(inputs, renderer_factory=lambda batch: PrivateRenderer(batch=batch))
    assert rejection.outcome.kind == "cannot_decide"
    assert rejection.rendered is not None and rejection.decision is not None
    assert rejection.validation.kind == "invalid" and rejection.validated_message_bytes is None
    assert any(i.code == "private_disclosure" for i in rejection.issues)


@pytest.mark.asyncio
async def test_interpreter_and_both_strategy_ports_are_replaceable(relationship):
    inputs = recorded(relationship)
    seen = []

    class ReplacementInterpreter(InputEchoTestInterpreter):
        async def interpret(self, context, conversation, previous_assessment, budget):
            seen.append(("interpreter", context.snapshot, conversation.messages[0].body))
            output = await super().interpret(context, conversation, previous_assessment, budget)
            return changed(output, interpreter_id="replacement-interpreter-test-v1")

    class ReplacementProposal(SuppliedIntentTestPolicy):
        async def propose_strategies(self, context, assessment, state, budget, research):
            seen.append(("proposal", context.snapshot, assessment.interpreter_id))
            return await super().propose_strategies(context, assessment, state, budget, research)

    class ReplacementSelector(MinimumCostTestSelector):
        async def select_action(self, candidates, assessment, state, budget, research):
            seen.append(("selector", candidates.snapshot, assessment.observations[0].citations[0].quote))
            result = await super().select_action(candidates, assessment, state, budget, research)
            alternate = next(i for i in candidates.items if i.candidate.contents.packages == (inputs.packages[0],))
            return changed(
                result,
                selector_id="replacement-selector-test-v1",
                candidate_id=alternate.candidate.candidate_id,
                evaluation_id=alternate.evaluation_id,
            )

    trace = await run(
        inputs,
        interpreter=ReplacementInterpreter(supplier_id="sup:F"),
        proposal=ReplacementProposal(supplier_id="sup:F"),
        selector=ReplacementSelector(),
    )
    assert trace.outcome.kind == "selected" and trace.validation.kind == "valid"
    assert trace.rendered.payload.packages == (inputs.packages[0],)
    assert [item[0] for item in seen] == ["interpreter", "proposal", "selector"]
    assert all(item[1] == trace.snapshot for item in seen)
    assert seen[0][2] == seen[2][2] == inputs.server.threads[0].conversation.messages[0].body
    assert seen[1][2] == trace.assessment.interpreter_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["assessment_snapshot", "ungrounded_span", "unknown_intent_observation", "forged_selection"]
)
async def test_untrusted_component_outputs_cannot_cross_stage_boundaries(relationship, fault):
    inputs = recorded(relationship)

    class BadInterpreter(InputEchoTestInterpreter):
        async def interpret(self, context, conversation, previous_assessment, budget):
            result = await super().interpret(context, conversation, previous_assessment, budget)
            if fault == "assessment_snapshot":
                return changed(result, snapshot=changed(result.snapshot, state_version=99))
            obs = result.observations[0]
            span = obs.citations[0]
            span = changed(span, quote="invented", start=0, end=8)
            return changed(result, observations=(changed(obs, citations=(span,)),))

    class BadProposal(SuppliedIntentTestPolicy):
        async def propose_strategies(self, context, assessment, state, budget, research):
            result = await super().propose_strategies(context, assessment, state, budget, research)
            return changed(result, intents=(changed(result.intents[0], observation_refs=("invented",)),))

    class BadSelector(MinimumCostTestSelector):
        async def select_action(self, candidates, assessment, state, budget, research):
            result = await super().select_action(candidates, assessment, state, budget, research)
            return changed(result, candidate_id="invented")

    overrides = (
        {"interpreter": BadInterpreter(supplier_id="sup:F")}
        if fault
        in (
            "assessment_snapshot",
            "ungrounded_span",
        )
        else {"proposal": BadProposal(supplier_id="sup:F")}
        if fault == "unknown_intent_observation"
        else {"selector": BadSelector()}
    )
    trace = await run(inputs, **overrides)
    assert trace.outcome.kind == "cannot_decide"
    assert trace.validated_message_bytes is None and trace.stages[-1].status == "failed"
    assert trace.stages[-1].name == (
        "interpretation" if "interpreter" in overrides else "proposal" if "proposal" in overrides else "selection"
    )


@pytest.mark.asyncio
async def test_expired_certificate_after_validator_returns_is_not_admitted(relationship):
    inputs = recorded(relationship)
    clock = FakeClock()

    class LateValidator:
        def validate_action(self, action, context, state, budget):
            result = FinalActionValidator(
                evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=clock
            ).validate_action(action, context, state, budget)
            clock.advance(61)
            return result

    trace = await run(inputs, clock=clock, validator=LateValidator())
    assert trace.outcome.kind == "cannot_decide"
    assert trace.stages[-1].name == "validation"
    assert trace.validation.kind == "valid" and trace.validated_message_bytes is None


def test_temporal_derivation_preserves_raw_original_and_unknowns(relationship):
    inputs = recorded(relationship)
    records = inputs.prepared.records
    expired = changed(
        records[1],
        temporal=changed(records[1].temporal, valid_to=AS_OF.date() - timedelta(days=1)),
    )
    prepared = reprepare(inputs.prepared, (records[0], expired, records[2]))
    context = LayeredContextBuilder().build_context(prepared, inputs.case, inputs.server, (), inputs.as_of)
    winner = next(r for r in context.records if r.record_id == expired.record_id)
    assert winner.temporal.status == "stale" and prepared.records[1].temporal.status == "current"
    assert winner.provenance == expired.provenance and winner.disclosure == expired.disclosure
    unknown = changed(expired, temporal=changed(expired.temporal, valid_to=None, status="unknown"))
    prepared = reprepare(prepared, (records[0], unknown, records[2]))
    context = LayeredContextBuilder().build_context(prepared, inputs.case, inputs.server, (), inputs.as_of)
    assert next(r for r in context.records if r.record_id == unknown.record_id).temporal.status == "unknown"


@pytest.mark.asyncio
async def test_trace_byte_tampering_is_detected(relationship):
    trace = await run(recorded(relationship))
    tampered = trace.model_copy(update={"validated_message_bytes": b"{}"})
    with pytest.raises(ContractViolation, match="digest mismatch"):
        tampered.verify()


@pytest.mark.asyncio
async def test_complete_registered_clarification_keeps_rejected_generation(relationship):
    inputs = changed(recorded(relationship), packages=())
    trace = await run(inputs, proposal=SuppliedIntentTestPolicy(supplier_id="sup:F", include_question=True))
    assert trace.outcome.kind == "selected" and trace.validation.kind == "valid"
    assert trace.rendered.kind == "question" and not trace.rendered.payload.packages
    assert not trace.evaluations.items[0].economic
    assert trace.generations[0].rejections and not trace.generations[0].candidates
    assert trace.validated_message_bytes == payload_bytes(trace.rendered.payload)
