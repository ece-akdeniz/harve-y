import copy

import pytest
from test_lab_loop_store import checkpoint
from test_lab_memory import ARENA, add_run, build, rehash
from test_lab_policy import sample

from negotiator.lab.loop_store import LoopStore
from negotiator.lab.policy import evaluate_campaign


@pytest.fixture
def comparison(tmp_path):
    path = tmp_path / 'memory.sqlite'
    for name, case in [('A', 'case:one'), ('B', 'case:one'), ('C', 'case:two')]:
        add_run(path, name, supplier='sup:' + name, case=case)
    memory = build(path)
    suite, _, attempts = sample()
    suite['arena_url'] = ARENA
    baseline, candidate = checkpoint('baseline'), checkpoint('candidate')
    baseline['source_tree'] = candidate['source_tree'] = 'c' * 40
    candidate['commit'] = 'd' * 40
    candidate['config']['memory'] = memory
    for attempt in attempts:
        suppliers = ['sup:X', 'sup:Y'] if attempt['case_id'] == 'case:D01' else ['sup:Z']
        threads = {s: {'supplier_id': s, 'messages': [{'from': 'sales@' + s.split(':')[1], 'body': 'Quote.'}]}
                   for s in suppliers}
        attempt.update(session_id='session:' + attempt['attempt_id'], threads=threads)
        attempt['result'].update(threads={s: {'closed': True} for s in suppliers}, supplier_id=suppliers[0])
        original(attempt)
    return suite, baseline, candidate, attempts, path


def original(attempt):
    attempt['outcome'] = copy.deepcopy({k: v for k, v in attempt.items() if k not in
                                      {'arm', 'case_id', 'repeat', 'outcome', 'start', 'reconciliation'}})


def evaluate(comparison):
    return evaluate_campaign(*comparison[:4])


def test_disjoint_three_supplier_two_case_original_outcomes_pass(comparison):
    result = evaluate(comparison)
    assert result['eligible']
    assert {'memory_holdout', 'memory_comparability'} <= {g['id'] for g in result['gates']}


@pytest.mark.parametrize('change', [
    'source_supplier', 'hidden_supplier', 'source_case', 'source_session', 'missing_threads',
    'missing_thread', 'missing_original', 'recovered', 'unknown_author', 'wrong_thread_identity',
    'cohort_mismatch', 'too_few_suppliers', 'wrong_arena', 'wrong_environment', 'duplicate_session',
])
def test_memory_holdout_rejects_contamination_despite_numeric_gain(comparison, change):
    suite, baseline, candidate, attempts, _ = comparison
    a = attempts[1]
    if change in ('source_supplier', 'hidden_supplier'):
        supplier = 'sup:A'
        a['threads'][supplier] = {'messages': [{'from': 'sales@A', 'body': 'Hello.'}]}
        a['result']['threads'][supplier] = {'closed': True}
        if change == 'source_supplier':
            a['result']['supplier_id'] = supplier
    elif change == 'source_case':
        candidate['config']['memory'] = rehash({**candidate['config']['memory'], 'source_cases':
                                               sorted(['case:one', 'case:two', 'case:D01'])})
    elif change == 'source_session':
        a['session_id'] = 'session:A'
    elif change == 'missing_threads':
        a['threads'] = {}
    elif change == 'missing_thread':
        a['threads'].pop('sup:Y')
    elif change == 'missing_original':
        a.pop('outcome')
    elif change == 'recovered':
        a['outcome']['status'] = 'recovered'
    elif change == 'unknown_author':
        a['threads']['sup:X']['messages'][0]['from'] = 'supplier'
    elif change == 'wrong_thread_identity':
        a['threads']['sup:X']['supplier_id'] = 'sup:A'
    elif change == 'cohort_mismatch':
        a['threads']['sup:Q'] = a['threads'].pop('sup:Y')
        a['threads']['sup:Q'] = {'messages': [{'from': 'sales@Q'}]}
        a['result']['threads']['sup:Q'] = a['result']['threads'].pop('sup:Y')
    elif change == 'too_few_suppliers':
        for row in attempts:
            row['threads'] = {'sup:X': {'messages': [{'from': 'sales@X'}]}}
            row['result']['threads'] = {'sup:X': {'closed': True}}
            row['result']['supplier_id'] = 'sup:X'
            original(row)
    elif change == 'wrong_arena':
        suite['arena_url'] = 'https://elsewhere.test'
    elif change == 'wrong_environment':
        suite['environment'] = 'practice'
    elif change == 'duplicate_session':
        a['session_id'] = attempts[0]['session_id']
    if change not in {'missing_original', 'recovered'}:
        original(a)
    result = evaluate(comparison)
    assert not result['eligible']
    assert 'memory_holdout' in result['evidence_gaps']
    assert next(g for g in result['gates'] if g['id'] == 'gain')['passed']


