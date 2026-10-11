"""Async runner against arena_kit.sim on a compressed clock (60 s rule on, injected reply delays)."""

import asyncio
import time

import httpx
import pytest
from arena_kit.client import ArenaError
from arena_kit.sim import Fail, Sim, load_cases

from negotiator import runner
from negotiator.agent import PackageAgent
from negotiator.client import AsyncArena, RateLimiter, UncertainOutcome
from negotiator.evaluator import close_decision
from negotiator.runner import CaseRunner, Clock, run_set
from negotiator.state import Journal

SCALE = 0.004  # 1 simulated second = 4 ms; the 60 s rule takes 0.24 s


class ScaledClock(Clock):
    def __init__(self, scale=SCALE):
        self.scale, self.t0, self.m0 = scale, time.time(), time.monotonic()

    def time(self):
        return self.t0 + (time.monotonic() - self.m0) / self.scale

    async def sleep(self, s):
        await asyncio.sleep(max(0.0, s) * self.scale)


class SimArena:
    """AsyncArena's interface over the kit simulator: X-Move-Id idempotency, supplier reply
    delays that do not count against the buyer (as hosted), and one-shot fault injection."""

    def __init__(self, clock, delays=None):
        self.clock, self.delays = clock, delays or {}
        self.sim = Sim(load_cases(), clock=clock.time)
        self.team, self.replies, self.opens, self.posts = "t", {}, 0, []
        self.fail_next_close = None  # an ArenaError status to raise once on the next close POST
        self.lose_reply = False  # next send lands but the reply is lost (UncertainOutcome)

    def _do(self, fn, *a):
        try:
            return fn(self.team, *a)
        except Fail as e:
            raise ArenaError(e.status, e.detail) from None

    async def cases(self, set_):
        return [{**c, "hosted": True} for c in self.sim.cases.values()]

    async def open_session(self, case_id, move_id):
        if move_id in self.replies:
            return self.replies[move_id]
        self.opens += 1
        r = self.replies[move_id] = self._do(self.sim.open, case_id)
        return r

    async def send(self, session_id, supplier_id, message, move_id):
        self.posts.append((move_id, supplier_id, message))
        if move_id in self.replies:
            return self.replies[move_id]
        if message.get("action") and self.fail_next_close:
            status, self.fail_next_close = self.fail_next_close, None
            raise ArenaError(status, "injected")
        reply = self._do(self.sim.message, session_id, supplier_id, message)
        self.replies[move_id] = reply
        if not message.get("action") and "result" not in reply:
            await self.clock.sleep(self.delays.get(supplier_id, 0))
            th = self.sim.sessions[session_id]["threads"][supplier_id]
            if not th["closed"]:
                th["last_at"] = self.clock.time()  # the buyer's 60 s start at the supplier's reply
            if self.lose_reply:
                self.lose_reply = False
                raise UncertainOutcome(move_id, ConnectionError("reply lost"))
        return reply

    async def session(self, session_id):
        return self._do(self.sim.state, session_id)

    async def thread(self, session_id, supplier_id):
        return self._do(self.sim.thread, session_id, supplier_id)

    async def attachment(self, session_id, attachment_id):
        return self._do(self.sim.attachment, session_id, attachment_id)[0]


def recording(fn=close_decision):
    calls = []

    def close(case, threads, estimates=None, reason=""):
        calls.append(reason)
        return fn(case, threads, estimates, reason)

    return close, calls


def timeouts(arena, sid):
    return {k: len(t["late"]) for k, t in arena.sim.sessions[sid]["threads"].items()}


@pytest.mark.parametrize("slots", [1, None])
async def test_two_thread_rfq_slow_replies_no_timeouts(tmp_path, slots):
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 30, "sup:70360": 50})
    close, calls = recording()
    r = await CaseRunner(arena, "case:S02", PackageAgent(), Journal(tmp_path / "j.jsonl"),
                         clock=clock, close_fn=close, send_slots=slots).run()
    assert r["deal"] and r["score"] > 0
    assert set(timeouts(arena, r["session_id"]).values()) == {0}
    assert r["thread_timeouts"] == {"sup:70340": 0, "sup:70360": 0}
    assert calls, "every close goes through close_decision"
    rounds = {k: t["round"] for k, t in arena.sim.sessions[r["session_id"]]["threads"].items()}
    assert min(rounds.values()) >= 2  # both threads were worked, not just one


