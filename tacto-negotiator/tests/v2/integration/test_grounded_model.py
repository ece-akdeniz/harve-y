"""Budgeted fake-transport plumbing and bounded semantics; no model-quality claim."""

import asyncio
import hashlib
import json
import threading
import time
from decimal import Decimal
from uuid import UUID

import pytest

from negotiator.v2.adapters.model import AsyncModelGateway
from negotiator.v2.core import models as m
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.intelligence.interpreter import GroundedInterpreter, InterpreterConfig
from negotiator.v2.orchestration.budgets import DecisionModelLedger, failure
from negotiator.v2.orchestration.offline import OfflineDecisionTrace
from tests.v2.contracts.test_layered_resolver import changed
from tests.v2.fakes import FakeClock
from tests.v2.integration.test_offline_decision import recorded, services


def setup(relationship, body="We prefer delivery flexibility.", *, seconds="1", tokens=2048):
    inputs = recorded(relationship, body=body)
    inputs = changed(inputs, budget=changed(inputs.budget, model_call_limit=2, model_time_limit_s=Decimal(seconds)))
    assembler, coordinator = services(inputs)
    snapshot = assembler.assemble(inputs)
    clock = FakeClock()
    ledger = DecisionModelLedger(budget=inputs.budget, clock=clock, token_limit=tokens)
    config = InterpreterConfig(provider_id="fake", protocol_id="injected-v1", model_id="test-model",
                               prompt_version="grounded-supplier-v1", task_schema_version="assessment-draft-v1",
                               max_tokens=512, time_limit_s=Decimal(seconds),
                               approved_message_hashes=tuple(
                                   msg.content_hash for msg in snapshot.conversation.messages))
    return inputs, snapshot, coordinator, clock, ledger, config


def draft(snapshot, kind="ambiguity", **updates):
    msg = snapshot.conversation.messages[0]
    span = m.MessageSpan(session_id=msg.session_id, thread_id=msg.thread_id, message_id=msg.message_id,
                         start=0, end=len(msg.body), quote=msg.body)
    observation = m.GroundedObservation(observation_id="observation:1", kind=kind, dimension=None,
                                        summary=msg.body, citations=(span,))
    return m.AssessmentDraft(observations=(observation,), reported_constraints=(), hypotheses=(),
                             uncertainties=(), questions=(), unknowns=(), **updates)


def success(request, raw, usage=None):
    return m.ModelSuccess(kind="success", call_id=request.call_id, model_id=request.model_id,
                          elapsed_s=Decimal("0"), issues=(), raw_response_json=raw,
                          response_hash=hashlib.sha256(raw.encode()).hexdigest(), usage=usage or m.ModelUsage())


def test_ledger_owns_stage_caps_and_clips_refreshed_stage_budgets(relationship):
    inputs, _, _, clock, ledger, _ = setup(relationship, seconds="12")
    original_deadline = inputs.budget.deadline_at
    interpret = ledger.model_budget(task="interpret", max_tokens=512, time_limit_s=Decimal("12"))
    assert interpret.time_limit_s <= Decimal("8")
    clock.advance(3)
    proposal = ledger.model_budget(task="propose", max_tokens=512, time_limit_s=Decimal("12"))
    assert proposal.time_limit_s <= Decimal("4")
    assert proposal.deadline_at < original_deadline
    clock.advance(8)
    with pytest.raises(ContractViolation, match="no model time remains"):
        ledger.model_budget(task="propose", max_tokens=512, time_limit_s=Decimal("12"))


class Transport:
    def __init__(self, raw, *, kind="success", usage=None):
        self.raw, self.kind, self.usage = raw, kind, usage
        self.calls = []

    async def __call__(self, request, budget):
        self.calls.append((request, budget))
        if self.kind == "success":
            return success(request, self.raw, self.usage)
        return failure(request, self.kind, "scripted")


def interpreter(clock, ledger, config, transport):
    gateway = AsyncModelGateway(transport=transport, ledger=ledger)
    return GroundedInterpreter(model=gateway, clock=clock, config=config)


