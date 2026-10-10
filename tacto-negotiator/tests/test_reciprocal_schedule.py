"""Opt-in `reciprocal_schedule`: while the supplier is open, moving and more than two of our moves
ahead, our step is at most its last step (a token step when it holds) and we stay outside the closing
gap of its ask; from N-2 on, on finals and once the gap is closed, today's schedule and close logic
run unchanged."""

import copy
import json
from pathlib import Path

import pytest
from arena_kit.play import moves_left
from test_evaluator import msg, ours

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "configs/score-push-v3.json").read_text())
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
THREAD = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
OPENING = THREAD["messages"][0]  # carries the quote PDF the agent reads standard terms from
COUNTER_TERMS = THREAD["messages"][2]["term_sheets"][0]["terms"]  # supplier's package on our terms


@pytest.fixture(autouse=True, scope="module")
def _cache_data_package():
    """Every fresh agent rebuilds the evidence context and dossiers (~0.7 s); cache them per case so
    the many side-by-side agents below stay fast. Prices never depend on these objects."""
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
    policy = PolicyConfig.from_dict({**BASE, "reciprocal_schedule": flag})
    return PackageAgent(policy=policy, estimates={}, meso=False, tracer=tracer)


def _price(move):
    message = move.get("message") or {}
    sheets = message.get("term_sheets") or [{}]
    return (sheets[0].get("terms") or {}).get("unit_price")


def _opening(price):
    first = copy.deepcopy(OPENING)
    first["term_sheets"][0]["terms"]["unit_price"] = price
    return first


def _supplier(i, price, status="open"):
    terms = {**COUNTER_TERMS, "unit_price": price}
    return {"from": "sales", "status": status, "term_sheets": [{"term_sheet_id": f"offer:sim-{i}", "terms": terms}]}


def _simulate(case, agent, asks, statuses=None):
    """Feed the supplier's successive asks; return (rows, events) with one row per buyer move:
    (ask_before_move, our_price, moves_left_before_move, action)."""
    sid = case["suppliers"][0]
    events, rows = [_opening(asks[0])], []
    for i, ask in enumerate(asks[1:], 1):
        left = moves_left(case, events)
        move = agent.decide(case, {sid: events})
        rows.append((asks[i - 1], _price(move), left, move["message"].get("action")))
        if move["message"].get("action"):
            break
        events.append({"from": "buyer", **move["message"]})
        events.append(_supplier(i, ask, (statuses or {}).get(i, "open")))
    return rows, events


def _replay(agent):
    case, sid = CASES["case:P18"], THREAD["supplier_id"]
    sent, out = [], []
    for i, message in enumerate(THREAD["messages"]):
        if message.get("from") != "buyer":
            continue
        it = iter(sent)
        history = [next(it) if e.get("from") == "buyer" else e for e in THREAD["messages"][:i]]
        move = agent.decide(case, {sid: history})["message"]
        out.append(move.get("term_sheets") or move.get("action"))
        sent.append({"from": "buyer", **move})
    return out


def test_flag_off_replays_the_retained_p18_thread_exactly():
    expected = [m.get("term_sheets") or m.get("action") for m in THREAD["messages"] if m.get("from") == "buyer"]
    assert _replay(_agent(False)) == expected
    # The retained supplier moved 0.10 per round, more than the schedule's own steps: the reciprocal
    # cap never binds, so the flag reproduces the same thread too (it never raises a price).
    assert _replay(_agent(True)) == expected


@pytest.mark.parametrize("case_id", ["case:P18", "case:P08"])
def test_flag_on_steps_follow_the_supplier_then_token_steps_while_it_holds(case_id):
    case = CASES[case_id]
    trace = Trace()
    agent = _agent(True, tracer=trace)
    asks = [6.10, 6.00, 5.90, 5.80, 5.80, 5.80, 5.80, 5.80, 5.80, 5.80]
    rows, _ = _simulate(case, agent, asks)
    prices = [p for _, p, _, _ in rows if p is not None]
    assert prices == sorted(prices)  # never backtracks
    recip = [r for r in trace.rows if r.get("kind") == "reciprocal"]
    assert recip and all(r["moves_left"] > 2 for r in recip)
    gap = {r["price"]: max(r["ask"] * agent.close_gap, 0.01) for r in recip}
    for r in recip:
        assert r["price"] <= round(r["ask"] - gap[r["price"]], 2) + 1e-9  # never within the gap of its ask
        assert r["price"] <= r["scheduled"] + 1e-9  # never above the default schedule
        if not r["held"]:
            assert r["step"] <= r["their_step"] + 1e-6  # our step <= its last step while it moves
        else:
            assert 0.01 - 1e-9 <= r["step"] <= max(0.01, round(r["ask"] * 0.002, 2)) + 1e-9  # token step
    moving = [r for r in recip if not r["held"]]
    held = [r for r in recip if r["held"]]
    assert len(moving) >= 2 and len(held) >= 3
    # the opening is on the supplier's standard terms, so its first step is measured on our terms `n`
    # (P08: 0.05); from the second counter on, both sheets share the package and the step is the 0.10
    assert moving[0]["their_step"] <= 0.10 + 1e-6
    assert all(abs(r["their_step"] - 0.10) < 1e-6 for r in moving[1:])
    # once it holds, our rounds before N-2 are token steps only - no convergence on our own
    assert all(abs(r["step"] - 0.01) < 1e-9 for r in held)


