"""Recover a migrated ambiguous start using only its original persisted move ID."""

import asyncio
import fcntl
import hashlib
import json

from ..client import AsyncArena
from ..state import Journal
from .campaign import campaign_dir, load_state, outcome, reconcile_attempt
from .execution import launch_worker, prepare_arms
from .worker import durable_json


def original_start(root, campaign, attempt):
    """Require durable original executor ownership and unchanged original evidence."""
    directory = campaign_dir(root, campaign["campaign_id"])
    saved = load_state(root, campaign["campaign_id"])
    owner = saved.get("start_requests", {}).get(attempt["attempt_id"])
    if (not owner or owner != attempt.get("start", {}).get("request") or
            attempt["status"] != "ambiguous" or attempt.get("session_id")):
        raise ValueError("ambiguous start ownership unavailable")
    path = directory / "attempts" / hashlib.sha256(attempt["attempt_id"].encode()).hexdigest()
    result = json.loads((path / "result.json").read_text())
    if result.get("final") is not True or outcome(result) != attempt.get("outcome"):
        raise ValueError("original outcome mismatch")
    records = [json.loads(line) for line in (path / "journal.jsonl").read_text().splitlines() if line]
    if len(records) != 1:
        raise ValueError("recovery requires exactly one unresolved open intent")
    intent = records[0]
    if (intent.get("rec") != "intent" or intent.get("kind") != "open" or
            intent.get("case") != attempt["case_id"] or intent.get("session") is not None or
            intent.get("payload") != {"case_id": attempt["case_id"]} or not intent.get("move_id")):
        raise ValueError("original open intent mismatch")
    return directory, path, intent


def recover_start(client, campaign, attempt, project, root, data_paths):
    directory, original, intent = original_start(root, campaign, attempt)
    with (directory / "execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        suite = client.read("suites", campaign["suite_id"])
        manifests, projects, paths = prepare_arms(client, campaign, project, directory, data_paths, suite)
        recovery = original / "recovery"
        recovery.mkdir(exist_ok=True)
        journal_path = recovery / "journal.jsonl"
        if not journal_path.exists():
            # Preserve the original journal. Only this recovery copy may be extended.
            journal_path.write_bytes((original / "journal.jsonl").read_bytes())
        receipt = recovery / "open-receipt.json"

        async def resolve():
            arena = AsyncArena(base_url=suite["arena_url"], retries=2, calls_per_s=1)
            try:
                if receipt.exists():
                    opened = json.loads(receipt.read_text())
                else:
                    # No fresh ID, no fallback to a different running session on 409.
                    opened = await arena.open_session(intent["case"], intent["move_id"])
                    if opened.get("case", {}).get("case_id") != intent["case"]:
                        raise ValueError("recovered session case mismatch")
                    durable_json(receipt, opened)
                current = await arena.session(opened["session_id"])
                return opened, current
            finally:
                await arena.aclose()

        opened, current = asyncio.run(resolve())
        journal = Journal(journal_path)
        if journal.session_for(intent["case"]) is None:
            journal.outcome(intent["move_id"], "done", session=opened["session_id"])
            journal.session(intent["case"], opened["session_id"], opened["case"])
        if current.get("ended") is not True:
            if (recovery / "result.json").exists():
                return {"state": "recovery_incomplete", "session_id": opened["session_id"]}
            request = {
                "checkpoint": manifests[attempt["arm"]], "project": str(projects[attempt["arm"]]),
                "attempt": attempt, "attempt_root": str(recovery), "arena_url": suite["arena_url"],
                "environment": suite["environment"], "data_paths": paths,
                "worker_id": attempt["start"]["request"]["worker_id"],
            }
            launch_worker(request, lock_fd=lock.fileno())
        # This appends recovery evidence; it never replaces the original failed sample.
        return reconcile_attempt(client, campaign["campaign_id"], attempt["attempt_id"], opened["session_id"])
