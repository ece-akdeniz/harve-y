"""Opt-in levers of codex/score-push-small: multi-year tenor, fast payment, evidence after advice."""

import json
from pathlib import Path

import pytest
from arena_kit.cost import total_cost

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig
from negotiator.trades import TradePolicy


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def msg(status, *sheets):
    return {"from": "sales", "status": status, "body": "", "attachments": [{
        "name": "quote-1.pdf", "text": "Our standard terms\nPayment terms (days net) 30\nIncoterm FCA"}],
        "term_sheets": [{"term_sheet_id": i, "terms": t} for i, t in sheets]}


@pytest.mark.parametrize("key", ["multi_year_tenor_types", "fast_payment_types"])
def test_new_type_lists_validate(key):
    assert PolicyConfig().__getattribute__(key) == ()
    assert getattr(PolicyConfig.from_dict({"version": 1, key: ["renewal", "renewal"]}), key) == ("renewal",)
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, key: ["nope"]})


def test_evidence_after_advice_is_boolean():
    assert PolicyConfig().evidence_after_advice is False
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "evidence_after_advice": 1})


def test_multi_year_tenor_takes_longest_equal_cost_tenor():
    c = case("case:P04")
    sid = c["suppliers"][0]
    picks = {}
    for types in ((), ("renewal",)):
        policy = PolicyConfig(package_types=("renewal",), multi_year_tenor_types=types)
        trade = TradePolicy(policy, lambda *a, **k: None)
        trade.traits[sid] = {"multi_year_only"}
        picks[types] = trade.initial(c, sid, 4.96, 0.12, {}, None)
    assert picks[()]["contract_months"] == 24
    assert picks[("renewal",)]["contract_months"] == 36
    terms = {k: {**v, "unit_price": 4.94} for k, v in picks.items()}
    assert total_cost(c, terms[("renewal",)]) == pytest.approx(total_cost(c, terms[()]))


def test_multi_year_tenor_needs_trait():
    c = case("case:P04")
    sid = c["suppliers"][0]
    trade = TradePolicy(PolicyConfig(package_types=("renewal",), multi_year_tenor_types=("renewal",)),
                        lambda *a, **k: None)
    legacy = TradePolicy(PolicyConfig(package_types=("renewal",)), lambda *a, **k: None)
    trade.traits[sid] = legacy.traits[sid] = set()
    assert trade.initial(c, sid, 4.96, 0.12, {}, None) == legacy.initial(c, sid, 4.96, 0.12, {}, None)


def test_fast_payment_opening_and_note():
    c = case("case:P01")
    sid = c["suppliers"][0]
    m0 = msg("open", ("offer:0", {"unit_price": 138.55, "effective_date": "2026-11-01"}))
    base = {"version": 1, "standard_payment_types": ["price_increase"]}
    moves = {}
    for extra in ({}, {"fast_payment_types": ["price_increase"]}):
        agent = PackageAgent(policy=PolicyConfig.from_dict({**base, **extra}), claims=False)
        moves[bool(extra)] = agent.propose(c, {sid: [m0]}, sid)["message"]
    assert moves[False]["term_sheets"][0]["terms"]["payment_days"] == 30
    assert moves[True]["term_sheets"][0]["terms"]["payment_days"] == 14
    assert "doc:20260902-70110-M2" in moves[True]["body"] and "within 14 days" in moves[True]["body"]
    assert "cash discount" not in moves[False]["body"]


def test_fast_payment_needs_public_trait():
    c = case("case:P02")  # supplier 70510 has no fast-payment note
    sid = c["suppliers"][0]
    agent = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "fast_payment_types": ["price_increase"]}),
                         claims=False)
    assert agent._fast_payment(c, sid, {"unit_price": 380.0, "payment_days": 30}, {}) is None


def test_fast_payment_is_kept_against_free_payment_concession():
    c = case("case:P01")
    sid = c["suppliers"][0]
    agent = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "fast_payment_types": ["price_increase"]}),
                         claims=False)
    n = {"effective_date": "2027-04-01", "payment_days": 14}
    theirs = {"unit_price": 136.8, "effective_date": "2027-04-01", "payment_days": 30}
    assert agent._free_concessions(c, n, theirs, {}, None, sid)["payment_days"] == 14
    assert agent._free_concessions(c, n, theirs, {}, None)["payment_days"] == 30


def test_evidence_deferred_only_with_flag_and_advisor():
    c = case("case:P10")
    on = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                                    "evidence_after_advice": True}), claims=False)
    off = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"]}),
                       claims=False)
    on.package_advisor = off.package_advisor = object()
    assert on._defer_evidence(c) and not off._defer_evidence(c)
    on.package_advisor = None
    assert not on._defer_evidence(c)


SCREENS = {
    "p01-fast-payment": {"fast_payment_types": ["price_increase"]},
    "p04-multi-year-tenor": {"multi_year_tenor_types": ["renewal"]},
    "p10-capacity-evidence": {"evidence_types": ["capacity", "price_increase", "quality"],
                              "evidence_after_advice": True},
}


@pytest.mark.parametrize("name", sorted(SCREENS))
def test_screen_configs_extend_v2_by_one_lever(name):
    v2 = json.loads(Path("configs/score-push-v2.json").read_text())
    assert json.loads(Path(f"configs/{name}.json").read_text()) == {**v2, **SCREENS[name]}
    PolicyConfig.load(f"configs/{name}.json")
