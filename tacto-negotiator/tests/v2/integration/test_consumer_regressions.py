"""Assignment 1: consumer regressions with valid refreshed boundary identities."""

from decimal import Decimal

import pytest

from negotiator.v2.adapters.official import OfficialArithmetic
from negotiator.v2.core import models as m
from negotiator.v2.core.certificates import case_contract_hash, economic_fingerprint
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.economics.official import OfficialEconomicEvaluator
from negotiator.v2.evidence.context import LayeredContextBuilder
from negotiator.v2.execution.render import render_hash
from negotiator.v2.execution.validation import FinalActionValidator
from tests.v2.contracts.test_layered_resolver import changed
from tests.v2.contracts.test_strategy_boundary import boundary, select
from tests.v2.fakes import FakeClock
from tests.v2.integration.test_offline_decision import recorded, reprepare, run


def case_overlay(inputs, *overlays):
    prepared = reprepare(inputs.prepared, tuple(r for r in inputs.prepared.records if r.provenance.layer != "case"))
    case = changed(inputs.case, case_facts=overlays)
    case = changed(case, contract_hash=case_contract_hash(case))
    return changed(inputs, prepared=prepared, case=case, state=changed(inputs.state, case=case))


def context(inputs):
    return LayeredContextBuilder().build_context(inputs.prepared, inputs.case, inputs.server, (), inputs.as_of)


@pytest.mark.asyncio
async def test_case_fact_route_reaches_economics_and_validated_offer(relationship):
    original = recorded(relationship)
    override = original.prepared.records[1]
    inputs = case_overlay(original, override)
    before = inputs.model_dump_json()
    resolved = context(inputs)
    assert next(r for r in resolved.records if r.canonical_id == override.canonical_id) == override
    assert override.provenance.source_version in resolved.source_versions
    assert any(override.record_id == c.winning_record_id for c in resolved.conflicts)
    trace = await run(inputs)
    assert trace.validation.kind == "valid"
    assert trace.rendered.payload.packages == (inputs.packages[1],)
    assert override.record_id in {
        ref.record_id for item in trace.evaluations.items for result in item.economic for ref in result.assumption_refs
    }
    assert context(case_overlay(original, override, override)) == resolved
    assert trace == await run(inputs)
    assert inputs.model_dump_json() == before


@pytest.mark.parametrize("failure", ("scope", "collision", "identity", "statement"))
@pytest.mark.asyncio
async def test_case_overlay_cannot_resurrect_release_cost(relationship, failure):
    original = recorded(relationship)
    override = original.prepared.records[1]
    if failure == "scope":
        overlays = (changed(override, scope=changed(override.scope, case_id="case:other")),)
    elif failure == "collision":
        overlays = (override, changed(override, record_id="case:collision"))
    elif failure == "identity":
        overlays = (override, changed(override, payload=changed(override.payload, confidence_pct=Decimal("50"))))
    else:
        overlays = (changed(override, kind="supplier_statement"),)
    inputs = case_overlay(original, *overlays)
    resolved = context(inputs)
    assert not any(
        r.provenance.layer == "release" and r.canonical_id == override.canonical_id for r in resolved.records
    )
    with pytest.raises(ContractViolation):
        await run(inputs)


def with_price(package, amount):
    return m.Package(
        bindings=tuple(changed(b, value=Decimal(amount)) if b.field == "unit_price" else b for b in package.bindings),
        price_basis=package.price_basis,
    )


@pytest.mark.parametrize("price,valid", (("49.01", True), ("49.00", True), ("49.05", True), ("49.005", False)))
def test_declared_zero_origin_tick_and_cent_precision(relationship, price, valid):
    ctx, _, _, packages = boundary(relationship, 47)
    economic = ctx.economic
    evaluator = OfficialEconomicEvaluator(oracle=OfficialArithmetic())
    package = with_price(packages[1], price)
    if valid:
        assert evaluator.evaluate_package(package, "sup:F", economic).numerically_valid
    else:
        with pytest.raises(ContractViolation, match="uncertified_price"):
            evaluator.evaluate_package(package, "sup:F", economic)