def test_flag_on_never_exceeds_the_default_schedule_and_matches_it_from_n_minus_2():
    case, sid = CASES["case:P18"], "sup:70740"
    asks = [6.10, 6.00, 5.90, 5.80] + [5.80] * 6
    rows_on, _ = _simulate(case, _agent(True), asks)
    rows_off, _ = _simulate(case, _agent(False), asks)
    for (_, p_on, _, _), (_, p_off, _, _) in zip(rows_on, rows_off, strict=False):
        if p_on is not None and p_off is not None:
            assert p_on <= p_off + 1e-9
    # identical history fed to both agents from moves_left <= 2 on: the default schedule verbatim
    events = [_opening(6.10)]
    ask = 6.00
    for i in range(1, 9):  # 8 buyer offers -> moves_left == 2
        price = round(5.37 + 0.01 * (i - 1), 2)
        events.append(ours({**COUNTER_TERMS, "index_clause": None, "unit_price": price}))
        events.append(_supplier(i, ask))
    assert moves_left(case, events) == 2
    on, off = _agent(True).decide(case, {sid: events}), _agent(False).decide(case, {sid: events})
    assert on == off and _price(on) is not None
    # at moves_left == 1 the coordinator closes: the standing sheet beats the quote alternative
    events.append(ours({**COUNTER_TERMS, "index_clause": None, "unit_price": _price(on)}))
    events.append(_supplier(9, ask))
    assert moves_left(case, events) == 1
    on, off = _agent(True).decide(case, {sid: events}), _agent(False).decide(case, {sid: events})
    assert on == off and on["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:sim-9"}


def test_reciprocal_only_while_open_moving_and_outside_the_gap():
    case, sid = CASES["case:P18"], "sup:70740"
    trace = Trace()
    agent = _agent(True, tracer=trace)
    # one round in: the supplier jumps to within the closing gap of our last price -> gap-closed branch
    events = [_opening(6.10)]
    events.append({"from": "buyer", **agent.decide(case, {sid: events})["message"]})
    last = _price({"message": events[-1]})
    events.append(_supplier(1, round(last + 0.01, 2)))
    move = agent.decide(case, {sid: events})
    assert not [r for r in trace.rows if r.get("kind") == "reciprocal"]
    assert move == _agent(False).decide(case, {sid: events})
    # a supplier that raised its ask counts as holding: token step, never a larger one
    trace.rows.clear()
    events = [_opening(6.10)]
    events.append({"from": "buyer", **agent.decide(case, {sid: events})["message"]})
    events.append(_supplier(1, 6.00))
    events.append({"from": "buyer", **agent.decide(case, {sid: events})["message"]})
    events.append(_supplier(2, 6.05))
    agent.decide(case, {sid: events})
    row = [r for r in trace.rows if r.get("kind") == "reciprocal"][-1]
    assert row["held"] and row["their_step"] == 0 and abs(row["step"] - 0.01) < 1e-9


def test_final_offer_moves_are_identical_with_and_without_the_flag():
    case, sid = CASES["case:P18"], "sup:70740"
    asks = [6.10, 6.00, 5.90, 5.80]
    _, events = _simulate(case, _agent(True), asks)
    for final_price in (5.80, 5.50, 5.42):
        history = [*events[:-1], _supplier(9, final_price, status="final_offer")]
        on, off = _agent(True).decide(case, {sid: history}), _agent(False).decide(case, {sid: history})
        assert on == off
    # today's `_final_counter`: one counter at its price on our terms when the final leads by enough,
    # a plain accept when the counter is not worth the walk risk - unchanged by the flag
    history = [*events[:-1], _supplier(9, 5.80, status="final_offer")]
    move = _agent(True).decide(case, {sid: history})
    assert _price(move) == 5.80 and move["message"]["term_sheets"][0]["terms"]["index_clause"] is None
    history = [*events[:-1], _supplier(9, 5.50, status="final_offer")]
    move = _agent(True).decide(case, {sid: history})
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:sim-9"}
    # once the supplier walked, nothing from the schedule runs: both agents give the same close
    history = [*events[:-1], _supplier(9, 5.80, status="walked_away")]
    assert _agent(True).decide(case, {sid: history}) == _agent(False).decide(case, {sid: history})
    assert _agent(True).decide(case, {sid: history})["message"]["action"] == {"type": "walk_away"}


def test_rfq_beat_final_cap_path_is_unaffected():
    case = CASES["case:P05"]
    leader, rival = case["suppliers"][:2]
    terms = {"unit_price": 32.5, "payment_days": 60, "lead_time_days": 35}
    threads = {
        leader: [msg("open", ("offer:lead-1", {**terms, "unit_price": 34.5})), ours({**terms, "unit_price": 30.0}),
                 msg("final_offer", ("offer:lead-2", terms))],
        rival: [msg("open", ("offer:riv-1", {**terms, "unit_price": 36.0})), ours({**terms, "unit_price": 30.5}),
                msg("open", ("offer:riv-2", {**terms, "unit_price": 35.0}))],
    }
    trace = Trace()
    on, off = _agent(True, tracer=trace), _agent(False)
    # the leader's final stands; the rival is asked to beat it (cap_c path): no reciprocal step at all
    first_on, first_off = on.decide(case, copy.deepcopy(threads)), off.decide(case, copy.deepcopy(threads))
    assert first_on == first_off and first_on["supplier_id"] == rival
    assert _price(first_on) < terms["unit_price"]
    assert on.beat_asked == off.beat_asked == {rival: "offer:lead-2"}
    assert not [r for r in trace.rows if r.get("kind") == "reciprocal"]
