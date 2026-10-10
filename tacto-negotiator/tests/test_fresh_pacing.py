"""Opt-in `claim_pacing`: one verified claim per message, deeper bank, nothing on finals."""

import json
from pathlib import Path

import pytest

from negotiator.claims import Claim, case_facts, check, history_claims, render
from negotiator.dossiers import load_package
from negotiator.evidence import EvidencePolicy

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}


@pytest.fixture(scope="module")
def package():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def _policy(package, pacing):
    return EvidencePolicy(package, case_types=["price_increase", "quality"],
                          recent_window_types=["raw_material", "price_increase", "quality"], claim_pacing=pacing)


def _move(price=5.5):
    return {"supplier_id": "sup:70740", "message": {"body": "Offer.", "term_sheets": [{"terms": {"unit_price": price}}]}}


def _supplier(price, status="open"):
    return {"from": "supplier", "status": status, "body": "Our price.", "term_sheets": [{"terms": {"unit_price": price}}]}


def test_history_claims_verify_against_facts_and_stay_below_current_price(package):
    for cid in ("case:P08", "case:P18", "case:P01", "case:P02"):
        case = CASES[cid]
        facts = case_facts(case, package)
        claims = history_claims(case, package)
        assert claims, cid
        for c in claims:
            assert check(c, facts, package, case) is None
            assert c.disclosure == "supplier_own" and c.supplier_id in case["suppliers"]
            assert c.figure <= case["buyer"]["current_unit_price"] + 1e-9
            assert all(i in c.sentence for i in c.ids)
            if c.kind == "po_history":
                assert 2 <= len(c.ids) <= 8 and all(i.startswith("po:") for i in c.ids)
                assert all(facts[i]["part"] == case["parts"][0] for i in c.ids)
            else:
                assert c.kind == "own_quote" and c.ids[0].startswith("quote:")
    assert history_claims(CASES["case:P05"], package) == []  # no orders with the RFQ bidders


def test_history_claim_checks_fail_closed():
    facts = {
        "po:1": {"supplier": "sup:A", "part": "part:X", "unit_price": 5.0, "price_unit": 1},
        "po:2": {"supplier": "sup:A", "part": "part:X", "unit_price": 5.2, "price_unit": 1},
        "po:3": {"supplier": "sup:B", "part": "part:X", "unit_price": 4.0, "price_unit": 1},
        "quote:9": {"supplier": "sup:A", "part": "part:X", "unit_price": 5.1, "price_unit": 1},
    }
    case = {"case_id": "c", "type": "raw_material", "suppliers": ["sup:A"], "parts": ["part:X"]}
    good = Claim("po_history", ("po:1", "po:2"), 5.2, "EUR", "", supplier_id="sup:A", part_id="part:X",
                 disclosure="supplier_own", subject="sup:A")
    good = Claim(**{**good.__dict__, "sentence": render(good, facts)})
    assert check(good, facts, None, case) is None
    assert "between EUR 5.00 and EUR 5.20" in good.sentence
    bad = Claim(**{**good.__dict__, "ids": ("po:1", "po:3")})
    assert check(Claim(**{**bad.__dict__, "sentence": render(bad, facts)}), facts, None, case) == "other supplier or part"
    single = Claim(**{**good.__dict__, "ids": ("po:1",), "figure": 5.0})
    assert check(Claim(**{**single.__dict__, "sentence": render(single, facts)}), facts, None, case) \
        == "needs two to eight order lines"
    wrong = Claim(**{**good.__dict__, "figure": 5.9})
    assert check(Claim(**{**wrong.__dict__, "sentence": render(wrong, facts)}), facts, None, case).startswith("figure")
    quote = Claim("own_quote", ("quote:9",), 5.1, "EUR", "", supplier_id="sup:A", part_id="part:X",
                  disclosure="supplier_own", subject="sup:A")
    quote = Claim(**{**quote.__dict__, "sentence": render(quote, facts)})
    assert check(quote, facts, None, case) is None
    assert check(Claim(**{**quote.__dict__, "disclosure": "public"}), facts, None, case) == "wrong disclosure"


def test_pacing_releases_one_claim_per_message_then_deeper_bank(package):
    case, sid = CASES["case:P18"], "sup:70740"
    ev = _policy(package, pacing=True)
    events = [_supplier(6.10)]
    sent = []
    for _ in range(6):
        out = ev.enrich(case, {sid: events}, sid, _move())
        refs = out["message"].get("refs") or []
        sent.append(refs)
        events = [*events, {"from": "buyer", **out["message"]}, _supplier(6.0)]
    non_empty = [r for r in sent if r]
    # one argument per message: index windows first (two series), then the deeper bank
    assert all(len({r.split("@")[0] for r in refs}) <= 1 or all(r.startswith("po:") for r in refs) for refs in non_empty)
    assert len(non_empty) >= 3
    assert non_empty[0] == ["idx:AS-14404@2026-06", "idx:AS-14404@2026-09"]
    kinds = ["po" if refs[0].startswith("po:") else refs[0].split(":")[0] for refs in non_empty]
    assert "po" in kinds and "sc" in kinds
    flat = [r for refs in non_empty for r in refs]
    assert len(flat) == len(set(flat))  # each ID once per case
    # exhausted: the last messages carry nothing new rather than repeating or inventing
    assert sent[-1] == []


def test_without_pacing_behaviour_is_unchanged(package):
    case, sid = CASES["case:P18"], "sup:70740"
    events = [_supplier(6.10)]
    out = _policy(package, pacing=False).enrich(case, {sid: events}, sid, _move())
    assert out["message"]["refs"] == ["idx:AS-14404@2026-06", "idx:AS-14404@2026-09",
                                      "idx:PPI-C2431@2026-06", "idx:PPI-C2431@2026-08"]
    events = [*events, {"from": "buyer", **out["message"]}, _supplier(6.0)]
    assert _policy(package, pacing=False).enrich(case, {sid: events}, sid, _move()) == _move()


def test_pacing_never_decorates_after_final_offer_and_skips_history_at_or_above_ask(package):
    case, sid = CASES["case:P18"], "sup:70740"
    ev = _policy(package, pacing=True)
    assert ev.enrich(case, {sid: [_supplier(6.10, "final_offer")]}, sid, _move()) == _move()
    # a supplier asking no more than our order price gets no order-history argument
    events = [_supplier(5.84)]
    refs = []
    for _ in range(6):
        out = ev.enrich(case, {sid: events}, sid, _move())
        refs += out["message"].get("refs") or []
        events = [*events, {"from": "buyer", **out["message"]}, _supplier(5.84)]
    assert not any(r.startswith("po:") for r in refs)


def test_p08_hedged_supplier_gets_history_not_index_claims(package):
    case, sid = CASES["case:P08"], "sup:70710"
    ev = _policy(package, pacing=True)
    events = [_supplier(6.05)]
    kinds = []
    for _ in range(4):
        out = ev.enrich(case, {sid: events}, sid, _move())
        refs = out["message"].get("refs") or []
        kinds += sorted({r.split(":")[0] for r in refs})
        events = [*events, {"from": "buyer", **out["message"]}, _supplier(6.0)]
    assert "idx" not in kinds and "quote" in kinds and "po" in kinds
