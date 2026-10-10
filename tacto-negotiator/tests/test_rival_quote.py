"""Opt-in public rival-quote disclosure (`rival_quote_types`): cost-based, valid, once per thread."""

import json
from pathlib import Path

import pytest

from negotiator.claims import public_rival_quotes
from negotiator.dossiers import load_package
from negotiator.evidence import EvidencePolicy
from negotiator.policy import PolicyConfig

CASES = {c["case_id"]: c for c in json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())}
CLAUSE = {"series": "AS-14404", "material_share": 0.45, "deadband_pct": 0, "base_month": "2026-08"}


@pytest.fixture(scope="module")
def pkg():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def thread(*sheets):
    return [{"from": "sales", "status": "open", "term_sheets": [{"term_sheet_id": f"o:{i}", "terms": s}]}
            for i, s in enumerate(sheets)]


def test_policy_field_validates():
    assert PolicyConfig.from_dict({"version": 1, "rival_quote_types": ["raw_material"]}).rival_quote_types == (
        "raw_material",)
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "rival_quote_types": ["nope"]})


def test_public_rival_quotes_are_valid_other_supplier_quotes(pkg):
    found = {c.ids[0]: (c, t) for c, t in public_rival_quotes(CASES["case:P18"], pkg)}
    assert "quote:7300008" in found  # sup:70710, 2026-09-10, 90 days valid on 2026-09-22
    assert "quote:7100064" not in found  # 2025 quote, expired
    claim, terms = found["quote:7300008"]
    assert claim.supplier_id == "sup:70740" and claim.subject == "sup:70710" and claim.figure == 5.45
    assert terms["index_clause"] is None and terms["payment_days"] == 30


def test_cited_only_when_complete_cost_beats_standing_sheet(pkg):
    ev = EvidencePolicy(package=pkg, case_types=["raw_material"], rival_quote_types=["raw_material"])
    case = CASES["case:P18"]
    dear = {"unit_price": 5.60, "payment_days": 90, "index_clause": CLAUSE, "contract_months": 24}
    cheap = {"unit_price": 5.20, "payment_days": 90, "index_clause": CLAUSE, "contract_months": 24}
    assert [c.ids for c in ev.cheaper_rivals(case, thread(dear), "sup:70740")] == [("quote:7300008",)]
    assert ev.cheaper_rivals(case, thread(cheap), "sup:70740") == []
    cited = [{"from": "buyer", "refs": ["quote:7300008"]}] + thread(dear)
    assert ev.cheaper_rivals(case, cited, "sup:70740") == []
    # P08's only valid rival (sup:70740 at 6.06) costs more than the supplier's standing sheet.
    assert ev.cheaper_rivals(CASES["case:P08"], thread(dear), "sup:70710") == []


def test_off_by_default(pkg):
    ev = EvidencePolicy(package=pkg, case_types=["raw_material"])
    dear = {"unit_price": 5.60, "payment_days": 90, "index_clause": CLAUSE, "contract_months": 24}
    assert ev.cheaper_rivals(CASES["case:P18"], thread(dear), "sup:70740") == []


def test_recent_index_window_only_when_opted_in(pkg):
    from negotiator.claims import build_bank

    bank = build_bank(CASES["case:P18"], pkg)
    recent = [c for c in bank if c.note.startswith("recent buyer window")]
    assert {(c.subject, c.window) for c in recent} >= {("AS-14404", ("2026-06", "2026-09"))}
    assert all(c.cherry_picked and c.supports_buyer for c in recent)
    assert PolicyConfig.from_dict({"version": 1, "index_window_types": ["raw_material"]}).index_window_types == (
        "raw_material",)
