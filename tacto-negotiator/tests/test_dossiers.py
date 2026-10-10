import json

import pytest
from arena_kit.cost import relationship_cost, supplier_value, total_cost

from negotiator import dossiers as D
from negotiator import traits


@pytest.fixture(scope="module")
def pkg():
    try:
        return D.load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


@pytest.fixture(scope="module")
def built(pkg):
    return D.build(pkg)


def case(goal="stabilise", supplier="sup:70110", part="part:310010", price=126.53) -> dict:
    return {
        "case_id": "case:T", "type": "price_increase", "parts": [part], "suppliers": [supplier],
        "negotiable": ["unit_price", "payment_days"], "fixed_terms": {"lead_time_days": 42, "incoterm": "FCA"},
        "buyer": {"category_goal": goal, "need_per_year": 8150, "horizon_years": 1, "current_unit_price": price,
                  "fallback_unit_price": 145.0, "interest_rate": 0.08, "reference_payment_days": 60,
                  "need_lead_time_days": 42, "freight_eur_per_unit": {"EXW": 2.0, "FCA": 1.2, "DAP": 0.0},
                  "sustainable_margin_pct": 4, "relationship_eur_per_point": 5000},
    }


def test_build_matches_prototype_traits(built):
    assert len(built) == 46
    d = built["sup:70110"]
    assert d.traits >= {"wants_fast_payment", "partnership_owner", "stale_index_owner", "not_tracking_costs"}
    assert traits.evidence(d, "wants_fast_payment")
    assert d.should_cost["part:310010"]["unit_cost"] == 132.64


def test_supplier_estimate_brandlhuber(pkg, built):
    est = D.supplier_estimate(case(), "sup:70110", pkg, built)
    assert est["full_cost"] == 132.64 and est["cost_basis"] == "supplier_plant"
    assert est["full_cost_range"] == (126.01, 139.27)
    assert est["interest_rate"] > est["usual_rate"]  # wants_fast_payment
    assert est["standard"]["payment_days"] == 30 and est["standard"]["incoterm"] == "FCA"
    assert any("margin at current price" in n for n in est["notes"])
    c = case()
    terms = {"unit_price": 136.0, "payment_days": 30}
    assert supplier_value(c, terms, est) > 0
    assert relationship_cost(c, terms, supplier=est) >= 0
    low = relationship_cost(c, {"unit_price": 126.53, "payment_days": 60}, supplier=est)
    assert low > relationship_cost(c, {"unit_price": 140.0, "payment_days": 30}, supplier=est)
    assert total_cost(c, terms, est["standard"], est) > total_cost(c, terms, est["standard"])


def test_cash_short_rate(pkg, built):
    crisis = next(s for s, d in built.items() if "liquidity_crisis" in d.traits)
    part = next(iter(built[crisis].should_cost), "part:310010")
    est = D.supplier_estimate(case(supplier=crisis, part=part), crisis, pkg, built)
    assert est["interest_rate"] == D.CRISIS_RATE
    calm = next(s for s, d in built.items() if not d.traits & traits.CASH_SHORT and d.should_cost)
    est = D.supplier_estimate(case(supplier=calm, part=next(iter(built[calm].should_cost))), calm, pkg, built)
    assert est["interest_rate"] == D.BASE_RATE


def test_non_relationship_goal_returns_none(pkg, built):
    assert D.supplier_estimate(case(goal="leverage"), "sup:70110", pkg, built) is None
    assert D.supplier_estimate(case(goal="leverage"), "sup:70110", pkg, built, force=True)


def test_german_base_row_gets_country_factor(pkg, built):
    row = pkg.query("SELECT part_id FROM should_cost WHERE supplier_id IS NULL OR supplier_id = '' LIMIT 1")[0]
    cz = next(s for s, d in built.items() if d.country == "CZ")
    est = D.supplier_estimate(case(supplier=cz, part=row["part_id"]), cz, pkg, built)
    base = pkg.query("SELECT unit_cost FROM should_cost WHERE part_id = ?", (row["part_id"],))[0]["unit_cost"]
    assert est["cost_basis"] == "german_base"
    assert est["full_cost"] == pytest.approx(base * D.COUNTRY_FACTOR["CZ"], abs=0.01)


def test_release_news_adds_trait(pkg, tmp_path):
    calm = "sup:70520"
    rel = tmp_path / "release-sunday"
    rel.mkdir()
    (rel / "facts.json").write_text(json.dumps({"news:20261011-99": {
        "date": "2026-10-11", "headline": "x", "supplier": calm, "topic": "credit_watch"}}))
    p = D.load_package(str(pkg.root), release=str(rel))
    d = D.build(p)[calm]
    assert "credit_watch" in d.traits
    est = D.supplier_estimate(case(supplier=calm, part="part:350010", price=217.77), calm, p)
    assert est["interest_rate"] == D.CASH_SHORT_RATE


def test_for_case_adds_case_news(built):
    c = case()
    c["facts"] = {"news:X-1": {"supplier": "sup:70110", "topic": "restructuring", "date": "2026-10-01"}}
    d = D.for_case(built, c)["sup:70110"]
    assert "restructuring" in d.traits and "restructuring" not in built["sup:70110"].traits
