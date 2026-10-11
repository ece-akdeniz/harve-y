"""Resolver-backed observations -> explicit estimates -> unchanged legal package comparisons."""

from decimal import Decimal

import pytest
from arena_kit import cost as kit

from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.core.models import (
    EstimateRecord,
    EvidenceContext,
    FieldOrigin,
    NamedEstimate,
    Price,
    ResolvedStandards,
    SourceRef,
    TextRecord,
)
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.economics.estimates import SourceCostEstimateBuilder
from negotiator.v2.economics.official import _version
from negotiator.v2.evidence.claims import EvidenceProjections
from negotiator.v2.evidence.resolver import LayeredEvidenceResolver

from .test_cost_projection import AS_OF, current
from .test_layered_resolver import changed
from .test_official_adapter import resolved
from .test_package_evaluation import context_for, evaluate, package


def source(relationship, amount, layer="release", revision=None):
    basis = context_for(relationship["case"], relationship["declared_fixture_basis"]).case.parts[0].price_basis
    r = current(layer, str(amount), supplier="sup:F", part=basis.part_ids[0], case="case:T01")
    r = changed(r, payload=changed(r.payload, unit_cost=Price(amount=Decimal(str(amount)), basis=basis)))
    return changed(r, record_id=revision or "sha256:" + semantic_hash(r))


def evidence(*sources):
    selected, conflicts, gaps = LayeredEvidenceResolver().resolve(
        tuple(sources), case_id="case:T01", supplier_ids=("sup:F",), part_ids=sources[0].scope.part_ids,
    )
    c = EvidenceContext(case_id="case:T01", supplier_ids=("sup:F",), part_ids=sources[0].scope.part_ids,
                        as_of=AS_OF, prepared_artifact_id="sha256:" + semantic_hash(sources),
                        records=selected, conflicts=conflicts, gaps=gaps, relevance=(),
                        source_versions=tuple(r.provenance.source_version for r in sources), context_version="pending")
    projection = c.model_dump(mode="json", exclude={"context_version"})
    return changed(c, context_version="sha256:" + semantic_hash(projection))


def standards():
    t = resolved({"payment_days": 60, "incoterm": "FCA"})
    std = ResolvedStandards(bindings=t.bindings, field_origins=tuple(
        FieldOrigin(field=b.field, source_kind="quote", source_refs=(SourceRef(record_id="quote:applicable-1"),))
        for b in t.bindings), version_hash="0" * 64)
    return changed(std, version_hash=_version(std, "field_origins"))


def assumption(cost, original):
    b = cost.unit_cost.basis
    values = tuple(NamedEstimate(name=name, value=value, unit=unit, basis=b if unit == "EUR_per_price_unit" else None,
                                 range_low=value if name == "full_cost" else None,
                                 range_high=value if name == "full_cost" else None)
                   for name, value, unit in (
                       ("full_cost", cost.unit_cost.amount, "EUR_per_price_unit"),
                       ("interest_rate", Decimal("0.08"), "fraction"),
                       ("usual_rate", Decimal("0.08"), "fraction"),
                       ("ppm", Decimal("0"), "ppm"),
                       ("extra_per_unit", Decimal("0"), "EUR_per_price_unit"),
                   ))
    r = changed(original, kind="hypothesis", canonical_id="assumption:source-cost",
                payload=EstimateRecord(kind="estimate", method_id="source-cost-v1", values=values,
                                       assumptions=cost.source_refs))
    r = changed(r, provenance=changed(r.provenance, layer="derived", source_version="explicit-assumptions/1",
                                     content_hash=semantic_hash(r.payload), locator="internal/assumptions/source-cost"))
    return changed(r, record_id="sha256:" + semantic_hash(r))


def construct(ctx, *, assumption_record=None):
    cost = EvidenceProjections().cost_input(ctx, "cost:310010")
    a = assumption_record or assumption(cost, ctx.records[0])
    estimate = SourceCostEstimateBuilder().construct(cost, supplier_id="sup:F", standard=standards(),
                                                    assumptions=a, as_of=AS_OF)
    return cost, a, estimate


def run(relationship, ctx):
    cost, a, estimate = construct(ctx)
    economic = context_for(relationship["case"], relationship["declared_fixture_basis"], estimate)
    packages = tuple(package({"unit_price": price, "payment_days": 60}, economic) for price in (45, 49))
    return cost, a, estimate, economic, packages, tuple(evaluate(p, economic) for p in packages)


