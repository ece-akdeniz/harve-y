"""Regenerate the expanded test manifest from executable assertions (offline collection)."""

import ast
import json
import subprocess
import sys
from pathlib import Path

OWNERS = {
    "test_hardening.py": "T1.1a/T1.1b/T1.1c hardening",
    "test_foundation.py": "T1.1a/T1.1b", "test_boundaries.py": "T1.1b",
    "test_guardrails.py": "T1.1c/T1.3", "test_evidence.py": "T2.1/T2.3",
    "test_preparation.py": "T2.2", "test_interpretation.py": "T3.2",
    "test_economics.py": "T4.1/T4.2", "test_selection.py": "T4.3/T4.4",
    "test_validation.py": "T5.1", "test_state.py": "T1.4/T5.2",
    "test_pipeline.py": "T1.2b/T1.4", "test_behavior.py": "T4.3",
    "test_recovery.py": "T5.2/T5.3/T5.4", "test_model_budget.py": "T3.2/T3.3",
}


def main():
    project = Path(__file__).resolve().parents[2]
    output = subprocess.check_output(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/v2"], cwd=project, text=True,
    )
    identifiers = [line for line in output.splitlines() if line.startswith("tests/v2/") and "::" in line]
    entries = []
    for identifier in identifiers:
        relative, name = identifier.split("::", 1)
        path = project / relative
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                        and node.name == name.split("[")[0])
        assertions = [ast.unparse(node.test) for node in ast.walk(function) if isinstance(node, ast.Assert)]
        raises = [ast.unparse(node) for node in ast.walk(function) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == "raises"]
        fixture_arguments = [argument.arg for argument in function.args.args if argument.arg != "request"]
        sources = []
        for argument in ("p10", "relationship"):
            if argument in fixture_arguments:
                sources.append(f"tests/fixtures/v2/{argument}.json")
        for node in ast.walk(function):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "read_fixture" and node.args
                    and isinstance(node.args[0], ast.Constant)):
                sources.append("tests/fixtures/v2/" + node.args[0].value)
        if not sources:
            sources.append("test-local controlled values and parametrization")
        entries.append({
            "test_id": identifier, "group": path.parent.name, "task": OWNERS[path.name],
            "fixture_arguments": fixture_arguments,
            "fixture_sources": sources,
            "assertions": assertions, "expected_exceptions": raises, "source_line": function.lineno,
            "failure_condition": "A specified assertion/exception expectation fails, unexpected error occurs, "
                                 "or an absent owning component is required by --v2-require.",
        })
    manifest = {
        "fixture_version": "negotiator-v2-fixtures/1", "contract_version": "negotiator-v2/1",
        "generated_from": "pytest collection and Python assertion AST; regenerate after test edits",
        "test_count": len(entries), "tests": entries,
    }
    (project / "tests/fixtures/v2/test-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(entries)} expanded test contracts.")


if __name__ == "__main__":
    main()
