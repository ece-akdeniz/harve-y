import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from negotiator.lab.checkpoints import resolve_config
from negotiator.lab.loop_store import LoopStore
from negotiator.lab.policy import default_suite
from negotiator.lab.server import DashboardServer
from negotiator.lab.store import Store


def checkpoint(name):
    return dict(
        schema_version=1,
        checkpoint_id=name,
        commit="a" * 40,
        project_path=".",
        author="tester",
        description="test",
        parent_id=None,
        created_at="2026-10-10T12:00:00+00:00",
        agent="package",
        config=resolve_config({}),
        runner="serial",
        lock_sha256="b" * 64,
        submodules={},
        data={},
        harness_version="lab-v1",
        remote="https://example.org/repo.git",
        ref=f"refs/heads/lab/checkpoints/{name}",
        published=True,
    )


@pytest.fixture
def loop(tmp_path):
    loop = LoopStore(tmp_path / "lab.sqlite")
    for name in ("base", "one", "two"):
        loop.write("checkpoint", checkpoint(name))
    loop.write("suite", default_suite())
    loop.write("family", dict(family_id="f", max_sessions=24))
    loop.write("seed", dict(suite_id=default_suite()["suite_id"], checkpoint_id="base", author="tester"))
    return loop


def campaign(loop, name="c", **changes):
    return loop.write(
        "campaign",
        dict(
            campaign_id=name,
            family_id="f",
            suite_id=default_suite()["suite_id"],
            baseline_id="base",
            candidate_id="one",
            generation=1,
            seed=1,
            author="tester",
            hypothesis="test",
            **changes,
        ),
    )


def finish(loop, campaign):
    for a in campaign["attempts"]:
        loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="laptop", key_id="shared"))
        loop.write(
            "attempt-result",
            dict(
                attempt_id=a["attempt_id"],
                checkpoint_id=a["checkpoint_id"],
                session_id=a["attempt_id"],
                status="completed",
                score=0.7 if a["arm"] == "candidate" else 0.6,
                timeouts=0,
                result={"deal": True, "must_haves_ok": True, "ended": True},
                threads={},
                elapsed_s=1.0,
            ),
        )


def test_promotion_stale_idempotency_restore(loop):
    first, second = campaign(loop), campaign(loop, "other")
    finish(loop, first)
    finish(loop, second)
    result = loop.write("complete", {"campaign_id": "c"})
    assert result["status"] == "promoted"
    assert loop.write("complete", {"campaign_id": "c"}) == result
    assert loop.write("complete", {"campaign_id": "other"})["status"] == "baseline_superseded"
    assert len(loop.read("history")["history"]) == 2
    loop.write(
        "restore",
        dict(
            request_id="restore-1",
            suite_id=default_suite()["suite_id"],
            checkpoint_id="base",
            generation=2,
            author="tester",
        ),
    )
    assert loop.read("recommended", default_suite()["suite_id"])["checkpoint_id"] == "base"
    assert len(loop.read("history")["history"]) == 3


def test_reservation_race_and_start_lease(loop):
    def reserve(name):
        try:
            return campaign(loop, name)
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = list(pool.map(reserve, ["a", "b", "c"]))
    assert sum(x is not None for x in outcomes) == 2
    attempts = [x["attempts"][0] for x in outcomes if x]
    loop.write("attempt-start", dict(attempt_id=attempts[0]["attempt_id"], worker_id="a", key_id="key"))
    with pytest.raises(ValueError):
        loop.write("attempt-start", dict(attempt_id=attempts[1]["attempt_id"], worker_id="b", key_id="key"))
    assert loop.read("families", "f")["reserved_sessions"] == 24


def test_reject_changed_outcome_and_bad_finding(loop):
    c = campaign(loop)
    finish(loop, c)
    a = c["attempts"][0]
    body = dict(
        attempt_id=a["attempt_id"],
        checkpoint_id="base",
        session_id=a["attempt_id"],
        status="completed",
        score=0.1,
        timeouts=0,
        result={},
        threads={},
        elapsed_s=1.0,
    )
    with pytest.raises(ValueError):
        loop.write("attempt-result", body)
    with pytest.raises(ValueError):
        loop.write(
            "finding",
            dict(
                finding_id="x",
                campaign_id="c",
                candidate_id="one",
                author="tester",
                observation="x",
                hypothesis="x",
                change="x",
                next_test="x",
                confidence=0.5,
                disposition="proposed",
                evidence=[dict(attempt_id=a["attempt_id"], supplier="missing", message_index=0)],
            ),
        )


def test_checkpoint_and_suite_immutability(loop):
    with pytest.raises(ValueError):
        loop.write("checkpoint", {**checkpoint("base"), "description": "changed"})
    with pytest.raises(ValueError):
        loop.write("suite", {**default_suite(), "repetitions": 4})


