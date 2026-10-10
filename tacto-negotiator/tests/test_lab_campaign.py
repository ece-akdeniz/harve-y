import json

import httpx
import pytest


def test_order_contains_each_cell_once_and_preserves_seed_behavior():
    import random

    from negotiator.lab.ordering import campaign_order

    cells = campaign_order(["D01", "D02"], 3, 7)
    assert len(cells) == 12
    assert len({(c["arm"], c["case_id"], c["repeat"]) for c in cells}) == 12
    expected = []
    rng = random.Random(7)
    for repeat in range(1, 4):
        for case in ["D01", "D02"]:
            arms = ["baseline", "candidate"]
            rng.shuffle(arms)
            expected.extend(dict(arm=arm, case_id=case, repeat=repeat) for arm in arms)
    assert cells == expected


def test_transport_encodes_identity_and_never_echoes_server_credentials():
    from negotiator.lab.loop_client import LoopClient, LoopError

    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(409, json={"error": "private-password"})

    client = LoopClient("http://localhost:8000", "private-password", transport=httpx.MockTransport(respond))
    with pytest.raises(LoopError) as error:
        client.read("evidence", "campaign:0:1:baseline")
    assert "private-password" not in str(error.value)
    assert seen[0].headers["Authorization"] == "Bearer private-password"
    assert seen[0].url.path == "/api/loop/evidence/campaign:0:1:baseline"


def test_sync_uploads_saved_outcome_without_any_execution(tmp_path):
    from negotiator.lab.campaign import save_state, sync_campaign

    class Client:
        def __init__(self):
            self.calls = []

        def write(self, operation, body):
            self.calls.append((operation, body))
            if operation == "attempt-result":
                return body
            return {"status": "rejected"}

        def read(self, resource, key):
            return {"attempts": [{"attempt_id": "c:0:1:baseline", "status": "completed"}]}

    body = dict(
        attempt_id="c:0:1:baseline", checkpoint_id="base", session_id="s", status="completed", result={"ended": True}
    )
    save_state(
        tmp_path, "c", {"campaign_id": "c", "results": {body["attempt_id"]: {**body, "final": True}}, "uploaded": []}
    )
    client = Client()
    result = sync_campaign(client, "c", tmp_path)
    assert [op for op, _ in client.calls] == ["attempt-result", "complete"]
    assert result["uploaded"] == [body["attempt_id"]]
    assert json.loads((tmp_path / "c/state.json").read_text())["uploaded"] == [body["attempt_id"]]


def test_worker_environment_reconstructs_estimates_and_disables_incidental_data(tmp_path, monkeypatch):
    from negotiator.lab.worker import prepare_environment

    monkeypatch.setenv("NEGOTIATOR_ESTIMATES", "0")
    monkeypatch.setenv("ARENA_RELEASE", "/wrong/release")
    monkeypatch.setenv("ARENA_DATA", "/wrong/base")
    monkeypatch.setenv("NEGOTIATOR_CLAIMS", "1")
    from negotiator.lab.checkpoints import _data_hash

    base = tmp_path / "base"
    base.mkdir()
    manifest = {"config": {"estimates": None, "claims": False}, "data": {"base": {"sha256": _data_hash(base)}}}
    prepare_environment(manifest, {"base": str(base)}, tmp_path)
    import os

    assert os.environ["NEGOTIATOR_ESTIMATES"] == "1"
    assert os.environ["ARENA_DATA"] == str(base)
    assert os.environ["ARENA_RELEASE"] != "/wrong/release"
    assert not list(__import__("pathlib").Path(os.environ["ARENA_RELEASE"]).iterdir())
    assert "NEGOTIATOR_CLAIMS" not in os.environ
    prepare_environment({"config": {"estimates": {}, "claims": False}, "data": {}}, {}, tmp_path)
    assert "NEGOTIATOR_ESTIMATES" not in os.environ


def test_serial_transport_journals_payload_and_move_id_before_request(tmp_path):
    from negotiator.lab.transport import JournaledArena

    seen = []

    def respond(request):
        journal = [json.loads(line) for line in (tmp_path / "serial.jsonl").read_text().splitlines()]
        assert journal[-1]["payload"] == {"case_id": "case:S01"}
        assert journal[-1]["move_id"] == request.headers["X-Move-Id"]
        assert "private-key" not in json.dumps(journal)
        seen.append(request)
        return httpx.Response(200, json={"session_id": "owned"})

    arena = JournaledArena(
        tmp_path / "serial.jsonl",
        base_url="http://localhost",
        api_key="private-key",
        transport=httpx.MockTransport(respond),
        rate=1000,
    )
    assert arena.open_session("case:S01") == {"session_id": "owned"}
    assert len(seen) == 1
    arena.http.close()


