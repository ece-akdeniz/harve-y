import base64
import json
from pathlib import Path

import pytest

from negotiator import fixed_volume
from negotiator.dossiers import load_package

CASES = json.loads((Path(__file__).parent / "fixtures" / "practice_cases.json").read_text())


def _case(cid):
    for c in CASES if isinstance(CASES, list) else CASES.get("cases", []):
        if c.get("case_id") == cid:
            return c
    pytest.skip(f"{cid} not in fixtures")


@pytest.fixture(scope="module")
def package():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def test_plan_needs_fixed_volume_and_forecast(package):
    case = _case("case:P08")
    p = fixed_volume.plan(case, package, "sup:70710")
    assert p and p["volume"] == 94800 and p["fc"].startswith("fc:370010@")
    no_vol = {**case, "fixed_terms": {k: v for k, v in case["fixed_terms"].items() if k != "volume_per_year"}}
    assert fixed_volume.plan(no_vol, package, "sup:70710") is None
    assert fixed_volume.plan({**case, "parts": ["part:1", "part:2"]}, package, "sup:70710") is None


def test_attachment_is_public_monthly_csv_with_committed_share(package):
    p = fixed_volume.plan(_case("case:P08"), package, "sup:70710")
    att = fixed_volume.attachment(p)
    assert att["type"] == "csv" and att["name"].endswith(".csv")
    csv = base64.b64decode(att["content_b64"]).decode()
    rows = [r for r in csv.splitlines() if r and not r.startswith("#")]
    assert rows[0].startswith("forecast_id,part,month,")
    assert len(rows) == 1 + len(p["lines"]) and all(p["fc"] in r for r in rows[1:])
    assert f"binding annual volume under this contract: {p['volume']}" in csv


def test_first_paragraph_cites_the_forecast_once_and_states_the_term_total(package):
    p = fixed_volume.plan(_case("case:P08"), package, "sup:70710")
    text, ids = fixed_volume.first_paragraph(p, {"contract_months": 24})
    assert ids == [p["fc"]] and text.count(p["fc"]) == 1
    assert "94800" in text and str(94800 * 2) in text and "24 months" in text
    assert "budget" not in text.lower() and "walk" not in text.lower()


def test_reminder_only_after_the_supplier_asks():
    assert fixed_volume.asked_for_volume([{"from": "sup:x", "body": "Which volume can you commit to?"}])
    assert not fixed_volume.asked_for_volume([{"from": "buyer", "body": "Which volume can you commit to?"}])
    assert not fixed_volume.asked_for_volume([{"from": "sup:x", "body": "Our price follows AS-14404."}])


def test_p08_opening_adds_volume_paragraph_forecast_file_and_fc_ref(monkeypatch, package):
    from negotiator.agent import PackageAgent
    from negotiator.policy import PolicyConfig

    c = _case("case:P08")
    sid = c["suppliers"][0]
    m0 = {"from": "sales", "status": "open", "attachments": [], "body": "Which volume can you commit to?",
          "term_sheets": [{"term_sheet_id": "offer:0",
                           "terms": {"unit_price": 6.05, "payment_days": 30, "contract_months": 12,
                                     "index_clause": None}}]}
    base = PackageAgent(policy=PolicyConfig.load("configs/score-push-v2.json"), claims=False)
    new = PackageAgent(policy=PolicyConfig.load("configs/breakthrough-ladder.json"), claims=False)
    b = base.propose(c, {sid: [m0]}, sid)["message"]
    n = new.propose(c, {sid: [m0]}, sid)["message"]
    assert "94800" in n["body"] and "fc:370010@" in n["body"]
    assert n["refs"] and all(r.startswith("fc:") for r in n["refs"])
    assert n["attachments"][0]["type"] == "csv"
    assert "attachments" not in b or not b.get("attachments")
    # the deeper raw-material anchor (0.19 below the quote) replaces the agent default
    assert n["term_sheets"][0]["terms"]["unit_price"] < b["term_sheets"][0]["terms"]["unit_price"]
    assert abs(n["term_sheets"][0]["terms"]["unit_price"] - 6.05 * 0.81) < 0.03
    # second buyer offer: only a one-line reminder when the supplier asked again, no second file
    ours = {"from": "buyer", "body": n["body"], "term_sheets": [{"terms": n["term_sheets"][0]["terms"]}]}
    m1 = {**m0, "body": "Which volume can you commit to?",
          "term_sheets": [{"term_sheet_id": "offer:1", "terms": {**m0["term_sheets"][0]["terms"], "unit_price": 5.6}}]}
    n2 = new.propose(c, {sid: [m0, ours, m1]}, sid)["message"]
    assert "binding quantity is 94800" in n2["body"] and not n2.get("attachments")