def test_full_causal_chain_changes_economic_order_with_unchanged_packages(relationship):
    release = source(relationship, 43)
    override = source(relationship, 47, "case")
    first, second = run(relationship, evidence(release)), run(relationship, evidence(release, override))
    assert first[4] == second[4]
    assert first[0].unit_cost.amount == Decimal("43") and second[0].unit_cost.amount == Decimal("47")
    assert first[2].full_cost == first[0].unit_cost and second[2].full_cost == second[0].unit_cost
    assert first[2].estimate_id != second[2].estimate_id
    assert first[3].fingerprint != second[3].fingerprint
    for trace in (first, second):
        cost, a, estimate, economic, packages, results = trace
        assert cost.source_refs[0] in estimate.assumption_refs
        assert SourceRef(record_id=a.record_id, canonical_id=a.canonical_id) in estimate.assumption_refs
        assert estimate.uncertainty_kind == "unknown"
        assert estimate.standard == economic.standards_by_supplier[0].standards
        for p, r in zip(packages, results, strict=True):
            assert r.must_haves_ok and r.numerically_valid and r.basis_verified and not r.issues
            assert r.assumption_refs == estimate.assumption_refs
            raw_supplier = {**relationship["estimate"], "full_cost": float(cost.unit_cost.amount),
                            "usual_rate": 0.08, "ppm": 0, "extra": 0}
            values = {"unit_price": float(next(t.value for t in p.bindings if t.field == "unit_price")),
                      "payment_days": 60}
            assert r.nominal_cost.amount == Decimal(str(kit.total_cost(
                relationship["case"], values, supplier=raw_supplier,
            )))
            assert {v.kind: v.amount.amount for v in r.components} == {
                k: Decimal(str(v)) for k, v in kit.cost_breakdown(
                    relationship["case"], values, supplier=raw_supplier,
                ).items()
            }
        repeat = evidence(release) if cost.unit_cost.amount == 43 else evidence(release, override)
        assert run(relationship, repeat) == trace
    assert [r.nominal_cost.amount for r in first[5]] == [Decimal("369600"), Decimal("401600")]
    assert [r.nominal_cost.amount for r in second[5]] == [Decimal("429044.44"), Decimal("401600")]
    assert first[5][0].nominal_cost.amount < first[5][1].nominal_cost.amount
    assert second[5][0].nominal_cost.amount > second[5][1].nominal_cost.amount


def test_disabled_estimates_keep_nominal_costs_unchanged(relationship):
    first = run(relationship, evidence(source(relationship, 43)))
    second = run(relationship, evidence(source(relationship, 47)))
    disabled = context_for(relationship["case"], relationship["declared_fixture_basis"])
    assert first[3].case.buyer == second[3].case.buyer == disabled.case.buyer
    assert first[4] == second[4]
    one = tuple(evaluate(p, disabled) for p in first[4])
    two = tuple(evaluate(p, disabled) for p in second[4])
    assert one == two
    assert [r.nominal_cost.amount for r in one] == [Decimal("369600"), Decimal("401600")]
    assert all(not r.assumption_refs and not r.scenario_costs for r in one)


def test_irrelevant_wording_does_not_change_estimates_or_economics(relationship):
    cost = source(relationship, 47)
    text = changed(cost, record_id="statement:greeting", canonical_id=None, kind="supplier_statement",
                   payload=TextRecord(kind="text", title="Greeting", text="Hello, thank you!", document_kind="message"))
    assert run(relationship, evidence(cost)) == run(relationship, evidence(cost, text))


def test_source_only_revision_changes_attribution_not_costs(relationship):
    a = source(relationship, 47)
    b = changed(a, record_id="record:revised-source", provenance=changed(a.provenance, source_version="new/2"))
    first, second = run(relationship, evidence(a)), run(relationship, evidence(b))
    assert first[0].source_refs != second[0].source_refs
    assert first[2].estimate_id != second[2].estimate_id
    assert first[3].fingerprint != second[3].fingerprint
    assert [r.nominal_cost for r in first[5]] == [r.nominal_cost for r in second[5]]
    assert first[5][0].economic_fingerprint != second[5][0].economic_fingerprint


@pytest.mark.parametrize("kind", ["supplier_statement", "estimate", "hypothesis"])
def test_unverified_cost_claim_cannot_construct_estimate(relationship, kind):
    with pytest.raises(ContractViolation, match="unsupported_claim"):
        construct(evidence(changed(source(relationship, 47), kind=kind)))


def test_conflict_and_inapplicable_winner_block_construction(relationship):
    base = source(relationship, 43)
    one, two = source(relationship, 47, "case"), source(relationship, 48, "case")
    with pytest.raises(ContractViolation):
        construct(evidence(base, one, two))
    wrong = changed(one, scope=changed(one.scope, supplier_ids=("sup:OTHER",)))
    with pytest.raises(ContractViolation):
        construct(evidence(base, wrong))


