import copy
import threading

import httpx
import pytest

from negotiator.lab.models import Run, summarize
from negotiator.lab.server import DashboardServer
from negotiator.lab.store import Conflict, Store


def snapshot(run_id="run-one", *, score=None, status="pending", cases=None):
    cases = cases or ["case:D01"]
    return {
        "schema_version": 1,
        "run_id": run_id,
        "revision": 1,
        "name": "Synthetic experiment",
        "author": "Tester",
        "hypothesis": "Local test",
        "agent": "naive",
        "config": {},
        "source": "tracked",
        "environment": "sandbox",
        "arena_url": "https://arena.tacto.ai",
        "baseline_id": None,
        "started_at": "2026-10-10T12:00:00+00:00",
        "updated_at": "2026-10-10T12:00:00+00:00",
        "status": "running",
        "cases": cases,
        "repetitions": 1,
        "provenance": {
            "commit": "abc",
            "dirty": False,
            "patch_sha256": None,
            "lock_sha256": "a" * 64,
            "data_sha256": "b" * 64,
        },
        "quota": None,
        "attempts": [
            {
                "attempt_id": f"{case}:1",
                "case_id": case,
                "repeat": 1,
                "status": status,
                "session_id": None,
                "replay_url": None,
                "score": score,
                "rounds": None,
                "elapsed_s": None,
                "timeouts": None,
                "error": None,
                "result": {},
                "threads": {},
            }
            for case in cases
        ],
    }


