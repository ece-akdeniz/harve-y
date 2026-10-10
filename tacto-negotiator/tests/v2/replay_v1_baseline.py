"""Replay the frozen V1 first move from tracked source, without changing the checkout.

Run from tacto-negotiator: .venv/bin/python tests/v2/replay_v1_baseline.py
This uses the existing locked environment; it installs nothing and makes no service calls.
"""

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[2]
    repository = project.parent
    fixtures = project / "tests/fixtures/v2"
    manifest = json.loads((fixtures / "v1-baseline.json").read_text())
    revision = manifest["v1_revision"]
    for name, expected in manifest["tracked_file_sha256"].items():
        blob = subprocess.check_output(["git", "show", revision + ":" + name], cwd=repository)
        if hashlib.sha256(blob).hexdigest() != expected:
            raise ValueError(f"Frozen source mismatch: {name}")
    kit = subprocess.check_output(
        ["git", "rev-parse", revision + ":negotiation-arena-kit"], cwd=repository, text=True,
    ).strip()
    if kit != manifest["kit_revision"]:
        raise ValueError("Frozen kit revision mismatch")
    blob = subprocess.check_output(
        ["git", "archive", revision, "tacto-negotiator/src", "tacto-negotiator/configs",
         "tacto-negotiator/tests", "tacto-negotiator/pyproject.toml", "tacto-negotiator/uv.lock"],
        cwd=repository,
    )
    with tempfile.TemporaryDirectory(prefix="negotiator-v1-frozen-") as temporary:
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            archive.extractall(temporary, filter="data")
        archived_project = Path(temporary) / "tacto-negotiator"
        environment = {k: v for k, v in os.environ.items() if not k.startswith("NEGOTIATOR_")}
        environment["PYTHONPATH"] = str(archived_project / "src")
        # Only explicit fixture arguments enter the constructor; no dotenv/CLI/provider loader.
        program = """
import json, sys
from negotiator.agent import PackageAgent
fixture=json.load(open(sys.argv[1]))
baseline=json.load(open(sys.argv[2]))
config=dict(baseline['configuration'])
conditional=config.pop('conditional_exchange')
agent=PackageAgent(**config)
agent.conditional_exchange=conditional
sid=fixture['supplier_id']
result=agent.propose(fixture['case'], {sid:[fixture['opening']]}, sid)
assert result == baseline['expected_first_move'], (result, baseline['expected_first_move'])
print('Frozen V1 first move matches 3653046; no hosted or model calls.')
"""
        subprocess.run(
            [sys.executable, "-c", program, str(fixtures / "p10.json"), str(fixtures / "v1-baseline.json")],
            cwd=archived_project, env=environment, check=True,
        )


if __name__ == "__main__":
    main()
