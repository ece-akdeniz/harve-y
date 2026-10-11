"""Time-compressed schedule (policy `compressed_schedule`, default OFF since codex/consolidated: the lane's own
sim turned every case into a round-2 match; opt in per config): with a wave cap the agent sizes
the rounds that still fit before the wave guard - rounds_available = floor((time left - guard) /
max(ROUND_FLOOR_S, slowest measured round)) - and, when the normal schedule cannot reach its end state
by round rounds_available - 1, rescales the remaining path so that it does. Fake clock throughout;
without a cap rounds_available is None and nothing changes (replay proof in
tests/test_compressed_schedule_replay.py)."""

import copy
import json
from pathlib import Path

import pytest
from arena_kit import sim as kit_sim
from test_evaluator import msg, ours
from test_runner import ScaledClock, recording
from test_wave_time_guard import CAP_S, REPLY_S, PatientArena, Trace

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig
from negotiator.runner import CaseRunner
from negotiator.state import Journal

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
V3 = json.loads((ROOT / "configs/score-push-v3.json").read_text())


def _comp(**kw):
    """A policy-less agent with the compressed schedule switched on (opt-in since codex/consolidated)."""
    agent = PackageAgent(**kw)
    agent.compressed_schedule = True
    return agent
ASKED = "Faster payment is welcome; we can reflect it in the price."
T35 = {"payment_days": 30, "lead_time_days": 35}


class Clock:
    """Fake wave clock: `left` seconds to the cap, `slowest` measured round."""

    def __init__(self, left, slowest=0.0):
        self.left, self.slowest = left, slowest

    def wire(self, agent):
        agent.time_left_fn = lambda: self.left
        agent.round_estimate_fn = lambda: self.slowest
        return agent


def test_policy_keys_default_on_and_validate():
    p = PolicyConfig.from_dict({"version": 1})
    assert p.time_guard is True and p.compressed_schedule is False  # guard on, compression opt-in
    assert PolicyConfig.from_dict({"version": 1, "compressed_schedule": True}).compressed_schedule is True
    off = PolicyConfig.from_dict({**V3, "time_guard": False, "compressed_schedule": False})
    assert off.time_guard is False and off.compressed_schedule is False
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "compressed_schedule": "yes"})
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "time_guard": 1})
    agent = PackageAgent(policy=off)
    assert agent.time_guard_rounds == 0 and agent.compressed_schedule is False
    assert Clock(100.0).wire(agent).time_guard() is None
    # rounds_available is a clock fact (the safety uses key on it); the rescale itself is off
    assert agent.rounds_available() == 0 and agent.compression(CASES["case:P18"], "s", 0) is None
    v4 = json.loads((ROOT / "configs/score-push-v4.json").read_text())
    assert "time_guard" in v4 and "compressed_schedule" in v4  # both recorded explicitly
    assert v4["time_guard"] is True and PolicyConfig.from_dict(v4).compressed_schedule is v4["compressed_schedule"]
    assert v4["compressed_schedule"] is False and v4["prewarm"] is True
    v3 = json.loads((ROOT / "configs/score-push-v3.json").read_text())
    extra = ("time_guard", "compressed_schedule", "prewarm", "claim_pacing", "rfq_fast_payment_reanchor",
             "reciprocal_schedule", "alt_clause_counter", "supplier_payment_trade", "cost_breakdown_request")
    assert {k: v for k, v in v4.items() if k not in extra} == v3  # v3 + the explicit flag block
    assert PolicyConfig.from_dict(v4).claim_pacing and PolicyConfig.from_dict(v4).rfq_fast_payment_reanchor