def test_http_loop_auth(tmp_path):
    server = DashboardServer(
        ("127.0.0.1", 0), Store(tmp_path / "http.sqlite"), password="password", upload_token="token"
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            assert client.get("/api/loop/overview").status_code == 401
            assert client.post("/api/loop/suite", json=default_suite()).status_code == 401
            assert client.post("/api/login", json={"password": "password"}).status_code == 200
            assert client.get("/api/loop/overview").status_code == 200
            assert client.post("/api/loop/suite", json=default_suite()).status_code == 401
            assert (
                client.post(
                    "/api/loop/suite", json=default_suite(), headers={"Authorization": "Bearer token"}
                ).status_code
                == 200
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_practice_quota_atomic_and_ambiguous_lease_not_refunded(loop):
    import time

    suite = default_suite(environment="practice")
    loop.write("suite", suite)
    loop.write("family", dict(family_id="practice", max_sessions=100, practice_allowance=24, reserve=5))
    loop.write("seed", dict(suite_id=suite["suite_id"], checkpoint_id="base", author="tester"))
    request = dict(
        campaign_id="practice-1",
        family_id="practice",
        suite_id=suite["suite_id"],
        baseline_id="base",
        candidate_id="one",
        generation=1,
        seed=1,
        author="tester",
        hypothesis="x",
    )
    with pytest.raises(ValueError):
        loop.write("campaign", request)
    request["quota"] = dict(remaining=20, observed_at=time.time(), open_sessions=0)
    first = loop.write("campaign", request)
    with pytest.raises(ValueError):
        loop.write("campaign", {**request, "campaign_id": "practice-2"})
    a = first["attempts"][0]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="a", key_id="p", quota=request["quota"]))
    loop.write(
        "attempt-result",
        dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id=None,
            status="ambiguous",
            score=None,
            timeouts=None,
        ),
    )
    with pytest.raises(ValueError):
        loop.write(
            "attempt-start",
            dict(attempt_id=first["attempts"][1]["attempt_id"], worker_id="a", key_id="p", quota=request["quota"]),
        )
    assert loop.read("families", "practice")["reserved_sessions"] == 12


def test_valid_finding_and_evidence_are_traceable(loop):
    c = campaign(loop)
    a = c["attempts"][0]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
    loop.write(
        "attempt-result",
        dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id="s",
            status="completed",
            score=0.6,
            timeouts=0,
            result={"deal": False, "ended": True},
            threads={"supplier": {"messages": [{"text": "evidence"}]}},
            elapsed_s=1.0,
        ),
    )
    body = dict(
        finding_id="finding",
        campaign_id="c",
        candidate_id="one",
        author="tester",
        observation="x",
        hypothesis="x",
        change="x",
        next_test="x",
        confidence=0.5,
        disposition="proposed",
        evidence=[dict(attempt_id=a["attempt_id"], supplier="supplier", message_index=0)],
    )
    assert loop.write("finding", body)["finding_id"] == "finding"
    assert loop.read("evidence", a["attempt_id"])["attempt"]["threads"]["supplier"]["messages"][0]["text"] == "evidence"
    assert "threads" not in str(loop.read("overview"))


def test_duplicate_session_and_mismatch_rejected(loop):
    c = campaign(loop)
    a, b = c["attempts"][:2]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
    loop.write(
        "attempt-result",
        dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id="shared",
            result={"ended": True},
            status="completed",
            score=0.6,
            timeouts=0,
        ),
    )
    loop.write("attempt-start", dict(attempt_id=b["attempt_id"], worker_id="w", key_id="k"))
    with pytest.raises(ValueError):
        loop.write(
            "attempt-result",
            dict(
                attempt_id=b["attempt_id"],
                checkpoint_id=b["checkpoint_id"],
                session_id="shared",
                status="completed",
                score=0.6,
                timeouts=0,
            ),
        )
    with pytest.raises(ValueError):
        loop.write(
            "attempt-result",
            dict(
                attempt_id=b["attempt_id"],
                checkpoint_id="two",
                session_id="new",
                status="completed",
                score=0.6,
                timeouts=0,
            ),
        )


def test_premature_completion_does_not_freeze_campaign(loop):
    c = campaign(loop)
    with pytest.raises(ValueError):
        loop.write("complete", {"campaign_id": "c"})
    assert loop.read("campaigns", "c")["status"] == "running"
    loop.write("attempt-start", dict(attempt_id=c["attempts"][0]["attempt_id"], worker_id="w", key_id="k"))