@pytest.mark.asyncio
async def test_interpreter_and_coordinator_retain_attributed_usage_and_safe_raw(relationship):
    inputs, snapshot, coordinator, clock, ledger, config = setup(relationship)
    raw = draft(snapshot).model_dump_json()
    transport = Transport(raw, usage=m.ModelUsage(input_tokens=100, output_tokens=60))
    coordinator.interpreter = interpreter(clock, ledger, config, transport)
    coordinator.model_token_limit = 2048
    trace = await coordinator.run_once(snapshot, recorded_input_bytes=inputs.model_dump_json().encode())
    assert trace.assessment.status == "ok"
    assert trace.validation.kind == "valid"
    assert trace.assessment.model_call_id == str(trace.model_calls[0].request.call_id)
    assert trace.model_calls[0].usage.input_tokens == 100
    assert trace.model_calls[0].charged_tokens == 160
    assert trace.model_calls[0].permitted_raw_response == raw
    assert trace.model_calls[0].response_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert trace.model_calls[0].request_hash == semantic_hash(trace.model_calls[0].request)
    restored = OfflineDecisionTrace.model_validate_json(trace.model_dump_json())
    restored.verify()
    assert restored == trace
    # A second decision owns a fresh ledger; the explicit standalone ledger was unused.
    assert ledger.calls == 0


@pytest.mark.parametrize("kind", ("refused", "invalid", "timeout", "capacity_unavailable", "transport_failure"))
@pytest.mark.asyncio
async def test_every_model_failure_retains_unknown_usage_and_fallback(relationship, kind):
    _, snapshot, _, clock, ledger, config = setup(relationship)
    transport = Transport("", kind=kind)
    result = await interpreter(clock, ledger, config, transport).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "fallback" and result.model_call_id is not None
    assert result.observations and not result.reported_constraints and not result.hypotheses
    assert ledger.calls == 1 and len(transport.calls) == 1
    assert ledger.traces[0].result_kind == kind
    assert ledger.traces[0].usage.input_tokens is None
    assert ledger.traces[0].charged_tokens == config.max_tokens


@pytest.mark.parametrize("fault", ("json", "quote", "scope", "meaning", "condition", "private", "extra", "number"))
@pytest.mark.asyncio
async def test_schema_grounding_and_exact_quote_wrong_meaning_fail(relationship, fault):
    _, snapshot, _, clock, ledger, config = setup(relationship, body="If payment is 30 days, we can offer EUR 49.")
    response = json.loads(draft(snapshot, "conditional_offer").model_dump_json())
    span = response["observations"][0]["citations"][0]
    if fault == "json":
        raw = "{"
    else:
        if fault == "quote":
            span["quote"] = "different words"
        elif fault == "scope":
            span["session_id"] = "session:foreign"
        elif fault == "meaning":
            response["observations"][0]["kind"] = "constraint"
        elif fault == "condition":
            span["start"] = snapshot.conversation.messages[0].body.index("we can")
            span["quote"] = snapshot.conversation.messages[0].body[span["start"]:]
            response["observations"][0]["summary"] = span["quote"]
        elif fault == "private":
            response["unknowns"] = ["private reservation cost 100"]
        elif fault == "extra":
            response["action"] = "accept"
        elif fault == "number":
            response["reported_constraints"] = [{
                "constraint_id": "c:1", "dimension": "unit_price", "op": "==", "value": "45",
                "condition_observation_refs": ["observation:1"], "citations": [span],
                "authority": "supplier_reported", "status": "active",
            }]
        raw = json.dumps(response)
    result = await interpreter(clock, ledger, config, Transport(raw)).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "fallback"
    assert ledger.traces[0].permitted_raw_response is None
    assert ledger.traces[0].response_hash == hashlib.sha256(raw.encode()).hexdigest()


@pytest.mark.parametrize("private", ("Our buyer budget is 100.", "LLM_API_KEY=abc", "expected_action=accept"))
@pytest.mark.asyncio
async def test_raw_private_prose_rejected_even_when_hash_approved(relationship, private):
    _, snapshot, _, clock, ledger, config = setup(relationship, body=private)
    transport = Transport("{}")
    result = await interpreter(clock, ledger, config, transport).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "fallback" and result.model_call_id is None
    assert not transport.calls and ledger.calls == 0


@pytest.mark.asyncio
async def test_projection_excludes_economics_evidence_and_previous_text(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship)
    transport = Transport(draft(snapshot).model_dump_json())
    component = interpreter(clock, ledger, config, transport)
    previous = await component.interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
    previous = changed(previous, unknowns=("private target_price 10",))
    # Fresh ledger: model-call identity is content-derived; same-decision replays are blocked.
    ledger2 = DecisionModelLedger(budget=snapshot.budget, clock=clock, token_limit=2048)
    result = await interpreter(clock, ledger2, config, transport).interpret(
        snapshot.context, snapshot.conversation, previous, snapshot.budget,
    )
    projected = transport.calls[-1][0].input
    assert projected.evidence == () and projected.previous is None
    assert "target_price" not in projected.model_dump_json()
    assert "cost_policy" not in projected.model_dump_json()
    assert result.parent_assessment_id == previous.assessment_id and result.revision == 2


