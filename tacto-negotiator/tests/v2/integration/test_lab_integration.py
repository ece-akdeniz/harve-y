"""Cross the actual tracked Lab/agent/V2 boundary with official local Sim outcomes."""

import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from experiments.v2.evaluate_interpretation import evaluate
from experiments.v2.evaluate_stabilization import FIXTURE, run_controls
from experiments.v2.run_lab_local import DATASET, run_local
from negotiator.lab.publish import load_snapshots
from negotiator.lab.runner import agent_factory, plan_run, run_experiment
from negotiator.lab.simulator import InProcessSimulatorClient
from negotiator.v2.factory import local_lab_agent
from negotiator.v2.orchestration.offline import OfflineDecisionTrace


def test_tracked_lab_drives_v2_multiple_rounds_and_retrieves_real_outcome(tmp_path):
    report = run_local(tmp_path)
    assert report['hosted_calls'] == report['remote_writes'] == 0
    assert len(report['runs']) == 3
    snapshots = {r.run_id: r for _, r in load_snapshots(tmp_path / 'runs')}
    for row in report['runs']:
        assert row['status'] == 'completed' and row['error'] is None
        assert 1 <= row['rounds'] == row['traces_verified'] <= 6
        assert row['deal'] is False and row['score'] == 0
        assert row['buyer_cost'] is None  # No agreement cost invented from validated offer costs.
        run = snapshots[row['run_id']]
        assert run.environment == 'simulator' and run.attempts[0].timeouts == 0
        paths = sorted((tmp_path / 'traces' / row['run_id']).glob('*/decision-*.json'))
        previous = None
        for round_index, path in enumerate(paths):
            trace = OfflineDecisionTrace.model_validate_json(path.read_bytes())
            trace.verify()
            assert trace.snapshot.session_id == row['session_id']
            assert trace.snapshot.run_id == row['run_id']
            assert trace.snapshot.state_version == round_index
            assert trace.assessment.parent_assessment_id == previous
            previous = trace.assessment.assessment_id
            assert trace.validation.kind == 'valid' and trace.validated_message_bytes
            assert len(trace.model_calls) == {'minimum': 0, 'direct': 1, 'grounded': 2}[row['arm']]
            assert all(c.consumer_admitted is True and c.result_kind == 'success' for c in trace.model_calls)
            assert not any(c.fallback_used for c in trace.model_calls)
            assert all(s.status == 'completed' for s in trace.stages)
            assert path.stat().st_mode & 0o777 == 0o600
        assert all(d['cost_delta'] == '0.0' for d in row['metrics']['decisions'])


def test_lab_agent_registration_and_remote_preflight_fail_closed(tmp_path):
    config = {'dataset_path': str(DATASET), 'trace_root': str(tmp_path / 'traces'), 'arm': 'grounded'}
    factory = agent_factory('negotiator.v2.factory:local_lab_agent', config)
    assert factory().local_only
    case = json.loads(DATASET.read_text())['case']
    class NoNetworkClient:
        def __getattr__(self, name):
            raise AssertionError('client must not be touched for a remote V2 Lab attempt')
    run = plan_run(name='preflight', author='local-verification', hypothesis='deny remote V2 execution',
                   agent='negotiator.v2.factory:local_lab_agent', config=config, cases=[case['case_id']],
                   repetitions=1, max_sessions=1, environment='sandbox', arena_url='https://arena.example',
                   provenance={})
    # quota_snapshot conservatively catches unavailable reads; no session/client call succeeds.
    final = run_experiment(run, tmp_path / 'runs', NoNetworkClient(),
                           agent_factory(run.agent, config))
    assert final.status == 'failed' and final.attempts[0].session_id is None
    assert not list((tmp_path / 'traces').glob('**/*.json'))


def test_unvalidated_decision_never_reaches_simulator(tmp_path):
    from negotiator.v2.core.errors import ContractViolation
    agent = local_lab_agent(dataset_path=str(DATASET), trace_root=str(tmp_path), arm='grounded')
    client = InProcessSimulatorClient(json.loads(DATASET.read_text())['case'])
    opened = client.open_session('case:P10')
    agent.observe_lab_session('run:invalid-test', opened['session_id'])
    for events in opened['threads'].values():
        for event in events:
            for attachment in event.get('attachments', []):
                agent.observe_lab_attachment(attachment['attachment_id'],
                    client.attachment(opened['session_id'], attachment['attachment_id']))
    from negotiator.v2.core import models as m
    from negotiator.v2.factory import bounded_services
    class RejectValidator:
        def validate_action(self, action, context, state, budget):
            return m.InvalidActionResult(kind='invalid', report=m.ValidationReport(
                check_version='test-reject', snapshot=context.snapshot, checks=(),
                issues=(m.Issue(code='infeasible', severity='error', component='test', refs=(),
                                detail='injected independent rejection'),)))
    def rejecting_services(*args, **kwargs):
        assembler, coordinator = bounded_services(*args, **kwargs)
        coordinator.validator = RejectValidator()
        return assembler, coordinator
    agent.runtime_builder = rejecting_services
    with pytest.raises(ContractViolation, match='independent validation'):
        agent.decide(opened['case'], opened['threads'])
    assert client.session(opened['session_id'])['rounds'] == 0


