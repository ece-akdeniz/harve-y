import copy
import time

import pytest
from arena_kit.cost import total_cost

from negotiator.agent import PackageAgent
from negotiator.evaluator import close_decision, eligible_sheets, price_for_cost, revealed_deltas
from negotiator.optimizer import alternative_cost
from negotiator.play import play_case

RFQ = {
    "case_id": "case:T02",
    "type": "rfq",
    "title": "Shaft RFQ",
    "suppliers": ["sup:J", "sup:C"],
    "negotiable": ["unit_price", "payment_days", "lead_time_days", "incoterm"],
    "fixed_terms": {"contract_months": 24},
    "term_options": {
        "payment_days": [14, 30, 45, 60],
        "lead_time_days": [21, 28, 35, 42, 49],
        "incoterm": ["EXW", "FCA", "DAP"],
    },
    "buyer": {
        "category_goal": "leverage",
        "need_per_year": 6000,
        "horizon_years": 2,
        "current_unit_price": None,
        "fallback_unit_price": 19.9,
        "fallback_risk_pct": 5,
        "interest_rate": 0.08,
        "reference_payment_days": 60,
        "need_lead_time_days": 35,
        "late_cost_per_day": 150,
        "cost_per_defect": 40,
        "freight_eur_per_unit": {"EXW": 0.6, "FCA": 0.4, "DAP": 0.0},
        "index_paths": {},
        "must_haves": [{"field": "lead_time_days", "op": "<=", "value": 42}],
        "alternative": {"kind": "quote", "terms": {"unit_price": 19.9, "incoterm": "DAP", "payment_days": 60,
                                                    "lead_time_days": 35}},
    },
    "round_limit": 10,
}

STABILISE = {
    "case_id": "case:T01",
    "type": "price_increase",
    "title": "Housing",
    "suppliers": ["sup:F"],
    "negotiable": ["unit_price", "payment_days"],
    "fixed_terms": {"lead_time_days": 35, "incoterm": "FCA", "contract_months": 24},
    "term_options": {"payment_days": [30, 45, 60]},
    "buyer": {
        "category_goal": "stabilise",
        "need_per_year": 4000,
        "horizon_years": 2,
        "current_unit_price": 48.6,
        "fallback_unit_price": 55.0,
        "fallback_risk_pct": 5,
        "sustainable_margin_pct": 4,
        "relationship_eur_per_point": 5000,
        "interest_rate": 0.08,
        "reference_payment_days": 60,
        "need_lead_time_days": 35,
        "late_cost_per_day": 0,
        "cost_per_defect": 0,
        "freight_eur_per_unit": {"EXW": 1.9, "FCA": 1.2, "DAP": 0.0},
        "index_paths": {},
        "must_haves": [],
        "alternative": {"kind": "none"},
    },
    "round_limit": 10,
}
ESTIMATE = {"sup:F": {"standard": {"payment_days": 60, "incoterm": "FCA"}, "interest_rate": 0.08, "full_cost": 47.0}}


def msg(status, *sheets, sender="sales"):
    return {"from": sender, "status": status, "attachments": [],
            "term_sheets": [{"term_sheet_id": i, "terms": t} for i, t in sheets]}


def ours(terms):
    return {"from": "buyer", "term_sheets": [{"terms": terms}], "body": ""}


BAD = {"unit_price": 14.0, "payment_days": 45, "lead_time_days": 49, "incoterm": "EXW"}  # breaks lead <= 42
GOOD = {"unit_price": 16.0, "payment_days": 45, "lead_time_days": 35, "incoterm": "EXW"}


def test_eligible_sheets_drop_must_have_break_then_rank_by_c():
    events = [msg("open", ("offer:bad", BAD), ("offer:good", GOOD), ("offer:dear", {**GOOD, "unit_price": 17.0}))]
    out = eligible_sheets(RFQ, events)
    assert [s for _, s, _ in out] == ["offer:good", "offer:dear"]
    assert out[0][0] == total_cost(RFQ, GOOD)


def test_eligible_sheets_empty_for_ended_thread():
    assert eligible_sheets(RFQ, [msg("walked_away", ("offer:good", GOOD))]) == []


def test_invalid_cheapest_plus_valid_alternative_accepts_alternative():
    threads = {"sup:J": [msg("agreed", ("offer:bad", BAD), ("offer:good", GOOD))]}
    move = close_decision(RFQ, threads)
    assert move == {"supplier_id": "sup:J", "message": {"action": {"type": "accept", "term_sheet_id": "offer:good"}}}
    move = PackageAgent().decide(RFQ, threads)
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "offer:good"}


