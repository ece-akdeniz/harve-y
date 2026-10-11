"""Async orchestration: one worker per supplier thread, one case coordinator, wave deadlines, resume.

- Workers propose per-thread moves (send / close / park). The coordinator serialises proposals
  and closes under an asyncio lock but never holds it while awaiting HTTP or a supplier reply.
- Every close (agreed, wave cap, nothing left to work) goes through the shared evaluator
  `negotiator.evaluator.close_decision(case, threads, estimates, reason)`, which owns both accept
  and walk-away. Never the kit's `closing_move`.
- Every POST is journalled (move id + payload) before it leaves; retries reuse both; after an
  uncertain outcome or 409 the coordinator reconciles from GET session/thread first.
- Wave cap: close at max(90 s, slowest round + 15 s) before the cap, re-read on every tick.
- Wave time guard (agent side, fed from here): `agent.time_left_fn` returns seconds to the cap and
  `agent.round_estimate_fn` the slowest round measured; with < TIME_GUARD_ROUNDS (2) x
  max(120 s, slowest round) left the agent stops extending (accepts / converges to the ask).
- `run_waves` polls `/v1/cases?set=final` only. Spectator endpoints are blocked in the client.

Worst-case fit (brief: 60 s per buyer message, supplier replies up to ~1 min, 10 messages, 8-minute
wave): 10 x (60 s ours + 60 s theirs) = 1200 s = 20 min > 480 s. Even at a realistic 50-60 s round
(fast decision, slow supplier) only ~8 rounds fit before the cap margin, and the slower opt-in
schedules (`reciprocal_schedule`, `claim_pacing`) need all 10. The agent's time guard therefore ends the
negotiation on its own with >= 2 rounds (>= 240 s, or 2 x the slowest measured round) of margin: one
round for the converging message and the supplier's reply, one spare for a late or lost reply before
the coordinator's cap close (`_watchdog`, max(90 s, slowest + 15 s)) would take over.

Timing trace (events through `tracer.log`, all with case/session): `wave_time_left` {supplier,
seconds, guard_s} at every decision while a cap exists; `round_time` {supplier, round, reply_s,
decide_s, round_s, status} per observed supplier reply (round = this thread's buyer messages so far,
reply_s = send -> reply observed, decide_s = agent compute, round_s = decision start -> reply);
`thread_time` {supplier, total_s, rounds, slowest_round_s, slowest_decide_s, timeouts, end} per thread
at the end of the case.
"""

import asyncio
import inspect
import logging
import random
import threading
import time

from arena_kit.client import ArenaError
from arena_kit.docs import read_document
from arena_kit.play import CLOSE_BEFORE_CAP_S, ENDED, MOVE_LIMIT_S, ROUND_MARGIN_S, RUNNING, hosted, latest, moves_left

from .agent import ROUND_ESTIMATE_S, TIME_GUARD_ROUNDS
from .client import UncertainOutcome
from .evaluator import best_close
from .play import _safe_estimates, poll_backoff, repeat_last_offer
from .state import CaseState, Journal, ThreadState

log = logging.getLogger("negotiator.runner")

BUYER_TARGET_S = 35.0  # buyer work per message; the hard limit is MOVE_LIMIT_S from the reply
CLOSE_WAIT_S = 20.0  # longest a non-cap close waits for in-flight replies
CLOSE_BUDGET_S = 20.0  # keep this much of a thread's 60 s window when waiting before a close
WATCHDOG_TICK_S = 1.0
MAX_CLOSE_ATTEMPTS = 3
MAX_REJECTS = 2  # consecutive 422s before a thread is parked
HOLD_RECHECK_S = 2.0  # a holding worker asks again after this long, or sooner when any thread changes
SEND_RESERVE_S = 25.0  # stop waiting for the session's send slot this long before the thread's deadline


class IncompleteSession(RuntimeError):
    """The server has not confirmed completion; retain the journal for resume."""


class Clock:
    """Wall clock + sleep. Tests swap in a compressed clock; server deadlines are wall-clock."""

    def time(self) -> float:
        return time.time()

    async def sleep(self, s: float) -> None:
        await asyncio.sleep(max(0.0, s))


def quota_used_up(error) -> bool:
    return isinstance(error, ArenaError) and error.status == 429 and str(error.detail).startswith("practice limit")


def resolve_close_fn():
    """Use the required shared evaluator; never substitute a weaker closing policy."""
    from .evaluator import close_decision

    return close_decision


