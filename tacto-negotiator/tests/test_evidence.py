import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from negotiator.claims import Claim, render
from negotiator.evidence import EvidencePolicy


@pytest.fixture
def context(monkeypatch):
    facts = {
        "idx:ENERGY@2025-08": {"value": 100, "month": "2025-08"},
        "idx:ENERGY@2026-08": {"value": 90, "month": "2026-08"},
        "sc:F@2026Q3": {"supplier": "sup:F", "otd_pct": 85},
        "doc:notice": {"supplier": "sup:F", "days": 30, "asked_pct": 5,
                       "part": "part:F", "date": "2026-09-01"},
        "ctr:F": {"supplier": "sup:F", "days": 60, "part": "part:F",
                  "valid_from": "2026-01-01", "valid_to": "2026-12-31"},
        "cost:F": {"unit_cost": 12},
    }
    claims = [
        Claim("index_change", ("idx:ENERGY@2025-08", "idx:ENERGY@2026-08"), -10, "%",
              "The index fell 10 % between idx:ENERGY@2025-08 and idx:ENERGY@2026-08.", subject="ENERGY"),
        Claim("scorecard_otd", ("sc:F@2026Q3",), 85, "%", "sc:F@2026Q3 records 85 % on time.",
              supplier_id="sup:F", subject="sup:F", disclosure="supplier_own"),
        Claim("notice", ("doc:notice", "ctr:F"), 30, "days", "doc:notice gives 30 days against ctr:F.",
              supplier_id="sup:F", subject="sup:F", part_id="part:F", disclosure="supplier_own"),
        Claim("should_cost", ("cost:F",), 12, "EUR", "cost:F is EUR 12.", disclosure="internal"),
    ]
    claims = [replace(c, sentence=render(c, facts)) for c in claims]
    monkeypatch.setattr("negotiator.context.build_bank", lambda *_: claims)
    case = {"case_id": "case:T", "type": "price_increase", "suppliers": ["sup:F"],
            "parts": ["part:F"], "trigger_doc": "doc:notice"}
    move = {"supplier_id": "sup:F", "message": {"body": "Our proposed price is EUR 15.",
            "term_sheets": [{"terms": {"unit_price": 15, "payment_days": 30}}]}}
    return case, move, SimpleNamespace(facts=facts), claims


def test_claims_do_not_change_terms_and_never_disclose_internal_cost(context):
    case, move, package, _ = context
    before = copy.deepcopy(move)
    policy = EvidencePolicy(package)
    out = policy.enrich(case, {}, "sup:F", move)
    assert move == before
    assert out["message"]["term_sheets"] == move["message"]["term_sheets"]
    assert len(out["message"]["refs"]) == 5  # three checked claims, not three IDs
    assert "cost:F" not in out["message"]["body"]
    assert policy.enrich(case, {}, "sup:F", move) == move  # reserved before another proposal


def test_resume_recovers_used_ids_from_buyer_messages(context):
    case, move, package, _ = context
    first = EvidencePolicy(package).enrich(case, {}, "sup:F", move)
    history = {"sup:F": [{**first["message"], "from": "buyer"}]}
    assert EvidencePolicy(package).enrich(case, history, "sup:F", move) == move


def test_reverify_rejects_bad_figure(context):
    case, move, package, claims = context
    claims[:] = [replace(claims[0], figure=-50)]
    assert EvidencePolicy(package).enrich(case, {}, "sup:F", move) == move


def test_no_claims_on_close_or_other_case_types(context):
    case, move, package, _ = context
    close = {"supplier_id": "sup:F", "message": {"action": {"type": "accept", "term_sheet_id": "offer:F"}}}
    policy = EvidencePolicy(package)
    assert policy.enrich(case, {}, "sup:F", close) == close
    assert policy.enrich({**case, "type": "rfq"}, {}, "sup:F", move) == move


def test_missing_package_falls_back_to_original_offer(context, monkeypatch):
    case, move, _, _ = context
    def missing():
        raise FileNotFoundError
    monkeypatch.setattr("negotiator.evidence.load_package", missing)
    assert EvidencePolicy().enrich(case, {}, "sup:F", move) == move
