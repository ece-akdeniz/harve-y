"""Async orchestration: one worker per supplier thread, one case coordinator, wave deadlines, resume.

- Workers propose per-thread moves (send / close / park). The coordinator serialises proposals
  and closes under an asyncio lock but never holds it while awaiting HTTP or a supplier reply.
- Every close (agreed, wave cap, nothing left to work) goes through the shared evaluator
  `negotiator.evaluator.close_decision(case, threads, estimates, reason)`, which owns both accept
  and walk-away. Never the kit's `closing_move`.
- Every POST is journalled (move id + payload) before it leaves; retries reuse both; after an
  uncertain outcome or 409 the coordinator reconciles from GET session/thread first.
- Wave cap: close at max(90 s, slowest round + 15 s) before the cap, re-read on every tick.
- `run_waves` polls `/v1/cases?set=final` only. Spectator endpoints are blocked in the client.
"""

import asyncio
import inspect
import logging
import time

from arena_kit.client import ArenaError
from arena_kit.cost import must_haves_ok, total_cost
from arena_kit.docs import read_document, standard_terms
from arena_kit.play import CLOSE_BEFORE_CAP_S, ENDED, MOVE_LIMIT_S, ROUND_MARGIN_S, RUNNING, hosted, latest, moves_left

from .client import UncertainOutcome
from .state import CaseState, Journal, ThreadState

log = logging.getLogger("negotiator.runner")

BUYER_TARGET_S = 35.0  # buyer work per message; the hard limit is MOVE_LIMIT_S from the reply
CLOSE_WAIT_S = 20.0  # longest a non-cap close waits for in-flight replies
CLOSE_BUDGET_S = 20.0  # keep this much of a thread's 60 s window when waiting before a close
WATCHDOG_TICK_S = 1.0
MAX_CLOSE_ATTEMPTS = 3
MAX_REJECTS = 2  # consecutive 422s before a thread is parked
SEND_RESERVE_S = 25.0  # stop waiting for the session's send slot this long before the thread's deadline


class Clock:
    """Wall clock + sleep. Tests swap in a compressed clock; server deadlines are wall-clock."""

    def time(self) -> float:
        return time.time()

    async def sleep(self, s: float) -> None:
        await asyncio.sleep(max(0.0, s))


def quota_used_up(error) -> bool:
    return isinstance(error, ArenaError) and error.status == 429 and str(error.detail).startswith("practice limit")


def resolve_close_fn():
    """The shared evaluator's close_decision, imported lazily; a conservative fallback until it lands."""
    try:
        from .evaluator import close_decision
    except ImportError:
        log.warning("negotiator.evaluator.close_decision missing; using runner fallback close")
        return fallback_close
    return close_decision


def fallback_close(case, threads, estimates=None, reason=""):
    """Accept the cheapest valid sheet (any sheet of any live thread's latest message) that keeps
    must-haves and beats the alternative; else walk away. Stand-in for evaluator.close_decision."""
    alt = case["buyer"].get("alternative") or {}
    c_alt = total_cost(case, alt["terms"]) if alt.get("terms", {}).get("unit_price") else float("inf")
    live = [sid for sid, ev in threads.items() if latest(ev).get("status") not in ENDED]
    best = None
    for sid in live:
        std = standard_terms(threads[sid])
        for sheet in latest(threads[sid]).get("term_sheets") or []:
            terms = sheet.get("terms") or {}
            if terms.get("unit_price") is None or not must_haves_ok(case, terms, std):
                continue
            c = total_cost(case, terms, std)
            if c < c_alt and (best is None or c < best[0]):
                best = (c, sid, sheet["term_sheet_id"])
    if best is None:
        return {"supplier_id": (live or list(threads))[0], "message": {"action": {"type": "walk_away"}}}
    return {"supplier_id": best[1], "message": {"action": {"type": "accept", "term_sheet_id": best[2]}}}


