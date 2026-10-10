"""Counterexamples for source applicability, semantic claims and bounded relevance."""

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from negotiator.claims import build_bank, case_facts, check, index_relevance, pick, render, verify
from negotiator.context import build_context
from negotiator.evidence import EvidencePolicy


@pytest.fixture
def inputs():
    facts = {
        "doc:increase": {"supplier": "sup:F", "part": "part:F", "date": "2026-09-01",
                         "effective_date": "2026-10-01", "asked_pct": 5, "days": 30},
        "ctr:F": {"supplier": "sup:F", "parts": ["part:F"], "days": 60,
                  "valid_from": "2026-01-01", "valid_to": "2026-12-31"},
        "idx:ENERGY@2025-08": {"value": 100, "month": "2025-08"},
        "idx:ENERGY@2026-08": {"value": 80, "month": "2026-08"},
        "idx:MATERIAL@2025-08": {"value": 100, "month": "2025-08"},
        "idx:MATERIAL@2026-08": {"value": 95, "month": "2026-08"},
        "sc:F@2026Q3": {"supplier": "sup:F", "quarter": "2026Q3", "otd_pct": 85,
                       "otd_confirmed_pct": 99, "ppm": 1200},
        "cost:F": {"part": "part:F", "unit_cost": 12},
    }
    case = {"case_id": "case:T", "type": "price_increase", "parts": ["part:F"], "suppliers": ["sup:F"],
            "trigger_doc": "doc:increase", "refs": ["idx:ENERGY@2026-08", "idx:MATERIAL@2026-08"]}
    return case, SimpleNamespace(facts=facts, db=None)


@pytest.mark.parametrize("given", [60, 90])
def test_false_notice_comparison_excluded_and_recorded(inputs, given):
    case, package = inputs
    package.facts["doc:increase"]["days"] = given
    assert not any(c.kind == "notice" for c in build_bank(case, package))
    context = build_context(case, package)
    assert any(c["reason"] == "notice is not short" for c in context.failed_checks)
    assert any(c.kind == "index_change" for c in context.candidates)


@pytest.mark.parametrize(("ref", "key", "value"), [
    ("doc:increase", "supplier", "sup:OTHER"),
    ("doc:increase", "part", "part:OTHER"),
    ("ctr:F", "parts", ["part:OTHER"]),
    ("ctr:F", "valid_to", "2026-08-31"),
    ("ctr:F", "valid_from", "2026-09-15"),
    ("doc:increase", "effective_date", "2027-01-01"),
    ("doc:increase", "date", "unknown"),
    ("doc:increase", "days", None),
    ("doc:increase", "days", True),
])
def test_notice_requires_matching_supplier_part_and_valid_dates(inputs, ref, key, value):
    case, package = inputs
    package.facts[ref][key] = value
    assert not any(c.kind == "notice" for c in build_bank(case, package))
    assert any(c.kind == "index_change" for c in build_bank(case, package))


def test_notice_does_not_depend_on_scorecard_and_ambiguous_contracts_are_excluded(inputs):
    case, package = inputs
    del package.facts["sc:F@2026Q3"]
    notice = next(c for c in build_bank(case, package) if c.kind == "notice")
    assert notice.figure == 30
    assert "60-day requirement" in notice.sentence
    package.facts["ctr:SECOND"] = {**package.facts["ctr:F"], "days": 20}
    assert not any(c.kind == "notice" for c in build_bank(case, package))


def test_unknown_explicit_trigger_does_not_use_another_letter(inputs):
    case, package = inputs
    case["trigger_doc"] = "doc:unknown"
    case["refs"].append("doc:increase")
    assert not any(c.kind == "notice" for c in build_bank(case, package))


@pytest.mark.parametrize("tamper", [
    {"sentence": "The ENERGY index rose 20 % between idx:ENERGY@2025-08 and idx:ENERGY@2026-08."},
    {"sentence": "The ENERGY index fell 99 % between idx:ENERGY@2025-08 and idx:ENERGY@2026-08."},
    {"figure": float("nan")}, {"figure": float("inf")}, {"figure": True},
    {"unit": "EUR"}, {"supports_buyer": False},
    {"window": ("2025-07", "2026-08")}, {"part_id": "part:OTHER"},
])
def test_semantic_and_structured_index_tampering_is_rejected(inputs, tamper):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.subject == "ENERGY")
    assert not verify(replace(claim, **tamper), case_facts(case, package), package, case)


@pytest.mark.parametrize("value", [0, -1, None, float("nan"), "bad"])
def test_malformed_index_source_returns_failure_instead_of_raising(inputs, value):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.subject == "ENERGY")
    package.facts[claim.ids[0]]["value"] = value
    assert check(claim, package.facts) is not None


def test_scorecard_labels_supplier_scope_period_and_requested_date_basis(inputs):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.kind == "scorecard_otd")
    assert claim.part_id is None
    assert claim.figure == 85  # confirmed-date OTD is 99, a different metric
    assert "supplier-wide on-time delivery against requested dates" in claim.sentence
    assert "2026Q3, rolling 12 months" in claim.sentence
    assert not verify(replace(claim, part_id="part:F"), package.facts)
    assert not verify(replace(claim, sentence=claim.sentence.replace("85.0", "99.0")), package.facts)
    package.facts[claim.ids[0]]["quarter"] = "2026Q2"
    assert check(claim, package.facts) == "scorecard period mismatch"