def test_rounds_available_formula():
    agent = _comp()
    assert agent.rounds_available() is None  # practice: no clock wired
    agent.time_left_fn = lambda: None
    assert agent.rounds_available() is None
    clock = Clock(480.0)
    clock.wire(agent)
    # guard = 2 x max(120, 0) = 240; a round is never assumed faster than 60 s -> floor(240 / 60) = 4
    assert agent.rounds_available() == 4
    clock.slowest = 85.0  # guard stays 240 (85 < 120); rounds at the measured pace
    assert agent.rounds_available() == int((480 - 240) // 85) == 2
    clock.left = 395.0
    assert agent.rounds_available() == 1
    clock.left = 200.0  # inside the guard window: nothing fits
    assert agent.rounds_available() == 0
    clock.left, clock.slowest = 1000.0, 150.0  # guard = 2 x 150 = 300; floor(700 / 150) = 4
    assert agent.rounds_available() == 4
    agent.compressed_schedule = False
    assert agent.rounds_available() == 4 and agent.compression(CASES["case:P18"], "s", 0) is None


def test_compression_activates_only_when_the_schedule_does_not_fit():
    case = CASES["case:P18"]
    agent = _comp(rounds=5)
    assert agent.compression(case, "s", 0) is None  # no cap
    # the normal 5-round schedule needs 6 moves (fractions 0/5 .. 5/5) from k = 0
    assert agent.compression(case, "s", 0, avail=7) is None  # fit = 6 >= 6
    comp = agent.compression(case, "s", 0, avail=6)  # fit = 5 < 6: compress
    assert comp is not None and comp[0] == 6 and comp[1] == pytest.approx(0 + 5 / 5) and comp[2] == pytest.approx(6 / 5)
    # with 2 offers sent the path still needs 4 moves; 4 rounds available -> fit = 3 < 4
    avail, k_eff, ratio = agent.compression(case, "s", 2, avail=4)
    assert k_eff == pytest.approx(2 + 3 / 3) and ratio == pytest.approx(4 / 3)
    assert agent.compression(case, "s", 2, avail=5) is None
    # one round or none: the end state now
    assert agent.compression(case, "s", 1, avail=1)[1] == 5.0
    assert agent.compression(case, "s", 1, avail=0)[1] == 5.0
    # stage gates counted in holds/rounds advance proportionally, never below one
    assert agent._gate(2, (4, 3.0, 4 / 3)) == 2 and agent._gate(2, (3, 5.0, 2.5)) == 1 and agent._gate(1, None) == 1


def _p18_thread():
    thread = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
    opening = copy.deepcopy(thread["messages"][0])
    opening["term_sheets"][0]["terms"]["unit_price"] = 6.10
    counter = thread["messages"][2]["term_sheets"][0]["terms"]
    return thread["supplier_id"], opening, counter


def _play(agent, case, sid, opening, counter, asks, clock=None, round_s=85.0):
    """Our offers against a supplier that answers each with the next ask; the fake clock advances one
    round per exchange and the slowest round is known from the first reply on."""
    events, prices = [opening], []
    for i, ask in enumerate(asks, 1):
        move = agent.decide(case, {sid: events})
        if move.get("message", {}).get("action"):
            prices.append(move["message"]["action"])
            break
        terms = move["message"]["term_sheets"][0]["terms"]
        prices.append(terms["unit_price"])
        events.append(ours(terms))
        events.append(msg("open", (f"offer:sim-{i}", {**counter, "unit_price": ask})))
        if clock is not None:
            clock.left -= round_s
            clock.slowest = round_s
    return prices, events


def test_end_state_is_reached_by_round_rounds_available_minus_one():
    """Supplier holds at 6.00 on our terms; the plain 5-round schedule needs six moves to reach that
    ask. With four rounds available (and one fewer each round) the compressed schedule is at the ask on
    its third move - rounds_available - 1 - where the plain schedule would still be at 3/5 of the gap."""
    case = CASES["case:P18"]
    sid, opening, counter = _p18_thread()
    asks = [6.00] * 6
    plain = _comp(rounds=5, estimates={}, meso=False)
    plain_prices, _ = _play(plain, case, sid, opening, counter, asks)
    trace = Trace()
    fast = _comp(rounds=5, estimates={}, meso=False, tracer=trace)
    clock = Clock(480.0)  # 480 s wave, guard 240 s, 60 s rounds -> 4, 3, 2 rounds available
    clock.wire(fast)
    fast_prices, _ = _play(fast, case, sid, opening, counter, asks, clock, round_s=60.0)
    comp = trace.kinds("compression")
    assert comp and comp[0]["rounds_available"] == 4 and comp[0]["moves_needed"] == 6
    assert [c["rounds_available"] for c in comp[:3]] == [4, 3, 2]
    assert [round(c["k_eff"], 2) for c in comp[:3]] == [1.67, 3.0, 5.0]  # fractions 1/3, 3/5, 1 of the gap
    ask_on_ours = fast_prices[2]
    # third move (rounds_available - 1 = 3 at the first decision): at the supplier's ask on our terms
    assert fast_prices[2] >= fast_prices[1] >= fast_prices[0]
    assert plain_prices[2] < ask_on_ours and plain_prices[5] == ask_on_ours  # plain path: six moves
    assert "compressed" in [r for r in trace.kinds("offer")][0]["reason"]
    # then the gap is closed (the match on our terms), never a step back
    assert fast_prices[3] == ask_on_ours or isinstance(fast_prices[3], dict)


def test_compression_is_inactive_without_a_cap_and_when_rounds_fit():
    case = CASES["case:P18"]
    sid, opening, counter = _p18_thread()
    asks = [6.00, 5.95, 5.90, 5.85, 5.80, 5.80]
    plain = _comp(rounds=5, estimates={}, meso=False)
    a, _ = _play(plain, case, sid, opening, counter, asks)
    trace = Trace()
    wide = _comp(rounds=5, estimates={}, meso=False, tracer=trace)
    Clock(10_000.0, 60.0).wire(wide)  # a long wave: floor((10000 - 240) / 60) = 162 rounds
    b, _ = _play(wide, case, sid, opening, counter, asks)
    assert a == b and not trace.kinds("compression") and not trace.kinds("time_guard")


def _rfq_threads(case, body, hold=False, rounds_sent=1):
    """Leader a opened 32.00/30d and wrote `body`; we countered `rounds_sent` times at 29.0x/90d and a
    answered each with a 0.50 step - except the last answer, which repeats its price when `hold`; b
    opened 34.00."""
    a, b = case["suppliers"][:2]
    first = {**msg("open", ("offer:a-1", {**T35, "unit_price": 32.0})), "body": body}
    events, price = [first], 32.0
    for i in range(rounds_sent):
        events.append(ours({**T35, "unit_price": 29.0 + 0.3 * i, "payment_days": 90}))
        if not (hold and i == rounds_sent - 1):
            price = round(price - 0.5, 2)
        events.append({**msg("open", (f"offer:a-{i + 2}", {**T35, "unit_price": price})), "body": body})
    return {a: events, b: [msg("open", ("offer:b-1", {**T35, "unit_price": 34.0}))]}


def _rfq_agent(**cfg):
    policy = PolicyConfig.from_dict({**V3, "rfq_undercut_reanchor": True, "rfq_fast_payment_reanchor": True,
                                     "compressed_schedule": True, **cfg})
    return PackageAgent(policy=policy, estimates={}, meso=False, model_assist=False)


def test_fast_payment_chip_under_compression_fires_on_the_first_hold_by_round_3():
    """rounds_available <= 5: the 14-day chip may come on the leader's first hold (not only at the undercut
    re-anchor) if it wrote that faster payment is welcome and the sheet is C-cheaper - but never before a
    hold or re-anchor, never for a supplier that did not ask, and not after our round-3 message."""
    case = CASES["case:P05"]
    a = case["suppliers"][0]
    # Round 1 (no hold yet, the supplier only opened): 90 d, no chip even with 4 rounds available.
    agent = Clock(480.0, 60.0).wire(_rfq_agent())  # floor(240 / 60) = 4 rounds available (<= 5)
    first = agent.propose(case, _rfq_threads(case, ASKED, rounds_sent=0), a)["message"]
    assert first["term_sheets"][0]["terms"]["payment_days"] == 90 and "faster payment" not in first["body"]
    # Round 2 on the first hold: the chip fires with the compressed note (the compressed price is still
    # below the ask, so the 14-day sheet is C-cheaper for us than the standing 32.00/30 d).
    agent = Clock(480.0, 60.0).wire(_rfq_agent())
    move = agent.propose(case, _rfq_threads(case, ASKED, hold=True, rounds_sent=1), a)["message"]
    assert move["term_sheets"][0]["terms"]["payment_days"] == 14 and "14 days" in move["body"]
    assert move["term_sheets"][0]["terms"]["unit_price"] < 32.0 and a in agent.fast_payment_traded
    # A fresh concession (no hold) at round 2: no chip.
    agent = Clock(480.0, 60.0).wire(_rfq_agent())
    step = agent.propose(case, _rfq_threads(case, ASKED, hold=False, rounds_sent=1), a)["message"]
    assert step["term_sheets"][0]["terms"]["payment_days"] == 90 and "faster payment" not in step["body"]
    # The supplier never asked: no chip on a hold.
    agent = Clock(480.0, 60.0).wire(_rfq_agent())
    silent = agent.propose(case, _rfq_threads(case, "We hold this price.", hold=True, rounds_sent=1), a)["message"]
    assert silent["term_sheets"][0]["terms"]["payment_days"] == 90
    # Round 3 on a hold: still allowed (the latest round).
    agent = Clock(480.0, 60.0).wire(_rfq_agent())
    r3 = agent.propose(case, _rfq_threads(case, ASKED, hold=True, rounds_sent=2), a)["message"]
    assert r3["term_sheets"][0]["terms"]["payment_days"] == 14
    # Round 4 on a hold: too late for the compressed rule (the re-anchor path alone may still use it).
    agent = Clock(480.0, 60.0).wire(_rfq_agent())
    r4 = agent.propose(case, _rfq_threads(case, ASKED, hold=True, rounds_sent=3), a)["message"]
    assert r4["term_sheets"][0]["terms"]["payment_days"] == 90
    # Without a cap the compressed rule never applies: a hold at round 2 stays at 90 d (byte-identical).
    r2_plain = _rfq_agent().propose(case, _rfq_threads(case, ASKED, hold=True, rounds_sent=1), a)["message"]
    assert r2_plain["term_sheets"][0]["terms"]["payment_days"] == 90 and "faster payment" not in r2_plain["body"]
    # Plenty of rounds available (> 5): the chip waits for the normal re-anchor stage.
    agent = Clock(10_000.0, 60.0).wire(_rfq_agent())
    wide = agent.propose(case, _rfq_threads(case, ASKED, hold=True, rounds_sent=1), a)["message"]
    assert wide["term_sheets"][0]["terms"]["payment_days"] == 90


def test_final_offer_is_never_countered_when_the_counter_cannot_be_reaped():
    """A final offer with fewer than two rounds available: no `_final_counter` (and the guard never
    counters a final either); the move is the close the evaluator resolves."""
    case = CASES["case:P18"]
    sid, opening, counter = _p18_thread()
    events = [opening, ours({**counter, "unit_price": 5.50}),
              msg("final_offer", ("offer:final", {**counter, "unit_price": 6.00}))]
    trace = Trace()
    agent = _comp(rounds=5, estimates={}, meso=False, tracer=trace)
    plain = agent.propose(case, {sid: events}, sid)
    assert plain.get("message", {}).get("term_sheets")  # without a cap: the one counter to a final
    trace.rows.clear()
    agent = _comp(rounds=5, estimates={}, meso=False, tracer=trace)
    Clock(480.0, 85.0).wire(agent)  # 2 rounds available: the counter's round could still be reaped
    assert agent.propose(case, {sid: events}, sid).get("message", {}).get("term_sheets")
    trace.rows.clear()
    agent = _comp(rounds=5, estimates={}, meso=False, tracer=trace)
    Clock(395.0, 85.0).wire(agent)  # 1 round available: never counter
    move = agent.propose(case, {sid: events}, sid)
    assert move.get("close") and trace.kinds("final_counter_skipped")
    assert not [r for r in trace.kinds("offer")]
    # under the guard (time left < 240 s) the same final is accepted, never countered
    agent = _comp(rounds=5, estimates={}, meso=False, tracer=trace)
    Clock(200.0, 85.0).wire(agent)
    move = agent.propose(case, {sid: events}, sid)
    assert move.get("close") and "accept" in move["reason"]


@pytest.fixture
def no_final(monkeypatch):
    monkeypatch.setattr(kit_sim, "FINAL_ROUND", 99)


async def _run(arena, clock, agent, tmp_path, tracer=None):
    close, calls = recording()
    t0 = clock.time()
    deadline = t0 + CAP_S
    runner = CaseRunner(arena, "case:S01", agent, Journal(tmp_path / "j.jsonl"), clock=clock, close_fn=close,
                        deadline=lambda: deadline, tracer=tracer)
    result = await runner.run()
    return result, calls, clock.time() - t0, runner


async def test_compressed_schedule_closes_before_cap_minus_20s(tmp_path, no_final):
    """S01, 12-step schedule, 50 s replies, 480 s cap: compression (guard on) reaches the supplier's
    ask and the deal well before cap - 20 s; the guard never has to fire; no wave_cap."""
    clock, trace = ScaledClock(), Trace()
    arena = PatientArena(clock, {"sup:70270": REPLY_S})
    agent = _comp(rounds=12, tracer=trace)
    result, calls, took, runner = await _run(arena, clock, agent, tmp_path, tracer=trace)
    assert result["deal"] and result["ended"] and result.get("end_reason") != "wave_cap"
    assert calls == ["sup:70270 agreed"] and "wave cap" not in calls
    assert CAP_S - took >= 20 and CAP_S - took >= 2 * runner.st.slowest_round_s
    comp = trace.kinds("compression")
    assert comp and all(c["rounds_available"] <= 4 for c in comp)  # 480 s / (240 s guard, >= 60 s rounds)
    assert trace.kinds("offer")[-1]["reason"].startswith(("round", "gap closed")) or trace.kinds("offer")
    assert result["thread_timeouts"] == {"sup:70270": 0}


async def test_compressed_schedule_alone_still_closes_before_the_cap(tmp_path, no_final):
    """Guard off, compression on: the schedule is at the ask by round rounds_available - 1 and the sim
    agrees - the case ends by agreement before cap - 20 s without the guard or the watchdog."""
    clock, trace = ScaledClock(), Trace()
    arena = PatientArena(clock, {"sup:70270": REPLY_S})
    agent = _comp(rounds=12, tracer=trace)
    agent.time_guard_rounds = 0  # compression sizes itself on the guard window even when the guard is off
    assert agent.time_guard() is None
    result, calls, took, _ = await _run(arena, clock, agent, tmp_path, tracer=trace)
    assert result["deal"] and calls == ["sup:70270 agreed"] and CAP_S - took >= 20
