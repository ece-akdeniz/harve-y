import copy
import json

import pytest
from arena_kit.cost import total_cost
from test_agent import _case
from test_lab_memory import add_run, build, rehash

from negotiator.agent import PackageAgent
from negotiator.trace import Tracer


@pytest.fixture
def memory(tmp_path):
    path = tmp_path / 'memory.sqlite'
    for name, case in [('A', 'case:one'), ('B', 'case:one'), ('C', 'case:two')]:
        add_run(path, name, supplier='sup:' + name, case=case)
    return build(path)


def negotiation():
    case = _case('S03')
    # Both 12 and 24 months cover the entire one-year need and cost exactly the same.
    case['buyer']['horizon_years'] = 1
    case['suppliers'] = ['sup:unseen']
    terms = dict(unit_price=230.0, payment_days=90, contract_months=12, incoterm='DAP')
    threads = {'sup:unseen': [dict(
        **{'from': 'sales@unseen'}, status='open', attachments=[], body='Our current quote.',
        term_sheets=[dict(term_sheet_id='offer:current', terms=terms)],
    )]}
    return case, threads


def offered(agent, case, threads):
    return agent.decide(case, threads)['message']


def test_general_lesson_changes_initial_package_for_unseen_supplier_and_logs_citations(memory, tmp_path):
    case, threads = negotiation()
    baseline = offered(PackageAgent(), case, threads)
    agent = PackageAgent(memory=memory, tracer=Tracer(tmp_path))
    candidate = offered(agent, case, threads)
    before, after = [m['term_sheets'][0]['terms'] for m in (baseline, candidate)]
    assert before['contract_months'] == 12
    assert after['contract_months'] == 24
    assert total_cost(case, after) <= total_cost(case, before)
    assert 'prefer longer' not in candidate['body'].lower()
    assert all(supplier not in candidate['body'] for supplier in memory['source_suppliers'])
    trace = [json.loads(line) for line in (tmp_path / 'trace.jsonl').read_text().splitlines()]
    decision = next(row for row in trace if row.get('kind') == 'memory_package')
    assert decision['snapshot_id'] == memory['snapshot_id']
    assert decision['lesson_ids'] == ['preference:contract_months:higher']
    assert decision['evidence_ids'] == memory['lessons'][0]['evidence_ids']
    # Later current supplier requests remain authoritative; memory does not reapply.
    later = offered(agent, case, threads)
    assert later['term_sheets'][0]['terms']['contract_months'] == 12
    trace = [json.loads(line) for line in (tmp_path / 'trace.jsonl').read_text().splitlines()]
    assert sum(row.get('kind') == 'memory_package' for row in trace) == 1


@pytest.mark.parametrize('change', ['costlier', 'must_have', 'unsupported', 'empty'])
def test_memory_abstains_when_preference_is_unsupported_or_not_cost_neutral(memory, change):
    case, threads = negotiation()
    if change == 'costlier':
        case['buyer'].update(horizon_years=2, fallback_unit_price=100, fallback_risk_pct=0)
    elif change == 'must_have':
        case['buyer']['must_haves'] = [dict(field='contract_months', op='<=', value=12)]
    elif change == 'unsupported':
        case['term_options']['contract_months'] = [12]
    else:
        memory = rehash({**memory, 'lessons': []})
    assert offered(PackageAgent(memory=memory), case, threads) == offered(PackageAgent(), case, threads)


def test_tampered_memory_stops_agent_before_execution(memory):
    memory['lessons'][0]['direction'] = 'lower'
    with pytest.raises(ValueError):
        PackageAgent(memory=memory)


def test_runtime_helper_abstains_on_invalid_current_options(memory):
    from negotiator.memory_policy import prefer_package

    case, _ = negotiation()
    before = dict(payment_days=90, contract_months=12, incoterm='DAP')
    case['term_options']['contract_months'] = ['invalid', 24]
    selected, trace = prefer_package(case, before, 230.0, memory=memory)
    assert selected == before
    assert trace is None


def test_snapshot_is_detached_from_callers_after_agent_construction(memory):
    agent = PackageAgent(memory=memory)
    memory['lessons'].clear()
    case, threads = negotiation()
    assert offered(agent, case, threads)['term_sheets'][0]['terms']['contract_months'] == 24
    assert agent.memory != copy.deepcopy(memory)


def worker_request(tmp_path, memory, runner='serial'):
    import hashlib
    from pathlib import Path

    from test_lab_loop_store import checkpoint

    from negotiator.lab import worker
    from negotiator.lab.checkpoints import resolve_config

    project = Path(worker.__file__).resolve().parents[3]
    manifest = checkpoint('worker')
    manifest.update(runner=runner, config=resolve_config({'memory': memory}),
                    lock_sha256=hashlib.sha256((project / 'uv.lock').read_bytes()).hexdigest())
    return dict(checkpoint=manifest, project=str(project), attempt_root=str(tmp_path),
                attempt={'attempt_id': 'heldout', 'case_id': 'case:S03'},
                arena_url=memory['arena_url'], environment=memory['environment'])


@pytest.mark.parametrize('runner', ['serial', 'async'])
def test_worker_both_runners_persist_real_memory_decisions(tmp_path, memory, runner, monkeypatch):
    import os

    import negotiator.play
    import negotiator.runner
    from negotiator.lab import worker

    for key in set(os.environ) | {'ARENA_DATA', 'ARENA_RELEASE', 'PYTHONPATH'}:
        if key.startswith('NEGOTIATOR_') or key in {'ARENA_DATA', 'ARENA_RELEASE', 'PYTHONPATH'}:
            monkeypatch.setenv(key, os.environ.get(key, '0'))
    case, threads = negotiation()

    def serial(table, case_id, agent):
        terms = offered(agent, case, threads)['term_sheets'][0]['terms']
        return dict(ended=True, score=0.8, terms=terms)

    async def parallel(arena, case_id, agent, journal):
        return serial(arena, case_id, agent)

    # Replace only external orchestration, retaining the real agent, validation and trace.
    monkeypatch.setattr(negotiator.play, 'play_case', serial)
    monkeypatch.setattr(negotiator.runner, 'play_case', parallel)
    request = worker_request(tmp_path, memory, runner)
    result = worker.execute(request)
    assert result['status'] == 'completed'
    assert result['result']['terms']['contract_months'] == 24
    trace_path = tmp_path / 'trace.jsonl'
    assert trace_path.is_file()
    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert next(e for e in events if e.get('kind') == 'memory_package')['snapshot_id'] == memory['snapshot_id']


@pytest.mark.parametrize('change', ['arena', 'environment', 'missing_scope', 'tampered_memory', 'source_tree'])
def test_worker_rejects_invalid_memory_scope_and_identity_before_execution(tmp_path, memory, change, monkeypatch):
    from negotiator.lab import worker
    from negotiator.lab.checkpoints import _git

    request = worker_request(tmp_path, memory)
    if change == 'arena':
        request['arena_url'] = 'https://another-arena.test'
    elif change == 'environment':
        request['environment'] = 'practice'
    elif change == 'missing_scope':
        request.pop('environment')
    elif change == 'tampered_memory':
        request['checkpoint']['config']['memory']['lessons'][0]['direction'] = 'lower'
    else:
        request['checkpoint'].update(commit=_git(request['project'], 'rev-parse', 'HEAD'), source_tree='0' * 40)
    with pytest.raises(ValueError):
        worker.validate_runtime(request)
