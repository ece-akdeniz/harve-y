"""Validated, deterministic complete-package economics; no model-generated numbers."""

import math

from arena_kit.cost import closing_terms, cost_breakdown, must_haves_ok, total_cost


class InfeasiblePackage(ValueError):
    pass


def evaluate(case, terms, standard=None, supplier=None):
    resolved = closing_terms(case, terms, standard)
    price = resolved.get("unit_price")
    if type(price) not in (int, float) or not math.isfinite(price) or price <= 0:
        raise InfeasiblePackage("price must be positive and finite")
    if any(field in terms and terms[field] != value for field, value in case.get("fixed_terms", {}).items()):
        raise InfeasiblePackage("fixed terms cannot be changed")
    for field, options in case.get("term_options", {}).items():
        if field in case["negotiable"] and options and resolved.get(field) not in options:
            raise InfeasiblePackage(f"unsupported {field}")
    if not must_haves_ok(case, terms, standard):
        raise InfeasiblePackage("must-have violation")
    try:
        parts = cost_breakdown(case, terms, standard, supplier)
    except (ZeroDivisionError, KeyError, TypeError, ValueError) as exc:
        raise InfeasiblePackage("incomplete or invalid economics") from exc
    if not all(math.isfinite(v) for v in parts.values()):
        raise InfeasiblePackage("non-finite cost")
    buyer = case["buyer"]
    years = min(resolved["contract_months"] / 12 if resolved["contract_months"] else 1,
                buyer["horizon_years"])
    covered = min(resolved["volume_per_year"], buyer["need_per_year"]) * years
    need = buyer["need_per_year"] * buyer["horizon_years"]
    return {"terms": resolved, "cost": round(sum(parts.values()), 2), "components": parts,
            "covered_units": covered, "uncovered_units": need - covered,
            "horizon_years": buyer["horizon_years"], "supplier_estimate": supplier is not None}


def price_for_budget(case, terms, budget, standard=None, supplier=None, hi=None):
    """Highest checked feasible price in a bounded search, not a global-optimum claim.

    With relationship estimates search a grid first: their penalty is not monotonic.
    Refine the boundary above the highest feasible sample and recheck after rounding.
    """
    if not math.isfinite(budget):
        raise InfeasiblePackage("finite cost budget required")
    ceiling = min(1e7, hi or max(1.0, (terms.get("unit_price") or 1.0) * 4))

    def cost(price):
        try:
            return total_cost(case, {**terms, "unit_price": price}, standard, supplier)
        except (ZeroDivisionError, ValueError, OverflowError):
            return math.inf

    if not supplier and cost(ceiling) <= cost(0.01):
        reference = round(terms.get("unit_price") or 0.01, 2)
        if cost(reference) > budget:
            raise InfeasiblePackage("no cost-neutral reference price on a flat/decreasing cost surface")
        evaluate(case, {**terms, "unit_price": reference}, standard)
        return reference
    while cost(ceiling) <= budget and ceiling < 1e7:
        ceiling = min(1e7, ceiling * 2)
    if supplier:
        samples = {0.01, ceiling, max(0.01, min(ceiling, terms.get("unit_price") or 0.01))}
        samples.update(0.01 + (ceiling - 0.01) * i / 512 for i in range(513))
        feasible = [p for p in samples if cost(p) <= budget]
        if not feasible:
            raise InfeasiblePackage("no feasible sampled price under relationship-cost budget")
        lo = max(feasible)
        upper = min((p for p in samples if p > lo), default=lo)
    else:
        lo, upper = 0.01, ceiling
        if cost(lo) > budget:
            raise InfeasiblePackage("non-price costs exceed budget")
        # Affine fixed-package cost can be flat/decreasing (e.g. effective date beyond horizon).
        if cost(ceiling) <= budget:
            lo = upper
    for _ in range(50):
        mid = (lo + upper) / 2
        if cost(mid) <= budget:
            lo = mid
        else:
            upper = mid
    price = math.floor(lo * 100) / 100
    # Rounding down can raise relationship cost; do not assume it preserves feasibility.
    checked = [p for p in {price, round(price + 0.01, 2)}
               if 0 < p <= ceiling and cost(p) <= budget]
    if not checked:
        raise InfeasiblePackage("no cent-rounded price meets budget")
    answer = max(checked)
    evaluate(case, {**terms, "unit_price": answer}, standard, supplier)
    return answer
