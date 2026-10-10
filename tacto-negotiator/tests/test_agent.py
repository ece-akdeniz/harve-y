import json
from importlib.resources import files

from arena_kit.cost import must_haves_ok, total_cost

from negotiator.agent import PackageAgent
from negotiator.optimizer import alternative_cost, best_terms


def _case(name):
    return json.loads(files("arena_kit").joinpath(f"sim_cases/{name}.json").read_text())


def test_best_terms_beats_plan_and_keeps_must_haves():
    case = _case("S03")
    terms = best_terms(case, 230.0)
    assert set(terms) == set(case["negotiable"])
    assert must_haves_ok(case, terms)
    for combo_field, options in case["term_options"].items():
        for v in options:
            assert total_cost(case, terms) <= total_cost(case, {**terms, combo_field: v}) + 1e-6


def test_never_accepts_above_alternative():
    case = _case("S03")
    pricey = alternative_cost(case) * 2 / (case["buyer"]["need_per_year"] * 2)
    sup = case["suppliers"][0]
    threads = {sup: [{"from": "sales", "status": "agreed", "attachments": [],
                      "term_sheets": [{"term_sheet_id": "offer:x", "terms": {"unit_price": pricey}}]}]}
    move = PackageAgent().decide(case, threads)
    assert move["message"]["action"]["type"] == "walk_away"


def test_offer_has_exact_negotiable_fields_and_no_leak():
    case = _case("S02")
    threads = {
        s: [{"from": "sales", "status": "open", "attachments": [],
             "term_sheets": [{"term_sheet_id": f"offer:{s}-0", "terms": {"unit_price": 17.0}}]}]
        for s in case["suppliers"]
    }
    move = PackageAgent().decide(case, threads)
    sheet = move["message"]["term_sheets"][0]["terms"]
    assert set(sheet) == set(case["negotiable"])
    assert sheet["unit_price"] < 17.0


def test_standing_picks_cheapest_of_several_sheets():
    from negotiator.agent import standing

    case = _case("S01")
    events = [{"from": "sales", "status": "open", "attachments": [], "term_sheets": [
        {"term_sheet_id": "offer:a", "terms": {"unit_price": 17.0, "payment_days": 60}},
        {"term_sheet_id": "offer:b", "terms": {"unit_price": 16.0, "payment_days": 60}},
    ]}]
    assert standing(case, events)[0] == "offer:b"
