"""PD1.3 local fault tests; all Arena and Lab traffic is injected in-process."""

import json

import httpx
import pytest

from experiments.v2.run_hosted_sandbox import capture_terminal_evidence, publication_state_path, publish_verified
from negotiator.lab.lifecycle import PublicationJournal
from negotiator.lab.runner import plan_run


def make_run(tmp_path):
    return plan_run(name="PD1.3 fake only", author="test", hypothesis="terminal and publication barriers",
                    agent="fake", config={}, cases=["case:D01"], repetitions=1, max_sessions=1,
                    environment="sandbox", arena_url="https://arena.example", provenance={})


class FakeAgent:
    def __init__(self):
        self.terminal = None
        self.outcome = None
        self.attachments = {}

    def observe_lab_terminal(self, state):
        assert state["status"] == "ended"
        self.terminal = state

    def observe_lab_outcome(self, result, threads):
        self.outcome = (result, threads)

    def observe_lab_attachment(self, attachment_id, content):
        self.attachments[attachment_id] = content

    def experiment_evidence(self):
        return {"terminal_json": json.dumps(self.terminal, sort_keys=True)}


class EndedArena:
    def __init__(self, *, fail_first=False):
        self.fail_first, self.sessions = fail_first, 0
        self.state = {"session_id": "session-owned", "status": "ended", "rounds": 2,
                      "threads": {"supplier": {"status": "ended"}},
                      "result": {"deal": False, "score": 0.0}}

    def session(self, session_id):
        assert session_id == "session-owned"
        self.sessions += 1
        if self.fail_first and self.sessions == 1:
            raise httpx.ReadTimeout("injected transient GET timeout")
        return self.state

    def thread(self, session_id, supplier):
        return {"messages": [{"from": "supplier", "body": "withdrawn"}], "timeouts": []}

    def attachment(self, session_id, attachment_id):
        return b"fixture attachment"


def prepare_terminal(tmp_path, run=None):
    run = run or make_run(tmp_path)
    attempt = run.attempts[0]
    attempt.session_id, attempt.status = "session-owned", "failed"
    attempt.error = "attempt failed (TimeoutError)"
    run.status = "failed"
    return run


def test_successful_terminal_collection_and_single_publication(tmp_path, monkeypatch):
    run = prepare_terminal(tmp_path)
    journal = PublicationJournal(publication_state_path(tmp_path, run.run_id))
    journal.save()
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    puts, gets = [], []
    remote = {}

    def handle(request):
        if request.method == "PUT":
            puts.append(request)
            remote[run.run_id] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})
        gets.append(request)
        if request.url.path.endswith("/" + run.run_id):
            return httpx.Response(200, json=remote[run.run_id])
        return httpx.Response(200, json={"runs": [{"run_id": run.run_id}]})

    monkeypatch.setenv("LAB_UPLOAD_TOKEN", "fake-token")
    proof = publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(handle))
    assert proof["retrieval_verified"] and len(puts) == 1 and len(gets) == 2
    state = json.loads(publication_state_path(tmp_path, run.run_id).read_text())
    assert state["publication"]["write_attempted"] is True
    assert state["publication"]["payload_sha256"] == proof["payload_sha256"]
    assert state["publication"]["status"] == "verified"


def test_failed_execution_and_terminal_arena_outcome_remain_distinct(tmp_path):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    assert run.status == "failed" and run.attempts[0].status == "failed"
    assert run.attempts[0].error.startswith("attempt failed")
    assert run.attempts[0].result["deal"] is False
    evidence = json.loads((tmp_path / "terminal-evidence/session-owned.json").read_text())
    assert evidence["status"] == "complete" and evidence["session"]["status"] == "ended"


