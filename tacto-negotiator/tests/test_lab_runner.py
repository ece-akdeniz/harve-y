import json
import subprocess
import threading
from pathlib import Path

import httpx
import pytest

from negotiator.lab.cli import main, parse_args
from negotiator.lab.history import import_history
from negotiator.lab.models import Run
from negotiator.lab.publish import Publisher, save_snapshot, sync
from negotiator.lab.runner import capture_provenance, plan_run, run_experiment
from negotiator.lab.server import DashboardServer
from negotiator.lab.store import Store


class FakeArena:
    def __init__(self, root, *, fail=False, interrupt=False):
        self.root = root
        self.fail = fail
        self.interrupt = interrupt
        self.opened = 0
        self.reads = []
        self.practice_remaining = 198

    def cases(self, set_):
        self.reads.append(("cases", set_))
        return [{"case_id": "case:D01", "hosted": True}, {"case_id": "case:D02", "hosted": True}]

    def me(self):
        self.reads.append(("me", None))
        return {"practice_sessions_used": 2, "practice_sessions_left": 198, "practice_sessions_limit": 200}

    def open_session(self, case_id):
        snapshots = list(self.root.glob("*/run.json"))
        saved = json.loads(snapshots[0].read_text())
        assert saved["attempts"][self.opened]["status"] == "running"
        self.opened += 1
        if self.interrupt:
            raise KeyboardInterrupt
        if self.fail:
            raise RuntimeError("ARENA_API_KEY=never-emit-this-secret")
        return {
            "session_id": f"s{self.opened}",
            "case": {"case_id": case_id},
            "threads": {"supplier": [{"from": "supplier", "status": "open", "body": "Quote"}]},
        }

    def send_message(self, session_id, supplier_id, message):
        return {"result": {"score": 0.6, "deal": False, "end_reason": "walked_away"}}

    def session(self, session_id):
        self.reads.append(("session", session_id))
        return {
            "session_id": session_id,
            "case_id": "case:D01",
            "status": "ended",
            "result": {"score": 0.6, "deal": False},
            "replay_url": "https://arena.tacto.ai/replay/" + session_id,
            "threads": ["supplier"],
        }

    def thread(self, session_id, supplier_id):
        self.reads.append(("thread", session_id))
        return {"messages": [{"from": "buyer", "body": "Closed"}], "timeouts": []}

    def sessions(self, set_):
        self.reads.append(("sessions", set_))
        return [
            {"session_id": "s1", "case_id": "case:D01", "status": "ended"},
            {"session_id": "s2", "case_id": "case:D01", "status": "ended"},
        ]


class CloseAgent:
    def decide(self, case, threads):
        return {"supplier_id": "supplier", "message": {"action": {"type": "walk_away"}}}


def planned(tmp_path, **changes):
    options = dict(
        name="Synthetic",
        author="Tester",
        hypothesis="No hosted calls",
        agent="naive",
        config={},
        cases=["case:D01"],
        repetitions=1,
        max_sessions=1,
        environment="sandbox",
        arena_url="https://arena.tacto.ai",
        provenance={},
    )
    options.update(changes)
    return plan_run(**options)


@pytest.mark.parametrize(
    "changes",
    [
        {"repetitions": 0},
        {"max_sessions": 0},
        {"max_sessions": 1, "repetitions": 2},
        {"cases": []},
        {"cases": ["case:D01", "case:D01"]},
        {"environment": "final"},
        {"config": {"api_key": "secret"}},
    ],
)
def test_explicit_bounded_plan_validation(tmp_path, changes):
    with pytest.raises(ValueError):
        planned(tmp_path, **changes)


def test_serial_run_persists_before_network_and_completed_result(tmp_path):
    root = tmp_path / "runs"
    run = planned(tmp_path, cases=["case:D01", "case:D02"], max_sessions=2)
    arena = FakeArena(root)
    final = run_experiment(run, root, arena, CloseAgent)
    saved = json.loads((root / final.run_id / "run.json").read_text())
    assert saved["status"] == "completed"
    assert [a["session_id"] for a in saved["attempts"]] == ["s1", "s2"]
    assert saved["attempts"][0]["score"] == 0.6
    assert saved["quota"]["left"] == 198
    assert saved["revision"] > 1


