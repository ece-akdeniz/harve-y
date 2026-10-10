"""Server cost_breakdown vs local arena_kit cost_breakdown for our own closed deals.

Usage: uv run --locked python tools/compare_breakdown.py SESSION_ID... (needs ARENA_API_KEY, ARENA_DATA)."""
import json
import os
import sys

import httpx
from arena_kit.cost import cost_breakdown

from negotiator import cost_target as ct
from negotiator.dossiers import supplier_estimate

H = {"X-API-Key": os.environ["ARENA_API_KEY"]}
B = "https://arena.tacto.ai/v1"
cases = {c["case_id"]: c for c in json.load(open("tests/fixtures/practice_cases.json"))}
for sess in sys.argv[1:]:
    s = httpx.get(f"{B}/sessions/{sess}", headers=H, timeout=60).json()
    res = s["result"]
    case = cases[s["case_id"]]
    terms, srv = res["terms"], res["cost_breakdown"]
    sid = res.get("supplier_id") or (res.get("deal") or {}).get("supplier_id") or case["suppliers"][0]
    est = supplier_estimate(case, sid, force=True)
    std = est["standard"]
    print(f"== {s['case_id']} {sess} score {res['score']:.4f} sup {sid} fc {est.get('full_cost')} "
          f"range {est.get('full_cost_range')} rate {est.get('interest_rate')} std {json.dumps(std)}")
    loc = cost_breakdown(case, terms, std, est)
    grid = ct.scenarios(est) if est.get("full_cost") else [est]
    expv = {k: sum(cost_breakdown(case, terms, std, g)[k] for g in grid) / len(grid) for k in loc}
    for k in sorted(set(srv) | set(loc)):
        a, b, e = srv.get(k, 0), loc.get(k, 0), expv.get(k, 0)
        if a or b or e:
            print(f"  {k:16s} server {a:14,.2f}  local@mid {b:14,.2f}  local E[grid] {e:14,.2f}"
                  f"  diff(mid) {b - a:12,.2f}")
    print(f"  {'TOTAL':16s} server {sum(srv.values()):14,.2f}  local@mid {sum(loc.values()):14,.2f}  "
          f"local E[grid] {sum(expv.values()):14,.2f}")