def _arity(fn) -> int:
    try:
        return len(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return -1


def propose(agent, case, threads, sid, workable) -> tuple[str, object]:
    """Per-thread proposal for `sid`: ("send", message) | ("close", reason) | ("hold", reason) |
    ("park", reason).

    Uses `agent.propose(case, threads, supplier_id)` when present: a move,
    {"close": True, "reason"} asking the coordinator to close (via close_decision),
    {"hold": True, "reason"} to wait and ask again when something changes, or None /
    {"park": True} for nothing more on this thread. Otherwise adapts `agent.decide`: full snapshot first (a
    case-level close is honoured), then a snapshot restricted to `sid`. A thread-level accept
    closes the case only when it is a gap-closed accept on an open thread or nothing else is
    workable.
    """
    fn = getattr(agent, "propose", None)
    if fn is not None and _arity(fn) == 3:
        d = fn(case, threads, sid)
        if not d or d.get("park") or (not d.get("message") and not d.get("close") and not d.get("hold")):
            return "park", (d or {}).get("reason", "agent: nothing to send")
        if d.get("close"):
            return "close", f"agent: {d.get('reason', 'close requested')}"
        if d.get("hold"):
            return "hold", d.get("reason", "agent: hold")
        return _thread_level(case, threads, sid, workable, d)
    d = agent.decide(case, threads)
    action = (d.get("message") or {}).get("action")
    if action:
        if action.get("type") == "accept":
            return "close", f"agent: accept {action.get('term_sheet_id')}"
        return "park", "agent: walk_away on full view"
    if d.get("supplier_id") == sid:
        return "send", d["message"]
    return _thread_level(case, threads, sid, workable, agent.decide(case, {sid: threads[sid]}))


def _thread_level(case, threads, sid, workable, d):
    msg = d.get("message") or {}
    action = msg.get("action")
    if not action:
        if d.get("supplier_id") not in (None, sid):
            return "park", f"agent proposed {d.get('supplier_id')} for worker {sid}"
        return "send", msg
    others = [s for s in workable if s != sid]
    if action.get("type") != "accept":
        return "park", "agent: walk_away on this thread"
    events = threads[sid]
    if not others:
        return "close", "agent: accept, nothing else workable"
    if latest(events).get("status") == "open" and moves_left(case, events) > 1:
        return "close", "agent: accept (gap closed)"
    return "park", "agent: accept on a final/exhausted thread while others are workable"


def fallback_propose(agent, case, threads, sid) -> tuple[str, object]:
    """After `propose` crashed for `sid`: close (the coordinator accepts the best eligible sheet
    via close_decision) when one keeps the must-haves and beats the alternative; else repeat our
    last offer on this thread if it is open with a round left; else park (when every thread is
    parked the watchdog closes, which walks away without an eligible sheet)."""
    try:
        if best_close(case, threads, _safe_estimates(agent, case)):
            return "close", "fallback: accept best eligible sheet"
        if (message := repeat_last_offer(case, threads.get(sid) or [])) is not None:
            return "send", message
    except Exception:
        log.exception("%s: fallback proposal failed", sid)
    return "park", "fallback: no safe move"


def multi_supplier(case) -> bool:
    """`--runner auto` routes cases with more than one supplier to the async runner."""
    return len((case or {}).get("suppliers") or []) > 1


class SharedPace:
    """One key-wide pace shared by the serial (sync, threads) and async clients of an auto run."""

    def __init__(self, rate: float = 8.0, clock=time.monotonic):
        self.interval, self.clock, self._next, self._lock = 1.0 / rate, clock, 0.0, threading.Lock()

    def reserve(self) -> float:
        with self._lock:
            now = self.clock()
            wait, self._next = self._next - now, max(now, self._next) + self.interval
        return max(0.0, wait)

    def pace(self) -> None:  # arena_kit.ArenaClient._pace
        time.sleep(self.reserve())

    async def wait(self) -> None:  # negotiator.client.RateLimiter.wait
        await asyncio.sleep(self.reserve())


class CaseRunner:
    """Plays one case: open or resume, workers per thread, coordinated close."""

    def __init__(
        self,
        arena,
        case_id: str,
        agent,
        journal: Journal,
        *,
        case: dict | None = None,
        deadline=None,
        clock: Clock | None = None,
        close_fn=None,
        estimates=None,
        tracer=None,
        move_limit_s: float = MOVE_LIMIT_S,
        send_slots: int | None = 1,
    ):
        advice_skipped = getattr(agent, "package_advisor", None) is not None
        if advice_skipped:
            # Package advice is serial-only; the async runner plays this case without it.
            log.warning("%s: package advice disabled for the async runner", case_id)
            agent.package_advisor = None
            if getattr(agent, "final_advisor", None) is not None:
                agent.final_advisor = None
        self.arena, self.case_id, self.agent, self.journal = arena, case_id, agent, journal
        self.case_meta, self.deadline_fn = case, deadline
        self.clock = clock or Clock()
        self.close_fn = close_fn or resolve_close_fn()
        self.estimates, self.tracer, self.move_limit_s = estimates, tracer, move_limit_s
        self.st: CaseState | None = None
        self.lock = asyncio.Lock()  # coordinator: proposals and close decisions only
        self.close_lock = asyncio.Lock()
        self.changed = asyncio.Event()  # set whenever a thread's in-flight state changes
        self.closing = False
        self.docs: dict[str, str] = {}
        self.slot = asyncio.Semaphore(send_slots) if send_slots else None
        if advice_skipped:
            self._trace("package_advice_capability_skip", reason="async_runner")

    # -- helpers -------------------------------------------------------------------------------
    def _trace(self, event, **fields):
        if self.tracer:
            sess = self.st.session_id if self.st else None
            self.tracer.log(event, case=self.case_id, session=sess, **fields)

    def _cap(self):
        cap = self.deadline_fn() if callable(self.deadline_fn) else self.deadline_fn
        return cap

    def _cap_margin(self) -> float:
        return max(CLOSE_BEFORE_CAP_S, self.st.slowest_round_s + ROUND_MARGIN_S)

    def _time_left(self):
        """Seconds to the wave cap on the runner's clock; None without a cap (practice/sandbox)."""
        cap = self._cap()
        return None if cap is None else cap - self.clock.time()

    def _slowest_round(self) -> float:
        return self.st.slowest_round_s if self.st else 0.0

    def _wire_agent_clock(self):
        """Give the agent the wave clock (time left, slowest measured round) for its time guard."""
        if hasattr(self.agent, "time_left_fn"):
            self.agent.time_left_fn = self._time_left
        if hasattr(self.agent, "round_estimate_fn"):
            self.agent.round_estimate_fn = self._slowest_round

    async def _docs(self, message: dict) -> dict:
        for att in message.get("attachments") or []:
            aid = att.get("attachment_id")
            if not aid or "text" in att:
                continue
            if aid not in self.docs:
                data = await self.arena.attachment(self.st.session_id, aid)
                self.docs[aid] = await asyncio.to_thread(read_document, att["name"], data)
            att["text"] = self.docs[aid]
        return message

    def _end(self, result: dict | None, how: str):
        if self.st.ended:
            return
        self.st.ended, self.st.result = True, result
        self.closing = True
        self.changed.set()
        self._trace("case_end", how=how, score=(result or {}).get("score"))

    def _workable(self) -> list[str]:
        out = []
        for sid, t in self.st.threads.items():
            if t.closed or t.parked or latest(t.events).get("status") in ENDED:
                continue
            if t.in_flight or moves_left(self.st.case, t.events) > 1:
                out.append(sid)
        return out

    def _live_snapshot(self) -> dict:
        return {sid: list(t.events) for sid, t in self.st.threads.items() if not t.closed}

    # -- open / resume -------------------------------------------------------------------------
    async def _open(self):
        self._wire_agent_clock()  # coordinator start: before any decision, with or without a cap
        if getattr(self.agent, "trades", None):
            meta = self.case_meta
            if meta is None:
                set_ = "sandbox" if self.case_id.startswith("case:D") else "practice"
                meta = next((c for c in await self.arena.cases(set_) if c["case_id"] == self.case_id), None)
            if meta:
                await asyncio.to_thread(self.agent.trades.prepare, meta)
        if (done := self.journal.finished(self.case_id)) is not None:
            return done
        session_id = self.journal.session_for(self.case_id)
        if session_id is None:
            pend = [p for p in self.journal.pending(case_id=self.case_id) if p["kind"] == "open"]
            payload = {"case_id": self.case_id}
            intent = pend[-1] if pend else self.journal.intent(self.case_id, None, None, "open", payload)
            try:
                r = await self.arena.open_session(self.case_id, intent["move_id"])
            except ArenaError as e:
                running = RUNNING.search(str(e.detail)) if e.status == 409 else None
                if not running:
                    self.journal.outcome(intent["move_id"], "failed", http=e.status, detail=str(e.detail))
                    raise
                self.journal.outcome(intent["move_id"], "abandoned", resumed=running.group(1))
                session_id = running.group(1)
            else:
                self.journal.outcome(intent["move_id"], "done", session=r["session_id"])
                self.journal.session(self.case_id, r["session_id"], r["case"])
                now = self.clock.time()
                self.st = CaseState(case=r["case"], session_id=r["session_id"], opened_at=now)
                for sid, events in r["threads"].items():
                    self.st.threads[sid] = ThreadState(sid, list(events), deadline_utc=now + self.move_limit_s)
                for t in self.st.threads.values():
                    for m in t.events:
                        await self._docs(m)
                self._trace("open", suppliers=list(self.st.threads))
                return None
            self.journal.session(self.case_id, session_id, self.case_meta)
        return await self._resume(session_id)

    async def _resume(self, session_id: str):
        """Pick up a session this key already started: rebuild every thread from the server and
        settle journalled moves that never got an outcome."""
        state = await self.arena.session(session_id)
        case = self.case_meta or state.get("case") or self.journal.case_file(self.case_id)
        if case is None:
            raise RuntimeError(f"cannot resume {session_id}: case metadata unknown")
        self.st = CaseState(case=case, session_id=session_id, opened_at=self.clock.time())
        self._trace("resume", status=state.get("status"))
        if state.get("status") == "ended":
            self._end(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")}, "resumed ended")
            return self.st.result
        for sid in state["threads"]:
            self.st.threads[sid] = ThreadState(sid)
        await self._refresh_all(state)
        for intent in self.journal.pending(session_id=session_id):
            await self._settle_pending(intent)
            if self.st.ended:
                return self.st.result
        return None

    # -- reconciliation ------------------------------------------------------------------------
    async def _refresh_all(self, state: dict | None = None):
        state = state or await self.arena.session(self.st.session_id)
        observed_at = self.clock.time()
        if state.get("status") == "ended":
            self._end(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")}, "server ended")
            return state
        for sid in self.st.threads:
            await self._refresh_thread(sid, state, observed_at=observed_at)
        return state

    async def _refresh_thread(self, sid: str, state: dict, observed_at=None):
        """Authoritative thread from the server: messages, closed flag, remaining window."""
        observed_at = self.clock.time() if observed_at is None else observed_at
        t = self.st.threads[sid]
        info = (state.get("threads") or {}).get(sid) or {}
        remote = await self.arena.thread(self.st.session_id, sid)
        events = [await self._docs(m) for m in remote.get("messages") or []]
        t.timeouts = max(t.timeouts, len(remote.get("timeouts") or []))
        if remote.get("closed") or info.get("closed"):
            t.closed = remote.get("closed") or info.get("closed")
            events.append(
                {
                    "from": "arena",
                    "status": "walked_away",
                    "term_sheets": [],
                    "attachments": [],
                    "body": f"(thread ended: {t.closed})",
                }
            )
        t.events = events
        if info.get("seconds_left") is not None:
            t.deadline_utc = observed_at + float(info["seconds_left"])

    async def _settle_pending(self, intent: dict):
        """A journalled POST without outcome (crash or uncertain transport): decide from server
        state whether it landed, re-send it with the same move id, or abandon it."""
        mid, sid, kind = intent["move_id"], intent["supplier"], intent["kind"]
        for _ in range(3):
            state = await self.arena.session(self.st.session_id)
            if state.get("status") == "ended":
                self.journal.outcome(mid, "abandoned", why="session ended")
                await self._refresh_all(state)
                return
            info = state["threads"].get(sid) or {}
            if info.get("closed"):
                self.journal.outcome(mid, "abandoned", why="thread closed")
                await self._refresh_thread(sid, state)
                return
            if kind == "close":
                action = intent["payload"].get("action") or {}
                offer = action.get("term_sheet_id")
                if action.get("type") == "accept" and not any(
                    th.get("offer_id") == offer and not th.get("closed") for th in state["threads"].values()
                ):
                    self.journal.outcome(mid, "abandoned", why="offer no longer standing")
                    await self._refresh_all(state)
                    return
            else:
                remote = await self.arena.thread(self.st.session_id, sid)
                buyers = sum(m.get("from") == "buyer" for m in remote.get("messages") or [])
                landed = buyers > intent.get("buyer_count", 0)
                if not landed and info.get("offer_id") != intent.get("offer_id"):
                    self.journal.outcome(mid, "abandoned", why="thread moved on")
                    await self._refresh_thread(sid, state)
                    return
            try:
                reply = await self.arena.send(self.st.session_id, sid, intent["payload"], mid)
            except UncertainOutcome:
                continue
            except ArenaError as e:
                self.journal.outcome(mid, "failed", http=e.status, detail=str(e.detail))
                await self._refresh_all()
                return
            self.journal.outcome(mid, "done", status=reply.get("status"))
            if "result" in reply:
                self._end(reply["result"], "settled pending")
                return
            await self._refresh_thread(sid, await self.arena.session(self.st.session_id))
            return
        await self._refresh_all()
        if not self.st.ended:
            raise UncertainOutcome(mid, RuntimeError("reconciliation exhausted; move remains pending"))

    # -- workers -------------------------------------------------------------------------------
    async def _worker(self, sid: str):
        t = self.st.threads[sid]
        while not self.closing and not self.st.ended and not t.closed and not t.parked:
            t0 = self.clock.time()
            prepared_response = None
            if getattr(self.agent, "model_assist", None):
                snap = self._live_snapshot()
                try:
                    await asyncio.to_thread(self.agent.prepare_email, self.st.case, snap, sid)
                except Exception:
                    log.exception("%s %s: e-mail interpretation failed; continuing without", self.case_id, sid)
            if getattr(self.agent, "response_writer", None):
                snap = self._live_snapshot()
                try:
                    prepared_response = await asyncio.to_thread(
                        self.agent.prepare_response, self.st.case, snap, sid,
                        remaining_s=max(0.0, (t.deadline_utc or 0) - self.clock.time()))
                except Exception:
                    log.exception("%s %s: response preview failed; continuing without", self.case_id, sid)
            async with self.lock:  # decide + journal only; no HTTP under the lock
                if self.closing or self.st.ended:
                    return
                snap = self._live_snapshot()
                if getattr(self.agent, "trades", None):
                    self.agent.trades.deadlines[sid] = time.time() + max(0, (t.deadline_utc or 0) - self.clock.time())
                if (left := self._time_left()) is not None:
                    tg = getattr(self.agent, "time_guard", None)
                    tg = tg() if callable(tg) else None
                    self._trace("wave_time_left", supplier=sid, seconds=round(left, 1),
                                guard_s=round(tg[1], 1) if tg else None)
                d0 = self.clock.time()
                try:
                    kind, what = await asyncio.to_thread(
                        propose, self.agent, self.st.case, snap, sid, self._workable())
                except Exception as exc:
                    log.exception("%s %s: decision step failed; using the fallback", self.case_id, sid)
                    kind, what = fallback_propose(self.agent, self.st.case, snap, sid)
                    self._trace("propose_fallback", supplier=sid, error=repr(exc)[:500], kind=kind,
                                reason=what if kind != "send" else "repeat last offer")
                t.decide_s = self.clock.time() - d0
                t.slowest_decide_s = max(t.slowest_decide_s, t.decide_s)
                if kind == "send":
                    if prepared_response and what == prepared_response["original"]:
                        what = {**what, "body": prepared_response["body"]}
                    from .decision_contract import decision_record

                    record = decision_record(self.agent, self.st.case, snap,
                                             {"supplier_id": sid, "message": what}, runner="async")
                    events = t.events
                    offer = (latest(events).get("term_sheets") or [{}])[0].get("term_sheet_id")
                    intent = self.journal.intent(
                        self.case_id,
                        self.st.session_id,
                        sid,
                        "send",
                        what,
                        buyer_count=sum(m.get("from") == "buyer" for m in events),
                        offer_id=offer,
                        decision_record=record,
                    )
                    t.in_flight = intent["move_id"]
                    t.events.append({**what, "from": "buyer"})
                elif kind == "park":
                    t.parked = what
            took = self.clock.time() - t0
            if took > BUYER_TARGET_S:
                log.warning("%s %s: buyer work took %.1fs (target %.0fs)", self.case_id, sid, took, BUYER_TARGET_S)
            if kind == "close":
                self._trace("propose_close", supplier=sid, reason=what)
                await self._close(what)
                return
            if kind == "park":
                self._trace("park", supplier=sid, reason=what)
                self.changed.set()
                return
            if kind == "hold":
                if what != t.holding:
                    self._trace("hold", supplier=sid, reason=what)
                t.holding = what
                if t.deadline_utc and self.clock.time() > t.deadline_utc:
                    await self._refresh_all()  # learn the timeout (or closure) the wait just cost
                self.changed.clear()
                try:
                    await asyncio.wait_for(self.changed.wait(), timeout=HOLD_RECHECK_S * self._scale())
                except TimeoutError:
                    pass
                continue
            t.holding = None
            await self._send(sid, intent, what, t0)
        self.changed.set()

    async def _send_slot(self, t: ThreadState) -> bool:
        """Soft per-session send slot: hosted answers concurrent calls on one session slowly, so
        prefer one POST at a time, but never wait past the thread's own budget."""
        if self.slot is None:
            return False
        budget = (t.deadline_utc or self.clock.time()) - self.clock.time() - SEND_RESERVE_S
        try:
            await asyncio.wait_for(self.slot.acquire(), timeout=max(0.0, budget) * self._scale())
        except TimeoutError:
            self._trace("slot_skip", supplier=t.supplier_id)
            return False
        return True

    async def _send(self, sid: str, intent: dict, message: dict, t0: float):
        t, mid = self.st.threads[sid], intent["move_id"]
        held = await self._send_slot(t)
        late_by = self.clock.time() - (t.deadline_utc or self.clock.time())
        self._trace(
            "send",
            supplier=sid,
            move_id=mid,
            late_by=round(late_by, 1),
            terms=[s.get("terms") for s in message.get("term_sheets") or []],
        )
        ok = False
        sent_at = self.clock.time()
        try:
            reply = await self.arena.send(self.st.session_id, sid, message, mid)
            ok = True
        except ArenaError as e:
            self.journal.outcome(mid, "failed", http=e.status, detail=str(e.detail))
            if t.events and t.events[-1].get("from") == "buyer":
                t.events.pop()
            self._trace("send_error", supplier=sid, http=e.status, detail=str(e.detail))
            if e.status == 422:
                t.rejects += 1
                if t.rejects >= MAX_REJECTS:
                    t.parked = f"422 x{t.rejects}: {e.detail}"
            else:
                t.timeouts += e.status == 409 and "late" in str(e.detail)
                if not self.st.ended:
                    await self._refresh_all()
            return
        except UncertainOutcome:
            if t.events and t.events[-1].get("from") == "buyer":
                t.events.pop()
            await self._settle_pending(intent)
            return
        finally:
            if held:
                self.slot.release()
            if not ok:
                t.in_flight = None
                self.changed.set()
        self.journal.outcome(mid, "done", status=reply.get("status"))
        t.rejects = 0
        if "result" in reply:
            t.in_flight = None
            self._end(reply["result"], f"reply from {sid}")
            return
        now = self.clock.time()
        t.events.append(await self._docs(reply))
        t.deadline_utc = now + self.move_limit_s
        t.in_flight = None  # only now: a closer waiting on this thread sees the new offer
        self.st.slowest_round_s = max(self.st.slowest_round_s, now - t0)
        t.slowest_round_s = max(t.slowest_round_s, now - t0)
        t.rounds_timed += 1
        self.changed.set()
        self._trace("reply", supplier=sid, status=reply.get("status"), round_s=round(now - t0, 1))
        self._trace(
            "round_time",
            supplier=sid,
            round=sum(m.get("from") == "buyer" for m in t.events),
            reply_s=round(now - sent_at, 1),
            decide_s=round(t.decide_s, 2),
            round_s=round(now - t0, 1),
            status=reply.get("status"),
        )
        if reply.get("status") == "agreed":
            await self._close(f"{sid} agreed")

    # -- closing -------------------------------------------------------------------------------
    async def _wait_in_flight(self, until: float):
        while any(t.in_flight for t in self.st.threads.values()) and not self.st.ended:
            left = until - self.clock.time()
            if left <= 0:
                return
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), timeout=min(left, 1.0) * self._scale())
            except TimeoutError:
                pass

    def _scale(self) -> float:
        return getattr(self.clock, "scale", 1.0)

    async def _close(self, reason: str, wait: bool = True):
        async with self.close_lock:
            if self.st.ended:
                return
            self.closing = True
            pending_only = not any(
                not t.closed and not t.in_flight and latest(t.events).get("status") not in ENDED
                for t in self.st.threads.values()
            )
            if wait or pending_only:
                now = self.clock.time()
                cap = self._cap()
                # A cap close with every sheet pending can use the reserved wave window.
                # The ordinary 20-second wait may end before a healthy supplier reply.
                until = (cap - CLOSE_BUDGET_S if pending_only and reason == "wave cap"
                         and cap is not None else now + CLOSE_WAIT_S)
                waiting = [
                    t.deadline_utc
                    for t in self.st.threads.values()
                    if not t.in_flight and not t.closed and t.deadline_utc
                ]
                if waiting:
                    until = min(until, min(waiting) - CLOSE_BUDGET_S)
                if cap is not None:
                    # A cap-triggered close with every reply pending needs one current
                    # sheet; use the reserved closing window rather than stale offers.
                    margin = CLOSE_BUDGET_S if pending_only else self._cap_margin()
                    until = min(until, cap - margin)
                await self._wait_in_flight(until)
            for _attempt in range(MAX_CLOSE_ATTEMPTS):
                if self.st.ended:
                    return
                async with self.lock:
                    snap = self._live_snapshot()
                    # A pending POST may already have superseded its last visible offer.
                    # After the bounded wait, close only on independently available sheets.
                    live = {s: ev for s, ev in snap.items()
                            if latest(ev).get("status") not in ENDED and not self.st.threads[s].in_flight}
                    if not live:
                        break
                    estimates = self.estimates
                    if estimates is None:
                        estimates_for = getattr(self.agent, "estimates_for", None)
                        estimates = (
                            estimates_for(self.st.case)
                            if estimates_for is not None
                            else getattr(self.agent, "estimates", None)
                        )
                    d = self.close_fn(self.st.case, live, estimates, reason)
                    sid, msg = d["supplier_id"], d["message"]
                    from .decision_contract import decision_record

                    record = decision_record(self.agent, self.st.case, live, d, runner="async")
                    intent = self.journal.intent(self.case_id, self.st.session_id, sid, "close", msg,
                                                 reason=reason, decision_record=record)
                self._trace("close", supplier=sid, action=msg.get("action"), reason=reason)
                try:
                    reply = await self.arena.send(self.st.session_id, sid, msg, intent["move_id"])
                except UncertainOutcome:
                    await self._settle_pending(intent)
                    continue
                except ArenaError as e:
                    self.journal.outcome(intent["move_id"], "failed", http=e.status, detail=str(e.detail))
                    self._trace("close_error", http=e.status, detail=str(e.detail))
                    if e.status not in (409, 422):
                        raise
                    await self._refresh_all()  # stale offer, late or ended: reconcile, then decide again
                    continue
                self.journal.outcome(intent["move_id"], "done", status=reply.get("status"))
                self._end(reply.get("result", reply), f"close: {reason}")
                return
            if not self.st.ended:
                state = await self.arena.session(self.st.session_id)
                if state.get("status") == "ended":
                    await self._refresh_all(state)
                else:
                    raise IncompleteSession(f"{self.st.session_id}: close unresolved; resume existing session")

    async def _watchdog(self):
        while not self.st.ended:
            cap = self._cap()
            if cap is not None and self.clock.time() >= cap - self._cap_margin():
                log.info("%s: wave cap near - closing", self.case_id)
                await self._close("wave cap", wait=False)
                return
            if not self.closing and not self._workable() and not any(t.in_flight for t in self.st.threads.values()):
                await self._close("all threads done", wait=False)
                return
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), timeout=WATCHDOG_TICK_S * self._scale())
            except TimeoutError:
                pass

    def _trace_thread_times(self):
        """One `thread_time` per thread at the end of the case (see the module docstring)."""
        if not self.tracer or not self.st:
            return
        now = self.clock.time()
        total = round(now - self.st.opened_at, 1) if self.st.opened_at is not None else None
        for sid, t in self.st.threads.items():
            end = t.closed or t.parked or latest(t.events).get("status") if t.events else None
            self._trace(
                "thread_time",
                supplier=sid,
                total_s=total,
                rounds=sum(m.get("from") == "buyer" for m in t.events),
                slowest_round_s=round(t.slowest_round_s, 1),
                slowest_decide_s=round(t.slowest_decide_s, 2),
                timeouts=t.timeouts,
                end=end,
            )

    # -- entry ---------------------------------------------------------------------------------
    async def run(self) -> dict:
        early = await self._open()
        if early is not None:
            return early
        if budget := getattr(self.agent, "model_budget", None):
            budget.bind(self.st.session_id, self.journal.path)
        if not self.st.ended:
            workers = [asyncio.create_task(self._worker(sid)) for sid in self.st.threads]
            watchdog = asyncio.create_task(self._watchdog())
            tasks = [watchdog, *workers]
            try:
                # Propagate worker failures too; waiting only on the watchdog can hang forever.
                pending = set(tasks)
                while not watchdog.done():
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        task.result()
                watchdog.result()
                if not self.st.ended:
                    await self._close("watchdog exit", wait=False)
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        if self.st.ended:
            for p in self.journal.pending(session_id=self.st.session_id):
                self.journal.outcome(p["move_id"], "abandoned", why="case ended")
        self._trace_thread_times()
        result = dict(self.st.result or {})
        self.journal.result(self.case_id, self.st.session_id, result)
        try:
            timeouts = {}
            for sid in self.st.threads:
                remote = await self.arena.thread(self.st.session_id, sid)
                timeouts[sid] = len(remote.get("timeouts") or [])
            result["thread_timeouts"] = timeouts
        except ArenaError:
            pass
        result["session_id"] = self.st.session_id
        self._trace("result", result=result)
        return result


