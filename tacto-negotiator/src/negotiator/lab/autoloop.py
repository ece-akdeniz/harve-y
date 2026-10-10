"""Persistent VM learning worker. No model is allowed to spend quota or promote policy."""

import argparse
import fcntl
import json
import signal
import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from ..ingestion import fingerprint
from .campaign import arena_snapshot, run_campaign
from .checkpoints import create_checkpoint, publish_checkpoint, restore_checkpoint
from .learning import PERMITTED_CHANGES, TERMINAL, LearningStore
from .loop_store import LoopStore
from .policy import evaluate_campaign
from .worker import durable_json


def status(db_path):
    with sqlite3.connect(db_path, timeout=10) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='worker_goal'").fetchone():
            return None
        row = db.execute("SELECT body FROM worker_goal WHERE id=1").fetchone()
    return json.loads(row[0]) if row else None


class ReviewedClient:
    """The executor cannot invoke the legacy automatic-promotion path."""

    def __init__(self, store, freeze=float("inf")):
        self.store = store
        self.freeze = freeze

    def read(self, *args):
        return self.store.read(*args)

    def write(self, operation, body):
        if operation == "attempt-start" and time.time() >= self.freeze:
            raise ValueError("hosted starts frozen")
        if operation == "complete":
            campaign = self.read("campaigns", body["campaign_id"])
            if not campaign.get("completion"):
                proposals = self.read("learning-proposals")["learning-proposals"]
                registered = any(p.get("checkpoint_id") == campaign["candidate_id"]
                                 and p["status"] == "registered" for p in proposals)
                if not registered:
                    evaluation = evaluate_campaign(
                        self.read("suites", campaign["suite_id"]),
                        self.read("checkpoints", campaign["baseline_id"]),
                        self.read("checkpoints", campaign["candidate_id"]), campaign["attempts"])
                    if evaluation["eligible"]:
                        return {"campaign_id": campaign["campaign_id"], "status": "awaiting_review",
                                "evaluation": evaluation}
        if operation in {"seed", "restore", "learning-review"}:
            raise ValueError("worker cannot change recommendations")
        return self.store.write(operation, body)


