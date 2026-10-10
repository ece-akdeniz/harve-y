import copy
import json
import time
from pathlib import Path

import pytest
from arena_kit.cost import must_haves_ok, total_cost

from negotiator.agent import PackageAgent
from negotiator.package_advisor import PackageAdvisor, approved_packages
from negotiator.policy import PolicyConfig
from negotiator.runner import CaseRunner


def setup():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P10')
    sid = case['suppliers'][0]
    events = [{'from': sid, 'status': 'open', 'body': 'Which volume can you commit to?',
               'term_sheets': [{'term_sheet_id': 'offer:0', 'terms': {
                   'unit_price': 32.2, 'lead_time_days': 54, 'volume_per_year': 19890, 'contract_months': 12}}]}]
    move = {'supplier_id': sid, 'message': {'subject': 'Offer', 'body': 'Our proposal follows.',
            'term_sheets': [{'terms': {'unit_price': 28.34, 'lead_time_days': 42,
                                      'volume_per_year': 23400, 'contract_months': 24}}], 'refs': []}}
    return case, {sid: events}, move


def fixture():
    case, threads, move = setup()
    threads[move['supplier_id']][0].update(
        body='We need a longer contract commitment to allocate capacity.',
        sender={'name': 'Commercial Director', 'role': 'owner'}, role='owner')
    return case, threads, move


def select_36(context, _timeout):
    return {'selected_id': next(k for k, t in context['approved_packages'].items()
                                if t.get('contract_months') == 36),
            'supporting_quote': 'longer contract commitment'}


def test_real_fixture_free_36_month_commitment_is_complete_and_cost_neutral():
    case, threads, move = fixture()
    before = copy.deepcopy(move)
    changed, trace = PackageAdvisor(select_36).select(case, threads, move)
    old = move['message']['term_sheets'][0]['terms']
    new = changed['message']['term_sheets'][0]['terms']
    assert trace['status'] == 'ok'
    assert new == {**old, 'contract_months': 36}
    assert total_cost(case, new) == total_cost(case, old)
    assert must_haves_ok(case, new) and move == before
    assert changed['message']['refs'] == []
    assert 'longer contract commitment' not in changed['message']['body']


def test_serial_integration_records_choice_and_async_rejects_before_session_open():
    case, threads, move = fixture()
    sid = move['supplier_id']
    policy = PolicyConfig(package_advice_types=('capacity',), cost_neutral_lead_time=True)
    agent = PackageAgent(policy=policy)
    agent.package_advisor = PackageAdvisor(select_36)
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    selected = agent.decide(case, threads)
    terms = selected['message']['term_sheets'][0]['terms']
    assert terms['contract_months'] == 36
    assert agent.prev[sid]['contract_months'] == 36
    retained = agent._free_concessions(case, agent.prev[sid], {**terms, 'contract_months': 24}, {}, None)
    assert retained['contract_months'] == 36
    with pytest.raises(ValueError, match='serial runner'):
        CaseRunner(None, case['case_id'], agent, None)


def test_role_history_public_notes_and_cache_without_private_economics():
    case, threads, move = fixture()
    seen = []
    def model(context, timeout):
        seen.append(context)
        return select_36(context, timeout)
    advisor = PackageAdvisor(model)
    notes = [{'id': 'doc:public', 'text': 'Capacity is allocated to longer commitments.',
              'full_cost': 999, 'reservation_cost': 123}]
    advisor.select(case, threads, move, public_notes=notes)
    advisor.select(case, threads, move, public_notes=notes)
    assert len(seen) == 1
    context = seen[0]
    assert context['recent_messages'][-1]['role'] == 'owner'
    assert context['recent_messages'][-1]['sender']['role'] == 'owner'
    assert context['recent_messages'][-1]['term_sheets']
    assert context['public_dossier_notes'] == [{'id': 'doc:public', 'text': notes[0]['text']}]
    assert '999' not in json.dumps(context) and 'reservation_cost' not in json.dumps(context)
    assert 'c_best' not in context and 'buyer' not in context


@pytest.mark.parametrize('advice', [
    {'selected_id': 'package_evil', 'supporting_quote': 'longer contract commitment'},
    {'selected_id': [], 'supporting_quote': 'longer contract commitment'},
    {'selected_id': 'keep', 'supporting_quote': 'invented'},
    {'selected_id': 'keep', 'supporting_quote': '', 'terms': {'unit_price': 1}},
    None,
])
def test_malicious_invalid_output_falls_back(advice):
    case, threads, move = fixture()
    changed, trace = PackageAdvisor(lambda *_: advice).select(case, threads, move)
    assert changed == move and trace['status'] == 'fallback'


def test_fabricated_supporting_quote_cannot_select_even_approved_package():
    case, threads, move = fixture()
    def fabricated(context, timeout):
        return {**select_36(context, timeout), 'supporting_quote': 'We already accepted 36 months.'}
    changed, trace = PackageAdvisor(fabricated).select(case, threads, move)
    assert changed == move and trace['status'] == 'fallback'


