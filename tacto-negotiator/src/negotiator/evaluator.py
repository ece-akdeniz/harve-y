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
    return {**est, "standard": est.get("standard") or standard or {}}


def eligible_sheets(case, events, supplier=None):
    """[(C, term_sheet_id, terms)] of the supplier's latest message, cheapest first: priced,
    must-haves kept with standard terms resolved, thread not ended."""
    if not events:
        return []
    msg = latest(events)
    if msg.get("status") in ENDED:
        return []
    std = standard_terms(events)
    out = []
    for sheet in msg.get("term_sheets") or []:
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
    """Unit price at which `terms` (non-price fields kept) cost `target_c`; C rises with price."""
    hi = hi or max(1.0, (terms.get("unit_price") or 1.0) * 4)
    lo = 0.0
    while total_cost(case, {**terms, "unit_price": hi}, standard, supplier) < target_c and hi < 1e7:
        hi *= 2
    for _ in range(60):
        mid = (lo + hi) / 2
        if total_cost(case, {**terms, "unit_price": mid}, standard, supplier) < target_c:
            lo = mid
        else:
            hi = mid
    return lo


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
