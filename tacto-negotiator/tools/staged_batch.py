"""Run an explicit, bounded manifest sequentially; stop on failed safety checks.

Rows: {case, label, ref, config?}. Ref must be an immutable commit SHA.
This tool deliberately accepts no leaderboard or historical cost targets.
"""
import argparse
import json
import os
from pathlib import Path

from compare import ROOT, Arm, practice_left, run_one


def inspect_run(client, run, directory):
    from negotiator.state import Journal

    failures = []
    if run['returncode'] or run['timed_out'] or not run['cases']:
        failures.append('runtime failure or missing result')
    evidence = {}
    for cid, row in run['cases'].items():
        sid = row.get('session')
        if not sid or row.get('score') is None or row.get('error') or row.get('must_haves_ok') is False:
            failures.append(f'{cid}: incomplete or invalid result')
        if not sid:
            continue
        state = client.session(sid)
        threads = {supplier: client.thread(sid, supplier) for supplier in state.get('threads', {})}
        evidence[cid] = {'state': state, 'threads': threads}
        if state.get('status') != 'ended':
            failures.append(f'{cid}: session not ended')
        counts = [t.get('timeouts') for t in threads.values()]
        row['timeouts'] = sum(counts) if counts and all(isinstance(x, int) for x in counts) else None
        def walk(obj, cid=cid):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == 'claim_results':
                        for claim in v or []:
                            if 'contradict' in json.dumps(claim).lower():
                                failures.append(f'{cid}: contradicted claim')
                    else:
                        walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        walk(threads)
    for path in directory.rglob('journal.jsonl'):
        journal = Journal(path)
        pending = {r['move_id'] for r in journal.records if r.get('rec') == 'intent'}
        resolved = {r['move_id'] for r in journal.records if r.get('rec') in ('done', 'failed', 'abandoned')}
        if pending - resolved:
            failures.append('unreconciled requests')
        if any(r.get('rec') == 'failed' for r in journal.records):
            failures.append('failed request: inspect before new starts')
    (directory / 'server-evidence.json').write_text(json.dumps(evidence, indent=2))
    return failures


def main():
    from arena_kit.cli import load_env
    from arena_kit.client import ArenaClient

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest', type=Path)
    ap.add_argument('--budget', type=int, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    jobs = json.loads(args.manifest.read_text())
    if not 0 < len(jobs) <= args.budget <= 52:
        ap.error('manifest must fit the released batch budget')
    if args.out.exists():
        ap.error('output already exists; inspect existing sessions before restarting')
    os.chdir(ROOT)
    load_env()
    env = {**os.environ, 'ARENA_URL': 'https://arena.tacto.ai',
           'ARENA_DATA': str(ROOT / 'data/package'), 'NEGOTIATOR_CLAIMS': '0',
           'NEGOTIATOR_ESTIMATES': '0', 'NEGOTIATOR_MESO': '0'}
    client = ArenaClient(base_url=env['ARENA_URL'], api_key=env.get('ARENA_API_KEY'))
    before = practice_left(env)
    if before.get('left', 0) - len(jobs) < 46:
        ap.error('insufficient quota to preserve 46 sessions')
    args.out.mkdir(parents=True)
    result = {'before': before, 'manifest': jobs, 'runs': [], 'stopped': None}
    arms = []
    try:
        for job in jobs:
            if len(job['ref']) != 40 or any(c not in '0123456789abcdef' for c in job['ref']):
                raise ValueError('immutable full source SHA required')
            options = ['--runner', 'async']
            if job.get('config'):
                options += ['--policy-config', job['config']]
            arm = Arm(job['label'], job['ref'], {}, options)
            arm.prepare(Path(env['ARENA_DATA']))
            arms.append(arm)
        for i, (job, arm) in enumerate(zip(jobs, arms, strict=True), 1):
            if practice_left(env).get('left', 0) <= 46:
                raise RuntimeError('reserve reached')
            directory = args.out / f"{i}-{job['case']}-{job['label']}"
            print(f"Starting {i}/{len(jobs)}: {job['case']} {job['label']}", flush=True)
            run = run_one(arm, ['play', f"case:{job['case']}"], env, directory, 600)
            run['job'] = job
            result['runs'].append(run)
            problems = inspect_run(client, run, directory)
            result['after'] = practice_left(env)
            result['stopped'] = problems or None
            (args.out / 'summary.json').write_text(json.dumps(result, indent=2))
            print(json.dumps({'case': job['case'], 'label': job['label'], 'results': run['cases'],
                              'problems': problems, 'left': result['after'].get('left')}), flush=True)
            if problems:
                return 1
    finally:
        for arm in arms:
            arm.cleanup()
        (args.out / 'summary.json').write_text(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
