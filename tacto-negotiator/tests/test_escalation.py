import json
from pathlib import Path

import pytest
from test_evaluator import msg, ours

from negotiator import escalation
from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig


def test_request_only_beyond_band():
    assert escalation.request(2, 433.08, 430.0) is None  # 0.7 % is within the band
    text = escalation.request(2, 433.08, 404.61)
    assert "6.6 %" in text and "2 %" in text and "pricing committee" in text
    assert escalation.request(None, 433.08, 400.0) is None
    assert escalation.request(2, 433.08, 440.0) is None


def test_policy_field_is_opt_in():
    assert PolicyConfig.from_dict({"version": 1}).committee_escalation_types == ()
    cfg = PolicyConfig.from_dict({"version": 1, "committee_escalation_types": ["renewal"]})
    assert cfg.committee_escalation_types == ("renewal",)
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "committee_escalation_types": ["x"]})


@pytest.fixture(scope="module")
def p03():
    data = json.loads(Path("tests/fixtures/practice_cases.json").read_text())
    return next(c for c in data if c["case_id"] == "case:P03")


def _events(*prices):
    terms = {"unit_price": 0, "payment_days": 90, "contract_months": 24, "volume_per_year": 4580}
    events = [msg("open", ("o:0", {**terms, "unit_price": 438.21, "payment_days": 30, "contract_months": 12}))]
    for i, p in enumerate(prices, 1):
        events += [ours({**terms, "unit_price": 380.0 + 10 * i}), msg("open", (f"o:{i}", {**terms, "unit_price": p}))]
    return events


def _body(agent, case, events, monkeypatch, threshold=2.0):
    from negotiator import bundle_volume, dossiers

    monkeypatch.setattr(dossiers, "load_package", lambda *a, **k: None)
    monkeypatch.setattr(dossiers, "build_one", lambda *a, **k: None)
    monkeypatch.setattr(bundle_volume, "committee_threshold", lambda d: threshold)
    sid = case["suppliers"][0]
    move = agent.propose(case, {sid: events}, sid)
    return move["message"]["body"]


def test_agent_escalates_only_when_supplier_holds(p03, monkeypatch):
    on = PackageAgent(policy=PolicyConfig(package_types=("renewal",), committee_escalation_types=("renewal",)))
    assert "pricing committee" in _body(on, p03, _events(433.08, 433.08), monkeypatch)
    on = PackageAgent(policy=PolicyConfig(package_types=("renewal",), committee_escalation_types=("renewal",)))
    assert "pricing committee" not in _body(on, p03, _events(436.0, 433.08), monkeypatch)
    off = PackageAgent(policy=PolicyConfig(package_types=("renewal",)))
    assert "pricing committee" not in _body(off, p03, _events(433.08, 433.08), monkeypatch)
