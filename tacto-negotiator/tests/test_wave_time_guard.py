"""Live-Final wall-clock guard: with fewer than TIME_GUARD_ROUNDS rounds of wave left the agent stops
extending. Compressed clock (see test_runner.ScaledClock), kit simulator with slow replies, an
8-minute (480 s) cap through the async runner's `deadline`, and a sim supplier that never sends a
final offer so a slow schedule would otherwise walk into the cap."""

import copy
import json
from pathlib import Path

import pytest
from arena_kit import sim as kit_sim
from test_evaluator import msg, ours
from test_runner import ScaledClock, SimArena, recording

from negotiator import agent as agent_mod
from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig
from negotiator.runner import CaseRunner
from negotiator.state import Journal

ROOT = Path(__file__).resolve().parents[1]
CAP_S = 480.0
REPLY_S = 50.0  # a slow supplier: close to the ~1 min per reply the brief allows


class Trace:
    def __init__(self):
        self.rows = []

    def log(self, event, **fields):
        self.rows.append({"event": event, **fields})

    def kinds(self, kind):
        return [r for r in self.rows if r["event"] == "decision" and r.get("kind") == kind]

    def events(self, event):
        return [r for r in self.rows if r["event"] == event]


class PatientArena(SimArena):
    """Kit sim whose supplier never sends a final offer (keeps conceding 2 % steps, then holds)."""

    def __init__(self, clock, delays, case_patch=None):
        super().__init__(clock, delays)
        if case_patch:
            cid, patch = case_patch
            case = copy.deepcopy(self.sim.cases[cid])
            case["buyer"].update(patch)
            self.sim.cases[cid] = case


@pytest.fixture
def no_final(monkeypatch):
    monkeypatch.setattr(kit_sim, "FINAL_ROUND", 99)


def _slow_agent(tracer=None, **kw):
    """A 12-step schedule: on its own it needs every one of the 10 messages (> 8 minutes at ~1 min a round)."""
    agent = PackageAgent(rounds=12, tracer=tracer, **kw)
    return agent


def _rounds(arena, session_id):
    return {k: t["round"] for k, t in arena.sim.sessions[session_id]["threads"].items()}


async def _run(arena, clock, agent, tmp_path, cap=CAP_S, tracer=None):
    close, calls = recording()
    t0 = clock.time()
    deadline = t0 + cap
    runner = CaseRunner(arena, "case:S01", agent, Journal(tmp_path / "j.jsonl"), clock=clock, close_fn=close,
                        deadline=lambda: deadline, tracer=tracer)
    result = await runner.run()
    return result, calls, clock.time() - t0, runner


async def test_guard_accepts_acceptable_standing_sheet_before_the_cap(tmp_path, no_final):
    """S01 has no alternative (C_alt = inf): every priced sheet is acceptable. The slow schedule alone
    would still be extending at the cap; the guard closes with >= 2 rounds to spare and no wave_cap."""
    clock, trace = ScaledClock(), Trace()
    arena = PatientArena(clock, {"sup:70270": REPLY_S})
    result, calls, took, runner = await _run(arena, clock, _slow_agent(trace), tmp_path, tracer=trace)
    assert result["deal"] and result["ended"] and result.get("end_reason") != "wave_cap"
    # PackageAgent.decide resolves the guard's close itself (through close_decision): an accept move
    assert calls and calls[0].startswith("agent: accept") and "wave cap" not in calls
    guard = trace.kinds("time_guard")
    assert guard and guard[0]["action"] == "accept"
    assert _rounds(arena, result["session_id"])["sup:70270"] < 10  # it stopped extending
    assert guard[0]["guard"] == 2 * max(agent_mod.ROUND_ESTIMATE_S, runner.st.slowest_round_s)
    assert guard[0]["time_left"] < guard[0]["guard"]
    # closed with at least two measured rounds of margin before the cap
    assert CAP_S - took >= 2 * runner.st.slowest_round_s
    assert result["thread_timeouts"] == {"sup:70270": 0}
    # timing trace: one round_time per observed reply, one thread_time per thread
    rounds = trace.events("round_time")
    assert rounds and all(r["reply_s"] >= REPLY_S - 1 and r["decide_s"] >= 0 for r in rounds)
    assert [r["round"] for r in rounds] == list(range(1, len(rounds) + 1))
    thread = trace.events("thread_time")
    assert len(thread) == 1 and thread[0]["rounds"] == len(rounds) and thread[0]["slowest_round_s"] >= REPLY_S
    assert all(r["seconds"] > 0 and r["guard_s"] >= 240 for r in trace.events("wave_time_left"))


async def test_without_guard_the_same_thread_walks_into_the_cap(tmp_path, no_final):
    """Control: guard off -> the watchdog's cap close is what ends the case (the thread was still open)."""
    clock = ScaledClock()
    arena = PatientArena(clock, {"sup:70270": REPLY_S})
    agent = _slow_agent()
    agent.time_guard_rounds = 0
    result, calls, took, _ = await _run(arena, clock, agent, tmp_path)
    assert calls[0] == "wave cap" and result["ended"]
    assert took > CAP_S - 2 * agent_mod.ROUND_ESTIMATE_S  # it ran past the point where the guard would fire


