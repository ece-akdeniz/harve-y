"""Shared closing evaluator: the one check behind every accept and walk-away.

Normal decisions, `agreed`, final offers, "no moves left" and the deadline fallback all close
through `close_decision`. A sheet is eligible when it is in the supplier's latest message of a
live thread, has a price and keeps the must-haves with the supplier's standard terms resolved;
eligible sheets are ranked by complete C (`arena_kit.cost.total_cost`) including the supplier
estimate, if any, and only a sheet below the alternative's C may be accepted.
"""

import math

from arena_kit.cost import closing_terms, must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import ENDED, latest, live_threads

from .optimizer import alternative_cost


def supplier_for(estimates, supplier_id, standard):
    """The estimate for `supplier_id` in the shape `total_cost(..., supplier=...)` takes, with the
    quote PDF's standard terms filled in when the estimate has none; None without an estimate."""
    est = (estimates or {}).get(supplier_id)
    if not est:
        return None
    # The current quote is authoritative for fields it establishes; estimate/master
    # defaults remain useful only for fields omitted by this quote.
    effective = {**(est.get("standard") or {}), **(standard or {})}
    return {**est, "standard": effective}


def eligible_sheets(case, events, supplier=None, alternatives=False):
    """[(C, term_sheet_id, terms)] of the supplier's latest message, cheapest first: priced,
    must-haves kept with standard terms resolved, thread not ended. Only the first sheet is the
    standing offer the arena lets us accept ("offer:...-a" alternatives give HTTP 422); with
    `alternatives` the other sheets are included as packages to counter with."""
    if not events:
        return []
    msg = latest(events)
    if msg.get("status") in ENDED:
        return []
    std = standard_terms(events)
    out = []
    sheets = msg.get("term_sheets") or []
    for sheet in sheets if alternatives else sheets[:1]:
        sheet_id, terms = sheet.get("term_sheet_id"), sheet.get("terms") or {}
        if not sheet_id or closing_terms(case, terms, std).get("unit_price") is None:
            continue
        if not must_haves_ok(case, terms, std):
            continue
        c = total_cost(case, terms, std, supplier)
        if math.isfinite(c):
            out.append((c, sheet_id, terms))
    return sorted(out, key=lambda x: (x[0], x[1]))


def best_close(case, threads, estimates=None):
    """(C, supplier_id, term_sheet_id, terms) of the cheapest eligible sheet over all live threads
    that beats the alternative, else None."""
    c_alt = alternative_cost(case)
    best = None
    for sid in live_threads(threads):
        sup = supplier_for(estimates, sid, standard_terms(threads[sid]))
        for c, sheet_id, terms in eligible_sheets(case, threads[sid], sup)[:1]:
            if c < c_alt and (best is None or (c, sid) < best[:2]):
                best = (c, sid, sheet_id, terms)
    return best


def close_decision(case, threads, estimates=None, reason=""):
    """Accept the best eligible sheet across live threads if it beats the alternative, else walk
    away. `estimates`: {supplier_id: supplier estimate for total_cost}. `reason` is for callers'
    traces only."""
    best = best_close(case, threads, estimates)
    if best:
        _, sid, sheet_id, _ = best
        return {"supplier_id": sid, "message": {"action": {"type": "accept", "term_sheet_id": sheet_id}}}
    live = live_threads(threads) or list(threads)
    return {"supplier_id": live[0], "message": {"action": {"type": "walk_away"}}}


def nonprice(case, terms):
    """The negotiable non-price fields of a term sheet."""
    return {k: terms.get(k) for k in case["negotiable"] if k != "unit_price"}


def same_package(case, a, b, standard=None):
    """True when two sheets close on the same negotiable non-price terms."""
    ta, tb = closing_terms(case, a, standard), closing_terms(case, b, standard)
    return all(ta.get(k) == tb.get(k) for k in case["negotiable"] if k != "unit_price")


def price_for_cost(case, terms, target_c, standard=None, supplier=None, hi=None):
    """Find a positive-price cost root, preferring the branch nearest the reference price.

    Relationship costs can be nonmonotonic in price. Those cases use a bounded scan to find
    feasible brackets; absence of a bracket is reported as ``None`` rather than a guessed zero.
    """
    reference = terms.get("unit_price")
    if not math.isfinite(float(target_c)) or target_c <= 0:
        return None
    upper = float(hi or max(1.0, (reference or 1.0) * 4))
    upper = min(max(upper, 0.01), 1e7)

    def cost(price):
        return total_cost(case, {**terms, "unit_price": price}, standard, supplier)

    # Grow a finite search interval while cost at the upper end remains below target.
    while upper < 1e7 and cost(upper) < target_c:
        upper = min(upper * 2, 1e7)
    lower = 0.01
    if supplier:
        # A bounded grid detects multiple roots and local reversals. Refine every bracket,
        # then choose the root nearest the caller's reference branch.
        count = 10000
        step = (upper - lower) / count
        points = [(lower + i * step, cost(lower + i * step)) for i in range(count + 1)]
        roots = []
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if not (math.isfinite(y0) and math.isfinite(y1)) or (y0 - target_c) * (y1 - target_c) > 0:
                continue
            left, right = x0, x1
            increasing = y1 >= y0
            for _ in range(40):
                mid = (left + right) / 2
                if (cost(mid) < target_c) == increasing:
                    left = mid
                else:
                    right = mid
            candidate = (left + right) / 2
            if candidate > 0 and abs(cost(candidate) - target_c) <= max(0.01, abs(target_c) * 1e-8):
                roots.append(candidate)
        return min(roots, key=lambda p: abs(p - (reference or p))) if roots else None

    low_cost = cost(lower)
    high_cost = cost(upper)
    if not (math.isfinite(low_cost) and math.isfinite(high_cost)) or low_cost > target_c or high_cost < target_c:
        return None
    lo, hi = lower, upper
    for _ in range(60):
        mid = (lo + hi) / 2
        if cost(mid) < target_c:
            lo = mid
        else:
            hi = mid
    candidate = (lo + hi) / 2
    return candidate if candidate > 0 and abs(cost(candidate) - target_c) <= max(0.01, abs(target_c) * 1e-8) else None


def revealed_deltas(case, sheets, standard=None):
    """Price differences the supplier reveals between two of its sheets that differ in exactly one
    non-price field: [(field, value_a, value_b, price_b - price_a)]. Sheets differing in several
    fields reveal only a combined package difference and are not listed."""
    out = []
    priced = [s.get("terms") or {} for s in sheets if (s.get("terms") or {}).get("unit_price") is not None]
    for i, a in enumerate(priced):
        for b in priced[i + 1 :]:
            ta, tb = closing_terms(case, a, standard), closing_terms(case, b, standard)
            diff = [k for k in case["negotiable"] if k != "unit_price" and ta.get(k) != tb.get(k)]
            if len(diff) == 1:
                f = diff[0]
                out.append((f, ta.get(f), tb.get(f), round(b["unit_price"] - a["unit_price"], 2)))
    return out
