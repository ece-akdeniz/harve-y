"""Per-case-type opening anchor (opt-in): the retained policy is unchanged when omitted."""

import json
from pathlib import Path

import pytest

from negotiator.agent import configured_agent
from negotiator.policy import PolicyConfig

ROOT = Path(__file__).resolve().parents[1]


def _first_offer(config_name, case_id, thread):
    config = json.loads((ROOT / f"configs/{config_name}.json").read_text())
    agent = configured_agent(**config)
    agent.conditional_exchange = True
    case = next(c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == case_id)
    move = agent.decide(case, {thread["supplier_id"]: thread["messages"][:1]})
    return move["message"]["term_sheets"][0]["terms"]


def test_raw_material_anchor_deepens_only_the_opening_price():
    thread = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
    base = _first_offer("retained-package-policy", "case:P18", thread)
    deep = _first_offer("rawmat-anchor16", "case:P18", thread)
    assert base["unit_price"] == 5.37
    assert deep["unit_price"] == 5.12
    assert {k: v for k, v in deep.items() if k != "unit_price"} == {
        k: v for k, v in base.items() if k != "unit_price"
    }


@pytest.mark.parametrize("anchors", [{"rfqx": 0.1}, {"raw_material": 0.5}, {"raw_material": True}, []])
def test_invalid_anchors_rejected(anchors):
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "anchors": anchors})
