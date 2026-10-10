"""Free D01/D02 crash-and-resume rehearsal. Never opens practice cases."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from arena_kit.cli import load_env
from arena_kit.client import ArenaClient
from compare import ROOT
from staged_batch import inspect_run


def main():
    from negotiator.report import summarise

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('output already exists; inspect sessions instead of starting again')
    os.chdir(ROOT)
    load_env()
    env = {**os.environ, 'ARENA_URL': 'https://arena.tacto.ai', 'NEGOTIATOR_LOG_DIR': str(args.out),
           'NEGOTIATOR_CLAIMS': '0', 'NEGOTIATOR_ESTIMATES': '0', 'NEGOTIATOR_MESO': '0'}
    args.out.mkdir(parents=True)
    client = ArenaClient(base_url=env['ARENA_URL'], api_key=env.get('ARENA_API_KEY'))
    before = client.me().get('practice')
    command = ['uv', 'run', '--locked', 'python', str(ROOT / 'tools/selected_cases.py'),
               '--set', 'sandbox', '--cases', 'case:D01', 'case:D02', '--parallel', '2',
               '--policy-config', args.config]
    killed = False
    with (args.out / 'first-process.txt').open('w') as log:
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        start = time.monotonic()
        while proc.poll() is None and time.monotonic() - start < 120:
            trace = args.out / 'trace.jsonl'
            if trace.exists():
                rows = []
                for line in trace.read_text().splitlines():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                if any(row.get('event') == 'send' for row in rows):
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    killed = True
                    break
            time.sleep(0.1)
        if proc.poll() is None:
            # No injection point: allow the already-open sessions to finish.
            proc.wait(timeout=600)
    print('Crash injected after first journalled send:', killed, flush=True)
    with (args.out / 'resumed-process.txt').open('w') as log:
        resumed = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    summary = summarise(args.out)
    run = {'returncode': resumed.returncode, 'timed_out': False, 'cases': summary['cases']}
    problems = inspect_run(client, run, args.out)
    sessions = summary['sessions']
    if len(sessions) != 2:
        problems.append('expected exactly two sandbox sessions across restart')
    result = {'crash_injected': killed, 'sessions': sessions, 'problems': problems,
              'before': before, 'after': client.me().get('practice'),
              'results': {c: {k: r.get(k) for k in ('score','deal','timeouts','must_haves_ok','session')}
                          for c, r in run['cases'].items()}}
    (args.out / 'rehearsal.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    return 0 if killed and not problems else 1


if __name__ == '__main__':
    raise SystemExit(main())