def _arity(fn) -> int:
    try:
        return len(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        return -1


def propose(agent, case, threads, sid, workable) -> tuple[str, object]:
    """Per-thread proposal for `sid`: ("send", message) | ("close", reason) | ("park", reason).

    Uses `agent.propose(case, threads, supplier_id)` when present: a move, or
    {"close": True, "reason": ...} asking the coordinator to close (via close_decision), or None /
    {"park": True} for nothing to say. Otherwise adapts `agent.decide`: full snapshot first (a
    case-level close is honoured), then a snapshot restricted to `sid`. A thread-level accept
    closes the case only when it is a gap-closed accept on an open thread or nothing else is
    workable.
    """
    fn = getattr(agent, "propose", None)
    if fn is not None and _arity(fn) == 3:
        d = fn(case, threads, sid)
        if not d or d.get("park"):
            return "park", (d or {}).get("reason", "agent: nothing to send")
        if d.get("close"):
            return "close", f"agent: {d.get('reason', 'close requested')}"
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
                self.st = CaseState(case=r["case"], session_id=r["session_id"])
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
        self.st = CaseState(case=case, session_id=session_id)
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
        if state.get("status") == "ended":
            self._end(state.get("result") or {"deal": False, "end_reason": state.get("end_reason")}, "server ended")
            return state
        for sid in self.st.threads:
            await self._refresh_thread(sid, state)
        return state

    async def _refresh_thread(self, sid: str, state: dict):
        """Authoritative thread from the server: messages, closed flag, remaining window."""
        t = self.st.threads[sid]
        info = (state.get("threads") or {}).get(sid) or {}
        remote = await self.arena.thread(self.st.session_id, sid)
        events = [await self._docs(m) for m in remote.get("messages") or []]
        t.timeouts = max(t.timeouts, len(remote.get("timeouts") or []))
        if remote.get("closed") or info.get("closed"):
            t.closed = remote.get("closed") or info.get("closed")
            events.append({"from": "arena", "status": "walked_away", "term_sheets": [], "attachments": [],
                           "body": f"(thread ended: {t.closed})"})
        t.events = events
        if info.get("seconds_left") is not None:
            t.deadline_utc = self.clock.time() + float(info["seconds_left"])

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
            t = self.st.threads[sid]
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
            t.deadline_utc = self.clock.time() + self.move_limit_s
            return
        self.journal.outcome(mid, "abandoned", why="unresolved after retries")
        await self._refresh_all()

    # -- workers -------------------------------------------------------------------------------
    async def _worker(self, sid: str):
        t = self.st.threads[sid]
        while not self.closing and not self.st.ended and not t.closed and not t.parked:
            t0 = self.clock.time()
            async with self.lock:  # decide + journal only; no HTTP under the lock
                if self.closing or self.st.ended:
                    return
                snap = self._live_snapshot()
                kind, what = await asyncio.to_thread(propose, self.agent, self.st.case, snap, sid, self._workable())
                if kind == "send":
                    events = t.events
                    offer = (latest(events).get("term_sheets") or [{}])[0].get("term_sheet_id")
                    intent = self.journal.intent(
                        self.case_id, self.st.session_id, sid, "send", what,
                        buyer_count=sum(m.get("from") == "buyer" for m in events), offer_id=offer,
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
        self._trace("send", supplier=sid, move_id=mid, late_by=round(late_by, 1), terms=[
            s.get("terms") for s in message.get("term_sheets") or []])
        ok = False
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
        self.changed.set()
        self._trace("reply", supplier=sid, status=reply.get("status"), round_s=round(now - t0, 1))
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
            if wait:
                now = self.clock.time()
                until = now + CLOSE_WAIT_S
                waiting = [t.deadline_utc for t in self.st.threads.values()
                           if not t.in_flight and not t.closed and t.deadline_utc]
                if waiting:
                    until = min(until, min(waiting) - CLOSE_BUDGET_S)
                if (cap := self._cap()) is not None:
                    until = min(until, cap - self._cap_margin())
                await self._wait_in_flight(until)
            for _attempt in range(MAX_CLOSE_ATTEMPTS):
                if self.st.ended:
                    return
                async with self.lock:
                    snap = self._live_snapshot()
                    live = {s: ev for s, ev in snap.items() if latest(ev).get("status") not in ENDED}
                    if not live:
                        break
                    d = self.close_fn(self.st.case, live, self.estimates, reason)
                    sid, msg = d["supplier_id"], d["message"]
                    intent = self.journal.intent(self.case_id, self.st.session_id, sid, "close", msg, reason=reason)
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
                fallback = {"deal": False, "end_reason": state.get("end_reason")}
                self._end(state.get("result") or fallback, "close fallback")

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

    # -- entry ---------------------------------------------------------------------------------
    async def run(self) -> dict:
        early = await self._open()
        if early is not None:
            return early
        if not self.st.ended:
            workers = [asyncio.create_task(self._worker(sid)) for sid in self.st.threads]
            watchdog = asyncio.create_task(self._watchdog())
            await watchdog
            if not self.st.ended:
                await self._close("watchdog exit", wait=False)
            for w in workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        if self.st.ended:
            for p in self.journal.pending(session_id=self.st.session_id):
                self.journal.outcome(p["move_id"], "abandoned", why="case ended")
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
    return await CaseRunner(arena, case_id, agent, journal, **kw).run()


async def run_set(arena, set_: str, new_agent, journal: Journal, parallel: int = 8, case_ids=None, **kw) -> dict:
    """Practice/sandbox: play every hosted case of the set (≤ parallel, ≤ 10 open sessions).
    Stops starting new cases once the practice quota is used up. {case_id: result or exception}."""
    ids = case_ids or [c["case_id"] for c in hosted(await arena.cases(set_))]
    sem, used_up, out = asyncio.Semaphore(min(parallel, 10)), asyncio.Event(), {}

    async def one(case_id):
        async with sem:
            if used_up.is_set():
                out[case_id] = ArenaError(429, "not started: the practice quota is used up")
                return
            try:
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


async def run_waves(arena, new_agent, journal: Journal, waves: int = 5, parallel: int = 10, poll_s: float = 3.0,
                    clock: Clock | None = None, **kw) -> dict:
    """Live Final: poll final case metadata, start every open case of a running wave with a cap
    from fresh `seconds_left`, until `waves` waves have closed and every case has finished."""
    clock = clock or Clock()
    started, closed, caps = {}, set(), {}
    sem = asyncio.Semaphore(min(parallel, 10))

    async def one(case):
        async with sem:
            try:
                return await play_case(arena, case["case_id"], new_agent(), journal, case=case,
                                       deadline=lambda w=case["wave"]: caps.get(w), clock=clock, **kw)
            except Exception as e:
                log.exception("%s failed", case["case_id"])
                return e

    while len(closed) < waves or not all(f.done() for f in started.values()):
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
        await clock.sleep(poll_s)
    return {cid: f.result() for cid, f in started.items()}


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
        },
    }


def run_async(args, new_agent, tracer, run_dir) -> dict:
    """CLI entry for `--runner async` (play / run). NEGOTIATOR_JOURNAL resumes a previous run's journal."""
    import os

    from .client import AsyncArena

    journal = Journal(os.environ.get("NEGOTIATOR_JOURNAL") or f"{run_dir}/journal.jsonl")

    async def main():
        arena = AsyncArena()
        try:
            if args.cmd == "play":
                return {args.case_id: await play_case(arena, args.case_id, new_agent(), journal, tracer=tracer)}
            parallel = min(args.parallel, 10)
            if args.set_ == "final":
                return await run_waves(arena, new_agent, journal, args.waves, parallel, tracer=tracer)
            return await run_set(arena, args.set_, new_agent, journal, parallel, tracer=tracer)
        finally:
            await arena.aclose()

    return asyncio.run(main())
