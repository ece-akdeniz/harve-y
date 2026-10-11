"""Print a deterministic byte manifest for the local V6 supplier intelligence candidate."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "279f7a8348f4f94f0de650cb5f990aeaff794ab4"
PATHS = (
    "src/negotiator/advice.py", "src/negotiator/assessment.py",
    "src/negotiator/questions.py", "src/negotiator/final_review.py",
    "src/negotiator/final_advice.py", "src/negotiator/strategy_advisor.py",
    "src/negotiator/supplier_briefs.py", "src/negotiator/skill_docs.py",
    "src/negotiator/message_prose.py", "src/negotiator/response_writer.py",
    "src/negotiator/model_budget.py", "src/negotiator/validation_repair.py",
    "src/negotiator/decision_contract.py",
    "src/negotiator/cli.py",
    "src/negotiator/skills/negotiation/SKILL.md",
    "src/negotiator/skills/final/SKILL.md",
    "src/negotiator/skills/validation/SKILL.md",
    "src/negotiator/skills/brief/SKILL.md",
    "src/negotiator/skills/response/SKILL.md",
    "src/negotiator/agent.py", "src/negotiator/fixed_volume.py",
    "src/negotiator/lab/feedback.py", "src/negotiator/model_assist.py",
    "src/negotiator/package_advisor.py", "src/negotiator/play.py",
    "src/negotiator/policy.py", "src/negotiator/runner.py",
    "configs/score-push-v6.json", "configs/score-push-v6-guarded.json",
    "configs/score-push-v6-shadow.json", "configs/score-push-v6-select.json",
    "configs/score-push-v6-questions.json", "configs/score-push-v6-final-review.json",
    "configs/score-push-v6-final-advice.json",
    "configs/score-push-v6-final-explore.json",
    "configs/score-push-v6-strategy.json", "configs/score-push-v6-briefed.json",
    "configs/score-push-v6-skilled.json",
    "configs/score-push-v6-all-cases.json",
    "tests/test_assessment.py", "tests/test_capacity_advice.py",
    "tests/test_questions.py", "tests/test_final_review.py", "tests/test_final_advice.py",
    "tests/test_generalization_hardening.py", "tests/test_lab_learning.py",
    "tests/test_package_advisor.py", "tests/test_strategy_advisor.py",
    "tests/test_supplier_briefs.py", "tests/test_response_writer.py",
    "tests/test_model_budget.py", "tests/test_validation_repair.py",
    "tests/test_decision_contract.py", "tools/release_check.py",
    "scripts/fingerprint_v6_candidate.py",
)


def manifest():
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PATHS}
    identity = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    patch = subprocess.run(["git", "diff", "--binary", "HEAD", "--", "."], cwd=ROOT,
                           check=True, capture_output=True).stdout
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "."],
                            cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    dependencies = ROOT / "uv.lock"
    data_paths = ("data/package/facts.json", "data/release-sunday/data/news.csv")
    return {"schema_version": 1, "status": "local_candidate_not_provider_frozen",
            "base_commit": BASE, "candidate_identity": identity, "files": files,
            "tracked_diff_sha256": hashlib.sha256(patch).hexdigest(),
            "dirty_path_count": len(status),
            "untracked_path_count": sum(row.startswith("??") for row in status),
            "runtime_file_count": sum(p.is_file() and p.name != ".gitkeep"
                                      for p in (ROOT / "experiments/runs").rglob("*")),
            "dependency_lock_sha256": hashlib.sha256(dependencies.read_bytes()).hexdigest(),
            "data_files": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                           for name in data_paths if (ROOT / name).is_file()},
            "model_settings": {name: os.environ.get(name) for name in
                               ("LLM_PROVIDER", "LLM_MODEL", "LLM_EFFORT",
                                "VALIDATION_LLM_MODEL", "VALIDATION_LLM_EFFORT")}}


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=2))
