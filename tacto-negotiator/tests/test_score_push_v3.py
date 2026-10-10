"""score-push-v3: P01 fast payment (from codex/score-push-small) + P11 value swap config."""

import json
from pathlib import Path

import pytest

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def msg(status, *sheets):
    return {"from": "sales", "status": status, "body": "", "attachments": [{
        "name": "quote-1.pdf", "text": "Our standard terms\nPayment terms (days net) 30\nIncoterm FCA"}],
        "term_sheets": [{"term_sheet_id": i, "terms": t} for i, t in sheets]}


def test_fast_payment_types_validate():
    assert PolicyConfig().fast_payment_types == ()
    assert PolicyConfig.from_dict({"version": 1, "fast_payment_types": ["renewal", "renewal"]}).fast_payment_types \
        == ("renewal",)
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "fast_payment_types": ["nope"]})


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


def test_v3_config_is_v2_plus_validated_levers_only():
    v2 = json.loads(Path("configs/score-push-v2.json").read_text())
    v3 = json.loads(Path("configs/score-push-v3.json").read_text())
    expected = {k: v for k, v in v2.items() if k != "preferences"}
    expected.update(fast_payment_types=["price_increase"], value_swap_types=["quality"],
                    value_swap_holds=1, value_swap_split=0.5)
    assert v3 == expected
    assert json.loads(Path("configs/score-push-v3-run.json").read_text())["policy_config"] == v3
    assert json.loads(Path("configs/p01-fast-payment.json").read_text()) == {
        **v2, "fast_payment_types": ["price_increase"]}
    PolicyConfig.load("configs/score-push-v3.json")
