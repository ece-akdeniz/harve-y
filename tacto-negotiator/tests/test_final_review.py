import copy
import time

from test_evaluator import RFQ, msg, ours

from negotiator.agent import PackageAgent
from negotiator.final_review import no_deal_fallback_cost, review
from negotiator.optimizer import alternative_cost
from negotiator.policy import PolicyConfig


def test_review_requires_comparable_outside_option_and_time():
    good = review(100, 90, 110, walk_bound=.25, remaining_s=35)
    assert good["admitted"] and good["break_even_walk_probability"] == .5
    assert good["possible_loss"] == 10 and good["continuation"] == "unpriced"
    assert review(100, 90, float("inf"), walk_bound=.25, remaining_s=35)["reason"] == (
        "no_comparable_executable_alternative")
    assert review(100, 90, 110, walk_bound=.25, remaining_s=20)["reason"] == "insufficient_time"
    assert review(100, 99, 120, walk_bound=.25, remaining_s=35)["reason"] == (
        "risk_bound_exceeds_break_even")


def test_no_deal_scenario_is_case_priced_and_requires_exploratory_loss_envelope():
    case = {"buyer": {"need_per_year": 100, "horizon_years": 2,
                      "fallback_unit_price": 1.0, "fallback_risk_pct": 25}}
    assert no_deal_fallback_cost(case) == 250
    assert no_deal_fallback_cost({"buyer": {"need_per_year": 100}}) is None
    cautious = review(200, 190, float("inf"), walk_bound=.2, remaining_s=40,
                      no_deal_cost=250)
    assert not cautious["admitted"] and cautious["reason"] == "no_comparable_executable_alternative"
    assert cautious["possible_loss"] == 50 and cautious["break_even_walk_probability"] == 1 / 6
    assert cautious["walk_probability"] == "unknown" and not cautious["no_deal_executable"]
    blocked = review(200, 190, float("inf"), walk_bound=.2, remaining_s=40,
                     no_deal_cost=250, exploratory=True, max_loss_fraction=.2)
    assert not blocked["admitted"] and blocked["reason"] == "exploratory_loss_limit"
    admitted = review(200, 190, float("inf"), walk_bound=.2, remaining_s=40,
                      no_deal_cost=250, exploratory=True, max_loss_fraction=.3)
    assert admitted["admitted"] and admitted["reason"] == "exploratory_no_alt_counter"
    assert admitted["decision_basis"] == "explicit_loss_envelope_not_walk_estimate"
    assert not review(200, 190, float("inf"), walk_bound=.2, remaining_s=20,
                      no_deal_cost=250, exploratory=True, max_loss_fraction=.3)["admitted"]


def test_bounded_final_counter_is_single_and_respects_deadline():
    case = copy.deepcopy(RFQ)
    case["suppliers"] = ["sup:J"]
    sid = "sup:J"
    standing = {"unit_price": 19.3, "payment_days": 14, "lead_time_days": 35, "incoterm": "DAP"}
    preferred = {**standing, "payment_days": 60}
    events = [msg("open", ("o:0", standing)), ours({**preferred, "unit_price": 18}),
              msg("final_offer", ("o:1", standing))]
    policy = PolicyConfig(final_offer_risk="bounded_review", final_review_max_walk_probability=.2)
    agent = PackageAgent(policy=policy)
    agent.prev[sid] = {k: v for k, v in preferred.items() if k != "unit_price"}
    agent.trades.deadlines[sid] = time.time() + 40
    result = agent._final_counter(case, {sid: events}, sid, alternative_cost(case))
    assert result and result["message"]["term_sheets"][0]["terms"] == preferred
    assert agent._final_counter(case, {sid: events}, sid, alternative_cost(case)) is None
    late = PackageAgent(policy=policy)
    late.prev[sid] = agent.prev[sid]
    late.trades.deadlines[sid] = time.time() + 19
    assert late._final_counter(case, {sid: events}, sid, alternative_cost(case)) is None


def test_final_review_policy_requires_explicit_probability_bound():
    try:
        PolicyConfig.from_dict({"version": 1, "final_offer_risk": "bounded_review"})
    except ValueError:
        pass
    else:
        raise AssertionError("missing explicit risk bound was admitted")
