"""Live Final zero-score guards: auto runner routing, resilient case-list polling, decision fallback.

Fake clients, fake errors and a fake clock only; no network.
"""

import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from arena_kit.client import ArenaError
from test_evaluator import RFQ, msg
from test_runner import ScaledClock, SimArena

from negotiator import cli, play, runner
from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig
from negotiator.runner import CaseRunner, SharedPace, fallback_propose, run_set, run_waves
from negotiator.state import Journal

V3 = Path(__file__).resolve().parents[1] / "configs" / "score-push-v3.json"
CHEAP = {"unit_price": 15.0, "payment_days": 60, "lead_time_days": 35, "incoterm": "DAP"}  # beats alt 19.9
DEAR = {"unit_price": 25.0, "payment_days": 60, "lead_time_days": 35, "incoterm": "DAP"}
OURS = {"unit_price": 17.0, "payment_days": 60, "lead_time_days": 35, "incoterm": "DAP"}


def one_supplier(round_limit=10):
    case = copy.deepcopy(RFQ)
    case["suppliers"], case["round_limit"] = ["sup:J"], round_limit
    return case


def buyer(terms):
    return {"from": "buyer", "subject": "Shafts", "body": "Our proposal.", "term_sheets": [{"terms": dict(terms)}]}


class Crashing:
    """An agent whose decision step always fails."""

    tracer = None

    def decide(self, case, threads):
        raise RuntimeError("boom")

    def propose(self, case, threads, sid):
        raise RuntimeError("boom")


# -- 3. decision-step fallback (serial play_case) ------------------------------------------------


class FakeTable:
    def __init__(self, case, threads, replies=()):
        self.case, self.threads, self.replies = case, threads, list(replies)
        self.sent, self.closed, self.session_id, self.done = [], [], None, None

    def open(self, case_id):
        return self.case, self.threads

    def send(self, sid, message):
        self.sent.append((sid, message))
        return self.replies.pop(0)

    def close(self, sid, message):
        self.closed.append((sid, message))
        return {"deal": message["action"]["type"] == "accept", "score": 0.5}

    def attachment(self, attachment_id):
        raise AssertionError("no attachments")

    def result(self):
        return {"deal": False}


def test_serial_crash_accepts_best_eligible_sheet():
    case = one_supplier()
    table = FakeTable(case, {"sup:J": [msg("open", ("o:1", CHEAP))]})
    result = play.play_case(table, case["case_id"], Crashing())
    assert table.closed == [("sup:J", {"action": {"type": "accept", "term_sheet_id": "o:1"}})]
    assert result["deal"] is True and not table.sent


def test_serial_crash_repeats_last_offer_and_never_counters_a_final_offer():
    case = one_supplier()
    threads = {"sup:J": [msg("open", ("o:0", DEAR)), buyer(OURS), msg("open", ("o:1", DEAR))]}
    table = FakeTable(case, threads, replies=[msg("final_offer", ("o:2", DEAR))])
    result = play.play_case(table, case["case_id"], Crashing())
    assert [(s, m["term_sheets"]) for s, m in table.sent] == [("sup:J", [{"terms": OURS}])]
    assert table.closed == [("sup:J", {"action": {"type": "walk_away"}})]  # final offer: no counter
    assert result["deal"] is False


def test_serial_crash_without_round_left_walks_away():
    case = one_supplier(round_limit=1)
    threads = {"sup:J": [msg("open", ("o:0", DEAR)), buyer(OURS), msg("open", ("o:1", DEAR))]}
    table = FakeTable(case, threads)
    play.play_case(table, case["case_id"], Crashing())
    assert not table.sent and table.closed == [("sup:J", {"action": {"type": "walk_away"}})]


def test_serial_invalid_decision_uses_the_fallback():
    class Broken(Crashing):
        def decide(self, case, threads):
            return {"supplier_id": "sup:unknown", "message": None}

    case = one_supplier()
    table = FakeTable(case, {"sup:J": [msg("open", ("o:1", CHEAP))]})
    play.play_case(table, case["case_id"], Broken())
    assert table.closed[0][1]["action"]["type"] == "accept"


