"""Read-only post-run analysis. No inference, Arena/Lab access or evaluation-label changes."""

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from experiments.v2.run_semantic_validation import frozen_digest
from negotiator.v2.core import models as m
from negotiator.v2.core.diagnostics import rejection
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.orchestration.offline import OfflineDecisionTrace


def synthetic_union_control():
    """Known local counterexample, not reconstruction or repair of any rejected response."""
    body = 'We prefer delivery in 42 days.'
    raw = dict(observations=[dict(observation_id='observation:control', kind='ambiguity', dimension=None,
        summary=body, citations=[dict(session_id='session:offline-p10', thread_id='thread:offline-p10',
        message_id='message:offline-p10-1', start=0, end=len(body), quote=body)], package_fingerprint=None)],
        reported_constraints=[], hypotheses=[], uncertainties=[], questions=[], unknowns=[])
    correct = m.AssessmentDraft.model_validate_json(json.dumps(raw))
    raw = correct.model_dump(mode='json')
    raw['observations'][0]['citations'][0]['end'] += 1
    try:
        m.AssessmentDraft.model_validate_json(json.dumps(raw))
    except ValidationError as error:
        return {'evidence': 'local synthetic control only',
                'fault': 'one-character offset/quote-length mismatch',
                'diagnostic': rejection(error, 'schema').model_dump(mode='json'),
                'error_types_and_paths': [{'type': e['type'], 'path': list(e['loc'])}
                    for e in error.errors(include_input=False, include_context=False, include_url=False)],
                'inference': 'The first SourceRef union-branch error masks the relevant MessageSpan error; '
                             'the same diagnostic does not establish the cause of a hosted rejected response.'}
    raise AssertionError('synthetic invalid span unexpectedly admitted')