def test_close_decision_picks_best_across_threads():
    cheaper = {**GOOD, "unit_price": 15.5}
    threads = {"sup:J": [msg("final_offer", ("offer:j", GOOD))], "sup:C": [msg("open", ("offer:c", cheaper))]}
    move = close_decision(RFQ, threads)
    assert move["supplier_id"] == "sup:C"
    assert move["message"]["action"]["term_sheet_id"] == "offer:c"


def test_walk_when_nothing_beats_alternative():
    dear = {**GOOD, "unit_price": 25.0}
    threads = {"sup:J": [msg("agreed", ("offer:bad", BAD), ("offer:dear", dear))]}
    assert close_decision(RFQ, threads)["message"]["action"] == {"type": "walk_away"}
    assert PackageAgent().decide(RFQ, threads)["message"]["action"] == {"type": "walk_away"}


def test_estimates_change_the_ranking():
    low, fair = {"unit_price": 45.0, "payment_days": 60}, {"unit_price": 47.5, "payment_days": 60}
    threads = {"sup:F": [msg("agreed", ("offer:low", low), ("offer:fair", fair))]}
    assert close_decision(STABILISE, threads)["message"]["action"]["term_sheet_id"] == "offer:low"
    move = close_decision(STABILISE, threads, ESTIMATE)
    assert move["message"]["action"]["term_sheet_id"] == "offer:fair"
    assert PackageAgent(estimates=ESTIMATE).decide(STABILISE, threads)["message"]["action"]["term_sheet_id"] == (
        "offer:fair"
    )


class FakeTable:
    def __init__(self, case, threads):
        self.case, self.threads, self.closed, self.sent = case, threads, [], []

    def open(self, case_id):
        return self.case, copy.deepcopy(self.threads)

    def send(self, sid, message):
        self.sent.append((sid, message))
        return msg("open", ("offer:x", GOOD))

    def close(self, sid, message):
        self.closed.append((sid, message))
        return {"deal": message["action"]["type"] == "accept", "supplier_id": sid}

    def attachment(self, attachment_id):
        raise AssertionError("no attachments")


class NoDecide(PackageAgent):
    def decide(self, case, threads):
        raise AssertionError("the deadline path must not ask the agent")


def test_play_case_deadline_uses_close_decision_with_estimates():
    low, fair = {"unit_price": 45.0, "payment_days": 60}, {"unit_price": 47.5, "payment_days": 60}
    table = FakeTable(STABILISE, {"sup:F": [msg("open", ("offer:low", low), ("offer:fair", fair))]})
    play_case(table, "case:T01", NoDecide(estimates=ESTIMATE), deadline=time.time())
    assert table.closed == [("sup:F", {"action": {"type": "accept", "term_sheet_id": "offer:fair"}})]
    assert not table.sent


def test_play_case_deadline_skips_invalid_first_sheet():
    table = FakeTable(RFQ, {"sup:J": [msg("open", ("offer:bad", BAD), ("offer:good", GOOD))]})
    play_case(table, "case:T02", NoDecide(), deadline=lambda: time.time())
    assert table.closed == [("sup:J", {"action": {"type": "accept", "term_sheet_id": "offer:good"}})]


def test_price_for_cost_inverts_total_cost():
    terms = {"payment_days": 30, "lead_time_days": 21, "incoterm": "DAP", "unit_price": 1.0}
    target = total_cost(RFQ, {**terms, "unit_price": 15.0})
    assert price_for_cost(RFQ, terms, target) == pytest.approx(15.0, abs=1e-4)


def test_revealed_delta_only_for_single_term_difference():
    a = {"unit_price": 136.2, "payment_days": 30, "lead_time_days": 35, "incoterm": "DAP"}
    b = {**a, "unit_price": 138.4, "payment_days": 60}
    c = {**b, "incoterm": "EXW", "unit_price": 137.0}
    sheets = [{"term_sheet_id": i, "terms": t} for i, t in (("a", a), ("b", b), ("c", c))]
    assert revealed_deltas(RFQ, sheets) == [("payment_days", 30, 60, 2.2), ("incoterm", "DAP", "EXW", -1.4)]


