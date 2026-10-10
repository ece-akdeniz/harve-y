import copy

import pytest

from tests.v2.fakes import FakeClock, ReplayModelGateway
from tests.v2.support import inputs, require, terms_of


async def decide(request, p10, variant_id):
    interpreter = require(request, "intelligence.interpreter")
    strategy = require(request, "strategy.capacity")
    variant = copy.deepcopy(next(v for v in p10["variants"] if v["id"] == variant_id))
    p10["reply"] = variant["body"]
    p10["model_response"] = variant["model_response"]
    data = inputs(request, p10)
    assessment = await interpreter.GroundedInterpreter(
        model=ReplayModelGateway(data.model_result), clock=FakeClock(),
    ).interpret(
        data.context, data.conversation, data.previous_assessment, data.budget,
    )
    intents = await strategy.GroundedExchangePolicy().propose_strategies(
        data.context, assessment, data.state, data.budget, data.research,
    )
    return assessment, intents, data


@pytest.mark.asyncio
async def test_meaningful_preference_flip_changes_intent_direction(request, p10):
    long_assessment, long_intents, _ = await decide(request, copy.deepcopy(p10), "longer")
    short_assessment, short_intents, _ = await decide(request, copy.deepcopy(p10), "shorter")
    assert any(h.direction == "increase" for h in long_assessment.hypotheses)
    assert any(h.direction == "decrease" for h in short_assessment.hypotheses)
    assert any(i.dimension == "contract_months" and i.direction == "increase" for i in long_intents.intents)
    assert any(i.dimension == "contract_months" and i.direction == "decrease" for i in short_intents.intents)
    assert all(i.evidence_refs or i.observation_refs for i in long_intents.intents if i.kind == "exchange")


@pytest.mark.asyncio
async def test_irrelevant_greeting_changes_neither_strategy_nor_package(request, p10):
    _, original, original_data = await decide(request, copy.deepcopy(p10), "longer")
    edited = copy.deepcopy(p10)
    variant = next(v for v in edited["variants"] if v["id"] == "longer")
    variant["body"] += " Hello and have a pleasant day!"
    # Original spans remain valid because the greeting is appended.
    _, greeting, greeting_data = await decide(request, edited, "longer")
    def signature(batch):
        return [(i.kind, i.dimension, i.direction) for i in batch.intents]
    assert signature(original) == signature(greeting)
    factory = require(request, "factory")
    services = factory.build_decision_services(
        config=original_data.config, model=ReplayModelGateway(original_data.model_result),
    )
    first = await services.evaluate_and_select(original, original_data)
    second = await services.evaluate_and_select(greeting, greeting_data)
    assert first.candidate.contents.packages == second.candidate.contents.packages
    assert first.economic == second.economic


@pytest.mark.asyncio
async def test_refusal_suppresses_exchange_without_becoming_case_constraint(request, p10):
    _, intents, data = await decide(request, p10, "refusal")
    assert not any(i.dimension == "contract_months" and i.direction == "increase" for i in intents.intents)
    assert 36 in next(o for o in data.case.options if o.field == "contract_months").values


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["uncertain", "contradiction"])
async def test_approval_uncertainty_chooses_clarification(request, p10, variant):
    _, batch, _ = await decide(request, p10, variant)
    assert any(i.kind == "clarify" and i.question_id for i in batch.intents)


@pytest.mark.asyncio
async def test_grounded_preference_changes_selected_package_when_cost_justifies_it(request, p10):
    factory = require(request, "factory")
    # The fixed candidate prices are synthetic controlled supplier surfaces, not learned values.
    p10["controlled_candidates"] = [p10["packages"][0], p10["packages"][2]]
    data = inputs(request, p10)
    services = factory.build_decision_services(config=data.config, model=ReplayModelGateway(data.model_result))
    _, long_intents, _ = await decide(request, copy.deepcopy(p10), "longer")
    _, short_intents, _ = await decide(request, copy.deepcopy(p10), "shorter")
    long = await services.evaluate_and_select(long_intents, data)
    short = await services.evaluate_and_select(short_intents, data)
    assert terms_of(long.candidate.contents.packages[0])["contract_months"] == 36
    assert terms_of(short.candidate.contents.packages[0])["contract_months"] == 24
    assert long.economic[0].nominal_cost.amount < short.economic[0].nominal_cost.amount


@pytest.mark.asyncio
async def test_injection_never_creates_accept_or_disclosure_intent(request, p10):
    _, intents, _ = await decide(request, p10, "injection")
    assert all(i.kind in {"keep", "clarify"} for i in intents.intents)
    assert "reservation_cost" not in intents.model_dump_json()
    assert "offer:foreign" not in intents.model_dump_json()


@pytest.mark.asyncio
async def test_expressed_preference_does_not_override_economic_ceiling(request, p10):
    factory = require(request, "factory")
    p10["controlled_candidates"] = [p10["packages"][0], {
        **p10["packages"][1], "contract_months": 36,
    }]
    _, intents, data = await decide(request, p10, "longer")
    services = factory.build_decision_services(config=data.config, model=ReplayModelGateway(data.model_result))
    selected = await services.evaluate_and_select(intents, data)
    assert terms_of(selected.candidate.contents.packages[0])["contract_months"] == 24
