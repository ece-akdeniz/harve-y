"""Tracked local Lab -> V2 -> official Sim demonstration; no network or hosted inference.

.venv/bin/python experiments/v2/run_lab_local.py --out /tmp/v2-lab-stabilization
"""

import argparse
import json
from pathlib import Path

from negotiator.lab.cli import main as lab_main
from negotiator.lab.publish import load_snapshots
from negotiator.v2.orchestration.offline import OfflineDecisionTrace

PROJECT = Path(__file__).resolve().parents[2]
DATASET = PROJECT / "experiments/v2/p10-offline-input.json"




def run_local(out, *, arms=("minimum", "direct", "grounded")):
    out = Path(out)
    dataset = json.loads(DATASET.read_text())
    out.mkdir(parents=True, exist_ok=True)
    case_file = out / "case.json"
    case_file.write_text(json.dumps(dataset["case"]))
    summaries = []
    for arm in arms:
        before = {r.run_id for _, r in load_snapshots(out / "runs")}
        config = {"dataset_path": str(DATASET), "trace_root": str(out / "traces"), "arm": arm,
                  "closing_authority": True}
        exit_code = lab_main([
            "run", "--name", f"V2 local {arm}", "--author", "local-verification",
            "--hypothesis", "Tracked Lab drives V2 and retrieves official Sim outcomes.",
            "--agent", "negotiator.v2.factory:local_lab_agent", "--config", json.dumps(config),
            "--cases", dataset["case"]["case_id"], "--repetitions", "1", "--max-sessions", "1",
            "--environment", "simulator", "--local-case", str(case_file), "--allow-dirty",
            "--repo", str(PROJECT), "--data", str(PROJECT / "tests/fixtures/v2"),
            "--root", str(out / "runs"),
        ])
        restored = next(r for _, r in load_snapshots(out / "runs") if r.run_id not in before)
        if exit_code and restored.status == "completed":
            raise ValueError("Lab CLI result and persisted status disagree")
        final = restored
        attempt = restored.attempts[0]
        paths = sorted((out / "traces" / final.run_id).glob("*/decision-*.json"))
        for path in paths:
            trace = OfflineDecisionTrace.model_validate_json(path.read_bytes())
            trace.verify()
        summaries.append({"arm": arm, "run_id": final.run_id, "status": restored.status,
                          "session_id": attempt.session_id, "rounds": attempt.rounds, "score": attempt.score,
                          "deal": attempt.result.get("deal"), "end_reason": attempt.result.get("end_reason"),
                          "buyer_cost": attempt.result.get("c_deal"), "traces_verified": len(paths),
                          "metrics": attempt.result.get("agent_metrics"), "error": attempt.error})
    report = {"evidence": "local official Sim outcomes with explicitly scripted model responses",
              "hosted_calls": 0, "remote_writes": 0, "runs": summaries,
              "claim_scope": "integration/reliability only; no model superiority or semantic reliability claim"}
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run_local(args.out)
    print(json.dumps({"report": str(args.out / "report.json"), "runs": [
        {k: r[k] for k in ("arm", "run_id", "status", "rounds", "deal", "traces_verified", "error")}
        for r in report["runs"]]}, indent=2))
    if any(r["status"] != "completed" for r in report["runs"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
