"""Read historic traces without modifying them or exposing retained source/model content."""

import argparse
import json
from pathlib import Path

from negotiator.v2.orchestration.offline import OfflineDecisionTrace


def audit(root):
    rows = []
    count = 0
    for path in sorted(root.glob('*.json')):
        if not path.name.endswith(('-grounded.json', '-direct.json', '-minimum.json')):
            continue
        trace = OfflineDecisionTrace.model_validate_json(path.read_bytes())
        trace.verify()
        count += 1
        for call in trace.model_calls:
            admitted = call.permitted_raw_response is not None
            cause = call.cause
            if call.request.task == 'interpret' and trace.assessment.status != 'ok':
                cause = next((x for x in trace.assessment.unknowns
                              if x in ('model_invalid', 'ungrounded_output')), None)
            rows.append(dict(
                artifact=path.name, task=call.request.task, transport_result=call.result_kind,
                consumer_admission='historically_admitted' if admitted else 'historically_rejected',
                retained_coarse_cause=cause, exact_rejection_category=None if admitted else 'unattributable',
                reason=None if admitted else 'Rejected raw outputs and detailed validation errors were not retained.',
            ))
    return {'verified_unchanged_traces': count, 'benchmark_only': True, 'calls': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.root)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'verified_traces': report['verified_unchanged_traces'], 'calls': len(report['calls'])}))


if __name__ == '__main__':
    main()
