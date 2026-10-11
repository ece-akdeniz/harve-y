"""Verify/export original tracked simulator evidence, optionally enrich its Lab metadata.

No model calls, Arena operations or network publication. Original snapshots are retained.
"""

import argparse
import json
from pathlib import Path

from negotiator.lab.publish import _atomic_file, load_snapshots, save_snapshot
from negotiator.lab.store import Store
from negotiator.v2.core.lab_evidence import decision_evidence
from negotiator.v2.orchestration.offline import OfflineDecisionTrace


def export(root, *, enrich=False):
    rows, transcript = [], []
    store = Store(root / "lab.sqlite3")
    for path, run in load_snapshots(root / "runs"):
        directory = root / "traces" / run.run_id
        traces = [
            OfflineDecisionTrace.model_validate_json(p.read_bytes())
            for p in sorted(directory.glob("*/decision-*.json"))
        ]
        for trace in traces:
            trace.verify()
        terminal = json.loads(next(directory.glob("*/terminal-observation.json")).read_text())
        evidence = {
            "scope": "original admitted stage outputs; no rejected raw responses",
            "decisions": [decision_evidence(trace) for trace in traces],
        }
        if enrich and "agent_evidence" not in run.attempts[0].result:
            originals = root / "originals"
            originals.mkdir(exist_ok=True, mode=0o700)
            _atomic_file(originals / (run.run_id + ".json"), path.read_text())
            run.attempts[0].result["agent_evidence"] = evidence
            run.revision += 1
            save_snapshot(run, root / "runs")
        store.upsert(run)
        attempt = run.attempts[0]
        proposals = [json.loads(trace.validated_message_bytes) for trace in traces]
        rows.append(
            {
                "run_id": run.run_id,
                "arm": run.config["arm"],
                "environment": run.environment,
                "status": run.status,
                "rounds": attempt.rounds,
                "result": attempt.result,
                "terminal": terminal["terminal"],
                "proposals": proposals,
                "verified_decision_count": len(traces),
            }
        )
        transcript.append(
            {
                "run_id": run.run_id,
                "environment": run.environment,
                "official_threads": attempt.threads,
                "terminal": terminal,
                "stage_results": evidence,
                "original_decisions": [json.loads(trace.model_dump_json()) for trace in traces],
            }
        )
    ids = {row["arm"]: row["run_id"] for row in rows}
    proof = {
        "scope": "local existing Lab Store; remote publication requires separate proof",
        "listing": store.listing(),
        "retrievable_ids": [row["run_id"] for row in rows],
        "retrieval_verified": all(store.get(row["run_id"]) is not None for row in rows),
        "comparison": store.comparison(ids["minimum"], ids["adaptive"]),
    }
    report = {
        "scope": "scripted integration control; not genuine hosted LLM performance or online negotiation",
        "hosted_calls": 0,
        "online_sessions": 0,
        "runs": rows,
        "local_lab_proof": proof,
    }
    _atomic_file(root / "complete-transcript.json", json.dumps(transcript, indent=2))
    _atomic_file(root / "milestone-report.json", json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--enrich", action="store_true")
    args = parser.parse_args()
    report = export(args.root, enrich=args.enrich)
    print(json.dumps({"runs": len(report["runs"]), "local_retrieval": report["local_lab_proof"]["retrieval_verified"]}))


if __name__ == "__main__":
    main()
