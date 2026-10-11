"""Final-offer counter review with explicit executable and exploratory outcomes."""

import math


def no_deal_fallback_cost(case):
    """Case-priced cost of covering the whole need after no deal, not an executable quote.

    The published buyer cost function prices uncovered need at the case's fallback
    unit price plus its fallback risk. This is a scenario, not a walk probability.
    """
    buyer = case.get("buyer") or {}
    values = [buyer.get(k) for k in ("need_per_year", "horizon_years", "fallback_unit_price")]
    risk = buyer.get("fallback_risk_pct", 0)
    if (any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values)
            or type(risk) not in (int, float) or not math.isfinite(risk) or risk < 0):
        return None
    cost = math.prod(values) * (1 + risk / 100)
    return cost if math.isfinite(cost) and cost > 0 else None


def review(standing_cost, counter_cost, outside_cost, *, walk_bound, remaining_s,
           no_deal_cost=None, exploratory=False, max_loss_fraction=0.0):
    """Return a binary walk/accept screen; continuation is reported but unpriced.

    An absent executable alternative stays absent. Exploratory mode may separately
    use the case-priced no-deal scenario within an explicit loss envelope.
    """
    result = {"admitted": False, "reason": None, "standing_cost": standing_cost,
              "counter_cost": counter_cost,
              "outside_cost": outside_cost if type(outside_cost) in (int, float)
              and math.isfinite(outside_cost) else None,
              "remaining_s": remaining_s, "walk_probability_bound": walk_bound,
              "continuation": "unpriced", "approximation": "binary accept_or_walk"}
    if remaining_s is None or remaining_s <= 20:
        result["reason"] = "insufficient_time"
        return result
    def valid(x):
        return type(x) in (int, float) and math.isfinite(x) and x > 0
    if not valid(standing_cost) or not valid(counter_cost):
        result["reason"] = "invalid_cost"
        return result
    executable = valid(outside_cost)
    scenario = not executable and valid(no_deal_cost)
    if not executable and not scenario:
        result["reason"] = "no_comparable_executable_alternative"
        return result
    loss_cost = outside_cost if executable else no_deal_cost
    gain, loss = standing_cost - counter_cost, max(0.0, loss_cost - standing_cost)
    result.update(gain=gain, possible_loss=loss)
    if scenario:
        result.update(no_deal_scenario_cost=no_deal_cost, no_deal_scenario_source="case_buyer_fallback",
                      no_deal_executable=False, walk_probability="unknown",
                      walk_probability_bound=None)
    if gain <= 1e-6:
        result["reason"] = "no_gain"
        return result
    threshold = gain / (gain + loss)
    result["break_even_walk_probability"] = threshold
    result["sensitivity"] = {str(p): (1 - p) * gain - p * loss
                             for p in (0.1, walk_bound, 0.5)}
    if scenario:
        result["possible_loss_fraction"] = loss / standing_cost
        if not exploratory:
            result["reason"] = "no_comparable_executable_alternative"
            return result
        if (type(max_loss_fraction) not in (int, float) or not math.isfinite(max_loss_fraction)
                or not 0 < max_loss_fraction <= 1
                or result["possible_loss_fraction"] > max_loss_fraction):
            result["reason"] = "exploratory_loss_limit"
            return result
        result.update(admitted=True, reason="exploratory_no_alt_counter",
                      decision_basis="explicit_loss_envelope_not_walk_estimate",
                      max_loss_fraction=max_loss_fraction)
        return result
    if not 0 < walk_bound <= 0.5 or walk_bound >= threshold:
        result["reason"] = "risk_bound_exceeds_break_even"
        return result
    result.update(admitted=True, reason="bounded_counter")
    return result