# ---------------------------------------------------------------- the claim ladder (v5)

DB0 = {"series": "AS-14404", "material_share": 0.45, "deadband_pct": 0.0, "base_month": "2026-08"}


def _sup(sid, n, price, status="open", clause=DB0, pay=90, months=24, body=""):
    return {"from": f"sales@{sid[4:]}", "status": status, "body": body, "attachments": [], "refs": [],
            "term_sheets": [{"term_sheet_id": f"offer:{sid[4:]}-{n}",
                             "terms": {"unit_price": price, "payment_days": pay, "index_clause": clause,
                                       "contract_months": months}}]}


def _play(agent, case, sid, replies):
    """Feed fixed supplier replies; return the agent's moves (the supplier never sees our asks)."""
    events, moves = [], []
    for reply in replies:
        events.append(dict(reply))
        move = agent.decide(case, {sid: events})
        moves.append(move)
        msg = move.get("message") or {}
        if msg.get("action") or not msg.get("term_sheets"):
            break
        events.append({"from": "buyer", **{k: v for k, v in msg.items() if k != "attachments"}})
    return moves


def test_ladder_order_po_lowest_price_then_one_window_per_driver(package):
    from negotiator import claims

    c = _case("case:P08")
    ladder = fixed_volume.ladder(c, package, "sup:70710")
    kinds = [x.kind for x in ladder]
    assert kinds[0] == "po_history" and kinds[1:] == ["index_change", "index_change"]
    assert ladder[0].figure == 5.17 and len(ladder[0].ids) == 3  # its lowest delivered price, not the latest orders
    assert [x.subject for x in ladder[1:]] == ["AS-14404", "PPI-C2431"]  # driver weight order, LCI-C (5 %) excluded
    assert all(claims.verify(x, claims.case_facts(c, package), package, c) for x in ladder)
    # the hedge filter of recent_index_claims is deliberately not applied on P08 (70710 "covered until March")
    assert not claims.recent_index_claims(c, package, claims.case_facts(c, package))


def test_next_claim_skips_cited_series_and_orders_at_or_above_the_ask(package):
    c = _case("case:P18")
    sid = "sup:70740"
    ev = [_sup(sid, 0, 6.10, clause=None, pay=30, months=12),
          {"from": "buyer", "refs": ["fc:370010@2026-09"], "term_sheets": [{"terms": {"unit_price": 4.94}}]},
          _sup(sid, 1, 5.60)]
    first = fixed_volume.next_claim(c, package, sid, ev)
    assert first.kind == "po_history" and first.figure == 5.26
    ev += [{"from": "buyer", "refs": list(first.ids), "term_sheets": [{"terms": {"unit_price": 5.09}}]},
           _sup(sid, 2, 5.50)]
    second = fixed_volume.next_claim(c, package, sid, ev)
    assert second.kind == "index_change" and second.subject == "AS-14404"
    ev += [{"from": "buyer", "refs": list(second.ids), "term_sheets": [{"terms": {"unit_price": 5.17}}]},
           _sup(sid, 3, 5.40)]
    third = fixed_volume.next_claim(c, package, sid, ev)
    assert third.kind == "index_change" and third.subject == "PPI-C2431"
    ev += [{"from": "buyer", "refs": list(third.ids), "term_sheets": [{"terms": {"unit_price": 5.29}}]},
           _sup(sid, 4, 5.30)]
    assert fixed_volume.next_claim(c, package, sid, ev) is None  # every series used once; nothing stacked
    # an order price at or above the standing ask is no argument
    low = [_sup(sid, 0, 5.20, clause=None, pay=30, months=12),
           {"from": "buyer", "refs": [], "term_sheets": [{"terms": {"unit_price": 4.5}}]}, _sup(sid, 1, 5.20)]
    assert fixed_volume.next_claim(c, package, sid, low).kind == "index_change"
    # nothing after the supplier's final offer
    assert fixed_volume.next_claim(c, package, sid, ev[:-1] + [_sup(sid, 4, 5.30, status="final_offer")]) is None


