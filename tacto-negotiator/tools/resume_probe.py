"""Sandbox-only crash/restart rehearsal on D02. Opens exactly one logical session.

caffeinate -i uv run --locked python tools/resume_probe.py
"""

import json
import os
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from arena_kit.cli import load_env
from arena_kit.client import ArenaClient


def records(path):
    out = []
    for line in path.read_text().splitlines() if path.exists() else []:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            break
    return out


def stop(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def main():
    load_env()
    root = Path("experiments/runs") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-resume-D02-" + uuid4().hex[:6]
    )
    root.mkdir(parents=True)
    journal = (root / "journal.jsonl").resolve()
    env = {**os.environ, "NEGOTIATOR_JOURNAL": str(journal), "NEGOTIATOR_CLAIMS": "0",
           "NEGOTIATOR_ESTIMATES": "0", "NEGOTIATOR_MESO": "0"}
    cmd = ["uv", "run", "--locked", "negotiator", "play", "case:D02", "--runner", "async"]
    before = ArenaClient(timeout=15, retries=0).me().get("practice")
    with (root / "interrupted.log").open("w") as log:
        first = subprocess.Popen(cmd, env={**env, "NEGOTIATOR_LOG_DIR": str(root / "interrupted")},
                                 stdout=log, stderr=log, start_new_session=True)
        try:
            limit = time.monotonic() + 60
            while time.monotonic() < limit and first.poll() is None:
                if any(r.get("rec") == "intent" and r.get("kind") == "send" for r in records(journal)):
                    break
                time.sleep(0.01)
        finally:
            stop(first)
    interrupted = records(journal)
    intents = [r for r in interrupted if r.get("rec") == "intent" and r.get("kind") == "send"]
    if not intents:
        raise SystemExit(f"No send intent observed; evidence saved at {root}")
    print(f"Interrupted after a persisted send intent; resuming the same journal: {root}", flush=True)
    with (root / "resumed.log").open("w") as log:
        second = subprocess.Popen(cmd, env={**env, "NEGOTIATOR_LOG_DIR": str(root / "resumed")},
                                  stdout=log, stderr=log, start_new_session=True)
        try:
            second.wait(timeout=480)
        finally:
            stop(second)
    rows = records(journal)
    sessions = {r["session"] for r in rows if r.get("rec") == "session"}
    opened = [r for r in rows if r.get("rec") == "intent" and r.get("kind") == "open"]
    done = {r["move_id"] for r in rows if r.get("rec") in ("done", "failed", "abandoned")}
    pending = [r["move_id"] for r in rows if r.get("rec") == "intent" and r["move_id"] not in done]
    client = ArenaClient(timeout=15, retries=0, rate=3)
    states, timeouts = {}, {}
    for sid in sessions:
        state = client.session(sid)
        states[sid] = state
        for supplier in state.get("threads", {}):
            thread = client.thread(sid, supplier)
            timeouts[supplier] = len(thread.get("timeouts") or [])
    (root / "server-states.json").write_text(json.dumps(states, indent=2))
    result = next(iter(states.values()), {}).get("result") or {}
    out = {"sessions": sorted(sessions), "open_intents": len(opened), "pending": pending,
           "returncode": second.returncode, "deal": result.get("deal"), "score": result.get("score"),
           "must_haves_ok": result.get("must_haves_ok"), "timeouts": timeouts,
           "quota_before": before, "quota_after": client.me().get("practice")}
    (root / "summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out), flush=True)
    return 0 if (len(sessions) == len(opened) == 1 and not pending and result.get("deal")
                 and result.get("must_haves_ok") and not any(timeouts.values()) and second.returncode == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
