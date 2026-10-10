"""Synthetic stateful supplier stress tests, not forecasts of hosted scores.

Only the starting prefix comes from saved conversations. Every subsequent reply is
computed from the actual agent proposal by an explicit, deliberately simple rule.
Synthetic suppliers can refuse our price or withdraw a historical package. No LLM,
arena endpoint, score target, or recorded future reply participates in these tests.
"""

import copy
import json
import socket
import time
from pathlib import Path

import pytest
from arena_kit.cost import closing_terms, must_haves_ok, total_cost
from arena_kit.docs import standard_terms

from negotiator.agent import PackageAgent
from negotiator.evaluator import close_decision, price_for_cost
from negotiator.policy import PolicyConfig
from negotiator.responses import permitted
from negotiator.trades import history

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOTS = {s["id"]: s for s in json.loads((FIXTURES / "replay_decisions.json").read_text())["snapshots"]}
CASES = {c["case_id"]: c for c in json.loads((FIXTURES / "practice_cases.json").read_text())}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Synthetic trajectories must not access the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)


class Supplier:
    """Local rule: reject below a package-specific floor; eventually stop bargaining."""

    def __init__(self, floors, rejected_shapes=()):
        self.floors = floors
        self.rejected_shapes = rejected_shapes
        self.replies = []

    def reply(self, proposed, field):
        turn = len(self.replies) + 1
        shape = proposed[field]
        allowed = shape in self.floors and shape not in self.rejected_shapes
        confirmed = allowed and proposed["unit_price"] >= self.floors[shape]
        if confirmed:
            terms, status = dict(proposed), "agreed"
        elif self.replies and self.replies[-1]["status"] == "final_offer":
            terms, status = {}, "walked_away"
        else:
            offered = shape if allowed else next(k for k in self.floors if k not in self.rejected_shapes)
            terms = {**proposed, field: offered, "unit_price": self.floors[offered]}
            status = "final_offer" if turn >= 2 else "open"
        message = {
            "from": "synthetic@supplier", "status": status,
            "message_id": f"synthetic-message-{turn}",
            "body": ("We confirm your actual package." if confirmed else
                     "We reject your price or package. Only the new quoted terms are available."),
            "term_sheets": ([] if status == "walked_away" else
                            [{"term_sheet_id": f"synthetic-offer-{turn}", "terms": terms}]),
        }
        self.replies.append(message)
        return message


def trajectory(name, supplier, field):
    snapshot = copy.deepcopy(SNAPSHOTS[name])
    case = copy.deepcopy(CASES[snapshot["case_id"]])
    sid, threads = snapshot["supplier_id"], snapshot["threads"]
    policy = PolicyConfig(**{**snapshot["policy"], "evidence_types": (),
                             "response_types": (case["type"],)})
    sent = []
    for _ in range(8):
        # Every decision restarts the agent: history, not private in-memory state, is authoritative.
        agent = PackageAgent(policy=policy, estimates={}, claims=False, meso=False)
        agent.trades.deadlines[sid] = time.time() + 60
        move = agent.propose(case, copy.deepcopy(threads), sid)
        if move.get("close"):
            action = close_decision(case, threads)["message"]["action"]
            if action["type"] == "accept":
                assert action["term_sheet_id"] == threads[sid][-1]["term_sheets"][0]["term_sheet_id"]
                assert action["term_sheet_id"].startswith("synthetic-offer-")
            return case, threads[sid], sent, action
        assert not move.get("hold"), "A single synthetic supplier must not deadlock"
        message = move["message"]
        assert "action" not in message
        assert len(message["term_sheets"]) == 1
        assert "term_sheet_id" not in message["term_sheets"][0]
        terms = message["term_sheets"][0]["terms"]
        assert set(terms) == set(case["negotiable"])
        assert permitted(case, terms) and must_haves_ok(case, terms, standard_terms(threads[sid]))
        if case["case_id"] == "case:P11":
            assert closing_terms(case, terms)["payment_days"] == 60
        sent.append(copy.deepcopy(terms))
        threads[sid].append({**copy.deepcopy(message), "from": "buyer"})
        assert history(case, threads[sid])[2] <= 2
        threads[sid].append(supplier.reply(terms, field))
    pytest.fail("Synthetic negotiation failed to terminate in its bounded reply budget")


@pytest.mark.parametrize("discount_from_break_even", [-1.0, 0.0, 1.0])
def test_priced_payment_refusal_then_current_offer_close(discount_from_break_even):
    """Payment costs money even when its alternative has a lower displayed price."""
    case = CASES["case:P02"]
    expensive = {"unit_price": 374.07, "payment_days": 90, "index_clause": None}
    break_even = price_for_cost(case, {**expensive, "payment_days": 30}, total_cost(case, expensive))
    faster_price = round(break_even - discount_from_break_even, 2)
    snapshot = copy.deepcopy(SNAPSHOTS["p02-priced-payment"])
    sid = snapshot["supplier_id"]
    snapshot["threads"][sid][-1]["term_sheets"][1]["terms"]["unit_price"] = faster_price
    # A private snapshot entry avoids mutating the shared on-disk fixture.
    name = f"synthetic-payment-{discount_from_break_even}"
    SNAPSHOTS[name] = snapshot
    try:
        supplier = Supplier({90: 374.07, 30: faster_price})
        _, _, sent, action = trajectory(name, supplier, "payment_days")
    finally:
        del SNAPSHOTS[name]
    assert sent[0]["payment_days"] == 30
    assert sent[0]["unit_price"] < faster_price  # The actual aggressive proposal is refused.
    assert supplier.replies[0]["status"] == "open"
    assert total_cost(case, sent[0]) <= total_cost(case, expensive)
    assert action["type"] == "accept"
    if discount_from_break_even < 0:
        assert total_cost(case, {**expensive, "payment_days": 30, "unit_price": faster_price}) > total_cost(
            case, expensive
        )


@pytest.mark.parametrize("withdraw_old_package", [False, True])
def test_historical_chargeback_package_reconfirmed_or_refused(withdraw_old_package):
    """An old beneficial quote is a request, never executable after it disappears."""
    supplier = Supplier({150: 46.5, 500: 48.5}, rejected_shapes=(150,) if withdraw_old_package else ())
    _, events, sent, action = trajectory("p11-remember-alternative", supplier, "chargeback_eur_per_complaint")
    assert sent[0]["chargeback_eur_per_complaint"] == 150
    assert sent[0]["unit_price"] < 46.5  # No fake guaranteed concession by the synthetic opponent.
    assert supplier.replies[0]["status"] == "open"
    assert supplier.replies[0]["term_sheets"][0]["terms"]["chargeback_eur_per_complaint"] == (
        500 if withdraw_old_package else 150
    )
    assert history(CASES["case:P11"], events)[2] <= 2
    assert action["type"] == "accept"
    assert action["term_sheet_id"] != "offer:70140-1-a"