async def play_case(arena, case_id: str, agent, journal: Journal, **kw) -> dict:
    from .prewarm import prewarm_case_async

    await prewarm_case_async(agent, kw.get("case"), tracer=kw.get("tracer"))  # before the session opens
    return await CaseRunner(arena, case_id, agent, journal, **kw).run()


async def run_set(arena, set_: str, new_agent, journal: Journal, parallel: int = 8, case_ids=None, serial=None,
                  **kw) -> dict:
    """Practice/sandbox: play every hosted case of the set (≤ parallel, ≤ 10 open sessions).
    Stops starting new cases once the practice quota is used up. {case_id: result or exception}.
    `serial` (auto runner): async callable (case, agent, deadline) for one-supplier cases."""
    metas = {c["case_id"]: c for c in hosted(await arena.cases(set_))} if serial or not case_ids else {}
    ids = case_ids or list(metas)
    sem, used_up, out = asyncio.Semaphore(min(parallel, 10)), asyncio.Event(), {}

    async def one(case_id):
        async with sem:
            if used_up.is_set():
                out[case_id] = ArenaError(429, "not started: the practice quota is used up")
                return
            try:
                meta = metas.get(case_id)
                if serial is not None and meta is not None and not multi_supplier(meta):
                    _route(kw.get("tracer"), case_id, "serial")
                    out[case_id] = await serial(meta, new_agent(), None)
                else:
                    if serial is not None:
                        _route(kw.get("tracer"), case_id, "async")
                    out[case_id] = await play_case(arena, case_id, new_agent(), journal, **kw)
            except ArenaError as e:
                if quota_used_up(e):
                    used_up.set()
                    log.warning("practice quota used up: %s", e.detail)
                else:
                    log.exception("%s failed", case_id)
                out[case_id] = e
            except Exception as e:  # one broken case must not stop the others
                log.exception("%s failed", case_id)
                out[case_id] = e

    await asyncio.gather(*(one(c) for c in ids))
    return out


