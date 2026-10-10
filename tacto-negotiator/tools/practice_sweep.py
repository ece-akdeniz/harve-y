"""One recorded run per hosted practice case. Explicit --execute consumes quota."""

import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from arena_kit.cli import load_env
from arena_kit.data import DataPackage
from arena_kit.play import hosted, play
from sandbox_baseline import RecordedClient

from negotiator.agent import PackageAgent
from negotiator.closing import GuardedRemoteTable
from negotiator.evidence import cost_driver_series
from negotiator.supplier_costs import load_estimates
from negotiator.trace import Tracer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--parallel', type=int, default=3, choices=range(1, 4))
    parser.add_argument('--case', action='append', help='restrict to these hosted case IDs')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('pass --execute to authorize one session per hosted case')
    load_env()
    root = Path('experiments/runs') / (datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ') + '-practice-' + uuid4().hex[:6])
    root.mkdir(parents=True)
    client = RecordedClient(root / 'requests.jsonl')
    package = DataPackage(args.data)
    facts, links = dict(package.facts), cost_driver_series(package)
    estimates = load_estimates(package)
    if package.db is not None:
        package.db.close()
    before = client.me()
    cases = hosted(client.cases('practice'))
    if args.case:
        unknown = set(args.case) - {c['case_id'] for c in cases}
        if unknown:
            raise SystemExit(f'Not hosted: {sorted(unknown)}')
        cases = [c for c in cases if c['case_id'] in args.case]
    if before.get('practice', {}).get('left', 0) < len(cases):
        raise SystemExit('Not enough quota for a complete sweep')
    metadata = {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'policy': 'adaptive-packages-final-offer-close', 'parallel': args.parallel,
                'quota_before': before.get('practice'), 'cases': cases}
    (root / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    print('RUN_DIR', root, flush=True)
    print('CASES', [c['case_id'] for c in cases], flush=True)

    def run(case):
        case_id = case['case_id']
        start = time.time()
        agent = PackageAgent(evidence=True, facts=facts, series_by_part=links, supplier_estimates=estimates,
                             tracer=Tracer(root / case_id.replace(':', '-')))
        table = GuardedRemoteTable(client, agent, case)
        print('START', case_id, flush=True)
        try:
            result = play(table, case_id, agent, deadline=start + 480)
            state = client.session(table.session_id)
            threads = {s: client.thread(table.session_id, s) for s in state.get('threads', {})}
            record = {'case': case_id, 'session': table.session_id, 'result': result, 'state': state,
                      'threads': threads, 'elapsed_s': time.time() - start}
            summary = {'case': case_id, 'session': table.session_id, 'score': result.get('score'),
                       'deal': result.get('deal'), 'must_haves_ok': result.get('must_haves_ok'),
                       'c_deal': result.get('c_deal'), 'elapsed_s': round(time.time() - start, 2),
                       'timeouts': {s: len(t.get('timeouts') or []) for s, t in threads.items()}}
        except Exception as exc:
            summary = {'case': case_id, 'session': table.session_id,
                       'error_type': type(exc).__name__, 'status': getattr(exc, 'status', None)}
            record = {'summary': summary}
            # Preserve server state after an error; never open a replacement session.
            if table.session_id:
                try:
                    record['state'] = client.session(table.session_id)
                except Exception as state_exc:
                    record['state_error_type'] = type(state_exc).__name__
        (root / (case_id.replace(':', '-') + '.json')).write_text(json.dumps(record, indent=2))
        print('RESULT', json.dumps(summary), flush=True)
        return summary

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        summaries = list(pool.map(run, cases))
    (root / 'summary.json').write_text(json.dumps(summaries, indent=2))
    after = client.me()
    (root / 'quota-after.json').write_text(json.dumps(after.get('practice'), indent=2))
    print('QUOTA_AFTER', after.get('practice'), flush=True)
    if any('error_type' in row for row in summaries):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
