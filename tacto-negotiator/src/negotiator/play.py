"""Serial play loop: `arena_kit.play.play` with our evaluator on the deadline path.

The kit loop closes near a wave's cap with its own `closing_move` (first sheet only, no supplier
estimates). `play_case` closes through `evaluator.close_decision` with the agent's estimates.
`play_all` and `play_waves` mirror the kit's but run `play_case`.
"""

import functools
import hashlib
import logging
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from arena_kit.client import ArenaError
from arena_kit.play import (
    CLOSE_BEFORE_CAP_S,
    MOVE_LIMIT_S,
    ROUND_MARGIN_S,
    RemoteTable,
    fetch_documents,
    live_threads,
    quota_used_up,
    standing,
)

from .evaluator import close_decision

log = logging.getLogger("negotiator")


def run_config(agent, runner="serial-play_case", facts="data/package/facts.json"):
    """What a run must record to be comparable: commit, agent params, estimates, runner, data."""
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain", "--", "src"], cwd=root, capture_output=True, text=True
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    path = Path(os.environ.get("ARENA_DATA", root / Path(facts).parent)) / "facts.json"
    provenance = {}
    try:
        from .dossiers import load_package

        package = load_package()
        for label, directory in [("base", package.root), ("release", package.release)]:
            if directory:
                paths = (
                    sorted(directory.rglob("*"))
                    if label == "release"
                    else [directory / "facts.json", directory / "world.sqlite"]
                )
                provenance[label] = {
                    "path": str(directory),
                    "files": {
                        str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in paths
                        if p.is_file()
                    },
                }
    except (OSError, ValueError):
        provenance["unavailable"] = True
    data = hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else None
    keys = ("anchor", "rounds", "close_gap", "final_hold_s", "meso", "p_walk", "claims")
    params = {k: getattr(agent, k) for k in keys if hasattr(agent, k)}
    return {
        "commit": commit,
        "src_dirty": dirty,
        "agent": getattr(agent, "version", type(agent).__name__),
        "params": params,
        "estimates": (
            "dossiers"
            if getattr(agent, "_estimates", {}) is None
            else "injected"
            if getattr(agent, "_estimates", None)
            else "off"
        ),
        "runner": runner,
        "facts_sha256": data,
        "data_provenance": provenance,
        "policy": agent.policy.record() if getattr(agent, "policy", None) else None,
        "runtime_guidance": getattr(agent, "runtime_guidance", None),
    }


def agent_estimates(agent, case):
    """The agent's supplier estimates for this case ({supplier_id: estimate}), if it has any."""
    if hasattr(agent, "estimates_for"):
        return agent.estimates_for(case)
    return getattr(agent, "estimates", None)


def play_case(table, case_id, agent, deadline=None):
    """Play one case to its end. `deadline` (time.time(), or a function returning it): a Live Final
    wave's cap - shortly before it, `close_decision` closes the case."""
    case, threads = table.open(case_id)
    if (tracer := getattr(agent, "tracer", None)) and getattr(table, "session_id", None):
        base = os.environ.get("ARENA_URL", "").rstrip("/")
        replay = f"{base}/replay/{table.session_id}"
        tracer.log("session", session_id=table.session_id, case_id=case_id, replay_url=replay)
    if getattr(table, "done", None):
        return table.done
    for events in threads.values():
        for m in events:
            fetch_documents(table, m)
    slowest = 0.0
    while live_threads(threads):
        t0 = time.monotonic()
        if getattr(agent, "trades", None):
            for sid in live_threads(threads):
                agent.trades.deadlines[sid] = time.time() + MOVE_LIMIT_S
        cap = deadline() if callable(deadline) else deadline
        if cap and time.time() > cap - max(CLOSE_BEFORE_CAP_S, slowest + ROUND_MARGIN_S):
            log.info("%s: the wave's cap is near - closing", case_id)
            decision = close_decision(case, threads, agent_estimates(agent, case), "deadline")
            if hasattr(agent, "log_close"):
                agent.log_close(case, threads, decision, "deadline")
        else:
            decision = agent.decide(case, threads)
        if (took := time.monotonic() - t0) > MOVE_LIMIT_S * 0.75:
            log.warning("decision took %.1fs - the limit is %ss per message", took, MOVE_LIMIT_S)
        sid, msg = decision["supplier_id"], decision["message"]
        try:
            if msg.get("action"):
                log.info("%s %s", sid, msg["action"])
                return table.close(sid, msg)
            reply = table.send(sid, msg)
        except ArenaError as e:
            if e.status != 409:
                raise
            log.info("%s: %s", sid, e.detail)
            reply = table.missed(sid, e)
            if msg.get("action") and "result" not in reply:
                threads[sid].append(fetch_documents(table, reply))
                continue
        if "result" in reply:
            return reply["result"]
        if tracer:
            tracer.log("supplier_reply", case=case_id, supplier=sid, message=reply)
        threads[sid] += [{**msg, "from": "buyer"}, fetch_documents(table, reply)]
        slowest = max(slowest, time.monotonic() - t0)
        log.info("%s %s %s", sid, reply.get("status"), standing(threads[sid])[1])
    return table.result()


def play_all(new_table, case_ids, new_agent, parallel=8):
    """Many cases at once, each with its own table and agent; stops starting cases once the
    practice quota is used up. {case_id: result or the exception that stopped it}."""
    used_up = threading.Event()

    def one(case_id):
        if used_up.is_set():
            return case_id, ArenaError(429, "not started: the practice quota is used up")
        try:
            return case_id, play_case(new_table(), case_id, new_agent())
        except ArenaError as e:
            if quota_used_up(e):
                used_up.set()
                log.warning("practice quota used up: %s", e.detail)
            elif e.status == 403:
                log.warning("%s: %s", case_id, e.detail)
            else:
                log.exception("%s failed", case_id)
            return case_id, e
        except Exception as e:
            log.exception("%s failed", case_id)
            return case_id, e

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        return dict(pool.map(one, case_ids))


def play_waves(client, new_agent, waves=5, parallel=10, poll=5.0):
    """The Live Final (kit `play_waves` structure): play each wave's cases within its cap."""
    started, closed, caps = {}, set(), {}

    def one(case, deadline):
        try:
            return play_case(RemoteTable(client, case), case["case_id"], new_agent(), deadline)
        except Exception as e:
            log.exception("%s failed", case["case_id"])
            return e

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        while len(closed) < waves or not all(f.done() for f in started.values()):
            try:
                cases = client.cases("final")
            except ArenaError as e:
                if e.status != 403:
                    raise
                cases = []
            for case in cases:
                if not case.get("open"):
                    closed.add(case["wave"])
                    continue
                if case.get("seconds_left") is not None:
                    caps[case["wave"]] = time.time() + case["seconds_left"]
                if case["case_id"] not in started and case.get("seconds_left"):
                    if case["wave"] not in {c["wave"] for c in cases if c["case_id"] in started}:
                        log.warning("wave %s started: %s", case["wave"], case.get("theme"))
                    started[case["case_id"]] = pool.submit(one, case, functools.partial(caps.get, case["wave"]))
            time.sleep(poll)
    return {case_id: f.result() for case_id, f in started.items()}
