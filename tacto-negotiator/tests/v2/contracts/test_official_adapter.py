"""Independent kit parity through validated oracle inputs; no full codec/evaluator."""

import copy
import hashlib
import inspect
import json
from decimal import Decimal
from pathlib import Path

import pytest
from arena_kit import cost as kit

from negotiator.v2.adapters.official import OfficialArithmetic
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.core.models import CaseContract, ResolvedTerms, SupplierEstimate
from negotiator.v2.core.serialization import semantic_hash
from tests.v2.contracts.test_layered_resolver import changed
from tests.v2.dto_spec import example


def binding(field, value):
    if field in {"unit_price", "tooling_eur", "chargeback_eur_per_complaint"}:
        value = str(value)
    if field == "index_clause" and value is not None:
        value = {**value, "material_share": str(value["material_share"]), "deadband_pct": str(value["deadband_pct"])}
    return dict(field=field, value=value)


def origin(field):
    return dict(field=field, source_kind="sheet", source_refs=[dict(record_id="source:terms")])


def resolved(values):
    raw = dict(bindings=[binding(k, v) for k, v in sorted(values.items())],
               origins=[origin(k) for k in sorted(values)], version_hash="a" * 64)
    model = ResolvedTerms.model_validate_json(json.dumps(raw))
    canonical = model.model_dump(mode="json")
    canonical.pop("version_hash")
    return ResolvedTerms(bindings=model.bindings, origins=model.origins, version_hash=semantic_hash(canonical))


def typed_case(raw, basis):
    seed = example("CaseContract")
    seed.update(case_id=raw["case_id"], case_type=raw["type"], title=raw["title"],
                supplier_ids=raw["suppliers"], parts=[dict(part_id=basis["part_ids"][0], price_basis=basis)],
                negotiable_fields=raw["negotiable"], options=[
                    dict(field=k, values=[binding(k, v)["value"] for v in values], allow_verified_standard=False)
                    for k, values in sorted(raw.get("term_options", {}).items())],
                fixed_terms=[binding(k, v) for k, v in sorted(raw.get("fixed_terms", {}).items())],
                round_limit=raw["round_limit"], case_facts=[], refs=[])
    b = raw["buyer"]
    seed["buyer"] = dict(
        category_goal=b["category_goal"], need_per_year=str(b["need_per_year"]), horizon_years=str(b["horizon_years"]),
        current_price=dict(amount=str(b["current_unit_price"]), basis=basis) if b.get("current_unit_price") else None,
        fallback_price=dict(amount=str(b["fallback_unit_price"]), basis=basis), interest_rate=str(b["interest_rate"]),
        reference_payment_days=b["reference_payment_days"], need_lead_time_days=b["need_lead_time_days"],
        fallback_risk_pct=str(b.get("fallback_risk_pct", 0)), index_risk_pct=str(b.get("index_risk_pct", 0)),
        late_cost_per_day=dict(amount=str(b.get("late_cost_per_day", 0))),
        cost_per_defect=dict(amount=str(b.get("cost_per_defect", 0))),
        sustainable_margin_pct=(str(b["sustainable_margin_pct"])
                                if b.get("sustainable_margin_pct") is not None else None),
        relationship_eur_per_point=dict(amount=str(b["relationship_eur_per_point"]))
        if b.get("relationship_eur_per_point") is not None else None,
        freight=[dict(incoterm=k, eur_per_unit=str(v)) for k, v in b["freight_eur_per_unit"].items()],
        index_paths=[dict(series=k, delta_fraction=str(v)) for k, v in b.get("index_paths", {}).items()],
        must_haves=[{**m, "value": binding(m["field"], m["value"])["value"]} for m in b.get("must_haves", [])],
        alternative=dict(kind="unavailable", reason_code="offline-oracle-not-closing"),
    )
    model = CaseContract.model_validate_json(json.dumps(seed))
    canonical = model.model_dump(mode="json")
    for key in ("contract_hash", "title", "refs"):
        canonical.pop(key)
    for key in ("fixed_terms", "options"):
        canonical[key] = sorted(canonical[key], key=lambda item: item["field"])
    return changed(model, contract_hash=semantic_hash(canonical))


def estimate(raw, basis, supplier_id):
    seed = example("SupplierEstimate")
    seed.update(supplier_id=supplier_id, basis=basis, assumption_refs=[dict(record_id="cost:explicit-revision")],
                method_id="fixture-point-v1", uncertainty_kind="unknown", interest_rate=str(raw["interest_rate"]),
                usual_rate=str(raw.get("usual_rate", raw["interest_rate"])), ppm=raw.get("ppm"),
                extra_per_unit=str(raw["extra"]) if "extra" in raw else None,
                standard=dict(bindings=[binding(k, v) for k, v in sorted(raw["standard"].items())],
                              field_origins=[origin(k) for k in sorted(raw["standard"])], version_hash="a" * 64))
    for key in ("full_cost", "full_cost_low", "full_cost_high"):
        seed[key] = dict(amount=str(raw["full_cost"]), basis=basis)
    return SupplierEstimate.model_validate_json(json.dumps(seed))