@pytest.mark.asyncio
async def test_new_requests_do_not_reset_call_or_unknown_token_budget(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, tokens=1024)
    transport = Transport(draft(snapshot).model_dump_json())
    component = interpreter(clock, ledger, config, transport)
    await component.interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
    original_request, mb = transport.calls[0]
    gateway = component.model
    second = changed(original_request, call_id=UUID(int=2))
    assert (await gateway.complete(second, mb)).kind == "success"
    third = changed(original_request, call_id=UUID(int=3))
    assert (await gateway.complete(third, mb)).kind == "capacity_unavailable"
    assert ledger.calls == 2 and ledger.tokens == 1024 and len(transport.calls) == 2
    assert all(t.usage.input_tokens is None for t in ledger.traces)


@pytest.mark.asyncio
async def test_token_overrun_and_partial_usage_are_not_free(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship)
    raw = draft(snapshot).model_dump_json()
    result = await interpreter(clock, ledger, config, Transport(raw, usage=m.ModelUsage(input_tokens=1))).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "ok" and ledger.tokens == 512
    ledger2 = DecisionModelLedger(budget=snapshot.budget, clock=clock, token_limit=1024)
    result = await interpreter(clock, ledger2, config, Transport(raw, usage=m.ModelUsage(
        input_tokens=700, output_tokens=400,
    ))).interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
    assert result.status == "fallback" and ledger2.tokens == 1100
    assert ledger2.traces[0].usage.output_tokens == 400


@pytest.mark.parametrize("mode", ("hung", "late", "cancel", "reserves", "mismatch", "transport"))
@pytest.mark.asyncio
async def test_deadline_cancel_identity_and_transport_paths(relationship, mode):
    _, snapshot, _, clock, ledger, config = setup(relationship, seconds="0.02")
    cancelled = asyncio.Event()

    async def transport(request, budget):
        if mode in ("hung", "cancel"):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        if mode == "transport":
            raise OSError("SECRET should never reach trace")
        if mode == "late":
            clock.advance(60)
        result = success(request, draft(snapshot).model_dump_json())
        return changed(result, call_id=UUID(int=3)) if mode == "mismatch" else result

    component = interpreter(clock, ledger, config, transport)
    if mode == "reserves":
        clock.advance(9)
    task = asyncio.create_task(component.interpret(snapshot.context, snapshot.conversation, None, snapshot.budget))
    if mode == "cancel":
        await asyncio.sleep(0.001)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(cancelled.wait(), 0.1)
        assert ledger.traces[0].result_kind == "cancelled"
    else:
        result = await asyncio.wait_for(task, 0.2)
        assert result.status == "fallback"
        if mode == "hung":
            await asyncio.wait_for(cancelled.wait(), 0.1)
        assert "SECRET" not in str(ledger.traces)


@pytest.mark.parametrize("case_id", (
    "conditional-offer", "unconditional-request", "hard-payment", "payment-preference", "scoped-refusal",
    "general-refusal", "approval-unknown", "contradiction", "reported-cost-rise", "greeting", "injection",
))
@pytest.mark.asyncio
async def test_provisional_semantic_corpus_routes_reviewed_draft_shapes(relationship, case_id):
    from pathlib import Path

    labels = json.loads((Path(__file__).parents[2] / "fixtures/v2/interpretation-pilot.json").read_text())
    label = next(item for item in labels["examples"] if item["id"] == case_id)
    _, snapshot, _, clock, ledger, config = setup(relationship, body=label["text"])
    scripted = draft(snapshot, label["observation_kinds"][0])
    scripted = changed(scripted, unknowns=tuple(label["unknowns"]))
    span = scripted.observations[0].citations[0]
    if case_id in ("hard-payment", "contradiction"):
        constraints = tuple(m.ReportedConstraint(
            constraint_id=f"constraint:{v}", dimension="payment_days", op="==", value=v,
            condition_observation_refs=(), citations=(span,), authority="supplier_reported", status="active",
        ) for v in ((30, 60) if case_id == "contradiction" else (30,)))
        scripted = changed(scripted, reported_constraints=constraints)
    if case_id == "payment-preference":
        hypothesis = m.PreferenceHypothesis(
            hypothesis_id="hypothesis:payment", dimension="payment_days", relation="prefers", direction="unknown",
            summary=label["text"], supporting_refs=(span,), contradicting_refs=(), confidence="low", status="active",
        )
        scripted = changed(scripted, hypotheses=(hypothesis,))
    if case_id == "contradiction":
        scripted = changed(scripted, uncertainties=(m.AssessmentUncertainty(
            uncertainty_id="uncertainty:contradiction", kind="contradiction", summary=label["text"], citations=(span,),
            related_observation_refs=("observation:1",), blocking=True,
        ),))
    result = await interpreter(clock, ledger, config, Transport(scripted.model_dump_json())).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "ok"
    assert {o.kind for o in result.observations} == set(label["observation_kinds"])
    assert set(label["unknowns"]) <= set(result.unknowns)
    assert all(c.authority == "supplier_reported" for c in result.reported_constraints)
    assert all(h.numeric_effect is None for h in result.hypotheses)
    assert snapshot.context.case == snapshot.state.case