async def test_guard_converges_to_the_ask_when_the_standing_sheet_is_not_acceptable(tmp_path, no_final):
    """A must-have the supplier's standard terms break: its sheet can never be accepted. The guard
    offers its own price on our (valid) terms instead of walking into the cap; the sim agrees."""
    clock, trace = ScaledClock(), Trace()
    patch = {"must_haves": [{"field": "payment_days", "op": ">=", "value": 45}]}
    arena = PatientArena(clock, {"sup:70270": REPLY_S}, case_patch=("case:S01", patch))
    result, calls, took, runner = await _run(arena, clock, _slow_agent(trace), tmp_path, tracer=trace)
    assert result["deal"] and result["must_haves_ok"] and result["terms"]["payment_days"] >= 45
    assert calls == ["sup:70270 agreed"]
    guard = trace.kinds("time_guard")
    assert guard and guard[0]["action"] == "match"
    offers = [r for r in trace.kinds("offer") if r.get("reason", "").startswith("time guard")]
    assert offers and offers[0]["terms"]["unit_price"] == guard[0]["terms"]["unit_price"]
    assert CAP_S - took >= 90  # agreed before the watchdog's cap margin
    # control: without the guard the sheet is never acceptable and the cap ends it with no deal
    clock2 = ScaledClock()
    arena2 = PatientArena(clock2, {"sup:70270": REPLY_S}, case_patch=("case:S01", patch))
    off = _slow_agent()
    off.time_guard_rounds = 0
    result2, calls2, _, _ = await _run(arena2, clock2, off, tmp_path / "off")
    assert calls2[0] == "wave cap" and not result2["deal"]


def test_guard_is_inactive_without_a_cap():
    """Practice: the runner passes no deadline -> time_left_fn returns None -> no guard, same moves."""
    agent = PackageAgent()
    assert agent.time_left_fn is None and agent.time_guard() is None and not agent._guarded()
    agent.time_left_fn = lambda: None
    assert agent.time_guard() is None
    agent.time_left_fn = lambda: 100.0
    assert agent.time_guard() == (100.0, 240.0) and agent._guarded()
    agent.round_estimate_fn = lambda: 150.0
    assert agent.time_guard() == (100.0, 300.0)
    agent.time_left_fn = lambda: 1000.0
    assert not agent._guarded()


def test_runner_wires_the_clock_only_with_a_cap(tmp_path):
    clock = ScaledClock()
    agent = PackageAgent()
    CaseRunner(SimArena(clock), "case:S01", agent, Journal(tmp_path / "j.jsonl"), clock=clock)._wire_agent_clock()
    assert agent.time_left_fn() is None  # practice: deadline_fn is None
    cap = clock.time() + 300
    CaseRunner(SimArena(clock), "case:S01", agent, Journal(tmp_path / "k.jsonl"), clock=clock,
               deadline=lambda: cap)._wire_agent_clock()
    assert 290 < agent.time_left_fn() <= 300


def test_reciprocal_schedule_is_bypassed_under_the_guard():
    """P18 with the fresh pacing levers: a holding supplier gets token steps; under the guard the move
    is the match at its ask (no reciprocal row, no schedule step)."""
    cases = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
    base = json.loads((ROOT / "configs/score-push-v3.json").read_text())
    thread = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
    case, sid = cases["case:P18"], thread["supplier_id"]
    counter = thread["messages"][2]["term_sheets"][0]["terms"]

    def supplier(i, price):
        return msg("open", (f"offer:sim-{i}", {**counter, "unit_price": price}))

    opening = copy.deepcopy(thread["messages"][0])
    opening["term_sheets"][0]["terms"]["unit_price"] = 6.10
    events = [opening]
    policy = PolicyConfig.from_dict({**base, "reciprocal_schedule": True, "claim_pacing": True})
    trace = Trace()
    agent = PackageAgent(policy=policy, estimates={}, meso=False, tracer=trace)
    for i, ask in enumerate([6.00, 5.90, 5.80, 5.80], 1):
        events.append(ours(agent.decide(case, {sid: events})["message"]["term_sheets"][0]["terms"]))
        events.append(supplier(i, ask))
    assert trace.kinds("reciprocal")  # the schedule was reciprocal while time was plentiful
    trace.rows.clear()
    agent.time_left_fn = lambda: 200.0  # < 2 x 120 s
    move = agent.decide(case, {sid: events})
    assert not trace.kinds("reciprocal") and trace.kinds("time_guard")
    guard = trace.kinds("time_guard")[0]
    # the standing 5.80 sheet beats P18's alternative: the guard accepts it instead of another token step
    assert guard["action"] == "accept"
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:sim-4"}
