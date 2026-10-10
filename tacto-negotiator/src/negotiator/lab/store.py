"""Atomic SQLite snapshots, immutable plans and durable cross-source recovery evidence."""

import json
import sqlite3
from pathlib import Path

from .models import MANIFEST_FIELDS, Run, compare, summarize, timestamp
from .reconcile import (
    attach_recovered,
    known_score,
    official_result,
    original_result,
    preserve_recovered,
    recovered_result,
)


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    arena TEXT NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
                    PRIMARY KEY(arena, session_id)
                );
            """)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _write(db, body):
        validated = Run.model_validate(body).model_dump()
        db.execute(
            "INSERT INTO runs VALUES (?, ?, ?) ON CONFLICT(run_id) DO UPDATE SET "
            "revision=excluded.revision, body=excluded.body",
            (validated["run_id"], validated["revision"], json.dumps(validated, allow_nan=False)),
        )

    @staticmethod
    def _add_recovery(db, owner: dict, session_id: str, outcome: dict) -> bool:
        for attempt in owner["attempts"]:
            if attempt["session_id"] == session_id and attach_recovered(attempt, outcome):
                # Keep the laptop writer's revision and timestamps. Polling recovered-count detects
                # this additive change without making its next numbered upload stale.
                Store._write(db, owner)
                return True
        return False

    def reconcile(self, run_id: str, session_id: str, outcome: dict) -> bool:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM runs WHERE run_id=?", (run_id,)).fetchone()
            return self._add_recovery(db, json.loads(row[0]), session_id, outcome) if row else False

    def _check_previous(self, previous: dict, body: dict):
        if any(previous[key] != body[key] for key in MANIFEST_FIELDS):
            raise Conflict("run manifest is immutable")
        if previous["status"] != "running" and body["status"] == "running":
            raise Conflict("run status cannot regress")
        old_attempts = {a["attempt_id"]: a for a in previous["attempts"]}
        for attempt in body["attempts"]:
            before = old_attempts.get(attempt["attempt_id"])
            if before is None or (before["session_id"] and before["session_id"] != attempt["session_id"]):
                raise Conflict("attempt identity is immutable")
            preserve_recovered(before, attempt)
            imported_retry = (
                body["source"] == "imported"
                and before["score"] is None
                and attempt["status"] == "completed"
                and known_score(attempt["score"])
                and before["error"] == attempt["error"]
            )
            if before["status"] in {"completed", "failed"} and not imported_retry:
                if (
                    before["status"] != attempt["status"]
                    or before["score"] != attempt["score"]
                    or original_result(before["result"]) != original_result(attempt["result"])
                ):
                    raise Conflict("finished attempts are immutable")

    def upsert(self, run: Run) -> bool:
        body = run.model_dump()
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute("SELECT revision, body FROM runs WHERE run_id=?", (run.run_id,)).fetchone()
                if old and old[0] >= run.revision:
                    previous = json.loads(old[1])
                    if all(previous[key] == body[key] for key in MANIFEST_FIELDS):
                        for attempt in body["attempts"]:
                            outcome = recovered_result(attempt)
                            if attempt["session_id"] and outcome:
                                self._add_recovery(db, previous, attempt["session_id"], outcome)
                    return False
                if old:
                    self._check_previous(json.loads(old[1]), body)
                sessions = [a["session_id"] for a in body["attempts"] if a["session_id"]]
                if len(set(sessions)) != len(sessions):
                    raise Conflict("duplicate arena session")
                replaced_imports = set()
                for attempt in body["attempts"]:
                    session = attempt["session_id"]
                    if not session:
                        continue
                    owner = db.execute(
                        "SELECT run_id FROM sessions WHERE arena=? AND session_id=?", (run.arena_url, session)
                    ).fetchone()
                    if not owner or owner[0] == run.run_id:
                        continue
                    owner_body = json.loads(
                        db.execute("SELECT body FROM runs WHERE run_id=?", (owner[0],)).fetchone()[0]
                    )
                    if run.source == "imported":
                        outcome = official_result(attempt)
                        if outcome:
                            self._add_recovery(db, owner_body, session, outcome)
                        return False
                    if owner_body["source"] != "imported" or len(owner_body["attempts"]) != 1:
                        raise Conflict("arena session already belongs to a run")
                    outcome = official_result(owner_body["attempts"][0])
                    if outcome:
                        attach_recovered(attempt, outcome)
                    replaced_imports.add(owner[0])
                # Preserve every official history outcome before restoring tracked provenance.
                # Later active/failure uploads inherit it without changing their original metrics.
                Run.model_validate(body)
                for owner_id in replaced_imports:
                    db.execute("DELETE FROM sessions WHERE run_id=?", (owner_id,))
                    db.execute("DELETE FROM runs WHERE run_id=?", (owner_id,))
                for session in sessions:
                    db.execute("INSERT OR IGNORE INTO sessions VALUES (?, ?, ?)", (run.arena_url, session, run.run_id))
                self._write(db, body)
        except ValueError as error:
            if isinstance(error, Conflict):
                raise
            raise Conflict("invalid or conflicting recovery evidence") from None
        return True

    def get(self, run_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT body FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self) -> list[Run]:
        with self._connect() as db:
            rows = db.execute("SELECT body FROM runs ORDER BY json_extract(body, '$.started_at') DESC").fetchall()
        return [Run.model_validate(json.loads(row[0])) for row in rows]

    def listing(self) -> dict:
        runs = self.all()
        quotas = [r.quota for r in runs if r.quota]
        latest = max(quotas, key=lambda q: timestamp(q.checked_at)) if quotas else None
        return {
            "runs": [summarize(run) for run in runs],
            "quota": latest.model_dump() if latest else None,
            "team": "y/agent",
        }

    def comparison(self, baseline: str, candidate: str) -> dict | None:
        left, right = self.get(baseline), self.get(candidate)
        return compare(Run.model_validate(left), Run.model_validate(right)) if left and right else None