def test_fallback_skips_must_have_violations():
    case = one_supplier()
    late = {**CHEAP, "lead_time_days": 49}  # must-have lead_time_days <= 42
    d = play.fallback_decision(case, {"sup:J": [msg("open", ("o:1", late))]})
    assert d["message"]["action"]["type"] == "walk_away"  # no buyer offer to repeat yet


# -- 3. decision-step fallback (async worker) ----------------------------------------------------


def test_async_fallback_propose_accept_repeat_park():
    case = one_supplier()
    assert fallback_propose(Crashing(), case, {"sup:J": [msg("open", ("o:1", CHEAP))]}, "sup:J")[0] == "close"
    open_thread = {"sup:J": [msg("open", ("o:0", DEAR)), buyer(OURS), msg("open", ("o:1", DEAR))]}
    kind, what = fallback_propose(Crashing(), case, open_thread, "sup:J")
    assert kind == "send" and what["term_sheets"] == [{"terms": OURS}]
    final = {"sup:J": [msg("open", ("o:0", DEAR)), buyer(OURS), msg("final_offer", ("o:1", DEAR))]}
    assert fallback_propose(Crashing(), case, final, "sup:J")[0] == "park"


@pytest.mark.parametrize("good_calls", [0, 3])
async def test_async_worker_crash_still_ends_the_session(tmp_path, good_calls):
    class Flaky(PackageAgent):
        calls = 0

        def propose(self, case, threads, sid):
            Flaky.calls += 1
            if Flaky.calls > good_calls:
                raise RuntimeError("boom")
            return super().propose(case, threads, sid)

    clock = ScaledClock()
    arena = SimArena(clock)
    r = await CaseRunner(arena, "case:S02", Flaky(estimates={}), Journal(tmp_path / "j.jsonl"), clock=clock).run()
    assert r["ended"] is True
    assert set(r["thread_timeouts"].values()) == {0}


# -- 1. auto runner ------------------------------------------------------------------------------


def test_async_runner_accepts_the_v3_policy_agent(tmp_path):
    agent = PackageAgent(policy=PolicyConfig.load(V3), estimates={})
    assert agent.package_advisor is not None
    CaseRunner(object(), "case:S02", agent, Journal(tmp_path / "j.jsonl"))
    assert agent.package_advisor is None


class ListArena:
    def __init__(self, cases):
        self.list = cases

    async def cases(self, set_):
        return self.list


SINGLE = {"case_id": "case:D01", "suppliers": ["sup:A"], "hosted": True}
MULTI = {"case_id": "case:D02", "suppliers": ["sup:A", "sup:B"], "hosted": True}


async def test_run_set_auto_routes_by_supplier_count(monkeypatch, tmp_path):
    routed = []

    async def serial(case, agent, deadline):
        routed.append(("serial", case["case_id"]))
        return {"score": 1}

    async def fake_async(arena, case_id, agent, journal, **kw):
        routed.append(("async", case_id))
        return {"score": 2}

    monkeypatch.setattr(runner, "play_case", fake_async)
    out = await run_set(ListArena([SINGLE, MULTI]), "sandbox", object, Journal(tmp_path / "j.jsonl"), serial=serial)
    assert sorted(routed) == [("async", "case:D02"), ("serial", "case:D01")]
    assert out == {"case:D01": {"score": 1}, "case:D02": {"score": 2}}


def test_serial_runner_uses_dedicated_pool(monkeypatch):
    seen = []

    def fake_play(table, case_id, agent, deadline):
        seen.append((type(table).__name__, case_id, deadline()))
        return {"score": 1}

    monkeypatch.setattr(play, "play_case", fake_play)
    with ThreadPoolExecutor(1) as pool:
        run = runner.serial_runner(object(), pool)
        assert asyncio.run(run(SINGLE, object(), lambda: 42.0)) == {"score": 1}
    assert seen == [("RemoteTable", "case:D01", 42.0)]


def test_shared_pace_spaces_sync_and_async_calls():
    now = [0.0]
    pace = SharedPace(rate=8.0, clock=lambda: now[0])
    assert [pace.reserve() for _ in range(3)] == [0.0, 0.125, 0.25]
    now[0] = 10.0
    assert pace.reserve() == 0.0