async def test_serial_waiting_would_time_out(tmp_path):
    """Control: waiting for one supplier's 50 s reply before answering the other costs a timeout."""
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 50, "sup:70360": 50})
    opened = await arena.open_session("case:S02", "m0")
    sid = opened["session_id"]
    sheet = {"terms": {"unit_price": 1.0}}
    case = opened["case"]
    sheet["terms"] = {f: (case["term_options"].get(f) or [None])[0] for f in case["negotiable"][1:]} | {
        "unit_price": 1.0}
    await clock.sleep(15)
    await arena.send(sid, "sup:70340", {"body": "x", "term_sheets": [sheet]}, "m1")
    with pytest.raises(ArenaError) as e:
        await arena.send(sid, "sup:70360", {"body": "x", "term_sheets": [sheet]}, "m2")
    assert e.value.status == 409 and "late" in e.value.detail


class OfferAgent:
    """Stub agent: offers the supplier's standing price (sim agrees) on `fast`, lowballs `slow`."""

    def __init__(self, fast):
        self.fast = fast

    def propose(self, case, threads, sid):
        last = threads[sid][-1]
        if last.get("from") == "buyer":
            return None
        price = last["term_sheets"][0]["terms"]["unit_price"]
        terms = {f: (case["term_options"].get(f) or [None])[0] for f in case["negotiable"][1:]}
        price = price if sid == self.fast else round(price * 0.5, 2)
        return {"supplier_id": sid, "message": {"subject": "s", "body": "Offer.",
                                                "term_sheets": [{"terms": {**terms, "unit_price": price}}]}}


async def test_pending_request_at_close(tmp_path):
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 1, "sup:70360": 55})
    close, calls = recording()
    t0 = clock.time()
    r = await CaseRunner(arena, "case:S02", OfferAgent("sup:70340"), Journal(tmp_path / "j.jsonl"),
                         clock=clock, close_fn=close).run()
    assert r["deal"] and r["supplier_id"] == "sup:70340"
    assert calls == ["sup:70340 agreed"]
    assert clock.time() - t0 < 55  # closed while sup:70360's reply was still pending
    assert r["thread_timeouts"]["sup:70340"] == 0


@pytest.mark.parametrize("status", [409, 422])
async def test_stale_offer_on_close_reconciles_and_redecides(tmp_path, status):
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 1, "sup:70360": 1})
    arena.fail_next_close = status
    close, calls = recording()
    j = Journal(tmp_path / "j.jsonl")
    r = await CaseRunner(arena, "case:S02", OfferAgent("sup:70340"), j, clock=clock, close_fn=close).run()
    assert r["deal"]
    assert len(calls) == 2  # decided again from reconciled state, through the evaluator
    failed = [x for x in j.records if x["rec"] == "failed"]
    assert failed and failed[0]["http"] == status
    assert not j.pending()


async def test_stale_offer_id_from_evaluator(tmp_path):
    """The evaluator picks an offer that is no longer standing: 422, reconcile, decide again."""
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 1, "sup:70360": 1})
    first = {"done": False}

    def stale_then_real(case, threads, estimates=None, reason=""):
        if not first["done"]:
            first["done"] = True
            return {"supplier_id": "sup:70340", "message": {"action": {"type": "accept", "term_sheet_id": "offer:x-0"}}}
        return close_decision(case, threads, estimates, reason)

    j = Journal(tmp_path / "j.jsonl")
    r = await CaseRunner(arena, "case:S02", OfferAgent("sup:70340"), j, clock=clock, close_fn=stale_then_real).run()
    assert r["deal"]
    assert [x["http"] for x in j.records if x["rec"] == "failed"] == [422]


async def test_restart_recovery_from_journal(tmp_path):
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 40, "sup:70360": 40})
    path = tmp_path / "j.jsonl"
    first = asyncio.create_task(
        CaseRunner(arena, "case:S02", PackageAgent(), Journal(path), clock=clock).run())
    while len(arena.posts) < 2:  # both threads' first messages landed, replies still pending
        await asyncio.sleep(0.001)
    first.cancel()  # crash
    with pytest.raises(asyncio.CancelledError):
        await first
    j = Journal(path)
    assert len(j.pending()) == 2
    r = await CaseRunner(arena, "case:S02", PackageAgent(), j, clock=clock).run()
    assert arena.opens == 1  # resumed, no duplicate session
    assert r["deal"] and set(r["thread_timeouts"].values()) == {0}
    assert not j.pending()
    s = arena.sim.sessions[r["session_id"]]
    sent = {mid for mid, _, msg in arena.posts if not msg.get("action")}
    buyer = sum(m.get("from") == "buyer" for t in s["threads"].values() for m in t["messages"])
    assert buyer == len(sent)  # retries reused move ids: every logical move landed once


