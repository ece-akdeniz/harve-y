"""Experimental responses to supplier-proposed packages; no model or network access.

Historical sheets are evidence for counterproposals, NEVER acceptable offer IDs.
Quoted terms do not prove that a counterproposal will be accepted.
"""

import math
import time

from arena_kit.cost import closing_terms, complete_offer, must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import latest, moves_left

from .evaluator import eligible_sheets, nonprice, price_for_cost
from .trades import history


def permitted(case, terms):
    if not isinstance(terms.get("unit_price"), (int, float)) or isinstance(terms["unit_price"], bool):
        return False
    if not math.isfinite(terms["unit_price"]) or terms["unit_price"] <= 0:
        return False
    if any(k in terms and terms[k] != v for k, v in case.get("fixed_terms", {}).items()):
        return False
    return all(k not in terms or terms[k] in options for k, options in case.get("term_options", {}).items())


def package_memory(case, events, standard, supplier=None):
    """Recover packages using only the supplied history prefix and original quote defaults."""
    out = []
    for i, event in enumerate(events):
        if event.get("from") == "buyer":
            continue
        quoted_standard = standard_terms(events[: i + 1])
        for sheet in event.get("term_sheets") or []:
            raw = sheet.get("terms") or {}
            if not permitted(case, raw):
                continue
            terms = complete_offer(case, closing_terms(case, raw, quoted_standard))
            if not permitted(case, terms) or not must_haves_ok(case, terms, standard):
                continue
            cost = total_cost(case, terms, standard, supplier)
            if math.isfinite(cost):
                out.append({"terms": terms, "quoted_cost": cost, "source_sheet": sheet.get("term_sheet_id"),
                            "message_index": i, "requires_reconfirmation": True})
    return sorted(out, key=lambda p: (p["quoted_cost"], -p["message_index"]))


def respond(case, events, proposed, standard, supplier, deadline):
    """One bounded, cost-neutral-or-better counter on a supplier-supported package.

Consider a cheaper historical package, a freshly priced single-field concession, or a
quoted index clause explicitly required for the current contract. Preserve the normal
concession schedule in buyer-cost space; do not assume a lower nominal price is savings.
    """
    ours, tried, switches = history(case, events)
    if (not ours or switches >= 2 or moves_left(case, events) < 3 or deadline - time.time() < 20
            or supplier or latest(events).get("status") != "open"):
        return proposed, None
    standing = eligible_sheets(case, events, supplier)
    if not standing:
        return proposed, None
    standing_c, _, standing_t = standing[0]
    target = min(total_cost(case, proposed, standard), standing_c)
    current = latest(events)
    current_index = max(i for i, m in enumerate(events) if m is current)
    body = current.get("body", "").lower()
    for candidate in package_memory(case, events, standard):
        quoted = candidate["terms"]
        shape = nonprice(case, quoted)
        if shape == nonprice(case, proposed) or shape in tried:
            continue
        fresh = candidate["message_index"] == current_index
        diffs = [k for k in shape if shape[k] != closing_terms(case, standing_t, standard).get(k)]
        priced_exchange = fresh and len(diffs) == 1 and quoted["unit_price"] < standing_t["unit_price"]
        required_clause = (fresh and "index_clause" in shape and shape["index_clause"] is not None
                           and proposed.get("index_clause") is None
                           and quoted.get("contract_months") == proposed.get("contract_months")
                           and any(s in body for s in ("must include", "clause is mandatory",
                                                       "cannot offer a fixed price")))
        if candidate["quoted_cost"] >= standing_c - 0.01 and not priced_exchange and not required_clause:
            continue
        price = min(quoted["unit_price"], math.floor(price_for_cost(case, quoted, target, standard) * 100) / 100)
        trial = {**quoted, "unit_price": price}
        if (not permitted(case, trial) or not must_haves_ok(case, trial, standard)
                or total_cost(case, trial, standard) > target + 0.01):
            continue
        return trial, {**candidate, "target_cost": target, "proposed_cost": total_cost(case, trial, standard),
                       "reason": "supplier-supported package; counterproposal, not acceptance"}
    return proposed, None
