"""Objective post-run feedback. Read-only analysis; never promotes a policy or sends a move."""

from ..economics import InfeasiblePackage, evaluate
from ..ingestion import fingerprint


class FeedbackAgent:
    def review(self, run, cases=None, memory=None, data_sha256=None, public_graph=None):
        body = run.model_dump() if hasattr(run, "model_dump") else run
        findings, memory_context, current_data_context = [], [], []
        data_matches = bool(data_sha256 and data_sha256 == (body.get("provenance") or {}).get("data_sha256"))
        public_nodes = (public_graph or {}).get("nodes", []) if data_matches else []

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
            case = (cases or {}).get(attempt["case_id"]) if data_matches else None
            for sid, thread in (attempt.get("threads") or {}).items():
                related = [node for node in public_nodes if node["kind"] == "public_fact"
                           and sid in {node["data"].get("supplier"), node["data"].get("supplier_id")}]
                if related:
                    current_data_context.append({"supplier_id": sid, "attempt_id": attempt["attempt_id"],
                                                 "source_ids": sorted(n["provenance"]["source_id"] for n in related),
                                                 "data_sha256": related[0]["provenance"]["data_sha256"],
                                                 "limitation": "Current public facts; not past conversation memory."})
                if memory is not None:
                    prior = memory.supplier_history(body, sid, purpose="feedback")
                    memory_context.append({"supplier_id": sid, "attempt_id": attempt["attempt_id"],
                                           "prior_attempt_ids": [n["id"] for n in prior],
                                           "evidence": [n["provenance"] for n in prior],
                                           "limitation": "Prior observations; not causal proof or current facts."})
                    failed = [n for n in prior if n["data"]["status"] == "failed"]
                    if failed:
                        add(attempt, "test", f"Shared memory contains {len(failed)} earlier failed attempts "
                            f"with {sid} in the same data version.",
                            "Compare failure causes before attributing repeated failures to supplier behavior.", sid)
                        findings[-1]["evidence"].extend(n["provenance"] for n in failed)
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
                                add(attempt, "test", f"Offer fails the matched public package check: {exc}.",
                                    "Check session overrides, then validate the complete rounded payload.", sid, index)
        if body.get("source") == "imported":
            limitation = "Historical import: source/config may be unknown; not an eligible checkpoint comparison."
        else:
            limitation = "Descriptive feedback only. Test hypotheses in a paired campaign before promotion."
        return {"schema_version": 1, "run_id": body["run_id"], "source_sha256": fingerprint(body),
                "findings": findings, "limitation": limitation,
                "policy_changed": False, "model_calls": 0, "memory_context": memory_context,
                "current_data_context": current_data_context,
                "package_validation": "matched public data; session overrides unknown" if data_matches else
                "skipped: no matching historical data fingerprint"}


def review_store(store, cases=None, data_sha256=None, package=None):
    """Persist audits separately from immutable original attempts; safe to rerun after imports."""
    from .knowledge import SnapshotMemory, export_graph

    agent, reports = FeedbackAgent(), []
    runs = store.all()
    graph = export_graph(runs, package=package)
    memory = SnapshotMemory(graph)
    for run in runs:
        report = agent.review(run, cases, memory, data_sha256, graph)
        reports.append(report)
    import json

    with store._connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS feedback (source_sha256 TEXT PRIMARY KEY, run_id TEXT, body TEXT)")
        for report in reports:
            db.execute("INSERT OR REPLACE INTO feedback VALUES (?, ?, ?)",
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


def review_one(store, run_id):
    """Refresh a terminal run's descriptive feedback after an accepted lab upload."""
    import json

    from .knowledge import SnapshotMemory, export_graph

    runs = store.all()
    run = next((item for item in runs if item.run_id == run_id), None)
    if run is None or run.status not in {"completed", "failed", "interrupted"}:
        return None
    report = FeedbackAgent().review(run, memory=SnapshotMemory(export_graph(runs)))
    with store._connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS feedback (source_sha256 TEXT PRIMARY KEY, run_id TEXT, body TEXT)")
        db.execute("INSERT OR REPLACE INTO feedback VALUES (?, ?, ?)",
                   (report["source_sha256"], report["run_id"], json.dumps(report, allow_nan=False)))
    return report