def campaign_fixture(tmp_path):
    from test_lab_loop_store import campaign, checkpoint

    from negotiator.lab.loop_store import LoopStore
    from negotiator.lab.policy import default_suite

    store = LoopStore(tmp_path / "loop.sqlite")
    for identity in ("base", "one"):
        store.write("checkpoint", checkpoint(identity))
    store.write("suite", default_suite())
    store.write("family", {"family_id": "f", "max_sessions": 24})
    store.write("seed", {"suite_id": default_suite()["suite_id"], "checkpoint_id": "base", "author": "tester"})
    return store, campaign(store)


def test_ambiguous_worker_stops_and_resume_never_creates_again(tmp_path, monkeypatch):
    import negotiator.lab.campaign as execution

    store, campaign = campaign_fixture(tmp_path)
    calls = []
    monkeypatch.setenv("ARENA_API_KEY", "private-key")
    monkeypatch.setattr(
        execution,
        "prepare_arms",
        lambda *args: (
            {"baseline": {"checkpoint_id": "base"}, "candidate": {"checkpoint_id": "one"}},
            {"baseline": tmp_path, "candidate": tmp_path},
            {},
        ),
    )
    monkeypatch.setattr(execution, "arena_snapshot", lambda suite: None)

    def worker(request, **kwargs):
        calls.append(request)
        return dict(
            attempt_id=request["attempt"]["attempt_id"],
            checkpoint_id=request["checkpoint"]["checkpoint_id"],
            session_id=None,
            status="ambiguous",
            result={},
            threads={},
        )

    monkeypatch.setattr(execution, "launch_worker", worker)
    first = execution.run_campaign(store, campaign["campaign_id"], tmp_path, tmp_path / "campaigns")
    assert len(calls) == 1
    assert first["blocking_attempts"]
    second = execution.run_campaign(store, campaign["campaign_id"], tmp_path, tmp_path / "campaigns")
    assert len(calls) == 1
    assert first["blocking_attempts"] == second["blocking_attempts"]
    attempt = store.read("campaigns", campaign["campaign_id"])["attempts"][0]
    assert "private-key" not in json.dumps(attempt)


def test_interrupted_upload_replays_same_result_and_completes_once(tmp_path):
    from negotiator.lab.campaign import save_state, sync_campaign

    store, campaign = campaign_fixture(tmp_path)
    results = {}
    for attempt in campaign["attempts"]:
        store.write("attempt-start", dict(attempt_id=attempt["attempt_id"], worker_id="w", key_id="key"))
        body = dict(
            attempt_id=attempt["attempt_id"],
            checkpoint_id=attempt["checkpoint_id"],
            session_id=attempt["attempt_id"],
            status="completed",
            score=0.8 if attempt["arm"] == "candidate" else 0.6,
            timeouts=0,
            result={"ended": True, "deal": True, "must_haves_ok": True},
            threads={},
        )
        store.write("attempt-result", body)
        results[attempt["attempt_id"]] = {**body, "final": True}
    save_state(tmp_path, campaign["campaign_id"], {"results": results, "uploaded": []})

    class LostAck:
        def read(self, *args):
            return store.read(*args)

        def write(self, op, body):
            value = store.write(op, body)
            if op == "attempt-result":
                raise ConnectionError("lost ack")
            return value

    with pytest.raises(ConnectionError):
        sync_campaign(LostAck(), campaign["campaign_id"], tmp_path)
    result = sync_campaign(store, campaign["campaign_id"], tmp_path)
    assert result["completion"]["status"] == "promoted"
    sync_campaign(store, campaign["campaign_id"], tmp_path)
    assert len(store.read("history")["history"]) == 2


def test_prelaunch_intent_without_server_start_can_resume_safely(tmp_path):
    from negotiator.lab.campaign import save_state, sync_campaign

    store, campaign = campaign_fixture(tmp_path)
    identity = campaign["attempts"][0]["attempt_id"]
    save_state(
        tmp_path,
        campaign["campaign_id"],
        {"results": {}, "uploaded": [], "started": [identity], "start_requests": {identity: {"worker_id": "local"}}},
    )
    result = sync_campaign(store, campaign["campaign_id"], tmp_path)
    assert not result["blocking_attempts"]
    assert identity not in result["started"]
    assert "start" in result["next_action"].lower()


