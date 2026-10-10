import json
from pathlib import Path

from negotiator.agent import PackageAgent
from negotiator.evaluator import total_cost
from negotiator.policy import PolicyConfig
from negotiator.trades import TradePolicy

ROOT = Path(__file__).parents[1]
CASES = json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())


def _case(cid):
    return next(c for c in CASES if c["case_id"] == cid)


def test_clause_variants_equal_cost_and_only_deadband_differs():
    case = _case("case:P18")
    agent = PackageAgent(policy=PolicyConfig.load(ROOT / "configs/p18-clause-variants.json"), estimates={}, meso=False)
    std = case["buyer"]["alternative"]["terms"]
    clause = case["term_options"]["index_clause"][1]
    terms = {"unit_price": 5.40, "payment_days": 30, "contract_months": 24, "index_clause": clause}
    variants = agent._clause_variants(case, [], terms, std, None)
    assert [v["index_clause"]["deadband_pct"] for v in variants] == [5, 3]
    c_main = total_cost(case, terms, std, None)
    for v in variants:
        assert v["index_clause"] in case["term_options"]["index_clause"]
        assert all(v[k] == terms[k] for k in terms if k not in ("unit_price", "index_clause"))
        assert total_cost(case, v, std, None) <= c_main + 1e-6
    probed = [{"from": "buyer", "term_sheets": [{"terms": terms}, *({"terms": v} for v in variants)]}]
    assert agent._clause_probed(probed)
    assert agent._clause_variants(case, probed, terms, std, None) == []


def test_clause_variants_off_by_default():
    case = _case("case:P18")
    agent = PackageAgent(policy=PolicyConfig.load(ROOT / "configs/package-advice.json"), estimates={}, meso=False)
    terms = {"unit_price": 5.40, "index_clause": case["term_options"]["index_clause"][1]}
    assert agent._clause_variants(case, [], terms, {}, None) == []


def test_longer_tenor_is_cost_neutral_tie_break():
    case = _case("case:P08")
    std = case["buyer"]["alternative"]["terms"]
    out = {}
    for name in ("package-advice.json", "p08-longer-tenor.json"):
        tp = TradePolicy(PolicyConfig.load(ROOT / "configs" / name), lambda *a, **k: None)
        tp.traits = {s: set() for s in case["suppliers"]}
        t = tp.initial(case, case["suppliers"][0], 6.06, 0.1, std, None)
        out[name] = {**t, "unit_price": 5.5}
    assert out["p08-longer-tenor.json"]["contract_months"] == 36
    assert total_cost(case, out["p08-longer-tenor.json"], std, None) <= total_cost(
        case, out["package-advice.json"], std, None
    ) + 1e-6
