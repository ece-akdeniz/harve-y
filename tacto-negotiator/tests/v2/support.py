"""Test-only bindings; absent components are the ONLY expected failure condition."""

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from tests.v2.builders import normalize_fixture

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v2"


def read_fixture(name):
    return json.loads((FIXTURES / name).read_text())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(request, suffix):
    name = "negotiator.v2." + suffix
    # Check files without importing V2 parents. A broken existing __init__ must fail, even if
    # its missing dependency happens to have the same name as a requested parent package.
    package = importlib.util.find_spec("negotiator")
    candidates = [Path(root) / "v2" / Path(*suffix.split(".")) for root in package.submodule_search_locations]
    exists = any(path.with_suffix(".py").is_file() or (path / "__init__.py").is_file() for path in candidates)
    if not exists:
        prefixes = request.config.getoption("--v2-require")
        if any(p == "all" or suffix == p or suffix.startswith(p + ".") for p in prefixes):
            pytest.fail(f"Required V2 component absent: {name}")
        pytest.xfail(f"UNIMPLEMENTED: {name}; remove this outcome by completing its owning task")
    # Existing modules with missing dependencies, missing symbols, or broken assertions fail normally.
    return importlib.import_module(name)


def inputs(request, fixture):
    module = require(request, "adapters.recorded")
    return module.load_inputs(normalize_fixture(fixture))


def terms_of(package):
    return {binding.field: binding.value for binding in package.bindings}


def codes(result):
    issues = result.issues if hasattr(result, "issues") else result.report.issues
    return {issue.code for issue in issues}


PORT_SIGNATURES = {
    "Clock": {"utcnow": (False, ""), "monotonic": (False, "")},
    "OfficialCostOracle": {"evaluate": (False, "case terms supplier")},
    "CanonicalClaimOracle": {"verify": (False, "candidate evidence recipient_id usage")},
    "ContextBuilder": {"build_context": (False, "prepared case server documents as_of")},
    "SupplierInterpreter": {"interpret": (True, "context conversation previous_assessment budget")},
    "StrategyProposalPolicy": {"propose_strategies": (True, "context assessment state budget research")},
    "CandidateGenerator": {"generate_candidates": (False, "intent context state budget")},
    "EconomicEvaluator": {
        "evaluate_package": (False, "package supplier_id context"),
        "evaluate_candidates": (False, "candidates context"),
    },
    "ActionSelectionPolicy": {"select_action": (True, "candidates assessment state budget research")},
    "CandidateResearch": {"evaluate_intents": (True, "intents budget")},
    "ClosingEvaluator": {"decide_close": (False, "context state reason_code")},
    "ClaimVerifier": {"verify": (False, "candidate evidence recipient_id usage")},
    "ActionRenderer": {"render": (False, "decision selected claims context")},
    "ActionValidator": {"validate_action": (False, "action context state budget")},
    "DecisionEngine": {"decide": (True, "snapshot")},
    "FeedbackProcessor": {"process_feedback": (False, "previous_state operation response")},
    "StateProjector": {"apply_event": (False, "state event")},
    "StateStore": {
        "load_state": (True, "run_id case_id"),
        "persist_state": (True, "expected_version commit"),
        "append_observations": (True, "expected_version events"),
        "pending_operations": (True, "run_id"),
    },
    "ActionExecutor": {
        "execute_action": (True, "action permit operation budget"),
        "reconcile": (True, "operation context state budget"),
    },
    "ArenaGateway": {
        "observe": (True, "session_id budget"),
        "submit": (True, "operation budget"),
        "fetch_document": (True, "session_id attachment_id budget"),
    },
    "ModelGateway": {"complete": (True, "request budget")},
}
