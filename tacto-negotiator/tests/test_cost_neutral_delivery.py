import json
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok, total_cost
from test_evaluator import msg

from negotiator.agent import PackageAgent
from negotiator.optimizer import best_terms
from negotiator.policy import PolicyConfig


def capacity():
    cases = json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
    return next(c for c in cases if c['case_id'] == 'case:P10')


def test_delivery_tie_preserves_complete_cost_and_changes_real_opening():
    case = capacity()
    legacy = best_terms(case, 32.2)
    candidate = best_terms(case, 32.2, prefer_longer_lead=True)
    assert legacy['lead_time_days'] == 35
    assert candidate == {**legacy, 'lead_time_days': 42}
    assert total_cost(case, candidate) == total_cost(case, legacy)
    sid = case['suppliers'][0]
    opening = {'unit_price': 32.2, 'lead_time_days': 54,
               'volume_per_year': 19890, 'contract_months': 12}
    agent = PackageAgent(policy=PolicyConfig(cost_neutral_lead_time=True))
    move = agent.propose(case, {sid: [msg('open', ('offer:0', opening))]}, sid)
    assert move['message']['term_sheets'][0]['terms']['lead_time_days'] == 42


def test_longer_delivery_never_adds_cost_or_breaks_a_must_have():
    case = capacity()
    case['buyer']['need_lead_time_days'] = 40
    assert best_terms(case, 32.2, prefer_longer_lead=True)['lead_time_days'] == 35
    case = capacity()
    case['buyer']['must_haves'].append({'field': 'lead_time_days', 'op': '<=', 'value': 35})
    chosen = best_terms(case, 32.2, prefer_longer_lead=True)
    assert chosen['lead_time_days'] == 35 and must_haves_ok(case, chosen)


def test_fixture_controls_without_negotiable_delivery_unchanged(tmp_path):
    cases = json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
    for case in cases:
        if 'lead_time_days' not in case['negotiable']:
            price = case['buyer']['current_unit_price'] or 30
            assert best_terms(case, price) == best_terms(case, price, prefer_longer_lead=True)
    config = {'version': 1, 'cost_neutral_lead_time': True}
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(config))
    assert PolicyConfig.load(path).cost_neutral_lead_time


@pytest.mark.parametrize("value", ["true", 1, None])
def test_delivery_flag_requires_boolean(tmp_path, value):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps({"version": 1, "cost_neutral_lead_time": value}))
    with pytest.raises(ValueError, match="must be boolean"):
        PolicyConfig.load(path)


def test_default_opening_unchanged_and_saved_config_adds_only_delivery_flag():
    case = capacity()
    sid = case["suppliers"][0]
    opening = {"unit_price": 32.2, "lead_time_days": 54,
               "volume_per_year": 19890, "contract_months": 12}
    for policy in (None, PolicyConfig()):
        move = PackageAgent(policy=policy).propose(case, {sid: [msg("open", ("offer:0", opening))]}, sid)
        assert move["message"]["term_sheets"][0]["terms"]["lead_time_days"] == 35
    base = json.loads(Path("configs/candidate.json").read_text())
    candidate = json.loads(Path("configs/cost-neutral-delivery.json").read_text())
    assert candidate == {**base, "cost_neutral_lead_time": True}
    policy = PolicyConfig.load("configs/cost-neutral-delivery.json")
    move = PackageAgent(policy=policy).propose(case, {sid: [msg("open", ("offer:0", opening))]}, sid)
    assert move["message"]["term_sheets"][0]["terms"]["lead_time_days"] == 42
