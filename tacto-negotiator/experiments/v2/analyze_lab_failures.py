"""Read-only analysis of the three runs named by an existing local Lab report.

Never opens simulator sessions, connects to Arena, modifies originals or reads source patches.
"""

import argparse
import json
from pathlib import Path

from arena_kit.sim import FLOOR, STEP

from negotiator.v2.orchestration.offline import OfflineDecisionTrace


def analyze(root):
    report = json.loads((root / 'report.json').read_text())
    rows, transcripts = [], []
    for row in report['runs']:
        run_path = root / 'runs' / row['run_id'] / 'run.json'
        run = json.loads(run_path.read_text())
        attempt = run['attempts'][0]
        events = next(iter(attempt['threads'].values()))['messages']
        transcript = [{'index': index, 'speaker': 'buyer' if e['from'] == 'buyer' else 'supplier',
                       'message_id': e.get('message_id'), 'status': e.get('status'), 'body': e['body'],
                       'sheets': e.get('term_sheets', [])} for index, e in enumerate(events)]
        transcripts.append(transcript)
        opening = events[0]['term_sheets'][0]['terms']['unit_price']
        prices, checks, verified = [], [], []
        for path in sorted((root / 'traces' / row['run_id'] / row['session_id']).glob('decision-*.json')):
            trace = OfflineDecisionTrace.model_validate_json(path.read_text())
            trace.verify()
            if trace.validation is None or trace.validation.kind != 'valid':
                raise ValueError('original decision was not independently valid')
            values = [float(b.value) for item in trace.evaluations.items
                      if item.candidate.contents.kind == 'offer'
                      for package in item.candidate.contents.packages for b in package.bindings
                      if b.field == 'unit_price']
            prices.extend(values)
            snapshot = json.loads(trace.snapshot_bytes)
            verified.append({'path': str(path), 'trace_hash': trace.trace_hash,
                             'state_version': trace.snapshot.state_version,
                             'supplier_message_count': len(snapshot['conversation']['messages']),
                             'observed_sheets': sum(len(m['observed_sheets'])
                                                    for m in snapshot['conversation']['messages']),
                             'attachments': sum(len(m['attachments'])
                                                for m in snapshot['conversation']['messages'])})
        for index, event in enumerate(events):
            if event['from'] != 'buyer':
                continue
            prior = events[index - 1]
            threshold = round(max(opening * FLOOR,
                                  prior['term_sheets'][0]['terms']['unit_price'] - opening * STEP), 2)
            price = max(s['terms']['unit_price'] for s in event['term_sheets'])
            checks.append({'buyer_message_index': index, 'preceding_status': prior['status'],
                           'offered_price': price, 'simulator_next_acceptance_threshold': threshold,
                           'meets_threshold': price >= threshold})
        rows.append({'arm': row['arm'], 'run_id': row['run_id'], 'original_run': str(run_path),
                     'result': {k: attempt['result'][k] for k in ('ended', 'deal', 'score', 'c_deal')},
                     'timeouts': attempt['timeouts'], 'transcript': transcript,
                     'threshold_checks': checks, 'candidate_prices': sorted(set(prices)),
                     'simulator_floor_price': round(opening * FLOOR, 2),
                     'any_candidate_can_meet_floor': max(prices) >= round(opening * FLOOR, 2),
                     'verified_decisions': verified})
    return {'evidence': 'read-only original transcripts/traces and pinned official simulator rules',
            'hosted_calls': 0, 'sessions_opened': 0, 'runs': rows,
            'identical_transcripts': all(t == transcripts[0] for t in transcripts),
            'scope': 'scripted supplier and fixed candidate controls; no real supplier inference'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.source)
    with args.out.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'runs': len(result['runs']), 'identical_transcripts': result['identical_transcripts'],
                      'verified_decisions': sum(len(r['verified_decisions']) for r in result['runs'])}, indent=2))
