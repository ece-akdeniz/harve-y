"""Hosted adapter conformance using ONLY in-process official Sim and mock inference.

These tests open no hosted sessions, make no inference calls, and publish no Lab records.
"""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from experiments.v2.run_adaptive_milestone import CONFIG
from experiments.v2.run_hosted_sandbox import (
    STAGES,
    SingleSessionArena,
    capture_terminal_evidence,
    dataset_for,
    execute,
    plan,
    publication_state_path,
)
from negotiator.lab.publish import load_snapshots
from negotiator.lab.runner import plan_run, run_experiment
from negotiator.lab.simulator import InProcessSimulatorClient
from negotiator.lab.store import Store
from negotiator.v2.adapters.lab import LocalFixtureTransport
from negotiator.v2.adapters.p10 import recorded_p10, term_binding
from negotiator.v2.core import models as m
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.factory import online_lab_agent

CASES = json.loads((Path(__file__).parents[2] / 'fixtures/v2/hosted-sandbox-cases.json').read_text())['cases']


def test_failed_session_captures_terminal_before_publication(tmp_path, monkeypatch):
    from experiments.v2 import run_hosted_sandbox as hosted

    state = {'session_id': 'owned', 'status': 'ended', 'rounds': 3,
             'threads': {'supplier': {'status': 'ended'}},
             'result': {'deal': False, 'score': 0.0}}
    attempt = SimpleNamespace(session_id='owned', result={}, status='failed', score=None,
                              rounds=None, timeouts=None, replay_url=None, threads={})
    run = SimpleNamespace(run_id='run:test', attempts=[attempt], arena_url='https://arena.example', revision=1,
                          status='failed')
    events = []

    class Client:
        def session(self, session_id):
            assert session_id == 'owned'
            return state

        def thread(self, session_id, supplier):
            return {'messages': [{'from': 'supplier', 'body': 'withdrawn'}], 'timeouts': []}

    class Agent:
        def observe_lab_terminal(self, observed):
            assert observed == state
            events.append('terminal')

        def observe_lab_outcome(self, outcome, threads):
            assert outcome == state['result'] and threads['supplier']['messages']
            events.append('outcome')

        def experiment_evidence(self):
            assert events == ['terminal', 'outcome']
            return {'terminal_json': json.dumps(state)}

    def save(observed_run, root):
        assert observed_run is run
        assert json.loads(attempt.result['agent_evidence']['terminal_json']) == state
        assert run.status == attempt.status == 'failed' and attempt.score is None
        events.append('saved')

    monkeypatch.setattr(hosted, 'save_snapshot', save)
    hosted.capture_terminal_evidence(run, Client(), Agent(), tmp_path, wait_seconds=1, request_timeout=0.5)
    assert events == ['terminal', 'outcome', 'saved']
    assert attempt.result['score'] == 0.0 and not attempt.result['deal']
    assert json.loads((tmp_path / 'terminal-evidence' / 'owned.json').read_text())['status'] == 'complete'
    publication = json.loads(publication_state_path(tmp_path, 'run:test').read_text())
    assert publication['evidence_collection']['status'] == 'complete'


class MockInference(LocalFixtureTransport):
    def __init__(self, stage):
        self.max_calls = STAGES[stage][1]
        self.max_usd = Decimal(STAGES[stage][2])
        self.calls, self.reserved, self.stopped = [], Decimal(0), False

    async def __call__(self, request, budget):
        self.calls.append({'task': request.task, 'mock_only': True})
        if request.task != 'propose':
            return await super().__call__(request, budget)
        source = request.input
        latest = next(sheet for msg in reversed(source.conversation.messages) if msg.speaker == 'supplier'
                      for sheet in msg.observed_sheets if sheet.standing)
        terms = {t.field: t.value for t in latest.complete_bindings}
        terms['unit_price'] = (terms['unit_price'] * Decimal('0.97')).quantize(Decimal('0.01'))
        for option in source.options:
            if terms.get(option.field) not in option.values:
                terms[option.field] = option.values[0]
        citations = [source.citation_catalog[-1][0]] if source.citation_catalog else []
        raw = json.dumps({'bindings': [term_binding(k, terms[k]) for k in source.negotiable_fields],
                          'citation_ids': citations, 'rationale': 'Mock contract test only.'}, default=str)
        return m.ModelSuccess(kind='success', call_id=request.call_id, model_id=request.model_id,
            elapsed_s=Decimal(0), issues=(), raw_response_json=raw,
            response_hash=hashlib.sha256(raw.encode()).hexdigest(), usage=m.ModelUsage())


