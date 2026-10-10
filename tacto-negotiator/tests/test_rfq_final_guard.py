import json
from pathlib import Path

from test_evaluator import msg, ours

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig


def test_serial_rfq_preserves_best_final_before_potentially_slow_rival_request():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    terms = {'unit_price': 32, 'payment_days': 14, 'lead_time_days': 28}
    threads = {case['suppliers'][0]: [msg('final_offer', ('offer:final', terms))],
               case['suppliers'][1]: [msg('open', ('offer:rival', {**terms, 'unit_price': 33}))]}
    agent = PackageAgent(policy=PolicyConfig(rfq_final_guard=True))
    move = agent.decide(case, threads)
    assert move['supplier_id'] == case['suppliers'][0]
    assert move['message']['action'] == {'type': 'accept', 'term_sheet_id': 'offer:final'}


def test_rfq_guard_does_not_accept_an_invalid_final():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    sid, rival = case['suppliers'][:2]
    threads = {sid: [msg('final_offer', ('offer:invalid', {'unit_price': 25, 'lead_time_days': 52,
                                                       'payment_days': 30}))],
               rival: [msg('open', ('offer:valid', {'unit_price': 32, 'lead_time_days': 28,
                                                  'payment_days': 30}))]}
    move = PackageAgent(policy=PolicyConfig(rfq_final_guard=True)).decide(case, threads)
    assert move.get('message', {}).get('action', {}).get('term_sheet_id') != 'offer:invalid'


def _p05_convergence_threads(case):
    leader, rival = case['suppliers'][:2]
    terms = {'unit_price': 32.5, 'payment_days': 60, 'lead_time_days': 35}
    rival_terms = {**terms, 'unit_price': 34.0}
    return leader, rival, {
        leader: [msg('open', ('offer:lead-1', {**terms, 'unit_price': 34.5})), ours({**terms, 'unit_price': 30.0}),
                 msg('open', ('offer:lead-2', terms))],
        rival: [msg('open', ('offer:riv-1', {**rival_terms, 'unit_price': 35.0})), ours(rival_terms),
                msg('open', ('offer:riv-2', rival_terms))],
    }


def test_p05_losing_rival_gap_closed_does_not_end_case_while_leader_workable():
    import time

    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    leader, rival, threads = _p05_convergence_threads(case)
    legacy = PackageAgent(policy=PolicyConfig())
    legacy.trades.deadlines[rival] = time.time() + 60
    assert legacy.propose(case, threads, rival) == {'close': True, 'reason': 'gap closed'}
    guarded = PackageAgent(policy=PolicyConfig(rfq_nonleading_hold=True))
    guarded.trades.deadlines[rival] = time.time() + 60
    assert guarded.propose(case, threads, rival)['hold']
    # Near the rival's own deadline it still holds: closing then would pick the losing sheet.
    guarded.trades.deadlines[rival] = time.time() + 5
    assert guarded.propose(case, threads, rival)['hold']
    # Once the leader is no longer workable, the legacy close returns.
    threads[leader][-1] = msg('final_offer', ('offer:lead-2', threads[leader][-1]['term_sheets'][0]['terms']))
    assert not guarded.propose(case, threads, rival).get('hold')


def test_rfq_supplier_lead_time_counters_longest_legal_option_up_to_quote():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    slow, fast = case['suppliers'][:2]
    threads = {slow: [msg('open', ('offer:s', {'unit_price': 31.5, 'lead_time_days': 52}))],
               fast: [msg('open', ('offer:f', {'unit_price': 36.0}))]}
    on = PackageAgent(policy=PolicyConfig(rfq_supplier_lead_time=True))
    off = PackageAgent(policy=PolicyConfig())
    lt = lambda a, s: a.propose(case, threads, s)['message']['term_sheets'][0]['terms']['lead_time_days']  # noqa: E731
    assert lt(on, slow) == 42  # never 56: must-have caps lead time at 42
    assert lt(off, slow) < 42
    assert lt(on, fast) == lt(off, fast)


def test_rfq_rival_offer_claim_cites_cheaper_standing_rival_once():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    a, b = case['suppliers'][:2]
    terms = {'payment_days': 30, 'lead_time_days': 35}
    threads = {a: [msg('open', ('offer:a-1', {**terms, 'unit_price': 32.0}))],
               b: [msg('open', ('offer:b-1', {**terms, 'unit_price': 34.0}))]}
    agent = PackageAgent(policy=PolicyConfig(rfq_rival_offer=True))
    move = agent.propose(case, threads, b)['message']
    assert move['refs'] == ['offer:a-1']
    assert f"{case['parts'][0]} at EUR 32.00 per unit (offer:a-1)" in move['body']
    assert 'refs' not in agent.propose(case, threads, a)['message']  # never cite a dearer rival
    threads[b].append({**move, 'from': 'buyer'})
    threads[b].append(msg('open', ('offer:b-2', {**terms, 'unit_price': 33.5})))
    assert 'offer:a-1' not in (agent.propose(case, threads, b)['message'].get('refs') or [])