async def run_waves(
    arena,
    new_agent,
    journal: Journal,
    waves: int = 5,
    parallel: int = 10,
    poll_s: float = 3.0,
    clock: Clock | None = None,
    serial=None,
    rng=random.random,
    **kw,
) -> dict:
    """Live Final: poll final case metadata, start every open case of a running wave with a cap
    from fresh `seconds_left`, until `waves` waves have closed and every case has finished.
    Case-list errors (other than 403 before wave 1) and network errors back off with jitter and
    keep polling: running sessions and later waves must continue. `serial` as in `run_set`."""
    clock = clock or Clock()
    started, closed, caps = {}, set(), {}
    sem = asyncio.Semaphore(min(parallel, 10))
    failures = 0

    async def one(case):
        async with sem:
            try:
                deadline = lambda w=case["wave"]: caps.get(w)  # noqa: E731
                if serial is not None and not multi_supplier(case):
                    _route(kw.get("tracer"), case["case_id"], "serial")
                    return await serial(case, new_agent(), deadline)
                if serial is not None:
                    _route(kw.get("tracer"), case["case_id"], "async")
                return await play_case(
                    arena,
                    case["case_id"],
                    new_agent(),
                    journal,
                    case=case,
                    deadline=deadline,
                    clock=clock,
                    **kw,
                )
            except Exception as e:
                log.exception("%s failed", case["case_id"])
                return e

    from .prewarm import prewarm_async

    await prewarm_async(new_agent, tracer=kw.get("tracer"))  # package, dossiers, facts: before the first poll
    while len(closed) < waves or not all(f.done() for f in started.values()):
        try:
            try:
                cases = await arena.cases("final")
            except ArenaError as e:
                if e.status != 403:  # 403: no wave has started yet
                    raise
                cases = []
            for case in cases:
                if not case.get("open"):
                    closed.add(case["wave"])
                    continue
                if case.get("seconds_left") is not None:
                    caps[case["wave"]] = clock.time() + case["seconds_left"]
                if case["case_id"] not in started and case.get("seconds_left"):
                    log.warning("start %s (wave %s, %ss left)", case["case_id"], case["wave"], case["seconds_left"])
                    started[case["case_id"]] = asyncio.create_task(one(case))
        except Exception as e:  # never let the final die
            failures += 1
            pause = poll_backoff(poll_s, failures, rng)
            log.warning("final case list failed (%d in a row): %r; retry in %.1fs", failures, e, pause)
            await clock.sleep(pause)
            continue
        failures = 0
        await clock.sleep(poll_s)
    return {cid: f.result() for cid, f in started.items()}


