"""Read-only export of the single Arena integration run; never opens a session."""

import argparse
import importlib.metadata
import json
from pathlib import Path

from arena_kit.cost import closing_terms, must_haves_ok, total_cost
from arena_kit.docs import standard_terms

from negotiator.lab.publish import load_snapshots
from negotiator.v2.orchestration.offline import OfflineDecisionTrace


def export(root, preflight):
    original = json.loads((root / 'report.json').read_text())
    if len(original['runs']) != 1:
        raise ValueError('exactly one original negotiation required')
    row = original['runs'][0]
    run = next(r for _, r in load_snapshots(root / 'runs') if r.run_id == row['run_id'])
    attempt = run.attempts[0]
    directory = root / 'traces' / run.run_id / attempt.session_id
    terminal = json.loads((directory / 'terminal-observation.json').read_text())
    case = json.loads((root / 'case.json').read_text())
    events = attempt.threads[case['suppliers'][0]]['messages']
    supplier_evaluations = []
    for index, event in enumerate(events):
        if event.get('from') == 'buyer':
            continue
        for sheet in event.get('term_sheets', []):
            standard = standard_terms(events[:index + 1])
            complete = closing_terms(case, sheet['terms'], standard)
            supplier_evaluations.append({
                'message_index': index, 'offer_id': sheet.get('term_sheet_id'),
                'status': event.get('status'), 'complete_terms': complete,
                'official_cost': total_cost(case, sheet['terms'], standard),
                'must_haves_ok': must_haves_ok(case, sheet['terms'], standard),
                'scope': 'post-run read-only evaluation; supplier estimate disabled',
            })
    traces = []
    for path in sorted(directory.glob('decision-*.json')):
        trace = OfflineDecisionTrace.model_validate_json(path.read_bytes())
        trace.verify()
        traces.append(trace.model_dump(mode='json'))
    decisions = row['metrics']['decisions']
    report = {
        'offline': {
            'environment': 'official arena-sim engine: arena_kit.sim.Sim, in-process, clock enabled',
            'arena_kit_version': importlib.metadata.version('arena-kit'),
            'source_revision': '1b5516bb95ef28e37f69aa446dc62168864bca53',
            'case_identity': case['case_id'], 'case_kind': 'public P10 supplied to official Sim; not bundled S01-S03',
            'run': row, 'official_outcome': attempt.result,
            'rounds': attempt.rounds, 'timeouts': attempt.timeouts,
            'interpretation_admission': sum(d['interpretation_admitted'] for d in decisions) / len(decisions),
            'fallbacks': sum(d['fallbacks'] for d in decisions),
            'model_calls': sum(d['calls'] for d in decisions),
            'model_latency_s': sum(d['latency_s'] for d in decisions),
            'negotiation_elapsed_s': attempt.elapsed_s,
            'inference_expenditure_usd': 0,
            'supplier_evaluations': supplier_evaluations,
            'supplier_offers': [e['complete_terms']['unit_price'] for e in supplier_evaluations],
            'buyer_counteroffers': [e['term_sheets'][0]['terms'] for e in events if e.get('from') == 'buyer'],
            'current_state_received': True, 'terminal': terminal,
            'strategy': ('existing supplied finite packages, scripted ambiguity interpreter '
                         'and official-minimum selector'),
            'proposal_changes': 0, 'justification': 'repeated official cost minimum in unchanged supplied universe',
            'live_model_reasoning_demonstrated': False,
            'source_scope': 'Lab saved run is authoritative. Later acknowledgement hardening tested without rerunning.',
        },
        'online': json.loads(preflight.read_text()),
        'comparison': 'No hosted outcome exists. Offline plumbing verified; online blocked before session creation.',
    }
    (root / 'integration-report.json').write_text(json.dumps(report, indent=2) + '\n')
    (root / 'complete-transcript.json').write_text(json.dumps({
        'case': case, 'events': events, 'normalized_terminal': terminal,
        'decisions': traces, 'supplier_evaluations': supplier_evaluations,
    }, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--preflight', type=Path, required=True)
    args = parser.parse_args()
    report = export(args.root, args.preflight)
    print(json.dumps({key: report['offline'][key] for key in (
        'supplier_offers', 'rounds', 'model_calls', 'model_latency_s', 'negotiation_elapsed_s',
        'interpretation_admission', 'fallbacks',
    )}, indent=2))
