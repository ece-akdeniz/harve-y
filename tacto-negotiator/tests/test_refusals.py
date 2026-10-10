"""Local refusal decisions use real case arithmetic, never hosted negotiations."""

import copy
import json
import time
from pathlib import Path

import pytest
from arena_kit.cost import closing_terms, complete_offer, must_haves_ok, total_cost

from negotiator.evaluator import nonprice
from negotiator.policy import PolicyConfig
from negotiator.refusals import MARKER, adjust
from negotiator.responses import permitted

CASES = {c["case_id"]: c for c in json.loads(
    (Path(__file__).parent / "fixtures/practice_cases.json").read_text()
)}


def sheet(terms, ident="offer:current"):
    return {"term_sheet_id": ident, "terms": terms}


def refusal_prefix():
    case = copy.deepcopy(CASES["case:P02"])
    prior = complete_offer(case, {"unit_price": 340, "payment_days": 30, "index_clause": None})
    quote = {**prior, "unit_price": 370}
    scheduled = {**prior, "unit_price": 345}
    events = [
        {"from": "supplier", "status": "open", "term_sheets": [sheet(quote, "offer:opening")]},
        {"from": "buyer", "body": "We offer this package.", "term_sheets": [{"terms": prior}]},
        {"from": "supplier", "status": "open", "body": "We cannot accept your proposed price.",
         "term_sheets": [sheet(quote)]},
    ]
    return case, events, scheduled


def withdrawal_prefix():
    case = copy.deepcopy(CASES["case:P11"])
    prior = complete_offer(case, {"unit_price": 45, "ppm_commitment": 1500,
                                 "chargeback_eur_per_complaint": 150})
    quote = {**prior, "unit_price": 48, "chargeback_eur_per_complaint": 500}
    scheduled = {**prior, "unit_price": 45.5}
    events = [
        {"from": "supplier", "status": "open", "term_sheets": [
            sheet(quote, "offer:opening"), sheet({**prior, "unit_price": 46.5}, "offer:old-alternative")]},
        {"from": "buyer", "body": "We offer this package.", "term_sheets": [{"terms": prior}]},
        {"from": "supplier", "status": "open",
         "body": "The previous package is no longer available.", "term_sheets": [sheet(quote)]},
    ]
    return case, events, scheduled


def decide(case, events, proposed, **kwargs):
    return adjust(case, events, proposed, {}, kwargs.pop("supplier", None),
                  kwargs.pop("deadline", time.time() + 60), **kwargs)


def test_price_refusal_uses_one_cost_midpoint_on_same_package():
    case, events, scheduled = refusal_prefix()
    terms, info = decide(case, events, scheduled)
    assert info and info["revised"]
    assert nonprice(case, terms) == nonprice(case, scheduled)
    assert terms["unit_price"] == pytest.approx(355, abs=0.01)
    assert total_cost(case, terms) >= total_cost(case, scheduled)
    assert total_cost(case, terms) <= total_cost(case, events[-1]["term_sheets"][0]["terms"])
    assert permitted(case, terms) and must_haves_ok(case, terms)


def test_midpoint_never_undoes_the_normal_scheduled_concession():
    case, events, scheduled = refusal_prefix()
    scheduled["unit_price"] = 360
    terms, _ = decide(case, events, scheduled)
    assert total_cost(case, terms) >= total_cost(case, scheduled) - 0.01


def test_prior_marker_reconstructs_used_midpoint_without_mutable_agent_state():
    case, events, scheduled = refusal_prefix()
    events[1]["body"] += " " + MARKER
    first = decide(case, events, scheduled)
    second = decide(case, copy.deepcopy(events), copy.deepcopy(scheduled))
    assert first == second
    terms, info = first
    assert terms == scheduled
    assert info and info["kind"] == "price_refused" and info["revised"] is False


@pytest.mark.parametrize("body", [
    "Thank you for your offer; please review our quote.",
    "We cannot offer the alternative package you mentioned earlier.",
    "The other option is no longer available.",
])
def test_unknown_or_other_option_text_does_not_trigger_refusal(body):
    case, events, scheduled = refusal_prefix()
    events[-1]["body"] = body
    assert decide(case, events, scheduled) == (scheduled, None)


@pytest.mark.parametrize("status", ["final_offer", "walked_away"])
def test_final_or_ended_status_keeps_existing_behavior(status):
    case, events, scheduled = refusal_prefix()
    events[-1]["status"] = status
    assert decide(case, events, scheduled)[0] == scheduled