@pytest.fixture
def dashboard(tmp_path):
    store = Store(tmp_path / "dashboard.sqlite3")
    server = DashboardServer(("127.0.0.1", 0), store, password="test-password", upload_token="test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
        yield client, store
    server.shutdown()
    server.server_close()
    thread.join()


def test_api_authentication_and_cookie_is_read_only(dashboard):
    client, _ = dashboard
    assert client.get("/api/runs").status_code == 401
    assert client.put("/api/runs/run-one", json=snapshot()).status_code == 401
    response = client.post("/api/login", json={"password": "test-password"})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=Strict" in response.headers["set-cookie"]
    assert client.get("/api/runs").json() == {"runs": [], "quota": None, "team": "y/agent"}
    assert client.put("/api/runs/run-one", json=snapshot()).status_code == 401
    assert (
        client.put("/api/runs/run-one", json=snapshot(), headers={"Authorization": "Bearer test-token"}).json()[
            "accepted"
        ]
        is True
    )
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/runs").status_code == 401


def test_snapshot_revisions_and_sqlite_persistence(dashboard):
    client, store = dashboard
    client.headers["Authorization"] = "Bearer test-token"
    first = snapshot(status="running")
    assert client.put("/api/runs/run-one", json=first).json()["accepted"]
    assert not client.put("/api/runs/run-one", json=first).json()["accepted"]
    newer = copy.deepcopy(first)
    newer.update(revision=3, status="completed")
    newer["attempts"][0].update(status="completed", score=0.7, result={"deal": True})
    assert client.put("/api/runs/run-one", json=newer).status_code == 200
    first["revision"] = 2
    assert not client.put("/api/runs/run-one", json=first).json()["accepted"]
    assert Store(store.path).get("run-one")["attempts"][0]["score"] == 0.7
    assert client.get("/api/runs").json()["runs"][0]["metrics"]["mean_score"] == 0.7


@pytest.mark.parametrize(
    "change",
    [
        {"name": "Changed"},
        {"config": {"anchor": 0.1}},
        {"arena_url": "https://other.example"},
        {"provenance": {}},
        {"cases": ["case:D02"]},
    ],
)
def test_manifest_is_immutable(dashboard, change):
    client, _ = dashboard
    client.headers["Authorization"] = "Bearer test-token"
    original = snapshot()
    client.put("/api/runs/run-one", json=original)
    altered = {**original, **change, "revision": 2}
    assert client.put("/api/runs/run-one", json=altered).status_code in {400, 409}
    assert client.get("/api/runs/run-one").json()["name"] == original["name"]


@pytest.mark.parametrize(
    "change",
    [
        {"revision": True},
        {"schema_version": 2},
        {"status": "made-up"},
        {"extra": "unknown"},
        {"run_id": "../escape"},
        {"arena_url": "https://user:secret@example.com"},
        {"config": {"api_key": "secret"}},
        {"repetitions": 0},
    ],
)
def test_invalid_payloads_are_safe_and_bounded(dashboard, change):
    client, _ = dashboard
    response = client.put(
        "/api/runs/run-one", json={**snapshot(), **change}, headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid run snapshot"}


def test_payload_and_login_limit(dashboard):
    client, _ = dashboard
    response = client.put(
        "/api/runs/run-one", content=b"x" * (2 * 1024 * 1024 + 1), headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 413
    for _ in range(5):
        assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"password": "test-password"}).status_code == 429


def test_missing_score_never_receives_complete_aggregate():
    run = snapshot(cases=["case:D01", "case:D02"], status="completed", score=0.5)
    run["attempts"][1].update(status="failed", score=None)
    metrics = summarize(Run.model_validate(run))["metrics"]
    assert metrics["mean_score"] is None
    assert metrics["observed_mean"] == 0.5
    assert metrics["planned"] == 2 and metrics["failed"] == 1


def test_comparison_is_case_aligned_and_incomplete_cells_are_visible(dashboard):
    client, store = dashboard
    baseline = snapshot("baseline", cases=["case:D01", "case:D02"], status="completed", score=0.5)
    candidate = snapshot("candidate", cases=["case:D01", "case:D03"], status="completed", score=0.7)
    candidate["attempts"][1].update(status="failed", score=None)
    store.upsert(Run.model_validate(baseline))
    store.upsert(Run.model_validate(candidate))
    client.headers["Authorization"] = "Bearer test-token"
    comparison = client.get("/api/compare?baseline=baseline&candidate=candidate").json()
    assert comparison["mean_delta"] == pytest.approx(0.2)
    assert [row["case_id"] for row in comparison["cases"]] == ["case:D01", "case:D02", "case:D03"]
    assert comparison["cases"][1]["delta"] is None
    assert comparison["warnings"]
    candidate.update(revision=2, environment="practice")
    candidate["run_id"] = "different-environment"
    store.upsert(Run.model_validate(candidate))
    comparison = client.get("/api/compare?baseline=baseline&candidate=different-environment").json()
    assert comparison["mean_delta"] is None and not comparison["comparable"]


def test_same_arena_session_cannot_be_double_counted(tmp_path):
    store = Store(tmp_path / "db")
    first = snapshot(status="running")
    first["attempts"][0]["session_id"] = "session-one"
    store.upsert(Run.model_validate(first))
    duplicate = snapshot("imported-session", status="running")
    duplicate["attempts"][0]["session_id"] = "session-one"
    with pytest.raises(Conflict):
        store.upsert(Run.model_validate(duplicate))


def test_imported_session_yields_to_delayed_tracked_snapshot(tmp_path):
    store = Store(tmp_path / "db")
    imported = snapshot("imported-first", status="completed", score=0.6)
    imported.update(source="imported", provenance=None, status="completed")
    imported["attempts"][0]["session_id"] = "session-one"
    store.upsert(Run.model_validate(imported))
    tracked = snapshot("tracked-later", status="completed", score=0.6)
    tracked.update(status="completed")
    tracked["attempts"][0]["session_id"] = "session-one"
    assert store.upsert(Run.model_validate(tracked))
    assert store.get("imported-first") is None
    assert len(store.listing()["runs"]) == 1
    # A delayed import retry must not reclaim ownership or add another scored row.
    assert store.upsert(Run.model_validate(imported)) is False


def test_terminal_outcome_cannot_be_overwritten_but_evidence_can_be_enriched(tmp_path):
    store = Store(tmp_path / "db")
    run = snapshot(status="completed", score=0.6)
    run["status"] = "completed"
    store.upsert(Run.model_validate(run))
    run["revision"] = 2
    run["attempts"][0]["threads"] = {"supplier": {"messages": []}}
    assert store.upsert(Run.model_validate(run))
    run["revision"] = 3
    run["attempts"][0]["score"] = 0.9
    with pytest.raises(Conflict):
        store.upsert(Run.model_validate(run))


def test_json_content_type_is_required(dashboard):
    client, _ = dashboard
    response = client.post("/api/login", content='{"password":"test-password"}', headers={"Content-Type": "text/plain"})
    assert response.status_code == 400
    response = client.put(
        "/api/runs/run-one", content="{}", headers={"Authorization": "Bearer test-token", "Content-Type": "text/plain"}
    )
    assert response.status_code == 400


def test_secure_cookie_mode_is_explicit(tmp_path):
    server = DashboardServer(
        ("127.0.0.1", 0), Store(tmp_path / "db"), password="p", upload_token="t", secure_cookie=True
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = httpx.post(f"http://127.0.0.1:{server.server_port}/api/login", json={"password": "p"})
        assert "; Secure" in response.headers["set-cookie"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_latest_quota_uses_absolute_timestamp_not_offset_text(tmp_path):
    store = Store(tmp_path / "db")
    older = snapshot("older")
    older["quota"] = {"used": 1, "left": 199, "limit": 200, "checked_at": "2026-10-10T12:10:00+02:00"}
    newer = snapshot("newer")
    newer["quota"] = {"used": 2, "left": 198, "limit": 200, "checked_at": "2026-10-10T11:00:00+00:00"}
    store.upsert(Run.model_validate(older))
    store.upsert(Run.model_validate(newer))
    assert store.listing()["quota"]["used"] == 2


def test_terminal_imported_outcome_survives_delayed_running_and_failed_tracked_snapshots(tmp_path):
    store = Store(tmp_path / "db")
    imported = snapshot("imported-outcome", status="completed", score=0.75)
    imported.update(source="imported", provenance=None, status="completed")
    imported["attempts"][0].update(session_id="same-session", result={"score": 0.75, "deal": True, "c_deal": 42})
    store.upsert(Run.model_validate(imported))
    tracked = snapshot("tracked-run", status="running")
    tracked["attempts"][0]["session_id"] = "same-session"
    store.upsert(Run.model_validate(tracked))
    saved = store.get("tracked-run")
    assert saved["attempts"][0]["score"] is None
    assert saved["attempts"][0]["result"]["reconciled_result"]["score"] == 0.75
    assert store.listing()["runs"][0]["metrics"]["recovered"] == 1
    tracked.update(revision=2, status="failed")
    tracked["attempts"][0].update(status="failed", error="local transport failed")
    assert store.upsert(Run.model_validate(tracked))
    saved = store.get("tracked-run")
    assert saved["status"] == "failed" and saved["attempts"][0]["error"] == "local transport failed"
    assert saved["attempts"][0]["result"]["reconciled_result"]["c_deal"] == 42
    assert store.upsert(Run.model_validate(imported)) is False
    assert len(store.listing()["runs"]) == 1


def test_import_reconciles_tracked_failure_and_survives_later_local_snapshot(tmp_path):
    store = Store(tmp_path / "db")
    tracked = snapshot("tracked-run", status="failed")
    tracked.update(status="failed")
    tracked["attempts"][0].update(session_id="same-session", error="original local failure")
    store.upsert(Run.model_validate(tracked))
    imported = snapshot("history-read", status="completed", score=0.75)
    imported.update(source="imported", provenance=None, status="completed")
    imported["attempts"][0].update(session_id="same-session", result={"score": 0.75, "deal": False})
    assert store.upsert(Run.model_validate(imported)) is False
    saved = store.get("tracked-run")
    assert saved["revision"] == 1  # recovery must not consume a live laptop writer's revision
    assert saved["provenance"]["commit"] == "abc" and saved["attempts"][0]["status"] == "failed"
    assert saved["attempts"][0]["result"]["reconciled_result"]["score"] == 0.75
    tracked["revision"] = 2
    assert store.upsert(Run.model_validate(tracked))
    assert store.get("tracked-run")["attempts"][0]["result"]["reconciled_result"]["score"] == 0.75
    summary = store.listing()["runs"][0]["metrics"]
    assert summary["failed"] == 1 and summary["scored"] == 0 and summary["recovered"] == 1


def test_history_does_not_prevent_ongoing_writer_from_finishing(tmp_path):
    store = Store(tmp_path / "db")
    tracked = snapshot("tracked-run", status="running")
    tracked["attempts"][0]["session_id"] = "same-session"
    store.upsert(Run.model_validate(tracked))
    imported = snapshot("history-read", status="completed", score=0.75)
    imported.update(source="imported", provenance=None, status="completed")
    imported["attempts"][0].update(session_id="same-session", result={"score": 0.75, "deal": True})
    store.upsert(Run.model_validate(imported))
    assert store.get("tracked-run")["attempts"][0]["status"] == "running"
    tracked.update(revision=2, status="completed")
    tracked["attempts"][0].update(status="completed", score=0.75, result={"score": 0.75, "deal": True})
    assert store.upsert(Run.model_validate(tracked))
    assert store.get("tracked-run")["attempts"][0]["result"]["reconciled_result"]["score"] == 0.75
    assert store.listing()["runs"][0]["metrics"]["mean_score"] == 0.75


def test_score_history_requires_login_and_returns_compact_points(dashboard):
    client, store = dashboard
    body = snapshot(score=.75, status='completed')
    body['attempts'][0]['result'] = {'supplier_id': 'sup:A', 'ended': True}
    store.upsert(Run.model_validate(body))
    assert client.get('/api/score-history').status_code == 401
    client.post('/api/login', json={'password': 'test-password'})
    response = client.get('/api/score-history')
    assert response.status_code == 200
    point = response.json()['points'][0]
    assert point['score'] == .75 and point['supplier_id'] == 'sup:A'
    assert 'threads' not in point and 'config' not in point
