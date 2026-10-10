"""Complete-sample comparison policy; narrative findings never affect eligibility."""

import math
import statistics


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