@pytest.mark.parametrize("missing", ["full_cost", "interest_rate", "usual_rate", "ppm", "extra_per_unit"])
def test_missing_assumptions_do_not_become_defaults(relationship, missing):
    ctx = evidence(source(relationship, 47))
    cost = EvidenceProjections().cost_input(ctx, "cost:310010")
    a = assumption(cost, ctx.records[0])
    a = changed(a, payload=changed(a.payload, values=tuple(v for v in a.payload.values if v.name != missing)))
    with pytest.raises(ContractViolation, match="all five"):
        construct(ctx, assumption_record=a)


def test_wrong_source_mapping_and_revision_rejected(relationship):
    ctx = evidence(source(relationship, 47))
    cost = EvidenceProjections().cost_input(ctx, "cost:310010")
    a = assumption(cost, ctx.records[0])
    altered = tuple(changed(v, value=Decimal("46"), range_low=Decimal("46"), range_high=Decimal("46"))
                    if v.name == "full_cost" else v for v in a.payload.values)
    with pytest.raises(ContractViolation, match="source_conflict"):
        construct(ctx, assumption_record=changed(a, payload=changed(a.payload, values=altered)))
    with pytest.raises(ContractViolation, match="exact cost-source revision"):
        construct(ctx, assumption_record=changed(a, payload=changed(a.payload,
                                                                 assumptions=(SourceRef(record_id="cost:old"),))))


def test_illegal_package_is_not_admitted_by_favorable_estimate(relationship):
    _, _, _, ctx, _, _ = run(relationship, evidence(source(relationship, 43)))
    with pytest.raises(ContractViolation, match="outside-option"):
        evaluate(package({"unit_price": 45, "payment_days": 61}, ctx), ctx)


@pytest.mark.parametrize("defect", ["missing_bounds", "fractional_ppm", "unknown_temporal", "claim", "wrong_basis",
                                    "varying_rate", "wrong_scope", "wrong_method"])
def test_inadmissible_or_unsupported_assumptions_fail_explicitly(relationship, defect):
    ctx = evidence(source(relationship, 47))
    cost = EvidenceProjections().cost_input(ctx, "cost:310010")
    a = assumption(cost, ctx.records[0])
    if defect == "unknown_temporal":
        a = changed(a, temporal=changed(a.temporal, status="unknown"))
    elif defect == "claim":
        a = changed(a, payload=TextRecord(kind="text", title="Claim", text="Trust my cost!", document_kind="message"),
                    kind="supplier_statement")
    elif defect == "wrong_scope":
        a = changed(a, scope=changed(a.scope, supplier_ids=("sup:OTHER",)))
    elif defect == "wrong_method":
        a = changed(a, payload=changed(a.payload, method_id="fixture-point-v1"))
    else:
        modified = []
        for v in a.payload.values:
            if defect == "missing_bounds" and v.name == "full_cost":
                v = changed(v, range_low=None, range_high=None)
            elif defect == "fractional_ppm" and v.name == "ppm":
                v = changed(v, value=Decimal("0.5"))
            elif defect == "wrong_basis" and v.name == "extra_per_unit":
                v = changed(v, basis=changed(v.basis, price_unit=100))
            elif defect == "varying_rate" and v.name == "interest_rate":
                v = changed(v, range_low=Decimal("0.07"), range_high=Decimal("0.09"))
            modified.append(v)
        a = changed(a, payload=changed(a.payload, values=tuple(modified)))
    with pytest.raises(ContractViolation):
        construct(ctx, assumption_record=a)


def test_explicit_full_cost_range_remains_a_scenario_range_not_calibration(relationship):
    ctx = evidence(source(relationship, 47))
    cost = EvidenceProjections().cost_input(ctx, "cost:310010")
    a = assumption(cost, ctx.records[0])
    values = tuple(changed(v, range_low=Decimal("46"), range_high=Decimal("48"))
                   if v.name == "full_cost" else v for v in a.payload.values)
    _, _, e = construct(ctx, assumption_record=changed(a, payload=changed(a.payload, values=values)))
    assert e.full_cost_low.amount == 46 and e.full_cost_high.amount == 48
    assert e.full_cost.amount == 47 and e.uncertainty_kind == "scenario_range"


def test_missing_reference_standards_fail_instead_of_borrowing_buyer_terms(relationship):
    ctx = evidence(source(relationship, 47))
    cost = EvidenceProjections().cost_input(ctx, "cost:310010")
    std = ResolvedStandards(bindings=(), field_origins=(), version_hash="0" * 64)
    std = changed(std, version_hash=_version(std, "field_origins"))
    with pytest.raises(ContractViolation, match="reference standards"):
        SourceCostEstimateBuilder().construct(cost, supplier_id="sup:F", standard=std,
                                             assumptions=assumption(cost, ctx.records[0]), as_of=AS_OF)