def test_advisory_timeout_uses_certified_fallback_and_submits_once(tmp_path):
    class SlowTransport:
        stopped = False

        def __init__(self):
            self.calls = []

        def stop_model_calls(self, reason):
            self.stopped = True

        async def __call__(self, request, budget):
            self.calls.append(request.task)
            await asyncio.Event().wait()

    dataset = json.loads(DATASET.read_text())
    transport = SlowTransport()
    agent = local_lab_agent(
        dataset_path=str(DATASET), trace_root=str(tmp_path / 'traces'), arm='adaptive', transport=transport,
        model_config=SimpleNamespace(provider_id='fake', protocol_id='injected-v1', model_id='fake-model'),
        closing_authority=True,
    )
    agent.normalize_live_inputs = lambda inputs, supplier: inputs.model_copy(update={
        'budget': inputs.budget.model_copy(update={'model_time_limit_s': Decimal('0.03')})
    })
    client = InProcessSimulatorClient(dataset['case'])
    opened = client.open_session(dataset['case']['case_id'])
    agent.observe_lab_session('run:timeout-fallback', opened['session_id'])
    for supplier, events in opened['threads'].items():
        agent.observe_lab_acknowledgement(supplier, client.thread(opened['session_id'], supplier))
        for event in events:
            for attachment in event.get('attachments', []):
                agent.observe_lab_attachment(attachment['attachment_id'],
                    client.attachment(opened['session_id'], attachment['attachment_id']))

    message = agent.decide(opened['case'], opened['threads'])
    trace = agent.traces[-1]
    assert transport.calls == ['propose'] and transport.stopped
    assert trace.assessment.status == 'ok'
    assert trace.assessment.interpreter_id == 'deterministic-evidence-copy-v1'
    assert trace.validation.kind == 'valid'
    reserved = [call for call in trace.model_calls if call.charged_tokens]
    denied = [call for call in trace.model_calls if not call.charged_tokens]
    assert len(reserved) == 1 and reserved[0].result_kind == 'timeout'
    assert all(call.result_kind == 'capacity_unavailable' for call in denied)
    evidence = agent.experiment_evidence()['decisions'][0]
    assert evidence['action_origin'] == 'fallback' and evidence['fallback_action'] is True
    assert evidence['fallback_reasons'][0]['task'] == 'propose'
    assert trace.model_calls[0].charged_tokens == trace.model_token_limit // 2
    supplier = dataset['case']['suppliers'][0]
    client.send_message(opened['session_id'], supplier, message['message'])
    assert client.session(opened['session_id'])['rounds'] == 1
    assert len(client.thread(opened['session_id'], supplier)['messages']) > len(opened['threads'][supplier])


def test_semantic_evaluation_is_separate_from_admission():
    report, predictions = asyncio.run(run_controls())
    assert report['structural_admission_rate'] == 1 and report['semantic_correct'] == 14
    assert report['critical_review_missing'] == 14
    fixture = json.loads(FIXTURE.read_text())
    labels = {**fixture, 'examples': [e['label'] for e in fixture['examples']]}
    changed = json.loads(json.dumps(predictions))
    # A grounded ambiguity without a preference hypothesis is still admitted structurally.
    changed[0]['assessment']['hypotheses'] = []
    result = evaluate(labels, changed)
    assert result['structural_admission_rate'] == 1
    assert result['semantic_correct'] == 13 and result['accuracy'] < 1



def test_fresh_attachment_history_matches_dispatch_hydration(tmp_path):
    from copy import deepcopy

    from negotiator.v2.core.errors import ContractViolation

    agent = local_lab_agent(dataset_path=DATASET, trace_root=tmp_path, arm='minimum')
    supplier = agent.dataset['case']['suppliers'][0]
    event = {'from': 'supplier', 'body': 'Standing offer.',
             'attachments': [{'attachment_id': 'att:quote', 'name': 'quote.txt'}]}
    agent.observe_lab_attachment('att:quote', b'Owned quote defaults')
    current = {'messages': [deepcopy(event)]}
    agent.observe_lab_acknowledgement(supplier, {'messages': [deepcopy(event)]})
    message = {'action': {'type': 'walk_away'}}
    agent.pending_message = {'supplier_id': supplier, 'message': message}
    agent.closing_enabled = True
    agent.closing = SimpleNamespace(validate=lambda *args, **kwargs: None)
    agent.closing_threads = lambda *args: {}
    agent.validate_lab_dispatch(supplier, message, current)
    assert agent.authoritative_threads[supplier][0]['attachments'][0]['text'] == 'Owned quote defaults'
    tampered = deepcopy(current)
    tampered['messages'][0]['body'] = 'Changed supplier offer.'
    with pytest.raises(ContractViolation, match='history changed'):
        agent.validate_lab_dispatch(supplier, message, tampered)