@pytest.mark.parametrize('field,value', [
    ('source_tree', 'f' * 40), ('lock_sha256', 'f' * 64), ('runner', 'async'),
    ('data', {'different': {}}), ('project_path', 'another-project'), ('submodules', {'kit': 'e' * 40}),
    ('harness_version', 'lab-v2'), ('config', {'anchor': 0.8}),
])
def test_memory_changes_require_identical_code_and_nonmemory_inputs(comparison, field, value):
    candidate = comparison[2]
    candidate[field] = {**candidate[field], **value} if field == 'config' else value
    result = evaluate(comparison)
    assert not result['eligible']
    assert 'memory_comparability' in result['evidence_gaps']


def test_legacy_commit_identity_and_both_discovery_cohorts(comparison):
    baseline, candidate, attempts = comparison[1:4]
    baseline.pop('source_tree')
    candidate.pop('source_tree')
    assert 'memory_comparability' in evaluate(comparison)['evidence_gaps']
    candidate['commit'] = baseline['commit']
    assert evaluate(comparison)['eligible']
    baseline['config']['memory'] = rehash({**candidate['config']['memory'],
                                        'source_suppliers': ['sup:A', 'sup:B', 'sup:C', 'sup:X']})
    assert 'memory_holdout' in evaluate(comparison)['evidence_gaps']
    candidate['config'].pop('memory')
    assert 'memory_holdout' in evaluate(comparison)['evidence_gaps']


def test_unchanged_or_empty_memory_preserves_legacy_evaluation(comparison):
    baseline, candidate = comparison[1:3]
    baseline['config']['memory'] = copy.deepcopy(candidate['config']['memory'])
    for attempt in comparison[3]:
        attempt['threads'] = {}
    assert evaluate(comparison)['eligible']
    baseline['config'].pop('memory')
    candidate['config']['memory'] = rehash({**candidate['config']['memory'], 'lessons': []})
    assert evaluate(comparison)['eligible']


def test_loop_memory_operations_registration_and_seed_protection(comparison, tmp_path):
    suite, _, candidate, _, path = comparison
    loop = LoopStore(path)
    built = loop.write('memory-snapshot', dict(arena_url=ARENA, environment='sandbox',
                                             source_cases=['case:one', 'case:two']))
    assert built == candidate['config']['memory']
    assert loop.read('memory-snapshots', built['snapshot_id']) == built
    assert loop.read('memory-snapshots')['memory-snapshots'] == [built]
    assert loop.read('memory')['lessons']
    with pytest.raises(ValueError):
        loop.write('memory-snapshot', dict(arena_url=ARENA, environment='sandbox',
                                          source_cases=['case:one'], lessons=[]))
    with pytest.raises(ValueError, match='snapshot'):
        LoopStore(tmp_path / 'unregistered.sqlite').write('checkpoint', candidate)
    loop.write('checkpoint', candidate)
    loop.write('suite', suite)
    with pytest.raises(ValueError, match='memory'):
        loop.write('seed', dict(suite_id=suite['suite_id'], checkpoint_id='candidate', author='tester'))
    with pytest.raises(ValueError, match='never recommended'):
        loop.write('restore', dict(suite_id=suite['suite_id'], checkpoint_id='candidate', author='tester',
                                   request_id='restore', generation=1))


def test_memory_promotion_is_atomic_and_historical_restore_preserves_memory(comparison):
    suite, baseline, candidate, attempts, path = comparison
    loop = LoopStore(path)
    for cp in (baseline, candidate):
        loop.write('checkpoint', cp)
    loop.write('suite', suite)
    loop.write('family', dict(family_id='holdout', max_sessions=12))
    loop.write('seed', dict(suite_id=suite['suite_id'], checkpoint_id='baseline', author='tester'))
    campaign = loop.write('campaign', dict(campaign_id='holdout', family_id='holdout', suite_id=suite['suite_id'],
                                          baseline_id='baseline', candidate_id='candidate', generation=1,
                                          seed=1, author='tester', hypothesis='Unseen supplier transfer'))
    by_cell = {(a['arm'], a['case_id'], a['repeat']): a for a in attempts}
    for attempt in campaign['attempts']:
        expected = by_cell[attempt['arm'], attempt['case_id'], attempt['repeat']]
        loop.write('attempt-start', dict(attempt_id=attempt['attempt_id'], worker_id='test', key_id='local'))
        outcome = copy.deepcopy(expected['outcome'])
        outcome.update(attempt_id=attempt['attempt_id'], checkpoint_id=attempt['checkpoint_id'])
        loop.write('attempt-result', outcome)
    completion = loop.write('complete', dict(campaign_id='holdout'))
    assert completion['status'] == 'promoted'
    assert loop.write('complete', dict(campaign_id='holdout')) == completion
    assert loop.read('recommended', suite['suite_id'])['checkpoint_id'] == 'candidate'
    rollback = loop.write('restore', dict(suite_id=suite['suite_id'], checkpoint_id='baseline', generation=2,
                                         request_id='rollback', author='tester'))
    assert rollback['checkpoint_id'] == 'baseline'
    restored = loop.write('restore', dict(suite_id=suite['suite_id'], checkpoint_id='candidate', generation=3,
                                         request_id='restore-tested-memory', author='tester'))
    assert loop.read('checkpoints', restored['checkpoint_id'])['config']['memory'] == candidate['config']['memory']