@pytest.mark.parametrize("seconds", [0, 19])
def test_near_deadline_does_not_adapt(seconds):
    case, events, scheduled = refusal_prefix()
    assert decide(case, events, scheduled, deadline=time.time() + seconds)[0] == scheduled


def test_relationship_estimates_disable_cost_inverse_refusal_policy():
    case, events, scheduled = refusal_prefix()
    assert decide(case, events, scheduled, supplier={"uncertain": True})[0] == scheduled


def test_rival_cost_cap_survives_midpoint_concession():
    case, events, scheduled = refusal_prefix()
    cap = total_cost(case, {**scheduled, "unit_price": 350})
    terms, _ = decide(case, events, scheduled, cap_c=cap)
    assert total_cost(case, terms) <= cap - 0.01
    assert total_cost(case, terms) >= total_cost(case, scheduled) - 0.01


def test_refusal_must_immediately_follow_our_proposal():
    case, events, scheduled = refusal_prefix()
    events.insert(-1, {"from": "supplier", "status": "open", "body": "Additional information."})
    assert decide(case, events, scheduled) == (scheduled, None)


def test_marker_on_a_different_package_does_not_consume_current_reprice():
    case, events, scheduled = refusal_prefix()
    old = {**scheduled, "payment_days": 90}
    events[:0] = [{"from": "buyer", "body": MARKER, "term_sheets": [{"terms": old}]}]
    terms, info = decide(case, events, scheduled)
    assert info and info["revised"]
    assert terms["unit_price"] == pytest.approx(355, abs=0.01)


def test_withdrawal_uses_only_fresh_quoted_shape_with_equivalent_cost():
    case, events, scheduled = withdrawal_prefix()
    terms, info = decide(case, events, scheduled)
    assert info and info["revised"]
    assert terms["chargeback_eur_per_complaint"] == 500
    assert closing_terms(case, terms)["payment_days"] == 60
    assert nonprice(case, terms) == nonprice(case, events[-1]["term_sheets"][0]["terms"])
    assert total_cost(case, terms) <= total_cost(case, scheduled) + 0.01
    # Cent rounding may reduce cost by less than one unit-price cent over the annual volume.
    assert total_cost(case, terms) >= total_cost(case, scheduled) - case["buyer"]["need_per_year"] * 0.01
    assert permitted(case, terms) and must_haves_ok(case, terms)


def test_claimed_withdrawal_with_same_package_still_quoted_does_not_switch():
    case, events, scheduled = withdrawal_prefix()
    events[-1]["term_sheets"].append(sheet({**scheduled, "unit_price": 46.5}, "offer:still-current"))
    assert decide(case, events, scheduled)[0] == scheduled


def test_withdrawal_without_a_valid_fresh_package_never_revives_history():
    case, events, scheduled = withdrawal_prefix()
    events[-1]["term_sheets"][0]["terms"]["payment_days"] = 30
    assert decide(case, events, scheduled)[0] == scheduled


@pytest.mark.parametrize("constraint", ["moves", "switches"])
def test_withdrawal_respects_reconstructed_exploration_budget(constraint):
    case, events, scheduled = withdrawal_prefix()
    if constraint == "moves":
        case["round_limit"] = 3  # One sent buyer message leaves fewer than three moves.
    else:
        prior = events[1]["term_sheets"][0]["terms"]
        events[1:1] = [
            {"from": "buyer", "term_sheets": [{"terms": {**prior, "chargeback_eur_per_complaint": 500}}]},
            copy.deepcopy(events[0]),
            {"from": "buyer", "term_sheets": [{"terms": {**prior, "chargeback_eur_per_complaint": 300}}]},
            copy.deepcopy(events[0]),
        ]
    assert decide(case, events, scheduled)[0] == scheduled


def test_refusal_configuration_defaults_off_and_validates_types(tmp_path):
    assert PolicyConfig().refusal_types == ()
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"version": 1, "refusal_types": ["quality", "price_increase"]}))
    assert set(PolicyConfig.load(path).refusal_types) == {"quality", "price_increase"}
    for invalid in ("quality", ["P11"], [True]):
        path.write_text(json.dumps({"version": 1, "refusal_types": invalid}))
        with pytest.raises(ValueError):
            PolicyConfig.load(path)
