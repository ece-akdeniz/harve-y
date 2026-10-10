"""Offline expected-C report: feature-gated on the relationship term, no hidden data."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("expected_cost_report", ROOT / "tools/expected_cost_report.py")
rep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rep)
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
EST = {"standard": {"payment_days": 30, "incoterm": "DAP", "lead_time_days": 35}, "interest_rate": 0.08,
       "usual_rate": 0.08, "full_cost": 374.95, "full_cost_range": (356.2, 393.7), "ppm": 273}


def test_leverage_case_has_no_relationship_term(monkeypatch):
    monkeypatch.setattr(rep, "supplier_estimate", lambda case, sid: None)
    assert rep.report(CASES["case:P18"])["note"] == "no relationship term"


def test_relationship_case_reports_clause_target(monkeypatch):
    monkeypatch.setattr(rep, "supplier_estimate", lambda case, sid: EST)
    out = rep.report(CASES["case:P02"])
    assert out["clause"]["terms"]["index_clause"]["deadband_pct"] == 5
    assert out["any"]["expected_c"] <= out["clause"]["expected_c"]
