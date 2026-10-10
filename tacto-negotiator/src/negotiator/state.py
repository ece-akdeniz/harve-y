"""Durable request journal and in-memory thread state, so a restarted runner can resume.

Journal: append-only JSONL under the run dir, fsynced per record. Every logical POST writes an
`intent` (move id + exact payload + what the thread looked like) *before* the request leaves;
the outcome is a `done`, `failed` (definite HTTP error, e.g. 422) or `abandoned` (reconciled as
no longer valid). Retries reuse both move id and payload. Sessions are recorded on open so a
restart resumes them instead of opening a duplicate. Clocks are stored as UTC epoch seconds;
monotonic timestamps never cross a restart.
"""

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

OUTCOMES = ("done", "failed", "abandoned")


def new_move_id() -> str:
    return uuid.uuid4().hex


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.records: list[dict] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self.records.append(json.loads(line))
                    except json.JSONDecodeError:  # torn last line after a crash
                        break

    def _write(self, rec: dict) -> dict:
        rec = {"utc": time.time(), **rec}
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
            self.records.append(rec)
        return rec

    # -- writes --------------------------------------------------------------------------------
    def intent(self, case_id, session_id, supplier_id, kind, payload, **context) -> dict:
        """Persist a logical POST before sending it. kind: open | send | close."""
        return self._write(
            {
                "rec": "intent",
                "move_id": new_move_id(),
                "case": case_id,
                "session": session_id,
                "supplier": supplier_id,
                "kind": kind,
                "payload": payload,
                **context,
            }
        )

    def outcome(self, move_id: str, outcome: str, **fields) -> dict:
        assert outcome in OUTCOMES
        return self._write({"rec": outcome, "move_id": move_id, **fields})

    def session(self, case_id: str, session_id: str, case: dict | None = None) -> dict:
        return self._write({"rec": "session", "case": case_id, "session": session_id, "case_file": case})

    def result(self, case_id: str, session_id: str | None, result: dict) -> dict:
        return self._write({"rec": "result", "case": case_id, "session": session_id, "result": result})

    # -- reads ---------------------------------------------------------------------------------
    def session_for(self, case_id: str) -> str | None:
        """The session this run already opened for the case (latest), if any."""
        for rec in reversed(self.records):
            if rec.get("case") == case_id and rec["rec"] == "session":
                return rec["session"]
        return None

    def case_file(self, case_id: str) -> dict | None:
        for rec in reversed(self.records):
            if rec.get("case") == case_id and rec["rec"] == "session" and rec.get("case_file"):
                return rec["case_file"]
        return None

    def pending(self, session_id: str | None = None, case_id: str | None = None) -> list[dict]:
        """Intents without an outcome, oldest first."""
        closed = {r["move_id"] for r in self.records if r["rec"] in OUTCOMES}
        return [
            r
            for r in self.records
            if r["rec"] == "intent"
            and r["move_id"] not in closed
            and (session_id is None or r.get("session") == session_id)
            and (case_id is None or r.get("case") == case_id)
        ]

    def finished(self, case_id: str) -> dict | None:
        for rec in reversed(self.records):
            if rec.get("case") == case_id and rec["rec"] == "result":
                return rec["result"]
        return None


@dataclass
class ThreadState:
    supplier_id: str
    events: list[dict] = field(default_factory=list)  # all e-mails, oldest first
    deadline_utc: float | None = None  # when the buyer's 60 s window for this thread ends
    in_flight: str | None = None  # move id of the POST awaiting the supplier's reply
    parked: str | None = None  # why workers stopped proposing on this thread (it may still be accepted)
    closed: str | None = None  # server says the thread ended
    rejects: int = 0  # consecutive 422s
    timeouts: int = 0  # timeouts observed by this runner (409 late / session state)


@dataclass
class CaseState:
    case: dict
    session_id: str
    threads: dict[str, ThreadState] = field(default_factory=dict)
    deadline: float | None = None  # wall-clock wave cap
    slowest_round_s: float = 0.0
    ended: bool = False
    result: dict | None = None

    def snapshot(self) -> dict[str, list[dict]]:
        """{supplier: events} in the agent's format (copies; workers may append meanwhile)."""
        return {sid: list(t.events) for sid, t in self.threads.items()}
