"""Opt-in `supplier_payment_trade`: main sheet to the supplier's payment term at public-rate value
parity, floored at buyer-cost parity, once per thread, any case type."""

import json
from pathlib import Path

import pytest
from arena_kit.cost import complete_offer, must_haves_ok, supplier_value, total_cost

from negotiator import traits as T
from negotiator.agent import PackageAgent
from negotiator.dossiers import BASE_RATE, Dossier, load_package
from negotiator.guards import leaks
from negotiator.policy import PolicyConfig

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
BASE = json.loads((ROOT / "configs/score-push-v3.json").read_text())
SIGNAL = "Thank you. Faster payment is welcome; we can reflect it in the price."
PLAIN = "Thank you for your counter. Please find our revised offer attached."
SUP = {"unit_price": 32.0, "payment_days": 30, "lead_time_days": 35}


@pytest.fixture(scope="module", autouse=True)
def package():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def agent(flag=True, **extra):
    return PackageAgent(policy=PolicyConfig.from_dict({**BASE, "supplier_payment_trade": flag, **extra}),
                        estimates={}, meso=False)


def msg(sid, status, sheet_id, terms, body=PLAIN):
    return {"from": f"sales@{sid.split(':')[1]}.example", "status": status, "attachments": [], "body": body,
            "term_sheets": [{"term_sheet_id": sheet_id, "terms": terms}]}


def ours(move):
    return {**move["message"], "from": "buyer"}


def sheet(move):
    return move["message"]["term_sheets"][0]["terms"]


def p05_threads(sid, prices=(32.0, 31.0), body=PLAIN, rival="sup:70240"):
    """P05 (rfq, payment options 14..90): supplier opens, we counter, supplier replies with `body`."""
    case = CASES["case:P05"]
    threads = {sid: [msg(sid, "open", f"offer:{sid[4:]}-1", {**SUP, "unit_price": prices[0]})]}
    if rival and rival != sid:
        threads[rival] = [msg(rival, "open", f"offer:{rival[4:]}-1", {**SUP, "unit_price": 34.0})]
    a = agent()
    first = a.propose(case, threads, sid)
    threads[sid] += [ours(first), msg(sid, "open", f"offer:{sid[4:]}-2", {**SUP, "unit_price": prices[1]}, body)]
    return case, threads, first


def test_flag_off_moves_are_identical_to_today():
    case, threads, _ = p05_threads("sup:70210", body=SIGNAL)
    off, legacy = agent(False), PackageAgent(policy=PolicyConfig.from_dict(BASE), estimates={}, meso=False)
    assert off.propose(case, threads, "sup:70210") == legacy.propose(case, threads, "sup:70210")
    assert sheet(off.propose(case, threads, "sup:70210"))["payment_days"] == 90
    assert off.payment_traded == set()


def test_signal_switches_main_sheet_to_supplier_term_at_value_parity_below_cost_parity():
    sid = "sup:70210"
    case, threads, first = p05_threads(sid, body=SIGNAL)
    prev = sheet(first)
    assert prev["payment_days"] == 90
    no_trade = sheet(agent(False).propose(case, threads, sid))
    a = agent()
    move = a.propose(case, threads, sid)
    new = sheet(move)
    assert new["payment_days"] == 30  # the supplier's own stated term, legal and shorter than ours
    assert set(new) == set(case["negotiable"]) and new["lead_time_days"] == prev["lead_time_days"]
    assert new["unit_price"] < no_trade["unit_price"] and new["unit_price"] < prev["unit_price"]
    assert total_cost(case, new) <= total_cost(case, no_trade)
    assert total_cost(case, new) <= total_cost(case, prev)
    pub = a._public_supplier(case, sid, {})
    assert pub["interest_rate"] == pytest.approx(0.30)  # skonto 2 % over 20 days = 36 %, capped
    assert supplier_value(case, new, pub) >= supplier_value(case, prev, pub) - 0.01
    assert supplier_value(case, {**new, "unit_price": new["unit_price"] + 0.01}, pub) > supplier_value(case, prev, pub)
    body = move["message"]["body"]
    assert "We can pay within 30 days; the attached unit price reflects that faster payment." in body
    assert not leaks(body)
    assert a.payment_traded == {sid}


def test_public_rate_without_skonto_is_base_rate_and_cost_parity_floor_holds():
    sid = "sup:70250"
    case, threads, first = p05_threads(sid, body=SIGNAL)
    a = agent()
    new = sheet(a.propose(case, threads, sid))
    pub = a._public_supplier(case, sid, {})
    assert pub["interest_rate"] == BASE_RATE
    assert new["payment_days"] == 30
    assert total_cost(case, new) <= total_cost(case, sheet(first))
    assert supplier_value(case, new, pub) >= supplier_value(case, sheet(first), pub) - 0.01


@pytest.mark.parametrize("sid, expect", [("sup:70250", "trait:wants_fast_payment"),
                                         ("sup:70210", "trait:offers_skonto"), ("sup:70240", None)])
def test_trait_trigger_without_signal(sid, expect):
    case, threads, first = p05_threads(sid, body=PLAIN)
    a = agent()
    assert a._payment_trade_trigger(sid, threads[sid]) == expect
    off = sheet(agent(False).propose(case, threads, sid))
    new = sheet(a.propose(case, threads, sid))
    if expect is None:
        assert new == off and a.payment_traded == set()
    else:
        assert new["payment_days"] == 30 and off["payment_days"] == 90 and new["unit_price"] < off["unit_price"]
        assert a.payment_traded == {sid}


