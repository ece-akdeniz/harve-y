"""Hard wall-clock bound for every model or network call inside the move loop.

The arena gives us 60 s per message; a supplier reply is awaited by the arena client (180 s, the
brief's minimum), everything else that leaves the process while a decision is pending must end -
result or fallback - within HARD_TIMEOUT_S of wall clock, whatever the HTTP client's per-phase
timeouts add up to. Call sites (module -> bound -> fallback):

- model_assist.ModelAssist.read: `bounded(complete, timeout_s <= 3 s)` -> rules interpretation.
- package_advisor.PackageAdvisor.select: `bounded_call(..., timeout_s <= 8 s)` -> scheduled package.
- inference.InferenceProbeAgent.propose: `bounded(choose_style, 8 s)` -> deterministic move unchanged.
- writer.compose/read: stubs (NotImplementedError), never called by the agent.
- client.AsyncArena / ArenaClient: arena POST/GET, 180 s (supplier think time; not a model call).
"""

import threading
from concurrent.futures import Future, InvalidStateError

HARD_TIMEOUT_S = 8.0
_SLOTS = threading.BoundedSemaphore(4)


def bounded(fn, timeout_s, *args, **kwargs):
    """Return within the wall limit; request local cancellation and discard late output.

    The daemon thread stays in one of four slots until its provider call completes.
    A client timeout cannot prove the remote server stopped work.
    """
    limit = max(0.01, min(float(timeout_s), HARD_TIMEOUT_S))
    if not _SLOTS.acquire(blocking=False):
        raise TimeoutError("model capacity busy")
    future = Future()
    cancelled = threading.Event()

    def call():
        try:
            result = fn(*args, **kwargs)
            if not cancelled.is_set():
                future.set_result(result)
        except BaseException as exc:  # the caller decides; a worker thread must never die silently
            if not cancelled.is_set() and not isinstance(exc, InvalidStateError):
                try:
                    future.set_exception(exc)
                except InvalidStateError:
                    pass
        finally:
            _SLOTS.release()

    threading.Thread(target=call, daemon=True).start()
    try:
        return future.result(timeout=limit)
    except TimeoutError:
        cancelled.set()
        future.cancel()  # local cancellation request; remote completion remains uncertain
        raise