class Worker:
    def __init__(self, db_path, config):
        self.db_path = Path(db_path)
        self.config = config
        self.root = Path(config["root"])
        self.root.mkdir(parents=True, exist_ok=True)
        if config.get("target_score") != 99 or config.get("environment") != "sandbox":
            raise ValueError("worker requires explicit sandbox goal and 99/100 target")
        if type(config.get("max_sessions")) is not int or config["max_sessions"] < 1:
            raise ValueError("explicit session ceiling required")
        self.freeze = datetime.fromisoformat(config["freeze_at"]).timestamp()
        self.learning = LearningStore(db_path)
        self.client = ReviewedClient(LoopStore(db_path), self.freeze)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS worker_goal (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS worker_events (
                    id INTEGER PRIMARY KEY, created_at REAL NOT NULL, body TEXT NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def record(self, state, **details):
        body = {"goal": "Repeatable 99/100 through reviewed lab comparisons", "target_score": 99,
                "host": "lab-vm", "state": state, "updated_at": time.time(),
                "family_id": self.config["family_id"], "max_sessions": self.config["max_sessions"],
                "promotion": "teammate_review", **details}
        previous = status(self.db_path)
        with self.connect() as db:
            db.execute("INSERT INTO worker_goal VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                       (json.dumps(body),))
            if ({k: v for k, v in body.items() if k != "updated_at"} !=
                    {k: v for k, v in (previous or {}).items() if k != "updated_at"}):
                db.execute("INSERT INTO worker_events(created_at,body) VALUES(?,?)",
                           (body["updated_at"], json.dumps(body)))
        return body

    def feedback(self):
        # Each tick does bounded work. Failed/stale reports stay retryable and visible.
        reviewed = []
        for run in self.learning.store.all():
            if run.status not in TERMINAL:
                continue
            current = self.learning.status(run.run_id)
            if current.get("state") == "ready" and current.get("source_sha256") == fingerprint(run.model_dump()):
                continue
            try:
                self.learning.review(run.run_id)
                reviewed.append({"run_id": run.run_id, "state": "ready"})
            except Exception as error:
                reviewed.append({"run_id": run.run_id, "state": "failed", "error": type(error).__name__})
            if len(reviewed) >= 2:
                break
        return reviewed

    def tick(self):
        feedback = self.feedback()
        family = self.client.read("families", self.config["family_id"])
        if family["max_sessions"] != self.config["max_sessions"] or family["practice_allowance"]:
            raise ValueError("lab family differs from approved sandbox ceiling")
        suite = self.client.read("suites", self.config["suite_id"])
        if suite["environment"] != "sandbox" or suite["runner"] != "async":
            raise ValueError("explicit async sandbox suite required")
        common = {"reserved_sessions": family["reserved_sessions"], "feedback": feedback}
        campaigns = [c for c in self.client.read("campaigns")["campaigns"]
                     if c["family_id"] == family["family_id"]]
        for campaign in campaigns:
            if campaign.get("completion"):
                self.finding(campaign)
        active = [c for c in campaigns if not c.get("completion")]
        if len(active) > 1:
            return self.record("blocked_multiple_campaigns", **common)
        if active:
            campaign = active[0]
            blockers = [a["attempt_id"] for a in campaign["attempts"] if a["status"] == "started" or
                        ("start" in a and not a.get("reconciliation") and not a.get("not_created")
                         and a.get("result", {}).get("ended") is not True)]
            if blockers:
                if (self.config.get("recover_original_start") is True and time.time() < self.freeze
                        and len(blockers) == 1):
                    from .start_recovery import recover_start

                    attempt = next(a for a in campaign["attempts"] if a["attempt_id"] == blockers[0])
                    if attempt["status"] == "ambiguous" and not attempt.get("session_id"):
                        self.record("recovering_original_start", campaign_id=campaign["campaign_id"], **common)
                        recovered = recover_start(self.client, campaign, attempt, Path(self.config["project"]),
                                                  self.root, self.config["data_paths"])
                        return self.record("reconciled" if recovered.get("reconciliation") else
                                           "recovery_incomplete", campaign_id=campaign["campaign_id"], **common)
                return self.record("blocked_reconciliation", campaign_id=campaign["campaign_id"],
                                   blocking_attempts=blockers, **common)
            if time.time() >= self.freeze:
                return self.record("frozen", campaign_id=campaign["campaign_id"], **common)
            self.record("executing", campaign_id=campaign["campaign_id"], **common)
            result = run_campaign(self.client, campaign["campaign_id"], Path(self.config["project"]),
                                  self.root, data_paths=self.config["data_paths"])
            completion = result.get("completion")
            if completion:
                self.finding({**campaign, "completion": completion})
                return self.record("awaiting_review" if completion["status"] == "awaiting_review"
                                   else "evaluated", campaign_id=campaign["campaign_id"],
                                   evaluation=completion, **common)
            return self.record("reconciling", campaign_id=campaign["campaign_id"], **common)
        if any(c.get("status") == "awaiting_review" for c in campaigns):
            return self.record("awaiting_review", **common)
        # A score is achieved only on a reviewed recommendation, with all original repetitions
        # meeting the target. Sandbox evidence does not prove unseen/final readiness.
        recommended = self.client.read("recommended", suite["suite_id"])
        for campaign in campaigns:
            samples = [a for a in campaign["attempts"] if a["arm"] == "candidate"]
            if (campaign["status"] == "promoted" and recommended["checkpoint_id"] == campaign["candidate_id"]
                    and samples and all(a["status"] == "completed" and a.get("score", -1) is not None
                                        and a["score"] >= .99 for a in samples)):
                return self.record("suite_target_achieved", campaign_id=campaign["campaign_id"], **common)
        if time.time() >= self.freeze:
            return self.record("frozen", **common)
        if family["max_sessions"] - family["reserved_sessions"] < suite["max_sessions"]:
            return self.record("waiting_budget", **common)
        proposals = self.client.read("learning-proposals")["learning-proposals"]
        tested = {c["candidate_id"] for c in campaigns}
        baseline = self.client.read("checkpoints", recommended["checkpoint_id"])
        for proposal in proposals:
            if proposal["status"] not in {"draft", "registered"} or proposal.get("checkpoint_id") in tested:
                continue
            if proposal["config_patch"] != PERMITTED_CHANGES.get(proposal["kind"]):
                continue
            if {**baseline["config"], **proposal["config_patch"]} == baseline["config"]:
                continue
            return self.prepare(proposal, baseline, suite, recommended, common)
        return self.record("waiting_evidence", **common)

    def finding(self, campaign):
        identity = "vm-review-" + campaign["campaign_id"]
        if any(f["finding_id"] == identity for f in self.client.read("findings")["findings"]):
            return
        references = [{"attempt_id": a["attempt_id"], "supplier": supplier, "message_index": 0}
                      for a in campaign["attempts"] for supplier, messages in a.get("threads", {}).items()
                      if isinstance(messages, list) and messages][:20]
        if not references:
            return
        evaluation = campaign["completion"]["evaluation"]
        self.client.write("finding", {
            "finding_id": identity, "campaign_id": campaign["campaign_id"],
            "candidate_id": campaign["candidate_id"], "author": "ece-vm-loop",
            "observation": json.dumps({"failed_gates": evaluation["evidence_gaps"],
                                       "cases": evaluation["cases"], "metrics": evaluation["metrics"]})[:3900],
            "hypothesis": campaign["hypothesis"],
            "change": "Immutable candidate " + campaign["candidate_id"],
            "next_test": "Review every gate and cited attempt; test one supported configuration proposal "
                         "only when the family has approved budget. Code changes require engineering work.",
            "confidence": 0.5, "disposition": "tested", "evidence": references})

    def prepare(self, proposal, baseline, suite, recommended, common):
        """One immutable config hypothesis, published before any budget reservation/start."""
        identity = proposal["proposal_id"]
        self.record("preparing_candidate", proposal_id=identity, **common)
        if proposal["status"] == "registered":
            candidate = self.client.read("checkpoints", proposal["checkpoint_id"])
            if candidate["parent_id"] != baseline["checkpoint_id"]:
                return self.record("blocked_stale_proposal", proposal_id=identity, **common)
        else:
            destination = self.root / ("proposal-" + identity)
            if not destination.exists():
                project = restore_checkpoint(Path(self.config["project"]), baseline, destination,
                                             data_paths=self.config["data_paths"])
            else:
                project = destination / baseline["project_path"]
            saved = self.root / ("candidate-" + identity + ".json")
            if saved.exists():
                candidate = json.loads(saved.read_text())
            else:
                checked = subprocess.run(["uv", "run", "--locked", "--offline", "pytest", "-q"],
                                         cwd=project, capture_output=True, timeout=300)
                if checked.returncode:
                    raise ValueError("candidate local checks failed")
                candidate = create_checkpoint(
                    project, config={**baseline["config"], **proposal["config_patch"]},
                    runner=baseline["runner"], author="ece-vm-loop", description=proposal["hypothesis"],
                    parent_id=baseline["checkpoint_id"], data=baseline["data"], root=self.root / "checkpoints")
                durable_json(saved, candidate)
            candidate = publish_checkpoint(project, candidate)
            self.client.write("checkpoint", candidate)
            self.client.write("learning-register", {"proposal_id": identity,
                                                    "checkpoint_id": candidate["checkpoint_id"]})
        campaign_id = "vm-" + fingerprint([self.config["family_id"], identity, recommended["generation"]])[:24]
        self.client.write("campaign", {"campaign_id": campaign_id, "family_id": self.config["family_id"],
                                       "suite_id": suite["suite_id"], "baseline_id": baseline["checkpoint_id"],
                                       "candidate_id": candidate["checkpoint_id"],
                                       "generation": recommended["generation"], "seed": 0,
                                       "author": "ece-vm-loop", "hypothesis": proposal["hypothesis"],
                                       "quota": arena_snapshot(suite)})
        return self.record("queued", campaign_id=campaign_id, **common)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    worker = Worker(args.db, json.loads(args.config.read_text()))
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    with (worker.root / "vm-worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while not stop.is_set():
            try:
                worker.tick()
            except Exception as error:
                # Never persist exception text: transport errors may contain credentials/prose.
                worker.record("retryable_error", error_code=type(error).__name__)
            if args.once:
                break
            stop.wait(max(10, int(worker.config.get("interval_s", 30))))


if __name__ == "__main__":
    main()
