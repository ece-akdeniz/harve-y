"""Opt-in expected-cost target (P02-shaped fixture; estimate values mirror the public dossier)."""
import copy
import json
from pathlib import Path

import pytest

from negotiator import cost_target as ct
from negotiator.agent import configured_agent
from negotiator.policy import PolicyConfig

CASES = {c["case_id"]: c for c in json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())}
CONFIG = Path(__file__).parents[1] / "configs/p02-cost-target.json"
STD = {"payment_days": 30, "incoterm": "DAP", "lead_time_days": 35}
EST = {"standard": STD, "interest_rate": 0.08, "usual_rate": 0.08, "full_cost": 374.95,
       "full_cost_range": (356.2, 393.7), "ppm": 273}
CLAUSE = {"series": "CU-NOTATION", "material_share": 0.2, "deadband_pct": 5.0, "base_month": "2026-08"}
SID = "sup:70510"


def case():
    return copy.deepcopy(CASES["case:P02"])


def agent():
    a = configured_agent(json.loads(CONFIG.read_text()), estimates={}, meso=False)
    a._target_cache[("case:P02", SID)] = EST
    return a


def sup_msg(sheets, status="open"):
    return {"from": "sales@70510", "status": status, "body": "Copper went up.",
            "term_sheets": [{"term_sheet_id": f"offer:{i}", "terms": t} for i, t in sheets]}


def buyer(t):
    return {"from": "buyer", "term_sheets": [{"terms": t}]}


def t(p, d=90, clause=CLAUSE):
    return {"unit_price": p, "payment_days": d, "index_clause": clause}


def test_policy_flags_default_off_and_validate():
    assert PolicyConfig.from_dict({"version": 1}).cost_target_types == ()
    assert PolicyConfig.from_dict({"version": 1}).cost_target_index_clause is False
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "cost_target_index_clause": "yes"})
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "cost_target_types": ["nope"]})
    cfg = PolicyConfig.load(CONFIG)
    assert cfg.cost_target_types == ("price_increase",) and cfg.cost_target_index_clause


def test_expected_target_is_interior_and_clause_restricted():
    c = case()
    free_c, free = ct.target(c, STD, EST)
    clause_c, clause = ct.target(c, STD, EST, index_clause=True)
    assert free["index_clause"] is None and clause["index_clause"]["deadband_pct"] == 5
    assert clause["payment_days"] == 90 and free_c <= clause_c
    p = clause["unit_price"]
    assert 360 < p < 372
    cost = lambda q: ct.expected_cost(c, {**clause, "unit_price": q}, STD, EST)  # noqa: E731
    assert cost(p - 5) > cost(p) < cost(p + 5)
    cap = cost(p + 3)
    assert ct.ceiling(c, clause, cap, STD, EST) == pytest.approx(p + 3, abs=0.02)
    assert ct.ceiling(c, clause, cost(p) - 1, STD, EST) is None


def test_inactive_without_relationship_estimate():
    c = case()
    assert not ct.active(c, None) and not ct.active(c, {"standard": STD})
    c["buyer"]["category_goal"] = "leverage"
    assert not ct.active(c, EST)


def test_first_offer_is_clause_target_and_accepts_when_met():
    c, a = case(), agent()
    _, tgt = ct.target(c, STD, EST, index_clause=True)
    threads = {SID: [sup_msg([(0, t(370.96, 30, None))])]}
    move = a.decide(c, threads)
    sent = move["message"]["term_sheets"][0]["terms"]
    assert sent["unit_price"] == tgt["unit_price"] and sent["index_clause"]["deadband_pct"] == 5
    assert sent["payment_days"] == 90 and "risk-sharing" in move["message"]["body"]
    threads[SID] += [buyer(sent), sup_msg([("1", t(tgt["unit_price"]))])]
    assert a.decide(c, threads)["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:1"}


def test_lower_counter_is_not_taken_and_final_gets_one_counter():
    c, a = case(), agent()
    _, tgt = ct.target(c, STD, EST, index_clause=True)
    threads = {SID: [sup_msg([(0, t(370.96, 30, None))]), buyer(tgt), sup_msg([("1", t(351.9))])]}
    again = a.decide(c, threads)["message"]["term_sheets"][0]["terms"]
    assert again["unit_price"] == tgt["unit_price"]  # never below the expected-C optimum
    threads[SID] += [buyer(again), sup_msg([("4", t(349.37)), ("4-a", t(367.02, 14, None))], "final_offer")]
    counter = a.decide(c, threads)["message"]["term_sheets"][0]["terms"]
    assert counter["unit_price"] == tgt["unit_price"]
    threads[SID] += [buyer(counter), sup_msg([("5", t(349.37))], "final_offer")]
    assert a.decide(c, threads)["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:5"}


def test_higher_ask_concedes_toward_it_without_backtracking():
    c, a = case(), agent()
    _, tgt = ct.target(c, STD, EST, index_clause=True)
    threads = {SID: [sup_msg([(0, t(380.0))]), buyer(tgt), sup_msg([("1", t(378.0))])]}
    p1 = a.decide(c, threads)["message"]["term_sheets"][0]["terms"]["unit_price"]
    assert tgt["unit_price"] < p1 < 378.0


def test_flag_off_keeps_default_path():
    c = case()
    cfg = json.loads(CONFIG.read_text())
    cfg.pop("cost_target_types")
    cfg.pop("cost_target_index_clause")
    a = configured_agent(cfg, estimates={}, meso=False)
    a._target_cache[("case:P02", SID)] = EST
    move = a.decide(c, {SID: [sup_msg([(0, t(370.96, 30, None))])]})
    assert "risk-sharing package, including the index clause" not in move["message"].get("body", "")
