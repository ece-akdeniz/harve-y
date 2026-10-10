import sqlite3

import pytest
from test_lab_loop_store import checkpoint, finish

from negotiator.lab.autoloop import Worker, status
from negotiator.lab.policy import default_suite


def setup_worker(tmp_path, *, campaign=True):
    worker = Worker(tmp_path / "db.sqlite", {
        "target_score": 99, "environment": "sandbox", "max_sessions": 12,
        "freeze_at": "2099-01-01T00:00:00+00:00", "root": str(tmp_path / "loop"),
        "family_id": "f", "suite_id": "async", "project": str(tmp_path), "data_paths": {},
    })
    store = worker.client.store
    for name in ("base", "one"):
        store.write("checkpoint", {**checkpoint(name), "runner": "async"})
    store.write("suite", {**default_suite(), "suite_id": "async", "runner": "async"})
    store.write("family", {"family_id": "f", "max_sessions": 12})
    store.write("seed", {"suite_id": "async", "checkpoint_id": "base", "author": "human"})
    if campaign:
        store.write("campaign", {"campaign_id": "c", "family_id": "f", "suite_id": "async",
                                 "baseline_id": "base", "candidate_id": "one", "generation": 1,
                                 "seed": 0, "author": "human", "hypothesis": "test"})
    return worker


def test_uncertain_attempt_blocks_starts_and_survives_restart(tmp_path, monkeypatch):
    worker = setup_worker(tmp_path)
    store = worker.client.store
    attempt = store.read("campaigns", "c")["attempts"][0]
    store.write("attempt-start", {"attempt_id": attempt["attempt_id"], "worker_id": "original", "key_id": "key"})
    monkeypatch.setattr("negotiator.lab.autoloop.run_campaign", lambda *a, **k: pytest.fail("started"))
    assert worker.tick()["state"] == "blocked_reconciliation"
    assert status(worker.db_path)["blocking_attempts"] == [attempt["attempt_id"]]
    replacement = Worker(worker.db_path, worker.config)
    assert replacement.tick()["state"] == "blocked_reconciliation"
    with sqlite3.connect(worker.db_path) as db:
        assert db.execute("SELECT count(*) FROM worker_events").fetchone()[0] == 1


def test_worker_cannot_auto_promote_even_eligible_unregistered_candidate(tmp_path):
    worker = setup_worker(tmp_path)
    finish(worker.client.store, worker.client.read("campaigns", "c"))
    completion = worker.client.write("complete", {"campaign_id": "c"})
    assert completion["evaluation"]["eligible"]
    assert completion["status"] == "awaiting_review"
    assert worker.client.read("recommended", "async")["checkpoint_id"] == "base"
    with pytest.raises(ValueError, match="recommendations"):
        worker.client.write("learning-review", {})


def test_exhausted_family_waits_without_creating_new_family(tmp_path, monkeypatch):
    worker = setup_worker(tmp_path)
    finish(worker.client.store, worker.client.read("campaigns", "c"))
    # Mark the eligible candidate reviewed using the existing human-owned path.
    worker.client.store.write("complete", {"campaign_id": "c"})
    monkeypatch.setattr(worker, "prepare", lambda *a: pytest.fail("budget bypass"))
    result = worker.tick()
    assert result["state"] == "waiting_budget"
    assert result["reserved_sessions"] == 12


def test_freeze_prevents_pending_starts(tmp_path, monkeypatch):
    worker = setup_worker(tmp_path)
    worker.freeze = 0
    worker.client.freeze = 0
    monkeypatch.setattr("negotiator.lab.autoloop.run_campaign", lambda *a, **k: pytest.fail("started"))
    assert worker.tick()["state"] == "frozen"
    with pytest.raises(ValueError, match="frozen"):
        worker.client.write("attempt-start", {})


def test_pending_campaign_uses_original_id_and_budget(tmp_path, monkeypatch):
    worker = setup_worker(tmp_path)
    called = []
    def run(client, identity, project, root, **kwargs):
        called.append(identity)
        return {}
    monkeypatch.setattr("negotiator.lab.autoloop.run_campaign", run)
    assert worker.tick()["state"] == "reconciling"
    assert called == ["c"]
    assert worker.client.read("families", "f")["reserved_sessions"] == 12


def test_worker_rejects_unapproved_family_limit(tmp_path):
    worker = setup_worker(tmp_path)
    worker.config["max_sessions"] = 24
    with pytest.raises(ValueError, match="ceiling"):
        worker.tick()


def test_no_evidence_means_no_invented_candidate(tmp_path):
    worker = setup_worker(tmp_path, campaign=False)
    assert worker.tick()["state"] == "waiting_evidence"
    assert worker.client.read("families", "f")["reserved_sessions"] == 0
