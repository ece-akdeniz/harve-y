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
from concurrent.futures import Future

HARD_TIMEOUT_S = 8.0


def bounded(fn, timeout_s, *args, **kwargs):
    """`fn(*args, **kwargs)` in a daemon thread; its result within min(timeout_s, HARD_TIMEOUT_S)
    seconds of wall clock, else TimeoutError (the thread is abandoned, never joined)."""
    limit = max(0.01, min(float(timeout_s), HARD_TIMEOUT_S))
    future = Future()

    def call():
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # the caller decides; a worker thread must never die silently
            future.set_exception(exc)

    threading.Thread(target=call, daemon=True).start()
    return future.result(timeout=limit)
