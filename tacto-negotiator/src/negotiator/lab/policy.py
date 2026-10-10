"""Complete-sample comparison policy; narrative findings never affect eligibility."""

import math
import statistics

from ..memory import identifier, normalize_arena, supplier_author_matches, validate_memory
from .loop_models import Outcome


def default_suite(arena_url="https://arena.tacto.ai", environment="sandbox"):
    return dict(
        suite_id=f"d01-d02-{environment}-serial-v1",
        cases=["case:D01", "case:D02"],
        repetitions=3,
        runner="serial",
        arena_url=arena_url,
        environment=environment,
        data={},
        max_sessions=12,
        policy=dict(version="v1", min_gain=1.0, max_case_regression=2.0, min_win_fraction=2 / 3),
    )


def evaluate_campaign(suite, baseline, candidate, attempts):
    gates, gaps = [], []

    def gate(name, passed, detail):
        gates.append(dict(id=name, passed=bool(passed), detail=detail))
        if not passed:
            gaps.append(name)

    gate(
        "checkpoints",
        all(
            c.get("published") is True and c.get("runner") == suite["runner"] and c.get("data") == suite["data"]
            for c in (baseline, candidate)
        ),
        "Published checkpoints and identical declared runner/data required",
    )
    _memory_gates(suite, baseline, candidate, attempts, gate)
    planned = {
        (arm, case, repeat)
        for arm in ("baseline", "candidate")
        for case in suite["cases"]
        for repeat in range(1, suite["repetitions"] + 1)
    }
    indexed = {(a.get("arm"), a.get("case_id"), a.get("repeat")): a for a in attempts}
    valid = len(indexed) == len(attempts) and set(indexed) == planned
    valid = valid and all(
        a.get("status") == "completed"
        and a.get("result", {}).get("ended") is True
        and type(a.get("score")) in (int, float)
        and math.isfinite(a["score"])
        and 0 <= a["score"] <= 1
        and ("score" not in a.get("result", {}) or a["result"]["score"] == a["score"])
        for a in attempts
    )
    gate("complete_sample", valid and suite["repetitions"] >= 3, "Every planned original outcome required")
    gate(
        "must_haves",
        all(
            type(a.get("result", {}).get("deal")) is bool
            and (not a["result"]["deal"] or a["result"].get("must_haves_ok") is True)
            for a in attempts
            if a.get("arm") == "candidate"
        ),
        "Every candidate deal complies",
    )
    timeout_valid = all(type(a.get("timeouts")) is int and a["timeouts"] >= 0 for a in attempts)
    gate("timeout_evidence", timeout_valid, "Complete known timeout counts required")
    totals = {}
    for arm in ("baseline", "candidate"):
        counts = [a.get("timeouts") for a in attempts if a.get("arm") == arm]
        totals[arm] = sum(counts) if all(type(n) is int and n >= 0 for n in counts) else None
    gate("timeouts", timeout_valid and totals["candidate"] <= totals["baseline"], totals)
    cases, repeats, metrics = [], [], dict(gain=None, timeouts=totals, sample_size=len(attempts))
    if valid:
        for case in suite["cases"]:
            row = {"case_id": case}
            for arm in ("baseline", "candidate"):
                scores = [100 * indexed[arm, case, r]["score"] for r in range(1, suite["repetitions"] + 1)]
                row[arm] = dict(mean=statistics.mean(scores), spread=statistics.pstdev(scores), scores=scores)
            row["gain"] = row["candidate"]["mean"] - row["baseline"]["mean"]
            cases.append(row)
        for r in range(1, suite["repetitions"] + 1):
            row = dict(repeat=r)
            for arm in ("baseline", "candidate"):
                row[arm] = statistics.mean(100 * indexed[arm, c, r]["score"] for c in suite["cases"])
            row["gain"] = row["candidate"] - row["baseline"]
            repeats.append(row)
        metrics.update(
            gain=statistics.mean(c["gain"] for c in cases),
            win_fraction=sum(r["gain"] > 0 for r in repeats) / len(repeats),
        )
    gate("gain", valid and metrics["gain"] >= suite["policy"]["min_gain"], metrics["gain"])
    gate("case_regression", valid and all(c["gain"] >= -suite["policy"]["max_case_regression"] for c in cases), cases)
    gate("repeat_wins", valid and metrics["win_fraction"] >= suite["policy"]["min_win_fraction"], repeats)
    return dict(
        eligible=all(g["passed"] for g in gates),
        gates=gates,
        cases=cases,
        repeats=repeats,
        metrics=metrics,
        evidence_gaps=gaps,
    )


