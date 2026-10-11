"""Opt-in `alt_clause_counter`: on `gap closed: take alternative` while the supplier is open and more
than two of our moves remain, counter once with the alternative's package at the standing sheet's price
(P18: 5.30 with the deadband-5 clause); never on a final offer, never twice, never a sheet already sent.
If the supplier stays open without taking it, the next decision takes the alternative as today."""

import copy
import json
from pathlib import Path

import pytest
from arena_kit.play import moves_left
from test_evaluator import ours

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "configs/fresh-h1h2-run.json").read_text())["policy_config"]  # the 0.5325 P18 run
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
THREAD = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
OPENING = THREAD["messages"][0]  # carries the quote PDF the agent reads standard terms from
SID = THREAD["supplier_id"]
CASE = CASES["case:P18"]
DB0 = THREAD["messages"][2]["term_sheets"][0]["terms"]  # 90d / 24m / AS-14404 deadband 0
DB5 = THREAD["messages"][2]["term_sheets"][1]["terms"]  # 90d / 24m / AS-14404 deadband 5


@pytest.fixture(autouse=True, scope="module")
def _cache_data_package():
    """Every fresh agent rebuilds the evidence context and dossiers (~0.7 s); cache them per case."""
    from negotiator import dossiers, evidence, trades

    mp = pytest.MonkeyPatch()
    package = dossiers.load_package()
    contexts, built, orig_context, orig_build_one = {}, {}, evidence.build_context, dossiers.build_one

    def build_context(case, pkg):
        if case["case_id"] not in contexts:
            contexts[case["case_id"]] = orig_context(case, pkg)
        return contexts[case["case_id"]]

    def build_one(pkg, sid):
        if sid not in built:
            built[sid] = orig_build_one(pkg, sid)
        return built[sid]

    mp.setattr(evidence, "load_package", lambda: package)
    mp.setattr(evidence, "build_context", build_context)
    mp.setattr(trades, "load_package", lambda: package)
    mp.setattr(trades, "build_one", build_one)
    yield
    mp.undo()


class Trace:
    def __init__(self):
        self.rows = []

    def log(self, _channel, **fields):
        self.rows.append(fields)


def _agent(flag, tracer=None):
    policy = PolicyConfig.from_dict({**BASE, "alt_clause_counter": flag})
    agent = PackageAgent(policy=policy, estimates={}, meso=False, tracer=tracer)
    agent.conditional_exchange = True
    return agent


def _two_sheets(i, main, alt, status="open"):
    """The retained supplier's shape: a standing db0 sheet and a dearer db5 alternative."""
    return {"from": "sales", "status": status, "term_sheets": [
        {"term_sheet_id": f"offer:sim-{i}", "terms": {**DB0, "unit_price": main}},
        {"term_sheet_id": f"offer:sim-{i}-a", "terms": {**DB5, "unit_price": alt}},
    ]}


def _sheet(move):
    message = move.get("message") or {}
    sheets = message.get("term_sheets") or [{}]
    return sheets[0].get("terms")


def _reasons(trace):
    return [r.get("reason") for r in trace.rows if r.get("kind") == "offer"]


def _converged(agent, replies=((5.40, 5.50), (5.30, 5.40), (5.30, 5.40))):
    """Replay the 0.5325 P18 path with the agent's own moves: 5.37 -> 5.40/5.50, 5.39 -> 5.30/5.40,
    5.40 (their price, our terms) -> 5.30/5.40 held. Returns the history at the `take alternative` point."""
    events = [copy.deepcopy(OPENING)]
    for i, (main, alt) in enumerate(replies, 1):
        move = agent.decide(CASE, {SID: events})
        assert move["message"].get("action") is None
        events.append({"from": "buyer", **move["message"]})
        events.append(_two_sheets(i, main, alt))
    return events


COUNTER = {**DB5, "unit_price": 5.30}
ALT = {**DB5, "unit_price": 5.40}


def test_flag_off_takes_the_alternative_as_today():
    trace = Trace()
    agent = _agent(False, tracer=trace)
    events = _converged(agent)
    assert [s["unit_price"] for s in agent._ours(events)] == [5.37, 5.39, 5.40]
    move = agent.decide(CASE, {SID: events})
    assert _sheet(move) == ALT
    assert _reasons(trace)[-1] == "gap closed: take alternative"
    assert not [r for r in trace.rows if r.get("kind") == "alt_clause_counter"]


def test_flag_on_counters_once_at_the_standing_price_with_the_alternative_clause():
    trace = Trace()
    agent = _agent(True, tracer=trace)
    events = _converged(agent)
    assert moves_left(CASE, events) > 2
    move = agent.decide(CASE, {SID: events})
    assert _sheet(move) == COUNTER  # 5.30 + deadband 5
    assert _reasons(trace)[-1] == "alt clause counter: standing price with alternative clause"
    row = [r for r in trace.rows if r.get("kind") == "alt_clause_counter"][-1]
    assert row["standing_price"] == 5.30 and row["alt_price"] == 5.40 and row["c_counter"] < row["c_alt_sheet"]
    assert agent.alt_clause_countered[SID] == {"counter": COUNTER, "alt": ALT}
    # every earlier move is identical to the flag-off agent's (the flag only acts at this branch)
    assert agent._ours(events) == _agent(False)._ours(_converged(_agent(False)))