def test_v5_p08_ladder_one_claim_per_round_real_steps_and_accepts_final(package):
    from negotiator.agent import PackageAgent
    from negotiator.policy import PolicyConfig

    c = _case("case:P08")
    sid = "sup:70710"
    agent = PackageAgent(policy=PolicyConfig.load("configs/score-push-v5.json"), claims=False)
    replies = [_sup(sid, 0, 6.05, clause=None, pay=30, months=12), _sup(sid, 1, 5.45), _sup(sid, 2, 5.31),
               _sup(sid, 3, 5.16, status="final_offer")]
    moves = _play(agent, c, sid, replies)
    msgs = [m["message"] for m in moves]
    prices = [m["term_sheets"][0]["terms"]["unit_price"] for m in msgs[:3]]
    assert prices[0] == 4.88 and all(b - a >= 0.05 for a, b in zip(prices, prices[1:], strict=False))
    assert all(m["term_sheets"][0]["terms"]["index_clause"] is None for m in msgs[:3])  # one no-clause sheet
    assert all(m["term_sheets"][0]["terms"]["payment_days"] == 90 for m in msgs[:3])  # payment never moves
    assert all(len(m["term_sheets"]) == 1 for m in msgs[:3])
    assert msgs[0]["refs"] == ["fc:370010@2026-09"] and msgs[0]["attachments"][0]["type"] == "csv"
    assert [r[:3] for r in msgs[1]["refs"]] == ["po:"] * 3 and len(msgs[1]["refs"]) == 3
    assert msgs[2]["refs"] == ["idx:AS-14404@2026-06", "idx:AS-14404@2026-09"]
    assert "attachments" not in msgs[1] and "attachments" not in msgs[2]
    assert msgs[3]["action"] == {"type": "accept", "term_sheet_id": "offer:70710-3"}  # final taken at once


def test_v5_p18_ladder_and_time_budget_floor(package):
    from negotiator.agent import PackageAgent
    from negotiator.policy import PolicyConfig

    c = _case("case:P18")
    sid = "sup:70740"
    agent = PackageAgent(policy=PolicyConfig.load("configs/score-push-v5.json"), claims=False)
    replies = [_sup(sid, 0, 6.10, clause=None, pay=30, months=12), _sup(sid, 1, 5.60), _sup(sid, 2, 5.50),
               _sup(sid, 3, 5.40), _sup(sid, 4, 5.20, status="final_offer")]
    msgs = [m["message"] for m in _play(agent, c, sid, replies)]
    prices = [m["term_sheets"][0]["terms"]["unit_price"] for m in msgs[:4]]
    assert prices[0] == 4.94 and all(b - a >= 0.05 for a, b in zip(prices, prices[1:], strict=False))
    assert [m.get("refs", [None])[0][:3] for m in msgs[:4]] == ["fc:", "po:", "idx", "idx"]
    assert msgs[4]["action"]["term_sheet_id"] == "offer:70740-4"
    # a supplier that holds at 5.70 for ever: our price reaches its ask by the 5th sheet (default k/5
    # convergence as the floor), so the thread closes within ~6 replies in a wave
    agent = PackageAgent(policy=PolicyConfig.load("configs/score-push-v5.json"), claims=False)
    hold = [_sup(sid, 0, 6.10, clause=None, pay=30, months=12)] + [_sup(sid, i, 5.70) for i in range(1, 9)]
    msgs = [m["message"] for m in _play(agent, c, sid, hold)]
    sheets = [m for m in msgs if m.get("term_sheets")]
    assert len(sheets) <= 6 and sheets[-1]["term_sheets"][0]["terms"]["unit_price"] == 5.70
    assert msgs[-1].get("action", {}).get("type") == "accept"