async def test_uncertain_outcome_reconciles_with_same_move_id(tmp_path):
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 5, "sup:70360": 5})
    arena.lose_reply = True
    j = Journal(tmp_path / "j.jsonl")
    r = await CaseRunner(arena, "case:S02", PackageAgent(), j, clock=clock).run()
    assert r["deal"]
    ids = [mid for mid, _, msg in arena.posts if not msg.get("action")]
    assert len(ids) - len(set(ids)) == 1  # exactly one retry, same id
    assert not j.pending()


async def test_wave_cap_closes_through_evaluator(tmp_path):
    """Watchdog safety net: with the agent's time guard off, the cap close goes through close_decision."""
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 30, "sup:70360": 30})
    close, calls = recording()
    cap = clock.time() + 150
    agent = PackageAgent()
    agent.time_guard_rounds = 0
    agent.compressed_schedule = False  # the compressed schedule alone would close by agreement first
    r = await CaseRunner(arena, "case:S02", agent, Journal(tmp_path / "j.jsonl"),
                         clock=clock, close_fn=close, deadline=lambda: cap).run()
    assert calls[0] == "wave cap"
    assert clock.time() < cap
    assert r["ended"]


async def test_agent_time_guard_closes_before_the_watchdog(tmp_path):
    """With < 2 rounds of wave left the agent itself asks to close; the watchdog never fires."""
    clock = ScaledClock()
    arena = SimArena(clock, {"sup:70340": 30, "sup:70360": 30})
    close, calls = recording()
    cap = clock.time() + 150
    r = await CaseRunner(arena, "case:S02", PackageAgent(), Journal(tmp_path / "j.jsonl"),
                         clock=clock, close_fn=close, deadline=lambda: cap).run()
    # the coordinator's per-thread `propose` path: the guard asks to close, the evaluator accepts
    assert calls and calls[0] == "agent: time guard: accept standing offer" and "wave cap" not in calls
    assert clock.time() < cap - 90
    assert r["ended"] and r["deal"]


async def test_resume_after_finish_returns_journalled_result(tmp_path):
    clock = ScaledClock()
    arena = SimArena(clock)
    j = Journal(tmp_path / "j.jsonl")
    r1 = await CaseRunner(arena, "case:S01", PackageAgent(), j, clock=clock).run()
    r2 = await CaseRunner(arena, "case:S01", PackageAgent(), Journal(tmp_path / "j.jsonl"), clock=clock).run()
    assert arena.opens == 1 and r2["score"] == r1["score"]


async def test_practice_limit_stops_new_cases(tmp_path):
    class Quota(SimArena):
        async def open_session(self, case_id, move_id):
            raise ArenaError(429, "practice limit: 200 sessions per team in 24 hours")

    clock = ScaledClock()
    out = await run_set(Quota(clock), "practice", PackageAgent, Journal(tmp_path / "j.jsonl"), parallel=1,
                        clock=clock)
    assert all(isinstance(v, ArenaError) for v in out.values())
    assert sum("not started" in str(v) for v in out.values()) == len(out) - 1


# -- client ------------------------------------------------------------------------------------
async def test_rate_limiter_has_no_bursts():
    lim, stamps = RateLimiter(50.0), []
    for _ in range(10):
        await lim.wait()
        stamps.append(time.monotonic())
    gaps = [b - a for a, b in zip(stamps, stamps[1:], strict=False)]
    assert min(gaps) >= 0.018


async def test_rate_limiter_spaces_concurrent_callers():
    lim, stamps = RateLimiter(50.0), []

    async def call():
        await lim.wait()
        stamps.append(time.monotonic())

    await asyncio.gather(*(call() for _ in range(8)))
    assert min(b - a for a, b in zip(stamps, stamps[1:], strict=False)) >= 0.018


async def test_client_retries_reuse_move_id_and_422_is_final():
    seen = []

    def handler(request):
        seen.append(request.headers.get("x-move-id"))
        if len(seen) == 1:
            return httpx.Response(503)
        if request.url.path.endswith("/bad/messages"):
            return httpx.Response(422, json={"detail": "invalid"})
        return httpx.Response(200, json={"status": "open"})

    arena = AsyncArena("http://x", "k", calls_per_s=1000, transport=httpx.MockTransport(handler))
    assert (await arena.send("s", "sup", {}, "mid-1"))["status"] == "open"
    assert seen == ["mid-1", "mid-1"]
    with pytest.raises(ArenaError) as e:
        await arena.send("s", "bad", {}, "mid-2")
    assert e.value.status == 422 and seen[-1] == "mid-2" and len(seen) == 3