def _cli(monkeypatch, tmp_path, argv):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "_run_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "ArenaClient", lambda: type("Client", (), {"practice_remaining": None})())
    seen = {}

    def fake_run_async(args, factory, *rest):
        seen["args"], seen["agent"] = args, factory()
        return {"case:T": {"score": 0.5, "deal": True, "ended": True}}

    monkeypatch.setattr(cli, "run_async", fake_run_async)
    monkeypatch.setattr(cli, "play_waves", lambda *a, **k: pytest.fail("final must not use the serial-only loop"))
    assert cli.main(argv) == 0
    return seen


def test_final_cli_defaults_to_auto_runner_and_v3_policy(monkeypatch, tmp_path):
    seen = _cli(monkeypatch, tmp_path, ["run", "--set", "final"])
    assert seen["args"].runner == "auto"
    assert Path(seen["args"].policy_config) == V3
    assert seen["agent"].policy == PolicyConfig.load(V3)
    assert '"runner": "auto"' in (tmp_path / "trace.jsonl").read_text()


def test_cli_auto_passes_explicit_policy_config(monkeypatch, tmp_path):
    other = Path(__file__).resolve().parents[1] / "configs" / "score-push-v2.json"
    seen = _cli(monkeypatch, tmp_path, ["run", "--set", "sandbox", "--runner", "auto", "--policy-config", str(other)])
    assert seen["args"].runner == "auto" and seen["agent"].policy == PolicyConfig.load(other)


# -- 2. final case-list polling ------------------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.now, self.sleeps = 1000.0, []

    def time(self):
        return self.now

    async def sleep(self, s):
        self.sleeps.append(s)
        self.now += s
        await asyncio.sleep(0)


class FlakyFinal:
    """Fails in every way the network can before and between waves, then plays one wave."""

    def __init__(self, case):
        self.case, self.calls = case, 0
        self.script = [ArenaError(500, "server"), httpx.ConnectError("wifi"), ArenaError(403, "not started"),
                       ArenaError(429, "slow down"), [{"bad": "row"}], ValueError("bad json"),
                       [{**case, "open": True, "wave": 1, "seconds_left": 300}],
                       ArenaError(502, "gateway"), [{**case, "open": False, "wave": 1}]]

    async def cases(self, set_):
        assert set_ == "final"
        step = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(step, Exception):
            raise step
        return step


async def test_run_waves_survives_poll_errors_and_backs_off(tmp_path):
    clock, played = FakeClock(), []

    async def serial(case, agent, deadline):
        played.append((case["case_id"], deadline()))
        return {"score": 1}

    arena = FlakyFinal(SINGLE)
    out = await run_waves(arena, object, Journal(tmp_path / "j.jsonl"), waves=1, poll_s=3.0,
                          clock=clock, serial=serial, rng=lambda: 0.5)
    assert out == {"case:D01": {"score": 1}}
    assert played and played[0][1] is not None
    # 500 and network errors back off (3 * 2, 3 * 4); 403 is "not started": normal poll.
    assert clock.sleeps[:3] == [6.0, 12.0, 3.0]
    assert max(clock.sleeps) <= play.POLL_BACKOFF_MAX_S * 1.5


def test_play_waves_survives_poll_errors(monkeypatch):
    class Client:
        def __init__(self):
            self.inner = FlakyFinal(SINGLE)

        def cases(self, set_):
            return asyncio.run(self.inner.cases(set_))

    monkeypatch.setattr(play, "play_case", lambda table, case_id, agent, deadline: {"score": 1})
    sleeps = []
    out = play.play_waves(Client(), object, waves=1, parallel=2, poll=0.0, sleep=sleeps.append, rng=lambda: 0.5)
    assert out == {"case:D01": {"score": 1}}
    assert len(sleeps) >= 9


def test_poll_backoff_is_capped_and_jittered():
    assert play.poll_backoff(3.0, 1, lambda: 0.0) == 3.0
    assert play.poll_backoff(3.0, 1, lambda: 1.0) == 9.0
    assert play.poll_backoff(3.0, 50, lambda: 0.5) == play.POLL_BACKOFF_MAX_S
