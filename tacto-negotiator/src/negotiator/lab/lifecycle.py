"""Narrow durable barriers for terminal evidence and immutable Lab publication."""

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import httpx

from .models import safe_url
from .publish import _atomic_file


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def bounded_read(read, *, deadline, request_timeout, clock=time.monotonic):
    """Run one read-only call with both an overall and per-request caller deadline."""
    remaining = deadline - clock()
    if remaining <= 0:
        raise TimeoutError("terminal evidence collection deadline exhausted")
    done, result = threading.Event(), {}

    def invoke():
        try:
            result["value"] = read()
        except BaseException as error:
            result["error"] = error
        finally:
            done.set()

    worker = threading.Thread(target=invoke, name="lab-terminal-read", daemon=True)
    worker.start()
    if not done.wait(min(remaining, request_timeout)):
        raise TimeoutError("terminal evidence request deadline exhausted")
    if "error" in result:
        raise result["error"]
    return result["value"]


def _verify_frozen(pub):
    payload = pub.get("payload")
    if payload is None:
        return
    digest = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    if digest != pub.get("payload_sha256") or payload.get("run_id") != pub.get("run_id"):
        raise ValueError("frozen publication payload failed its local identity/hash check")
    if safe_url(pub.get("destination")) != pub.get("destination"):
        raise ValueError("frozen publication destination failed validation")


