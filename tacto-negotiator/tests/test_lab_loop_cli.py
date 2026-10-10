import json

import pytest


def test_cli_invalid_input_returns_safe_versioned_error(capsys):
    from negotiator.lab.loop_cli import main

    assert main(["suite", "create", "--body", '{"token":"private-secret"}']) == 2
    value = json.loads(capsys.readouterr().out)
    assert value["schema_version"] == 1
    assert value["error"]["code"] == "invalid_input"
    assert "private-secret" not in json.dumps(value)


def test_cli_default_suite_uses_common_transport(monkeypatch, capsys):
    from negotiator.lab import loop_cli

    seen = []

    class Client:
        def __init__(self, *args):
            pass

        def write(self, operation, body):
            seen.append((operation, body))
            return body

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    assert loop_cli.main(["suite", "create"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema_version"] == 1
    assert seen[0][0] == "suite"
    assert seen[0][1]["max_sessions"] == 12


def test_direct_lab_suite_command_is_versioned(monkeypatch, capsys):
    from negotiator.lab import cli, loop_cli

    class Client:
        def __init__(self, *args):
            pass

        def read(self, resource, key=None):
            return {resource: []}

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    assert cli.main(["suite", "list"]) == 0
    assert json.loads(capsys.readouterr().out) == {"schema_version": 1, "suites": []}


def test_recommended_restore_updates_pointer_without_checkout(monkeypatch, capsys):
    from negotiator.lab import loop_cli

    calls = []

    class Client:
        def __init__(self, *args):
            pass

        def read(self, resource, key=None):
            return {"generation": 2}

        def write(self, op, body):
            calls.append((op, body))
            return {"checkpoint_id": body["checkpoint_id"], "generation": 3}

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    monkeypatch.setattr(loop_cli, "restore_checkpoint", lambda *args, **kw: (_ for _ in ()).throw(AssertionError()))
    assert loop_cli.main(["recommended", "restore", "--checkpoint", "base", "--request-id", "rollback"]) == 0
    assert calls[0][0] == "restore"
    assert calls[0][1]["generation"] == 2
    assert json.loads(capsys.readouterr().out)["generation"] == 3


def test_checkpoint_cli_publish_persists_manifest_and_restores_local_fake_remote(tmp_path, monkeypatch, capsys):
    import subprocess

    from test_lab_checkpoints import git

    from negotiator.lab import loop_cli
    from negotiator.lab.loop_store import LoopStore

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "local@example.org")
    git(repo, "config", "user.name", "Local")
    (repo / "uv.lock").write_text("lock")
    (repo / "source.py").write_text("immutable source")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    git(repo, "remote", "add", "origin", str(remote))
    store = LoopStore(tmp_path / "loop.sqlite")
    monkeypatch.setattr(loop_cli, "LoopClient", lambda *args: store)
    root = tmp_path / "local"
    shared = ["--repo", str(repo), "--root", str(root)]
    before = git(repo, "status", "--porcelain")
    assert loop_cli.main(["checkpoint", "create", "--description", "fixture", *shared]) == 0
    created = json.loads(capsys.readouterr().out)
    identity = created["checkpoint_id"]
    assert loop_cli.main(["checkpoint", "publish", identity, *shared]) == 0
    published = json.loads(capsys.readouterr().out)
    assert published["published"]
    assert json.loads((root / "checkpoints" / f"{identity}.json").read_text())["published"]
    assert store.read("checkpoints", identity)["commit"] == created["commit"]
    destination = tmp_path / "restored"
    assert loop_cli.main(["restore", identity, "--destination", str(destination), *shared]) == 0
    capsys.readouterr()
    assert (destination / "source.py").read_text() == "immutable source"
    assert git(repo, "status", "--porcelain") == before


def test_markdown_comparison_has_actionable_gates_scores_and_no_json_fence():
    from negotiator.lab.reports import markdown_report

    report = markdown_report(
        {
            "campaign_id": "c",
            "next_action": "reconcile a session",
            "evaluation": {
                "eligible": False,
                "gates": [{"id": "timeouts", "passed": False, "detail": "missing counts"}],
                "cases": [
                    {
                        "case_id": "case:D01",
                        "baseline": {"mean": 70, "spread": 1},
                        "candidate": {"mean": 75, "spread": 2},
                        "gain": 5,
                    }
                ],
                "repeats": [{"repeat": 1, "baseline": 70, "candidate": 75, "gain": 5}],
                "evidence_gaps": ["timeout_evidence"],
            },
        }
    )
    assert "reconcile a session" in report
    assert "| case:D01 | 70 | 75 | 5 | 1 | 2 |" in report
    assert "missing counts" in report and "timeout_evidence" in report
    assert "```json" not in report


def test_evidence_filters_supplier_and_message(monkeypatch, capsys):
    from negotiator.lab import loop_cli

    class Client:
        def __init__(self, *args):
            pass

        def read(self, *args):
            return {
                "campaign_id": "c",
                "attempt": {
                    "case_id": "D01",
                    "threads": {
                        "s1": {"messages": [{"body": "first"}, {"body": "wanted"}]},
                        "s2": {"messages": [{"body": "unrelated"}]},
                    },
                },
            }

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    assert loop_cli.main(["evidence", "show", "a", "--supplier", "s1", "--message", "1"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["attempt"]["threads"] == {"s1": {"messages": [{"body": "wanted"}]}}


def test_cli_markdown_uses_human_report(monkeypatch, capsys):
    from negotiator.lab import loop_cli

    class Client:
        def __init__(self, *args):
            pass

        def read(self, *args):
            return {"campaign_id": "c", "status": "running", "attempts": []}

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    assert loop_cli.main(["campaign", "status", "c", "--format", "markdown"]) == 0
    text = capsys.readouterr().out
    assert "**Status:** running" in text
    assert "```json" not in text


def test_checkpoint_show_reads_local_manifest_without_lab_credentials(tmp_path, monkeypatch, capsys):
    from test_lab_loop_store import checkpoint

    from negotiator.lab import loop_cli
    from negotiator.lab.checkpoints import _save

    _save(checkpoint("local"), tmp_path / "checkpoints")
    monkeypatch.delenv("LAB_URL", raising=False)
    monkeypatch.delenv("LAB_UPLOAD_TOKEN", raising=False)
    assert loop_cli.main(["checkpoint", "show", "local", "--root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["checkpoint_id"] == "local"


def test_remote_transport_real_local_http_roundtrip(tmp_path):
    import threading

    from negotiator.lab.loop_client import LoopClient
    from negotiator.lab.policy import default_suite
    from negotiator.lab.server import DashboardServer
    from negotiator.lab.store import Store

    server = DashboardServer(("127.0.0.1", 0), Store(tmp_path / "db"), password="local", upload_token="local-token")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = LoopClient(f"http://127.0.0.1:{server.server_port}", "local-token")
    try:
        suite = client.write("suite", default_suite())
        assert client.read("suites", suite["suite_id"]) == suite
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        thread.join()


def test_campaign_status_exposes_uncertain_session_next_action(monkeypatch, capsys):
    from negotiator.lab import loop_cli

    class Client:
        def __init__(self, *args):
            pass

        def read(self, *args):
            return {
                "campaign_id": "c",
                "status": "running",
                "attempts": [{"attempt_id": "a", "status": "ambiguous", "start": {}, "result": {}}],
            }

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    assert loop_cli.main(["campaign", "status", "c"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["blocking_attempts"] == ["a"]
    assert "reconcile" in body["next_action"]


def test_loop_coordinator_loads_existing_dotenv_setup_without_printing_keys(monkeypatch, capsys):
    from negotiator.lab import loop_cli

    seen = []

    def load_setup():
        monkeypatch.setenv("LAB_URL", "http://localhost:8000")
        monkeypatch.setenv("LAB_UPLOAD_TOKEN", "test-secret-from-dotenv")

    monkeypatch.setattr(loop_cli, "load_env", load_setup, raising=False)

    class Client:
        def __init__(self, url, token):
            seen.append((url, token))

        def read(self, *args):
            return {"suites": []}

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    assert loop_cli.main(["suite", "list"]) == 0
    assert seen == [("http://localhost:8000", "test-secret-from-dotenv")]
    assert "test-secret-from-dotenv" not in capsys.readouterr().out


@pytest.mark.parametrize("action", ["run", "sync"])
def test_campaign_mutation_incomplete_result_exits_nonzero(monkeypatch, capsys, action):
    from negotiator.lab import loop_cli

    monkeypatch.setattr(
        loop_cli,
        "dispatch",
        lambda args: {"campaign_id": "c", "blocking_attempts": ["a"], "next_action": "reconcile explicit session"},
    )
    argv = ["campaign", "run", "--campaign-id", "c"] if action == "run" else ["campaign", "sync", "c"]
    assert loop_cli.main(argv) == 1
    body = json.loads(capsys.readouterr().out)
    assert body["schema_version"] == 1
    assert body["execution_status"] == "blocked"
    assert body["next_action"] == "reconcile explicit session"


def test_identical_cli_restore_retry_reuses_original_generation_and_conflicts_on_changes(tmp_path, monkeypatch, capsys):
    from test_lab_campaign import campaign_fixture

    from negotiator.lab import loop_cli

    store, campaign = campaign_fixture(tmp_path)
    store.write(
        "restore",
        dict(request_id="advance", suite_id=campaign["suite_id"], checkpoint_id="base", generation=1, author="tester"),
    )
    monkeypatch.setattr(loop_cli, "LoopClient", lambda *args: store)
    argv = ["recommended", "restore", "--checkpoint", "base", "--request-id", "repeat-test", "--author", "tester"]
    assert loop_cli.main(argv) == 0
    first = json.loads(capsys.readouterr().out)
    assert loop_cli.main(argv) == 0
    assert json.loads(capsys.readouterr().out) == first
    assert first["generation"] == 3
    assert len(store.read("history")["history"]) == 3
    assert loop_cli.main([*argv, "--author", "changed"]) != 0
    capsys.readouterr()
    assert loop_cli.main([*argv, "--checkpoint", "one"]) != 0
    capsys.readouterr()
    assert len(store.read("history")["history"]) == 3


def test_documented_family24_campaign12_workflow_uses_existing_family(tmp_path, monkeypatch, capsys):
    from test_lab_campaign import campaign_fixture

    from negotiator.lab import loop_cli

    store, campaign = campaign_fixture(tmp_path)
    monkeypatch.setattr(loop_cli, "LoopClient", lambda *args: store)
    monkeypatch.setattr(loop_cli, "arena_snapshot", lambda suite: None)
    monkeypatch.setattr(
        loop_cli,
        "run_campaign",
        lambda client, identity, *args, **kwargs: {"campaign_id": identity, "completion": {"status": "rejected"}},
    )
    assert loop_cli.main(["family", "create", "--family-id", "closing-v1", "--max-sessions", "24"]) == 0
    capsys.readouterr()
    assert (
        loop_cli.main(
            [
                "campaign",
                "run",
                "--family",
                "closing-v1",
                "--candidate",
                "one",
                "--hypothesis",
                "test",
                "--max-sessions",
                "12",
                "--campaign-id",
                "closing-01",
                "--root",
                str(tmp_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    family = store.read("families", "closing-v1")
    assert family["max_sessions"] == 24 and family["reserved_sessions"] == 12
    assert len(store.read("campaigns", "closing-01")["attempts"]) == 12


def test_existing_practice_family_protections_are_preserved_and_conflicting_flags_rejected(
    tmp_path, monkeypatch, capsys
):
    import time

    from test_lab_campaign import campaign_fixture

    from negotiator.lab import loop_cli
    from negotiator.lab.policy import default_suite

    store, _ = campaign_fixture(tmp_path)
    suite = default_suite(environment="practice")
    store.write("suite", suite)
    store.write("seed", dict(suite_id=suite["suite_id"], checkpoint_id="base", author="tester"))
    store.write("family", dict(family_id="protected", max_sessions=24, practice_allowance=24, reserve=5))
    monkeypatch.setattr(loop_cli, "LoopClient", lambda *args: store)
    monkeypatch.setattr(
        loop_cli, "arena_snapshot", lambda suite: {"remaining": 100, "observed_at": time.time(), "open_sessions": 0}
    )
    monkeypatch.setattr(
        loop_cli,
        "run_campaign",
        lambda client, identity, *args, **kwargs: {"campaign_id": identity, "completion": {"status": "rejected"}},
    )
    argv = [
        "campaign",
        "run",
        "--family",
        "protected",
        "--candidate",
        "one",
        "--hypothesis",
        "test",
        "--suite",
        suite["suite_id"],
        "--max-sessions",
        "12",
        "--root",
        str(tmp_path),
    ]
    assert loop_cli.main([*argv, "--campaign-id", "protected-first"]) == 0
    capsys.readouterr()
    family = store.read("families", "protected")
    assert family["max_sessions"] == 24 and family["practice_allowance"] == 24 and family["reserve"] == 5
    assert family["practice_reserved"] == 12
    for flag, value in [("--practice-allowance", "0"), ("--reserve", "0")]:
        assert loop_cli.main([*argv, flag, value, "--campaign-id", "conflicting"]) != 0
        capsys.readouterr()
    assert store.read("families", "protected") == family
