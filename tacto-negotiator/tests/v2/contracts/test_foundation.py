import copy
import inspect
import json
from decimal import Decimal
from pathlib import Path

import pytest
from arena_kit.cost import cost_breakdown, must_haves_ok, total_cost
from pydantic import ValidationError

from tests.v2.fakes import FakeClock, ReplayArenaGateway, ReplayModelGateway, ScriptedPipeline
from tests.v2.support import PORT_SIGNATURES, digest, read_fixture, require


def basis():
    return {"currency": "EUR", "price_unit": 1, "part_ids": ["part:340010"],
            "quantity_basis": "arena-case-quantity", "source_refs": ["case:P10"]}


def price():
    return {"amount": "28.34", "basis": basis()}


def test_fixture_is_actual_p10_and_origin_is_explicit(p10):
    source = json.loads((Path(__file__).parents[2] / "fixtures/practice_cases.json").read_text())
    assert p10["case"] == next(c for c in source if c["case_id"] == "case:P10")
    assert "synthetic" in p10["origin"]
    assert p10["opening"]["term_sheets"][0]["terms"]["lead_time_days"] == 54
    assert 54 not in p10["case"]["term_options"]["lead_time_days"]


@pytest.mark.parametrize("index", range(3))
def test_frozen_official_cost_oracle(p10, index):
    golden = p10["official_cost_goldens"][index]
    assert must_haves_ok(p10["case"], golden["terms"])
    assert total_cost(p10["case"], golden["terms"]) == golden["total_cost"]
    assert cost_breakdown(p10["case"], golden["terms"]) == golden["components"]
    assert round(sum(golden["components"].values()), 2) == golden["total_cost"]


def test_late_delivery_is_not_free(p10):
    first, late = p10["official_cost_goldens"][:2]
    assert late["total_cost"] - first["total_cost"] == 33_600
    assert late["components"]["late_delivery"] == 33_600


@pytest.mark.parametrize("index", range(7))
def test_relationship_oracle(relationship, index):
    point = relationship["goldens"][index]
    terms = {**relationship["terms"], "unit_price": point["price"]}
    assert total_cost(relationship["case"], terms, supplier=relationship["estimate"]) == point["cost"]


def test_relationship_curve_is_nonmonotonic_and_known_root_exists(relationship):
    points = {row["price"]: row["cost"] for row in relationship["goldens"]}
    assert points[20] > points[45] > points[48] < points[49] < points[55]
    assert points[49] == float(relationship["target"])


def test_baseline_is_pinned_and_does_not_claim_full_suite(p10):
    baseline = read_fixture("v1-baseline.json")
    assert baseline["v1_revision"] == "3653046bce6dd7cbbeffe00ecf5dfd9c3edbc0ab"
    assert baseline["development_revision"] == "4c905b10be1f576de9b68be9c120cf6796ae4561"
    assert baseline["case_sha256"] == digest(p10["case"])
    assert baseline["configuration"]["claims"] is False
    assert baseline["configuration"]["estimates"] == {}
    assert baseline["expected_first_move"]["message"]["term_sheets"][0]["terms"] == {
        "unit_price": 28.34, "volume_per_year": 23400, "contract_months": 24, "lead_time_days": 35,
    }
    assert "not full suite" in baseline["validation"]["scope"]


@pytest.mark.parametrize("port", PORT_SIGNATURES)
def test_exact_port_signatures(request, port):
    ports = require(request, "core.ports")
    for method, (is_async, arguments) in PORT_SIGNATURES[port].items():
        function = getattr(getattr(ports, port), method)
        assert inspect.iscoroutinefunction(function) is is_async
        assert tuple(inspect.signature(function).parameters) == ("self", *arguments.split())
        assert inspect.signature(function).return_annotation is not inspect.Signature.empty
        for parameter in inspect.signature(function).parameters.values():
            if parameter.name != "self":
                assert parameter.annotation is not inspect.Parameter.empty
                assert str(parameter.annotation) not in {"Any", "typing.Any", "object", "dict"}
        assert str(inspect.signature(function).return_annotation) not in {"Any", "typing.Any", "object", "dict"}