def test_worker_preflight_rejects_unloadable_claim_data_before_open(tmp_path, monkeypatch):
    monkeypatch.setenv("NEGOTIATOR_CLAIMS", "0")
    monkeypatch.setenv("NEGOTIATOR_ESTIMATES", "0")
    monkeypatch.setenv("ARENA_DATA", "unused")
    monkeypatch.setenv("ARENA_RELEASE", "unused")
    from negotiator.lab import worker
    from negotiator.lab.checkpoints import _data_hash

    base = tmp_path / "base"
    base.mkdir()
    project = __import__("pathlib").Path(worker.__file__).resolve().parents[3]
    import hashlib

    checkpoint = {
        "config": {"claims": True, "estimates": {}},
        "data": {"base": {"sha256": _data_hash(base)}},
        "lock_sha256": hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest(),
    }
    with pytest.raises(FileNotFoundError):
        worker.validate_runtime(
            {
                "checkpoint": checkpoint,
                "project": str(project),
                "attempt_root": str(tmp_path),
                "data_paths": {"base": str(base)},
            }
        )


def test_definite_no_session_evidence_releases_lease_without_budget_refund(tmp_path):
    store, campaign = campaign_fixture(tmp_path)
    first, second = campaign["attempts"][:2]
    store.write("attempt-start", dict(attempt_id=first["attempt_id"], worker_id="w", key_id="key"))
    body = dict(
        attempt_id=first["attempt_id"],
        checkpoint_id=first["checkpoint_id"],
        reason="arena_rejected",
        http_status=422,
        worker_id="w",
    )
    store.write("attempt-not-created", body)
    store.write("attempt-not-created", body)
    store.write("attempt-start", dict(attempt_id=second["attempt_id"], worker_id="w", key_id="key"))
    assert store.read("families", "f")["reserved_sessions"] == 12
    assert store.read("campaigns", "c")["attempts"][0]["status"] == "failed"
    with pytest.raises(ValueError):
        store.write("attempt-not-created", {**body, "http_status": 503})


@pytest.mark.parametrize("http_status,expected", [(422, "failed"), (503, "ambiguous")])
def test_worker_definite_open_rejection_is_distinct_from_uncertainty(tmp_path, monkeypatch, http_status, expected):
    import hashlib
    from pathlib import Path

    import negotiator.play
    from negotiator.lab import transport, worker
    from negotiator.lab.checkpoints import resolve_config

    for key in ("ARENA_DATA", "ARENA_RELEASE", "NEGOTIATOR_ESTIMATES", "NEGOTIATOR_CLAIMS"):
        monkeypatch.setenv(key, "0")
    project = Path(worker.__file__).resolve().parents[3]
    checkpoint = dict(
        checkpoint_id="cp",
        runner="serial",
        config=resolve_config({}),
        data={},
        harness_version="lab-v1",
        lock_sha256=hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest(),
    )
    opens = []

    def respond(request):
        opens.append(request)
        return httpx.Response(http_status, json={"detail": "no session"})

    original = transport.JournaledArena
    monkeypatch.setattr(
        transport, "JournaledArena", lambda *args, **kw: original(*args, **kw, transport=httpx.MockTransport(respond))
    )
    invoked = []

    def custom_play(table, case_id, agent):
        invoked.append(case_id)
        return table.open(case_id)

    monkeypatch.setattr(negotiator.play, "play_case", custom_play)
    result = worker.execute(
        dict(
            checkpoint=checkpoint,
            project=str(project),
            attempt_root=str(tmp_path),
            attempt={"attempt_id": "a", "case_id": "case:S01"},
            arena_url="http://localhost",
        )
    )
    assert result["status"] == expected
    assert invoked == ["case:S01"]
    assert len(opens) == 1
    assert ("not_created" in result) == (http_status == 422)