def test_package_switches_only_when_supplier_package_is_cheaper():
    agent = PackageAgent()
    prev = {"payment_days": 60, "lead_time_days": 21, "incoterm": "DAP"}
    agent.prev["sup:J"] = prev
    on_prev = {**prev, "unit_price": 16.4}
    fast_pay = {**prev, "payment_days": 30, "unit_price": 15.9}  # cheaper by C than on_prev
    assert total_cost(RFQ, fast_pay) < total_cost(RFQ, on_prev)
    threads = {"sup:J": [msg("open", ("o:0", on_prev)), ours({**prev, "unit_price": 14.0}),
                         msg("open", ("o:1", on_prev), ("o:1-a", fast_pay))]}
    move = agent.propose(RFQ, threads, "sup:J")
    assert move["message"]["term_sheets"][0]["terms"]["payment_days"] == 30

    agent = PackageAgent()
    agent.prev["sup:J"] = prev
    pricier = {**prev, "payment_days": 30, "unit_price": 16.4}
    threads["sup:J"][-1] = msg("open", ("o:1", on_prev), ("o:1-a", pricier))
    move = agent.propose(RFQ, threads, "sup:J")
    assert move["message"]["term_sheets"][0]["terms"]["payment_days"] == 60


def test_postponement_cost_includes_units_at_old_price():
    case = copy.deepcopy(STABILISE)
    case["negotiable"] = ["unit_price", "effective_date"]
    case["term_options"] = {"effective_date": ["2026-12-01", "2027-12-01"]}
    early = total_cost(case, {"unit_price": 52.0, "effective_date": "2026-12-01"})
    late = total_cost(case, {"unit_price": 52.0, "effective_date": "2027-12-01"})
    assert late == pytest.approx(early - 4000 * (52.0 - 48.6), rel=1e-3)


def _final_thread(final):
    return {"sup:J": [msg("open", ("o:0", {**final, "unit_price": 17.1})), ours({**final, "unit_price": 15.0}),
                      msg("final_offer", ("o:1", final))]}


FINAL = {"unit_price": 15.7, "payment_days": 30, "lead_time_days": 21, "incoterm": "DAP"}
PREV = {"payment_days": 60, "lead_time_days": 21, "incoterm": "DAP"}


def test_final_offer_accepted_when_walk_risk_outweighs_gain():
    agent = PackageAgent()
    agent.prev["sup:J"] = PREV
    move = agent.decide(RFQ, _final_thread(FINAL))  # fallback is the far dearer alternative
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "o:1"}


def test_final_offer_gets_at_most_one_counter_then_close():
    case = copy.deepcopy(RFQ)
    case["buyer"]["alternative"]["terms"] = {**FINAL, "unit_price": 15.72}  # walking costs little
    agent = PackageAgent()
    agent.prev["sup:J"] = PREV
    threads = _final_thread(FINAL)
    move = agent.decide(case, threads)
    terms = move["message"]["term_sheets"][0]["terms"]
    assert terms["unit_price"] == 15.7 and terms["payment_days"] == 60
    threads["sup:J"] += [ours(terms), msg("final_offer", ("o:2", FINAL))]
    move = agent.decide(case, threads)
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "o:2"}


def test_final_offer_lets_open_rival_beat_it_once():
    final = {"unit_price": 15.7, "payment_days": 30, "lead_time_days": 21, "incoterm": "DAP"}
    rival = {"unit_price": 17.3, "payment_days": 60, "lead_time_days": 28, "incoterm": "DAP"}
    agent = PackageAgent()
    agent.final_counters["sup:J"] = 1
    threads = {
        "sup:J": [msg("final_offer", ("j:5", final))],
        "sup:C": [msg("open", ("c:0", {**rival, "unit_price": 17.7})), ours({**rival, "unit_price": 14.5}),
                  msg("open", ("c:1", rival))],
    }
    move = agent.decide(RFQ, threads)
    assert move["supplier_id"] == "sup:C"
    c_offer = total_cost(RFQ, move["message"]["term_sheets"][0]["terms"])
    assert c_offer < total_cost(RFQ, final)
    threads["sup:C"] += [ours(move["message"]["term_sheets"][0]["terms"]), msg("open", ("c:2", rival))]
    move = agent.decide(RFQ, threads)
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "j:5"}


def test_final_above_alternative_gets_one_counter_at_alternative():
    dear = {"unit_price": 21.0, "payment_days": 60, "lead_time_days": 35, "incoterm": "DAP"}
    agent = PackageAgent()
    threads = {"sup:J": [msg("final_offer", ("j:1", dear))]}
    move = agent.decide(RFQ, threads)
    assert total_cost(RFQ, move["message"]["term_sheets"][0]["terms"]) < alternative_cost(RFQ)
    threads["sup:J"] += [ours(move["message"]["term_sheets"][0]["terms"]), msg("final_offer", ("j:2", dear))]
    assert agent.decide(RFQ, threads)["message"]["action"] == {"type": "walk_away"}


def test_propose_returns_close_request_when_agreed():
    threads = {"sup:J": [msg("agreed", ("o:1", GOOD))], "sup:C": [msg("open", ("c:1", GOOD))]}
    assert PackageAgent().propose(RFQ, threads, "sup:C") == {"close": True, "reason": "supplier agreed"}