@pytest.mark.parametrize("field,value", [
    ("amount", "0"), ("amount", "-1"), ("amount", "NaN"), ("amount", "Infinity"),
    ("amount", True), ("extra", "forbidden"),
])
def test_price_rejects_invalid_boundary_values(request, field, value):
    models = require(request, "core.models")
    raw = {**price(), field: value}
    with pytest.raises(ValidationError):
        models.Price.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize("field,value", [
    ("price_unit", 0), ("price_unit", -100), ("price_unit", True),
    ("part_ids", []), ("currency", "USD"),
])
def test_basis_rejects_ambiguous_units(request, field, value):
    models = require(request, "core.models")
    with pytest.raises(ValidationError):
        models.PriceBasis.model_validate_json(json.dumps({**basis(), field: value}))


@pytest.mark.parametrize("unit", [1, 100, 1000])
def test_price_roundtrip_preserves_basis_and_decimal(request, unit):
    models = require(request, "core.models")
    raw = price()
    raw["basis"]["price_unit"] = unit
    result = models.Price.model_validate_json(json.dumps(raw))
    assert result.amount == Decimal("28.34")
    assert result.basis.price_unit == unit
    encoded = json.loads(result.model_dump_json())
    assert encoded["amount"] == "28.34"
    assert models.Price.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        result.amount = Decimal("1")
    assert isinstance(result.basis.part_ids, tuple)


@pytest.mark.parametrize("field,value", [
    ("lead_time_days", True), ("contract_months", "24"), ("payment_days", 30.5),
    ("unit_price", "0"), ("surprise_field", 1), ("incoterm", "UNKNOWN"),
])
def test_term_bindings_are_field_typed(request, field, value):
    models = require(request, "core.models")
    with pytest.raises(ValidationError):
        models.TermBinding.model_validate_json(json.dumps({"field": field, "value": value}))


def test_canonical_serialization_is_order_independent_but_semantic(request):
    codec = require(request, "core.serialization")
    first = {"a": "28.34", "b": [1, 2]}
    assert codec.semantic_hash(first) == codec.semantic_hash({"b": [1, 2], "a": "28.34"})
    assert codec.semantic_hash(first) != codec.semantic_hash({"a": "28.35", "b": [1, 2]})
    with pytest.raises(ValueError):
        codec.canonical_json({"a": float("nan")})


@pytest.mark.asyncio
async def test_scripted_ports_obey_signatures_and_do_not_reinterpret():
    sentinel = object()
    scripted = ScriptedPipeline({"assessment": sentinel})
    assert await scripted.interpret(1, 2, None, 4) is sentinel
    assert scripted.calls == [("assessment", (1, 2, None, 4))]
    for method in ("interpret", "propose_strategies", "generate_candidates", "select_action", "validate_action"):
        reference_port = next(p for p, methods in PORT_SIGNATURES.items() if method in methods)
        assert tuple(inspect.signature(getattr(ScriptedPipeline, method)).parameters) == (
            "self", *PORT_SIGNATURES[reference_port][method][1].split(),
        )


@pytest.mark.parametrize("port", PORT_SIGNATURES)
def test_every_port_has_minimal_reference_double(port):
    for method, (is_async, arguments) in PORT_SIGNATURES[port].items():
        implementation = (
            FakeClock if port == "Clock" else ReplayModelGateway if port == "ModelGateway"
            else ReplayArenaGateway if port == "ArenaGateway" else ScriptedPipeline
        )
        function = getattr(implementation, method)
        assert inspect.iscoroutinefunction(function) is is_async
        assert tuple(inspect.signature(function).parameters) == ("self", *arguments.split())


@pytest.mark.asyncio
async def test_fake_model_records_calls_and_propagates_scripted_failure():
    gateway = ReplayModelGateway(TimeoutError("scripted"))
    with pytest.raises(TimeoutError, match="scripted"):
        await gateway.complete("request", "budget")
    assert gateway.calls == [("request", "budget")]
    clock = FakeClock()
    previous = copy.copy(clock.now)
    clock.advance(8)
    assert (clock.utcnow() - previous).total_seconds() == 8