def _memory_gates(suite, baseline, candidate, attempts, gate):
    left, right = [checkpoint.get('config', {}).get('memory') for checkpoint in (baseline, candidate)]
    if left == right or not any(isinstance(memory, dict) and memory.get('lessons') for memory in (left, right)):
        return
    comparable_fields = ('lock_sha256', 'runner', 'data', 'project_path', 'submodules', 'harness_version', 'agent')
    differences = [field for field in comparable_fields
                   if field not in baseline or field not in candidate or baseline[field] != candidate[field]]
    if {k: v for k, v in baseline['config'].items() if k != 'memory'} != {
        k: v for k, v in candidate['config'].items() if k != 'memory'
    }:
        differences.append('config')
    # Capturing an identical tree deliberately produces unique checkpoint commits.
    # Legacy manifests have no verified tree identity: require the exact commit.
    if 'source_tree' in baseline and 'source_tree' in candidate:
        same_source = baseline['source_tree'] == candidate['source_tree']
    else:
        same_source = bool(baseline.get('commit')) and baseline.get('commit') == candidate.get('commit')
    if not same_source:
        differences.append('source')
    gate('memory_comparability', not differences, dict(differing_inputs=differences))
    try:
        memories = [validate_memory(memory) for memory in (left, right) if memory is not None]
        arena = normalize_arena(suite['arena_url'])
    except (ValueError, TypeError, KeyError):
        gate('memory_holdout', False, dict(reasons=['invalid_snapshot_or_scope']))
        return
    discovery = {name: {value for memory in memories for value in memory[name]}
                 for name in ('source_cases', 'source_suppliers', 'source_sessions')}
    reasons = set()
    if any(memory['arena_url'] != arena or memory['environment'] != suite['environment'] for memory in memories):
        reasons.add('discovery_scope_mismatch')
    cases = set(suite['cases'])
    if len(cases) < 2:
        reasons.add('fewer_than_two_cases')
    if cases & discovery['source_cases']:
        reasons.add('discovery_case_overlap')
    planned = {(arm, case, repeat) for arm in ('baseline', 'candidate') for case in cases
               for repeat in range(1, suite['repetitions'] + 1)}
    cohorts, sessions, suppliers = {}, set(), set()
    for attempt in attempts:
        cell = (attempt.get('arm'), attempt.get('case_id'), attempt.get('repeat'))
        if cell in cohorts or cell not in planned:
            reasons.add('unexpected_or_duplicate_attempt')
        cohort, failures = _original_cohort(attempt)
        reasons.update(failures)
        cohorts[cell] = cohort
        suppliers.update(cohort)
        session = attempt.get('session_id')
        if not identifier(session):
            reasons.add('unknown_session')
        elif session in sessions:
            reasons.add('duplicate_session')
        else:
            sessions.add(session)
        if session in discovery['source_sessions']:
            reasons.add('discovery_session_overlap')
    if set(cohorts) != planned:
        reasons.add('missing_planned_transcripts')
    if len(suppliers) < 3:
        reasons.add('fewer_than_three_suppliers')
    if suppliers & discovery['source_suppliers']:
        reasons.add('discovery_supplier_overlap')
    for case in cases:
        for repeat in range(1, suite['repetitions'] + 1):
            if cohorts.get(('baseline', case, repeat)) != cohorts.get(('candidate', case, repeat)):
                reasons.add('comparison_supplier_cohorts_differ')
    gate('memory_holdout', not reasons, dict(
        reasons=sorted(reasons), supplier_count=len(suppliers), case_count=len(cases),
        discovery_supplier_overlap=sorted(suppliers & discovery['source_suppliers']),
        discovery_case_overlap=sorted(cases & discovery['source_cases']),
        discovery_session_overlap=sorted(sessions & discovery['source_sessions']),
    ))


def _original_cohort(attempt):
    """Only immutable original outcomes establish a complete supplier cohort."""
    reasons = set()
    try:
        original = Outcome.model_validate(attempt.get('outcome')).model_dump()
    except (ValueError, TypeError):
        return set(), {'missing_original_outcome'}
    for key in ('attempt_id', 'checkpoint_id', 'session_id', 'status', 'result', 'threads', 'score', 'timeouts'):
        if original[key] != attempt.get(key):
            reasons.add('original_outcome_mismatch')
    if original['status'] != 'completed' or original['result'].get('ended') is not True:
        reasons.add('original_outcome_not_ended')
    result, threads = original['result'], original['threads']
    if result.get('session_id', original['session_id']) != original['session_id']:
        reasons.add('session_identity_mismatch')
    if result.get('case_id', attempt.get('case_id')) != attempt.get('case_id'):
        reasons.add('case_identity_mismatch')
    suppliers = set(threads)
    if not suppliers or any(not identifier(supplier) for supplier in suppliers):
        reasons.add('missing_supplier_transcripts')
    # The owned ended session response supplies the full roster, including losers.
    # Without it, an omitted thread cannot be distinguished from a complete cohort.
    roster = result.get('threads')
    if not isinstance(roster, dict) or not roster or set(roster) != suppliers:
        reasons.add('incomplete_supplier_roster')
    if result.get('supplier_id') is not None and result['supplier_id'] not in suppliers:
        reasons.add('selected_supplier_absent')
    for supplier, thread in threads.items():
        if isinstance(thread, dict):
            if thread.get('supplier_id', supplier) != supplier:
                reasons.add('thread_identity_mismatch')
            messages = thread.get('messages')
        else:
            messages = thread
        if (not isinstance(messages, list) or not messages
                or any(not isinstance(message, dict) for message in messages)
                or not any(supplier_author_matches(message.get('from'), supplier) for message in messages
                           if isinstance(message, dict))):
            reasons.add('missing_known_supplier_messages')
    return suppliers, reasons
