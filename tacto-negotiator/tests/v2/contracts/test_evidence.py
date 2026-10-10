import copy
from decimal import Decimal

import pytest

from tests.v2.support import inputs, require


def build(request, fixture):
    builder = require(request, "evidence.context").LayeredContextBuilder()
    data = inputs(request, fixture)
    return builder.build_context(data.prepared, data.case, data.server, data.documents, data.as_of)


def cost_record(context):
    return next(r for r in context.records if r.canonical_id == "cost:310010")


@pytest.mark.parametrize("removed,layer,amount", [
    ([], "case", "150.00"), (["case"], "release", "140.00"),
    (["case", "release"], "base", "132.64"),
])
def test_layer_precedence_and_winner_provenance(request, p10, removed, layer, amount):
    for name in removed:
        p10["evidence_layers"][name] = []
    result = build(request, p10)
    record = cost_record(result)
    assert record.payload.unit_cost.amount == Decimal(amount)
    assert record.provenance.layer == layer
    assert record.provenance.content_hash
    assert record.provenance.locator
    assert record.record_id != record.canonical_id
    if layer != "base":
        assert any(c.canonical_id == record.canonical_id and c.winning_record_id == record.record_id
                   for c in result.conflicts)


def test_case_override_replaces_record_without_filling_old_fields(request, p10):
    p10["evidence_layers"]["base"][0]["confidence_pct"] = "90"
    record = cost_record(build(request, p10))
    assert record.payload.confidence_pct is None
    assert record.payload.unit_cost.amount == Decimal("150.00")


def test_same_priority_conflict_is_blocking(request, p10):
    duplicate = {**p10["evidence_layers"]["case"][0], "amount": "151.00"}
    p10["evidence_layers"]["case"].append(duplicate)
    context = build(request, p10)
    conflict = next(c for c in context.conflicts if c.canonical_id == "cost:310010" and c.blocking)
    assert conflict.winning_record_id is None
    assert len(conflict.candidate_record_ids) == 2


@pytest.mark.parametrize("date_field,date_value,status", [
    ("published_at", "2027-01-01", "future"), ("valid_to", "2026-09-01", "stale"),
])
def test_temporal_validity_is_explicit(request, p10, date_field, date_value, status):
    p10["evidence_layers"]["case"][0][date_field] = date_value
    assert cost_record(build(request, p10)).temporal.status == status


@pytest.mark.parametrize("unit", [1, 100, 1000])
def test_basis_is_preserved_without_dividing_arena_prices(request, p10, unit):
    p10["evidence_layers"]["case"][0]["price_unit"] = unit
    record = cost_record(build(request, p10))
    assert record.payload.unit_cost.basis.price_unit == unit
    assert record.payload.unit_cost.amount == Decimal("150.00")
    assert record.disclosure.classification == "internal"


def test_scope_mismatch_never_becomes_supplier_cost(request, p10):
    p10["evidence_layers"]["case"][0]["supplier_id"] = "sup:OTHER"
    context = build(request, p10)
    assert not any(r.canonical_id == "cost:310010" for r in context.records)
    assert any(g.code == "scope_mismatch" for g in context.gaps)


def test_context_is_pure_deterministic_and_invalidates_on_fact_change(request, p10):
    original = copy.deepcopy(p10)
    first = build(request, p10)
    assert p10 == original
    assert build(request, p10) == first
    p10["evidence_layers"]["case"][0]["amount"] = "151.00"
    second = build(request, p10)
    assert first.context_version != second.context_version
    assert cost_record(first).record_id != cost_record(second).record_id


def test_case_and_economic_projections_use_one_resolved_cost_revision(request, p10):
    projector = require(request, "evidence.claims").EvidenceProjections()
    context = build(request, p10)
    claim = projector.internal_cost_claim(context, "cost:310010")
    estimate = projector.cost_input(context, "cost:310010")
    assert claim.source_refs == estimate.source_refs
    assert claim.figure == estimate.unit_cost.amount == Decimal("150.00")
    assert claim.disclosure.classification == "internal"
