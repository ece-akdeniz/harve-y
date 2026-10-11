"""Opt-in `claim_pacing`: one verified claim per kind per message, deeper bank after a deferral, nothing on finals."""

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
    return {"supplier_id": "sup:70740",
            "message": {"body": "Offer.", "term_sheets": [{"terms": {"unit_price": price}}]}}


def _supplier(price, status="open"):
    return {"from": "supplier", "status": status, "body": "Our price.",
            "term_sheets": [{"terms": {"unit_price": price}}]}


def test_history_claims_verify_against_facts_and_stay_below_current_price(package):
    for cid in ("case:P08", "case:P18", "case:P01", "case:P02"):
        case = CASES[cid]
        facts = case_facts(case, package)
        claims = history_claims(case, package)
        assert claims, cid
        case_quotes = set(case["refs"]) | {case["buyer"]["alternative"]["ref"]}
        for c in claims:
            assert check(c, facts, package, case) is None
            assert c.disclosure == "supplier_own" and c.supplier_id in case["suppliers"]
            assert c.figure <= case["buyer"]["current_unit_price"] + 1e-9
            assert all(i in c.sentence for i in c.ids)
            if c.kind == "po_history":
                assert 2 <= len(c.ids) <= 8 and all(i.startswith("po:") for i in c.ids)
                assert all(facts[i]["part"] == case["parts"][0] for i in c.ids)
            else:
                assert c.kind == "own_quote" and c.ids[0].startswith("quote:") and c.ids[0] in case_quotes
    # the supplier's own quotes of these cases (quote:7300008, quote:7300001) are outside the refs: a quote
    # counts only when it is "of this case (in its refs or your alternative)" - hosted run 9a4fbb93 had
    # quote:7300008 rated `irrelevant` and read as a rival quote
    for cid in ("case:P08", "case:P01"):
        assert [c.kind for c in history_claims(CASES[cid], package)] == ["po_history"], cid
    assert history_claims(CASES["case:P05"], package) == []  # no orders with the RFQ bidders


def test_own_quote_only_when_the_quote_is_a_case_ref_or_the_alternative(package):
    base = CASES["case:P08"]
    assert not [c for c in history_claims(base, package) if c.kind == "own_quote"]
    in_refs = {**base, "refs": [*base["refs"], "quote:7300008"]}
    [own] = [c for c in history_claims(in_refs, package) if c.kind == "own_quote"]
    assert own.ids == ("quote:7300008",) and own.figure == 5.45 and own.in_case_refs
    assert check(own, case_facts(in_refs, package), package, in_refs) is None
    as_alt = {**base, "buyer": {**base["buyer"], "alternative": {"kind": "quote", "ref": "quote:7300008", "terms": {}}}}
    [own] = [c for c in history_claims(as_alt, package) if c.kind == "own_quote"]
    assert own.ids == ("quote:7300008",) and not own.in_case_refs and "buyer alternative" in own.note
    # order lines carry no such qualifier (api.md lists `po` plainly): unchanged either way
    assert [c.ids for c in history_claims(base, package) if c.kind == "po_history"] \
        == [c.ids for c in history_claims(in_refs, package) if c.kind == "po_history"]


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
    bad = Claim(**{**bad.__dict__, "sentence": render(bad, facts)})
    assert check(bad, facts, None, case) == "other supplier or part"
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
    assert all(len({r.split("@")[0] for r in refs}) <= 1 or all(r.startswith("po:") for r in refs)
               for refs in non_empty)
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


def test_p08_hedged_supplier_without_deferral_is_unchanged_by_pacing(package):
    """P08's hedged supplier gets no index window under v3 (empty preferred bank); pacing never deferred
    anything in that thread, so the deeper bank stays closed and the messages equal the flag-off ones."""
    case, sid = CASES["case:P08"], "sup:70710"
    ev, base = _policy(package, pacing=True), _policy(package, pacing=False)
    events = [_supplier(6.05)]
    for _ in range(4):
        out = ev.enrich(case, {sid: events}, sid, _move())
        assert out == base.enrich(case, {sid: events}, sid, _move()) == _move()
        events = [*events, {"from": "buyer", **out["message"]}, _supplier(6.0)]


def test_pacing_keeps_mixed_kind_bundles_together_and_defers_only_same_kind():
    """The decision rule behind v4: every bundle v3 sends in one message (P01 notice+index+scorecard,
    P11 scorecard+index) stays in that message; only a second claim of a kind already carried waits."""
    def claim(kind, *ids):
        return Claim(kind, ids, 1.0, "%", "s", supplier_id="sup:A", subject=ids[0])

    notice, idx_a, idx_b, sc = claim("notice", "doc:1", "ctr:1"), claim("index_change", "idx:A"), \
        claim("index_change", "idx:B"), claim("scorecard_otd", "sc:1")
    kept, deferred = EvidencePolicy.pace([notice, idx_a, sc])
    assert (kept, deferred) == ([notice, idx_a, sc], [])
    kept, deferred = EvidencePolicy.pace([idx_a, idx_b])
    assert (kept, deferred) == ([idx_a], [idx_b])
    kept, deferred = EvidencePolicy.pace([sc, idx_a, idx_b])
    assert (kept, deferred) == ([sc, idx_a], [idx_b])
    # the deeper bank opens only once two claims of one kind were sent in the thread
    bank = [notice, idx_a, idx_b, sc]
    one_each = [{"from": "buyer", "refs": ["doc:1", "ctr:1", "idx:A", "sc:1"]}]
    assert not EvidencePolicy.paced_before(bank, one_each)
    spread = [{"from": "buyer", "refs": ["idx:A"]}, {"from": "supplier"}, {"from": "buyer", "refs": ["idx:B"]}]
    assert EvidencePolicy.paced_before(bank, spread)
    assert not EvidencePolicy.paced_before(bank, [])


def test_pacing_first_message_of_p01_and_p11_equals_v3(package):
    """Round 1 of the validated runs: P01 (.9602/.9702) notice + PPI-D351 + scorecard, P11 (.8771)
    scorecard + PPI-D351 - identical with and without `claim_pacing`; P18 defers PPI-C2431 to message 2."""
    for cid, sid, price in (("case:P01", "sup:70110", 140.0), ("case:P11", "sup:70140", 46.0)):
        case = CASES[cid]
        events = [{**_supplier(price), "status": "open"}]
        move = {**_move(price), "supplier_id": sid}
        on = _policy(package, pacing=True).enrich(case, {sid: events}, sid, move)
        off = _policy(package, pacing=False).enrich(case, {sid: events}, sid, move)
        assert on == off and len(on["message"]["refs"]) >= 2, cid
    case, sid = CASES["case:P18"], "sup:70740"
    ev = _policy(package, pacing=True)
    first = ev.enrich(case, {sid: [_supplier(6.10)]}, sid, _move())
    assert first["message"]["refs"] == ["idx:AS-14404@2026-06", "idx:AS-14404@2026-09"]
    events = [_supplier(6.10), {"from": "buyer", **first["message"]}, _supplier(5.40)]
    second = ev.enrich(case, {sid: events}, sid, _move(5.39))
    assert second["message"]["refs"] == ["idx:PPI-C2431@2026-06", "idx:PPI-C2431@2026-08"]
    events = [*events, {"from": "buyer", **second["message"]}, _supplier(5.30)]
    third = ev.enrich(case, {sid: events}, sid, _move(5.40))
    assert third["message"]["refs"] == ["sc:70740@2026Q3"]  # deeper bank, as in the 0.5325 run
