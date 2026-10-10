"""Full local simulator dialogues; socket connections blocked, no hosted or model calls.

Uses the test suite's in-memory transport and fault injection. The kit supplier has a
fixed price script: results validate mechanics, not persuasive or hosted performance.
Run with ARENA_DATA pointing at the public package and --output-dir under experiments/runs.
"""
import argparse
import asyncio
import importlib.util
import json
import socket
import subprocess
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from arena_kit.cost import must_haves_ok
from arena_kit.docs import standard_terms

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig
from negotiator.runner import CaseRunner, Clock
from negotiator.state import Journal
from negotiator.trace import Tracer

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sim_transport", ROOT / "tests/test_runner.py")
TRANSPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRANSPORT)


async def dialogue(case_id, name, policy, directory):
    directory.mkdir(parents=True, exist_ok=False)
    wave = name == "wave_deadline"
    clock = TRANSPORT.ScaledClock() if wave else Clock()
    arena = TRANSPORT.SimArena(clock, {"sup:70340": 30, "sup:70360": 30} if wave else {})
    if name == "lost_reply":
        arena.lose_reply = True
    if name == "stale_close":
        arena.fail_next_close = 422
    journal, trace = Journal(directory / "journal.jsonl"), Tracer(directory)
    agent = PackageAgent(policy=policy, estimates={}, meso=False, claims=False, tracer=trace)
    cap = clock.time() + 150 if wave else None
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("local simulation forbids network")):
        result = await asyncio.wait_for(CaseRunner(
            arena, case_id, agent, journal, clock=clock, tracer=trace,
            deadline=(lambda: cap) if wave else None,
        ).run(), timeout=20)
    ended_at = clock.time()
    session = arena.sim.sessions[result["session_id"]]
    threads = {sid: arena._do(arena.sim.thread, result["session_id"], sid)
               for sid in session["threads"]}
    evidence = {"result": result, "threads": threads}
    (directory / "dialogue.json").write_text(json.dumps(evidence, indent=2) + "\n")
    invalid_proposals = []
    for sid, thread in threads.items():
        events = thread["messages"]
        for i, message in enumerate(events):
            if message.get("from") != "buyer":
                continue
            for sheet in message.get("term_sheets") or []:
                if not must_haves_ok(arena.sim.cases[case_id], sheet["terms"], standard_terms(events[:i+1])):
                    invalid_proposals.append([sid, i])
    failures = [r for r in journal.records if r["rec"] == "failed"]
    intents = {r["move_id"]: r for r in journal.records if r["rec"] == "intent"}
    unresolved = journal.pending()
    recovered_close_errors = all(
        r.get("http") == 422 and intents[r["move_id"]]["kind"] == "close" for r in failures
    )
    expected_errors = (not failures if name not in ("stale_close", "wave_deadline")
                       else recovered_close_errors and len(failures) <= 1)
    if name == "stale_close":
        expected_errors = expected_errors and len(failures) == 1
    row = {"case": case_id, "scenario": name, "policy": policy.record(), "result": result,
           "local_opens": arena.opens, "invalid_proposals": invalid_proposals,
           "failed_requests": [{"kind": intents[r["move_id"]]["kind"], "http": r.get("http")}
                               for r in failures],
           "strict_zero_rejections": not failures,
           "before_wave_deadline": ended_at < cap if cap else None,
           "unresolved_requests": len(unresolved),
           "rounds": {sid: t["round"] for sid, t in session["threads"].items()},
           "artifacts": str(directory)}
    row["passed"] = bool(result.get("deal") and not invalid_proposals and not unresolved
                         and not any(result.get("thread_timeouts", {}).values())
                         and arena.opens == 1
                         and result.get("must_haves_ok") is True and expected_errors
                         and (cap is None or ended_at < cap))
    return row


async def run(output):
    candidate = PolicyConfig.load(ROOT / "configs/local-response-experiment.json")
    baseline = replace(candidate, response_types=(), free_concessions=False, rfq_close_guard=False)
    scenarios = [(f"case:S0{i}", "normal") for i in (1, 2, 3)]
    scenarios += [("case:S02", n) for n in ("lost_reply", "stale_close", "wave_deadline")]
    rows = []
    for case_id, scenario in scenarios:
        for arm, policy in (("baseline", baseline), ("candidate", candidate)):
            row = await dialogue(case_id, scenario, policy, output / f"{case_id[5:]}-{scenario}-{arm}")
            row["arm"] = arm
            rows.append(row)
            print(arm, case_id, scenario, "score", row["result"].get("score"), "passed", row["passed"], flush=True)
    report = {"source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "hosted_sessions": 0, "model_calls": 0, "network_connections": "blocked during dialogues",
              "interpretation": "Full dialogues against fixed-price kit suppliers, not hosted score predictions.",
              "baseline": "Same package configuration with the three response experiment flags disabled.",
              "passed": all(r["passed"] for r in rows), "rows": rows}
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.output_dir.resolve())))
