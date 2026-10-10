import copy
import json
import time
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok, total_cost
from test_evaluator import RFQ, msg, ours

from negotiator.agent import PackageAgent
from negotiator.claims import build_bank, verify
from negotiator.dossiers import load_package
from negotiator.policy import PolicyConfig
from negotiator.report import summarise
from negotiator.trace import Tracer
from negotiator.trades import TradePolicy, history


@pytest.fixture(scope="module")
def cases():
    path = Path("data/package")
    candidates = list(path.rglob("practice_cases.json"))
    if candidates:
        data = json.loads(candidates[0].read_text())
    else:
        saved = Path("tests/fixtures/practice_cases.json")
        if not saved.exists():
            pytest.skip("practice package not installed")
        data = json.loads(saved.read_text())
    return {c["case_id"]: c for c in data}


def test_all_nineteen_claim_banks(cases):
    p = load_package()
    assert len(cases) == 19
    for c in cases.values():
        bank = build_bank(c, p)
        assert bank
        assert all(verify(x, p.facts | (c.get("facts") or {})) for x in bank)
    assert any(x.kind == "scorecard_ppm" for x in build_bank(cases["case:P11"], p))
    assert not any(x.kind == "notice" for x in build_bank(cases["case:P04"], p))


def test_initial_multiyear_and_quality(cases):
    config = PolicyConfig(package_types=("renewal", "quality"))
    agent = PackageAgent(policy=config)
    for cid, opening in [
        ("case:P04", {"unit_price": 4.96, "payment_days": 30, "contract_months": 12}),
        ("case:P11", {"unit_price": 47, "ppm_commitment": 6400}),
    ]:
        c = cases[cid]
        sid = c["suppliers"][0]
        proposal = agent.propose(c, {sid: [msg("open", ("o:0", opening))]}, sid)
        t = proposal["message"]["term_sheets"][0]["terms"]
        assert set(t) == set(c["negotiable"]) and must_haves_ok(c, t)
        if cid == "case:P04":
            assert t["contract_months"] == 24 and "volume_per_year" not in t
        else:
            assert t["ppm_commitment"] == 1500 and t["chargeback_eur_per_complaint"] == 500
            assert "payment_days" not in t and "faster payment" not in proposal["message"]["body"]


def test_stagnation_switch_equivalent_cost_and_deadline():
    c = copy.deepcopy(RFQ)
    sid = "sup:J"
    t = {"unit_price": 15.7, "payment_days": 60, "lead_time_days": 21, "incoterm": "DAP"}
    events = [msg("open", ("o:0", t)), ours(t), msg("open", ("o:1", t)), ours(t), msg("open", ("o:2", t))]
    events[-1]["body"] = "Faster payment is welcome."
    policy = TradePolicy(PolicyConfig(package_types=("rfq",)), lambda *a, **kw: None)
    policy.deadlines[sid] = time.time() + 60
    new, reason = policy.switch(c, sid, events, t, {}, None)
    assert reason and new["payment_days"] < t["payment_days"]
    assert total_cost(c, new) <= total_cost(c, t) + 0.01
    # The journal's previous proposals reconstruct switch count after restart.
    events += [ours(new), msg("open", ("o:3", new)), ours({**new, "payment_days": 14})]
    assert history(c, events)[2] == 2
    assert policy.switch(c, sid, events, new, {}, None)[1] is None
    policy.deadlines[sid] = time.time() + 19
    assert policy.switch(c, sid, events[:5], t, {}, None)[1] is None


def test_final_proxy_own_alternative_and_budget():
    c = copy.deepcopy(RFQ)
    c["buyer"]["alternative"] = {"kind": "none", "terms": {}}
    sid = "sup:J"
    base = {"unit_price": 20, "payment_days": 30, "lead_time_days": 21, "incoterm": "DAP"}
    events = [
        msg("open", ("o:0", base)),
        ours({**base, "unit_price": 15}),
        msg("final_offer", ("o:1", {**base, "unit_price": 19}), ("o:1-a", {**base, "unit_price": 16})),
    ]
    agent = PackageAgent(policy=PolicyConfig(final_offer_risk="opening_proxy"))
    move = agent.propose(c, {sid: events}, sid)
    assert move["message"]["term_sheets"][0]["terms"]["unit_price"] == 16
    events += [ours(move["message"]["term_sheets"][0]["terms"]), events[-1]]
    assert PackageAgent(policy=agent.policy).propose(c, {sid: events}, sid).get("close")
    # Tiny gain relative to losing a much improved deal must not trigger a counter.
    events = [
        msg("open", ("o:0", {**base, "unit_price": 30})),
        ours(base),
        msg("final_offer", ("o:1", base), ("o:1-a", {**base, "unit_price": 19.99})),
    ]
    assert PackageAgent(policy=agent.policy).propose(c, {sid: events}, sid).get("close")


def test_unknown_timeouts_and_incomplete_result(tmp_path):
    tr = Tracer(tmp_path)
    tr.log("result", case="case:T", result={"deal": True, "score": 0.5})
    s = summarise(tmp_path)
    assert s["cases"]["case:T"]["timeouts"] is None
    assert s["aggregate"]["timeouts_unknown_cases"] == 1
    tr.log("result", case="case:U", result={})
    assert "case:U" in summarise(tmp_path)["aggregate"]["failures"]


def test_policy_roundtrip_and_validation(tmp_path):
    p = tmp_path / "p.json"
    p.write_text('{"version":1,"package_types":["quality"]}')
    cfg = PolicyConfig.load(p)
    assert cfg.package_types == ("quality",)
    assert cfg.record()["sha256"] == PolicyConfig.load(p).record()["sha256"]
    p.write_text('{"version":1,"unknown":true}')
    with pytest.raises(ValueError):
        PolicyConfig.load(p)


def test_cli_fails_incomplete_result(monkeypatch, tmp_path):
    from negotiator import cli

    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "_run_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "run_async", lambda *a: {"case:X": RuntimeError("broken")})
    monkeypatch.setenv("ARENA_URL", "http://localhost:1")
    assert cli.main(["play", "case:X", "--runner", "async"]) == 1


def test_notice_corruption_preserves_other_claims(cases):
    package = load_package()
    case = cases['case:P01']
    for value in (None, 'not-a-number'):
        damaged = copy.copy(package)
        damaged.facts = copy.deepcopy(package.facts)
        changed = copy.deepcopy(case)
        for facts in (damaged.facts, changed.get('facts', {})):
            for ref, row in facts.items():
                if ref.startswith('doc:') and isinstance(row, dict) and 'days' in row:
                    row['days'] = value
        bank = build_bank(changed, damaged)
        assert any(c.kind == 'index_change' for c in bank)
        assert not any(c.kind == 'notice' for c in bank)


def test_multiyear_keeps_quoted_annual_volume(cases):
    case = cases['case:P03']
    sid = case['suppliers'][0]
    trade = TradePolicy(PolicyConfig(package_types=('renewal',)), lambda *a, **kw: None)
    trade.traits[sid] = {'multi_year_only'}
    volume = case['term_options']['volume_per_year'][0]
    result = trade.initial(case, sid, 200, 0.12, {}, None, reference={'volume_per_year': volume})
    assert result['volume_per_year'] == volume
    assert result['contract_months'] >= 12 * case['buyer']['horizon_years']
