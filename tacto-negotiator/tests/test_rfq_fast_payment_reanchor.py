"""Opt-in `rfq_fast_payment_reanchor`: port of archive/codex/score-push-p05 fd195f3 `_rfq_fast_payment`
(the 0.8136 P05 lever). At the one-time RFQ undercut re-anchor the sheet moves to the shortest legal
payment term iff the supplier wrote that faster payment is welcome and the sheet is C-cheaper for us."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from replay_decisions import load_config, make_agent, replay_config  # noqa: E402
from test_evaluator import msg, ours  # noqa: E402

from negotiator.agent import PackageAgent  # noqa: E402
from negotiator.policy import PolicyConfig  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
V3 = json.loads((ROOT / "configs/score-push-v3.json").read_text())
SAVED = json.loads((ROOT / "tests/fixtures/p05_fast_payment_run.json").read_text())
ASKED = "Faster payment is welcome; we can reflect it in the price."
T35 = {"payment_days": 30, "lead_time_days": 35}


def test_flag_validates_and_defaults_off():
    assert PolicyConfig.from_dict({"version": 1}).rfq_fast_payment_reanchor is False
    assert PolicyConfig.from_dict({**V3, "rfq_fast_payment_reanchor": True}).rfq_fast_payment_reanchor is True
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "rfq_fast_payment_reanchor": "yes"})


def _threads(case, body, asked_by=None):
    """Supplier a opens 32.00/30d, we countered 31.74/90d, a replies 29.00/30d with `body` (an undercut of
    our ask); b opened 34.00/30d. `asked_by`: a second supplier whose reply carries the fast-payment text."""
    a, b = case["suppliers"][:2]
    first = msg("open", ("offer:a-1", {**T35, "unit_price": 32.0}))
    last = {**msg("open", ("offer:a-2", {**T35, "unit_price": 29.0})), "body": body}
    threads = {a: [first, ours({**T35, "unit_price": 31.74, "payment_days": 90}), last],
               b: [msg("open", ("offer:b-1", {**T35, "unit_price": 34.0}))]}
    if asked_by:
        threads[b][0] = {**threads[b][0], "body": ASKED}
    return threads


def _agent(**cfg):
    return PackageAgent(policy=PolicyConfig(rfq_undercut_reanchor=True, **cfg), model_assist=False)


def test_rfq_fast_payment_only_when_asked_and_cheaper_in_c():
    """Archived test fd195f3, keyed on the new flag."""
    case = CASES["case:P05"]
    a = case["suppliers"][0]
    on = _agent(rfq_fast_payment_reanchor=True)
    move = on.propose(case, _threads(case, ASKED), a)["message"]
    sheet = move["term_sheets"][0]["terms"]
    assert sheet["payment_days"] == 14 and sheet["unit_price"] < 29.0
    assert "14 days" in move["body"]
    off = _agent().propose(case, _threads(case, ASKED), a)["message"]
    assert off["term_sheets"][0]["terms"]["payment_days"] == 90
    assert "faster payment" not in off["body"]
    silent = _agent(rfq_fast_payment_reanchor=True)
    assert silent.propose(case, _threads(case, "We hold this price."), a)["message"]["term_sheets"][0]["terms"][
        "payment_days"] == 90


def test_lever_never_before_reanchor_and_never_for_a_supplier_that_did_not_ask():
    case = CASES["case:P05"]
    a, b = case["suppliers"][:2]
    # First counter: the supplier asked in its opening, but there is no re-anchor yet -> 90 d, no note.
    opening = {**msg("open", ("offer:a-1", {**T35, "unit_price": 32.0})), "body": ASKED}
    agent = _agent(rfq_fast_payment_reanchor=True)
    first = agent.propose(case, {a: [opening], b: [msg("open", ("offer:b-1", {**T35, "unit_price": 34.0}))]}, a)
    assert first["message"]["term_sheets"][0]["terms"]["payment_days"] == 90
    assert "faster payment" not in first["message"]["body"]
    assert not agent.fast_payment_traded
    # A small step (no undercut of our ask) after the ask is a normal converge move, not a 14-day switch.
    threads = _threads(case, ASKED)
    threads[a][-1]["term_sheets"][0]["terms"]["unit_price"] = 31.5
    step = agent.propose(case, threads, a)["message"]
    assert step["term_sheets"][0]["terms"]["payment_days"] == 90 and "faster payment" not in step["body"]
    # Only the rival asked: the undercutting supplier's own thread is silent -> plain re-anchor at 90 d.
    rival_only = _agent(rfq_fast_payment_reanchor=True)
    move = rival_only.propose(case, _threads(case, "We can come down to 29.00.", asked_by=b), a)["message"]
    assert move["term_sheets"][0]["terms"]["payment_days"] == 90 and "faster payment" not in move["body"]
    assert a not in rival_only.fast_payment_traded


def _replay(cfg):
    kwargs = load_config(ROOT / "configs/score-push-v3.json")
    kwargs["policy_config"] = {**kwargs["policy_config"], **cfg}
    rounds = replay_config(CASES["case:P05"], {s: list(m) for s, m in SAVED["threads"].items()},
                           make_agent(kwargs, conditional_exchange=False))
    return {(r["round"], r["saved_supplier"]): (r["move"] or {}).get("term_sheets") or [None] for r in rounds}


def test_saved_0_8136_transcript_replays_with_flag_on_and_is_unchanged_with_flag_off():
    """B reproduces the archived 70210 path (26.79/14d at r7, 28.00/14d at r10); flag off equals the
    pre-port HEAD decisions recorded on 3bf3959 and never sends 14 d."""
    on, off = _replay({"rfq_fast_payment_reanchor": True}), _replay({})
    sup = "sup:70210"
    assert on[(7, sup)][0] == {"unit_price": 26.79, "payment_days": 14, "lead_time_days": 35}
    assert on[(10, sup)][0] == {"unit_price": 28.0, "payment_days": 14, "lead_time_days": 35}
    head = {1: {"unit_price": 31.68, "payment_days": 90, "lead_time_days": 35},
            4: {"unit_price": 31.74, "payment_days": 90, "lead_time_days": 35},
            7: {"unit_price": 26.79, "payment_days": 90, "lead_time_days": 35},
            10: {"unit_price": 28.0, "payment_days": 90, "lead_time_days": 35}}
    for r, sheet in head.items():
        assert off[(r, sup)][0] == sheet
    assert all(sheet[0] is None or sheet[0].get("payment_days") != 14 for sheet in off.values())
    # Flag on changes only the 70210 thread from the re-anchor on; earlier rounds and rivals are untouched.
    for key in off:
        if key[1] != sup or key[0] < 7:
            assert on[key] == off[key], key
