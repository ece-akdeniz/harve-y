"""Finite strategy/economics/independent-validation proof, with adversarial controls."""

import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import TypeAdapter

from negotiator.v2.adapters.official import OfficialArithmetic
from negotiator.v2.core import models as m
from negotiator.v2.core.certificates import QUESTION_ID
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.economics.finite import SuppliedCandidateGenerator
from negotiator.v2.economics.official import OfficialEconomicEvaluator, economic_fingerprint
from negotiator.v2.execution.render import TemplateActionRenderer, render_hash
from negotiator.v2.execution.validation import FinalActionValidator, payload_bytes
from negotiator.v2.strategy.testing import MinimumCostTestSelector, SuppliedIntentTestPolicy
from tests.v2.dto_spec import example

from .test_cost_projection import AS_OF
from .test_evidence_economics import evidence, run, source
from .test_layered_resolver import changed
from .test_package_evaluation import package


class Clock:
    def utcnow(self):
        return AS_OF


def boundary(relationship, amount):
    e = evidence(source(relationship, 43), source(relationship, amount, "case"))
    trace = run(relationship, e)
    economic, packages = trace[3:5]
    snap = m.SnapshotRef(
        run_id="run:boundary",
        session_id="session:boundary",
        state_version=0,
        context_version=e.context_version,
        config_hash="a" * 64,
        case_contract_hash=economic.case.contract_hash,
    )
    context = m.NegotiationContext(
        snapshot=snap, case=economic.case, economic=economic, evidence=e, capabilities=("used-action-v1",), as_of=AS_OF
    )
    server = TypeAdapter(m.ServerState).validate_python(
        TypeAdapter(m.ServerState).validate_json(json.dumps(example("ServerState"))).model_dump()
    )
    original_thread = TypeAdapter(m.ServerThread).validate_json(json.dumps(example("ServerThread")))
    thread = changed(
        original_thread,
        supplier_id="sup:F",
        standards=economic.standards_by_supplier[0].standards,
        clock=changed(
            original_thread.clock, confidence="authoritative", server_deadline_at=AS_OF + timedelta(seconds=120)
        ),
        rounds=changed(original_thread.rounds, confidence="authoritative", server_rounds_used=0),
        conversation=changed(original_thread.conversation, session_id=snap.session_id, messages=()),
    )
    server = changed(server, session_id=snap.session_id, case_id=context.case.case_id, threads=(thread,))
    strategic = m.StrategicState(
        assessments=(), attempts=(), refusals=(), claim_usage=(), outstanding_questions=(), feedback=(), memory=()
    )
    state = m.NegotiationState(
        run_id=snap.run_id,
        attempt_id=UUID(int=1),
        case=context.case,
        server=server,
        strategic=strategic,
        operations=(),
        version=0,
        config_hash=snap.config_hash,
        runtime_status="ready",
        issues=(),
    )
    budget = m.DecisionBudget(
        deadline_at=AS_OF + timedelta(seconds=60),
        compute_limit_s=Decimal("10"),
        model_call_limit=0,
        model_time_limit_s=Decimal("1"),
        candidate_limit=20,
        fallback_reserve_s=Decimal("1"),
        submission_reserve_s=Decimal("1"),
        clock_refs=(),
    )
    return context, state, budget, packages


def intent(context, question=False):
    return m.StrategyIntent(
        intent_id="intent:clarify" if question else "intent:keep",
        strategy_id="test-supplied",
        supplier_id="sup:F",
        snapshot=context.snapshot,
        kind="clarify" if question else "keep",
        direction="unchanged",
        question_id=QUESTION_ID if question else None,
        observation_refs=(),
        evidence_refs=(),
        rationale="Supplied test candidate set.",
    )


async def select(context, state, budget, packages, *, question=False):
    generator = SuppliedCandidateGenerator(packages=packages)
    proposals = await SuppliedIntentTestPolicy(supplier_id="sup:F", include_question=question).propose_strategies(
        context,
        None,
        state,
        budget,
        None,
    )
    proposed = next(i for i in proposals.intents if i.kind == ("clarify" if question else "keep"))
    generation = generator.generate_candidates(proposed, context, state, budget)
    evaluator = OfficialEconomicEvaluator(oracle=OfficialArithmetic())
    batch = evaluator.evaluate_candidates(generation.candidates, context)
    decision = await MinimumCostTestSelector().select_action(batch, None, state, budget, None)
    selected = next(i for i in batch.items if i.candidate.candidate_id == decision.candidate_id)
    action = TemplateActionRenderer(batch=batch).render(decision, selected, (), context)
    result = FinalActionValidator(evaluator=evaluator, clock=Clock()).validate_action(action, context, state, budget)
    return generation, batch, decision, selected, action, result