def test_trade_happens_once_per_thread_and_schedule_continues_without_backtracking():
    sid = "sup:70210"
    case, threads, first = p05_threads(sid, body=SIGNAL)
    a = agent()
    traded = a.propose(case, threads, sid)
    c_traded = total_cost(case, sheet(traded))
    threads[sid] += [ours(traded), msg(sid, "open", "offer:70210-3", {**SUP, "unit_price": 30.5}, SIGNAL)]
    nxt = a.propose(case, threads, sid)
    t3 = sheet(nxt)
    assert t3["payment_days"] == 30  # stays on the traded package
    assert total_cost(case, t3) >= c_traded  # concedes by C, never backtracks
    assert t3["unit_price"] >= sheet(traded)["unit_price"]
    assert "reflects that faster payment" not in nxt["message"]["body"]
    # a restarted agent rebuilds "done" from our own sheets and does not trade again
    fresh = agent()
    again = fresh.propose(case, threads, sid)
    assert sheet(again) == t3 and fresh.payment_traded == {sid}


def test_traded_term_survives_free_concessions_and_package_switch():
    sid = "sup:70210"
    case, threads, _ = p05_threads(sid, body=SIGNAL)
    a = agent()
    traded = sheet(a.propose(case, threads, sid))
    # the supplier now asks for 90 days at a lower price: 90 would be a "free" concession by C
    theirs = {"unit_price": 29.0, "payment_days": 90, "lead_time_days": 35}
    n = a._free_concessions(case, {k: v for k, v in traded.items() if k != "unit_price"}, theirs, {}, None, sid)
    assert n["payment_days"] == 30
    off = agent(False)
    off.prev[sid] = {k: v for k, v in traded.items() if k != "unit_price"}
    assert off._free_concessions(case, off.prev[sid], theirs, {}, None, sid)["payment_days"] == 90
    threads[sid] += [ours({"message": {"term_sheets": [{"terms": traded}], "body": ""}}),
                     msg(sid, "open", "offer:70210-3", theirs)]
    assert sheet(a.propose(case, threads, sid))["payment_days"] == 30


def test_must_haves_and_term_options_respected():
    sid = "sup:70210"
    case, threads, _ = p05_threads(sid, body=SIGNAL)
    threads[sid][-1]["term_sheets"][0]["terms"]["payment_days"] = 21  # not a legal option
    a = agent()
    new = sheet(a.propose(case, threads, sid))
    assert new["payment_days"] == 14  # shortest legal option instead
    assert new["payment_days"] in case["term_options"]["payment_days"]
    assert must_haves_ok(case, new) and new == complete_offer(case, new)
    # a must-have that no shorter payment term can keep: no trade
    strict = {**case, "buyer": {**case["buyer"], "must_haves": [{"field": "payment_days", "op": ">=", "value": 90}]}}
    b = agent()
    assert b._payment_trade(strict, sid, threads[sid], {}, None, float("inf")) is None
    assert sheet(b.propose(strict, threads, sid))["payment_days"] == 90


def test_other_case_types_trade_too_but_only_when_payment_is_negotiable():
    case = CASES["case:P08"]  # raw_material, package type
    sid = case["suppliers"][0]
    opening = {"unit_price": 6.0, "payment_days": 30, "contract_months": 24, "index_clause": None}
    threads = {sid: [msg(sid, "open", "offer:70710-1", opening)]}
    a = agent()
    first = a.propose(case, threads, sid)
    prev = sheet(first)
    threads[sid] += [ours(first), msg(sid, "open", "offer:70710-2", {**opening, "unit_price": 5.9}, SIGNAL)]
    new = sheet(a.propose(case, threads, sid))
    if prev["payment_days"] > 30:
        assert new["payment_days"] == 30 and a.payment_traded == {sid}
        assert total_cost(case, new) <= total_cost(case, prev)
    fixed = {**CASES["case:P02"], "negotiable": ["unit_price", "index_clause"]}
    assert not a._payment_trade_on(fixed)


def test_classify_offers_skonto_from_master_data():
    def dossier(pct):
        return Dossier("sup:x", "X", "DE", "", master={"skonto_pct": pct, "skonto_days": 10, "payment_days": 30})

    assert "offers_skonto" in T.classify(dossier(2))
    assert "offers_skonto" not in T.classify(dossier(0))
    assert "offers_skonto" not in T.classify(dossier(None))
    assert "offers_skonto" not in T.classify(Dossier("sup:y", "Y", "DE", ""))
    assert "offers_skonto" in T.CASH_SHORT
    assert T.evidence(dossier(2), "offers_skonto") == []


def test_skonto_rate_is_implied_annual_rate_capped(package):
    from negotiator.dossiers import build_one

    a = agent()
    case = CASES["case:P05"]
    d = build_one(package, "sup:70210")
    assert d.master["skonto_pct"] == 2 and d.master["skonto_days"] == 10 and d.master["payment_days"] == 30
    assert a._public_supplier(case, "sup:70210", {})["interest_rate"] == pytest.approx(min(0.30, 0.02 * 360 / 20))
    assert a._public_supplier(case, "sup:70240", {})["interest_rate"] == BASE_RATE
    # the quote PDF's standard terms override master data
    assert a._public_supplier(case, "sup:70240", {"payment_days": 60})["standard"]["payment_days"] == 60


def test_fresh_h3_config_is_v3_plus_flag():
    cfg = json.loads((ROOT / "configs/fresh-h3.json").read_text())
    assert cfg == {**BASE, "supplier_payment_trade": True}
    assert PolicyConfig.load(ROOT / "configs/fresh-h3.json").supplier_payment_trade is True
