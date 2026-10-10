from decimal import Decimal

import pytest
from arena_kit.cost import total_cost

from tests.v2.support import codes, inputs, require, terms_of


def evaluator(request):
    module = require(request, "economics.official")
    oracle = require(request, "adapters.official").OfficialArithmetic()
    return module.OfficialEconomicEvaluator(oracle=oracle)


@pytest.mark.parametrize("index", range(3))
def test_v2_matches_frozen_official_components(request, p10, index):
    engine = evaluator(request)
    data = inputs(request, p10)
    result = engine.evaluate_package(data.packages[index], p10["supplier_id"], data.context.economic)
    golden = p10["official_cost_goldens"][index]
    assert result.nominal_cost.amount == Decimal(str(golden["total_cost"]))
    assert {c.kind: c.amount.amount for c in result.components} == {
        k: Decimal(str(v)) for k, v in golden["components"].items()
    }
    assert result.must_haves_ok and result.numerically_valid and result.basis_verified


def test_relationship_finite_ticks_retain_feasible_positive_price(request, p10, relationship):
    engine = evaluator(request)
    sid = relationship["case"]["suppliers"][0]
    p10.update(case=relationship["case"], supplier_id=sid,
               estimates={sid: relationship["estimate"]},
               fixture_basis=relationship["declared_fixture_basis"],
               packages=[{**relationship["terms"], "unit_price": float(p)}
                         for p in relationship["legal_price_ticks"]])
    p10["config"]["estimate_mode"] = "nominal_explicit"
    p10["config"]["price_max"] = "55.00"
    data = inputs(request, p10)
    values = [engine.evaluate_package(p, sid, data.context.economic) for p in data.packages]
    assert all(v.numerically_valid for v in values)
    assert [v.nominal_cost.amount for v in values] == [
        Decimal("429044.44"), Decimal("397273.61"), Decimal("401600.00"), Decimal("449600.00"),
    ]
    assert any(v.nominal_cost.amount == Decimal(relationship["target"]) for v in values)
    assert all(terms_of(p)["unit_price"] > 0 for p in data.packages)


def test_quote_standard_overrides_master_in_supplier_value_arithmetic(request, p10, relationship):
    engine = evaluator(request)
    sid = relationship["case"]["suppliers"][0]
    terms = {"unit_price": 49.0, "payment_days": 60}
    p10.update(case=relationship["case"], supplier_id=sid,
               estimates={sid: relationship["estimate"]}, packages=[terms],
               fixture_basis=relationship["declared_fixture_basis"],
               quote_standard={"payment_days": 30, "incoterm": "DAP"})
    p10["config"]["estimate_mode"] = "nominal_explicit"
    p10["config"]["price_max"] = "55.00"
    data = inputs(request, p10)
    result = engine.evaluate_package(data.packages[0], sid, data.context.economic)
    corrected = {**relationship["estimate"], "standard": p10["quote_standard"]}
    expected = total_cost(relationship["case"], terms, p10["quote_standard"], corrected)
    stale = total_cost(relationship["case"], terms, p10["quote_standard"], relationship["estimate"])
    assert expected != stale, "The fixture must detect a standards reference error economically"
    assert result.nominal_cost.amount == Decimal(str(expected))


def test_impossible_must_haves_return_empty_generation_not_default_package(request, p10):
    generator = require(request, "economics.candidates").FiniteCandidateGenerator(evaluator=evaluator(request))
    p10["case"]["buyer"]["must_haves"] = [{"field": "payment_days", "op": ">=", "value": 1000}]
    data = inputs(request, p10)
    result = generator.generate_candidates(data.intent, data.context, data.state, data.budget)
    assert result.candidates == ()
    assert "infeasible" in codes(result)


def test_generation_obeys_every_case_option_and_budget(request, p10):
    generator = require(request, "economics.candidates").FiniteCandidateGenerator(evaluator=evaluator(request))
    data = inputs(request, p10)
    generated = generator.generate_candidates(data.intent, data.context, data.state, data.budget)
    assert 0 < len(generated.candidates) <= data.budget.candidate_limit
    for candidate in generated.candidates:
        for package in candidate.contents.packages:
            terms = terms_of(package)
            assert set(terms) == set(p10["case"]["negotiable"])
            assert terms["volume_per_year"] == 23400
            assert terms["lead_time_days"] in {35, 42, 56}
            assert terms["contract_months"] in {12, 24, 36}
            assert terms["unit_price"] > 0
            assert terms["unit_price"].quantize(Decimal("0.01")) == terms["unit_price"]


def test_no_executable_alternative_is_tagged_unavailable_not_infinity(request, p10):
    data = inputs(request, p10)
    assert data.context.economic.case.buyer.alternative.kind == "unavailable"
    assert "Infinity" not in data.context.economic.model_dump_json()


def test_wrong_basis_blocks_approval_even_when_numeric_cost_is_finite(request, p10):
    engine = evaluator(request)
    p10["package_price_unit"] = 100
    data = inputs(request, p10)
    batch = engine.evaluate_candidates((data.candidate,), data.context)
    assert batch.items[0].disposition == "rejected"
    assert "unknown_basis" in codes(batch.items[0])


@pytest.mark.parametrize("failure", [ZeroDivisionError("supplier cash value is zero"), OverflowError("cost overflow")])
def test_arithmetic_failure_has_no_fabricated_zero_cost(request, p10, failure):
    module = require(request, "economics.official")
    data = inputs(request, p10)

    class FailingOracle:
        def evaluate(self, case, terms, supplier):
            raise failure

    engine = module.OfficialEconomicEvaluator(oracle=FailingOracle())
    result = engine.evaluate_package(data.packages[0], p10["supplier_id"], data.context.economic)
    assert result.numerically_valid is False
    assert result.nominal_cost is None
    assert result.components == ()
    assert "nonfinite_cost" in codes(result)
