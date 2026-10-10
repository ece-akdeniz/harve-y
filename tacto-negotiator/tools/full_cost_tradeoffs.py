"""Offline: complete buyer cost of every legal package for a case, at a reference price.

Usage: uv run python tools/full_cost_tradeoffs.py case:P18 5.45 [case:P08 5.31 ...]

For each combination of `term_options` (fixed terms from the case), prints C at the reference
price, the price that gives the same C as the reference package (first argument's package =
the cheapest-C combination at that price), and the EUR value of 0.01 of price. Public fixture
only: no c_best, no revealed breakdowns. Also prints the payment value for the supplier at an
assumed cost of money (8 %, the company rate; a cash-short supplier values it more).
"""

import itertools
import json
import sys
from pathlib import Path

from arena_kit.cost import cost_breakdown, total_cost

FIXTURE = Path(__file__).parents[1] / "tests/fixtures/practice_cases.json"


def price_for(case, terms, target):
    lo, hi = 0.01, 10 * (case["buyer"].get("current_unit_price") or 100)
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if total_cost(case, {**terms, "unit_price": mid}) < target else (lo, mid)
    return round(lo, 3)


def report(case, price):
    opts = {f: v for f, v in case.get("term_options", {}).items() if f in case["negotiable"]}
    rows = []
    for combo in itertools.product(*opts.values()):
        terms = dict(zip(opts, combo, strict=True))
        c = total_cost(case, {**terms, "unit_price": price})
        b = cost_breakdown(case, {**terms, "unit_price": price})
        rows.append((c, terms, {k: round(v) for k, v in b.items() if v}))
    rows.sort(key=lambda r: r[0])
    best_c, best_terms, _ = rows[0]
    cent = total_cost(case, {**best_terms, "unit_price": price + 0.01}) - best_c
    print(f"== {case['case_id']} at price {price}: EUR per 0.01 price = {cent:,.0f}")
    for c, terms, b in rows:
        short = {k: (v["deadband_pct"] if isinstance(v, dict) else v) for k, v in terms.items()}
        print(f"  C {c:12,.0f}  equal-C price {price_for(case, terms, best_c):8.3f}  {short}  {b}")


def main(args):
    cases = {c["case_id"]: c for c in json.loads(FIXTURE.read_text())}
    for cid, price in zip(args[::2], args[1::2], strict=True):
        report(cases[cid], float(price))


if __name__ == "__main__":
    main(sys.argv[1:])
