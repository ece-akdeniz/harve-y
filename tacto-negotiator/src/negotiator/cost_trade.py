"""One bounded risk-sharing package proposal after price resistance or cost-driver evidence."""
import itertools
import math
import time

from arena_kit.cost import complete_offer, must_haves_ok, total_cost
from arena_kit.play import latest, moves_left

from .evaluator import nonprice, price_for_cost
from .responses import permitted
from .trades import history

MARKER = "We propose this risk-sharing package in exchange for the attached unit price."
SIGNALS = (
    "cost structure", "cost drivers", "raw material costs", "input costs", "pricing flexibility",
    "cannot accept your", "cannot accept that price", "reject your price", "price is too low",
)


def propose(case, events, scheduled, standard, supplier, deadline, cap_c=None):
    if supplier or latest(events).get("status") != "open":
        return scheduled, None
    if moves_left(case, events) < 3 or deadline - time.time() < 20:
        return scheduled, None
    ours, tried, switches = history(case, events)
    if switches >= 2 or any(m.get("from") == "buyer" and MARKER in m.get("body", "") for m in events):
        return scheduled, None
    trigger = next((m for m in reversed(events) if m.get("from") != "buyer"
                    and any(s in m.get("body", "").lower() for s in SIGNALS)), None)
    if trigger is None:
        return scheduled, None
    options = case.get("term_options", {})
    fields = [f for f in ("index_clause", "contract_months") if f in case["negotiable"] and options.get(f)]
    if not fields:
        return scheduled, None
    current_c = total_cost(case, scheduled, standard)
    cap = min(current_c, cap_c - 0.01) if cap_c is not None else current_c
    choices = []
    for values in itertools.product(*(options[f] for f in fields)):
        candidate = {**scheduled, **dict(zip(fields, values, strict=True))}
        shape = nonprice(case, candidate)
        if shape == nonprice(case, scheduled) or shape in tried:
            continue
        if (candidate.get("index_clause") is None
                and candidate.get("contract_months") == scheduled.get("contract_months")):
            continue  # Removing risk sharing is not a new concession to cost pressure.
        if not permitted(case, candidate) or not must_haves_ok(case, candidate, standard):
            continue
        choices.append((total_cost(case, candidate, standard), candidate))
    if not choices:
        return scheduled, None
    # Compare packages at one price first. Inverse-pricing all options first would hide their differences.
    before, selected = min(choices, key=lambda row: row[0])
    selected = dict(selected)
    selected["unit_price"] = min(scheduled["unit_price"],
                                  math.floor(price_for_cost(case, selected, cap, standard) * 100) / 100)
    after = total_cost(case, selected, standard)
    if not permitted(case, selected) or not must_haves_ok(case, selected, standard) or after > cap + 0.01:
        return scheduled, None
    return complete_offer(case, selected), {
        "source_message": trigger.get("message_id"), "considered": len(choices),
        "scheduled": scheduled, "scheduled_cost": current_c, "same_price_package_cost": before,
        "selected": selected, "selected_cost": after,
        "reason": "lowest-cost permitted risk-sharing switch, repriced to preserve buyer cost",
    }
