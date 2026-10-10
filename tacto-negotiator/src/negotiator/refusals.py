"""Opt-in, one-step response to explicit refusals; never infer a supplier reservation price."""
import math
import time

from arena_kit.cost import must_haves_ok, total_cost
from arena_kit.play import latest, moves_left

from .evaluator import eligible_sheets, nonprice, price_for_cost
from .responses import package_memory, permitted
from .trades import history

MARKER = "We have made one revised price proposal on your quoted package."
PRICE_WORDS = (
    "we cannot accept your proposed price", "we cannot accept that price", "we reject your price",
    "your price is too low", "your proposed price is too low",
)
WITHDRAWAL_WORDS = (
    "the previous package is no longer available", "we cannot offer your proposed package",
)


def adjust(case, events, proposed, standard, supplier, deadline, cap_c=None):
    """One halfway concession in complete-cost space, or a fresh-package withdrawal response.

Halfway is an uncalibrated experimental heuristic, not an estimated acceptance threshold.
The buyer-visible marker plus package history prevents repeated acceleration after restart.
    """
    if supplier or latest(events).get("status") != "open":
        return proposed, None
    current = latest(events)
    index = next((i for i in range(len(events) - 1, -1, -1) if events[i] is current), None)
    if index is None or index == 0 or events[index - 1].get("from") != "buyer":
        return proposed, None
    ours, _, switches = history(case, events)
    if not ours:
        return proposed, None
    previous = ours[-1]
    shape = nonprice(case, previous)
    quotes = [p for p in package_memory(case, events, standard) if p["message_index"] == index]
    same = [p for p in quotes if nonprice(case, p["terms"]) == shape]
    body = current.get("body", "").lower()
    withdrawn = not same and any(s in body for s in WITHDRAWAL_WORDS)
    price_refused = bool(same) and any(s in body for s in PRICE_WORDS)
    if not (withdrawn or price_refused):
        return proposed, None
    info = {"kind": "package_unavailable" if withdrawn else "price_refused", "revised": False,
            "source_message": current.get("message_id"), "close": False}
    if moves_left(case, events) < 3 or deadline - time.time() < 20:
        info["close"] = withdrawn
        return proposed, info
    standing = eligible_sheets(case, events)
    if not standing or not quotes:
        info["close"] = True
        return proposed, info
    previous_c = total_cost(case, previous, standard)
    upper = standing[0][0]
    if cap_c is not None:
        upper = min(upper, cap_c - 0.01)
    scheduled_c = total_cost(case, proposed, standard)
    target = max(previous_c, scheduled_c)
    if withdrawn:
        if switches >= 2:
            info["close"] = True
            return proposed, info
        quoted = quotes[0]
        info["reason"] = "withdrawn package: request only newly quoted terms"
    else:
        quoted = same[0]
        if quoted["quoted_cost"] <= previous_c:
            return proposed, info
        already_revised = any(
            m.get("from") == "buyer" and MARKER in m.get("body", "")
            and any(nonprice(case, s.get("terms", {})) == shape for s in m.get("term_sheets") or [])
            for m in events[:index]
        )
        if already_revised:
            return proposed, info
        target = max(target, (previous_c + quoted["quoted_cost"]) / 2)
        info["reason"] = "explicit price refusal: one cost-space halfway concession"
    target = min(target, upper)
    trial = dict(quoted["terms"])
    low_price = math.ceil(price_for_cost(case, trial, previous_c, standard) * 100 - 1e-7) / 100
    high_price = math.floor(price_for_cost(case, trial, target, standard) * 100 + 1e-7) / 100
    if (nonprice(case, trial) == nonprice(case, proposed) and scheduled_c <= upper
            and proposed["unit_price"] > high_price):
        high_price = proposed["unit_price"]
    if low_price > high_price:
        info["close"] = withdrawn or previous_c > upper
        return proposed, info
    trial["unit_price"] = high_price
    cost = total_cost(case, trial, standard)
    if not permitted(case, trial) or not must_haves_ok(case, trial, standard) or cost > upper + 1e-6:
        info["close"] = withdrawn
        return proposed, info
    info.update(revised=True, previous_cost=previous_c, proposed_cost=cost, upper_cost=upper,
                source_sheet=quoted["source_sheet"])
    return trial, info
