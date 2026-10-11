"""Direct source-resolution acceptance, independent of codec and orchestration."""

import json
from decimal import Decimal
from itertools import permutations

import pytest
from pydantic import ValidationError

from negotiator.v2.core.models import (
    Conflict,
    CostFact,
    DisclosureRule,
    EstimateRecord,
    EvidenceRecord,
    EvidenceScope,
    IndexFact,
    NamedEstimate,
    Price,
    PriceBasis,
    Provenance,
    QuoteFact,
    ScorecardFact,
    TemporalValidity,
    TextRecord,
)
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.evidence.resolver import LayeredEvidenceResolver
from tests.v2.dto_spec import example


def record(layer="base", amount="132.64", *, record_id=None, canonical_id="cost:310010",
           kind="canonical", supplier="sup:70410", part="part:340010", case="case:P10",
           confidence=None, price_unit=1):
    basis = PriceBasis(currency="EUR", price_unit=price_unit, part_ids=(part,),
                       quantity_basis="arena-case-quantity", source_refs=("source:cost",))
    payload = CostFact(kind="cost", part=part, supplier=supplier,
                       unit_cost=Price(amount=Decimal(amount), basis=basis), confidence_pct=confidence)
    return EvidenceRecord(
        record_id=record_id or f"record:{layer}", canonical_id=canonical_id, kind=kind, payload=payload,
        scope=EvidenceScope(supplier_ids=(supplier,), part_ids=(part,), level="part", case_id=case),
        provenance=Provenance(layer=layer, source_version=f"synthetic-{layer}/1",
                              content_hash=semantic_hash(payload), locator=f"synthetic/{layer}/row/1",
                              parent_refs=()),
        temporal=TemporalValidity(status="unknown", freshness_rule_id="explicit/1"),
        disclosure=DisclosureRule(classification="internal", permitted_recipients=(), purpose=("cost_input",)),
    )


def changed(model, **fields):
    return type(model).model_validate({**model.model_dump(), **fields})


def resolve(*records, **targets):
    return LayeredEvidenceResolver().resolve(
        records, **{"case_id": "case:P10", "supplier_ids": ("sup:70410",),
                    "part_ids": ("part:340010",), **targets},
    )


@pytest.mark.parametrize("layers,winner,amount", [
    (("base",), "base", "132.64"),
    (("base", "release"), "release", "140.00"),
    (("base", "release", "case"), "case", "150.00"),
])
def test_layer_precedence_preserves_winner_and_shadowed_provenance(layers, winner, amount):
    amounts = {"base": "132.64", "release": "140.00", "case": "150.00"}
    sources = tuple(record(layer, amounts[layer]) for layer in layers)
    selected, conflicts, issues = resolve(*sources)
    assert selected == (sources[-1],)
    assert selected[0].payload.unit_cost.amount == Decimal(amount)
    assert selected[0].provenance.layer == winner
    assert issues == ()
    if len(sources) > 1:
        assert conflicts[0].winning_record_id == sources[-1].record_id
        assert set(conflicts[0].candidate_record_ids) == {r.record_id for r in sources}
        assert not conflicts[0].blocking
    else:
        assert conflicts == ()


def test_whole_record_replacement_does_not_restore_omitted_fields():
    base = record(confidence=Decimal("90"))
    raw = record("case", "150").model_dump(mode="json")
    raw["payload"].pop("confidence_pct")
    case = EvidenceRecord.model_validate_json(json.dumps(raw))
    selected, _, _ = resolve(base, case)
    assert selected == (case,)
    assert selected[0].payload.confidence_pct is None


@pytest.mark.parametrize("amount", ["150", "151"])
def test_equal_priority_distinct_revisions_block_even_with_identical_values(amount):
    one = record("case", "150")
    two = record("case", amount, record_id="record:case-other")
    selected, conflicts, issues = resolve(record(), one, two)
    assert selected == ()
    assert conflicts[0].blocking and conflicts[0].winning_record_id is None
    assert conflicts[0].candidate_record_ids == ("record:case", "record:case-other")
    assert issues[0].code == "source_conflict"