def test_ambiguous_known_session_retains_lease_until_reconciled(loop):
    c = campaign(loop)
    a, b = c["attempts"][:2]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
    loop.write(
        "attempt-result",
        dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id="lost",
            status="ambiguous",
            score=None,
            timeouts=None,
        ),
    )
    with pytest.raises(ValueError):
        loop.write("attempt-start", dict(attempt_id=b["attempt_id"], worker_id="w", key_id="k"))
    reconciliation = dict(
        attempt_id=a["attempt_id"],
        checkpoint_id=a["checkpoint_id"],
        session_id="lost",
        result={"ended": True, "deal": False},
        threads={},
        timeouts=0,
        score=0.5,
    )
    restored = loop.write("attempt-reconcile", reconciliation)
    assert restored["status"] == "ambiguous"
    assert restored["score"] is None
    assert loop.write("attempt-reconcile", reconciliation) == restored
    loop.write("attempt-start", dict(attempt_id=b["attempt_id"], worker_id="w", key_id="k"))


def test_restore_requires_previously_recommended_checkpoint(loop):
    with pytest.raises(ValueError):
        loop.write(
            "restore",
            dict(
                request_id="r", suite_id=default_suite()["suite_id"], checkpoint_id="two", generation=1, author="tester"
            ),
        )


def test_practice_concurrent_clients_cannot_overspend(loop):
    import time

    suite = default_suite(environment="practice")
    loop.write("suite", suite)
    loop.write("family", dict(family_id="p", max_sessions=100, practice_allowance=100, reserve=5))
    loop.write("seed", dict(suite_id=suite["suite_id"], checkpoint_id="base", author="tester"))

    def reserve(name):
        try:
            return loop.write(
                "campaign",
                dict(
                    campaign_id=name,
                    family_id="p",
                    suite_id=suite["suite_id"],
                    baseline_id="base",
                    candidate_id="one",
                    generation=1,
                    seed=1,
                    author="tester",
                    hypothesis="x",
                    quota=dict(remaining=20, observed_at=time.time(), open_sessions=0),
                ),
            )
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(x is not None for x in pool.map(reserve, ["p1", "p2"])) == 1


@pytest.mark.parametrize(
    "change", [dict(runner="async"), dict(data={"release": {"sha256": "c" * 64, "source": "https://example.org/data"}})]
)
def test_execution_inputs_must_match_suite(loop, change):
    loop.write("checkpoint", {**checkpoint("different"), **change})
    with pytest.raises(ValueError):
        loop.write(
            "campaign",
            dict(
                campaign_id="bad",
                family_id="f",
                suite_id=default_suite()["suite_id"],
                baseline_id="base",
                candidate_id="different",
                generation=1,
                seed=1,
                author="tester",
                hypothesis="x",
            ),
        )


def test_concurrent_hosted_start_has_single_owner(loop):
    c = campaign(loop)

    def start(attempt):
        try:
            return loop.write(
                "attempt-start", dict(attempt_id=attempt["attempt_id"], worker_id=attempt["arm"], key_id="key")
            )
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(x is not None for x in pool.map(start, c["attempts"][:2])) == 1


def test_history_is_chronological(loop):
    c = campaign(loop)
    finish(loop, c)
    loop.write("complete", {"campaign_id": "c"})
    assert [event["action"] for event in loop.read("history")["history"]] == ["seed", "promotion"]


def test_reconciled_unknown_start_cannot_be_upgraded_to_original_success(loop):
    c = campaign(loop)
    a = c["attempts"][0]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
    loop.write(
        "attempt-reconcile",
        dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id="recovered",
            result={"ended": True},
            score=0.6,
        ),
    )
    with pytest.raises(ValueError):
        loop.write(
            "attempt-result",
            dict(
                attempt_id=a["attempt_id"],
                checkpoint_id=a["checkpoint_id"],
                session_id="recovered",
                result={"ended": True},
                status="completed",
                score=0.6,
            ),
        )
    assert loop.read("evidence", a["attempt_id"])["attempt"]["status"] == "ambiguous"


@pytest.mark.parametrize("alias", ["https://arena.tacto.ai/", "https://ARENA.TACTO.AI", "https://arena.tacto.ai:443/"])
def test_equivalent_arena_origins_share_practice_reservations(loop, alias):
    import time

    loop.write("family", dict(family_id="shared-practice", max_sessions=100, practice_allowance=100, reserve=5))
    for name, origin in [("first", "https://arena.tacto.ai"), ("second", alias)]:
        suite = {**default_suite(environment="practice"), "suite_id": name, "arena_url": origin}
        stored = loop.write("suite", suite)
        loop.write("seed", dict(suite_id=name, checkpoint_id="base", author="tester"))
        request = dict(
            campaign_id=name,
            family_id="shared-practice",
            suite_id=name,
            baseline_id="base",
            candidate_id="one",
            generation=1,
            seed=1,
            author="tester",
            hypothesis="x",
            quota=dict(remaining=20, observed_at=time.time(), open_sessions=0),
        )
        if name == "first":
            loop.write("campaign", request)
        else:
            with pytest.raises(ValueError):
                loop.write("campaign", request)
            assert stored["arena_url"] == "https://arena.tacto.ai"
    assert loop.read("families", "shared-practice")["practice_reserved"] == 12


