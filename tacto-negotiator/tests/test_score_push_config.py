"""configs/score-push.json reproduces each screened per-case config's decisions offline.

Scripted supplier histories (fixture cases, no network): at every step the combined agent's move
must equal the screened agent's move on the same history. Screened sources: P01 standard
payment (.9602 x2), P02 expected-C target (.5993 x3), P05 rival-price history (.7208 x3), P18
retained package policy (.4531 x2); other cases the package-advice baseline (P11 .7902 x2).
"""
import copy
import json
from pathlib import Path

import pytest

from negotiator.agent import configured_agent
from negotiator.package_advisor import PackageAdvisor

ROOT = Path(__file__).parents[1]
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
COMBINED = "score-push.json"
SCREENED = {
    "case:P01": "p01-standard-payment.json",
    "case:P02": "p02-cost-target.json",
    "case:P03": "package-advice.json",
    "case:P04": "package-advice.json",
    "case:P05": "p05-rival-history.json",
    "case:P07": "package-advice.json",
    "case:P08": "package-advice.json",
    "case:P10": "package-advice.json",
    "case:P11": "package-advice.json",
    "case:P18": "retained-package-policy.json",
}
# Public-dossier-shaped estimates so the expected-C target is active where the case allows it.
EST = {
    "case:P01": {"full_cost": 0.0, "full_cost_range": None},
    "case:P02": {"full_cost": 374.95, "full_cost_range": (356.2, 393.7)},
}


def agent(name, case):
    cfg = json.loads((ROOT / "configs" / name).read_text())
    a = configured_agent(cfg.get("policy_config", cfg), estimates={}, meso=False)
    if a.package_advisor is not None:
        a.package_advisor = PackageAdvisor(lambda *_: {"package_id": "none"})  # deterministic fallback
    if case["case_id"] in EST:
        base = case["buyer"]["current_unit_price"]
        est = {**EST[case["case_id"]], "standard": {"payment_days": 30}, "interest_rate": 0.08,
               "usual_rate": 0.08, "ppm": 273}
        if not est["full_cost"]:
            est["full_cost"], est["full_cost_range"] = base * 0.92, (base * 0.88, base * 0.96)
        for sid in case["suppliers"]:
            a._target_cache[(case["case_id"], sid)] = est
    return a


def supplier_terms(case, price, clause=False):
    alt = case["buyer"]["alternative"]["terms"]
    options = case.get("term_options") or {}
    t = {"unit_price": round(price, 2)}
    for f in case["negotiable"]:
        if f == "unit_price":
            continue
        if f in alt:
            t[f] = alt[f]
        elif options.get(f):
            t[f] = options[f][0]
    if "index_clause" in options:
        t["index_clause"] = next((o for o in options["index_clause"] if o), None) if clause else None
    return t


def sup_msg(case, sid, k, price, status, clause=False):
    return {"from": f"sales@{sid}", "status": status, "body": "Our offer.", "attachments": [],
            "term_sheets": [{"term_sheet_id": f"offer:{sid}:{k}", "terms": supplier_terms(case, price, clause)}]}


def norm(move):
    return json.loads(json.dumps(move, sort_keys=True, default=str)) if move else move


PATH = (1.10, 1.07, 1.05, 1.04, 1.03)


def play_serial(case, a, b, clause=False):
    """Drive both agents on one history (built from agent a's moves); return the moves and first divergence."""
    sid = case["suppliers"][0]
    base = case["buyer"]["current_unit_price"]
    events, moves = [], []
    for k, f in enumerate(PATH):
        status = "final_offer" if k == len(PATH) - 1 else "open"
        events.append(sup_msg(case, sid, k, base * f, status, clause))
        ma, mb = a.decide(case, {sid: copy.deepcopy(events)}), b.decide(case, {sid: copy.deepcopy(events)})
        if norm(ma) != norm(mb):
            return moves, (k, ma, mb)
        moves.append(ma)
        msg = (ma or {}).get("message") or {}
        if not msg.get("term_sheets"):
            break
        events.append({"from": "buyer", "body": msg.get("body", ""), "term_sheets": msg["term_sheets"]})
    return moves, None


@pytest.mark.parametrize("cid", [c for c in SCREENED if c != "case:P05"])
def test_combined_matches_screened_serial(cid):
    case = copy.deepcopy(CASES[cid])
    for clause in (False, True):
        moves, diverged = play_serial(case, agent(SCREENED[cid], case), agent(COMBINED, case), clause)
        assert diverged is None, f"{cid} clause={clause}: diverged at step {diverged and diverged[0]}"
        assert moves


def test_p02_combined_reaches_the_cost_target_package():
    case = copy.deepcopy(CASES["case:P02"])
    moves, diverged = play_serial(case, agent(SCREENED["case:P02"], case), agent(COMBINED, case))
    assert diverged is None
    first = moves[0]["message"]["term_sheets"][0]["terms"]
    assert first["index_clause"] and first["payment_days"] == 90


def test_p01_cost_target_inert_without_index_clause_option():
    from negotiator import cost_target as ct

    case = copy.deepcopy(CASES["case:P01"])
    est = agent(COMBINED, case)._target_cache[(case["case_id"], case["suppliers"][0])]
    assert "index_clause" not in case["term_options"]
    assert ct.active(case, est) and ct.target(case, {"payment_days": 30}, est, index_clause=True) is None


def test_raw_material_has_no_clause_variants():
    """P18 .4531 came from the retained policy without clause variants (variants measured .4196)."""
    case = copy.deepcopy(CASES["case:P08"])
    moves, diverged = play_serial(case, agent("package-advice.json", case), agent(COMBINED, case), clause=True)
    assert diverged is None and all(len(m["message"].get("term_sheets") or [1]) <= 1 for m in moves)


def test_p05_combined_matches_nonleading_hold_async_and_serial():
    case = copy.deepcopy(CASES["case:P05"])
    a, b = agent(SCREENED["case:P05"], case), agent(COMBINED, case)
    leader, rival, third = case["suppliers"][:3]
    for steps in range(1, 4):
        threads = {
            leader: [sup_msg(case, leader, k, 34.5 - 0.5 * k, "open") for k in range(steps)],
            rival: [sup_msg(case, rival, k, 35.0 - 0.3 * k, "open") for k in range(steps)],
            third: [sup_msg(case, third, k, 36.0 - 0.2 * k, "final_offer" if k == steps - 1 else "open")
                    for k in range(steps)],
        }
        assert norm(a.decide(case, copy.deepcopy(threads))) == norm(b.decide(case, copy.deepcopy(threads)))
        for sid in threads:
            pa = a.propose(case, copy.deepcopy(threads), sid)
            pb = b.propose(case, copy.deepcopy(threads), sid)
            assert norm(pa) == norm(pb), (steps, sid)