def test_failed_and_interrupted_attempts_remain_visible_without_error_secrets(tmp_path):
    root = tmp_path / "runs"
    final = run_experiment(planned(tmp_path), root, FakeArena(root, fail=True), CloseAgent)
    assert final.status == "failed" and final.attempts[0].status == "failed"
    assert final.attempts[0].score is None
    assert "never-emit" not in (root / final.run_id / "run.json").read_text()
    interrupted_root = tmp_path / "interrupted"
    final = run_experiment(
        planned(tmp_path, cases=["case:D01", "case:D02"], max_sessions=2),
        interrupted_root,
        FakeArena(interrupted_root, interrupt=True),
        CloseAgent,
    )
    assert final.status == "interrupted"
    assert [a.status for a in final.attempts] == ["failed", "pending"]


def test_offline_upload_does_not_break_run_and_sync_retries_saved_snapshot(tmp_path):
    root = tmp_path / "runs"
    offline = Publisher("http://127.0.0.1:1", "test-token", interval=0.01, timeout=0.05)
    final = run_experiment(planned(tmp_path), root, FakeArena(root), CloseAgent, publisher=offline)
    assert final.status == "completed"
    assert (root / final.run_id / "run.json").is_file()
    store = Store(tmp_path / "db")
    server = DashboardServer(("127.0.0.1", 0), store, password="p", upload_token="test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = sync(root, f"http://127.0.0.1:{server.server_port}", "test-token")
        assert report == {"uploaded": 1, "failed": 0}
        assert store.get(final.run_id)["status"] == "completed"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_git_provenance_rejects_dirty_and_saves_patch_only_locally(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "uv.lock").write_text("locked\n")
    (repo / "strategy.py").write_text("value = 1\n")
    data = repo / "data"
    data.mkdir()
    (data / "case.json").write_text('{"case":1}')
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "local fixture",
        ],
        check=True,
    )
    clean, patch = capture_provenance(repo, data_dir=data)
    assert clean["dirty"] is False and patch is None and clean["data_sha256"]
    (repo / "strategy.py").write_text("value = 2\n")
    (repo / ".env").write_text("ARENA_API_KEY=never-emit")
    with pytest.raises(ValueError, match="dirty"):
        capture_provenance(repo, data_dir=data)
    dirty, patch = capture_provenance(repo, data_dir=data, allow_dirty=True)
    assert dirty["dirty"] and dirty["patch_sha256"]
    assert "value = 2" in patch and "never-emit" not in patch
    run = planned(tmp_path, provenance=dirty)
    path = save_snapshot(run, tmp_path / "runs", patch=patch)
    assert (path.parent / "source.patch").read_text() == patch
    assert "value = 2" not in path.read_text()


def test_history_import_is_read_only_and_deduplicates_tracked_and_imported(tmp_path):
    root = tmp_path / "runs"
    run = planned(tmp_path)
    run.attempts[0].status = "completed"
    run.attempts[0].session_id = "s1"
    run.attempts[0].score = 0.5
    run.status = "completed"
    save_snapshot(run, root)
    arena = FakeArena(root)
    report = import_history(arena, root, environment="sandbox", arena_url=run.arena_url, author="Tester")
    assert report == {"imported": 1, "skipped": 1, "failed": 0}
    assert arena.opened == 0
    assert all(kind in {"cases", "me", "sessions", "session", "thread"} for kind, _ in arena.reads)
    assert import_history(arena, root, environment="sandbox", arena_url=run.arena_url, author="Tester")["imported"] == 0
    imported = [Run.model_validate_json(path.read_text()) for path in root.glob("*/run.json")]
    assert next(r for r in imported if r.source == "imported").provenance is None
    with pytest.raises(ValueError):
        import_history(arena, root, environment="final", arena_url=run.arena_url, author="Tester")


