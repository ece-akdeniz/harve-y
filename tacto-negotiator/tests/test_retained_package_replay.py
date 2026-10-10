"""Protect the original agent-visible negotiation that reached the P18 best."""

import json
from pathlib import Path

from negotiator.agent import configured_agent


def test_retained_policy_reproduces_every_historical_buyer_message():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/retained-package-policy.json").read_text())
    agent = configured_agent(**config)
    agent.conditional_exchange = True  # installed runtime guidance used by CLI
    case = next(c for c in json.loads((root / "tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == "case:P18")
    thread = json.loads((root / "tests/fixtures/p18_retained_thread.json").read_text())
    checked = 0
    for i, message in enumerate(thread["messages"]):
        if message.get("from") != "buyer":
            continue
        move = agent.decide(case, {thread["supplier_id"]: thread["messages"][:i]})
        assert move["supplier_id"] == thread["supplier_id"]
        assert move["message"] == {k: v for k, v in message.items() if k != "from"}
        checked += 1
    assert checked == 5
