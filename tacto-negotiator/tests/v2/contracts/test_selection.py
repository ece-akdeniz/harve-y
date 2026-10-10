import pytest

from tests.v2.support import inputs, require


@pytest.mark.asyncio
async def test_deterministic_selector_chooses_only_approved_batch_member(request, p10):
    selector = require(request, "strategy.selection").DeterministicSelector()
    data = inputs(request, p10)
    decision = await selector.select_action(
        data.evaluation_batch, data.assessment, data.state, data.budget, data.research,
    )
    chosen = next(item for item in data.evaluation_batch.items if item.candidate.candidate_id == decision.candidate_id)
    assert chosen.disposition == "approved"
    assert decision.evaluation_id == chosen.evaluation_id
    assert decision.approved_batch_hash == data.evaluation_batch.batch_hash
    assert decision.snapshot == data.context.snapshot


@pytest.mark.asyncio
async def test_selector_cannot_treat_question_as_zero_cost_offer(request, p10):
    selector = require(request, "strategy.selection").DeterministicSelector()
    p10["selection_fixture"] = "offer_and_unneeded_question"
    data = inputs(request, p10)
    decision = await selector.select_action(
        data.evaluation_batch, data.assessment, data.state, data.budget, data.research,
    )
    chosen = next(item for item in data.evaluation_batch.items if item.candidate.candidate_id == decision.candidate_id)
    assert chosen.candidate.contents.kind == "offer"


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["invalid_id", "edited_cost", "malformed", "timeout"])
async def test_optional_model_selector_falls_back_to_certified_member(request, p10, fault):
    module = require(request, "strategy.selection")
    p10["selection_fixture"] = fault
    data = inputs(request, p10)
    from tests.v2.fakes import FakeClock, ReplayModelGateway

    selector = module.BoundedModelSelector(model=ReplayModelGateway(data.selector_model_result), clock=FakeClock())
    result = await selector.select_action(
        data.evaluation_batch, data.assessment, data.state, data.budget, data.research,
    )
    assert result.fallback_code is not None
    assert result.candidate_id in {item.candidate.candidate_id for item in data.evaluation_batch.items
                                   if item.disposition == "approved"}
    assert result.approved_batch_hash == data.evaluation_batch.batch_hash
