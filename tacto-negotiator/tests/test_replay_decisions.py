"""Saved hosted prefixes plus boundary mutations. These tests never predict supplier responses."""

import copy
import importlib.util
import json
import time
from pathlib import Path

import pytest
from arena_kit.cost import total_cost
from arena_kit.docs import standard_terms

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig
from negotiator.responses import package_memory, permitted, respond

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("replay_decisions", ROOT / "tools/replay_decisions.py")
LAB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB)
SNAPSHOTS = {s["id"]: s for s in json.loads(LAB.FIXTURE.read_text())["snapshots"]}
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}


@pytest.mark.parametrize("name", list(SNAPSHOTS))
def test_saved_decision_prefix(name):
    s = SNAPSHOTS[name]
    before = LAB.run_one(s, CASES[s["case_id"]])
    after = LAB.run_one(s, CASES[s["case_id"]], True)
    assert after["matches_annotation"] and after["safe"]
    assert before["matches_annotation"] == (name in ("p04-preserve-opening", "p02-preserve-final"))
    if after["terms"]:
        assert after["proposal_cost"] <= before["proposal_cost"] + 0.01
        assert not after["move"]["message"].get("action")


def test_annotations_never_change_the_policy_input():
    s = copy.deepcopy(SNAPSHOTS["p02-priced-payment"])
    original = LAB.run_one(s, CASES[s["case_id"]], True)
    s["expected"] = {"kind": "close", "terms": {"unit_price": 1}}
    assert LAB.run_one(s, CASES[s["case_id"]], True)["move"] == original["move"]


def test_prefixes_have_no_results_or_future_messages():
    for s in SNAPSHOTS.values():
        for sid, messages in s["threads"].items():
            assert len(messages) == s["source"]["prefix_ends"][sid] + 1
            assert all(set(m) <= {"from", "status", "term_sheets", "body", "refs", "message_id"}
                       for m in messages)


def test_memory_is_reconfirmation_only_and_not_acceptance():
    s = SNAPSHOTS["p11-remember-alternative"]
    c, events = CASES[s["case_id"]], s["threads"][s["supplier_id"]]
    memory = package_memory(c, events, standard_terms(events))
    older = next(p for p in memory if p["source_sheet"] == "offer:70140-1-a")
    assert older["requires_reconfirmation"] and older["message_index"] == 2
    assert older["quoted_cost"] == pytest.approx(770991)
    move = LAB.run_one(s, c, True)["move"]["message"]
    assert "action" not in move and "term_sheet_id" not in move["term_sheets"][0]


@pytest.mark.parametrize("seconds", [0, 19])
def test_unknown_or_near_deadline_does_not_switch(seconds):
    s = copy.deepcopy(SNAPSHOTS["p02-priced-payment"])
    s["seconds_left"] = seconds
    before = LAB.run_one(s, CASES[s["case_id"]])
    after = LAB.run_one(s, CASES[s["case_id"]], True)
    assert after["terms"] == before["terms"]


def test_nonleading_hold_expires_before_buyer_timeout():
    s = copy.deepcopy(SNAPSHOTS["p05-losing-close"])
    c = CASES[s["case_id"]]
    assert LAB.run_one(s, c, True)["kind"] == "hold"
    s["seconds_left"] = 19
    assert LAB.run_one(s, c, True)["kind"] == "close"


def test_leader_final_or_withdrawn_recomputes_case_decision():
    for state in ("final_offer", "walked_away"):
        s = copy.deepcopy(SNAPSHOTS["p05-losing-close"])
        # Remove the in-flight buyer message and change the leading supplier's latest status.
        s["threads"]["sup:70210"] = s["threads"]["sup:70210"][:5]
        s["threads"]["sup:70210"][-1]["status"] = state
        result = LAB.run_one(s, CASES[s["case_id"]], True)
        if state == "final_offer":
            assert result["kind"] == "close"
        else:
            # A different supplier now leads on complete cost; it should still get a chance.
            held = [e for e in result["trace"] if e.get("kind") == "nonleading_convergence"]
            assert held and held[-1]["leading_supplier"] == "sup:70240"
            s["threads"]["sup:70240"] = s["threads"]["sup:70240"][:5]
            s["threads"]["sup:70240"][-1]["status"] = "walked_away"
            assert LAB.run_one(s, CASES[s["case_id"]], True)["kind"] == "close"