def _route(tracer, case_id, runner):
    log.info("%s: auto runner -> %s", case_id, runner)
    if tracer:
        tracer.log("route", case=case_id, runner=runner)


def serial_runner(client, executor):
    """Auto runner's serial path: `play.play_case` on a sync client in a dedicated thread pool
    (so long serial cases never starve the async workers' default executor)."""
    from arena_kit.play import RemoteTable

    from .play import play_case as serial_play

    async def run(case, agent, deadline):
        loop = asyncio.get_running_loop()
        table = RemoteTable(client, case)
        return await loop.run_in_executor(executor, serial_play, table, case["case_id"], agent, deadline)

    return run


def runtime_config(parallel: int | None = None, calls_per_s: float = 8.0) -> dict:
    """Runtime settings a comparison must freeze (logged in the trace's run event)."""
    return {
        "parallel": parallel,
        "runtime": {
            "calls_per_s": calls_per_s,
            "move_limit_s": MOVE_LIMIT_S,
            "buyer_target_s": BUYER_TARGET_S,
            "close_wait_s": CLOSE_WAIT_S,
            "close_budget_s": CLOSE_BUDGET_S,
            "close_before_cap_s": CLOSE_BEFORE_CAP_S,
            "round_margin_s": ROUND_MARGIN_S,
            "max_close_attempts": MAX_CLOSE_ATTEMPTS,
            "send_slots_per_session": 1,
            "send_reserve_s": SEND_RESERVE_S,
            "time_guard_rounds": TIME_GUARD_ROUNDS,
            "time_guard_round_estimate_s": ROUND_ESTIMATE_S,
        },
    }


