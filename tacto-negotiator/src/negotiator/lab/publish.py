"""Durable local snapshots and best-effort upload outside the negotiation loop."""

import json
import os
import threading
from pathlib import Path

import httpx

from .models import MANIFEST_FIELDS, Run, safe_url
from .reconcile import attach_recovered, recovered_result


def _atomic_file(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def save_snapshot(run: Run, root: Path, *, patch: str | None = None) -> Path:
    validated = Run.model_validate(run.model_dump())
    directory = Path(root) / validated.run_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if patch is not None:
        _atomic_file(directory / "source.patch", patch)
    path = directory / "run.json"
    _atomic_file(
        path, json.dumps(validated.model_dump(), ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    )
    return path


def load_snapshots(root: Path):
    for path in sorted(Path(root).glob("*/run.json")):
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("saved snapshot exceeds the size limit")
        run = Run.model_validate_json(path.read_text())
        recovery = path.parent / "reconciliation.json"
        if recovery.is_file():
            if recovery.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("recovery evidence exceeds the size limit")
            outcomes = json.loads(recovery.read_text())
            body = run.model_dump()
            for attempt in body["attempts"]:
                if attempt["session_id"] in outcomes:
                    attach_recovered(attempt, outcomes[attempt["session_id"]])
            run = Run.model_validate(body)
        yield path, run


def save_reconciliation(run: Run, session_id: str, outcome: dict, root: Path) -> Run:
    directory = Path(root) / run.run_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "reconciliation.json"
    outcomes = json.loads(path.read_text()) if path.is_file() else {}
    outcomes[session_id] = outcome
    body = run.model_dump()
    for attempt in body["attempts"]:
        if attempt["session_id"] in outcomes:
            attach_recovered(attempt, outcomes[attempt["session_id"]])
    enriched = Run.model_validate(body)
    _atomic_file(path, json.dumps(outcomes, allow_nan=False))
    return enriched


def _merge_pending(before: Run, incoming: Run) -> Run:
    previous, submitted = before.model_dump(), incoming.model_dump()
    if any(previous[key] != submitted[key] for key in MANIFEST_FIELDS):
        raise ValueError("pending run manifest is immutable")
    body, evidence = (submitted, previous) if incoming.revision > before.revision else (previous, submitted)
    attempts = {(attempt["attempt_id"], attempt["session_id"]): attempt for attempt in body["attempts"]}
    for attempt in evidence["attempts"]:
        target = attempts.get((attempt["attempt_id"], attempt["session_id"]))
        outcome = recovered_result(attempt)
        if target is not None and attempt["session_id"] and outcome:
            attach_recovered(target, outcome)
    # Preserve object identity when nothing changes: acknowledgements and close() track the
    # actual payload attempted, since additive recovery does not consume writer revisions.
    return before if body == before.model_dump() else Run.model_validate(body)


def upload(run: Run, url: str, token: str, *, timeout=5.0) -> bool:
    target = safe_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        response = client.put(
            f"{target}/api/runs/{run.run_id}", json=run.model_dump(), headers={"Authorization": f"Bearer {token}"}
        )
    if response.status_code != 200:
        return False
    body = response.json()
    return isinstance(body, dict) and body.get("ok") is True


class Publisher:
    """One pending latest revision per run; unavailable servers retry periodically."""

    def __init__(self, url: str, token: str, *, interval=5.0, timeout=3.0):
        self.url, self.token = safe_url(url), token
        self.interval, self.timeout = interval, timeout
        self.pending = {}
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.stopped = threading.Event()
        self.attempted = threading.Event()
        self.thread = threading.Thread(target=self._work, daemon=True, name="lab-publisher")
        self.thread.start()

    def submit(self, run: Run):
        snapshot = Run.model_validate(run.model_dump())
        with self.lock:
            before = self.pending.get(run.run_id)
            merged = snapshot if before is None else _merge_pending(before, snapshot)
            if merged is not before:
                self.pending[run.run_id] = merged
                self.attempted.clear()
        self.wake.set()

    def _work(self):
        while not self.stopped.is_set():
            self.wake.wait(self.interval)
            self.wake.clear()
            with self.lock:
                snapshots = list(self.pending.values())
            for run in snapshots:
                try:
                    ok = upload(run, self.url, self.token, timeout=self.timeout)
                except (httpx.HTTPError, ValueError, OSError):
                    ok = False
                if ok:
                    with self.lock:
                        current = self.pending.get(run.run_id)
                        if current is run:
                            self.pending.pop(run.run_id, None)
                if self.stopped.is_set():
                    return
            with self.lock:
                # Signal after every latest pending revision has had at least one upload attempt.
                attempted_snapshots = {run.run_id: run for run in snapshots}
                if all(current is attempted_snapshots.get(run_id) for run_id, current in self.pending.items()):
                    self.attempted.set()

    def close(self):
        # A final join happens only after negotiation. Snapshots remain available to lab sync.
        self.wake.set()
        self.attempted.wait(timeout=self.timeout + 0.1)
        self.stopped.set()
        self.wake.set()
        self.thread.join(timeout=self.timeout + 0.1)


def sync(root: Path, url: str, token: str) -> dict:
    report = {"uploaded": 0, "failed": 0}
    for _, run in load_snapshots(root):
        try:
            success = upload(run, url, token)
        except (httpx.HTTPError, ValueError, OSError):
            success = False
        report["uploaded" if success else "failed"] += 1
    return report