def test_default_missing_endpoint_timeout_and_close_are_unchanged(monkeypatch):
    case, threads, move = fixture()
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    assert PackageAdvisor().select(case, threads, move)[1]['status'] == 'fallback'
    def slow(*_):
        time.sleep(0.2)
        return {}
    start = time.monotonic()
    assert PackageAdvisor(slow, timeout_s=0.01).select(case, threads, move)[1]['status'] == 'fallback'
    assert time.monotonic() - start < 0.1
    advisor = PackageAdvisor(lambda *_: pytest.fail('must not call model'))
    assert advisor.select(case, threads, move, remaining_s=19)[0] == move
    move['message']['refs'] = ['doc:evidence']
    assert advisor.select(case, threads, move)[0] == move
    move['message']['refs'] = []
    threads[move['supplier_id']][-1]['status'] = 'final_offer'
    assert advisor.select(case, threads, move)[1]['status'] == 'skipped_final'
    move['message'] = {'action': {'type': 'accept', 'term_sheet_id': 'offer:0'}}
    assert advisor.select(case, threads, move)[0] == move


def test_history_blocks_repeating_rejected_packages_and_two_switch_limit():
    case, threads, move = fixture()
    sid = move['supplier_id']
    terms = move['message']['term_sheets'][0]['terms']
    events = threads[sid]
    buyer = {'from': 'buyer', 'term_sheets': [{'terms': {**terms, 'contract_months': 36}}]}
    events[:0] = [buyer]
    candidates = approved_packages(case, events, terms)
    assert all(t['contract_months'] != 36 for t in candidates.values())
    events[:0] = [
        {'from': 'buyer', 'term_sheets': [{'terms': {**terms, 'contract_months': 12}}]},
        {'from': 'buyer', 'term_sheets': [{'terms': {**terms, 'contract_months': 24}}]},
    ]
    assert approved_packages(case, events, terms) == {}


def test_costly_delivery_is_compensated_and_illegal_quote_options_rejected():
    case, threads, move = fixture()
    terms = move['message']['term_sheets'][0]['terms']
    events = threads[move['supplier_id']]
    candidates = approved_packages(case, events, terms)
    delayed = next(t for t in candidates.values() if t['lead_time_days'] == 56)
    assert delayed['unit_price'] < terms['unit_price']
    assert total_cost(case, delayed) <= total_cost(case, terms)
    assert approved_packages(case, events, {**terms, 'lead_time_days': 54}) == {}
    constrained = copy.deepcopy(case)
    constrained['buyer']['must_haves'].append({'field': 'lead_time_days', 'op': '<=', 'value': 42})
    assert all(t['lead_time_days'] <= 42 for t in approved_packages(constrained, events, terms).values())


def test_relationship_estimate_does_not_use_monotonic_inverse_search(monkeypatch):
    case, threads, move = fixture()
    terms = move['message']['term_sheets'][0]['terms']
    supplier = {'full_cost': 24.31, 'interest_rate': 0.08, 'standard': {}}
    def invalid_inverse(*_):
        pytest.fail('relationship cost is nonmonotonic')
    monkeypatch.setattr('negotiator.package_advisor.price_for_cost', invalid_inverse)
    candidates = approved_packages(case, threads[move['supplier_id']], terms, supplier)
    assert all(total_cost(case, t, supplier=supplier) <= total_cost(case, terms, supplier=supplier)
               for t in candidates.values())


def test_arena_from_name_preserves_real_sender_role_without_explicit_role():
    case, threads, move = fixture()
    last = threads[move['supplier_id']][-1]
    last.pop('role')
    last.pop('sender')
    last['from'] = 'owner@70410'
    last['from_name'] = 'Owner, Supplier 70410'
    seen = []
    def model(context, timeout):
        seen.append(context)
        return select_36(context, timeout)
    result, trace = PackageAdvisor(model).select(case, threads, move)
    assert trace['status'] == 'ok'
    supplier_message = seen[0]['recent_messages'][-1]
    assert supplier_message['from_name'] == 'Owner, Supplier 70410'
    assert supplier_message['sender'] == 'owner@70410'
    assert supplier_message['role'] is None
    assert result['message']['term_sheets'][0]['terms']['contract_months'] == 36


def test_config_activates_only_measured_capacity_type_and_default_is_off():
    assert PackageAgent().package_advisor is None
    assert PackageAgent(policy=PolicyConfig()).package_advisor is None
    policy = PolicyConfig.load('configs/package-advice.json')
    assert policy.package_advice_types == ('capacity',)
    base = json.loads(Path('configs/cost-neutral-delivery.json').read_text())
    configured = json.loads(Path('configs/package-advice.json').read_text())
    assert configured == {**base, 'package_advice_types': ['capacity']}
