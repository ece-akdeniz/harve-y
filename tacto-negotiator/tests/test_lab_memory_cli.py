import json

import pytest
from test_lab_memory import add_run, build

from negotiator.lab import cli, loop_cli


@pytest.fixture
def memory(tmp_path):
    path = tmp_path / 'memory.sqlite'
    for name, case in [('A', 'case:one'), ('B', 'case:one'), ('C', 'case:two')]:
        add_run(path, name, supplier='sup:' + name, case=case)
    return build(path)


@pytest.mark.parametrize('command,resource,key', [
    (['graph'], 'memory', None),
    (['snapshots'], 'memory-snapshots', None),
    (['show', 'snapshot'], 'memory-snapshots', 'snapshot'),
])
def test_direct_lab_memory_reads(monkeypatch, capsys, command, resource, key):
    calls = []

    class Client:
        def __init__(self, *args):
            pass

        def read(self, resource, key=None):
            calls.append((resource, key))
            return {'result': 'read'}

    monkeypatch.setattr(loop_cli, 'LoopClient', Client)
    assert cli.main(['memory', *command]) == 0
    assert calls == [(resource, key)]
    assert json.loads(capsys.readouterr().out) == {'schema_version': 1, 'result': 'read'}


def test_build_memory_uses_exact_explicit_discovery_scope(monkeypatch, capsys):
    calls = []

    class Client:
        def __init__(self, *args):
            pass

        def write(self, operation, body):
            calls.append((operation, body))
            return body

    monkeypatch.setattr(loop_cli, 'LoopClient', Client)
    assert cli.main(['memory', 'build', '--arena-url', 'https://arena.test', '--environment', 'sandbox',
                     '--source-case', 'case:one', '--source-case', 'case:two', '--format', 'markdown']) == 0
    assert calls == [('memory-snapshot', {'arena_url': 'https://arena.test', 'environment': 'sandbox',
                                        'source_cases': ['case:one', 'case:two']})]
    assert 'https://arena.test' in capsys.readouterr().out


@pytest.mark.parametrize('conflict', [False, True])
def test_checkpoint_create_pins_complete_memory_and_rejects_conflicts(monkeypatch, capsys, memory, conflict):
    calls = []

    class Client:
        def __init__(self, *args):
            pass

        def read(self, resource, key=None):
            assert (resource, key) == ('memory-snapshots', memory['snapshot_id'])
            return memory

    def capture(*args, **kwargs):
        calls.append(kwargs['config'])
        return {'checkpoint_id': 'pinned'}

    monkeypatch.setattr(loop_cli, 'LoopClient', Client)
    monkeypatch.setattr(loop_cli, 'create_checkpoint', capture)
    config = {'memory': {'snapshot_id': 'conflicting'}} if conflict else {'rounds': 5}
    result = cli.main(['checkpoint', 'create', '--description', 'Memory candidate', '--memory', memory['snapshot_id'],
                       '--config', json.dumps(config)])
    assert result == (2 if conflict else 0)
    if conflict:
        assert calls == []
        assert json.loads(capsys.readouterr().out)['error']['code'] == 'invalid_input'
    else:
        assert calls == [{'rounds': 5, 'memory': memory}]


def test_cli_memory_pin_is_persisted_in_real_checkpoint(tmp_path, monkeypatch, capsys, memory):
    from test_lab_checkpoints import git

    from negotiator.lab.checkpoints import load_checkpoint

    repo = tmp_path / 'source'
    repo.mkdir()
    git(repo, 'init')
    git(repo, 'config', 'user.name', 'Test')
    git(repo, 'config', 'user.email', 'test@example.org')
    (repo / 'uv.lock').write_text('pinned lock')
    (repo / 'source.py').write_text('same source')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'fixture')
    root = tmp_path / 'checkpoints'
    from negotiator.lab.loop_store import LoopStore

    store = LoopStore(tmp_path / 'memory.sqlite')
    monkeypatch.setattr(loop_cli, 'LoopClient', lambda *args: store)
    assert cli.main(['checkpoint', 'create', '--repo', str(repo), '--root', str(root),
                     '--description', 'Memory pinned', '--memory', memory['snapshot_id'],
                     '--config', json.dumps({'memory': memory})]) == 0
    output = json.loads(capsys.readouterr().out)
    saved = load_checkpoint(output['checkpoint_id'], root / 'checkpoints')
    assert saved['config']['memory'] == memory
    assert saved['source_tree'] == git(repo, 'rev-parse', saved['commit'] + '^{tree}')


@pytest.mark.parametrize('command', [[], ['--arena-url', 'https://arena.test'],
                                     ['--arena-url', 'https://arena.test', '--environment', 'sandbox']])
def test_memory_build_requires_all_discovery_arguments(command, capsys):
    assert cli.main(['memory', 'build', *command]) == 2
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'invalid_input'


@pytest.mark.parametrize('action', ['graph', 'snapshots', 'show'])
def test_memory_markdown_is_readable_summary_with_citations(tmp_path, monkeypatch, capsys, memory, action):
    from negotiator.lab.loop_store import LoopStore

    store = LoopStore(tmp_path / 'memory.sqlite')
    monkeypatch.setattr(loop_cli, 'LoopClient', lambda *args: store)
    command = ['memory', action, '--format', 'markdown']
    if action == 'show':
        command.insert(2, memory['snapshot_id'])
    assert cli.main(command) == 0
    rendered = capsys.readouterr().out
    assert '**Record:**' not in rendered
    assert "'evidence_id':" not in rendered
    assert 'contract months' in rendered
    assert '3 suppliers' in rendered
    assert '2 cases' in rendered
    if action == 'graph':
        assert '3 original sessions' in rendered
        assert 'attempt:A' in rendered and 'message 0' in rendered
        assert 'Candidate' in rendered
    else:
        assert memory['snapshot_id'] in rendered
        assert 'case:one' in rendered and 'sup:A' in rendered and 'session:A' in rendered


def test_memory_markdown_caps_history_and_labels_conflict_without_supplier_prose(tmp_path, memory):
    from test_lab_memory import message

    from negotiator.lab.loop_store import LoopStore
    from negotiator.lab.reports import markdown_report

    path = tmp_path / 'memory.sqlite'
    for index in range(26):
        add_run(path, 'offer-' + str(index), messages=[message(
            body='<script>private untrusted supplier text</script>',
            term_sheets=[{'terms': {'contract_months': 12}}],
        )])
    add_run(path, 'opposition', messages=[message(body='We prefer shorter contracts.')])
    graph = LoopStore(path).read('memory')
    assert len(graph['observations']) == 30
    report = markdown_report(graph)
    assert 'Showing 25 of 30 observations' in report
    assert '**Conflict — abstains:** contract months' in report
    assert '**Abstains:** Insufficient consistent evidence' in report
    assert 'untrusted supplier text' not in report
    assert "'citation':" not in report