def agent_for(tmp_path, case):
    stage = case['case_id'].split(':')[1]
    dataset = dataset_for(case)
    path = tmp_path / 'dataset.json'
    path.write_text(json.dumps(dataset))
    allowance = {**plan(stage, dataset, 'https://lab.example'), 'authorized': True, 'token_accounting_confirmed': True}
    agent = online_lab_agent(dataset_path=path, trace_root=tmp_path / 'traces', model_config=CONFIG,
                             transport=MockInference(stage), execution_allowance=allowance)
    return agent


@pytest.mark.parametrize('case', CASES, ids=['D01', 'D02'])
def test_multisupplier_adapter_tracks_complete_original_evidence_before_finishing(tmp_path, case):
    agent = agent_for(tmp_path, case)

    class Simulator(InProcessSimulatorClient):
        def cases(self, set_):
            assert set_ == 'sandbox'
            return [case]

    client = Simulator(case)
    run = plan_run(name='Mock hosted-adapter conformance, local Sim ONLY', author='test', hypothesis='Contract test',
        agent='mock-test-only', config={'model_config_json': json.dumps(asdict(CONFIG))},
        cases=[case['case_id']], repetitions=1,
        max_sessions=1, environment='sandbox', arena_url='http://localhost', provenance={})
    published = []

    class PublisherSpy:
        def submit(self, snapshot):
            # Real publisher copies; retain copies to check completion ordering.
            published.append(type(snapshot).model_validate(snapshot.model_dump()))

        def close(self):
            pass

    final = run_experiment(run, tmp_path / 'runs', client, lambda: agent, publisher=PublisherSpy())
    assert final.status == 'running' and 'agent_evidence' not in final.attempts[0].result
    capture_terminal_evidence(final, client, agent, tmp_path, wait_seconds=1, request_timeout=.5, poll_interval=.001)
    assert final.status == 'completed', final.model_dump()
    result = final.attempts[0].result
    assert result['agent_evidence']['terminal_json']
    assert not result['agent_evidence'].get('evidence_truncated')
    assert all('agent_evidence' in r.attempts[0].result and r.attempts[0].threads
               for r in published if r.attempts[0].status == 'completed')
    assert set(final.attempts[0].threads) == set(case['suppliers'])
    assert all(t.validation.kind == 'valid' for t in agent.traces)
    assert all(c['mock_only'] for c in agent.transport.calls)
    assert all(sid in agent.supplier_memory for sid in case['suppliers'])
    assert all(t.evaluations.items[0].economic[0].basis_verified for t in agent.traces)
    store = Store(tmp_path / 'lab.sqlite3')
    for _, snapshot in load_snapshots(tmp_path / 'runs'):
        store.upsert(snapshot)
    assert store.get(final.run_id)['attempts'][0]['result']['agent_evidence'] == result['agent_evidence']


def test_d02_contract_preserves_executable_alternative_in_each_economic_slice():
    case = CASES[1]
    dataset = dataset_for(case)
    scoped = {**dataset, 'case': {**case, 'suppliers': [case['suppliers'][1]]}, 'supplier_messages': ['Public quote']}
    inputs = recorded_p10(scoped, message='Public quote', now=datetime.now(UTC))
    assert inputs.case.supplier_ids == (case['suppliers'][1],)
    assert inputs.case.buyer.current_price is None
    assert inputs.case.buyer.alternative.kind == 'available'
    assert inputs.case.buyer.alternative.ref.record_id == 'quote:D02-ALT'
    assert {t.field for t in inputs.case.buyer.alternative.terms.bindings} >= {'unit_price', 'volume_per_year'}


