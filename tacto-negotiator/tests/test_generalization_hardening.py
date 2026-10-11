"""Generalisation hardening (AUDIT-generalization.md #1-#4): what the v6 agent must NOT say on cases that
are not in the practice set - per-100 / per-1000 parts, a fixed volume in price units, raw_material cases
without a reconcilable fixed-volume plan, a listing without `type`. All fail closed; every practice case
replays byte-identically (the practice parts with claims are priced per 1, their briefings reconcile)."""

import copy
import json
from pathlib import Path

import pytest

from negotiator import claims, fixed_volume
from negotiator.agent import PackageAgent
from negotiator.dossiers import load_package
from negotiator.policy import PolicyConfig

CASES = {c["case_id"]: c for c in json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())}
V6 = "configs/score-push-v6.json"


@pytest.fixture(scope="module")
def package():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def _sup(sid, n, price, status="open", body="Which volume can you commit to?", **terms):
    return {"from": f"sales@{sid[4:]}", "status": status, "body": body, "attachments": [], "refs": [],
            "term_sheets": [{"term_sheet_id": f"offer:{sid[4:]}-{n}", "terms": {"unit_price": price, **terms}}]}


def _play(agent, case, sid, replies):
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


# -- #1 price basis --------------------------------------------------------------------------------


def test_unit_price_fails_closed_on_per_100_and_per_1000_lines():
    assert claims._unit_price({"unit_price": 6.06, "price_unit": 1}) == 6.06
    assert claims._unit_price({"unit_price": 6.06}) == 6.06
    assert claims._unit_price({"unit_price": 6.06, "price_unit": None}) == 6.06
    assert claims._unit_price({"unit_price": 84.34, "price_unit": 100}) is None
    assert claims._unit_price({"unit_price": 316.0, "price_unit": 1000}) is None
    assert claims._unit_price({"unit_price": 84.34, "price_unit": 100, "currency": "EUR"}) is None


def test_no_po_or_quote_claim_on_a_per_100_part(package):
    """P16 (part:370020, EUR 84.34 per 100 kg): the ladder has no po_history claim and the deep bank has no
    po_history / own_quote claim - rather than "EUR 0.84 per unit" next to a 94.44 ask. The index claims stay."""
    c = CASES["case:P16"]
    sid = c["suppliers"][0]
    facts = claims.case_facts(c, package)
    pos = [f for r, f in facts.items()
           if r.startswith("po:") and f.get("supplier") == sid and f.get("part") == c["parts"][0]]
    assert pos and all(f.get("price_unit") == 100 for f in pos)  # the fixture is really per-100
    ladder = fixed_volume.ladder(c, package, sid)
    assert all(k.kind == "index_change" for k in ladder)  # 370020's drivers show no recent fall: empty is fine
    assert all(k.kind not in ("po_history", "own_quote") for k in claims.history_claims(c, package))
    # a hand-built per-100 PO claim is rejected by the checker as well
    ids = tuple(sorted(r for r, f in facts.items() if r.startswith("po:") and f.get("supplier") == sid
                       and f.get("part") == c["parts"][0])[:2])
    bad = claims.Claim(kind="po_history", ids=ids, figure=0.84, unit="EUR", sentence=" ".join(ids),
                       supplier_id=sid, part_id=c["parts"][0], disclosure="supplier_own", subject=sid)
    assert claims._check(bad, facts, package, c) == "invalid price basis"


def test_p08_po_claim_unchanged_on_a_per_1_part(package):
    c = CASES["case:P08"]
    ladder = fixed_volume.ladder(c, package, c["suppliers"][0])
    po = [k for k in ladder if k.kind == "po_history"]
    assert po and po[0].figure == 5.17 and "EUR 5.17 per unit" in po[0].sentence


# -- #2 fixed volume in real units -------------------------------------------------------------------


def test_need_line_parses_count_multiplier_and_unit():
    assert fixed_volume.need({"briefing": "Need: 94800 kg a year. Current 5.70."}) == (94800, 1, "kg")
    assert fixed_volume.need({"briefing": "Need: 5510 x 100 kg a year."}) == (5510, 100, "kg")
    assert fixed_volume.need({"briefing": "Need: 3420 x 100 m a year."}) == (3420, 100, "m")
    assert fixed_volume.need({"briefing": "Need: 8150 pc a year."}) == (8150, 1, "units")
    assert fixed_volume.need({"briefing": "no volume here"}) is None
    assert fixed_volume.need({}) is None


def test_p16_plan_states_the_real_quantity_and_full_share(package):
    c = CASES["case:P16"]
    sid = c["suppliers"][0]
    p = fixed_volume.plan(c, package, sid)
    assert p and p["volume"] == 551000 and p["unit"] == "kg" and p["total"] == 551000
    text, ids = fixed_volume.first_paragraph(p, {"contract_months": 24})
    assert "551000 kg" in text and "1102000 kg in total" in text and "5510 kg" not in text
    assert ids == [p["fc"]]
    att = fixed_volume.attachment(p)
    import base64

    csv = base64.b64decode(att["content_b64"]).decode().splitlines()
    month = csv[1].split(",")
    assert month[3] == month[4]  # 100 % quota: committed = forecast, not 1 %
    assert "binding annual volume under this contract: 551000" in csv[-1]