class PublicationJournal:
    """Atomic local state; once a write is marked attempted, this object never writes again."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.state = json.loads(self.path.read_text()) if self.path.is_file() else {
            "schema_version": 1,
            "evidence_collection": {"status": "not_started", "session_id": None, "error": None},
            "publication": {"status": "not_prepared", "destination": None, "run_id": None,
                            "payload": None, "payload_sha256": None, "write_attempted": False,
                            "write_status": "not_attempted", "retrieval_status": "not_attempted"},
            "transitions": [],
        }
        self.attempt_marker = self.path.with_name(self.path.name + ".write-attempted")
        _verify_frozen(self.state.get("publication", {}))
        if self.attempt_marker.is_file():
            marker = json.loads(self.attempt_marker.read_text())
            pub = self.state.get("publication", {})
            if (marker.get("run_id") != pub.get("run_id")
                    or marker.get("payload_sha256") != pub.get("payload_sha256")
                    or marker.get("destination") != pub.get("destination")):
                raise ValueError("publication attempt marker does not match frozen publication identity")
            if not pub.get("write_attempted"):
                self.transition("publication", "outcome_unknown", write_attempted=True,
                                write_status="outcome_unknown", recovered_attempt_marker=True)

    def save(self):
        _atomic_file(self.path, json.dumps(self.state, ensure_ascii=False, allow_nan=False,
                                           separators=(",", ":")) + "\n")

    def transition(self, section, status, **fields):
        record = {"status": status, **fields}
        self.state[section] = {**self.state.get(section, {}), **record}
        self.state["transitions"].append({"at_utc": time.time(), "section": section, **record})
        self.save()

    def mark_collection(self, status, *, session_id=None, error=None, terminal_path=None):
        self.transition("evidence_collection", status, session_id=session_id, error=error,
                        terminal_path=str(terminal_path) if terminal_path else None)

    def prepare(self, run, destination, *, terminal_complete):
        if not terminal_complete:
            raise ValueError("complete terminal evidence is required before publication")
        pub = self.state["publication"]
        _verify_frozen(pub)
        payload = run.model_dump()
        encoded = canonical_json(payload)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        if pub["write_attempted"]:
            if pub["run_id"] != run.run_id or pub["payload_sha256"] != digest:
                raise ValueError("publication write already attempted for a different frozen payload")
            return pub
        if pub["status"] == "prepared" and (pub["run_id"] != run.run_id or pub["payload_sha256"] != digest):
            raise ValueError("prepared publication payload is immutable")
        self.transition("publication", "prepared", destination=safe_url(destination), run_id=run.run_id,
                        payload=payload, payload_sha256=digest, write_attempted=False,
                        write_status="not_attempted", retrieval_status="not_attempted")
        return self.state["publication"]

    def begin_write(self):
        pub = self.state["publication"]
        if pub["status"] != "prepared" or pub["write_attempted"]:
            raise ValueError("publication write is not eligible; reconcile existing state read-only")
        marker = canonical_json({"run_id": pub["run_id"], "payload_sha256": pub["payload_sha256"],
                                 "destination": pub["destination"]}) + "\n"
        try:
            descriptor = os.open(self.attempt_marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ValueError("publication attempt marker already exists; reconcile read-only") from None
        with os.fdopen(descriptor, "w") as stream:
            stream.write(marker)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "posix":
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        self.transition("publication", "write_attempted", write_attempted=True, write_status="attempted")

    def record_write(self, status, **fields):
        self.transition("publication", status, write_status=status, **fields)


def upload_once(journal: PublicationJournal, *, token: str, timeout: float = 30,
                transport=None, client_factory=httpx.Client) -> dict:
    """Make at most one PUT. Network ambiguity is persisted and only GET reconciliation may follow."""
    pub = journal.state["publication"]
    _verify_frozen(pub)
    if pub["status"] != "prepared" or pub["write_attempted"]:
        raise ValueError("publication write already attempted; read-only reconciliation required")
    journal.begin_write()  # durable barrier before entering the network stack
    try:
        with client_factory(timeout=timeout, follow_redirects=False, transport=transport) as client:
            response = client.put(f"{pub['destination']}/api/runs/{pub['run_id']}", json=pub["payload"],
                                  headers={"Authorization": f"Bearer {token}"})
    except (httpx.TransportError, OSError, TimeoutError) as error:
        journal.record_write("outcome_unknown", error=type(error).__name__)
        return {"status": "outcome_unknown"}
    if response.status_code == 200:
        try:
            accepted = response.json().get("ok") is True
        except (ValueError, AttributeError):
            accepted = False
        if accepted:
            journal.record_write("acknowledged")
            return {"status": "acknowledged"}
        journal.record_write("outcome_unknown", error="invalid_acknowledgement")
        return {"status": "outcome_unknown"}
    if response.status_code >= 500 or response.status_code in {408, 429}:
        journal.record_write("outcome_unknown", http_status=response.status_code)
        return {"status": "outcome_unknown"}
    journal.record_write("rejected", http_status=response.status_code)
    return {"status": "rejected", "http_status": response.status_code}


def reconcile_publication(journal: PublicationJournal, *, token: str, timeout: float = 10,
                          transport=None, client_factory=httpx.Client) -> dict:
    """Read-only GET of individual record and ordinary listing; never retries a PUT."""
    pub = journal.state["publication"]
    _verify_frozen(pub)
    if not pub["write_attempted"]:
        raise ValueError("no publication write exists to reconcile")
    try:
        with client_factory(base_url=pub["destination"], timeout=timeout, follow_redirects=False,
                            transport=transport,
                            headers={"Authorization": f"Bearer {token}"}) as client:
            item = client.get("/api/runs/" + pub["run_id"])
            if item.status_code == 404:
                journal.transition("publication", pub["status"], retrieval_status="missing")
                return {"status": "missing"}
            item.raise_for_status()
            listing = client.get("/api/runs")
            listing.raise_for_status()
            body = item.json()
            listed = {entry.get("run_id") for entry in listing.json().get("runs", [])}
    except (httpx.HTTPError, OSError, ValueError) as error:
        journal.transition("publication", pub["status"], retrieval_status="unavailable",
                           reconciliation_error=type(error).__name__)
        return {"status": "unavailable"}
    exact = canonical_json(body) == canonical_json(pub["payload"])
    present = pub["run_id"] in listed
    if exact and present:
        journal.transition("publication", "verified", write_status="verified", retrieval_status="verified")
        return {"status": "verified"}
    journal.transition("publication", "outcome_unknown", retrieval_status="mismatch")
    return {"status": "mismatch"}