def test_lower_priority_collision_does_not_block_unique_case_override():
    base = record()
    other = record(record_id="record:base-other", amount="130")
    case = record("case", "150")
    selected, conflicts, issues = resolve(base, other, case)
    assert selected == (case,) and issues == ()
    assert not conflicts[0].blocking and len(conflicts[0].candidate_record_ids) == 3


def test_identical_replays_collapse_without_consuming_or_changing_records():
    base, case = record(), record("case", "150")
    assert resolve(base, case, base, case) == resolve(base, case)


def test_contradictory_record_identity_blocks_affected_groups_only():
    base = record()
    collision = record(amount="999", canonical_id="cost:other")
    case = record("case", "150")
    separate = record(record_id="record:unrelated", canonical_id="cost:unrelated")
    selected, conflicts, issues = resolve(base, collision, case, separate)
    assert selected == (separate,)
    assert conflicts == ()
    assert issues[0].code == "source_conflict" and issues[0].refs == (base.record_id,)


@pytest.mark.parametrize("target", [{"supplier": "sup:OTHER"}, {"part": "part:OTHER"}, {"case": "case:OTHER"}])
def test_inapplicable_winner_never_revives_applicable_base(target):
    case = record("case", "150", **target)
    selected, conflicts, issues = resolve(record(), case)
    assert selected == ()
    assert conflicts[0].winning_record_id == case.record_id
    assert issues[0].code == "scope_mismatch" and issues[0].refs == (case.record_id,)


def test_payload_ownership_cannot_be_broadened_by_outer_scope():
    case = record("case", "150", supplier="sup:OTHER")
    case = changed(case, scope=EvidenceScope(supplier_ids=(), part_ids=(), level="global"))
    assert resolve(record(), case)[0] == ()
    assert resolve(record(), case)[2][0].code == "scope_mismatch"


def test_unkeyed_statements_remain_distinct_and_unverified():
    one = record(canonical_id=None, kind="supplier_statement")
    one = changed(one, payload=TextRecord(kind="text", title="Supplier report", text="Cost rose 5%",
                                         document_kind="supplier_letter", declared_role="sales"))
    two = changed(one, record_id="record:statement-2")
    selected, conflicts, issues = resolve(two, one)
    assert selected == (one, two) and conflicts == issues == ()
    assert all(r.kind == "supplier_statement" and r.canonical_id is None for r in selected)


def test_shared_identifier_never_promotes_statement_or_hypothesis_to_fact():
    for kind in ("supplier_statement", "hypothesis", "estimate"):
        reported = record("case", "150", kind=kind)
        selected, _, _ = resolve(record(), reported)
        assert selected == (reported,) and selected[0].kind == kind


@pytest.mark.parametrize("layer", ["session", "derived"])
def test_unsupported_layer_blocks_affected_identity_without_fallback(layer):
    selected, _, issues = resolve(record(), record(layer, "150"))
    assert selected == ()
    assert issues[0].code == "unsupported_capability"


@pytest.mark.parametrize("status", ["unknown", "stale", "future", "current"])
@pytest.mark.parametrize("price_unit", [1, 100, 1000])
def test_basis_disclosure_and_temporal_status_are_preserved_without_conversion(status, price_unit):
    case = record("case", "150", price_unit=price_unit)
    case = changed(case, temporal=TemporalValidity(status=status, freshness_rule_id="explicit/1"))
    selected, _, _ = resolve(record(), case)
    assert selected[0] is case
    assert selected[0].payload.unit_cost.amount == Decimal("150")
    assert selected[0].payload.unit_cost.basis.price_unit == price_unit
    assert selected[0].disclosure.classification == "internal"
    assert selected[0].temporal.status == status


