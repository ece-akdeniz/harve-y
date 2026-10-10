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


def _enrich(config_name, case):
    from negotiator.evidence import EvidencePolicy
    from negotiator.policy import PolicyConfig

    policy = PolicyConfig.from_dict(json.loads((ROOT / "configs" / config_name).read_text())["policy_config"])
    ev = EvidencePolicy(case_types=policy.evidence_types, recent_window_types=policy.recent_index_window_types)
    sid = case["suppliers"][0]
    move = {"supplier_id": sid, "message": {"body": "Offer.", "term_sheets": [{"terms": {"unit_price": 1.0}}]}}
    return ev.enrich(case, {sid: []}, sid, move)


def test_fact_keyed_windows_only_change_cases_with_unhedged_recent_falls():
    cases = [c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
             if c.get("hosted") and len(c["suppliers"]) == 1]
    changed = {c["case_id"] for c in cases
               if _enrich("recent-index-window.json", c) != _enrich("retained-package-policy.json", c)}
    # P08's supplier documents covered material (letter + quote remark): no index claims there.
    assert changed == {"case:P18"}


def test_hedge_sentence_naming_material_hedges_matching_series_only():
    from negotiator.claims import _HEDGE, _stems

    sentence = _HEDGE.search("Note: our nickel and alloys requirement is covered at fixed prices until 2027.").group(0)
    assert _stems("Alloy surcharge 1.4404") & _stems(sentence)
    assert not _stems("cold drawing of bars") & _stems(sentence)