def assert_parity(raw, values, basis, supplier=None):
    case = typed_case(raw, basis)
    complete = kit.closing_terms(raw, values)
    result = OfficialArithmetic().evaluate(case, resolved(complete),
                                          estimate(supplier, basis, raw["suppliers"][0]) if supplier else None)
    assert result.total.amount == Decimal(str(kit.total_cost(raw, complete, supplier=supplier)))
    assert {c.kind: c.amount.amount for c in result.components} == {
        k: Decimal(str(v)) for k, v in kit.cost_breakdown(raw, complete, supplier=supplier).items()
    }
    assert len(result.components) == 11
    return result


def p10_basis(p10, price_unit=1):
    return dict(currency="EUR", price_unit=price_unit, part_ids=p10["case"]["parts"],
                quantity_basis="arena-case-quantity", source_refs=["case:P10"])


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("price_unit", [1, 100, 1000])
def test_p10_frozen_packages_match_all_eleven_components_without_unit_rescaling(p10, index, price_unit):
    golden = p10["official_cost_goldens"][index]
    result = assert_parity(p10["case"], golden["terms"], p10_basis(p10, price_unit))
    assert result.total.amount == Decimal(str(golden["total_cost"]))


@pytest.mark.parametrize("index", range(7))
def test_relationship_curve_matches_frozen_kit_results(relationship, index):
    point = relationship["goldens"][index]
    result = assert_parity(relationship["case"], {**relationship["terms"], "unit_price": point["price"]},
                           relationship["declared_fixture_basis"], relationship["estimate"])
    assert result.total.amount == Decimal(str(point["cost"]))


@pytest.mark.parametrize("payment,incoterm", [(30, "EXW"), (60, "FCA"), (90, "DAP")])
def test_payment_freight_quality_and_tooling_terms(p10, payment, incoterm):
    raw = copy.deepcopy(p10["case"])
    raw["fixed_terms"] = {}
    raw["buyer"]["cost_per_defect"] = 25
    values = {**p10["official_cost_goldens"][0]["terms"], "payment_days": payment, "incoterm": incoterm,
              "tooling_eur": 1234.56, "ppm_commitment": 120, "chargeback_eur_per_complaint": 10}
    assert_parity(raw, values, p10_basis(p10))


@pytest.mark.parametrize("path", [-0.1, 0.1])
def test_delayed_price_index_risk_and_fractional_need(p10, path):
    raw = copy.deepcopy(p10["case"])
    raw["fixed_terms"]["effective_date"] = "2026-01-01"
    raw["buyer"].update(index_paths={"series:test": path}, index_risk_pct=3, need_per_year=23400.5)
    raw["fixed_terms"].pop("effective_date")
    raw["fixed_terms"].pop("index_clause", None)
    raw["negotiable"].append("index_clause")
    raw["term_options"]["effective_date"] = ["2026-01-01", "2026-07-01"]
    raw["negotiable"].append("effective_date")
    values = {**p10["official_cost_goldens"][0]["terms"], "effective_date": "2026-07-01",
              "index_clause": dict(series="series:test", material_share=0.5, deadband_pct=2, base_month="2026-01")}
    assert_parity(raw, values, p10_basis(p10))


def test_evidence_cost_only_affects_explicit_supplier_estimate(relationship):
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    values = {**relationship["terms"], "unit_price": 49}
    plain = assert_parity(raw, values, basis)
    low = assert_parity(raw, values, basis, {**relationship["estimate"], "full_cost": 47})
    high = assert_parity(raw, values, basis, {**relationship["estimate"], "full_cost": 50})
    assert low.total != high.total
    assert plain.total == assert_parity(raw, values, basis).total
    assert next(c for c in plain.components if c.kind == "relationship").amount.amount == 0


def test_installed_kit_cost_source_matches_pinned_repository():
    project = Path(__file__).resolve().parents[3]
    pinned = project.parent / "negotiation-arena-kit/starter-kit/arena_kit/cost.py"
    installed_hash = hashlib.sha256(Path(inspect.getfile(kit)).read_bytes()).digest()
    assert installed_hash == hashlib.sha256(pinned.read_bytes()).digest()
    assert "1b5516bb95ef28e37f69aa446dc62168864bca53" in (project / "uv.lock").read_text()