def test_fixed_payment_illegal_ppm_and_out_of_schema_quotes_ignored():
    s = copy.deepcopy(SNAPSHOTS["p11-chargeback-alternative"])
    c, sid = CASES[s["case_id"]], s["supplier_id"]
    sheet = s["threads"][sid][-1]["term_sheets"][1]
    for changes in ({"payment_days": 30}, {"ppm_commitment": 2500},
                    {"chargeback_eur_per_complaint": 123}, {"unit_price": float("nan")}):
        bad = {**sheet["terms"], **changes}
        events = copy.deepcopy(s["threads"][sid])
        events[-1]["term_sheets"][1]["terms"] = bad
        assert not any(p["source_sheet"] == sheet["term_sheet_id"] for p in package_memory(c, events, {}))


def test_restart_reconstructs_switch_budget():
    s = SNAPSHOTS["p02-priced-payment"]
    c, sid = CASES[s["case_id"]], s["supplier_id"]
    events = copy.deepcopy(s["threads"][sid])
    base = LAB.run_one(s, c)["terms"]
    for payment in (60, 45):
        events += [{"from": "buyer", "term_sheets": [{"terms": {**base, "payment_days": payment}}]},
                   copy.deepcopy(events[2])]
    proposed = {**base, "payment_days": 45}
    assert respond(c, events, proposed, {}, None, time.time() + 60) == (proposed, None)


def test_repeated_restart_proposals_identical():
    for s in SNAPSHOTS.values():
        a = LAB.run_one(s, CASES[s["case_id"]], True)["move"]
        b = LAB.run_one(s, CASES[s["case_id"]], True)["move"]
        assert a == b


def test_p02_lower_nominal_price_is_not_savings():
    c = CASES["case:P02"]
    final = {"unit_price": 373.65, "payment_days": 90, "index_clause": None}
    cheaper_nominal = {**final, "unit_price": 369.95, "payment_days": 30}
    assert total_cost(c, cheaper_nominal) > total_cost(c, final)


def test_new_flags_validate_and_default_off(tmp_path):
    path = tmp_path / "policy.json"
    for flag in ("free_concessions", "rfq_close_guard"):
        path.write_text(json.dumps({"version": 1, flag: "true"}))
        with pytest.raises(ValueError):
            PolicyConfig.load(path)
    cfg = PolicyConfig()
    assert not cfg.response_types and not cfg.rfq_close_guard and not cfg.free_concessions
    assert PackageAgent(policy=cfg).policy == cfg
    assert not permitted(CASES["case:P02"], {"unit_price": -1})


@pytest.mark.parametrize("seconds", [0, 1, 19])
def test_free_concession_keeps_package_near_deadline(seconds):
    s = copy.deepcopy(SNAPSHOTS["p05-free-delivery"])
    s["seconds_left"] = seconds
    before = LAB.run_one(s, CASES[s["case_id"]])
    after = LAB.run_one(s, CASES[s["case_id"]], True)
    assert after["terms"] == before["terms"]


def test_free_concession_needs_three_moves():
    s = SNAPSHOTS["p05-free-delivery"]
    case = copy.deepcopy(CASES[s["case_id"]])
    # The prefix already has two buyer messages; only two moves remain.
    case["round_limit"] = 4
    before = LAB.run_one(s, case)
    after = LAB.run_one(s, case, True)
    assert after["terms"] == before["terms"]


def test_free_concession_reconstructs_exhausted_switch_budget():
    s = copy.deepcopy(SNAPSHOTS["p05-free-delivery"])
    events = s["threads"][s["supplier_id"]]
    # Two past switches, 28 -> 35 -> 28, leave no new package switch available.
    buyer = copy.deepcopy(events[1])
    buyer["term_sheets"][0]["terms"]["lead_time_days"] = 35
    events[2:2] = [copy.deepcopy(events[2]), buyer]
    before = LAB.run_one(s, CASES[s["case_id"]])
    after = LAB.run_one(s, CASES[s["case_id"]], True)
    assert after["terms"] == before["terms"]


def test_free_concession_cannot_chain_another_package_trade(monkeypatch):
    from negotiator import responses
    from negotiator.trades import TradePolicy

    def unexpected_trade(*args, **kwargs):
        pytest.fail("a free package switch must not also run response/stagnation trades")

    s = copy.deepcopy(SNAPSHOTS["p05-free-delivery"])
    monkeypatch.setattr(responses, "respond", unexpected_trade)
    monkeypatch.setattr(TradePolicy, "switch", unexpected_trade)
    policy = PolicyConfig(**{**s["policy"], "free_concessions": True, "response_types": ("rfq",)})
    agent = PackageAgent(policy=policy, estimates={}, meso=False, claims=False)
    sid = s["supplier_id"]
    agent.trades.deadlines[sid] = time.time() + 60
    move = agent.propose(CASES[s["case_id"]], s["threads"], sid)
    assert move["message"]["term_sheets"][0]["terms"]["lead_time_days"] == 35
