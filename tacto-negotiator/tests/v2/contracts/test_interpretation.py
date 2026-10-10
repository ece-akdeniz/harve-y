import copy
import json

import pytest

from tests.v2.fakes import FakeClock, ReplayModelGateway
from tests.v2.support import inputs, require


async def interpret(request, p10, variant_id, mutation=None, failure=None):
    interpreter = require(request, "intelligence.interpreter")
    variant = copy.deepcopy(next(v for v in p10["variants"] if v["id"] == variant_id))
    p10["reply"] = variant["body"]
    p10["model_response"] = variant["model_response"]
    if mutation:
        mutation(p10["model_response"])
    data = inputs(request, p10)
    model = ReplayModelGateway(failure if failure is not None else data.model_result)
    result = await interpreter.GroundedInterpreter(model=model, clock=FakeClock()).interpret(
        data.context, data.conversation, data.previous_assessment, data.budget,
    )
    return result, model, data


@pytest.mark.asyncio
@pytest.mark.parametrize("variant_id", ["delivery", "longer", "shorter", "refusal", "uncertain", "contradiction"])
async def test_assessment_preserves_grounding_and_revision(request, p10, variant_id):
    result, _, data = await interpret(request, p10, variant_id)
    assert result.status == "ok"
    assert result.supplier_id == p10["supplier_id"]
    assert result.snapshot == data.context.snapshot
    assert result.revision == 1
    assert result.parent_assessment_id is None
    assert result.observations
    for observation in result.observations:
        assert observation.citations
        for citation in observation.citations:
            if hasattr(citation, "quote"):
                assert citation.session_id == p10["session_id"]
                assert citation.message_id == p10["message_id"]
                assert p10["reply"][citation.start:citation.end] == citation.quote


@pytest.mark.asyncio
async def test_conditional_constraint_stays_reported_not_case_fixed(request, p10):
    result, _, data = await interpret(request, p10, "delivery")
    constraint = next(c for c in result.reported_constraints if c.dimension == "lead_time_days")
    assert constraint.value == 56
    assert constraint.authority == "supplier_reported"
    assert constraint.condition_observation_refs
    assert any(o.kind == "conditional_offer" for o in result.observations)
    assert data.case.contract_hash == data.context.case.contract_hash
    assert 42 in next(o for o in data.case.options if o.field == "lead_time_days").values


@pytest.mark.asyncio
async def test_uncertainty_does_not_invent_a_discount_or_approval(request, p10):
    result, _, _ = await interpret(request, p10, "uncertain")
    assert {"approval", "discount"} <= set(result.unknowns)
    assert any(u.kind == "approval" and u.blocking for u in result.uncertainties)
    assert all(h.numeric_effect is None for h in result.hypotheses)
    assert all(h.confidence in {"low", "unknown"} for h in result.hypotheses)


@pytest.mark.asyncio
async def test_contradiction_is_retained_not_collapsed_to_certainty(request, p10):
    result, _, _ = await interpret(request, p10, "contradiction")
    assert any(u.kind == "contradiction" and u.blocking for u in result.uncertainties)
    assert any(o.kind == "refusal" for o in result.observations)
    assert "approval" in result.unknowns


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["unknown_message", "wrong_quote", "negative_offset", "foreign_session"])
async def test_invalid_citations_fallback(request, p10, fault):
    def mutate(draft):
        citation = draft["observations"][0]["citations"][0]
        field, value = {
            "unknown_message": ("message_id", "message:foreign"),
            "wrong_quote": ("quote", "not in the reply"), "negative_offset": ("start", -1),
            "foreign_session": ("session_id", "session:foreign"),
        }[fault]
        citation[field] = value

    result, _, _ = await interpret(request, p10, "longer", mutation=mutate)
    assert result.status == "fallback"
    assert all(h.numeric_effect is None for h in result.hypotheses)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [TimeoutError("timeout"), ValueError("malformed transport result")])
async def test_provider_exception_is_explicit_fallback(request, p10, failure):
    result, model, _ = await interpret(request, p10, "longer", failure=failure)
    assert result.status == "fallback"
    assert result.model_call_id is not None
    assert len(model.calls) == 1


@pytest.mark.asyncio
async def test_prompt_injection_cannot_create_binding_action(request, p10):
    result, _, _ = await interpret(request, p10, "injection")
    assert result.status == "fallback"
    assert not hasattr(result, "action")
    assert not hasattr(result, "reservation_cost")


@pytest.mark.asyncio
async def test_model_projection_excludes_private_economics_and_transport_authority(request, p10):
    _, model, _ = await interpret(request, p10, "longer")
    request_dto, budget = model.calls[0]
    projection = request_dto.model_dump(mode="json")
    serialized = json.dumps(projection)
    for forbidden in ("fallback_unit_price", "reservation_cost", "target_price", "LLM_API_KEY", "terminal_score"):
        assert forbidden not in serialized

    def field_names(value):
        if isinstance(value, dict):
            return set(value).union(*(field_names(child) for child in value.values()))
        if isinstance(value, list):
            return set().union(*(field_names(child) for child in value))
        return set()

    assert not field_names(projection) & {
        "buyer", "fallback_price", "alternative", "fallback_risk_pct", "relationship_eur_per_point",
        "sustainable_margin_pct", "price_bounds", "ceiling", "cost_policy", "nominal_cost", "scenario_costs",
    }
    assert budget.max_calls == 1
    assert budget.retry_limit == 0