def test_missing_terms_and_forged_contract_hash_fail_explicitly(p10):
    case = typed_case(p10["case"], p10_basis(p10))
    with pytest.raises(ContractViolation, match="complete"):
        OfficialArithmetic().evaluate(case, resolved({"unit_price": 28.34}), None)
    with pytest.raises(ContractViolation, match="hash"):
        OfficialArithmetic().evaluate(changed(case, contract_hash="b" * 64),
                                      resolved(kit.closing_terms(p10["case"], p10["packages"][0])), None)


def test_fixed_terms_cannot_be_overridden(p10):
    case = typed_case(p10["case"], p10_basis(p10))
    values = {**kit.closing_terms(p10["case"], p10["packages"][0]), "payment_days": 90}
    with pytest.raises(ContractViolation, match="fixed"):
        OfficialArithmetic().evaluate(case, resolved(values), None)


def test_wrong_supplier_estimate_basis_fails(relationship):
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    foreign = {**basis, "price_unit": 100}
    with pytest.raises(ContractViolation, match="basis"):
        OfficialArithmetic().evaluate(typed_case(raw, basis), resolved(kit.closing_terms(raw, {"unit_price": 49})),
                                      estimate(relationship["estimate"], foreign, raw["suppliers"][0]))


def test_official_zero_supplier_value_is_explicit_failure(relationship):
    raw, basis = relationship["case"], relationship["declared_fixture_basis"]
    supplier = {**relationship["estimate"], "extra": -49}
    with pytest.raises(ContractViolation, match="official_calculation_failed"):
        OfficialArithmetic().evaluate(typed_case(raw, basis), resolved(kit.closing_terms(raw, {"unit_price": 49})),
                                      estimate(supplier, basis, raw["suppliers"][0]))


def test_replay_is_deterministic_and_does_not_mutate_inputs(p10):
    case = typed_case(p10["case"], p10_basis(p10))
    terms = resolved(kit.closing_terms(p10["case"], p10["packages"][0]))
    before = case.model_dump_json(), terms.model_dump_json()
    one = OfficialArithmetic().evaluate(case, terms, None)
    two = OfficialArithmetic().evaluate(case, terms, None)
    assert one == two and semantic_hash(one) == semantic_hash(two)
    assert before == (case.model_dump_json(), terms.model_dump_json())


def test_missing_index_path_is_not_implicitly_zero(p10):
    raw = copy.deepcopy(p10["case"])
    raw["fixed_terms"].pop("index_clause", None)
    raw["negotiable"].append("index_clause")
    values = {**p10["packages"][0], "index_clause": dict(
        series="missing", material_share=0.5, deadband_pct=2, base_month="2026-01")}
    with pytest.raises(ContractViolation, match="missing_source"):
        OfficialArithmetic().evaluate(typed_case(raw, p10_basis(p10)), resolved(kit.closing_terms(raw, values)), None)


def test_float_domain_overflow_never_produces_an_infinite_cost(p10):
    case = typed_case(p10["case"], p10_basis(p10))
    # The typed value is finite; the authoritative kit's numeric domain is narrower.
    buyer = changed(case.buyer, need_per_year=Decimal("1e400"))
    case = changed(case, buyer=buyer)
    canonical = case.model_dump(mode="json")
    for key in ("contract_hash", "title", "refs"):
        canonical.pop(key)
    case = changed(case, contract_hash=semantic_hash(canonical))
    with pytest.raises(ContractViolation, match="unsupported_numeric_domain"):
        OfficialArithmetic().evaluate(case, resolved(kit.closing_terms(p10["case"], p10["packages"][0])), None)


def test_binary_half_cent_conflict_with_frozen_decimal_result_contract_fails_explicitly(p10):
    raw = copy.deepcopy(p10["case"])
    raw["buyer"].update(category_goal="routine", need_per_year=1, horizon_years=0.5,
                         must_haves=[], interest_rate=0,
                         freight_eur_per_unit={"EXW": 0, "FCA": 0, "DAP": 0})
    raw["term_options"].update(volume_per_year=[1], contract_months=[6])
    values = {"unit_price": 2.67, "volume_per_year": 1, "contract_months": 6, "lead_time_days": 42}
    assert kit.total_cost(raw, values) == 1.33
    assert kit.cost_breakdown(raw, values)["price"] == 1.335
    # Do not modify components or total to hide a kit-float/contract-Decimal tie difference.
    with pytest.raises(ContractViolation, match="component_rounding_mismatch"):
        OfficialArithmetic().evaluate(typed_case(raw, p10_basis(p10)), resolved(kit.closing_terms(raw, values)), None)


def test_multi_supplier_case_is_explicitly_unsupported(p10):
    case = typed_case(p10["case"], p10_basis(p10))
    case = changed(case, supplier_ids=(*case.supplier_ids, "sup:OTHER"))
    with pytest.raises(ContractViolation, match="unsupported_capability"):
        OfficialArithmetic().evaluate(case, resolved(kit.closing_terms(p10["case"], p10["packages"][0])), None)