def test_flag_on_never_counters_a_final_offer():
    on, off = _agent(True), _agent(False)
    events_on, events_off = _converged(on), _converged(off)
    for history in (events_on, events_off):
        history[-1] = _two_sheets(3, 5.30, 5.40, status="final_offer")
    move_on, move_off = on.decide(CASE, {SID: events_on}), off.decide(CASE, {SID: events_off})
    assert move_on == move_off
    assert move_on["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:sim-3"}
    assert SID not in on.alt_clause_countered


def test_after_a_declined_counter_the_next_decision_takes_the_alternative_and_never_loops():
    trace = Trace()
    agent = _agent(True, tracer=trace)
    events = _converged(agent)
    events.append({"from": "buyer", **agent.decide(CASE, {SID: events})["message"]})
    assert agent._ours(events)[-1] == COUNTER
    # the supplier stays open and re-sends the same two sheets: take the alternative (today's move)
    events.append(_two_sheets(4, 5.30, 5.40))
    move = agent.decide(CASE, {SID: events})
    assert _sheet(move) == ALT
    assert _reasons(trace)[-1] == "alt clause counter declined: take alternative"
    assert len([r for r in trace.rows if r.get("kind") == "alt_clause_counter"]) == 1
    # a second hold: today's close logic (accept the standing sheet) - no second counter, no loop
    events.append({"from": "buyer", **move["message"]})
    events.append(_two_sheets(5, 5.30, 5.40))
    move = agent.decide(CASE, {SID: events})
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:sim-5"}
    assert len([r for r in trace.rows if r.get("kind") == "alt_clause_counter"]) == 1
    assert [s for s in agent._ours(events)].count(COUNTER) == 1  # the counter was sent exactly once


def test_declined_counter_fallback_tracks_an_improved_alternative_and_a_final_offer_accepts():
    agent = _agent(True)
    events = _converged(agent)
    events.append({"from": "buyer", **agent.decide(CASE, {SID: events})["message"]})
    # the supplier improves the alternative instead: take that one
    history = [*events, _two_sheets(4, 5.30, 5.35)]
    assert _sheet(agent.decide(CASE, {SID: history})) == {**DB5, "unit_price": 5.35}
    # a final offer after the counter: identical to the flag-off agent given the same history
    history = [*events, _two_sheets(4, 5.30, 5.40, status="final_offer")]
    off = _agent(False)
    assert agent.decide(CASE, {SID: history}) == off.decide(CASE, {SID: copy.deepcopy(history)})
    assert agent.decide(CASE, {SID: history})["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:sim-4"}


def test_once_per_thread_survives_a_restart_and_an_already_sent_sheet_is_never_repeated():
    sender = _agent(True)
    events = _converged(sender)
    events.append({"from": "buyer", **sender.decide(CASE, {SID: events})["message"]})
    events.append(_two_sheets(4, 5.30, 5.40))
    # a fresh agent (restart) sees the counter in history: it falls back instead of countering again
    trace = Trace()
    fresh = _agent(True, tracer=trace)
    move = fresh.decide(CASE, {SID: events})
    assert fresh.alt_clause_countered[SID] == {"counter": COUNTER, "alt": ALT}
    assert _sheet(move) == ALT and _reasons(trace)[-1] == "alt clause counter declined: take alternative"
    assert not [r for r in trace.rows if r.get("kind") == "alt_clause_counter"]
    # the history helper only recognises the exact pattern (alternative repriced at the standing price)
    plain = _converged(_agent(False))
    assert PackageAgent._alt_clause_history(CASE, plain) is None
    assert PackageAgent._alt_clause_history(CASE, events) == {"counter": COUNTER, "alt": ALT}


def test_n_minus_2_guard_leaves_the_default_move_in_place():
    # eight of our offers already sent -> moves_left == 2: the counter would leave no room to fall back
    events = [copy.deepcopy(OPENING)]
    for i in range(1, 8):
        events.append(ours({**DB0, "index_clause": None, "unit_price": round(5.30 + 0.01 * i, 2)}))
        events.append(_two_sheets(i, 5.60, 5.70))
    events.append(ours({**DB0, "index_clause": None, "unit_price": 5.40}))
    events.append(_two_sheets(8, 5.30, 5.40))
    assert moves_left(CASE, events) == 2
    trace = Trace()
    on, off = _agent(True, tracer=trace), _agent(False)
    move_on, move_off = on.decide(CASE, {SID: events}), off.decide(CASE, {SID: copy.deepcopy(events)})
    assert move_on == move_off and _sheet(move_on) == ALT
    assert _reasons(trace)[-1] == "gap closed: take alternative"
    assert SID not in on.alt_clause_countered
    # one more of our moves available (moves_left == 3): the counter fires
    shorter = [copy.deepcopy(OPENING), *events[3:]]
    assert moves_left(CASE, shorter) == 3
    assert _sheet(_agent(True).decide(CASE, {SID: shorter})) == COUNTER


def test_policy_flag_defaults_off_and_validates():
    assert PolicyConfig.from_dict({"version": 1}).alt_clause_counter is False
    assert PolicyConfig.from_dict({"version": 1, "alt_clause_counter": True}).alt_clause_counter is True
    with pytest.raises(ValueError, match="alt_clause_counter must be boolean"):
        PolicyConfig.from_dict({"version": 1, "alt_clause_counter": 1})
    cfg = json.loads((ROOT / "configs/p18-alt-counter.json").read_text())
    assert cfg["policy_config"].pop("alt_clause_counter") is True
    assert cfg["policy_config"] == BASE  # the 0.5325 claim_pacing P18 config plus the flag