def test_deterministic_resolution_does_not_mutate_input():
    records = (record(), record("release", "140"), record("case", "150"))
    snapshots = tuple(r.model_dump_json() for r in records)
    result = resolve(*records)
    assert all(resolve(*order) == result for order in permutations(records))
    assert tuple(r.model_dump_json() for r in records) == snapshots
    with pytest.raises(ValidationError):
        records[0].payload.unit_cost.amount = Decimal("999")


def test_unkeyed_record_id_cannot_collide_with_a_canonical_namespace():
    one = record(record_id="same", canonical_id=None)
    two = record(record_id="other", canonical_id="same")
    selected, conflicts, issues = resolve(one, two)
    assert set(r.record_id for r in selected) == {"same", "other"}
    assert conflicts == issues == ()


def test_inapplicable_record_does_not_hide_same_priority_conflict():
    one = record("case", "150")
    other = record("case", "151", record_id="record:other", supplier="sup:OTHER")
    selected, conflicts, issues = resolve(record(), one, other)
    assert selected == () and conflicts[0].blocking
    assert issues[0].code == "source_conflict"


def test_conflict_diagnostics_are_validated_contract_objects():
    with pytest.raises(ValidationError):
        Conflict(canonical_id="cost:1", candidate_record_ids=("record:1", "record:2"),
                 winning_record_id="record:1", blocking=True, rule_id="rule:1", reason_code="collision")


def test_resolver_rejects_untyped_mutable_input():
    with pytest.raises(TypeError):
        LayeredEvidenceResolver().resolve([record()], case_id="case:P10",
                                         supplier_ids=("sup:70410",), part_ids=("part:340010",))


@pytest.mark.parametrize("value", [True, 1, 1.5, "NaN", "Infinity", "not-a-number"])
def test_evidence_decimals_reject_non_string_json_and_nonfinite_content(value):
    with pytest.raises(ValidationError):
        IndexFact.model_validate_json(json.dumps({**example("IndexFact"), "value": value}))


@pytest.mark.parametrize("month", ["0000-01", "2026-00", "2026-1", "２０２６-10"])
def test_calendar_labels_require_real_ascii_year_and_month(month):
    with pytest.raises(ValidationError):
        IndexFact.model_validate_json(json.dumps({**example("IndexFact"), "month": month}))
    with pytest.raises(ValidationError):
        ScorecardFact.model_validate_json(json.dumps({**example("ScorecardFact"), "quarter": "0000Q1"}))


@pytest.mark.parametrize("patch", [
    {"unit": "fraction"}, {"basis": None}, {"range_high": None},
    {"range_low": "48"}, {"range_low": "0"}, {"value": "0", "range_low": None, "range_high": None},
])
def test_estimate_units_bounds_and_positive_cost_domain_are_independent_requirements(patch):
    with pytest.raises(ValidationError):
        NamedEstimate.model_validate_json(json.dumps({**example("NamedEstimate"), **patch}))


def test_estimate_assumptions_and_unique_names_are_required():
    raw = example("EstimateRecord")
    for patch in ({"assumptions": []}, {"values": raw["values"] * 2}):
        with pytest.raises(ValidationError):
            EstimateRecord.model_validate_json(json.dumps({**raw, **patch}))


def test_quote_checks_price_basis_and_unique_observed_fields():
    raw = example("QuoteFact")
    for patch in ({"part_ids": ["part:OTHER"]}, {"part_ids": raw["part_ids"] * 2},
                  {"observed_terms": [example("TermBinding")] * 2}):
        with pytest.raises(ValidationError):
            QuoteFact.model_validate_json(json.dumps({**raw, **patch}))


def test_estimates_scorecards_and_supersession_cannot_acquire_wrong_authority():
    raw = example("EvidenceRecord")
    for patch in ({"payload": example("EstimateRecord")}, {"supersedes": raw["record_id"]},
                  {"payload": example("ScorecardFact")}):
        with pytest.raises(ValidationError):
            EvidenceRecord.model_validate_json(json.dumps({**raw, **patch}))