def test_rfqs_require_exact_all_thread_round_accounting(tmp_path):
    case = CASES[1]
    agent = agent_for(tmp_path, case)
    agent.observe_lab_session('run:test', 'session:test')
    agent.authoritative_threads = {sid: [{'from': sid, 'body': 'opening'}] for sid in case['suppliers']}
    raw = {'session_id': 'session:test', 'case_id': case['case_id'], 'status': 'open', 'rounds': 1,
           'threads': {sid: {'offer_id': 'offer:test', 'seconds_left': 40, 'status': 'open'}
                       for sid in case['suppliers']}}
    agent.observe_lab_server_state(raw, requested_at=datetime.now(UTC), received_at=datetime.now(UTC))
    with pytest.raises(ContractViolation, match='RFQ rounds'):
        agent.thread_rounds(case['suppliers'][0])


def test_single_session_guard_blocks_reopen_even_after_definite_rejection(tmp_path):
    posts = []

    def handle(request):
        posts.append(request)
        return httpx.Response(422, json={'detail': 'rejected'})

    client = SingleSessionArena(tmp_path / 'journal.jsonl', 'case:D01', base_url='http://localhost',
                                transport=httpx.MockTransport(handle), rate=100)
    from arena_kit.client import ArenaError

    with pytest.raises(ArenaError):
        client.open_session('case:D01')
    with pytest.raises(ValueError, match='one exact'):
        client.open_session('case:D01')
    assert len(posts) == 1
    client.http.close()


def test_hosted_execution_requires_prior_review_before_keys_or_network(tmp_path, monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    review = tmp_path / 'review.json'
    review.write_text(json.dumps({'stage': 'offline', 'transcript_reviewed': False}))
    with pytest.raises(ValueError, match='reviewed first'):
        execute(tmp_path / 'run', tmp_path / 'approval.json', 'D02', dataset_for(CASES[1]),
                'https://lab.example', review)
    assert not (tmp_path / 'run').exists()


def test_failed_development_gate_is_preserved_in_lab_without_opening_simulator(tmp_path, monkeypatch):
    from experiments.v2 import run_adaptive_milestone as offline
    from experiments.v2 import run_hosted_sandbox as hosted

    monkeypatch.setattr(offline, 'load_env', lambda: None)
    monkeypatch.setenv('LLM_API_KEY', 'unused-test-key')
    monkeypatch.setattr(hosted, 'verify_model_access', lambda: None)

    async def rejected(output, allowance):
        (output / 'predictions.json').write_text('[]')
        (output / 'interpretation-report.json').write_text('{"semantic_correct":0}')
        raise ValueError('development usability gate failed')

    monkeypatch.setattr(offline, 'interpretations', rejected)
    monkeypatch.setattr(offline, 'InProcessSimulatorClient', lambda *a: pytest.fail('must not open simulator'))
    approval = tmp_path / 'approval.json'
    approval.write_text(json.dumps({**offline.plan(), 'authorized': True, 'token_accounting_confirmed': True}))
    output = tmp_path / 'run'
    with pytest.raises(ValueError, match='development usability'):
        offline.execute(output, approval)
    snapshots = [run for _, run in load_snapshots(output / 'runs')]
    assert len(snapshots) == 2
    assert all(run.status == 'failed' and run.attempts[0].session_id is None for run in snapshots)
    assert all('development_evidence_json' in run.attempts[0].result for run in snapshots)
    assert approval.with_name(approval.name + '.consumed').exists()



def test_session_creation_does_not_require_a_message_dispatch_certificate(tmp_path):
    posts = []

    def handle(request):
        posts.append(request)
        return httpx.Response(200, json={'session_id': 'owned', 'case': {'case_id': 'case:D01'}})

    client = SingleSessionArena(tmp_path / 'journal.jsonl', 'case:D01', base_url='http://localhost',
                                transport=httpx.MockTransport(handle), rate=100)
    client.pre_http_check = lambda *args: pytest.fail('message certificate applied to session creation')
    try:
        assert client.open_session('case:D01')['session_id'] == 'owned'
        assert client.journal.session_for('case:D01') == 'owned'
        assert len(posts) == 1
        assert not client.journal.pending()
    finally:
        client.http.close()
