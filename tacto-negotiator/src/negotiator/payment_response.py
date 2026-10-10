"""Respond to repeated quoted payment terms with a cost-compensated primary offer."""

import math

from arena_kit.cost import must_haves_ok, total_cost

from .evaluator import price_for_cost


def payment_response(case, events, terms, standard=None, supplier=None):
    """Two consecutive supplier counteroffers must repeat the same faster payment option.

    Use only explicit primary term-sheet fields, never prose or inferred defaults. Preserve
    the scheduled offer's complete buyer cost, rounded conservatively and checked again.
    """
    current = terms.get("payment_days")
    options = (case.get("term_options") or {}).get("payment_days") or []
    if "payment_days" not in case["negotiable"] or current is None or supplier:
        return terms  # The baseline's inverse price search assumes monotonic costs.
    replies, waiting = [], False
    for event in events[-64:]:
        if event.get("from") == "buyer":
            waiting = bool(event.get("term_sheets"))
        elif waiting:
            sheets = event.get("term_sheets") or []
            quoted = (sheets[0].get("terms") or {}).get("payment_days") if sheets else None
            replies.append(quoted if event.get("status") == "open" else None)
            waiting = False
    if len(replies) < 2 or replies[-1] != replies[-2]:
        return terms
    preferred = replies[-1]
    if preferred not in options or type(preferred) not in (int, float) or preferred >= current:
        return terms
    budget = total_cost(case, terms, standard)
    trial = {**terms, "payment_days": preferred}
    if not math.isfinite(budget) or not must_haves_ok(case, trial, standard):
        return terms
    raw_price = price_for_cost(case, trial, budget, standard)
    if not math.isfinite(raw_price) or raw_price <= 0:
        return terms
    trial["unit_price"] = math.floor(raw_price * 100) / 100
    cost = total_cost(case, trial, standard)
    if trial["unit_price"] <= 0 or not math.isfinite(cost) or cost > budget:
        return terms
    return trial
