"""One durable, session-wide reservation ledger for live inference attempts.

An unknown or timed-out attempt stays charged. The ledger stores digests and usage
only; request text, supplier prose and credentials never enter it.
"""

import fcntl
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path


class SessionModelBudget:
    def __init__(self, *, max_calls=8, total_s=32.0, decision_reserve_s=8.0,
                 validation_reserve_s=0.0):
        self.max_calls, self.total_s = max_calls, total_s
        self.decision_reserve_s = decision_reserve_s
        self.validation_reserve_s = validation_reserve_s
        self.session_id = None
        self.path = None
        self.rows = []
        self.corrupt = False
        self.lock = threading.Lock()

    def bind(self, session_id, journal_path=None):
        if not session_id:
            return
        if self.session_id == session_id:
            return
        if self.session_id is not None:
            raise ValueError("cannot rebind a model budget to a different session")
        self.session_id = session_id
        self.path = Path(journal_path).with_name("model-budget.jsonl") if journal_path else None
        if self.path and self.path.is_file():
            self.path.chmod(0o600)
            with self.path.open(encoding="utf-8") as stream:
                try:
                    self.rows = self._read(stream)
                except ValueError:
                    self.corrupt = True

    def _read(self, stream):
        rows = []
        stream.seek(0)
        for line in stream:
            try:
                row = json.loads(line)
                if (row.get("record") == "model_reservation"
                        and isinstance(row.get("session_id"), str)
                        and isinstance(row.get("supplier_id"), str)
                        and isinstance(row.get("role"), str)
                        and isinstance(row.get("update_hash"), str)
                        and isinstance(row.get("request_digest"), str)
                        and type(row.get("seconds")) in (int, float)
                        and 0 < row["seconds"] <= 8):
                    if row["session_id"] == self.session_id:
                        rows.append(row)
                else:
                    raise ValueError("invalid model budget row")
            except (ValueError, TypeError):
                raise ValueError("corrupt model budget ledger") from None
        return rows

    def reserve(self, role, supplier_id, update_hash, request_digest, seconds, *,
                remaining_s, optional=False, closing_reserve_s=20.0):
        if not self.session_id:
            return True, "unbound", seconds
        if self.corrupt:
            return False, "ledger_corrupt", 0.0
        if remaining_s is None or remaining_s <= closing_reserve_s + seconds:
            return False, "deadline_reserve", 0.0
        row = {"record": "model_reservation", "session_id": self.session_id,
               "supplier_id": supplier_id, "role": role, "update_hash": update_hash,
               "request_digest": request_digest, "seconds": seconds}
        with self.lock:
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
                self.path.chmod(0o600)
                with os.fdopen(descriptor, "a+", encoding="utf-8") as stream:
                    fcntl.flock(stream, fcntl.LOCK_EX)
                    try:
                        try:
                            rows = self._read(stream)
                        except ValueError:
                            self.corrupt = True
                            return False, "ledger_corrupt", 0.0
                        result = self._admit(rows, row, optional)
                        if result[0]:
                            stream.seek(0, os.SEEK_END)
                            stream.write(json.dumps(row, sort_keys=True) + "\n")
                            stream.flush()
                            os.fsync(stream.fileno())
                            self.rows = [*rows, row]
                        return result
                    finally:
                        fcntl.flock(stream, fcntl.LOCK_UN)
            result = self._admit(self.rows, row, optional)
            if result[0]:
                self.rows.append(row)
            return result

    def _admit(self, rows, row, optional):
        if any((r["role"], r["supplier_id"], r["update_hash"], r["request_digest"]) ==
               (row["role"], row["supplier_id"], row["update_hash"], row["request_digest"])
               for r in rows):
            return False, "already_reserved", 0.0
        calls = len(rows)
        spent = sum(r["seconds"] for r in rows)
        if calls >= self.max_calls or spent + row["seconds"] > self.total_s + 1e-9:
            return False, "budget_exhausted", 0.0
        if (self.validation_reserve_s and row["role"] != "validation-repair-v1"
                and not any(r["role"] == "validation-repair-v1" for r in rows)
                and (calls + 1 >= self.max_calls
                     or spent + row["seconds"] + self.validation_reserve_s > self.total_s + 1e-9)):
            return False, "validation_budget_reserved", 0.0
        if optional and (calls + 1 >= self.max_calls
                         or spent + row["seconds"] + self.decision_reserve_s > self.total_s + 1e-9):
            return False, "decision_budget_reserved", 0.0
        return True, "reserved", row["seconds"]

    def metrics(self):
        with self.lock:
            rows = list(self.rows)
        by_role = {}
        for row in rows:
            role = by_role.setdefault(row["role"], {"calls": 0, "reserved_s": 0.0})
            role["calls"] += 1
            role["reserved_s"] += row["seconds"]
        return {"session_id": self.session_id, "calls": len(rows),
                "reserved_s": sum(row["seconds"] for row in rows), "by_role": by_role,
                "max_calls": self.max_calls, "total_s": self.total_s,
                "validation_reserve_s": self.validation_reserve_s}

    def artifact(self, role, request_digest, context, *, response=None, error=None):
        """Private bounded replay evidence, separate from sanitized shared traces."""
        try:
            return self._artifact(role, request_digest, context, response=response, error=error)
        except OSError:
            return False

    def _artifact(self, role, request_digest, context, *, response=None, error=None):
        if not self.path:
            return False
        directory = self.path.with_name("model-evidence")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
        payload = {"session_id": self.session_id, "role": role,
                   "request_digest": request_digest,
                   "request": json.dumps(context, ensure_ascii=False, default=str)[:16000],
                   "response": json.dumps(response, ensure_ascii=False, default=str)[:16000]
                   if response is not None else None,
                   "error_code": getattr(error, "code", type(error).__name__) if error else None,
                   "raw_response": getattr(error, "raw", None)}
        path = directory / (uuid.uuid4().hex + ".json")
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        cutoff = time.time() - 30 * 86400
        for old in directory.glob("*.json"):
            if re.fullmatch(r"[0-9a-f]{32}\.json", old.name) and old.stat().st_mtime < cutoff:
                old.unlink(missing_ok=True)
        return True