def test_subprocess_runs_restored_source_not_mutable_receiver(tmp_path, monkeypatch):
    import subprocess

    from test_lab_checkpoints import git

    from negotiator.lab.checkpoints import create_checkpoint
    from negotiator.lab.execution import launch_worker, prepare_arms

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.org")
    git(repo, "config", "user.name", "Test")
    (repo / "pyproject.toml").write_text(
        '[project]\nname="fixture"\nversion="0.1.0"\nrequires-python=">=3.12,<3.13"\ndependencies=[]\n'
    )
    subprocess.run(["uv", "lock", "--offline"], cwd=repo, check=True, capture_output=True)
    source = repo / "src/negotiator/lab"
    source.mkdir(parents=True)
    worker = source / "worker.py"
    worker.write_text("""import json, sys
from pathlib import Path
request=json.load(sys.stdin)
if '--preflight' in sys.argv:
 print('{}')
else:
 body={'final':True,'attempt_id':request['attempt']['attempt_id'],'checkpoint_id':request['checkpoint']['checkpoint_id'],
       'session_id':'local-only','status':'completed','result':{'ended':True,'source':'checkpoint'}}
 path=Path(request['attempt_root'])/'result.json'
 path.write_text(json.dumps(body))
""")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "fixture")
    checkpoint = create_checkpoint(repo, config={}, author="test", description="fixture")
    worker.write_text('raise RuntimeError("mutable receiver must never execute")')

    class Client:
        def read(self, *args):
            return checkpoint

    manifests, projects, paths = prepare_arms(
        Client(), {"baseline_id": "cp", "candidate_id": "cp"}, repo, tmp_path / "campaign", {}
    )
    result = launch_worker(
        dict(
            checkpoint=manifests["candidate"],
            project=str(projects["candidate"]),
            attempt={"attempt_id": "a"},
            attempt_root=str(tmp_path / "attempt"),
            data_paths=paths,
        )
    )
    assert result["result"]["source"] == "checkpoint"


def test_definite_worker_failure_stops_new_starts_even_when_lease_released(tmp_path, monkeypatch):
    import negotiator.lab.campaign as execution

    store, campaign = campaign_fixture(tmp_path)
    monkeypatch.setenv("ARENA_API_KEY", "private-key")
    monkeypatch.setattr(
        execution,
        "prepare_arms",
        lambda *args: (
            {"baseline": {"checkpoint_id": "base"}, "candidate": {"checkpoint_id": "one"}},
            {"baseline": tmp_path, "candidate": tmp_path},
            {},
        ),
    )
    monkeypatch.setattr(execution, "arena_snapshot", lambda suite: None)
    calls = []

    def worker(request, **kwargs):
        calls.append(request)
        attempt = request["attempt"]
        return dict(
            attempt_id=attempt["attempt_id"],
            checkpoint_id=attempt["checkpoint_id"],
            session_id=None,
            status="failed",
            result={},
            threads={},
            not_created=dict(
                attempt_id=attempt["attempt_id"],
                checkpoint_id=attempt["checkpoint_id"],
                reason="arena_rejected",
                http_status=422,
            ),
        )

    monkeypatch.setattr(execution, "launch_worker", worker)
    result = execution.run_campaign(store, "c", tmp_path, tmp_path / "campaigns")
    assert len(calls) == 1
    assert not result["blocking_attempts"]
    assert result["next_action"]


def test_lost_start_ack_before_worker_launch_releases_lease_with_explicit_local_proof(tmp_path):
    from negotiator.lab.campaign import save_state, sync_campaign

    store, campaign = campaign_fixture(tmp_path)
    first, second = campaign["attempts"][:2]
    store.write("attempt-start", dict(attempt_id=first["attempt_id"], worker_id="c", key_id="key"))
    save_state(
        tmp_path,
        "c",
        {
            "results": {},
            "uploaded": [],
            "started": [first["attempt_id"]],
            "start_requests": {first["attempt_id"]: {"worker_id": "c"}},
        },
    )
    result = sync_campaign(store, "c", tmp_path)
    assert not result["blocking_attempts"]
    evidence = store.read("evidence", first["attempt_id"])["attempt"]
    assert evidence["not_created"]["reason"] == "worker_preflight"
    assert evidence["status"] == "failed"
    store.write("attempt-start", dict(attempt_id=second["attempt_id"], worker_id="c", key_id="key"))


def test_fully_uploaded_campaign_completes_automatically(tmp_path, monkeypatch):
    import negotiator.lab.campaign as execution

    store, campaign = campaign_fixture(tmp_path)
    monkeypatch.setenv("ARENA_API_KEY", "private-key")
    monkeypatch.setattr(
        execution,
        "prepare_arms",
        lambda *args: (
            {"baseline": {"checkpoint_id": "base"}, "candidate": {"checkpoint_id": "one"}},
            {"baseline": tmp_path, "candidate": tmp_path},
            {},
        ),
    )
    monkeypatch.setattr(execution, "arena_snapshot", lambda suite: None)
    calls = []

    def worker(request, **kwargs):
        attempt = request["attempt"]
        calls.append(attempt["attempt_id"])
        return dict(
            attempt_id=attempt["attempt_id"],
            checkpoint_id=attempt["checkpoint_id"],
            session_id=attempt["attempt_id"],
            status="completed",
            score=0.8 if attempt["arm"] == "candidate" else 0.6,
            timeouts=0,
            result={"ended": True, "deal": True, "must_haves_ok": True},
            threads={},
        )

    monkeypatch.setattr(execution, "launch_worker", worker)
    result = execution.run_campaign(store, "c", tmp_path, tmp_path / "campaigns")
    assert len(calls) == 12 and len(set(calls)) == 12
    assert result["completion"]["status"] == "promoted"
    execution.run_campaign(store, "c", tmp_path, tmp_path / "campaigns")
    assert len(calls) == 12


