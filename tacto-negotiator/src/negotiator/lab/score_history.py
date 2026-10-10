"""Compact read-only history; case outcomes belong only to the recorded selected supplier."""

from datetime import UTC, datetime

from .reconcile import known_score, official_result


def _name(supplier, threads):
    if not supplier:
        return 'No selected supplier'
    thread = threads.get(supplier, {}) if isinstance(threads, dict) else {}
    messages = thread.get('messages', []) if isinstance(thread, dict) else []
    if isinstance(messages, list):
        for message in messages:
            if (isinstance(message, dict) and message.get('from') not in (None, 'buyer')
                    and isinstance(message.get('from_name'), str) and message['from_name'].strip()):
                return message['from_name'][:200]
    return supplier


def _original(attempt, *, require_ended=False):
    result = attempt.get('result') or {}
    return (attempt.get('status') == 'completed' and known_score(attempt.get('score'))
            and result.get('ended') is not False and (not require_ended or result.get('ended') is True))


def _point(meta, attempt, *, require_ended=False):
    result = attempt.get('result') or {}
    original = _original(attempt, require_ended=require_ended)
    outcome = result if original else official_result({**attempt, 'status': 'failed'})
    outcome = outcome or {}
    supplier = outcome.get('supplier_id')
    supplier = supplier if isinstance(supplier, str) and supplier else None
    return {
        **meta, 'session_id': attempt.get('session_id'), 'status': attempt.get('status'),
        'score': attempt['score'] if original else outcome.get('score'),
        'recovered': bool(outcome) and not original,
        'supplier_id': supplier, 'supplier_name': _name(supplier, attempt.get('threads', {})),
    }


def score_history(runs, *, campaigns=(), suites=(), checkpoints=()):
    """Never fabricate per-thread scores or alter promotion evidence. Scores remain fractions."""
    points = []
    suite_by_id = {s['suite_id']: s for s in suites}
    checkpoint_by_id = {c['checkpoint_id']: c for c in checkpoints}
    for campaign in campaigns:
        suite = suite_by_id.get(campaign['suite_id'])
        if not suite:
            continue
        for attempt in campaign['attempts']:
            if attempt['status'] == 'pending':
                continue
            outcome = dict(attempt.get('outcome') or {})
            outcome['status'] = attempt['status']
            recovery = attempt.get('reconciliation')
            if outcome['status'] == 'recovered' and not recovery:
                recovery = dict(outcome)
            if recovery and not _original(outcome, require_ended=True):
                recovered = dict(recovery.get('result') or {})
                if recovered.get('ended') is True:
                    if known_score(recovery.get('score')):
                        recovered['score'] = recovery['score']
                    outcome['result'] = {**outcome.get('result', {}), 'reconciled_result': recovered}
                    if not outcome.get('session_id'):
                        outcome['session_id'] = recovery.get('session_id')
                    if recovery.get('threads'):
                        outcome['threads'] = recovery['threads']
            started = attempt.get('start', {}).get('started_at', campaign['created_at'])
            checkpoint = checkpoint_by_id.get(attempt['checkpoint_id'], {})
            meta = dict(
                point_id=attempt['attempt_id'], run_id=None, campaign_id=campaign['campaign_id'],
                name=campaign['campaign_id'], author=campaign['author'], source='campaign',
                case_id=attempt['case_id'], environment=suite['environment'], arena_url=suite['arena_url'],
                started_at=datetime.fromtimestamp(started, UTC).isoformat(),
                time_basis='Attempt start' if attempt.get('start') else 'Campaign start',
                commit=checkpoint.get('commit'), dirty=False,
                checkpoint_id=attempt['checkpoint_id'], arm=attempt['arm'],
            )
            points.append(_point(meta, outcome, require_ended=True))
    for run in sorted(runs, key=lambda r: r.source == 'imported'):
        for attempt in run.attempts:
            if attempt.status == 'pending':
                continue
            meta = dict(
                point_id=f'{run.run_id}:{attempt.attempt_id}', run_id=run.run_id, campaign_id=None,
                name=run.name, author=run.author, source=run.source, case_id=attempt.case_id,
                environment=run.environment, arena_url=run.arena_url, started_at=run.started_at,
                time_basis='Session start' if run.source == 'imported' else 'Run start',
                commit=run.provenance.commit if run.provenance else None,
                dirty=run.provenance.dirty if run.provenance else None, checkpoint_id=None, arm=None,
            )
            points.append(_point(meta, attempt.model_dump()))
    unique = {}
    for point in points:
        key = ((point['arena_url'].rstrip('/'), point['session_id'])
               if point['session_id'] else ('point', point['point_id']))
        if key not in unique:
            unique[key] = point
        elif unique[key]['score'] is None and known_score(point['score']):
            first = unique[key]
            first.update(score=point['score'], recovered=True, supplier_id=point['supplier_id'],
                         supplier_name=point['supplier_name'])
    return {'points': sorted(unique.values(), key=lambda p: (datetime.fromisoformat(p['started_at']), p['point_id']))}