def test_terminal_timeout_retains_local_partial_and_blocks_publication(tmp_path, monkeypatch):
    class OpenArena(EndedArena):
        def __init__(self):
            super().__init__()
            self.state["status"] = "open"

    run = prepare_terminal(tmp_path)
    with pytest.raises(ValueError, match="publication is blocked"):
        capture_terminal_evidence(run, OpenArena(), FakeAgent(), tmp_path, wait_seconds=.04,
                                  request_timeout=.02, poll_interval=.01)
    monkeypatch.setenv("LAB_UPLOAD_TOKEN", "fake-token")
    with pytest.raises(ValueError, match="complete terminal evidence"):
        publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(lambda _: pytest.fail()))
    state = json.loads(publication_state_path(tmp_path, run.run_id).read_text())
    assert state["evidence_collection"]["status"] == "missing"
    assert json.loads((tmp_path / "terminal-evidence/session-owned.json").read_text())["status"] == "missing"
    assert not state["publication"]["write_attempted"]


def test_transient_terminal_read_failure_recovers_within_bound(tmp_path):
    run = prepare_terminal(tmp_path)
    arena = EndedArena(fail_first=True)
    capture_terminal_evidence(run, arena, FakeAgent(), tmp_path, wait_seconds=1,
                              request_timeout=.2, poll_interval=.001)
    assert arena.sessions >= 2
    assert json.loads((tmp_path / "terminal-evidence/session-owned.json").read_text())["status"] == "complete"


def test_interruption_during_collection_persists_recoverable_state(tmp_path):
    run = prepare_terminal(tmp_path)

    class InterruptedArena(EndedArena):
        def session(self, session_id):
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        capture_terminal_evidence(run, InterruptedArena(), FakeAgent(), tmp_path, wait_seconds=1,
                                  request_timeout=.2)
    state = json.loads(publication_state_path(tmp_path, run.run_id).read_text())
    assert state["evidence_collection"]["status"] == "missing"
    assert state["publication"]["write_status"] == "not_attempted"
    assert json.loads((tmp_path / "terminal-evidence/session-owned.json").read_text())["status"] == "interrupted"


def test_interrupted_terminal_collection_resumes_same_owned_session(tmp_path):
    run = prepare_terminal(tmp_path)

    class InterruptedThreadOnce(EndedArena):
        interrupted = False

        def thread(self, session_id, supplier):
            if not self.interrupted:
                self.interrupted = True
                raise KeyboardInterrupt()
            return super().thread(session_id, supplier)

    arena, agent = InterruptedThreadOnce(), FakeAgent()
    with pytest.raises(KeyboardInterrupt):
        capture_terminal_evidence(run, arena, agent, tmp_path, wait_seconds=1, request_timeout=.2)
    partial = json.loads((tmp_path / "terminal-evidence/session-owned.json").read_text())
    assert partial["session"]["status"] == "ended" and partial["status"] == "interrupted"
    capture_terminal_evidence(run, arena, agent, tmp_path, wait_seconds=1, request_timeout=.2)
    resumed = json.loads((tmp_path / "terminal-evidence/session-owned.json").read_text())
    assert resumed["session"]["status"] == "ended" and resumed["status"] == "complete"
    assert arena.sessions == 2


def test_interruption_before_write_can_resume_but_payload_is_frozen(tmp_path, monkeypatch):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    state = PublicationJournal(publication_state_path(tmp_path, run.run_id))
    state.prepare(run, "https://lab.example", terminal_complete=True)
    digest = state.state["publication"]["payload_sha256"]
    resumed = PublicationJournal(publication_state_path(tmp_path, run.run_id))
    assert resumed.state["publication"]["payload_sha256"] == digest
    assert not resumed.state["publication"]["write_attempted"]
    monkeypatch.setenv("LAB_UPLOAD_TOKEN", "fake-token")
    remote, puts = {}, []

    def handle(request):
        if request.method == "PUT":
            puts.append(request)
            remote[run.run_id] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})
        if request.url.path.endswith("/" + run.run_id):
            return httpx.Response(200, json=remote[run.run_id])
        return httpx.Response(200, json={"runs": [{"run_id": run.run_id}]})

    assert publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(handle))
    assert len(puts) == 1


