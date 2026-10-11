import json
from pathlib import Path

from arena_kit.cost import total_cost

from negotiator.explore import Explorer


def test_standing_selects_lowest_total_cost_across_alternatives():
    cases = json.loads((Path(__file__).parent / "fixtures" / "practice_cases.json").read_text())
    case = next(case for case in cases if case["case_id"] == "case:P18")
    clause = {"series": "AS-14404", "material_share": 0.45, "base_month": "2026-08"}
    expensive = {
        "unit_price": 5.20,
        "payment_days": 90,
        "contract_months": 24,
        "index_clause": {**clause, "deadband_pct": 0},
    }
    cheap = {
        "unit_price": 5.30,
        "payment_days": 90,
        "contract_months": 24,
        "index_clause": {**clause, "deadband_pct": 5},
    }
    events = [
        {
            "from": "sup:test",
            "status": "final_offer",
            "term_sheets": [
                {"term_sheet_id": "offer:primary", "terms": expensive},
                {"term_sheet_id": "offer:alternative", "terms": cheap},
            ],
        }
    ]

    sheet_id, terms, cost, std = Explorer.standing(case, events)

    assert total_cost(case, cheap, std) < total_cost(case, expensive, std)
    assert sheet_id == "offer:alternative"
    assert terms == cheap
    assert cost == total_cost(case, cheap, std)