def test_p08_plan_unchanged(package):
    p = fixed_volume.plan(CASES["case:P08"], package, "sup:70710")
    assert p["volume"] == 94800 and p["unit"] == "kg" and p["total"] == 118500


def test_plan_is_none_when_the_volume_does_not_reconcile(package):
    c = CASES["case:P16"]
    sid = c["suppliers"][0]
    # briefing count disagrees with the fixed volume
    assert fixed_volume.plan({**c, "fixed_terms": {**c["fixed_terms"], "volume_per_year": 5500}}, package, sid) is None
    # no Need line at all
    assert fixed_volume.plan({**c, "briefing": "Raw material case."}, package, sid) is None
    # multiplier makes the quantity exceed the whole shared forecast
    assert fixed_volume.plan({**c, "briefing": "Need: 5510 x 1000 kg a year."}, package, sid) is None


def test_p16_opening_body_has_the_right_quantity_and_no_per_unit_po_claim(package):
    c = CASES["case:P16"]
    sid = c["suppliers"][0]
    agent = PackageAgent(policy=PolicyConfig.load(V6), claims=False)
    replies = [_sup(sid, i, 94.44, payment_days=30, contract_months=12, index_clause=None) for i in range(4)]
    moves = _play(agent, c, sid, replies)
    bodies = [m["message"]["body"] for m in moves if m.get("message", {}).get("term_sheets")]
    assert "551000 kg" in bodies[0] and "5510 kg" not in bodies[0]
    assert moves[0]["message"]["attachments"][0]["type"] == "csv"
    assert not any("per unit" in b for b in bodies)
    refs = [r for m in moves for r in (m.get("message") or {}).get("refs") or []]
    assert refs and all(r.startswith(("fc:", "idx:")) for r in refs)


# -- #3 raw_material without a plan falls through to the generic evidence path ------------------------


class _Trace:
    def __init__(self):
        self.rows = []

    def log(self, event, **fields):
        self.rows.append({"event": event, **fields})


def test_raw_material_without_fixed_volume_still_cites_evidence(package):
    """P18's supplier (70740) minus the fixed volume: no plan -> the generic v4 evidence path runs
    (AS-14404 / PPI-C2431 falls, orders, scorecard) instead of six silent rounds. 70710 (P08) would still
    send nothing on that path - its hedge statements empty the preferred bank, as under v4."""
    c = copy.deepcopy(CASES["case:P18"])
    del c["fixed_terms"]["volume_per_year"]
    sid = c["suppliers"][0]
    trace = _Trace()
    agent = PackageAgent(policy=PolicyConfig.load(V6), claims=False, tracer=trace)
    assert agent._fixed_volume_plan(c, sid) is None
    replies = [_sup(sid, i, 5.94, payment_days=30, contract_months=12, index_clause=None) for i in range(5)]
    moves = _play(agent, c, sid, replies)
    refs = [r for m in moves for r in (m.get("message") or {}).get("refs") or []]
    assert refs and any(r.startswith("idx:") for r in refs)  # the v4 index-fall claims, not silence
    assert any(r["event"] == "evidence_selection" for r in trace.rows)
    assert not any((m.get("message") or {}).get("attachments") for m in moves)
    # with the plan (P18 as shipped) the ladder owns the claims: no generic selection at all
    plain = _Trace()
    shipped = PackageAgent(policy=PolicyConfig.load(V6), claims=False, tracer=plain)
    _play(shipped, CASES["case:P18"], sid, replies[:2])
    assert shipped._fixed_volume_plan(CASES["case:P18"], sid) is not None
    assert not any(r["event"] == "evidence_selection" for r in plain.rows)


# -- #4 missing type is inert -----------------------------------------------------------------------


def test_missing_type_does_not_raise_and_uses_the_default_schedule(package):
    c = copy.deepcopy(CASES["case:P08"])
    del c["type"]
    sid = c["suppliers"][0]
    agent = PackageAgent(policy=PolicyConfig.load(V6), claims=False)
    move = agent.decide(c, {sid: [_sup(sid, 0, 5.94, payment_days=30, contract_months=12, index_clause=None)]})
    terms = move["message"]["term_sheets"][0]["terms"]
    assert abs(terms["unit_price"] - 5.94 * (1 - agent.anchor)) < 0.02  # default anchor, not the 0.19 ladder
    assert "type" not in c  # the caller's dict is left alone
    moves = _play(agent, c, sid, [_sup(sid, i, 5.94, payment_days=30, contract_months=12, index_clause=None)
                                  for i in range(6)])
    assert all("message" in m or m.get("close") for m in moves)