@pytest.mark.asyncio
async def test_preference_is_not_hard_constraint_and_approval_is_not_certain(relationship):
    for body, kind in (("We prefer payment in 30 days.", "constraint"),
                       ("This needs manager approval.", "approval_requirement")):
        _, snapshot, _, clock, ledger, config = setup(relationship, body=body)
        response = draft(snapshot, kind)
        if kind == "constraint":
            response = changed(response, reported_constraints=(m.ReportedConstraint(
                constraint_id="constraint:payment", dimension="payment_days", op="==", value=30,
                condition_observation_refs=(), citations=response.observations[0].citations,
                authority="supplier_reported", status="active",
            ),))
        result = await interpreter(clock, ledger, config, Transport(response.model_dump_json())).interpret(
            snapshot.context, snapshot.conversation, None, snapshot.budget,
        )
        assert result.status == "fallback"
        assert "ungrounded_output" in result.unknowns


def test_semantic_report_retains_missing_outputs_and_unreviewed_critical_errors():
    from experiments.v2.evaluate_interpretation import evaluate

    labels = {"review_status": "pending", "examples": [
        {"id": "a", "group": "conditions", "observation_kinds": ["conditional_offer"], "unknowns": []},
    ]}
    report = evaluate(labels, [])
    assert report["denominator"] == 1 and report["missing"] == 1
    assert report["recall"] == 0 and report["precision"] is None


@pytest.mark.asyncio
async def test_cancellation_resistant_late_transport_is_never_admitted(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, seconds="0.01")
    release = asyncio.Event()
    finished = asyncio.Event()

    async def resistant(request, budget):
        try:
            await release.wait()
        except asyncio.CancelledError:
            await release.wait()
        finished.set()
        return success(request, draft(snapshot).model_dump_json())

    result = await asyncio.wait_for(interpreter(clock, ledger, config, resistant).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    ), 0.1)
    assert result.status == "fallback"
    assert ledger.traces[0].result_kind == "timeout"
    release.set()
    await asyncio.wait_for(finished.wait(), 0.1)
    assert ledger.traces[0].permitted_raw_response is None
    assert result.status == "fallback"


@pytest.mark.asyncio
async def test_unapproved_message_and_mixed_history_fail_without_truncation(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship)
    transport = Transport("{}")
    buyer_conversation = changed(
        snapshot.conversation, messages=(changed(snapshot.conversation.messages[0], speaker="buyer"),),
    )
    for config2, conversation in (
        (changed(config, approved_message_hashes=()), snapshot.conversation),
        (config, buyer_conversation),
    ):
        result = await interpreter(clock, ledger, config2, transport).interpret(
            snapshot.context, conversation, None, snapshot.budget,
        )
        assert result.status == "fallback"
    assert transport.calls == []


@pytest.mark.asyncio
async def test_internal_clarification_is_grounded_but_not_an_outgoing_action(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, body="This needs manager approval.")
    response = changed(draft(snapshot, "approval_requirement"), unknowns=("approval",))
    response = changed(response, questions=(m.ClarificationQuestion(
        question_id="question:approval", template_id="clarify:terms", dimension=None,
        citations=response.observations[0].citations, unknown_id="approval",
        expected_information="Clarify the reported uncertainty.",
    ),))
    result = await interpreter(clock, ledger, config, Transport(response.model_dump_json())).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "ok" and result.questions[0].unknown_id == "approval"
    assert not hasattr(result, "action")


@pytest.mark.asyncio
async def test_insufficient_token_capacity_is_rejected_before_transport(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, tokens=100)
    transport = Transport(draft(snapshot).model_dump_json())
    result = await interpreter(clock, ledger, config, transport).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert result.status == "fallback" and not transport.calls
    assert ledger.calls == 0 and ledger.tokens == 0
    assert ledger.traces[0].result_kind == "capacity_unavailable"