@pytest.mark.asyncio
async def test_evidence_ranking_reaches_same_strategy_interface_and_validation(relationship):
    first, second = boundary(relationship, 43), boundary(relationship, 47)
    one, two = await select(*first), await select(*second)
    assert first[3] == second[3]
    assert one[3].candidate.contents.packages == (first[3][0],)
    assert two[3].candidate.contents.packages == (second[3][1],)
    assert one[3].economic[0].nominal_cost.amount == Decimal("369600")
    assert two[3].economic[0].nominal_cost.amount == Decimal("401600")
    for inputs, trace in ((first, one), (second, two)):
        assert trace[5].kind == "valid"
        assert trace[2].approved_batch_hash == trace[1].batch_hash
        assert trace[3].economic[0].assumption_refs == inputs[0].economic.estimates[0].assumption_refs
        assert trace[5].action.payload_hash == hashlib.sha256(payload_bytes(trace[4].payload)).hexdigest()
        assert await select(*inputs) == trace


@pytest.mark.asyncio
async def test_registered_clarification_has_no_economics_or_claims(relationship):
    inputs = boundary(relationship, 47)
    trace = await select(*inputs, question=True)
    assert trace[3].candidate.contents.kind == "question" and not trace[3].economic
    assert trace[5].kind == "valid" and not trace[4].payload.packages


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["private_body", "claim", "attachment", "illegal_terms", "ceiling", "stale", "expired", "hash"]
)
async def test_independent_validator_blocks_adversarial_selected_output(relationship, fault):
    context, state, budget, packages = boundary(relationship, 47)
    trace = await select(context, state, budget, packages)
    action = trace[4]
    if fault == "private_body":
        action = changed(action, payload=changed(action.payload, body="Our reservation cost is EUR 500000."))
    elif fault == "claim":
        action = changed(action, claim_ids=("claim:invented",))
    elif fault == "attachment":
        a = TypeAdapter(m.OutboundAttachment).validate_json(json.dumps(example("OutboundAttachment")))
        action = changed(action, payload=changed(action.payload, attachments=(a,)))
    elif fault == "illegal_terms":
        action = changed(
            action,
            payload=changed(
                action.payload, packages=(package({"unit_price": 49, "payment_days": 61}, context.economic),)
            ),
        )
    elif fault == "ceiling":
        policy = changed(context.economic.cost_policy, ceiling=m.Money(amount=Decimal("400000")))
        economic = changed(context.economic, cost_policy=policy)
        economic = changed(economic, fingerprint=economic_fingerprint(economic))
        context = changed(context, economic=economic)
    elif fault == "stale":
        state = changed(state, version=1)
    elif fault == "expired":
        budget = changed(budget, deadline_at=AS_OF)
    action = changed(action, render_hash="b" * 64 if fault == "hash" else render_hash(action))
    result = FinalActionValidator(
        evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=Clock()
    ).validate_action(action, context, state, budget)
    assert result.kind == "invalid"
    assert any(i.severity == "error" for i in result.report.issues)


@pytest.mark.asyncio
async def test_selector_edit_cannot_bypass_registered_membership(relationship):
    context, state, budget, packages = boundary(relationship, 47)
    _, batch, decision, selected, _, _ = await select(context, state, budget, packages)
    renderer = TemplateActionRenderer(batch=batch)
    for forged in (
        changed(decision, candidate_id="invented"),
        changed(decision, evaluation_id="invented"),
        changed(decision, approved_batch_hash="b" * 64),
    ):
        with pytest.raises(ContractViolation):
            renderer.render(forged, selected, (), context)
    with pytest.raises(ContractViolation):
        await MinimumCostTestSelector().select_action(changed(batch, batch_hash="b" * 64), None, state, budget, None)