def run_async(args, new_agent, tracer, run_dir) -> dict:
    """CLI entry for `--runner async|auto` (play / run). NEGOTIATOR_JOURNAL resumes a previous run's
    journal. `auto`: cases with more than one supplier use the async runner, one-supplier cases the
    serial runner (sync client, dedicated threads); both clients share one key-wide pace."""
    import os
    from concurrent.futures import ThreadPoolExecutor

    from .client import AsyncArena

    journal = Journal(os.environ.get("NEGOTIATOR_JOURNAL") or f"{run_dir}/journal.jsonl")
    auto = getattr(args, "runner", "async") == "auto"

    async def main():
        pace = SharedPace() if auto else None
        arena = AsyncArena(limiter=pace)
        serial, executor = None, None
        if auto:
            from arena_kit.client import ArenaClient

            client = ArenaClient()
            client._pace = pace.pace
            executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="serial-case")
            serial = serial_runner(client, executor)
        try:
            if args.cmd == "play":
                if serial is not None:
                    set_ = "sandbox" if args.case_id.startswith("case:D") else "practice"
                    meta = next((c for c in await arena.cases(set_) if c["case_id"] == args.case_id), None)
                    if meta is not None and not multi_supplier(meta):
                        _route(tracer, args.case_id, "serial")
                        return {args.case_id: await serial(meta, new_agent(), None)}
                    _route(tracer, args.case_id, "async")
                return {args.case_id: await play_case(arena, args.case_id, new_agent(), journal, tracer=tracer)}
            parallel = min(args.parallel, 10)
            if args.set_ == "final":
                return await run_waves(arena, new_agent, journal, args.waves, parallel, tracer=tracer, serial=serial)
            return await run_set(arena, args.set_, new_agent, journal, parallel, tracer=tracer, serial=serial)
        finally:
            await arena.aclose()
            if executor is not None:
                executor.shutdown(wait=False)

    return asyncio.run(main())
