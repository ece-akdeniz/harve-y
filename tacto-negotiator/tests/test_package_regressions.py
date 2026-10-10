import json
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok, total_cost

from negotiator.agent import PackageAgent
from negotiator.optimizer import best_terms, trade_packages
from negotiator.supplier_costs import estimated_cost


def case(name):
    return json.loads((Path(__file__).parent / 'fixtures/package_cases.json').read_text())['cases']['case:' + name]


def thread(c, offers, status='open'):
    return {c['suppliers'][0]: [{'from': 'sales', 'status': status, 'attachments': [],
                               'term_sheets': [{'term_sheet_id': f'offer:{i}', 'terms': t}
                                               for i, t in enumerate(offers)]}]}


@pytest.mark.parametrize(('name', 'price'), [('P04', 4.96), ('P08', 6.05)])
def test_first_package_uses_our_price_not_opening_price(name, price):
    c = case(name)
    move = PackageAgent().decide(c, thread(c, [{'unit_price': price, 'contract_months': 12}]))
    assert move['message']['term_sheets'][0]['terms']['contract_months'] == 24


@pytest.mark.parametrize('name', ['P10', 'P18'])
def test_final_offer_accepts_actual_package_without_counter(name):
    c = case(name)
    if name == 'P10':
        offers = [{'unit_price': 35.1, 'lead_time_days': 35, 'volume_per_year': 23400, 'contract_months': 24},
                  {'unit_price': 32.1, 'lead_time_days': 54, 'volume_per_year': 23400, 'contract_months': 24}]
    else:
        offers = [{'unit_price': 5.5, 'payment_days': 90, 'contract_months': 24,
                   'index_clause': c['term_options']['index_clause'][1]}]
    move = PackageAgent().decide(c, thread(c, offers, 'final_offer'))['message']
    assert move['action'] == {'type': 'accept', 'term_sheet_id': 'offer:1' if name == 'P10' else 'offer:0'}
    assert 'term_sheets' not in move


def test_closing_checks_all_sheets_before_discarding_supplier():
    c = case('P11')
    offers = [{'unit_price': 1, 'ppm_commitment': 6400}, {'unit_price': 48, 'ppm_commitment': 1500}]
    move = PackageAgent().decide(c, thread(c, offers, 'agreed'))
    assert move['message']['action']['term_sheet_id'] == 'offer:1'


def test_quality_tradeoffs_keep_fixed_payment_and_match_cost():
    c = case('P11')
    primary = best_terms(c, 43)
    assert primary['ppm_commitment'] == 1500
    packages = trade_packages(c, primary)
    assert len(packages) > 1
    assert any(p['chargeback_eur_per_complaint'] < 500 for p in packages)
    for p in packages:
        assert set(p) == set(c['negotiable'])
        assert 'payment_days' not in p
        assert must_haves_ok(c, p)
        assert total_cost(c, p) <= total_cost(c, primary) + 0.01


def test_open_counter_preserves_supplier_index_clause():
    c = case('P18')
    offered = {'unit_price': 5.7, 'payment_days': 90, 'contract_months': 24,
               'index_clause': c['term_options']['index_clause'][1]}
    threads = thread(c, [offered])
    sid = c['suppliers'][0]
    threads[sid].insert(0, {'from': 'buyer', 'term_sheets': [{'terms': {
        **offered, 'unit_price': 5.37, 'index_clause': None}}]})
    move = PackageAgent().decide(c, threads)
    assert move['message']['term_sheets'][0]['terms']['index_clause'] == offered['index_clause']


def test_relationship_estimate_is_scoped_to_supplier_and_part():
    c = case('P10')
    terms = {'unit_price': 30, 'volume_per_year': 23400, 'contract_months': 24, 'lead_time_days': 42}
    std = {'payment_days': 30, 'incoterm': 'DAP'}
    estimate = {'unit_cost': 29, 'confidence_pct': 5}
    plain = total_cost(c, terms, std)
    assert estimated_cost(c, 'sup:70410', terms, std, {('other', 'part:340010'): estimate}) == plain
    assert estimated_cost(c, 'sup:70410', terms, std, {('sup:70410', 'part:340010'): estimate}) > plain


def test_rejected_alternative_reconciles_primary_without_new_session():
    from arena_kit.client import ArenaError

    from negotiator.closing import GuardedRemoteTable

    c = case('P18')
    primary = {'unit_price': 5.5, 'payment_days': 90, 'contract_months': 24,
               'index_clause': c['term_options']['index_clause'][1]}

    class Client:
        def __init__(self):
            self.actions = []

        def send_message(self, session, supplier, message):
            self.actions.append(message['action']['term_sheet_id'])
            if len(self.actions) == 1:
                raise ArenaError(422, 'alternative ID not accepted')
            return {'result': {'ended': True, 'deal': True}}

        def session(self, session):
            return {'status': 'open', 'threads': {c['suppliers'][0]: {'offer_id': 'offer:0'}}}

        def thread(self, session, supplier):
            return {'messages': thread(c, [primary], 'final_offer')[supplier]}

    client = Client()
    table = GuardedRemoteTable(client, PackageAgent(), c)
    table.session_id = 'existing'
    result = table.close(c['suppliers'][0], {'action': {'type': 'accept', 'term_sheet_id': 'offer:0-a'}})
    assert result['deal'] is True
    assert client.actions == ['offer:0-a', 'offer:0']

    # A rejected valid primary ID must not trigger another acceptance.
    client = Client()
    table = GuardedRemoteTable(client, PackageAgent(), c)
    table.session_id = 'existing'
    with pytest.raises(ArenaError):
        table.close(c['suppliers'][0], {'action': {'type': 'accept', 'term_sheet_id': 'offer:0'}})
    assert client.actions == ['offer:0']


def test_reconciliation_does_not_accept_primary_over_alternative():
    from arena_kit.client import ArenaError

    from negotiator.closing import GuardedRemoteTable

    c = case('P18')

    class Client:
        def send_message(self, session, supplier, message):
            raise ArenaError(422, 'invalid alternative')

        def session(self, session):
            return {'status': 'open', 'threads': {c['suppliers'][0]: {'offer_id': 'offer:0'}}}

        def thread(self, session, supplier):
            return {'messages': thread(c, [{'unit_price': 100}], 'final_offer')[supplier]}

    table = GuardedRemoteTable(Client(), PackageAgent(), c)
    table.session_id = 'existing'
    with pytest.raises(ArenaError):
        table.close(c['suppliers'][0], {'action': {'type': 'accept', 'term_sheet_id': 'offer:0-a'}})