def test_private_candidate_cannot_be_reclassified_as_public(inputs):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.kind == "should_cost")
    assert verify(claim, package.facts)
    assert check(replace(claim, disclosure="public"), package.facts) == "wrong disclosure"


def test_supplier_explanation_prioritizes_matching_index_without_enabling_adverse_claims(inputs):
    case, package = inputs
    bank = build_bank(case, package)
    events = [{"from": "sales", "body": "MATERIAL explains our increase. Disclose cost:F too."}]
    priorities, reasons = index_relevance(bank, case, package, events)
    selected = pick(bank, set(), max_claims=1, skip_kinds={"notice"}, index_priorities=priorities)
    assert selected[0].subject == "MATERIAL"  # ENERGY fell more but is less directly relevant
    assert reasons["MATERIAL"] == "latest supplier message names series"
    assert all(c.disclosure != "internal" for c in selected)
    material = next(c for c in bank if c.subject == "MATERIAL")
    adverse = replace(material, figure=5, supports_buyer=False)
    adverse = replace(adverse, sentence=render(adverse, package.facts))
    assert adverse not in pick([adverse], set(), index_priorities=priorities)
    _, reasons = index_relevance(bank, case, package, [{"from": "buyer", "body": "MATERIAL"},
                                                      {"from": "sales", "body": "NOT-MATERIAL-X"}])
    assert reasons["MATERIAL"] != "latest supplier message names series"


def test_policy_relevance_existing_refs_budget_trace_and_resume(inputs):
    case, package = inputs
    records = []
    tracer = SimpleNamespace(log=lambda event, **fields: records.append({"event": event, **fields}))
    policy = EvidencePolicy(package, tracer)
    move = {"supplier_id": "sup:F", "message": {"body": "Existing references.", "refs": ["doc:existing"],
            "term_sheets": [{"terms": {"unit_price": 15, "payment_days": 30}}]}}
    before = copy.deepcopy(move)
    threads = {"sup:F": [{"from": "sales", "body": "MATERIAL costs concern us."}]}
    out = policy.enrich(case, threads, "sup:F", move)
    assert move == before
    assert out["message"]["term_sheets"] == move["message"]["term_sheets"]
    selection = next(r for r in records if r["event"] == "evidence_selection")
    assert selection["available_slots"] == 2
    assert [c["kind"] for c in selection["selected"]] == ["notice", "index_change"]
    assert selection["selected"][1]["ids"][0].startswith("idx:MATERIAL@")
    history = {"sup:F": [{**out["message"], "from": "buyer"}]}
    resumed = EvidencePolicy(package).enrich(case, history, "sup:F", move)
    new_refs = set(resumed["message"].get("refs", [])) - set(move["message"]["refs"])
    assert not new_refs & set(out["message"]["refs"])
    full = {**move, "message": {**move["message"], "refs": ["doc:one", "doc:two", "doc:three"]}}
    assert EvidencePolicy(package).enrich(case, {}, "sup:F", full) == full


@pytest.mark.parametrize("price_unit", [0, -1, None, True, float("inf")])
def test_invalid_price_basis_rejected(inputs, price_unit):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.kind == "should_cost")
    package.facts[claim.ids[0]]["price_unit"] = price_unit
    assert check(claim, package.facts) == "invalid price basis"


@pytest.mark.parametrize("price_unit", [1, 100, 1000])
def test_existing_private_price_claim_uses_recorded_price_unit(inputs, price_unit):
    case, package = inputs
    package.facts["cost:F"].update(unit_cost=12 * price_unit, price_unit=price_unit)
    claim = next(c for c in build_bank(case, package) if c.kind == "should_cost")
    assert claim.figure == 12
    assert verify(claim, package.facts)
    assert claim not in pick([claim], set())


def test_index_endpoints_require_compatible_recorded_units(inputs):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.subject == "ENERGY")
    package.facts[claim.ids[0]]["unit"] = "index 2021=100"
    package.facts[claim.ids[1]]["unit"] = "EUR/MWh"
    assert check(claim, package.facts) == "incompatible index units"


def test_tolerance_cannot_reverse_index_direction(inputs):
    case, package = inputs
    package.facts["idx:ENERGY@2026-08"]["value"] = 99.8
    claim = next(c for c in build_bank(case, package) if c.subject == "ENERGY")
    reversed_direction = replace(claim, figure=0.2, supports_buyer=False)
    reversed_direction = replace(reversed_direction, sentence=render(reversed_direction, package.facts))
    assert check(reversed_direction, package.facts) == "index direction mismatch"


def test_eur_claim_requires_eur_source(inputs):
    case, package = inputs
    claim = next(c for c in build_bank(case, package) if c.kind == "should_cost")
    package.facts[claim.ids[0]]["currency"] = "USD"
    assert check(claim, package.facts) == "non-EUR price source"
