import asyncio

import pytest
from arena_kit.client import ArenaError
from test_runner import ScaledClock, SimArena

from negotiator.agent import PackageAgent
from negotiator.client import UncertainOutcome
from negotiator.runner import CaseRunner, IncompleteSession
from negotiator.state import Journal


async def test_rejected_close_stays_resumable(tmp_path):
    class RejectClose(SimArena):
        reject = True

        async def send(self, session_id, supplier_id, message, move_id):
            if self.reject and message.get("action"):
                raise ArenaError(422, "injected close rejection")
            return await super().send(session_id, supplier_id, message, move_id)

    clock = ScaledClock(scale=0.02)
    arena, journal = RejectClose(clock), Journal(tmp_path / "j.jsonl")
    runner = CaseRunner(arena, "case:S01", PackageAgent(), journal, clock=clock)
    with pytest.raises(IncompleteSession):
        await asyncio.wait_for(runner.run(), 5)
    assert journal.finished("case:S01") is None
    assert (await arena.session(runner.st.session_id))["status"] == "open"
    arena.reject = False
    result = await CaseRunner(arena, "case:S01", PackageAgent(), journal, clock=clock).run()
    assert result["ended"] and arena.opens == 1


async def test_cached_reply_keeps_server_remaining_window(tmp_path):
    clock = ScaledClock(scale=0.02)
    arena = SimArena(clock)
    runner = CaseRunner(arena, "case:S01", PackageAgent(), Journal(tmp_path / "j.jsonl"), clock=clock)
    await runner._open()
    sid = next(iter(runner.st.threads))
    move = runner.agent.decide(runner.st.case, runner._live_snapshot())["message"]
    intent = runner.journal.intent("case:S01", runner.st.session_id, sid, "send", move, buyer_count=0)
    await arena.send(runner.st.session_id, sid, move, intent["move_id"])
    await clock.sleep(40)
    await runner._settle_pending(intent)
    remaining = runner.st.threads[sid].deadline_utc - clock.time()
    assert 0 < remaining < 25  # cached response must not reset this to 60


async def test_unresolved_post_retains_pending_identity(tmp_path):
    class Uncertain(SimArena):
        async def send(self, session_id, supplier_id, message, move_id):
            raise UncertainOutcome(move_id, ConnectionError("injected"))

    clock = ScaledClock()
    arena, journal = Uncertain(clock), Journal(tmp_path / "j.jsonl")
    runner = CaseRunner(arena, "case:S01", PackageAgent(), journal, clock=clock)
    await runner._open()
    sid = next(iter(runner.st.threads))
    state = await arena.session(runner.st.session_id)
    intent = journal.intent("case:S01", runner.st.session_id, sid, "send", {"body": "x"},
                            buyer_count=0, offer_id=state["threads"][sid]["offer_id"])
    with pytest.raises(UncertainOutcome):
        await runner._settle_pending(intent)
    assert journal.pending(session_id=runner.st.session_id)[0]["move_id"] == intent["move_id"]
    assert journal.finished("case:S01") is None


async def test_recovered_window_includes_time_spent_fetching_threads(tmp_path):
    class SlowRead(SimArena):
        slow = False

        async def thread(self, session_id, supplier_id):
            if self.slow:
                await self.clock.sleep(15)
            return await super().thread(session_id, supplier_id)

    clock = ScaledClock(scale=0.02)
    arena = SlowRead(clock)
    runner = CaseRunner(arena, "case:S01", PackageAgent(), Journal(tmp_path / "j.jsonl"), clock=clock)
    await runner._open()
    sid = next(iter(runner.st.threads))
    state = await arena.session(runner.st.session_id)
    observed = clock.time()
    arena.slow = True
    await runner._refresh_all(state)
    assert runner.st.threads[sid].deadline_utc <= observed + state["threads"][sid]["seconds_left"] + 1
