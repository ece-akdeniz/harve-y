import json
from pathlib import Path

import pytest
from arena_kit.cost import total_cost

from negotiator.optimizer import best_terms
from negotiator.policy import PolicyConfig


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def test_longer_tenor_tie_keeps_cost():
    c = case("case:P07")
    legacy = best_terms(c, 5.4)
    longer = best_terms(c, 5.4, prefer_longer_tenor=True)
    assert total_cost(c, longer) == pytest.approx(total_cost(c, legacy), abs=1e-6)
    assert longer["contract_months"] >= legacy["contract_months"]


def test_configs_load_and_extend_candidate():
    base = json.loads(Path("configs/candidate.json").read_text())
    for name, key, val in (("p07-longer-tenor", "longer_tenor_types", ["bundling"]),
                           ("p01-standard-payment", "standard_payment_types", ["price_increase"])):
        assert json.loads(Path(f"configs/{name}.json").read_text()) == {**base, key: val}
        assert getattr(PolicyConfig.load(f"configs/{name}.json"), key) == tuple(val)


@pytest.mark.parametrize("key", ["longer_tenor_types", "standard_payment_types"])
def test_unknown_type_rejected(tmp_path, key):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"version": 1, key: ["nope"]}))
    with pytest.raises(ValueError):
        PolicyConfig.load(p)


def test_p01_standard_payment_opening_uses_quote_standard():
    from test_evaluator import msg

    from negotiator.agent import PackageAgent

    c = case("case:P01")
    sid = c["suppliers"][0]
    m0 = msg("open", ("offer:0", {"unit_price": 138.55, "effective_date": "2026-11-01"}))
    m0["attachments"] = [{"name": "quote-1.pdf",
                          "text": "Our standard terms\nPayment terms (days net) 30\nIncoterm FCA"}]
    terms = {}
    for cfg in ("configs/candidate.json", "configs/p01-standard-payment.json"):
        agent = PackageAgent(policy=PolicyConfig.load(cfg), claims=False)
        move = agent.propose(c, {sid: [m0]}, sid)
        terms[cfg] = move["message"]["term_sheets"][0]["terms"]
    assert terms["configs/candidate.json"]["payment_days"] == 90
    assert terms["configs/p01-standard-payment.json"]["payment_days"] == 30
    assert terms["configs/candidate.json"]["unit_price"] == terms["configs/p01-standard-payment.json"]["unit_price"]


def test_p07_evidence_config_only_adds_bundling():
    base = json.loads(Path("configs/candidate.json").read_text())
    cfg = json.loads(Path("configs/p07-evidence.json").read_text())
    assert cfg == {**base, "evidence_types": base["evidence_types"] + ["bundling"]}
    assert "bundling" in PolicyConfig.load("configs/p07-evidence.json").evidence_types


def test_anchor_by_type_only_moves_listed_type_opening():
    from test_evaluator import msg

    from negotiator.agent import PackageAgent

    c = case("case:P07")
    sid = c["suppliers"][0]
    events = {sid: [msg("open", ("offer:0", {"unit_price": 5.74, "payment_days": 30, "contract_months": 12}))]}
    base = PackageAgent(policy=PolicyConfig.load("configs/candidate.json"), claims=False)
    deep = PackageAgent(policy=PolicyConfig.load("configs/p07-deep-anchor.json"), claims=False)
    p_base = base.propose(c, events, sid)["message"]["term_sheets"][0]["terms"]["unit_price"]
    p_deep = deep.propose(c, events, sid)["message"]["term_sheets"][0]["terms"]["unit_price"]
    assert p_base == 5.05 and p_deep == 4.59
    q = case("case:P01")
    qs = q["suppliers"][0]
    qe = {qs: [msg("open", ("offer:0", {"unit_price": 138.55, "effective_date": "2026-11-01"}))]}
    assert base.propose(q, qe, qs) == deep.propose(q, qe, qs)


@pytest.mark.parametrize("value", [{"bundling": 0.5}, {"nope": 0.1}, {"bundling": "0.2"}])
def test_anchor_by_type_validation(tmp_path, value):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"version": 1, "anchor_by_type": value}))
    with pytest.raises(ValueError):
        PolicyConfig.load(p)
