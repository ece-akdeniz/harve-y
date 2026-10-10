"""€ value of each negotiable lever on the kit's simulator cases (arena_kit.total_cost).

Run on practice case files too once the key works: save `arena cases` JSON and pass the path.
"""

import json
import sys
from importlib import resources

from arena_kit.cost import complete_offer, total_cost


def cases(path=None):
    if path:
        data = json.loads(open(path, encoding="utf-8").read())
        return data if isinstance(data, list) else data.get("cases", [data])
    root = resources.files("arena_kit") / "sim_cases"
    return [json.loads((root / n).read_text()) for n in ("S01.json", "S02.json", "S03.json")]


def main():
    for case in cases(sys.argv[1] if len(sys.argv) > 1 else None):
        b = case["buyer"]
        price = round((b.get("current_unit_price") or b["fallback_unit_price"]) * 1.05, 2)
        base = complete_offer(case, {"unit_price": price})

        def c(case=case, base=base, **kw):
            return total_cost(case, {**base, **kw})

        c0 = c()
        print(f"\n{case['case_id']} {case['type']} goal={b['category_goal']} need={b['need_per_year']}x"
              f"{b['horizon_years']}y price={price} C={c0:,.0f}")
        print(f"  price -1%: {c(unit_price=round(price * 0.99, 2)) - c0:+,.0f}")
        for field, opts in case.get("term_options", {}).items():
            if field in base:
                print(f"  {field}: " + ", ".join(f"{o}->{c(**{field: o}) - c0:+,.0f}" for o in opts))


if __name__ == "__main__":
    main()
