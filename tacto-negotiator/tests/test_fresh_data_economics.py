import json
from pathlib import Path

import pytest
from arena_kit.cost import complete_offer, total_cost
from test_evaluator import ESTIMATE, STABILISE

from negotiator.claims import series_values
from negotiator.dossiers import build_one, for_case, load_package
from negotiator.economics import InfeasiblePackage, evaluate, price_for_budget
from negotiator.ingestion import VersionedPackage, context_manifest
from negotiator.optimizer import option_combinations


def test_unseen_large_option_space_is_bounded():
    with pytest.raises(InfeasiblePackage):
        option_combinations({"x": list(range(100)), "y": list(range(100))}, ["x", "y"])


def test_facts_only_unseen_supplier_and_contact_update(tmp_path):
    facts = {"doc:new": {"supplier": "sup:unseen", "title": "New contact person",
                          "text": "Finance director approval is required."},
             "news:new": {"supplier": "sup:unseen", "topic": "free_capacity"}}
    (tmp_path / "facts.json").write_text(json.dumps(facts))
    package = VersionedPackage(tmp_path)
    dossier = build_one(package, "sup:unseen")
    assert dossier.notes[0]["text"] == facts["doc:new"]["text"]
    assert "free_capacity" in dossier.traits
    case = {"suppliers": ["sup:case-only"], "facts": {"doc:case": {
        "supplier": "sup:case-only", "title": "New contact person", "body": "New buyer contact"}}}
    assert for_case({}, case)["sup:case-only"].notes[0]["text"] == "New buyer contact"
    assert context_manifest(case, package)["data_sha256"] == package.manifest["sha256"]
    assert package.warnings


def test_conflicting_release_id_is_not_citable_and_versions_retained(tmp_path):
    (tmp_path / "facts.json").write_text(json.dumps({"news:1": {"supplier": "sup:old"}}))
    release = tmp_path / "release-sunday"
    release.mkdir()
    (release / "facts.json").write_text(json.dumps({"news:1": {"supplier": "sup:new"}}))
    package = VersionedPackage(tmp_path)
    assert package.lookup("news:1") is None and "news:1" not in package.ids("news:")
    assert package.manifest["conflicts"]["news:1"]["base"]["supplier"] == "sup:old"


def test_explicit_bad_data_path_does_not_use_old_package(tmp_path, monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_package()


def test_malformed_index_does_not_poison_other_series():
    facts = {"idx:X@2026-09": {"value": float("nan")}, "idx:X@2026-13": {"value": 5},
             "idx:Y@2026-09": {"value": 10, "series": "Z"}, "idx:Z@2026-09": {"value": 8}}
    assert series_values(facts) == {"Z": {"2026-09": 8.0}}


def test_contract_coverage_uses_same_horizon_and_annual_volume():
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    case = next(c for c in cases if c["case_id"] == "case:P04")
    terms = complete_offer(case, {"unit_price": 4.0})
    one = evaluate(case, {**terms, "contract_months": 12})
    two = evaluate(case, {**terms, "contract_months": 24})
    assert one["uncovered_units"] == case["buyer"]["need_per_year"]
    assert two["uncovered_units"] == 0
    assert two["terms"]["volume_per_year"] == one["terms"]["volume_per_year"]
    assert two["cost"] == total_cost(case, {**terms, "contract_months": 24})


def test_nonmonotonic_budget_and_unreachable_target():
    sup = ESTIMATE["sup:F"]
    terms = complete_offer(STABILISE, {"unit_price": 40})
    target = total_cost(STABILISE, terms, supplier=sup)
    price = price_for_budget(STABILISE, terms, target, supplier=sup)
    assert price >= 40
    assert total_cost(STABILISE, {**terms, "unit_price": price}, supplier=sup) <= target
    with pytest.raises(InfeasiblePackage):
        price_for_budget(STABILISE, terms, -1, supplier=sup)


@pytest.mark.parametrize("price", [0, -1, float("inf"), float("nan"), True])
def test_invalid_prices_never_reach_a_sheet(price):
    with pytest.raises(InfeasiblePackage):
        evaluate(STABILISE, {"unit_price": price})