def analyze(root, previous):
    report = json.loads((root / 'report.json').read_text())
    old = json.loads((previous / 'report.json').read_text())
    attempts = report['inference']['calls']
    approved = json.loads((root / 'hosted-started.json').read_text())
    if not approved['authorized'] or not approved['token_accounting_confirmed']:
        raise ValueError('missing exact hosted authorization marker')
    if len(attempts) > 19 or Decimal(report['inference']['reserved_usd']) > Decimal('1.00'):
        raise ValueError('experiment exceeds approved allowance')
    if len(attempts) * approved['per_call_reserved_tokens'] > 311296:
        raise ValueError('experiment exceeds token reservation allowance')
    if not (report['frozen_held_out_sha256_after'] == approved['frozen_held_out_sha256'] == frozen_digest()):
        raise ValueError('held-out digest mismatch')
    predictions = json.loads((root / 'predictions.json').read_text())
    reviewed = json.loads((root / 'review-pending.json').read_text())
    interpreter_calls = list(report['interpretation_calls'])
    selection_calls, paired, p10_review = [], [], []
    for index, row in enumerate(report['selection_decisions']):
        trace = OfflineDecisionTrace.model_validate_json((root / f'p10-{index}.json').read_text())
        control = OfflineDecisionTrace.model_validate_json((root / f'p10-{index}-baseline.json').read_text())
        trace.verify()
        control.verify()
        if trace.evaluations != control.evaluations:
            raise ValueError('same-input baseline economics differ')
        selected = next(item for item in trace.evaluations.items
                        if item.candidate.candidate_id == trace.decision.candidate_id)
        history = old['p10'][index]
        same_action = semantic_hash(selected.candidate.contents) == history['selected_contents_hash']
        interpreter_calls.extend(c.model_dump(mode='json', exclude={'permitted_raw_response'})
                                 for c in trace.model_calls if c.request.task == 'interpret')
        selection_calls.extend(c.model_dump(mode='json', exclude={'permitted_raw_response'})
                               for c in trace.model_calls if c.request.task == 'select')
        paired.append({'message_index': index, 'same_selected_contents_as_previous': same_action,
            'old_assessment_status': history['assessment_status'], 'new_assessment_status': trace.assessment.status,
            'old_selected_cost': history['official_costs'], 'new_selected_cost': row['official_cost'],
            'new_cost_delta': row['cost_delta'], 'new_selection_admitted': row['selection_admitted'],
            'new_final_action_valid': row['final_action_valid'], 'trace_hash': trace.trace_hash})
        p10_review.append({'message_index': index,
            'reviewer_type': 'nonblind agent review; not independent human evaluation',
            'observation': ('Minimum package answers volume within validated 23400/year terms; no unsupported '
                'economic departure. It does not prove supplier commitment or preference understanding.'
                if index == 0 else
                '42-day package and exact preference citation retained; +EUR1262.88 official proposal cost. '
                'Plausible preference response, not required concession or evidence of agreement.'),
            'interpretation_contribution': 'unavailable: interpreter fell back',
            'independent_human_semantic_correct': None, 'independent_human_critical_errors': None})
    failures = Counter((c['diagnostic']['stage'], c['diagnostic']['category'], c['diagnostic']['field'])
                       for c in interpreter_calls if c['diagnostic'])
    admitted = sum(c['consumer_admitted'] is True for c in interpreter_calls)
    ground_failures = sum(c['diagnostic'] is not None and c['diagnostic']['stage'] == 'grounding'
                          for c in interpreter_calls)
    return {
        'evidence': 'read-only analysis of completed actual hosted run; synthetic control separately identified',
        'hosted_status': report['status'], 'attempts': len(attempts),
        'transport_success': sum(c['status'] == 'success' for c in attempts),
        'reserved_tokens': len(attempts) * approved['per_call_reserved_tokens'],
        'reserved_usd': report['inference']['reserved_usd'],
        'usage_estimate_usd': report['inference']['uncached_reported_usage_cost_usd'],
        'usage_known_calls': len(attempts) - report['inference']['unknown_usage_calls'],
        'input_tokens': sum(c['input_tokens'] or 0 for c in attempts),
        'output_tokens': sum(c['output_tokens'] or 0 for c in attempts),
        'summed_model_latency_s': sum(c['latency_s'] for c in attempts),
        'interpretation': {'attempts': len(interpreter_calls), 'consumer_admitted': admitted,
            'fallbacks': sum(c['fallback_used'] for c in interpreter_calls),
            'development_admitted': sum(c['consumer_admitted'] is True for c in report['interpretation_calls']),
            'development_denominator': len(predictions),
            'automatic_provisional_correct': report['interpretation']['semantic_correct'],
            'sole_admitted_development_example': [p['id'] for p in predictions if p['assessment']['status'] == 'ok'],
            'diagnostics': [{'stage': k[0], 'category': k[1], 'field': k[2], 'count': count}
                            for k, count in failures.items()],
            'grounding_stage_rejections': ground_failures,
            'grounding_claim_limit': 'Fifteen schema-rejected outputs did not reach grounding; '
                                    'the sole admitted output has empty commercial collections.'},
        'selection': {'p10_calls': len(selection_calls),
            'consumer_admitted': sum(c['consumer_admitted'] is True for c in selection_calls),
            'fallbacks': sum(c['fallback_used'] for c in selection_calls),
            'probe_admitted': json.loads((root / 'connectivity.json').read_text())['consumer_valid'],
            'paired_p10': paired, 'agent_review': p10_review},
        'independent_human_review': {'status': 'pending',
            'development_rows_unreviewed': sum(x['semantic_correct'] is None for x in reviewed['interpretation']),
            'p10_selection_rows_unreviewed': sum(x['semantic_defensible'] is None for x in reviewed['selection']),
            'critical_errors': None},
        'semantic_gate': {'passed': False,
            'reason': '1/14 admitted development outputs misses the preregistered 12/14 usability criterion; '
                      'independent human adjudication also remains pending'},
        'assignment_4_recommendation': 'Do not proceed. First resolve the citation-admission compatibility '
            'and union-diagnostic ambiguity offline without weakening validators; '
            'any hosted rerun needs new authorization.',
        'previous_run': {'attempts': old['inference']['attempts'],
            'usage_estimate_usd': old['inference']['uncached_reported_usage_cost_usd'],
            'comparison_limit': 'Development corpus differs from previous benchmark; only the two P10 '
                                'messages/package contents are a direct comparison. No randomized ablation.'},
        'synthetic_diagnostic_control': synthetic_union_control(),
        'frozen_held_out_sha256': frozen_digest(), 'held_out_calls': 0,
        'original_artifacts_modified': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run, args.previous)
    with args.out.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('attempts', 'transport_success', 'usage_estimate_usd', 'semantic_gate')},
                     indent=2))