def test_not_created_cannot_release_known_session_or_upgrade_failure(tmp_path):
    store, campaign = campaign_fixture(tmp_path)
    attempt = campaign["attempts"][0]
    store.write("attempt-start", dict(attempt_id=attempt["attempt_id"], worker_id="w", key_id="key"))
    body = dict(
        attempt_id=attempt["attempt_id"],
        checkpoint_id=attempt["checkpoint_id"],
        reason="worker_preflight",
        worker_id="w",
        http_status=None,
    )
    store.write("attempt-not-created", body)
    with pytest.raises(ValueError):
        store.write(
            "attempt-result",
            dict(
                attempt_id=attempt["attempt_id"],
                checkpoint_id=attempt["checkpoint_id"],
                session_id="s",
                status="completed",
                result={"ended": True},
            ),
        )


def test_sync_refuses_active_local_worker_lock(tmp_path):
    import fcntl

    from negotiator.lab.campaign import campaign_dir, sync_campaign

    store, campaign = campaign_fixture(tmp_path)
    directory = campaign_dir(tmp_path, "c")
    directory.mkdir()
    with (directory / "execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match="worker is active"):
            sync_campaign(store, "c", tmp_path)


def test_worker_outer_failure_after_open_intent_never_claims_not_created(tmp_path, monkeypatch, capsys):
    import io
    import sys

    from negotiator.lab import worker
    from negotiator.state import Journal

    request = {"attempt": {"attempt_id": "a"}, "checkpoint": {"checkpoint_id": "cp"}, "attempt_root": str(tmp_path)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(request)))
    monkeypatch.setattr(sys, "argv", ["worker"])

    def fail(request):
        Journal(tmp_path / "serial.jsonl").intent(
            "case:S01", None, None, "serial-post", {"case_id": "case:S01"}, path="/sessions"
        )
        raise OSError("late disk failure")

    monkeypatch.setattr(worker, "execute", fail)
    assert worker.main() == 1
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "ambiguous"
    assert "not_created" not in body


def test_async_worker_uses_checkpoint_config_and_durable_journal_identity(tmp_path, monkeypatch):
    import hashlib
    from pathlib import Path

    import negotiator.runner
    from negotiator.lab import transport, worker
    from negotiator.lab.checkpoints import resolve_config

    for key in ("ARENA_DATA", "ARENA_RELEASE", "NEGOTIATOR_ESTIMATES", "NEGOTIATOR_CLAIMS"):
        monkeypatch.setenv(key, "0")
    project = Path(worker.__file__).resolve().parents[3]
    checkpoint = dict(
        checkpoint_id="cp",
        runner="async",
        config=resolve_config({}),
        data={},
        harness_version="lab-v1",
        lock_sha256=hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest(),
    )
    original = transport.JournaledArena
    monkeypatch.setattr(
        transport,
        "JournaledArena",
        lambda *args, **kw: original(
            *args,
            **kw,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json={"session_id": "owned", "case_id": "case:S01", "ended": True, "threads": {}}
                )
            ),
        ),
    )
    calls = []

    async def custom_play(arena, case_id, agent, journal):
        assert arena.retries == 0
        assert agent._estimates == {}
        journal.session(case_id, "owned", {"case_id": case_id})
        calls.append(case_id)
        return {"score": 0.8, "deal": True, "must_haves_ok": True, "ended": True}

    monkeypatch.setattr(negotiator.runner, "play_case", custom_play)
    result = worker.execute(
        dict(
            checkpoint=checkpoint,
            project=str(project),
            attempt_root=str(tmp_path),
            attempt={"attempt_id": "a", "case_id": "case:S01"},
            arena_url="http://localhost",
        )
    )
    assert calls == ["case:S01"]
    assert result["session_id"] == "owned"
    assert result["status"] == "completed"
    assert result["timeouts"] == 0
    assert (tmp_path / "journal.jsonl").exists()