def test_independent_publication_owners_share_one_durable_write_claim(tmp_path):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    path = publication_state_path(tmp_path, run.run_id)
    owner_a, owner_b = PublicationJournal(path), PublicationJournal(path)
    owner_a.prepare(run, "https://lab.example", terminal_complete=True)
    owner_b = PublicationJournal(path)
    owner_a.begin_write()
    with pytest.raises(ValueError, match="attempt marker already exists"):
        owner_b.begin_write()
    recovered = PublicationJournal(path)
    assert recovered.state["publication"]["write_attempted"] is True
    assert recovered.state["publication"]["payload_sha256"] == owner_a.state["publication"]["payload_sha256"]


def test_tampered_frozen_payload_fails_closed_before_any_write(tmp_path):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    path = publication_state_path(tmp_path, run.run_id)
    journal = PublicationJournal(path)
    journal.prepare(run, "https://lab.example", terminal_complete=True)
    body = json.loads(path.read_text())
    body["publication"]["payload"]["name"] = "tampered"
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="payload failed"):
        PublicationJournal(path)
    assert not path.with_name(path.name + ".write-attempted").exists()


def test_uncertain_write_reconciles_read_only_and_never_repeats_put(tmp_path, monkeypatch):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    monkeypatch.setenv("LAB_UPLOAD_TOKEN", "fake-token")
    remote, puts, reads = {}, [], []

    def handle(request):
        if request.method == "PUT":
            puts.append(request)
            remote[run.run_id] = json.loads(request.content)  # server commits, response is lost
            raise httpx.ReadTimeout("response lost after commit")
        reads.append(request.method + request.url.path)
        if request.url.path.endswith("/" + run.run_id):
            return httpx.Response(200, json=remote[run.run_id])
        return httpx.Response(200, json={"runs": [{"run_id": run.run_id}]})

    proof = publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(handle))
    assert proof["retrieval_verified"] and len(puts) == 1
    assert reads == ["GET/api/runs/" + run.run_id, "GET/api/runs"]
    publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(handle))
    assert len(puts) == 1


def test_uncertain_missing_record_stays_blocked_without_put_retry(tmp_path, monkeypatch):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    monkeypatch.setenv("LAB_UPLOAD_TOKEN", "fake-token")
    puts = []

    def handle(request):
        if request.method == "PUT":
            puts.append(request)
            raise httpx.ConnectTimeout("injected ambiguous connect failure")
        if request.url.path.endswith("/" + run.run_id):
            return httpx.Response(404)
        return httpx.Response(200, json={"runs": []})

    with pytest.raises(ValueError, match="not verified"):
        publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(handle))
    with pytest.raises(ValueError, match="not verified"):
        publish_verified(run, "https://lab.example", tmp_path, transport=httpx.MockTransport(handle))
    assert len(puts) == 1
    assert json.loads(publication_state_path(tmp_path, run.run_id).read_text())["publication"]["write_attempted"]


def test_definite_publication_rejection_is_persisted_without_retry(tmp_path, monkeypatch):
    run = prepare_terminal(tmp_path)
    capture_terminal_evidence(run, EndedArena(), FakeAgent(), tmp_path, wait_seconds=1, request_timeout=.2)
    monkeypatch.setenv("LAB_UPLOAD_TOKEN", "fake-token")
    puts = []

    def handle(request):
        if request.method == "PUT":
            puts.append(request)
        return httpx.Response(422, json={"detail": "validation rejected"})

    transport = httpx.MockTransport(handle)
    with pytest.raises(ValueError, match="Lab rejected"):
        publish_verified(run, "https://lab.example", tmp_path, transport=transport)
    with pytest.raises(ValueError, match="not verified"):
        publish_verified(run, "https://lab.example", tmp_path, transport=transport)
    publication = json.loads(publication_state_path(tmp_path, run.run_id).read_text())["publication"]
    assert len(puts) == 1 and publication["write_status"] == "rejected"