def test_rfq_supplier_payment_adopts_stated_term_but_never_below_30_days():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    a, b = case['suppliers'][:2]
    for stated, expected in ((30, 30), (14, 90)):
        agent = PackageAgent(policy=PolicyConfig(rfq_supplier_payment=True))
        threads = {a: [msg('open', ('offer:a', {'unit_price': 33.0, 'payment_days': stated, 'lead_time_days': 35}))],
                   b: [msg('open', ('offer:b', {'unit_price': 36.0}))]}
        terms = agent.propose(case, threads, a)['message']['term_sheets'][0]['terms']
        assert terms['payment_days'] == expected



def test_rfq_undercut_reanchor_counters_once_below_a_price_under_our_ask():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    a, b = case['suppliers'][:2]
    ask = {'unit_price': 31.74, 'payment_days': 90, 'lead_time_days': 35}
    sup = {'payment_days': 30, 'lead_time_days': 35}

    def threads():
        return {a: [msg('open', ('offer:a-1', {**sup, 'unit_price': 32.0})), ours(ask),
                    msg('open', ('offer:a-2', {**sup, 'unit_price': 29.0}))],
                b: [msg('open', ('offer:b-1', {**sup, 'unit_price': 34.0}))]}

    off = PackageAgent(policy=PolicyConfig()).propose(case, threads(), a)['message']['term_sheets'][0]['terms']
    assert off['unit_price'] == 29.0
    agent = PackageAgent(policy=PolicyConfig(rfq_undercut_reanchor=True))
    t = threads()
    move = agent.propose(case, t, a)['message']
    price = move['term_sheets'][0]['terms']['unit_price']
    assert price < 29.0 and move['term_sheets'][0]['terms']['lead_time_days'] <= 42
    # Only once: a repeat at 29.00 no longer re-anchors.
    t[a] += [{**move, 'from': 'buyer'}, msg('open', ('offer:a-3', {**sup, 'unit_price': 29.0}))]
    nxt = agent.propose(case, t, a)
    assert agent.reanchored == {a}
    assert nxt.get('close') or nxt['message']['term_sheets'][0]['terms']['unit_price'] >= price  # no backtracking


def test_rfq_data_claims_adds_one_fresh_fact_only_without_rival_claim():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    a, b = case['suppliers'][:2]
    terms = {'payment_days': 30, 'lead_time_days': 35}
    threads = {a: [msg('open', ('offer:a-1', {**terms, 'unit_price': 32.0}))],
               b: [msg('open', ('offer:b-1', {**terms, 'unit_price': 34.0}))]}
    cfg = dict(rfq_rival_offer=True, rfq_data_claims=True, evidence_types=('price_increase',))
    agent = PackageAgent(policy=PolicyConfig(**cfg))
    rival = agent.propose(case, threads, b)['message']
    assert rival['refs'] == ['offer:a-1']  # rival claim present: no extra data claim
    leader = agent.propose(case, threads, a)['message']
    refs = leader.get('refs') or []
    assert len(refs) <= 2 and not any(r.startswith('cost:') for r in refs)
    off = PackageAgent(policy=PolicyConfig(rfq_rival_offer=True, evidence_types=('price_increase',)))
    assert not off.propose(case, threads, a)['message'].get('refs')


def test_rfq_lead_trade_offers_42_never_56_and_reverts_when_not_cheaper():
    case = next(c for c in json.loads((Path(__file__).parent / 'fixtures/practice_cases.json').read_text())
                if c['case_id'] == 'case:P05')
    a, b = case['suppliers'][:2]
    t35 = {'payment_days': 30, 'lead_time_days': 35}
    base = [msg('open', ('offer:a-1', {**t35, 'unit_price': 32.0})), ours({**t35, 'unit_price': 31.74, 'payment_days': 90}),
            msg('open', ('offer:a-2', {**t35, 'unit_price': 29.0}))]
    threads = {a: base, b: [msg('open', ('offer:b-1', {**t35, 'unit_price': 34.0}))]}
    agent = PackageAgent(policy=PolicyConfig(rfq_undercut_reanchor=True, rfq_lead_trade=True))
    sheet = agent.propose(case, threads, a)['message']['term_sheets'][0]['terms']
    assert sheet['lead_time_days'] == 42 and sheet['unit_price'] < 29.0
    threads[a] = base + [ours(sheet), msg('open', ('offer:a-3', {**t35, 'unit_price': 29.0, 'lead_time_days': 42}))]
    again = agent.propose(case, threads, a)['message']['term_sheets'][0]['terms']
    assert again['lead_time_days'] == 35  # 29.00 at 42 d costs more than 29.00 at 35 d