@pytest.mark.parametrize("price", ("49.01", "49.00", "49.05"))
def test_unsupported_tick_cannot_bypass_service_with_refreshed_identity(relationship, price):
    ctx, _, _, packages = boundary(relationship, 47)
    # Reproduce the review's model_copy bypass; a validated v1 policy cannot
    # carry this tick. Refresh the fingerprint so that it cannot mask the defect.
    policy = ctx.economic.cost_policy.model_copy(update={"tick": Decimal("0.05")})
    economic = ctx.economic.model_copy(update={"cost_policy": policy})
    economic = economic.model_copy(update={"fingerprint": economic_fingerprint(economic)})
    evaluator = OfficialEconomicEvaluator(oracle=OfficialArithmetic())
    with pytest.raises(ContractViolation, match="unsupported_capability.*cent price tick"):
        evaluator.evaluate_package(with_price(packages[1], price), "sup:F", economic)


@pytest.mark.asyncio
async def test_each_missing_outgoing_field_fails_even_with_refreshed_hash(relationship):
    ctx, state, budget, packages = boundary(relationship, 47)
    *_, action, valid = await select(ctx, state, budget, packages)
    assert valid.kind == "valid"
    evaluator = OfficialEconomicEvaluator(oracle=OfficialArithmetic())
    for field in ctx.case.negotiable_fields:
        partial = m.Package(
            bindings=tuple(b for b in action.payload.packages[0].bindings if b.field != field),
            price_basis=action.payload.packages[0].price_basis,
        )
        edited = changed(action, payload=changed(action.payload, packages=(partial,)))
        edited = changed(edited, render_hash=render_hash(edited))
        validator = FinalActionValidator(evaluator=evaluator, clock=FakeClock())
        result = validator.validate_action(edited, ctx, state, budget)
        assert result.kind == "invalid"
        assert any(c.check_id.startswith("outgoing_fields:") and not c.passed for c in result.report.checks)
        assert next(c for c in result.report.checks if c.check_id == "hash").passed
        if field == "payment_days":
            assert evaluator.evaluate_package(partial, "sup:F", ctx.economic).numerically_valid


@pytest.mark.asyncio
async def test_coordinator_rejects_incomplete_supplied_offer(relationship):
    inputs = recorded(relationship)
    partial = m.Package(bindings=tuple(b for b in inputs.packages[1].bindings if b.field != "payment_days"),
                        price_basis=inputs.packages[1].price_basis)
    trace = await run(changed(inputs, packages=(partial,)))
    assert trace.validation.kind == "invalid"
    assert trace.outcome.kind == "cannot_decide"
    assert trace.validated_message_bytes is None
    assert next(c for c in trace.validation.report.checks if c.check_id == "hash").passed
    assert trace.evaluations.items[0].economic[0].numerically_valid


@pytest.mark.asyncio
async def test_coordinator_rejects_off_grid_price_with_valid_package_identity(relationship):
    inputs = recorded(relationship)
    inputs = changed(inputs, packages=(with_price(inputs.packages[1], "49.005"),))
    trace = await run(inputs)
    assert trace.outcome.kind == "cannot_decide"
    assert trace.validated_message_bytes is None
    assert any(s.status == "failed" for s in trace.stages)
    assert "uncertified_price" in trace.model_dump_json()


def test_case_override_deleted_optional_value_does_not_fill_from_release(relationship):
    original = recorded(relationship)
    release, override, quote = original.prepared.records
    release = changed(release, payload=changed(release.payload, confidence_pct=Decimal("75")))
    override = changed(override, payload=changed(override.payload, confidence_pct=None))
    prepared = reprepare(original.prepared, (release, override, quote))
    inputs = case_overlay(changed(original, prepared=prepared), override)
    winner = next(r for r in context(inputs).records if r.canonical_id == override.canonical_id)
    assert winner == override
    assert winner.payload.confidence_pct is None


@pytest.mark.asyncio
async def test_extra_outgoing_field_rejected_independently(relationship):
    ctx, state, budget, packages = boundary(relationship, 47)
    *_, action, _ = await select(ctx, state, budget, packages)
    package = m.Package(bindings=action.payload.packages[0].bindings + (
        m.TermBinding(field="incoterm", value="FCA"),
    ), price_basis=action.payload.packages[0].price_basis)
    action = changed(action, payload=changed(action.payload, packages=(package,)))
    action = changed(action, render_hash=render_hash(action))
    validator = FinalActionValidator(
        evaluator=OfficialEconomicEvaluator(oracle=OfficialArithmetic()), clock=FakeClock()
    )
    result = validator.validate_action(action, ctx, state, budget)
    assert result.kind == "invalid"
    assert any(c.check_id.startswith("outgoing_fields:") and not c.passed for c in result.report.checks)
    assert next(c for c in result.report.checks if c.check_id == "hash").passed
