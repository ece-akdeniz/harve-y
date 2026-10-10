"""Opt-in real pinned-project/kit-simulator rehearsal. Retains /tmp artifacts.

Run: uv run --locked --offline python tools/rehearse_loop.py
Only temporary local Git remotes, lab SQLite and loopback arena are used.
Synthetic policy outcomes are isolated from measured simulator evidence.
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import uvicorn
from arena_kit.sim import Sim, create_app, load_cases

from negotiator.lab.checkpoints import _private, _verify_checkout_bytes
from negotiator.lab.loop_store import LoopStore
from negotiator.lab.policy import default_suite
from negotiator.lab.server import DashboardServer
from negotiator.lab.store import Store


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.PIPE).strip()


def finish_fixture(loop, campaign, gain, *, complete=True):
    for attempt in campaign['attempts']:
        loop.write('attempt-start', dict(attempt_id=attempt['attempt_id'], worker_id='fixture', key_id='fixture'))
        loop.write('attempt-result', dict(
            attempt_id=attempt['attempt_id'], checkpoint_id=attempt['checkpoint_id'],
            session_id='fixture-' + attempt['attempt_id'], status='completed',
            score=0.6 + (gain if attempt['arm'] == 'candidate' else 0), timeouts=0,
            result=dict(deal=True, must_haves_ok=True, ended=True), threads={}, elapsed_s=0,
        ))
    return loop.write('complete', dict(campaign_id=campaign['campaign_id'])) if complete else None


def verify(output, baseline, candidate, suite, cli, measured, status, comparison, session_count):
    for attempt in status['attempts']:
        assert attempt['result']['ended'] is True
        assert attempt['timeouts'] == 0
        identity = hashlib.sha256(attempt['attempt_id'].encode()).hexdigest()
        result = json.loads((output / 'loop' / 'measured' / 'attempts' / identity / 'result.json').read_text())
        assert result['final'] is True
        assert result['runtime']['lock_sha256'] == baseline['lock_sha256']
    storage = output / 'loop'
    remote = output / 'remote.git'
    for arm, checkpoint in [('baseline', baseline), ('candidate', candidate)]:
        worktree = storage / 'measured' / arm
        _verify_checkout_bytes(worktree, checkpoint['commit'])
        assert hashlib.sha256((worktree / 'uv.lock').read_bytes()).hexdigest() == checkpoint['lock_sha256']
        assert (worktree / '.venv').is_dir()
    second = output / 'second-clone'
    if not second.exists():
        subprocess.run(['git', 'clone', '-q', str(remote), str(second)], check=True)
    (second / 'active-untracked.txt').write_text('preserved')
    before = git(second, 'status', '--porcelain')
    restored = output / 'restored'
    if not restored.exists():
        cli('restore', candidate['checkpoint_id'], '--destination', restored, project=second,
            storage_root=output / 'second-loop')
    assert git(second, 'status', '--porcelain') == before
    _verify_checkout_bytes(restored, candidate['commit'])
    attempt = next(a for a in status['attempts'] if a['arm'] == 'candidate')
    supplier = next(iter(attempt['threads']))
    cli('evidence', 'show', attempt['attempt_id'], '--supplier', supplier, '--message', '0',
        project=output / 'source', storage_root=storage)
    finding = dict(finding_id='measured-local-observation', campaign_id='measured',
                   candidate_id=candidate['checkpoint_id'], author='rehearsal',
                   observation='Three local toy repetition blocks improved with zero observed timeouts.',
                   hypothesis='Anchored rounds help this deterministic toy simulator.',
                   change='Test-only anchored rounds versus one-round zero-anchor control.',
                   next_test='Explicitly budgeted hosted sandbox comparison, when authorized.',
                   confidence=0.5, disposition='tested',
                   evidence=[dict(attempt_id=attempt['attempt_id'], supplier=supplier, message_index=0)])
    cli('findings', 'add', '--body', json.dumps(finding), project=output / 'source', storage_root=storage)
    cli('findings', 'list', '--campaign', 'measured', project=output / 'source', storage_root=storage)
    policy_path = output / f'policy-{uuid.uuid4().hex}.sqlite'
    loop = LoopStore(policy_path)
    for checkpoint in (baseline, candidate):
        loop.write('checkpoint', {**checkpoint, 'published': True})
    loop.write('suite', suite)
    loop.write('family', dict(family_id='policy', max_sessions=36))
    loop.write('seed', dict(suite_id=suite['suite_id'], checkpoint_id=baseline['checkpoint_id'], author='fixture'))

    def campaign(name):
        return loop.write('campaign', dict(campaign_id=name, family_id='policy', suite_id=suite['suite_id'],
                          baseline_id=baseline['checkpoint_id'], candidate_id=candidate['checkpoint_id'],
                          generation=1, seed=1, author='fixture', hypothesis='Synthetic policy invariant'))

    rejected = finish_fixture(loop, campaign('reject'), 0)
    assert rejected['status'] == 'rejected'
    first, stale = campaign('promote'), campaign('stale')
    finish_fixture(loop, first, 0.1, complete=False)
    finish_fixture(loop, stale, 0.1, complete=False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda name: loop.write('complete', dict(campaign_id=name)), ['promote', 'stale']))
    assert sorted(o['status'] for o in outcomes) == ['baseline_superseded', 'promoted']
    promoted = next(o for o in outcomes if o['status'] == 'promoted')
    superseded = next(o for o in outcomes if o['status'] == 'baseline_superseded')
    assert loop.write('complete', dict(campaign_id=promoted['campaign_id'])) == promoted
    rollback_body = dict(request_id='rollback', suite_id=suite['suite_id'],
                         checkpoint_id=baseline['checkpoint_id'], generation=2, author='fixture')
    rollback = loop.write('restore', rollback_body)
    assert rollback['generation'] == 3
    assert loop.write('restore', rollback_body) == rollback
    summary = dict(artifact_root=str(output), policy_db=str(policy_path), measured=measured, comparison=comparison,
                   sessions=session_count, policy=dict(rejected=rejected, promoted=promoted,
                   superseded=superseded, rollback=rollback), restored=str(restored))
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(dict(artifacts=str(output), sessions=session_count,
                          verdict=status['completion']['status'],
                          metrics=status['completion']['evaluation']['metrics']), indent=2))


def main():
    source = Path(__file__).resolve().parents[1]
    output = Path(tempfile.mkdtemp(prefix='tacto-loop-rehearsal-'))
    print(f'Artifacts: {output}', flush=True)
    repo = output / 'source'
    repo.mkdir()
    root = Path(git(source, 'rev-parse', '--show-toplevel'))
    names = set()
    for args in [('ls-files', '-z'), ('ls-files', '--others', '--exclude-standard', '-z')]:
        names.update(subprocess.check_output(['git', '-C', str(root), *args], text=True).split('\0'))
    for name in names:
        original = root / name
        if not name or _private(name) or not original.is_file() or original.is_symlink():
            continue
        try:
            relative = original.relative_to(source)
        except ValueError:
            continue
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.name', 'Local rehearsal')
    git(repo, 'config', 'user.email', 'local@localhost')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'Exact public project snapshot')
    remote = output / 'remote.git'
    subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True)
    git(repo, 'remote', 'add', 'origin', str(remote))
    git(repo, 'push', '-q', '-u', 'origin', 'HEAD')
    upload_token = uuid.uuid4().hex
    lab = DashboardServer(('127.0.0.1', 0), Store(output / 'lab.sqlite'),
                          password=uuid.uuid4().hex, upload_token=upload_token)
    threading.Thread(target=lab.serve_forever, daemon=True).start()
    sim = Sim(load_cases())
    arena_key = uuid.uuid4().hex
    sim.teams[arena_key] = 'local-rehearsal'
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(sim), log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.02)
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('NEGOTIATOR_', 'LAB_', 'ARENA_', 'LLM_', 'ANTHROPIC_', 'OPENAI_')):
            env.pop(key)
    env.update(LAB_UPLOAD_TOKEN=upload_token, ARENA_API_KEY=arena_key,
               ARENA_URL=f'http://127.0.0.1:{port}', PYTHONPATH=str(source / 'src'))
    lab_url = f'http://127.0.0.1:{lab.server_port}'
    storage = output / 'loop'
    calls = []

    def cli(*args, project=repo, storage_root=storage):
        command = [sys.executable, '-m', 'negotiator.cli', 'lab', *map(str, args),
                   '--repo', str(project), '--root', str(storage_root), '--url', lab_url, '--author', 'rehearsal']
        result = subprocess.run(command, env=env, cwd=output, capture_output=True, text=True)
        body = json.loads(result.stdout)
        calls.append(dict(args=list(map(str, args)), exit=result.returncode, body=body))
        (output / 'cli-results.json').write_text(json.dumps(calls, indent=2))
        if result.returncode:
            raise RuntimeError(f'CLI exit {result.returncode}: {body}')
        return body

    try:
        baseline = cli('checkpoint', 'create', '--description', 'Simulator one-round control', '--config',
                       json.dumps(dict(anchor=0, rounds=1, final_hold_s=0, estimates={}, claims=False, meso=False)))
        candidate = cli('checkpoint', 'create', '--description', 'Simulator anchored rounds', '--config',
                        json.dumps(dict(final_hold_s=0, estimates={}, claims=False, meso=False)))
        for checkpoint in (baseline, candidate):
            cli('checkpoint', 'publish', checkpoint['checkpoint_id'])
        suite = default_suite(env['ARENA_URL'], 'simulator')
        suite.update(suite_id='s01-s02-simulator-rehearsal-v1', cases=['case:S01', 'case:S02'])
        cli('suite', 'create', '--body', json.dumps(suite))
        cli('recommended', 'seed', '--suite', suite['suite_id'], '--checkpoint', baseline['checkpoint_id'])
        print('Starting real CLI campaign: twelve planned simulator sessions', flush=True)
        measured = cli('campaign', 'run', '--family', 'measured', '--candidate', candidate['checkpoint_id'],
                       '--hypothesis', 'Anchored rounds improve local toy score over one-round control',
                       '--max-sessions', '12', '--suite', suite['suite_id'], '--campaign-id', 'measured')
        status = cli('campaign', 'status', 'measured')
        comparison = cli('campaign', 'compare', 'measured')
        cli('campaign', 'sync', 'measured')
        assert len(status['attempts']) == 12
        assert all(a['status'] == 'completed' for a in status['attempts'])
        assert len(sim.sessions) == 12
        verify(output, baseline, candidate, suite, cli, measured, status, comparison, len(sim.sessions))
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        lab.shutdown()
        lab.server_close()



def verify_existing(output):
    """Finish path/restore/policy assertions without repeating measured sessions."""
    records = json.loads((output / 'cli-results.json').read_text())
    def result(prefix):
        return next(r['body'] for r in records if r['args'][:len(prefix)] == prefix)
    baseline = records[0]['body']
    candidate = records[1]['body']
    suite = {k: v for k, v in result(['suite', 'create']).items() if k != 'schema_version'}
    status = result(['campaign', 'status'])
    comparison = result(['campaign', 'compare'])
    measured = result(['campaign', 'run'])
    assert len(status['attempts']) == 12
    assert all(a['status'] == 'completed' for a in status['attempts'])
    assert len({a['session_id'] for a in status['attempts']}) == 12
    token = uuid.uuid4().hex
    lab = DashboardServer(('127.0.0.1', 0), Store(output / 'lab.sqlite'),
                          password=uuid.uuid4().hex, upload_token=token)
    threading.Thread(target=lab.serve_forever, daemon=True).start()
    env = os.environ.copy()
    env.update(LAB_UPLOAD_TOKEN=token, ARENA_API_KEY=uuid.uuid4().hex,
               ARENA_URL='http://127.0.0.1:1')

    def cli(*args, project, storage_root):
        command = [sys.executable, '-m', 'negotiator.cli', 'lab', *map(str, args),
                   '--repo', str(project), '--root', str(storage_root),
                   '--url', f'http://127.0.0.1:{lab.server_port}', '--author', 'rehearsal']
        proc = subprocess.run(command, env=env, cwd=output, capture_output=True, text=True)
        body = json.loads(proc.stdout)
        records.append(dict(args=list(map(str, args)), exit=proc.returncode, body=body))
        (output / 'cli-results.json').write_text(json.dumps(records, indent=2))
        assert proc.returncode == 0, body
        return body

    try:
        verify(output, baseline, candidate, suite, cli, measured, status, comparison, 12)
    finally:
        lab.shutdown()
        lab.server_close()

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-existing':
        verify_existing(Path(sys.argv[2]))
    else:
        main()
