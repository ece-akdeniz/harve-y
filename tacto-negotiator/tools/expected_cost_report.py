"""Offline: expected-C-optimal package per practice case over the PUBLIC supplier-cost range.

Usage: uv run python tools/expected_cost_report.py [case:P02 case:P10 ...]

Feature-gated like `cost_target.active`: only cases whose buyer goal carries a relationship term
(RELATIONSHIP_GOALS + relationship_eur_per_point + sustainable_margin_pct) are valued under fc
uncertainty; others print "no relationship term" (C is then monotone in price). Uses the fixture
case, the dossier estimate and nothing hidden (no c_best, no revealed breakdowns).
"""

import json
import sys
from pathlib import Path

from negotiator import cost_target as ct
from negotiator.dossiers import supplier_estimate

FIXTURE = Path(__file__).parents[1] / "tests/fixtures/practice_cases.json"


def report(case):
    sups = case.get("suppliers") or []
    sid = sups[0]["supplier_id"] if sups and isinstance(sups[0], dict) else (sups[0] if sups else None)
    est = supplier_estimate(case, sid) if sid else None
    if not ct.active(case, est):
        return {"case": case["case_id"], "type": case["type"], "note": "no relationship term"}
    std = est["standard"]
    out = {"case": case["case_id"], "type": case["type"], "fc": est["full_cost"], "fc_range": est["full_cost_range"]}
    for label, clause in (("any", False), ("clause", True)):
        t = ct.target(case, std, est, index_clause=clause)
        if t:
            out[label] = {"expected_c": round(t[0]), "terms": t[1]}
    return out


def main(ids):
    cases = {c["case_id"]: c for c in json.loads(FIXTURE.read_text())}
    for cid in ids or sorted(cases):
        if case := cases.get(cid):
            print(json.dumps(report(case), default=str))


if __name__ == "__main__":
    main(sys.argv[1:])
