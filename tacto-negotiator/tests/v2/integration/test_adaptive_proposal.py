"""Adversarial proposal admission and real tracked simulator terminal retrieval."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from experiments.v2.run_lab_local import DATASET, run_local
from negotiator.lab.publish import load_snapshots
from negotiator.lab.store import Store
from negotiator.lab.transport import JournaledArena, RecoveryRequired
from negotiator.v2.adapters.lab import LocalFixtureTransport
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core import models as m
from negotiator.v2.factory import bounded_services, run_recorded_decision
from negotiator.v2.orchestration.offline import OfflineDecisionTrace


class Clock:
    def utcnow(self):
        return datetime.now(UTC)

    def monotonic(self):
        import time

        return time.monotonic()


@pytest.mark.parametrize(
    "mutation",
    [None, "foreign_citation", "must_have", "fixed_field", "invalid_price", "garbage"],
)
def test_model_generates_new_terms_or_uses_certified_fixed_fallback(mutation):
    data = json.loads(DATASET.read_text())
    clock = Clock()
    inputs = recorded_p10(data, message=data["supplier_messages"][0], now=clock.utcnow())
    config = type(
        "Config",
        (),
        {
            "provider_id": "local-fixture",
            "protocol_id": "chat-completions-json-v1",
            "model_id": "explicit-scripted-fixture",
        },
    )()

    class Transport(LocalFixtureTransport):
        async def __call__(self, request, budget):
            if request.task != "propose":
                return await super().__call__(request, budget)
            terms = {**data["candidate_terms"][0], "unit_price": 30.01}
            if mutation == "must_have":
                terms["volume_per_year"] = 16379
            if mutation == "fixed_field":
                terms["payment_days"] = 30
            if mutation == "invalid_price":
                terms["unit_price"] = 30.001
            from negotiator.v2.adapters.p10 import term_binding

            bindings = [term_binding(k, v) for k, v in terms.items()]
            raw = (
                json.dumps(
                    {
                        "bindings": bindings,
                        "citation_ids": ["citation:forged"] if mutation == "foreign_citation" else [],
                        "rationale": "Test new legal proposal.",
                    }
                )
                if mutation != "garbage"
                else "not JSON"
            )
            return m.ModelSuccess(
                kind="success",
                call_id=request.call_id,
                model_id=request.model_id,
                elapsed_s=Decimal("0"),
                issues=(),
                raw_response_json=raw,
                response_hash=hashlib.sha256(raw.encode()).hexdigest(),
                usage=m.ModelUsage(),
            )

    assembler, coordinator = bounded_services(inputs, clock, Transport(), config, prompt_revision="v3", arm="adaptive")
    trace = asyncio.run(run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator))
    trace.verify()
    assert trace.validation.kind == "valid"
    call = next(c for c in trace.model_calls if c.request.task == "propose")
    if mutation is None:
        assert call.consumer_admitted is True
        assert trace.rendered.payload.packages[0].fingerprint not in {p.fingerprint for p in inputs.packages}
    else:
        assert call.fallback_used and call.permitted_raw_response is None
        assert trace.rendered.kind == "question" and not trace.rendered.payload.packages
        assert all(candidate.candidate_builder_id != "bounded-proposal-v3"
                   for generation in trace.generations for candidate in generation.candidates)
        assert any(i.component == "strategy.proposal" for i in trace.issues)
    projection = call.request.input.model_dump_json()
    assert "fallback_unit_price" not in projection and "relationship_eur_per_point" not in projection


def test_adaptive_control_closes_and_is_visible_through_normal_lab_store(tmp_path):
    report = run_local(tmp_path, arms=("minimum", "adaptive"))
    baseline, adaptive = report["runs"]
    assert baseline["status"] == adaptive["status"] == "completed"
    assert adaptive["deal"] is True and adaptive["rounds"] >= 2
    paths = sorted((tmp_path / "traces" / adaptive["run_id"]).glob("*/decision-*.json"))
    traces = [OfflineDecisionTrace.model_validate_json(p.read_bytes()) for p in paths]
    assert len({t.rendered.payload.packages[0].fingerprint for t in traces}) >= 2
    for trace in traces:
        trace.verify()
        assert trace.validation.kind == "valid"
    first = traces[0]
    proposal_call = next(call for call in first.model_calls if call.request.task == "propose")
    assert proposal_call.consumer_admitted and not proposal_call.fallback_used
    assert proposal_call.request.input.commercial_reference.kind == "observed_supplier_offer"
    from negotiator.v2.adapters.chat_completions import ChatCompletionConfig, messages_for, response_format

    chat_config = ChatCompletionConfig(base_url="http://localhost/v1", provider_id="local-fixture",
        model_id="explicit-scripted-fixture", structured_output=True)
    assert "code derives term directions" in messages_for(proposal_call.request, chat_config)[0]["content"]
    schema = response_format(proposal_call.request, chat_config)["json_schema"]["schema"]["properties"]
    assert "buyer_requests" not in schema
    selected = next(item for generation in first.generations for item in generation.candidates
                    if item.candidate_id == first.decision.candidate_id)
    assert selected.candidate_builder_id == "bounded-proposal-v3"
    assert selected.contents.packages[0].fingerprint == first.rendered.payload.packages[0].fingerprint
    evaluation = next(
        item for item in first.evaluations.items if item.candidate.candidate_id == first.decision.candidate_id
    )
    assert evaluation.disposition == "approved" and evaluation.economic[0].nominal_cost is not None
    assert first.validation.action.rendered == first.rendered
    assert first.validated_message_bytes is not None
    later = next(trace for trace in traces[1:] if trace.snapshot_bytes)
    next_snapshot = m.DecisionSnapshot.model_validate_json(later.snapshot_bytes)
    messages = next_snapshot.conversation.messages
    buyer_index = next(i for i, msg in enumerate(messages) if msg.speaker == "buyer")
    selected_terms = {binding.field: binding.value for binding in selected.contents.packages[0].bindings}
    buyer_terms = next(sheet.bindings for sheet in messages[buyer_index].observed_sheets)
    observed_terms = {binding.field: binding.value for binding in buyer_terms if binding.field in selected_terms}
    assert observed_terms == selected_terms
    assert any(msg.speaker == "supplier" for msg in messages[buyer_index + 1:])
    assert later.assessment.model_call_id is None
    assert later.assessment.interpreter_id == "deterministic-evidence-copy-v1"
    assert all(call.request.task == "propose" for call in later.model_calls)
    from negotiator.v2.orchestration.metrics import decision_metrics

    assert decision_metrics(later)["interpretation_admitted"] is False
    response_bodies = {msg.body for msg in messages[buyer_index + 1:] if msg.speaker == "supplier"}
    proposal_call = next(call for call in later.model_calls if call.request.task == "propose")
    assert response_bodies & {msg.body for msg in proposal_call.request.input.conversation.messages
                             if msg.speaker == "supplier"}
    assert all("not interpreted" in unknown for unknown in later.assessment.unknowns)
    assert all(
        msg.speaker in {"buyer", "supplier", "arena"}
        for msg in m.DecisionSnapshot.model_validate_json(traces[-1].snapshot_bytes).conversation.messages
    )
    terminal = json.loads(
        next((tmp_path / "traces" / adaptive["run_id"]).glob("*/terminal-observation.json")).read_text()
    )
    assert terminal["terminal"]["deal"] is True and terminal["terminal"]["offer_id"]
    store = Store(tmp_path / "lab.sqlite3")
    for _, run in load_snapshots(tmp_path / "runs"):
        store.upsert(run)
    assert len(store.listing()["runs"]) == 2
    assert store.get(adaptive["run_id"])["attempts"][0]["result"]["deal"] is True
    assert store.comparison(baseline["run_id"], adaptive["run_id"]) is not None


def test_uncertain_submission_survives_restart_and_reconciles_without_retry(tmp_path):
    messages = [{"from": "supplier", "body": "standing"}]
    posts = []
    payload = {"body": "validated", "term_sheets": []}

    def handle(request):
        if request.method == "POST":
            posts.append(request)
            messages.append({**payload, "from": "buyer"})
            messages.append({"from": "supplier", "body": "reply"})
            raise httpx.ReadTimeout("uncertain", request=request)
        if str(request.url).endswith("/threads/supplier:test"):
            return httpx.Response(200, json={"messages": messages})
        return httpx.Response(200, json={"status": "open"})

    journal = tmp_path / "requests.jsonl"
    client = JournaledArena(journal, base_url="http://localhost", rate=100)
    client.http.close()
    client.http = httpx.Client(base_url="http://localhost/v1", transport=httpx.MockTransport(handle))
    with pytest.raises(RecoveryRequired):
        client.send_message("session:test", "supplier:test", payload)
    pending = client.journal.pending()[0]
    assert posts[0].headers["X-Move-Id"] == pending["move_id"]
    assert posts[0].content.decode() == pending["payload_utf8"]
    client.http.close()
    restarted = JournaledArena(journal, base_url="http://localhost", rate=100)
    restarted.http.close()
    restarted.http = httpx.Client(base_url="http://localhost/v1", transport=httpx.MockTransport(handle))
    with pytest.raises(RecoveryRequired):
        restarted.send_message("session:test", "supplier:test", payload)
    assert len(posts) == 1
    assert restarted.reconcile_pending()[0]["status"] == "acknowledged"
    assert not restarted.journal.pending() and len(posts) == 1
    restarted.http.close()


def test_final_dispatch_check_runs_after_pacing_and_before_journaled_post(tmp_path):
    events, posts = [], []
    messages = [{"from": "supplier", "body": "latest"}]

    def handle(request):
        if request.method == "POST":
            events.append("post")
            posts.append(request)
            return httpx.Response(200, json={"status": "ok"})
        events.append("history")
        return httpx.Response(200, json={"messages": messages})

    client = JournaledArena(tmp_path / "dispatch.jsonl", base_url="http://localhost", rate=100)
    client.http.close()
    client.http = httpx.Client(base_url="http://localhost/v1", transport=httpx.MockTransport(handle))
    client._pace = lambda: events.append("pace")

    def check(supplier, message, thread):
        events.append("check")
        assert supplier == "supplier:test" and thread["messages"] == messages
        assert message["body"] == "approved"

    client.pre_post_check = check
    payload = {"body": "approved", "term_sheets": []}
    client.send_message("session:test", "supplier:test", payload)
    # The owned GET has its own limiter admission; the permit check follows its
    # response and the POST follows without another await/pacing interval.
    assert events == ["pace", "pace", "history", "check", "post"]
    intent = client.journal.records[0]
    assert posts[0].content.decode() == intent["payload_utf8"]
    assert posts[0].headers["X-Move-Id"] == intent["move_id"]
    client.http.close()


def test_final_dispatch_rejection_creates_no_post_or_operation_intent(tmp_path):
    posts = []

    def handle(request):
        if request.method == "POST":
            posts.append(request)
            return httpx.Response(200, json={"status": "unexpected"})
        return httpx.Response(200, json={"messages": [{"from": "supplier", "body": "changed"}]})

    client = JournaledArena(tmp_path / "stale.jsonl", base_url="http://localhost", rate=100)
    client.http.close()
    client.http = httpx.Client(base_url="http://localhost/v1", transport=httpx.MockTransport(handle))
    client._pace = lambda: None
    client.pre_post_check = lambda *_: (_ for _ in ()).throw(RuntimeError("stale permit"))
    with pytest.raises(RuntimeError, match="stale permit"):
        client.send_message("session:test", "supplier:test", {"body": "approved"})
    assert not posts and not client.journal.pending()
    client.http.close()


def test_permit_expiry_after_journal_is_proven_not_dispatched(tmp_path):
    posts, events = [], []

    def handle(request):
        if request.method == 'POST':
            posts.append(request)
            return httpx.Response(200, json={'status': 'unexpected'})
        return httpx.Response(200, json={'messages': [{'from': 'supplier', 'body': 'latest'}]})

    client = JournaledArena(tmp_path / 'expired-after-intent.jsonl', base_url='http://localhost', rate=100)
    client.http.close()
    client.http = httpx.Client(base_url='http://localhost/v1', transport=httpx.MockTransport(handle))
    client._pace = lambda: None
    original_intent = client.journal.intent

    def intent(*args, **kwargs):
        row = original_intent(*args, **kwargs)
        events.append('intent')
        return row

    client.journal.intent = intent

    def expired(*args):
        events.append('expired-check')
        raise RuntimeError('deadline expired after journal fsync')

    client.pre_http_check = expired
    with pytest.raises(RuntimeError, match='deadline expired'):
        client.send_message('session:test', 'supplier:test', {'body': 'approved'})
    assert events == ['intent', 'expired-check'] and not posts
    assert not client.journal.pending()
    assert client.journal.records[-1]['reason'] == 'proven_not_dispatched'
    assert client.journal.records[-1]['dispatched'] is False
    client.http.close()


def test_hosted_allowance_rejects_source_or_budget_changes_before_credentials(tmp_path, monkeypatch):
    from experiments.v2.run_adaptive_milestone import execute, plan

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    approved = {**plan(), "authorized": True, "token_accounting_confirmed": True}
    approved["max_calls"] += 1
    authorization = tmp_path / "approval.json"
    authorization.write_text(json.dumps(approved))
    with pytest.raises(ValueError, match="exactly match"):
        execute(tmp_path / "run", authorization)
    assert not (tmp_path / "run").exists()
    assert not authorization.with_name(authorization.name + ".consumed").exists()


def test_online_factory_requires_exact_allowance_and_verified_live_clocks(tmp_path):
    from experiments.v2.run_adaptive_milestone import CONFIG
    from negotiator.v2.core.errors import ContractViolation
    from negotiator.v2.core.serialization import semantic_hash
    from negotiator.v2.factory import online_lab_agent

    dataset = json.loads(DATASET.read_text())

    class FakeGuard:
        max_calls, max_usd = 18, Decimal("1.00")

    kwargs = dict(dataset_path=DATASET, trace_root=tmp_path, transport=FakeGuard(), model_config=CONFIG)
    with pytest.raises(ContractViolation, match="approval"):
        online_lab_agent(**kwargs, execution_allowance={})
    allowance = dict(
        authorized=True,
        environment="practice",
        online_sessions=1,
        retries=0,
        max_calls=18,
        max_total_reserved_tokens=1769472,
        max_usd="1.00",
        offline_verification=True,
        remote_lab_verified=True,
        case_hash=semantic_hash(dataset["case"]),
        model_id=CONFIG.model_id,
    )
    agent = online_lab_agent(**kwargs, execution_allowance=allowance)
    agent.validate_lab_case(dataset["case"])
    altered = {**dataset["case"], "round_limit": 11}
    with pytest.raises(ContractViolation, match="reviewed"):
        agent.validate_lab_case(altered)
    agent.observe_lab_session("run:readiness-test", "session:offline-p10")
    clock = Clock()
    inputs = recorded_p10(dataset, message=dataset["supplier_messages"][0], now=clock.utcnow())
    raw = {
        "session_id": "session:offline-p10",
        "case_id": "case:P10",
        "status": "open",
        "rounds": 0,
        "threads": {dataset["case"]["suppliers"][0]: {"offer_id": None, "seconds_left": 40}},
    }
    agent.observe_lab_server_state(raw, requested_at=clock.utcnow(), received_at=clock.utcnow())
    normalized = agent.normalize_live_inputs(inputs, dataset["case"]["suppliers"][0])
    assert normalized.server.threads[0].rounds.confidence == "authoritative"
    assert normalized.server.threads[0].clock.confidence == "conservative"
    raw["rounds"] = None
    with pytest.raises(ContractViolation, match="rounds/clock"):
        agent.normalize_live_inputs(inputs, dataset["case"]["suppliers"][0])
