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