def test_equivalent_origins_share_session_ownership(loop):
    first = campaign(loop)
    alias = {**default_suite(), "suite_id": "alias", "arena_url": "https://ARENA.TACTO.AI:443/"}
    loop.write("suite", alias)
    loop.write("seed", dict(suite_id="alias", checkpoint_id="base", author="tester"))
    second = loop.write(
        "campaign",
        dict(
            campaign_id="other",
            family_id="f",
            suite_id="alias",
            baseline_id="base",
            candidate_id="one",
            generation=1,
            seed=1,
            author="tester",
            hypothesis="x",
        ),
    )
    a, b = first["attempts"][0], second["attempts"][0]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
    loop.write(
        "attempt-result",
        dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id="same",
            status="completed",
            score=0.6,
            timeouts=0,
            result={"ended": True},
        ),
    )
    loop.write("attempt-start", dict(attempt_id=b["attempt_id"], worker_id="w", key_id="k"))
    with pytest.raises(ValueError):
        loop.write(
            "attempt-result",
            dict(
                attempt_id=b["attempt_id"],
                checkpoint_id=b["checkpoint_id"],
                session_id="same",
                status="completed",
                score=0.6,
                timeouts=0,
                result={"ended": True},
            ),
        )


def test_recovered_only_campaign_never_promotes(loop):
    c = campaign(loop)
    for a in c["attempts"]:
        loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
        recovered = dict(
            attempt_id=a["attempt_id"],
            checkpoint_id=a["checkpoint_id"],
            session_id=a["attempt_id"],
            result={"ended": True, "deal": True, "must_haves_ok": True},
            score=0.7 if a["arm"] == "candidate" else 0.6,
            timeouts=0,
        )
        loop.write("attempt-reconcile", recovered)
        with pytest.raises(ValueError):
            loop.write("attempt-result", {**recovered, "status": "completed"})
    assert loop.write("complete", {"campaign_id": "c"})["status"] == "insufficient_evidence"
    assert loop.read("recommended", default_suite()["suite_id"])["checkpoint_id"] == "base"
    assert len(loop.read("history")["history"]) == 1


def test_reconciliation_session_identity_is_immutable(loop):
    c = campaign(loop)
    a = c["attempts"][0]
    loop.write("attempt-start", dict(attempt_id=a["attempt_id"], worker_id="w", key_id="k"))
    original = dict(
        attempt_id=a["attempt_id"],
        checkpoint_id=a["checkpoint_id"],
        session_id="original",
        status="ambiguous",
        score=None,
        timeouts=None,
    )
    loop.write("attempt-result", original)
    with pytest.raises(ValueError):
        loop.write(
            "attempt-reconcile",
            dict(
                attempt_id=a["attempt_id"],
                checkpoint_id=a["checkpoint_id"],
                session_id="different",
                result={"ended": True},
            ),
        )
    recovered = dict(
        attempt_id=a["attempt_id"], checkpoint_id=a["checkpoint_id"], session_id="original", result={"ended": True}
    )
    loop.write("attempt-reconcile", recovered)
    with pytest.raises(ValueError):
        loop.write("attempt-reconcile", {**recovered, "session_id": "changed"})
    assert loop.write("attempt-result", original)["session_id"] == "original"


@pytest.mark.parametrize("ended", [False, None])
def test_original_nonended_samples_cannot_promote_even_after_reconciliation(loop, ended):
    planned = campaign(loop)
    for attempt in planned["attempts"]:
        loop.write("attempt-start", dict(attempt_id=attempt["attempt_id"], worker_id="w", key_id=attempt["attempt_id"]))
        result = {"deal": True, "must_haves_ok": True}
        if ended is not None:
            result["ended"] = ended
        loop.write(
            "attempt-result",
            dict(
                attempt_id=attempt["attempt_id"],
                checkpoint_id=attempt["checkpoint_id"],
                session_id=attempt["attempt_id"],
                status="completed",
                score=0.7 if attempt["arm"] == "candidate" else 0.6,
                timeouts=0,
                result=result,
            ),
        )
        loop.write(
            "attempt-reconcile",
            dict(
                attempt_id=attempt["attempt_id"],
                checkpoint_id=attempt["checkpoint_id"],
                session_id=attempt["attempt_id"],
                result={**result, "ended": True},
            ),
        )
    completion = loop.write("complete", {"campaign_id": "c"})
    assert completion["status"] == "insufficient_evidence"
    gate = next(g for g in completion["evaluation"]["gates"] if g["id"] == "complete_sample")
    assert gate["passed"] is False
    assert loop.read("recommended", planned["suite_id"])["checkpoint_id"] == "base"
    assert len(loop.read("history")["history"]) == 1
