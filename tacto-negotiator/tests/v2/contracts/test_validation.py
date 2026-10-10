import copy

import pytest

from tests.v2.support import codes, inputs, require

NEGATIVES = [
    ("price_zero", "unit_price", 0, "uncertified_price"),
    ("price_negative", "unit_price", -1, "uncertified_price"),
    ("price_nan", "unit_price", "NaN", "invalid_schema"),
    ("price_fractional_tick", "unit_price", 28.341, "uncertified_price"),
    ("invalid_lead", "lead_time_days", 54, "infeasible"),
    ("invalid_volume", "volume_per_year", 19890, "infeasible"),
    ("wrong_type", "contract_months", True, "invalid_schema"),
    ("unauthorized_fixed_term", "payment_days", 60, "invalid_schema"),
    ("unknown_field", "discount_secret", 1, "invalid_schema"),
]


def validator(request):
    module = require(request, "execution.validation")
    oracle = require(request, "adapters.official").OfficialArithmetic()
    evaluator = require(request, "economics.official").OfficialEconomicEvaluator(oracle=oracle)
    claim_oracle = require(request, "adapters.claims").LegacyClaimOracle()
    verifier = require(request, "evidence.claims").CanonicalClaimVerifier(oracle=claim_oracle)
    return module.FinalActionValidator(evaluator=evaluator, claim_verifier=verifier)


def validate(request, fixture):
    guard = validator(request)
    data = inputs(request, fixture)
    # Raw wire bytes are parsed without snapping; malformed DTOs become typed invalid reports.
    return guard.validate_wire(data.wire_payload, data.context, data.state, data.budget)


def test_complete_valid_offer_gets_certificate_without_payload_changes(request, p10):
    result = validate(request, p10)
    assert result.kind == "valid"
    assert result.action.payload_hash
    data = inputs(request, p10)
    assert result.action.rendered.payload == data.rendered.payload


@pytest.mark.parametrize("name,field,value,issue", NEGATIVES, ids=[row[0] for row in NEGATIVES])
def test_invalid_offer_is_rejected_not_snapped(request, p10, name, field, value, issue):
    original = copy.deepcopy(p10)
    p10["wire_terms"] = {**p10["packages"][0], field: value}
    result = validate(request, p10)
    assert result.kind == "invalid", name
    assert issue in codes(result)
    assert original["packages"][0] == p10["packages"][0]


@pytest.mark.parametrize("fault,issue", [
    ("missing_field", "invalid_schema"), ("mixed_accept_offer", "invalid_schema"),
    ("stale_state", "stale_state"), ("pending_operation", "operation_pending"),
    ("expired_deadline", "deadline_exhausted"), ("wrong_recipient", "scope_mismatch"),
    ("nonstanding_accept", "infeasible"), ("accept_above_alternative", "infeasible"),
    ("private_body", "private_disclosure"), ("internal_claim", "private_disclosure"),
    ("hallucinated_claim", "unsupported_claim"), ("stale_claim", "stale_source"),
    ("subject_301", "invalid_schema"), ("body_8001", "invalid_schema"),
    ("four_sheets", "invalid_schema"), ("refs_21", "invalid_schema"),
    ("attachments_6", "invalid_schema"), ("claims_4", "invalid_schema"),
])
def test_invalid_boundary_action_has_specific_issue(request, p10, fault, issue):
    p10["validation_fault"] = fault
    result = validate(request, p10)
    assert result.kind == "invalid"
    assert issue in codes(result)


@pytest.mark.parametrize("boundary", ["subject_300", "body_8000", "refs_20", "three_sheets", "question"])
def test_official_limits_and_question_positive_cases(request, p10, boundary):
    p10["validation_positive"] = boundary
    assert validate(request, p10).kind == "valid"