def test_init_secrets_are_owner_readable_and_output_only_the_path(tmp_path, capsys):
    path = tmp_path / ".lab-secrets.env"
    assert main(["init", "--secrets-file", str(path)]) == 0
    assert path.stat().st_mode & 0o777 == 0o600
    assert capsys.readouterr().out.strip() == str(path)
    contents = path.read_text()
    assert "LAB_PASSWORD=" in contents and "LAB_UPLOAD_TOKEN=" in contents
    assert main(["init", "--secrets-file", str(path)]) == 2
    assert path.read_text() == contents


def test_serve_defaults_can_be_supplied_by_managed_host_environment(tmp_path, monkeypatch):
    database = tmp_path / "dashboard.sqlite3"
    monkeypatch.setenv("LAB_HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("LAB_DB", str(database))
    monkeypatch.setenv("LAB_SECRETS_FILE", "/home/data/unused.env")
    monkeypatch.setenv("LAB_SECURE_COOKIES", "1")

    args = parse_args(["serve"])

    assert args.host == "0.0.0.0"
    assert args.port == 8080
    assert args.db == database
    assert args.secrets_file == Path("/home/data/unused.env")
    assert args.secure_cookies is True


def test_explicit_serve_arguments_override_managed_host_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("LAB_DB", "/home/data/dashboard.sqlite3")
    monkeypatch.setenv("LAB_SECURE_COOKIES", "1")

    args = parse_args(
        [
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "9000",
            "--db",
            str(tmp_path / "local.sqlite3"),
            "--no-secure-cookies",
        ]
    )

    assert args.host == "127.0.0.1"
    assert args.port == 9000
    assert args.db == tmp_path / "local.sqlite3"
    assert args.secure_cookies is False


def test_invalid_secure_cookie_environment_does_not_defeat_override_or_other_commands(monkeypatch):
    monkeypatch.setenv("LAB_SECURE_COOKIES", "")

    assert parse_args(["serve", "--no-secure-cookies"]).secure_cookies is False
    assert parse_args(["sync"]).command == "sync"
    with pytest.raises(ValueError, match="LAB_SECURE_COOKIES"):
        parse_args(["serve"])


def test_sync_cli_and_existing_cli_dispatch(tmp_path, monkeypatch):
    import negotiator.lab.cli as lab_cli
    from negotiator import cli

    seen = []
    monkeypatch.setattr(lab_cli, "main", lambda argv: seen.append(argv) or 0)
    assert cli.main(["lab", "sync", "--root", str(tmp_path)]) == 0
    assert seen == [["sync", "--root", str(tmp_path)]]


def test_fake_http_arena_runs_official_client_without_spectator_reads(tmp_path):
    from arena_kit.client import ArenaClient

    root = tmp_path / "runs"
    calls = []

    def route(request):
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path == "/v1/cases":
            return httpx.Response(200, json=[{"case_id": "case:D01", "hosted": True}])
        if path == "/v1/me":
            return httpx.Response(200, json={"practice": {"used": 1, "left": 199, "limit": 200}})
        if path == "/v1/sessions" and request.method == "GET":
            return httpx.Response(200, json=[{"session_id": "local-session", "case_id": "case:D01"}])
        if path == "/v1/sessions" and request.method == "POST":
            assert list(root.glob("*/run.json"))
            return httpx.Response(
                200,
                json={
                    "session_id": "local-session",
                    "case": {"case_id": "case:D01"},
                    "threads": {"supplier": [{"from": "supplier", "status": "open"}]},
                },
            )
        if path == "/v1/sessions/local-session/threads/supplier/messages":
            return httpx.Response(200, json={"result": {"deal": False, "score": 0.4}})
        if path == "/v1/sessions/local-session":
            return httpx.Response(
                200,
                json={
                    "session_id": "local-session",
                    "case_id": "case:D01",
                    "status": "ended",
                    "result": {"score": 0.4, "deal": False},
                    "rounds": 1,
                    "threads": {"supplier": {}},
                    "replay_url": "/replay/local-session",
                },
            )
        if path == "/v1/sessions/local-session/threads/supplier":
            return httpx.Response(200, json={"messages": [], "timeouts": []})
        return httpx.Response(404)

    client = ArenaClient(base_url="http://127.0.0.1:9999", transport=httpx.MockTransport(route), rate=100000)
    try:
        run = planned(tmp_path, arena_url="http://127.0.0.1:9999", environment="simulator")
        final = run_experiment(run, root, client, CloseAgent)
        assert final.status == "completed" and final.attempts[0].score == 0.4
        assert final.attempts[0].replay_url == "http://127.0.0.1:9999/replay/local-session"
        report = import_history(client, root, environment="sandbox", arena_url=run.arena_url, author="Tester")
        assert report == {"imported": 0, "skipped": 1, "failed": 0}
    finally:
        client.http.close()
    assert all(
        "/results" not in path and "/screen" not in path and "/events" not in path and "/leaderboard" not in path
        for _, path in calls
    )


def test_provenance_finds_nested_project_lock_and_fingerprints_overlay(tmp_path):
    import hashlib

    repo = tmp_path / "repo"
    project = repo / "nested-project"
    project.mkdir(parents=True)
    (project / "uv.lock").write_text("nested lock\n")
    base, overlay = project / "data", project / "release"
    base.mkdir()
    overlay.mkdir()
    (base / "case.json").write_text('{"base":1}')
    (overlay / "case.json").write_text('{"release":1}')
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    first, _ = capture_provenance(project, data_dir=base, release_dir=overlay)
    assert first["lock_sha256"] == hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest()
    (overlay / "case.json").write_text('{"release":2}')
    second, _ = capture_provenance(project, data_dir=base, release_dir=overlay, allow_dirty=True)
    assert first["data_sha256"] != second["data_sha256"]


def test_custom_agent_factory_reuses_validation_instance(tmp_path, monkeypatch):
    import sys
    import types

    from negotiator.lab.runner import agent_factory

    module = types.ModuleType("local_custom_agent")
    made = []

    def factory(label):
        made.append(label)
        return CloseAgent()

    module.factory = factory
    monkeypatch.setitem(sys.modules, module.__name__, module)
    create = agent_factory("local_custom_agent:factory", {"label": "configured"})
    assert len(made) == 1
    create()
    assert len(made) == 1
    create()
    assert len(made) == 2


def test_import_session_read_failure_is_preserved_as_missing_outcome(tmp_path):
    from arena_kit.client import ArenaError

    class BrokenSession(FakeArena):
        def session(self, session_id):
            raise ArenaError(503, "token=never-emit")

    root = tmp_path / "runs"
    report = import_history(
        BrokenSession(root), root, environment="sandbox", arena_url="https://arena.tacto.ai", author="Tester"
    )
    assert report["failed"] == 2
    saved = [Run.model_validate_json(path.read_text()) for path in root.glob("*/run.json")]
    assert len(saved) == 2
    assert all(run.status == "failed" and run.attempts[0].score is None for run in saved)
    assert all("never-emit" not in path.read_text() for path in root.glob("*/run.json"))


def test_open_history_session_is_skipped_until_completed(tmp_path):
    class OpenSession(FakeArena):
        ended = False

        def sessions(self, set_):
            return [{"session_id": "s1", "case_id": "case:D01", "status": "ended" if self.ended else "open"}]

        def session(self, session_id):
            state = super().session(session_id)
            state["status"] = "ended" if self.ended else "open"
            return state

    root = tmp_path / "runs"
    arena = OpenSession(root)
    report = import_history(arena, root, environment="sandbox", arena_url="https://arena.tacto.ai", author="Tester")
    assert report == {"imported": 0, "skipped": 1, "failed": 0}
    assert not list(root.glob("*/run.json"))
    arena.ended = True
    assert (
        import_history(arena, root, environment="sandbox", arena_url="https://arena.tacto.ai", author="Tester")[
            "imported"
        ]
        == 1
    )


def test_live_publisher_accepts_outcome_then_evidence_and_final_status(tmp_path):
    import time

    root = tmp_path / "runs"
    store = Store(tmp_path / "db")
    server = DashboardServer(("127.0.0.1", 0), store, password="p", upload_token="test-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    run = planned(tmp_path)

    class DelayedEvidence(FakeArena):
        def session(self, session_id):
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                row = store.get(run.run_id)
                if row and row["attempts"][0]["status"] == "completed":
                    break
                time.sleep(0.01)
            else:
                raise AssertionError("completed outcome was not published before evidence collection")
            return super().session(session_id)

    try:
        publisher = Publisher(f"http://127.0.0.1:{server.server_port}", "test-token", interval=0.03, timeout=1)
        final = run_experiment(run, root, DelayedEvidence(root), CloseAgent, publisher=publisher)
        saved = store.get(final.run_id)
        assert saved["status"] == "completed" and saved["revision"] == final.revision
        assert saved["attempts"][0]["replay_url"].endswith("/replay/s1")
        assert saved["attempts"][0]["threads"]["supplier"]["messages"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_manifest_rejects_known_credentials_and_records_safe_model_environment(tmp_path, monkeypatch):
    for key in ("LLM_PROVIDER", "LLM_MODEL", "LLM_EFFORT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ARENA_API_KEY", "sensitive-example-key")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "local-model")
    run = planned(tmp_path)
    assert run.config["_lab_environment"] == {"LLM_PROVIDER": "anthropic", "LLM_MODEL": "local-model"}
    with pytest.raises(ValueError, match="credentials"):
        planned(tmp_path, hypothesis="Accidental paste: sensitive-example-key")


def test_header_quota_updates_are_retained_if_final_me_is_unavailable(tmp_path):
    class HeaderQuota(FakeArena):
        def me(self):
            if self.opened:
                raise RuntimeError("offline")
            return {"practice": {"used": 2, "left": 198, "limit": 200}}

        def open_session(self, case_id):
            reply = super().open_session(case_id)
            self.practice_remaining = 197
            return reply

    root = tmp_path / "runs"
    final = run_experiment(planned(tmp_path, environment="practice"), root, HeaderQuota(root), CloseAgent)
    assert final.quota.left == 197 and final.quota.used == 3


def test_cli_rejects_hosted_simulator_url_before_arena_client(tmp_path, monkeypatch, capsys):
    import negotiator.lab.cli as lab_cli

    monkeypatch.setenv("ARENA_URL", "https://arena.tacto.ai")
    monkeypatch.setattr(lab_cli, "capture_provenance", lambda *args, **kwargs: ({}, None))
    constructed = []
    monkeypatch.setattr(lab_cli, "ArenaClient", lambda **kwargs: constructed.append(kwargs))
    code = main(
        [
            "run",
            "--name",
            "Unsafe label",
            "--hypothesis",
            "Local only",
            "--agent",
            "naive",
            "--cases",
            "case:D01",
            "--repetitions",
            "1",
            "--max-sessions",
            "1",
            "--environment",
            "simulator",
            "--root",
            str(tmp_path),
        ]
    )
    assert code == 2 and not constructed
    assert "simulator" in capsys.readouterr().err


def test_failed_import_is_retried_without_mutating_original_manifest(tmp_path):
    from arena_kit.client import ArenaError

    class RetryHistory(FakeArena):
        broken = True

        def sessions(self, set_):
            return [{"session_id": "s1", "case_id": "case:D01", "status": "ended"}]

        def session(self, session_id):
            if self.broken:
                raise ArenaError(503, "never-print-upstream")
            return super().session(session_id)

    root = tmp_path / "runs"
    store = Store(tmp_path / "db")
    arena = RetryHistory(root)
    first = import_history(
        arena, root, environment="sandbox", arena_url="https://arena.tacto.ai", author="Original", store=store
    )
    assert first["failed"] == 1
    original = store.all()[0]
    arena.broken = False
    report = import_history(
        arena, root, environment="sandbox", arena_url="https://arena.tacto.ai", author="Different author", store=store
    )
    assert report["imported"] == 1 and report["skipped"] == 0
    recovered = store.all()[0]
    assert recovered.run_id == original.run_id and recovered.revision > original.revision
    assert recovered.author == "Original" and recovered.started_at == original.started_at
    assert recovered.status == "completed" and recovered.attempts[0].score == 0.6
    assert recovered.attempts[0].error == original.attempts[0].error


def test_history_reconciles_tracked_crash_without_hiding_original_failure(tmp_path):
    root = tmp_path / "runs"
    store = Store(tmp_path / "db")
    run = planned(tmp_path)
    run.status = "failed"
    run.attempts[0].status = "failed"
    run.attempts[0].session_id = "s1"
    run.attempts[0].error = "original runtime failure"
    save_snapshot(run, root)
    store.upsert(run)
    arena = FakeArena(root)
    report = import_history(arena, root, environment="sandbox", arena_url=run.arena_url, author="Importer", store=store)
    assert report["imported"] == 2  # one recovered tracked outcome, one new history session
    saved = store.get(run.run_id)
    assert saved["source"] == "tracked" and saved["author"] == run.author
    assert saved["attempts"][0]["status"] == "failed" and saved["attempts"][0]["score"] is None
    assert saved["attempts"][0]["error"] == "original runtime failure"
    assert saved["attempts"][0]["result"]["reconciled_result"]["score"] == 0.6


def test_recovery_sidecar_survives_later_local_failure_and_syncs_without_rewriting_writer(tmp_path):
    from negotiator.lab.publish import load_snapshots

    root = tmp_path / "runs"
    original = planned(tmp_path)
    original.status = "failed"
    original.attempts[0].status = "failed"
    original.attempts[0].session_id = "s1"
    original.attempts[0].error = "original failure"
    path = save_snapshot(original, root)
    raw_before = path.read_text()
    import_history(FakeArena(root), root, environment="sandbox", arena_url=original.arena_url, author="Importer")
    assert path.read_text() == raw_before
    assert (path.parent / "reconciliation.json").is_file()
    original.revision = 2
    save_snapshot(original, root)  # a delayed local runner may still write its original failed payload
    merged = next(run for _, run in load_snapshots(root) if run.run_id == original.run_id)
    assert merged.attempts[0].result["reconciled_result"]["score"] == 0.6
    store = Store(tmp_path / "db")
    store.upsert(original)
    assert store.upsert(merged) is False  # same writer revision, additive evidence still survives
    assert store.get(original.run_id)["attempts"][0]["result"]["reconciled_result"]["score"] == 0.6
    assert store.listing()["runs"][0]["metrics"]["failed"] == 1


def test_one_history_import_accumulates_recovery_for_all_attempts_without_direct_store(tmp_path):
    root = tmp_path / "runs"
    run = planned(tmp_path, repetitions=2, max_sessions=2)
    run.status = "failed"
    for index, attempt in enumerate(run.attempts, start=1):
        attempt.status = "failed"
        attempt.session_id = f"s{index}"
        attempt.error = "original runtime failure"
    path = save_snapshot(run, root)
    original = path.read_text()

    class CapturingPublisher:
        snapshots = []

        def submit(self, snapshot):
            self.snapshots.append(Run.model_validate(snapshot.model_dump()))

        def close(self):
            pass

    publisher = CapturingPublisher()
    report = import_history(
        FakeArena(root), root, environment="sandbox", arena_url=run.arena_url, author="Importer", publisher=publisher
    )
    assert report == {"imported": 2, "skipped": 0, "failed": 0}
    assert path.read_text() == original
    assert set(json.loads((path.parent / "reconciliation.json").read_text())) == {"s1", "s2"}
    latest = publisher.snapshots[-1]
    assert latest.revision == run.revision
    assert [attempt.result["reconciled_result"]["score"] for attempt in latest.attempts] == [0.6, 0.6]
    assert all(attempt.status == "failed" and attempt.score is None for attempt in latest.attempts)


@pytest.mark.parametrize("incoming_revision", [1, 2])
def test_publisher_merges_same_or_lower_revision_recovery_while_upload_is_in_flight(
    tmp_path, monkeypatch, incoming_revision
):
    import negotiator.lab.publish as publishing
    from negotiator.lab.reconcile import attach_recovered

    run = planned(tmp_path, repetitions=2, max_sessions=2)
    run.revision = 2
    run.status = "failed"
    for index, attempt in enumerate(run.attempts, start=1):
        attempt.status = "failed"
        attempt.session_id = f"s{index}"
        attempt.error = "original failure"
    first, second = run.model_dump(), run.model_dump()
    attach_recovered(first["attempts"][0], {"score": 0.6, "deal": False})
    second["revision"] = incoming_revision
    attach_recovered(second["attempts"][1], {"score": 0.7, "deal": True})
    began, release = threading.Event(), threading.Event()
    uploaded = []

    def local_upload(snapshot, url, token, *, timeout):
        uploaded.append(snapshot)
        if len(uploaded) == 1:
            began.set()
            assert release.wait(3)
        return True

    monkeypatch.setattr(publishing, "upload", local_upload)
    publisher = Publisher("http://127.0.0.1:1", "test-token", interval=1000, timeout=0.2)
    try:
        publisher.submit(Run.model_validate(first))
        assert began.wait(1)
        publisher.submit(Run.model_validate(second))
        pending = publisher.pending[run.run_id]
        assert pending.revision == 2
        assert [a.result["reconciled_result"]["score"] for a in pending.attempts] == [0.6, 0.7]
    finally:
        release.set()
        publisher.close()
    # The first acknowledgement must not remove later recovery with the same writer revision.
    assert [a.result["reconciled_result"]["score"] for a in uploaded[-1].attempts] == [0.6, 0.7]
    assert not publisher.pending


def test_async_runner_metadata_and_single_attempt_plan(tmp_path):
    run = planned(tmp_path, runner="async", config={"policy_config": {"version": 1}})
    assert run.config["_lab_runner"] == "async"
    assert run.config["policy_config"] == {"version": 1}
    with pytest.raises(ValueError, match="reserved"):
        planned(tmp_path, config={"_lab_runner": "async"})
    with pytest.raises(ValueError, match="exactly one"):
        planned(tmp_path, runner="async", repetitions=2, max_sessions=2)
    args = parse_args(["run", "--name", "async", "--hypothesis", "h", "--runner", "async",
                       "--cases", "case:D01", "--repetitions", "1", "--max-sessions", "1",
                       "--environment", "sandbox"])
    assert args.runner == "async"


@pytest.mark.parametrize("fail_after_open", [False, True])
def test_async_run_persists_session_before_failure_and_collects_evidence(tmp_path, monkeypatch, fail_after_open):
    root = tmp_path / "runs"
    run = planned(tmp_path, runner="async", config={"policy_config": {"version": 1}})
    factory_calls, closed = [], []

    class AsyncClient:
        def __init__(self, **kwargs):
            assert kwargs["retries"] == 0
        async def aclose(self):
            closed.append(True)

    class AsyncRunner:
        def __init__(self, arena, case_id, agent, journal, **kwargs):
            assert agent == {"policy_config": {"version": 1}}
            self.journal, self.case_id = journal, case_id
        async def run(self):
            self.journal.intent(self.case_id, None, None, "open", {"case_id": self.case_id})
            self.journal.session(self.case_id, "known-session", {"case_id": self.case_id})
            saved = json.loads((root / run.run_id / "run.json").read_text())
            assert saved["attempts"][0]["session_id"] == "known-session"
            assert saved["attempts"][0]["status"] == "running"
            if fail_after_open:
                raise RuntimeError("api_key=do-not-print")
            return {"ended": True, "score": 0.7, "deal": False}

    def factory():
        factory_calls.append(1)
        return {"policy_config": {"version": 1}}

    monkeypatch.setattr("negotiator.client.AsyncArena", AsyncClient)
    monkeypatch.setattr("negotiator.runner.CaseRunner", AsyncRunner)
    client = FakeArena(root)
    final = run_experiment(run, root, client, factory)
    attempt = final.attempts[0]
    assert attempt.session_id == "known-session"
    assert attempt.status == ("failed" if fail_after_open else "completed")
    assert attempt.score == (None if fail_after_open else 0.7)
    assert attempt.timeouts == 0 and attempt.threads
    assert len(factory_calls) == 1 and closed == [True] and client.opened == 0
    assert "do-not-print" not in (root / run.run_id / "run.json").read_text()
    # Explicitly rerunning the same attempt must neither open nor silently resume.
    with pytest.raises(ValueError, match="already attempted"):
        run_experiment(run, root, client, factory)
    assert final.attempts[0].session_id == "known-session"
    assert closed == [True]
