import hashlib
import json

import pytest

from negotiator.lab.start_recovery import original_start, recover_start


def saved(tmp_path):
    attempt = {"attempt_id": "c:0:1:baseline", "case_id": "case:D01", "arm": "baseline",
               "checkpoint_id": "baseline", "status": "ambiguous", "session_id": None,
               "start": {"request": {"worker_id": "original"}}}
    result = {k: v for k, v in attempt.items() if k in
              {"attempt_id", "checkpoint_id", "status", "session_id"}}
    attempt["outcome"] = result
    campaign = {"campaign_id": "c", "suite_id": "suite", "attempts": [attempt]}
    directory = tmp_path / "c"
    original = directory / "attempts" / hashlib.sha256(attempt["attempt_id"].encode()).hexdigest()
    original.mkdir(parents=True)
    (original / "result.json").write_text(json.dumps({**result, "final": True}))
    (directory / "state.json").write_text(json.dumps({"start_requests": {
        attempt["attempt_id"]: {"worker_id": "original"}}}))
    (original / "journal.jsonl").write_text(json.dumps({"rec": "intent", "kind": "open", "case": "case:D01",
        "session": None, "move_id": "original-move", "payload": {"case_id": "case:D01"}}) + "\n")
    return campaign, attempt, original


def test_recovery_requires_exact_durable_ownership(tmp_path):
    campaign, attempt, _ = saved(tmp_path)
    attempt["start"]["request"]["worker_id"] = "another"
    with pytest.raises(ValueError, match="ownership"):
        original_start(tmp_path, campaign, attempt)


def test_recovery_reuses_move_and_receipt_after_upload_failure(tmp_path, monkeypatch):
    campaign, attempt, original = saved(tmp_path)
    before = (original / "journal.jsonl").read_bytes()
    calls = []
    class Arena:
        def __init__(self, **kwargs):
            pass
        async def open_session(self, case, move):
            calls.append((case, move))
            return {"session_id": "owned", "case": {"case_id": case}}
        async def session(self, session):
            return {"ended": True}
        async def aclose(self):
            pass
    class Client:
        def read(self, *args):
            return {"arena_url": "http://localhost", "environment": "sandbox"}
    monkeypatch.setattr("negotiator.lab.start_recovery.AsyncArena", Arena)
    monkeypatch.setattr("negotiator.lab.start_recovery.prepare_arms", lambda *a: ({}, {}, {}))
    def unavailable(*args):
        raise ValueError("upload failed")
    monkeypatch.setattr("negotiator.lab.start_recovery.reconcile_attempt", unavailable)
    with pytest.raises(ValueError, match="upload failed"):
        recover_start(Client(), campaign, attempt, tmp_path, tmp_path, {})
    monkeypatch.setattr("negotiator.lab.start_recovery.reconcile_attempt", lambda *a: {"reconciliation": {}})
    recover_start(Client(), campaign, attempt, tmp_path, tmp_path, {})
    assert calls == [("case:D01", "original-move")]
    assert (original / "journal.jsonl").read_bytes() == before
    assert json.loads((original / "result.json").read_text())["status"] == "ambiguous"