def test_worker_env_preserves_uv_default_and_explicit_cache(monkeypatch):
    from negotiator.lab.execution import worker_env

    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    assert worker_env().get("UV_CACHE_DIR") is None
    monkeypatch.setenv("UV_CACHE_DIR", "/user/chosen/cache")
    assert worker_env()["UV_CACHE_DIR"] == "/user/chosen/cache"


def test_arena_preflight_counts_status_not_missing_ended_and_deduplicates(tmp_path, monkeypatch):
    import negotiator.lab.campaign as campaign

    details = []

    class Arena:
        def __init__(self, **kwargs):
            self.http = self

        def close(self):
            pass

        def cases(self, set_):
            assert set_ == "sandbox"
            return [{"case_id": "case:D01"}, {"case_id": "case:D02"}]

        def sessions(self, set_):
            return [{"session_id": f"ended-{i}", "status": "ended", "end_reason": "deal"} for i in range(20)] + [
                {"session_id": "open", "status": "open"},
                {"session_id": "unknown"},
            ]

        def session(self, identity):
            details.append(identity)
            return {"ended": True}

        def me(self):
            return {"practice": {"used": 20, "left": 180, "limit": 200}}

    monkeypatch.setattr(campaign, "ArenaClient", Arena)
    from negotiator.lab.policy import default_suite

    snapshot = campaign.arena_snapshot(default_suite())
    assert snapshot["open_sessions"] == 1
    assert details == ["unknown"]


def test_environment_mismatch_and_hosted_simulator_fail_before_reservation(monkeypatch, capsys):
    from negotiator.lab import campaign, loop_cli
    from negotiator.lab.policy import default_suite

    writes = []

    class Arena:
        def __init__(self, **kwargs):
            self.http = self

        def close(self):
            pass

        def cases(self, set_):
            return [{"case_id": "case:D01"}]

    class Client:
        def __init__(self, *args):
            pass

        def read(self, *args):
            return {**default_suite(), "cases": ["case:P01"]}

        def write(self, *args):
            writes.append(args)

    monkeypatch.setattr(loop_cli, "LoopClient", Client)
    monkeypatch.setattr(campaign, "ArenaClient", Arena)
    assert (
        loop_cli.main(
            ["campaign", "run", "--family", "f", "--candidate", "c", "--hypothesis", "x", "--max-sessions", "12"]
        )
        != 0
    )
    capsys.readouterr()
    assert writes == []
    with pytest.raises(ValueError, match="simulator"):
        campaign.arena_snapshot(default_suite(environment="simulator"))


@pytest.mark.parametrize("observations", [False, True])
def test_two_roots_losing_executor_cannot_launch_or_release_winner(tmp_path, monkeypatch, observations):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    import negotiator.lab.campaign as execution

    store, campaign = campaign_fixture(tmp_path)
    barrier = threading.Barrier(2)
    release = threading.Event()
    winner_started = threading.Event()
    launches = []

    class RacingClient:
        def read(self, *args):
            return store.read(*args)

        def write(self, op, body):
            if op == "attempt-start":
                barrier.wait(timeout=5)
            return store.write(op, body)

    monkeypatch.setenv("ARENA_API_KEY", "private-key")
    monkeypatch.setattr(
        execution,
        "prepare_arms",
        lambda *args: (
            {"baseline": {"checkpoint_id": "base"}, "candidate": {"checkpoint_id": "one"}},
            {"baseline": tmp_path, "candidate": tmp_path},
            {},
        ),
    )
    counter = __import__("itertools").count()
    monkeypatch.setattr(
        execution,
        "arena_snapshot",
        lambda suite: (
            {"remaining": 200, "observed_at": __import__("time").time() + next(counter) * 0.001, "open_sessions": 0}
            if observations
            else None
        ),
    )

    def worker(request, **kwargs):
        launches.append(request)
        winner_started.set()
        assert release.wait(5)
        return dict(
            attempt_id=request["attempt"]["attempt_id"],
            checkpoint_id=request["checkpoint"]["checkpoint_id"],
            session_id="owned",
            status="ambiguous",
            result={},
            threads={},
        )

    monkeypatch.setattr(execution, "launch_worker", worker)
    roots = [tmp_path / "laptop-one", tmp_path / "laptop-two"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(execution.run_campaign, RacingClient(), "c", tmp_path, root) for root in roots]
        assert winner_started.wait(5)
        import time

        deadline = time.monotonic() + 5
        while not any(f.done() for f in futures) and time.monotonic() < deadline:
            time.sleep(0.01)
        losers = [i for i, f in enumerate(futures) if f.done()]
        try:
            assert len(losers) == 1
            loser = losers[0]
            with pytest.raises(ValueError):
                futures[loser].result()
            state = execution.sync_campaign(store, "c", roots[loser])
            assert state["blocking_attempts"]
            attempt = store.read("campaigns", "c")["attempts"][0]
            assert attempt["status"] == "started" and "not_created" not in attempt
            assert len(launches) == 1
        finally:
            release.set()
        futures[1 - losers[0]].result()


