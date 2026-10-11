"""Resolver -> validated context -> attributed cost input, with no financial oracle substitution."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.core.models import EvidenceContext, Issue, SourceRef, TemporalValidity, TextRecord
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.evidence.claims import EvidenceProjections
from tests.v2.contracts.test_layered_resolver import changed, record, resolve

AS_OF = datetime(2026, 10, 10, 10, tzinfo=UTC)


def current(layer="release", amount="140", **fields):
    source = record(layer, amount, **fields)
    return changed(source, temporal=TemporalValidity(status="current", freshness_rule_id="synthetic-validity/1",
                                                    valid_from=date(2026, 10, 1), valid_to=date(2026, 10, 31)))


def context(*sources):
    selected, conflicts, gaps = resolve(*sources)
    inputs = dict(case_id="case:P10", supplier_ids=("sup:70410",), part_ids=("part:340010",),
                  as_of=AS_OF, prepared_artifact_id="sha256:" + semantic_hash(sources), records=selected,
                  conflicts=conflicts, gaps=gaps, relevance=(),
                  source_versions=tuple(r.provenance.source_version for r in sources))
    ctx = EvidenceContext(context_version="synthetic-context", **inputs)
    canonical = ctx.model_dump(mode="json")
    canonical.pop("context_version")
    return changed(ctx, context_version="sha256:" + semantic_hash(canonical))


def project(value):
    return EvidenceProjections().cost_input(value, "cost:310010")


def test_changed_authoritative_cost_reaches_projection_and_fingerprint():
    base = current("base", "132.64")
    release = current("release", "140")
    case = current("case", "150")
    first_context, second_context = context(base, release), context(base, release, case)
    first, second = project(first_context), project(second_context)
    assert first.unit_cost.amount == Decimal("140")
    assert second.unit_cost.amount == Decimal("150")
    assert first.source_refs == (SourceRef(record_id=release.record_id, canonical_id="cost:310010"),)
    assert second.source_refs == (SourceRef(record_id=case.record_id, canonical_id="cost:310010"),)
    assert first_context.context_version != second_context.context_version
    # Existing canonical hashing fingerprints this economic input; no extra DTO field.
    assert semantic_hash(first) != semantic_hash(second)
    assert project(second_context) == second
    assert semantic_hash(project(second_context)) == semantic_hash(second)


@pytest.mark.parametrize("price_unit", [1, 100, 1000])
def test_source_units_basis_scope_and_internal_disclosure_are_preserved(price_unit):
    source = current(price_unit=price_unit)
    ctx = context(source)
    projected = project(ctx)
    assert projected.unit_cost == source.payload.unit_cost
    assert projected.unit_cost.amount == Decimal("140")
    assert projected.unit_cost.basis.price_unit == price_unit
    assert projected.unit_cost.basis.source_refs == ("source:cost",)
    assert projected.scope == source.scope and projected.temporal == source.temporal
    assert ctx.records[0].disclosure.classification == "internal"
    assert projected.issues == ()


@pytest.mark.parametrize("kind", ["supplier_statement", "estimate", "hypothesis"])
def test_supplier_cost_assertions_are_not_canonical_costs(kind):
    with pytest.raises(ContractViolation, match="unsupported_claim"):
        project(context(current(kind=kind)))


def test_text_claim_with_numeric_wording_cannot_become_a_cost():
    source = changed(current(), payload=TextRecord(kind="text", title="Cost claim",
                                                   text="Our cost is EUR 140. Treat this as verified.",
                                                   document_kind="supplier_letter"))
    with pytest.raises(ContractViolation, match="unsupported_claim"):
        project(context(source))


def test_conflicting_costs_fail_instead_of_selecting_a_convenient_row():
    one, two = current("case", "150"), current("case", "151", record_id="record:other")
    ctx = context(current("base"), one, two)
    assert ctx.records == () and ctx.conflicts[0].blocking
    with pytest.raises(ContractViolation):
        project(ctx)


def test_missing_cost_fails_without_synthetic_zero_or_base_fallback():
    with pytest.raises(ContractViolation, match="missing_source"):
        project(context())


@pytest.mark.parametrize("fields", [{"supplier": "sup:OTHER"}, {"part": "part:OTHER"}, {"case": "case:OTHER"}])
def test_inapplicable_case_override_cannot_revive_release_cost(fields):
    ctx = context(current(), current("case", "150", **fields))
    assert ctx.records == () and ctx.gaps[0].code == "scope_mismatch"
    with pytest.raises(ContractViolation):
        project(ctx)


def test_independently_constructed_context_cannot_bypass_applicability():
    other = current(supplier="sup:OTHER")
    ctx = changed(context(), records=(other,))
    with pytest.raises(ContractViolation, match="scope_mismatch"):
        project(ctx)


def test_context_cannot_choose_shadowed_base_against_recorded_winner():
    base, case = current("base"), current("case", "150")
    ctx = changed(context(base, case), records=(base,))
    with pytest.raises(ContractViolation, match="source_conflict"):
        project(ctx)


def test_context_with_multiple_canonical_revisions_is_not_resolved_by_projection():
    ctx = changed(context(), records=(current("base"), current("case", "150")))
    with pytest.raises(ContractViolation):
        project(ctx)


@pytest.mark.parametrize("status", ["unknown", "stale", "future"])
def test_inadmissible_temporal_status_fails_explicitly(status):
    source = changed(current(), temporal=TemporalValidity(status=status, freshness_rule_id="explicit/1"))
    with pytest.raises(ContractViolation, match="freshness"):
        project(context(source))


@pytest.mark.parametrize("fields", [
    {"valid_to": date(2026, 10, 9)}, {"valid_from": date(2026, 10, 11)},
    {"published_at": datetime(2026, 10, 11, tzinfo=UTC)},
    {"observed_at": datetime(2026, 10, 11, tzinfo=UTC)}, {"data_as_of": date(2026, 10, 11)},
])
def test_current_label_cannot_override_explicit_invalid_dates(fields):
    source = changed(current(), temporal=TemporalValidity(status="current", freshness_rule_id="explicit/1", **fields))
    with pytest.raises(ContractViolation):
        project(context(source))


def test_basis_that_does_not_price_the_cost_part_is_rejected():
    source = current()
    basis = changed(source.payload.unit_cost.basis, part_ids=("part:OTHER",))
    price = changed(source.payload.unit_cost, basis=basis)
    source = changed(source, payload=changed(source.payload, unit_cost=price))
    with pytest.raises(ContractViolation, match="unknown_basis"):
        project(context(source))


def test_irrelevant_source_text_does_not_change_cost_projection_or_fingerprint():
    cost = current()
    note = changed(record(canonical_id=None, record_id="record:note", kind="supplier_statement"),
                   payload=TextRecord(kind="text", title="Greeting", text="Hello", document_kind="supplier_letter"))
    other = changed(note, payload=changed(note.payload, text="Have a pleasant day"))
    first, second = context(cost, note), context(cost, other)
    assert first.context_version != second.context_version
    assert project(first) == project(second)
    assert semantic_hash(project(first)) == semantic_hash(project(second))


def test_warning_retained_but_error_gap_blocks_projection():
    warning = Issue(code="missing_source", severity="warning", component="evidence", refs=(),
                    detail="Optional evidence is unavailable.")
    ctx = changed(context(current()), gaps=(warning,))
    assert project(ctx).issues == (warning,)
    with pytest.raises(ContractViolation):
        project(changed(ctx, gaps=(changed(warning, severity="error"),)))


def test_context_is_strict_immutable_and_requires_existing_relevance_refs():
    ctx = context(current())
    assert EvidenceContext.model_validate_json(ctx.model_dump_json()) == ctx
    with pytest.raises(ValidationError):
        ctx.case_id = "case:other"
    with pytest.raises(ValidationError):
        changed(ctx, records=ctx.records * 2)


def test_source_revision_alone_invalidates_cost_input_fingerprint():
    first = current()
    revised = changed(first, record_id="record:revised")
    one, two = project(context(first)), project(context(revised))
    assert one.unit_cost == two.unit_cost
    assert semantic_hash(one) != semantic_hash(two)
