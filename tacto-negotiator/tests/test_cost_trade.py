"""Case-data and cost guards for the one-session risk-sharing experiment."""
import copy
import json
import time
from pathlib import Path

from arena_kit.cost import closing_terms, total_cost

from negotiator.cost_trade import MARKER, propose
from negotiator.policy import PolicyConfig

CASES = {c['case_id']: c for c in json.loads(
    (Path(__file__).parent / 'fixtures/practice_cases.json').read_text())}


def setup():
    case = copy.deepcopy(CASES['case:P02'])
    terms = {'unit_price': 330, 'payment_days': 90, 'index_clause': None}
    events = [{'from': 'supplier', 'status': 'open', 'body': 'Our raw material costs rose.',
               'term_sheets': [{'term_sheet_id': 'current', 'terms': {**terms, 'unit_price': 374}}]}]
    return case, events, terms


def test_case_schema_and_least_cost_allowed_switch():
    case, events, terms = setup()
    actual, info = propose(case, events, terms, {}, None, time.time()+60)
    assert 'contract_months' not in case['negotiable'] and case['fixed_terms']['contract_months'] == 12
    assert info and info['considered'] == 3
    assert actual['index_clause'] in case['term_options']['index_clause']
    assert actual['index_clause']['deadband_pct'] == 5
    assert closing_terms(case, actual)['contract_months'] == 12
    assert closing_terms(case, actual)['volume_per_year'] == 6110
    assert total_cost(case, actual) <= total_cost(case, terms)
    costs = [total_cost(case, {**terms, 'index_clause': clause})
             for clause in case['term_options']['index_clause'] if clause]
    assert info['same_price_package_cost'] == min(costs)


def test_no_trigger_or_no_permitted_fields_keeps_schedule():
    case, events, terms = setup()
    events[0]['body'] = 'Thank you for the offer.'
    assert propose(case, events, terms, {}, None, time.time()+60) == (terms, None)
    events[0]['body'] = 'Your price is too low.'
    case['negotiable'] = ['unit_price', 'payment_days']
    assert propose(case, events, terms, {}, None, time.time()+60) == (terms, None)


def test_restart_marker_prevents_repeated_switches():
    case, events, terms = setup()
    events += [{'from': 'buyer', 'body': MARKER, 'term_sheets': [{'terms': terms}]},copy.deepcopy(events[0])]
    assert propose(case, events, terms, {}, None, time.time()+60) == (terms, None)


def test_deadline_final_and_estimate_guards():
    case, events, terms = setup()
    assert propose(case, events, terms, {}, None, time.time()+19) == (terms, None)
    assert propose(case, events, terms, {}, {'uncertain': True}, time.time()+60) == (terms, None)
    events[0]['status'] = 'final_offer'
    assert propose(case, events, terms, {}, None, time.time()+60) == (terms, None)


def test_rival_cost_cap_is_preserved():
    case, events, terms = setup()
    cap = total_cost(case, {**terms,'unit_price':329})
    actual, info = propose(case, events, terms, {}, None, time.time()+60, cap)
    assert info and total_cost(case, actual) < cap


def test_hosted_config_refusal_off_and_factory_validates():
    from negotiator.agent import configured_agent
    path = Path(__file__).parents[1] / 'configs/p02-cost-driver-screen.json'
    config = json.loads(path.read_text())
    policy = PolicyConfig.load(path)
    assert policy.refusal_types == () and policy.response_types == ()
    assert policy.cost_trade_types == ('price_increase',)
    assert configured_agent(config, estimates={}, meso=False).policy == policy
