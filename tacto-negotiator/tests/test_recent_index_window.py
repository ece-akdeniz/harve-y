"""Opt-in recent buyer windows change only the first P18 counter's body/refs."""

import json
from pathlib import Path

from negotiator.agent import configured_agent
from negotiator.claims import recent_buyer_window

ROOT = Path(__file__).resolve().parents[1]


def test_recent_buyer_window_ends_at_latest_month():
    values = {"2026-01": 100.0, "2026-04": 90.0, "2026-06": 110.0, "2026-09": 104.0}
    assert recent_buyer_window(values) == ("2026-06", "2026-09")
    assert recent_buyer_window({"2026-01": 100.0, "2026-02": 101.0}) is None


def test_p18_recent_windows_only_decorate_first_counter():
    config = json.loads((ROOT / "configs/p18-recent-index-window.json").read_text())
    agent = configured_agent(**config)
    agent.conditional_exchange = True
    case = next(c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == "case:P18")
    thread = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
    sent, decorated = [], []
    for i, message in enumerate(thread["messages"]):
        if message.get("from") != "buyer":
            continue
        it = iter(sent)
        history = [next(it) if e.get("from") == "buyer" else e for e in thread["messages"][:i]]
        move = agent.decide(case, {thread["supplier_id"]: history})["message"]
        original = {k: v for k, v in message.items() if k != "from"}
        assert move.get("term_sheets") == original.get("term_sheets")
        assert move.get("action") == original.get("action")
        if move.get("body") != original.get("body"):
            decorated.append(move)
        sent.append({"from": "buyer", **move})
    assert len(decorated) == 1
    assert decorated[0] == {k: v for k, v in sent[0].items() if k != "from"}
    assert decorated[0]["refs"] == ["idx:AS-14404@2026-06", "idx:AS-14404@2026-09",
                                    "idx:PPI-C2431@2026-06", "idx:PPI-C2431@2026-08"]
    assert "fell 5.5 %" in decorated[0]["body"] and "fell 2.3 %" in decorated[0]["body"]
