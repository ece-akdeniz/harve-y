"""Direct package comparisons without codec, strategy or runtime dependencies."""

from decimal import Decimal

import pytest
from arena_kit import cost as kit

from negotiator.v2.adapters.official import OfficialArithmetic
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.core.models import (
    CostPolicy,
    EconomicContext,
    EstimateScenario,
    Package,
    Price,
    PriceInterval,
    ResolvedStandards,
    ScenarioPolicy,
    SupplierStandards,
)
from negotiator.v2.economics.official import OfficialEconomicEvaluator, _version, economic_fingerprint

from .test_official_adapter import binding, changed, estimate, p10_basis, typed_case


def context_for(raw, basis, supplier=None, mode=None):
    case = typed_case(raw, basis)
    standards = supplier.standard if supplier else ResolvedStandards(
        bindings=(), field_origins=(), version_hash="0" * 64,
    )
    standards = changed(standards, version_hash=_version(standards, "field_origins"))
    if supplier:
        supplier = changed(supplier, standard=standards)
    mode = mode or ("nominal_explicit" if supplier else "disabled_explicit")
    context = EconomicContext(
        case=case, standards_by_supplier=(SupplierStandards(supplier_id=case.supplier_ids[0], standards=standards),),
        estimates=(supplier,) if supplier else (),
        scenario_policy=ScenarioPolicy(mode=mode, scenarios=(EstimateScenario(
            scenario_id="explicit", estimate_ids=(supplier.estimate_id,),
        ),) if supplier else (), required_supplier_ids=case.supplier_ids if supplier else ()),
        cost_policy=CostPolicy(
            policy_id="test", comparison="robust_scenarios" if mode == "robust_scenarios" else "nominal",
                               price_bounds=PriceInterval(
            minimum=Price(amount=Decimal("0.01"), basis=case.parts[0].price_basis),
            maximum=Price(amount=Decimal("100"), basis=case.parts[0].price_basis)),
                               tick=Decimal("0.01"), fallback_rule="preserve_baseline_if_feasible",
                               alternative_rule="compare_executable_else_no_deal_score"),
        fingerprint="0" * 64, issues=(),
    )
    return changed(context, fingerprint=economic_fingerprint(context))


def package(values, context):
    from negotiator.v2.core.models import TermBinding
    return Package(bindings=tuple(TermBinding.model_validate_json(__import__('json').dumps(binding(k, v)))
                                  for k, v in sorted(values.items())), price_basis=context.case.parts[0].price_basis)


def evaluate(p, c, oracle=None):
    evaluator = OfficialEconomicEvaluator(oracle=oracle or OfficialArithmetic())
    return evaluator.evaluate_package(p, c.case.supplier_ids[0], c)


def test_two_legal_p10_packages_exact_complete_cost_comparison(p10):
    c = context_for(p10["case"], p10_basis(p10))
    results = []
    for golden in p10["official_cost_goldens"][:2]:
        values = {k: v for k, v in golden["terms"].items() if k in c.case.negotiable_fields}
        p = package(values, c)
        r = evaluate(p, c)
        assert r.must_haves_ok and r.numerically_valid and r.basis_verified
        assert r.nominal_cost.amount == Decimal(str(golden["total_cost"]))
        complete = kit.closing_terms(p10["case"], values)
        assert {x.kind: x.amount.amount for x in r.components} == {
            k: Decimal(str(v)) for k, v in kit.cost_breakdown(p10["case"], complete).items()
        }
        assert evaluate(p, c) == r
        assert any(o.source_kind == "fixed" for o in r.resolved_terms.origins)
        results.append(r)
    assert results[0].nominal_cost != results[1].nominal_cost
    assert results[0].economic_fingerprint != results[1].economic_fingerprint


@pytest.mark.parametrize("mode", ["nominal_explicit", "robust_scenarios"])
def test_explicit_scenario_parity_and_price_order_reversal(relationship, mode):
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    e = estimate(relationship["estimate"], basis, raw["suppliers"][0])
    c = context_for(raw, basis, e, mode)
    results = []
    for price in (45, 49):
        values = {k: v for k, v in {**relationship["terms"], "unit_price": price}.items()
                  if k in c.case.negotiable_fields}
        r = evaluate(package(values, c), c)
        expected = kit.total_cost(raw, values, supplier=relationship["estimate"])
        assert r.nominal_cost.amount == Decimal(str(expected))
        assert r.scenario_costs[0].cost == r.nominal_cost
        assert r.scenario_costs[0].estimate_id == e.estimate_id
        assert r.assumption_refs == e.assumption_refs
        results.append(r)
    assert results[0].nominal_cost.amount > results[1].nominal_cost.amount


def test_missing_standards_and_incomplete_package_rejected(p10):
    c = context_for(p10["case"], p10_basis(p10))
    p = package({}, c)
    with pytest.raises(ContractViolation, match="declare its own price"):
        evaluate(p, c)
    c = changed(c, standards_by_supplier=())
    c = changed(c, fingerprint=economic_fingerprint(c))
    with pytest.raises(ContractViolation, match="standards unavailable"):
        evaluate(p, c)


@pytest.mark.parametrize("field,value", [("payment_days", 90), ("lead_time_days", 54)])
def test_fixed_and_outside_option_values_are_not_repaired(p10, field, value):
    c = context_for(p10["case"], p10_basis(p10))
    values = {k: v for k, v in p10["official_cost_goldens"][0]["terms"].items() if k in c.case.negotiable_fields}
    values[field] = value
    with pytest.raises(ContractViolation, match="infeasible"):
        evaluate(package(values, c), c)