@pytest.mark.parametrize('change', ['one_case', 'missing_roster', 'missing_attempt', 'duplicate_attempt',
                                  'wrong_case_identity', 'wrong_session_identity', 'top_level_substitution'])
def test_memory_holdout_requires_complete_identified_original_transcripts(comparison, change):
    suite, _, _, attempts, _ = comparison
    if change == 'one_case':
        suite['cases'] = ['case:D01']
        attempts[:] = [a for a in attempts if a['case_id'] == 'case:D01']
    elif change == 'missing_attempt':
        attempts.pop()
    elif change == 'duplicate_attempt':
        attempts.append(copy.deepcopy(attempts[0]))
    elif change == 'missing_roster':
        attempts[0]['result'].pop('threads')
        original(attempts[0])
    elif change == 'wrong_case_identity':
        attempts[0]['result']['case_id'] = 'case:one'
        original(attempts[0])
    elif change == 'wrong_session_identity':
        attempts[0]['result']['session_id'] = 'session:A'
        original(attempts[0])
    else:
        attempts[0]['threads'] = {'sup:A': {'messages': [{'from': 'sales@A'}]}}
    assert 'memory_holdout' in evaluate(comparison)['evidence_gaps']


@pytest.mark.parametrize('runner', ['serial', 'async'])
def test_owned_session_envelope_survives_worker_and_establishes_holdout_cohort(
    comparison, tmp_path, monkeypatch, runner
):
    import os

    import httpx
    from test_memory_policy import negotiation, worker_request

    import negotiator.play
    import negotiator.runner
    from negotiator.lab import transport, worker
    from negotiator.lab.loop_models import Outcome

    suite, baseline, candidate, attempts, _ = comparison
    suite['runner'] = baseline['runner'] = candidate['runner'] = runner
    expected = attempts[1]
    session = expected['session_id']
    case, _ = negotiation()
    case['case_id'], case['suppliers'] = expected['case_id'], list(expected['threads'])
    ended = {**copy.deepcopy(expected['result']), 'session_id': session, 'case_id': case['case_id'], 'status': 'ended'}
    bare_result = {k: v for k, v in expected['result'].items() if k != 'threads'}
    bare_result['score'] = expected['score']
    visited = []

    def respond(request):
        path = request.url.path.removeprefix('/v1')
        visited.append(path)
        if path == '/sessions' and request.method == 'POST':
            return httpx.Response(200, json=dict(session_id=session, case=case, threads=expected['threads']))
        if path == '/sessions/' + session:
            return httpx.Response(200, json=ended)
        for supplier, thread in expected['threads'].items():
            if path == '/sessions/' + session + '/threads/' + supplier:
                return httpx.Response(200, json={**thread, 'timeouts': []})
        raise AssertionError('unexpected endpoint: ' + path)

    original_client = transport.JournaledArena
    monkeypatch.setattr(transport, 'JournaledArena', lambda *args, **kwargs:
                        original_client(*args, **kwargs, transport=httpx.MockTransport(respond)))
    for key in set(os.environ) | {'ARENA_DATA', 'ARENA_RELEASE', 'PYTHONPATH'}:
        if key.startswith('NEGOTIATOR_') or key in {'ARENA_DATA', 'ARENA_RELEASE', 'PYTHONPATH'}:
            monkeypatch.setenv(key, os.environ.get(key, '0'))

    def serial(table, case_id, agent):
        table.open(case_id)
        return bare_result

    async def parallel(arena, case_id, agent, journal):
        journal.session(case_id, session, case)
        return bare_result

    monkeypatch.setattr(negotiator.play, 'play_case', serial)
    monkeypatch.setattr(negotiator.runner, 'play_case', parallel)
    request = worker_request(tmp_path / runner, candidate['config']['memory'], runner)
    request['attempt'] = expected
    request['checkpoint']['checkpoint_id'] = expected['checkpoint_id']
    result = worker.execute(request)
    assert result['status'] == 'completed'
    assert 'threads' in result['result'], (result, visited)
    assert result['result']['threads'] == ended['threads']
    assert result['threads'] == {s: {**t, 'timeouts': []} for s, t in expected['threads'].items()}
    outcome = Outcome.model_validate({k: v for k, v in result.items() if k in Outcome.model_fields}).model_dump()
    expected.update(outcome, outcome=copy.deepcopy(outcome))
    assert evaluate(comparison)['eligible']
    assert all(path.startswith('/sessions') for path in visited)
