"""Recorded, sandbox-only baseline. No model calls or practice sessions.

uv run --locked python tools/sandbox_baseline.py --agent naive
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from arena_kit.agents.naive import NaiveAgent
from arena_kit.cli import load_env
from arena_kit.client import ArenaClient
from arena_kit.play import RemoteTable, play


class RecordedClient(ArenaClient):
    def __init__(self, log):
        super().__init__(rate=3.0)
        self.log = log
        self.log_lock = threading.Lock()

    def _call(self, method, path, body=None, params=None, raw=False):
        started, wall = time.monotonic(), datetime.now(UTC).isoformat()
        record = {"utc": wall, "method": method, "path": path, "payload": body}
        try:
            response = super()._call(method, path, body, params, raw)
            record["response"] = {"bytes": len(response)} if raw else response
            return response
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            record["status"] = getattr(exc, "status", None)
            raise
        finally:
            record["elapsed_s"] = round(time.monotonic() - started, 3)
            with self.log_lock:
                with self.log.open("a") as stream:
                    stream.write(json.dumps(record) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["naive", "package"], default="naive")
    parser.add_argument("--case", choices=["case:D01", "case:D02"], action="append")
    args = parser.parse_args()
    load_env()
    run = Path("experiments/runs") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-sandbox-{args.agent}-" + uuid4().hex[:6]
    )
    run.mkdir(parents=True)
    client = RecordedClient(run / "requests.jsonl")
    before = client.me()
    (run / "quota-before.json").write_text(json.dumps(before, indent=2))
    cases = client.cases("sandbox")
    (run / "cases.json").write_text(json.dumps(cases, indent=2))
    allowed = {c["case_id"] for c in cases}
    requested = args.case or ["case:D01", "case:D02"]
    if not set(requested) <= allowed:
        raise SystemExit("Requested sandbox case unavailable")
    print(f"Recording {args.agent} sandbox baseline to {run}", flush=True)

    def run_case(case_id):
        table = RemoteTable(client)
        started = time.monotonic()
        try:
            if args.agent == "package":
                from negotiator.agent import PackageAgent

                agent = PackageAgent()
            else:
                agent = NaiveAgent()
            result = play(table, case_id, agent, deadline=time.time() + 480)
            state = client.session(table.session_id)
            threads = {s: client.thread(table.session_id, s) for s in state.get("threads", {})}
            saved = {
                "case": case_id,
                "session": table.session_id,
                "result": result,
                "state": state,
                "threads": threads,
                "elapsed_s": time.monotonic() - started,
            }
            (run / (case_id.replace(":", "-") + ".json")).write_text(json.dumps(saved, indent=2))
            summary = {
                "case": case_id,
                "session": table.session_id,
                "score": result.get("score"),
                "deal": result.get("deal"),
                "must_haves_ok": result.get("must_haves_ok"),
                "c_deal": result.get("c_deal"),
                "c_best": result.get("c_best"),
                "elapsed_s": round(saved["elapsed_s"], 2),
                "thread_timeouts": {s: len(t.get("timeouts") or []) for s, t in threads.items()},
            }
            print(json.dumps(summary), flush=True)
            return summary
        except Exception as exc:
            summary = {
                "case": case_id,
                "session": table.session_id,
                "error_type": type(exc).__name__,
                "status": getattr(exc, "status", None),
            }
            (run / (case_id.replace(":", "-") + "-error.json")).write_text(json.dumps(summary))
            print(json.dumps(summary), flush=True)
            return summary

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run_case, requested))
    after = client.me()
    (run / "quota-after.json").write_text(json.dumps(after, indent=2))
    (run / "summary.json").write_text(json.dumps(outcomes, indent=2))
    print("Practice quota after sandbox:", json.dumps(after.get("practice")), flush=True)
    if any("error_type" in r for r in outcomes):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