def test_backend_not_created_requires_start_owner(tmp_path):
    store, campaign = campaign_fixture(tmp_path)
    first, second = campaign["attempts"][:2]
    store.write("attempt-start", dict(attempt_id=first["attempt_id"], worker_id="winner", key_id="key"))
    with pytest.raises(ValueError):
        store.write(
            "attempt-not-created",
            dict(
                attempt_id=first["attempt_id"],
                checkpoint_id=first["checkpoint_id"],
                worker_id="loser",
                reason="worker_preflight",
            ),
        )
    with pytest.raises(ValueError):
        store.write("attempt-start", dict(attempt_id=second["attempt_id"], worker_id="another", key_id="key"))


def test_orphaned_child_holds_lock_and_sync_uploads_only_final_result(tmp_path):
    import hashlib
    import os
    import subprocess
    import sys
    import time
    from pathlib import Path

    from negotiator.lab.campaign import save_state, sync_campaign

    store, campaign = campaign_fixture(tmp_path)
    attempt = campaign["attempts"][0]
    store.write("attempt-start", dict(attempt_id=attempt["attempt_id"], worker_id="proc-owner", key_id="key"))
    root = tmp_path / "campaigns"
    save_state(
        root,
        "c",
        {
            "results": {},
            "uploaded": [],
            "started": [attempt["attempt_id"]],
            "start_requests": {attempt["attempt_id"]: {"worker_id": "proc-owner"}},
        },
    )
    project = tmp_path / "fixture"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname="fixture"\nversion="0.1.0"\nrequires-python=">=3.12,<3.13"\ndependencies=[]\n'
    )
    subprocess.run(["uv", "lock", "--offline"], cwd=project, check=True, capture_output=True)
    subprocess.run(["uv", "sync", "--locked", "--offline"], cwd=project, check=True, capture_output=True)
    module = project / "src/negotiator/lab"
    module.mkdir(parents=True)
    (module / "worker.py").write_text("""import json, sys, time
from pathlib import Path
r=json.load(sys.stdin)
root=Path(r['attempt_root'])
body=dict(attempt_id=r['attempt']['attempt_id'],checkpoint_id=r['checkpoint']['checkpoint_id'],
          session_id='owned',status='ambiguous',score=None,timeouts=None,result={},threads={})
(root/'progress.json').write_text(json.dumps(body))
(root/'ready').write_text('ready')
end=time.monotonic()+10
while not (root/'finish').exists() and time.monotonic()<end:
 time.sleep(.01)
body.update(final=True,status='completed',score=.8,timeouts=0,result=dict(ended=True,deal=True,must_haves_ok=True))
(root/'result.json').write_text(json.dumps(body))
""")
    attempt_root = root / "c/attempts" / hashlib.sha256(attempt["attempt_id"].encode()).hexdigest()
    request = dict(
        project=str(project),
        attempt_root=str(attempt_root),
        attempt=attempt,
        checkpoint={"checkpoint_id": attempt["checkpoint_id"]},
    )
    code = """import fcntl,json,sys
from pathlib import Path
from negotiator.lab.execution import launch_worker
r=json.load(sys.stdin)
with (Path(r['attempt_root']).parents[1]/'execution.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 launch_worker(r,lock_fd=lock.fileno())
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    coordinator = subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    coordinator.stdin.write(json.dumps(request))
    coordinator.stdin.close()
    try:
        deadline = time.monotonic() + 8
        while not (attempt_root / "ready").exists() and time.monotonic() < deadline:
            assert coordinator.poll() is None
            time.sleep(0.01)
        assert (attempt_root / "ready").exists()
        assert not (attempt_root / "result.json").exists()
        coordinator.kill()
        coordinator.wait(timeout=3)
        with pytest.raises(ValueError, match="worker is active"):
            sync_campaign(store, "c", root)
        assert store.read("campaigns", "c")["attempts"][0]["status"] == "started"
        (attempt_root / "finish").touch()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            try:
                state = sync_campaign(store, "c", root)
                break
            except ValueError as error:
                assert "worker is active" in str(error)
                time.sleep(0.01)
        else:
            pytest.fail("child did not release inherited lock")
        uploaded = store.read("campaigns", "c")["attempts"][0]
        assert uploaded["status"] == "completed" and uploaded["session_id"] == "owned"
        assert uploaded["score"] == 0.8
        assert attempt["attempt_id"] in state["uploaded"]
    finally:
        if attempt_root.exists():
            (attempt_root / "finish").touch()
        if coordinator.poll() is None:
            coordinator.kill()
            coordinator.wait(timeout=3)
        coordinator.stderr.close()


def test_progress_preserves_identity_without_becoming_terminal_upload(tmp_path):
    import hashlib

    from negotiator.lab.campaign import save_state, sync_campaign
    from negotiator.lab.worker import durable_json

    store, campaign = campaign_fixture(tmp_path)
    attempt = campaign["attempts"][0]
    identity = attempt["attempt_id"]
    store.write("attempt-start", dict(attempt_id=identity, worker_id="owner", key_id="key"))
    save_state(
        tmp_path,
        "c",
        {"results": {}, "uploaded": [], "started": [identity], "start_requests": {identity: {"worker_id": "owner"}}},
    )
    root = tmp_path / "c/attempts" / hashlib.sha256(identity.encode()).hexdigest()
    durable_json(root / "request.json", {"worker_id": "owner"})
    body = dict(
        attempt_id=identity,
        checkpoint_id=attempt["checkpoint_id"],
        session_id="known",
        status="ambiguous",
        score=None,
        timeouts=None,
        result={},
        threads={},
    )
    durable_json(root / "progress.json", body)
    durable_json(root / "result.json", body)
    state = sync_campaign(store, "c", tmp_path)
    assert state["progress"][identity]["session_id"] == "known"
    assert not state["uploaded"]
    assert store.read("campaigns", "c")["attempts"][0]["status"] == "started"
    final = {
        **body,
        "final": True,
        "status": "completed",
        "score": 0.8,
        "timeouts": 0,
        "result": {"ended": True, "deal": True, "must_haves_ok": True},
    }
    durable_json(root / "result.json", final)
    state = sync_campaign(store, "c", tmp_path)
    assert state["results"][identity]["status"] == "completed"
    assert store.read("campaigns", "c")["attempts"][0]["status"] == "completed"


@pytest.mark.parametrize("listed_as_started", [True, False])
def test_repeated_prelaunch_recovery_then_resume_uses_fresh_owner(tmp_path, monkeypatch, listed_as_started):
    import negotiator.lab.campaign as execution

    store, campaign = campaign_fixture(tmp_path)
    identity = campaign["attempts"][0]["attempt_id"]
    execution.save_state(
        tmp_path,
        "c",
        {
            "results": {},
            "uploaded": [],
            "started": [identity] if listed_as_started else [],
            "start_requests": {identity: {"worker_id": "obsolete-owner"}},
        },
    )
    first = execution.sync_campaign(store, "c", tmp_path)
    second = execution.sync_campaign(store, "c", tmp_path)
    assert identity not in first["started"]
    assert identity not in second["start_requests"]
    monkeypatch.setenv("ARENA_API_KEY", "private-key")
    monkeypatch.setattr(execution, "arena_snapshot", lambda suite: None)
    monkeypatch.setattr(
        execution,
        "prepare_arms",
        lambda *args: (
            {"baseline": {"checkpoint_id": "base"}, "candidate": {"checkpoint_id": "one"}},
            {"baseline": tmp_path, "candidate": tmp_path},
            {},
        ),
    )
    owners = []

    def worker(request, **kwargs):
        owners.append(request["worker_id"])
        return dict(
            attempt_id=request["attempt"]["attempt_id"],
            checkpoint_id=request["checkpoint"]["checkpoint_id"],
            session_id="known",
            status="ambiguous",
            result={},
            threads={},
        )

    monkeypatch.setattr(execution, "launch_worker", worker)
    resumed = execution.run_campaign(store, "c", tmp_path, tmp_path)
    assert len(owners) == 1 and owners[0] != "obsolete-owner"
    assert resumed["blocking_attempts"] == [identity]
    assert store.read("campaigns", "c")["attempts"][0]["start"]["request"]["worker_id"] == owners[0]
