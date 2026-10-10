"""Objective post-run feedback. Read-only analysis; never promotes a policy or sends a move."""

from ..economics import InfeasiblePackage, evaluate
from ..ingestion import fingerprint


class FeedbackAgent:
    def review(self, run, cases=None):
        body = run.model_dump() if hasattr(run, "model_dump") else run
        findings = []

        def add(attempt, category, observation, next_test, supplier=None, message=None):
            ref = {"run_id": body["run_id"], "attempt_id": attempt["attempt_id"]}
            if supplier is not None:
                ref.update(supplier=supplier, message_index=message)
            findings.append({"category": category, "observation": observation, "next_test": next_test,
                             "evidence": [ref], "disposition": "proposed",
                             "confidence_basis": "recorded outcome or deterministic check; not causal proof"})

        for attempt in body["attempts"]:
            result = attempt.get("result") or {}
            if attempt["status"] != "completed":
                add(attempt, "change", "Original execution did not complete successfully.",
                    "Diagnose the original failure before comparing strategy scores.")
            if result.get("reconciled_result"):
                score = result["reconciled_result"].get("score")
                add(attempt, "recovery", f"Separate recovered outcome: score {score}; original status is unchanged.",
                    "Repeat recovery without operator assistance; do not promote from this recovered sample.")
            if attempt.get("timeouts") is None:
                add(attempt, "unknown", "Timeout evidence is unavailable.", "Collect owned thread timeout records.")
            elif attempt["timeouts"] > 0:
                add(attempt, "change", f"Recorded {attempt['timeouts']} thread timeouts.",
                    "Rehearse concurrent replies and server deadlines on the same runner.")
            elif attempt["status"] == "completed":
                add(attempt, "keep", "Completed with zero recorded thread timeouts.",
                    "Retain scheduling behavior; verify it under concurrent load.")
            if result.get("must_haves_ok") is False:
                add(attempt, "change", "The recorded deal violates must-haves.", "Recheck every closing path.")
            if result.get("must_haves_ok") is True:
                add(attempt, "keep", "The recorded deal satisfies must-haves.", "Retain complete-package guards.")
            uncovered = (result.get("cost_breakdown") or {}).get("uncovered_need")
            if isinstance(uncovered, (int, float)) and uncovered > 0:
                add(attempt, "test", f"Uncovered demand cost EUR {uncovered:.2f} in the result.",
                    "Compare feasible tenors/volumes over the same horizon; longer is not automatically better.")
            case = (cases or {}).get(attempt["case_id"])
            for sid, thread in (attempt.get("threads") or {}).items():
                messages = thread if isinstance(thread, list) else thread.get("messages", [])
                standing, standards = None, {}
                from arena_kit.docs import standard_terms

                for index, event in enumerate(messages):
                    standards = standard_terms(messages[:index + 1])
                    if event.get("from") != "buyer":
                        sheets = event.get("term_sheets") or []
                        standing = sheets[0].get("term_sheet_id") if sheets else None
                        if any(c.get("result") == "contradicted" for c in event.get("claim_results") or []):
                            add(attempt, "change", "Supplier response records a contradicted claim.",
                                "Recompute the source and suppress unsupported/rejected arguments.", sid, index)
                        continue
                    action = event.get("action") or {}
                    if action.get("type") == "accept" and action.get("term_sheet_id") != standing:
                        add(attempt, "change", "Acceptance did not reference the latest primary sheet.",
                            "Reconcile state and compare current primary offers before closing.", sid, index)
                    if case:
                        for sheet in event.get("term_sheets") or []:
                            try:
                                evaluate(case, sheet.get("terms") or {}, standards)
                            except InfeasiblePackage as exc:
                                add(attempt, "change", f"Invalid proposed package: {exc}.",
                                    "Validate the complete rounded payload before transmission.", sid, index)
        if body.get("source") == "imported":
            limitation = "Historical import: source/config may be unknown; not an eligible checkpoint comparison."
        else:
            limitation = "Descriptive feedback only. Test hypotheses in a paired campaign before promotion."
        return {"schema_version": 1, "run_id": body["run_id"], "source_sha256": fingerprint(body),
                "findings": findings, "limitation": limitation,
                "policy_changed": False, "model_calls": 0}


def review_store(store, cases=None):
    """Persist audits separately from immutable original attempts; safe to rerun after imports."""
    agent, reports = FeedbackAgent(), []
    for run in store.all():
        report = agent.review(run, cases)
        reports.append(report)
    import json

    with store._connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS feedback (source_sha256 TEXT PRIMARY KEY, run_id TEXT, body TEXT)")
        for report in reports:
            db.execute("INSERT OR IGNORE INTO feedback VALUES (?, ?, ?)",
                       (report["source_sha256"], report["run_id"], json.dumps(report, allow_nan=False)))
    recurring = {}
    for report in reports:
        for finding in report["findings"]:
            key = (finding["category"], finding["next_test"])
            item = recurring.setdefault(key, {"category": key[0], "next_test": key[1],
                                              "run_ids": set(), "evidence": []})
            item["run_ids"].add(report["run_id"])
            item["evidence"].extend(finding["evidence"])
    memory = [{**item, "run_ids": sorted(item["run_ids"]), "distinct_runs": len(item["run_ids"]),
               "status": "observations_only; not an approved runtime rule"}
              for item in recurring.values() if len(item["run_ids"]) > 1]
    return {"schema_version": 1, "runs": len(reports), "reports": reports, "shared_observations": memory}