async def test_client_transport_failure_is_uncertain():
    def handler(request):
        raise httpx.ConnectError("down")

    arena = AsyncArena("http://x", "k", calls_per_s=1000, retries=1, transport=httpx.MockTransport(handler))
    with pytest.raises(UncertainOutcome):
        await arena.send("s", "sup", {}, "mid")


@pytest.mark.parametrize(
    "move, kind",
    [
        ({"close": True, "reason": "x"}, "close"),
        ({"hold": True, "reason": "x"}, "hold"),
        (None, "park"),
        ({}, "park"),
        ({"supplier_id": "a", "message": {"body": "hi"}}, "send"),
        ({"supplier_id": "b", "message": {"body": "hi"}}, "park"),
    ],
)
def test_propose_adapter(move, kind):
    class Agent:
        def propose(self, case, threads, supplier_id):
            return move

    threads = {"a": [{"from": "s", "status": "open"}], "b": [{"from": "s", "status": "open"}]}
    assert runner.propose(Agent(), {}, threads, "a", ["a", "b"])[0] == kind


def test_fallback_close_matches_shape():
    assert runner.resolve_close_fn() is close_decision


@pytest.mark.parametrize("slots", [1, None])
async def test_package_agent_preserves_final_during_66_second_rival_call(tmp_path, slots):
    """Regression for P05's final withdrawal while a rival POST blocked for 65.6s."""
    from negotiator.policy import PolicyConfig

    clock = ScaledClock()

    final_at, accepted_at = [], []

    class FinalArena(SimArena):
        async def send(self, session_id, supplier_id, message, move_id):
            if message.get("action"):
                accepted_at.append(self.clock.time())
            reply = await super().send(session_id, supplier_id, message, move_id)
            if supplier_id == "sup:70340" and not message.get("action") and "result" not in reply:
                final_at.append(self.clock.time())
                reply["status"] = "final_offer"
                self.sim.sessions[session_id]["threads"][supplier_id]["status"] = "final_offer"
            return reply

    arena = FinalArena(clock, {"sup:70340": 2, "sup:70360": 66})
    agent = PackageAgent(policy=PolicyConfig(rfq_final_guard=True), estimates={}, meso=False)
    result = await CaseRunner(arena, "case:S02", agent, Journal(tmp_path / "journal.jsonl"),
                              clock=clock, send_slots=slots).run()
    assert result["deal"] and result["supplier_id"] == "sup:70340"
    assert accepted_at[0] - final_at[0] < 60
    assert result["thread_timeouts"]["sup:70340"] == 0
    assert any(sid == "sup:70360" and not msg.get("action") for _, sid, msg in arena.posts)


async def test_closer_excludes_stale_offer_of_in_flight_supplier(tmp_path):
    from negotiator.state import CaseState, ThreadState

    class ClosingArena:
        async def send(self, session_id, supplier_id, message, move_id):
            assert supplier_id == "sup:70340", "must not accept the pending rival's stale cheaper sheet"
            return {"result": {"ended": True, "deal": True, "supplier_id": supplier_id}}

    clock = ScaledClock()
    case = load_cases()["case:S02"]
    def event(sid, price, status):
        return {"from": "supplier", "status": status, "term_sheets": [
            {"term_sheet_id": f"offer:{sid}-1", "terms": {"unit_price": price}}]}
    running = CaseRunner(ClosingArena(), case["case_id"], PackageAgent(estimates={}),
                         Journal(tmp_path / "journal.jsonl"), clock=clock)
    running.st = CaseState(case, "s", threads={
        "sup:70340": ThreadState("sup:70340", [event("70340", 15, "final_offer")],
                                 deadline_utc=clock.time() + 30),
        "sup:70360": ThreadState("sup:70360", [event("70360", 10, "open")],
                                 in_flight="pending", deadline_utc=clock.time() + 30)})
    await running._close("deadline", wait=False)
    assert running.st.ended


@pytest.mark.parametrize("attribute", ["package_advisor"])
def test_async_disables_package_advice_instead_of_raising(tmp_path, attribute):
    from types import SimpleNamespace

    agent = SimpleNamespace(**{attribute: object()})
    CaseRunner(object(), "case:S02", agent, Journal(tmp_path / "journal.jsonl"))
    assert getattr(agent, attribute) is None
