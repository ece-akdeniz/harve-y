"""tools/replay_decisions.py: the P18 fixture thread replayed under score-push-v3 against itself is identical."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_tool():
    spec = importlib.util.spec_from_file_location("replay_decisions", ROOT / "tools/replay_decisions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _p18():
    case = next(c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == "case:P18")
    thread = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
    return case, {thread["supplier_id"]: thread["messages"]}


def test_p18_fixture_same_config_is_identical():
    tool = _load_tool()
    case, saved = _p18()
    cfg = tool.load_config("configs/score-push-v3.json")
    assert cfg["estimates"] == {} and cfg["meso"] is False and cfg["model_assist"] is False
    result = tool.replay_threads(case, saved, cfg, cfg)
    assert result["first_divergence"] is None
    assert result["conditional_exchange"] is True  # fixture bodies mention the conditional exchange
    assert len(result["rounds"]) == sum(m.get("from") == "buyer" for m in saved["sup:70740"])
    assert all(r["diff"] == [] and not r["history_invalid"] for r in result["rounds"])
    assert all(r["supplier"] == "sup:70740" and not r["supplier_mismatch"] for r in result["rounds"])
    assert tool._what(result) == "identical"


def test_p18_fixture_retained_config_matches_saved_moves():
    tool = _load_tool()
    case, saved = _p18()
    cfg = tool.load_config("configs/p18-recent-index-window.json")
    result = tool.replay_threads(case, saved, cfg, cfg, conditional_exchange="on")
    # The fixture was produced with this config: term sheets and actions agree with the saved moves.
    assert result["first_vs_saved"] is None
    assert [r["price_a"] for r in result["rounds"]][:1] == [5.37]


def test_divergence_is_reported_at_first_round_then_flagged():
    tool = _load_tool()
    offer = {"term_sheets": [{"unit_price": 5.0, "payment_days": 30}], "action": None, "refs": [], "body": "x"}
    other = {"term_sheets": [{"unit_price": 4.5, "payment_days": 60}], "action": None, "refs": ["idx:a"], "body": "y"}
    rounds_a = [{"round": 1, "saved_supplier": "s", "move": offer, "saved": offer, "error": None},
                {"round": 2, "saved_supplier": "s", "move": offer, "saved": offer, "error": None}]
    rounds_b = [{"round": 1, "saved_supplier": "s", "move": offer, "saved": offer, "error": None},
                {"round": 2, "saved_supplier": "s", "move": other, "saved": offer, "error": None}]
    result = tool.compare(rounds_a, rounds_b)
    assert result["first_divergence"] == 2
    assert result["rounds"][1]["diff"] == ["price 5.0 vs 4.5 (delta -0.5)", "terms payment_days: 30 vs 60",
                                           "refs [] vs ['idx:a']", "body differs"]
    assert not result["rounds"][1]["history_invalid"]
    third_a, third_b = {**rounds_a[0], "round": 3}, {**rounds_b[1], "round": 3}
    result = tool.compare(rounds_a + [third_a], rounds_b + [third_b])
    assert result["rounds"][2]["history_invalid"] and result["first_divergence"] == 2
    assert tool._what(result).endswith("(+1 later rounds differ, history invalid)")
    assert tool.diff_summaries(offer, {**offer, "body": None}) == []  # saved bodies may be missing
    assert tool.diff_summaries({**offer, "refs": ["idx:a"]}, {**offer, "refs": None}) == []  # saved refs unknown
    assert tool._summary({"term_sheets": [{"terms": {"unit_price": 1}}]}, saved=True)["refs"] is None
    assert tool._summary({"term_sheets": [{"terms": {"unit_price": 1}}]})["refs"] == []


def test_decision_points_follow_message_index_across_threads():
    tool = _load_tool()
    sup, buyer = {"from": "sales@1"}, {"from": "buyer"}
    threads = {"sup:2": [sup, buyer, sup, buyer], "sup:1": [sup, buyer, sup]}
    assert tool.decision_points(threads) == [(1, "sup:1"), (1, "sup:2"), (3, "sup:2")]
    assert tool.thread_messages({"messages": [sup]}) == [sup] and tool.thread_messages(None) == []