@pytest.mark.asyncio
async def test_shared_scope_covers_separate_gateway_consumers_and_queue_time(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, seconds="0.02")
    transport = Transport(draft(snapshot).model_dump_json())
    component = interpreter(clock, ledger, config, transport)
    await component.interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
    request, mb = transport.calls[0]
    other = AsyncModelGateway(transport=transport)
    with component.decision_scope(ledger):
        assert (await other.complete(changed(request, call_id=UUID(int=2)), mb)).kind == "success"
        assert (await other.complete(changed(request, call_id=UUID(int=3)), mb)).kind == "capacity_unavailable"
    assert ledger.calls == 2


@pytest.mark.asyncio
async def test_concurrent_request_does_not_bypass_pending_reservation(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, seconds="0.1")
    warmup = Transport(draft(snapshot).model_dump_json())
    component = interpreter(clock, ledger, config, warmup)
    await component.interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
    request, mb = warmup.calls[0]
    entered, release = asyncio.Event(), asyncio.Event()

    async def queued(req, budget):
        entered.set()
        await release.wait()
        return success(req, draft(snapshot).model_dump_json())

    gateway = AsyncModelGateway(transport=queued, ledger=ledger)
    pending = asyncio.create_task(gateway.complete(changed(request, call_id=UUID(int=2)), mb))
    await entered.wait()
    rejected = await gateway.complete(changed(request, call_id=UUID(int=3)), mb)
    assert rejected.kind == "capacity_unavailable"
    release.set()
    assert (await pending).kind == "success"
    assert ledger.calls == 2


@pytest.mark.asyncio
async def test_transport_stop_is_visible_before_timeout_cancellation_cleanup(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, seconds="0.02")
    cleanup = asyncio.Event()

    class Guard:
        stopped = False

        def stop_model_calls(self, reason):
            self.stopped = True

        async def __call__(self, request, budget):
            try:
                await asyncio.Event().wait()
            finally:
                cleanup.set()

    guard = Guard()
    assessment = await interpreter(clock, ledger, config, guard).interpret(
        snapshot.context, snapshot.conversation, None, snapshot.budget,
    )
    assert assessment.status == "fallback"
    assert guard.stopped is True
    await asyncio.wait_for(cleanup.wait(), timeout=1)


@pytest.mark.asyncio
async def test_timeout_revokes_following_stage_and_keeps_unknown_usage_reserved(relationship):
    _, snapshot, _, clock, ledger, config = setup(relationship, seconds="0.02", tokens=1024)
    entered = asyncio.Event()

    class SlowTransport:
        stopped = False

        def stop_model_calls(self, reason):
            self.stopped = True

        async def __call__(self, request, budget):
            entered.set()
            await asyncio.Event().wait()

    transport = SlowTransport()
    gateway = AsyncModelGateway(transport=transport, ledger=ledger)
    component = GroundedInterpreter(model=gateway, clock=clock, config=config)
    assessment = await component.interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
    assert assessment.status == "fallback" and entered.is_set()
    first = ledger.traces[0]
    assert first.result_kind == "timeout" and first.charged_tokens == config.max_tokens
    assert ledger.tokens == config.max_tokens and ledger.disabled_reason == "model_timeout"

    later = changed(first.request, call_id=UUID(int=99))
    later_budget = m.ModelBudget(deadline_at=snapshot.budget.deadline_at, time_limit_s=Decimal("0.5"),
                                 max_tokens=512, max_calls=1, retry_limit=0)
    result = await gateway.complete(later, later_budget)
    assert result.kind == "capacity_unavailable"
    assert ledger.calls == 1 and ledger.tokens == config.max_tokens


def test_lab_sync_boundary_returns_without_waiting_for_asyncio_shutdown_cleanup():
    from negotiator.v2.adapters.lab import _run_decision_bounded
    from negotiator.v2.core.errors import ContractViolation

    cleaned = threading.Event()

    async def cancellation_resistant():
        await asyncio.sleep(0.4)
        cleaned.set()

    started = time.monotonic()
    with pytest.raises(ContractViolation, match="complete decision exceeded"):
        _run_decision_bounded(cancellation_resistant(), timeout_s=0.15)
    elapsed = time.monotonic() - started
    assert elapsed < 0.3
    assert not cleaned.is_set()
    assert cleaned.wait(1)