def test_incompatible_basis_rejected(p10):
    c = context_for(p10["case"], p10_basis(p10))
    p = package(p10["packages"][0], c)
    p = Package(bindings=p.bindings, price_basis=changed(p.price_basis, price_unit=100))
    with pytest.raises(ContractViolation, match="unknown_basis"):
        evaluate(p, c)


def test_oracle_numeric_failure_is_rejected_evaluation(p10):
    class Failing:
        def evaluate(self, case, terms, supplier):
            raise ContractViolation("component_rounding_mismatch: preserved official failure")
    c = context_for(p10["case"], p10_basis(p10))
    r = evaluate(package(p10["packages"][0], c), c, Failing())
    assert not r.numerically_valid and r.nominal_cost is None
    assert not r.components and not r.scenario_costs
    assert any(i.code == "nonfinite_cost" and "component_rounding_mismatch" in i.detail for i in r.issues)


def test_unknown_supplier_and_forged_economic_hash_rejected(p10):
    c = context_for(p10["case"], p10_basis(p10))
    p = package(p10["packages"][0], c)
    with pytest.raises(ContractViolation, match="scope_mismatch"):
        OfficialEconomicEvaluator(oracle=OfficialArithmetic()).evaluate_package(p, "unknown", c)
    with pytest.raises(ContractViolation, match="fingerprint"):
        evaluate(p, changed(c, fingerprint="b" * 64))


def test_estimate_source_revision_changes_economic_fingerprint(relationship):
    from negotiator.v2.core.models import SourceRef
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    e = estimate(relationship["estimate"], basis, raw["suppliers"][0])
    c = context_for(raw, basis, e)
    revised = context_for(raw, basis, changed(e, assumption_refs=(SourceRef(record_id="cost:revision-2"),)))
    p = package({"unit_price": 49}, c)
    first, second = evaluate(p, c), evaluate(p, revised)
    assert first.nominal_cost == second.nominal_cost
    assert first.economic_fingerprint != second.economic_fingerprint
    assert first.assumption_refs != second.assumption_refs


def test_must_have_failure_cannot_masquerade_as_admissible(p10):
    c = context_for(p10["case"], p10_basis(p10))
    # A declared legal option can still fail a buyer must-have.
    values = dict(p10["packages"][0])
    option = next(o for o in c.case.options if o.field == "volume_per_year")
    values["volume_per_year"] = min(option.values)
    r = evaluate(package(values, c), c)
    assert r.numerically_valid
    assert not r.must_haves_ok
    assert any(i.code == "infeasible" and i.severity == "error" for i in r.issues)


def test_multiple_scenarios_require_explicit_nominal_resolution(relationship):
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    c = context_for(raw, basis, estimate(relationship["estimate"], basis, raw["suppliers"][0]), "robust_scenarios")
    policy = changed(c.scenario_policy, scenarios=c.scenario_policy.scenarios + (
        EstimateScenario(scenario_id="second", estimate_ids=c.scenario_policy.scenarios[0].estimate_ids),
    ))
    c = changed(c, scenario_policy=policy)
    c = changed(c, fingerprint=economic_fingerprint(c))
    with pytest.raises(ContractViolation, match="nominal estimate"):
        evaluate(package({"unit_price": 49}, c), c)


def test_unavailable_required_estimate_cannot_construct_context(relationship):
    from pydantic import ValidationError
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    c = context_for(raw, basis, estimate(relationship["estimate"], basis, raw["suppliers"][0]))
    with pytest.raises(ValidationError, match="resolve"):
        changed(c, estimates=())


def test_fixed_terms_override_supplier_standards_and_sheet_overrides_quote(p10):
    from negotiator.v2.core.models import FieldOrigin, SourceRef, TermBinding
    c = context_for(p10["case"], p10_basis(p10))
    standard = ResolvedStandards(
        bindings=(TermBinding(field="payment_days", value=90), TermBinding(field="lead_time_days", value=56)),
        field_origins=tuple(FieldOrigin(field=k, source_kind="quote", source_refs=(SourceRef(record_id="quote:rev1"),))
                            for k in ("payment_days", "lead_time_days")), version_hash="0" * 64,
    )
    standard = changed(standard, version_hash=_version(standard, "field_origins"))
    c = changed(c, standards_by_supplier=(SupplierStandards(supplier_id=c.case.supplier_ids[0], standards=standard),))
    c = changed(c, fingerprint=economic_fingerprint(c))
    r = evaluate(package(p10["packages"][0], c), c)
    terms = {t.field: t.value for t in r.resolved_terms.bindings}
    assert terms["payment_days"] == 30
    assert terms["lead_time_days"] == p10["packages"][0]["lead_time_days"]
    assert next(o for o in r.resolved_terms.origins if o.field == "payment_days").source_kind == "fixed"
    assert next(o for o in r.resolved_terms.origins if o.field == "lead_time_days").source_kind == "sheet"


def test_unexpected_oracle_failure_is_not_disguised_as_numeric_failure(p10):
    class Broken:
        def evaluate(self, case, terms, supplier):
            raise RuntimeError("implementation defect")
    c = context_for(p10["case"], p10_basis(p10))
    with pytest.raises(RuntimeError, match="implementation defect"):
        evaluate(package(p10["packages"][0], c), c, Broken())
