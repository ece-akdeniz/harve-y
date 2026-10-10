"""configs/p03-cost-target.json: renewal-only expected-C target (P03 public dossier estimate)."""
import json
from pathlib import Path

from negotiator.agent import configured_agent

CASES = {c["case_id"]: c for c in json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())}
CONFIG = json.loads((Path(__file__).parents[1] / "configs/p03-cost-target.json").read_text())
SID = "sup:70530"
EST = {"standard": {"payment_days": 30, "incoterm": "DAP", "lead_time_days": 49}, "interest_rate": 0.08,
       "usual_rate": 0.08, "full_cost": 403.21, "full_cost_range": (383.05, 423.37), "ppm": 0}


def sup(i, p, d=90, m=24):
    terms = {"unit_price": p, "payment_days": d, "contract_months": m, "volume_per_year": 4580}
    return {"from": "sales@70530", "status": "open", "body": "Base prices frozen.",
            "term_sheets": [{"term_sheet_id": f"offer:70530-{i}", "terms": terms}]}


def test_config_scopes_only_renewal():
    assert CONFIG == {"version": 1, "cost_target_types": ["renewal"]}
    for cid in ("case:P01", "case:P02", "case:P10"):
        assert CASES[cid]["type"] != "renewal"


def test_p03_opens_at_expected_c_target_and_never_exceeds_supplier_price():
    a = configured_agent(CONFIG, estimates={}, meso=False)
    a._target_cache[("case:P03", SID)] = EST
    events, prices = [sup(0, 438.21, 30, 12)], []
    for i in range(1, 7):
        sheet = a.decide(CASES["case:P03"], {SID: events})["message"]["term_sheets"][0]
        prices.append(sheet["terms"]["unit_price"])
        events = [*events, {"from": "buyer", "term_sheets": [sheet]}, sup(i, 433.08)]
    assert prices[0] == 423.79
    assert prices == sorted(prices) and max(prices) <= 433.08
