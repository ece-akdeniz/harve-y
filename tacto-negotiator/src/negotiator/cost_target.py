"""Opt-in expected-cost target for relationship cases (`PolicyConfig.cost_target_types`).

With a public supplier full-cost estimate, C is convex but not monotonic in price: below the
price that leaves the supplier its sustainable margin the relationship term rises faster than the
spend falls. The supplier's true cost is uncertain, so every package is valued by its expected C
over a uniform grid on the public `full_cost_range` (falling back to +-5 % of `full_cost`). The
target is the expected-C-minimising permitted package (index-clause options included); near-ties
prefer the longest payment term. Offers never go below the target price; no hidden data is used.
"""

import itertools
import math

from arena_kit.cost import RELATIONSHIP_GOALS, complete_offer, must_haves_ok, supplier_value, total_cost

GRID = 41


def active(case, supplier):
    b = case.get("buyer") or {}
    return bool(
        supplier
        and supplier.get("full_cost")
        and b.get("category_goal") in RELATIONSHIP_GOALS
        and b.get("relationship_eur_per_point")
        and b.get("sustainable_margin_pct")
    )


def scenarios(supplier, n=GRID):
    fc = supplier["full_cost"]
    lo, hi = supplier.get("full_cost_range") or (fc * 0.95, fc * 1.05)
    if n <= 1 or hi <= lo:
        return [supplier]
    return [{**supplier, "full_cost": lo + i * (hi - lo) / (n - 1)} for i in range(n)]


def expected_cost(case, terms, standard, supplier, grid=None):
    grid = grid or scenarios(supplier)
    costs = [total_cost(case, terms, standard, s) for s in grid]
    if not all(math.isfinite(c) for c in costs):
        return math.inf
    w = [s.get("_w", 1.0) for s in grid]  # posterior weights (uniform prior: all 1)
    return sum(wi * c for wi, c in zip(w, costs, strict=True)) / sum(w)


def min_price(case, terms, standard, supplier, grid=None):
    """The EUR 0.01 price minimising expected C for `terms` (non-price fields kept; convex)."""
    grid = grid or scenarios(supplier)
    ref = terms.get("unit_price") or (case.get("buyer") or {}).get("current_unit_price") or 1.0
    lo, hi = 0.01, max(1.0, ref * 3)

    def c(p):
        return expected_cost(case, {**terms, "unit_price": p}, standard, supplier, grid)

    while hi - lo > 0.02:
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if c(m1) <= c(m2):
            hi = m2
        else:
            lo = m1
    mid = round((lo + hi) / 2, 2)
    return min((round(mid + k / 100, 2) for k in range(-3, 4)), key=lambda p: (c(p), p))


def target(case, standard, supplier, tie_pct=0.05, index_clause=False):
    """(expected C, complete terms) of the expected-C-minimising permitted package; with
    `index_clause` only packages carrying a permitted index clause (a risk-sharing package)."""
    grid = scenarios(supplier)
    options = case.get("term_options") or {}
    fields = [f for f in case["negotiable"] if f != "unit_price" and options.get(f)]
    ref = (case.get("buyer") or {}).get("current_unit_price") or 1.0
    out = []
    for values in itertools.product(*(options[f] for f in fields)):
        t = complete_offer(case, {"unit_price": ref, **dict(zip(fields, values, strict=True))})
        if not must_haves_ok(case, t, standard) or (index_clause and not t.get("index_clause")):
            continue
        t["unit_price"] = min_price(case, t, standard, supplier, grid)
        c = expected_cost(case, t, standard, supplier, grid)
        if math.isfinite(c):
            out.append((c, t))
    if not out:
        return None
    best = min(c for c, _ in out)
    near = [x for x in out if x[0] <= best * (1 + tie_pct / 100)]
    return min(near, key=lambda x: (-(x[1].get("payment_days") or 0), x[0]))


def ceiling(case, terms, cap_c, standard, supplier, grid=None):
    """Highest EUR 0.01 price above the target price on `terms`' package whose expected C stays
    at or below `cap_c`; None when even the minimum costs more."""
    grid = grid or scenarios(supplier)
    lo = min_price(case, terms, standard, supplier, grid)

    def c(p):
        return expected_cost(case, {**terms, "unit_price": p}, standard, supplier, grid)

    if c(lo) > cap_c:
        return None
    hi = lo * 2
    while c(hi) <= cap_c and hi < 1e7:
        hi *= 2
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if c(mid) <= cap_c else (lo, mid)
    return math.floor(lo * 100 + 1e-6) / 100


# -- in-session supplier-cost posterior (opt-in: PolicyConfig.cost_target_posterior) -------------
# Likelihood: the supplier accepts an offer worth v to it (supplier_value) iff v >= fc * (1 - s),
# s ~ U[0, s_max] = how far below its full cost it is willing to sell. Only the supplier's own
# replies in this session enter (agreed -> accept, any other reply -> refusal); nothing hidden.


def accept_prob(case, terms, standard, supplier, s_max):
    v = supplier_value(case, terms, {**supplier, "standard": {**(supplier.get("standard") or {}), **(standard or {})}})
    gap = 1 - v / supplier["full_cost"]  # share below full cost the offer asks it to sell at
    return min(1.0, max(0.0, (s_max - gap) / s_max))


def posterior(case, standard, supplier, observations, s_max, grid=None):
    """Grid with `_w` weights after `observations` = [(terms, accepted)]; uniform prior. Falls back
    to the prior when the evidence has zero likelihood everywhere."""
    grid = grid or scenarios(supplier)
    out = []
    for s in grid:
        w = s.get("_w", 1.0)
        for terms, accepted in observations:
            p = accept_prob(case, terms, standard, s, s_max)
            w *= p if accepted else 1 - p
        out.append({**s, "_w": w})
    return out if sum(s["_w"] for s in out) > 1e-12 else grid