@pytest.mark.asyncio
async def test_ceiling_rejects_cheaper_candidate_and_question_is_not_zero_cost(relationship):
    context, state, budget, packages = boundary(relationship, 47)
    policy = changed(context.economic.cost_policy, ceiling=m.Money(amount=Decimal("410000")))
    ec = changed(context.economic, cost_policy=policy)
    context = changed(context, economic=changed(ec, fingerprint=economic_fingerprint(ec)))
    g = SuppliedCandidateGenerator(packages=packages)
    offers = g.generate_candidates(intent(context), context, state, budget).candidates
    question = g.generate_candidates(intent(context, True), context, state, budget).candidates
    batch = OfficialEconomicEvaluator(oracle=OfficialArithmetic()).evaluate_candidates(offers + question, context)
    d = await MinimumCostTestSelector().select_action(batch, None, state, budget, None)
    chosen = next(i for i in batch.items if i.candidate.candidate_id == d.candidate_id)
    assert chosen.candidate.contents.kind == "offer"
    assert chosen.economic[0].nominal_cost.amount == Decimal("401600")
    assert len([i for i in batch.items if i.disposition == "rejected"]) == 1


def test_generation_bounds_and_unsupported_intents_are_explicit(relationship):
    context, state, budget, packages = boundary(relationship, 47)
    g = SuppliedCandidateGenerator(packages=packages)
    result = g.generate_candidates(intent(context), context, state, changed(budget, candidate_limit=1))
    assert not result.candidates and not result.search_complete and result.rejections
    with pytest.raises(ValueError):
        SuppliedCandidateGenerator(packages=(packages[0], packages[0]))


@pytest.mark.asyncio
async def test_email_body_is_reconstructed_from_the_approved_package(relationship):
    context, state, budget, packages = boundary(relationship, 43)
    _, _, _, selected, action, _ = await select(context, state, budget, packages)
    price = next(str(binding.value) for binding in packages[0].bindings if binding.field == "unit_price")
    assert price in action.payload.body
    assert "Guten Tag," in action.payload.body and "Kind regards," in action.payload.body
    tampered = action.model_copy(update={
        "payload": action.payload.model_copy(update={"body": action.payload.body.replace(price, "999.99")}),
        "render_hash": "0" * 64,
    })
    tampered = tampered.model_copy(update={"render_hash": render_hash(tampered)})
    validator = FinalActionValidator(evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=Clock())
    assert validator.validate_action(tampered, context, state, budget).kind == "invalid"


@pytest.mark.asyncio
async def test_alternate_strategy_uses_same_economics_renderer_and_validator(relationship):
    context, state, budget, packages = boundary(relationship, 43)
    _, batch, baseline, _, _, _ = await select(context, state, budget, packages)

    class AlternateTestSelector:
        async def select_action(self, candidates, assessment, state, budget, research):
            selected = next(i for i in candidates.items if i.candidate.contents.packages == (packages[1],))
            return changed(
                baseline,
                candidate_id=selected.candidate.candidate_id,
                evaluation_id=selected.evaluation_id,
                selector_id="alternate-test-v1",
            )

    decision = await AlternateTestSelector().select_action(batch, None, state, budget, None)
    selected = next(i for i in batch.items if i.candidate.candidate_id == decision.candidate_id)
    action = TemplateActionRenderer(batch=batch).render(decision, selected, (), context)
    result = FinalActionValidator(evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=Clock())
    assert result.validate_action(action, context, state, budget).kind == "valid"
    assert decision.selector_id != baseline.selector_id
    assert decision.approved_batch_hash == baseline.approved_batch_hash


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["unknown_rounds", "exhausted_rounds", "unknown_clock", "recipient", "edited_package"]
)
async def test_independent_scope_and_admissibility_controls(relationship, fault):
    context, state, budget, packages = boundary(relationship, 47)
    action = (await select(context, state, budget, packages))[4]
    thread = state.server.threads[0]
    if fault == "unknown_rounds":
        thread = changed(thread, rounds=changed(thread.rounds, confidence="unknown"))
    elif fault == "exhausted_rounds":
        thread = changed(thread, rounds=changed(thread.rounds, server_rounds_used=thread.rounds.limit))
    elif fault == "unknown_clock":
        thread = changed(thread, clock=changed(thread.clock, confidence="unknown"))
    elif fault == "recipient":
        action = changed(action, supplier_id="sup:invented")
    elif fault == "edited_package":
        edited = action.payload.packages[0].model_copy(update={"fingerprint": "b" * 64})
        action = action.model_copy(update={"payload": action.payload.model_copy(update={"packages": (edited,)})})
    state = changed(state, server=changed(state.server, threads=(thread,)))
    action = action.model_copy(update={"render_hash": render_hash(action)})
    result = FinalActionValidator(evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=Clock())
    assert result.validate_action(action, context, state, budget).kind == "invalid"
