"""`tenor_extend_types` (opt-in, off in score-push-v6): from our second offer on, extend contract_months to
the longest cost-neutral option on capacity cases (P10); the first offer and other case types are unchanged.
Hosted P10 `dedfccbdc54b873c`: 31.80 / 36 m final = the 24 m score (.6551), so the flag is kept off."""

import json
from pathlib import Path

from test_evaluator import msg

from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig

V5 = "configs/score-push-v5.json"
V6 = "configs/score-push-v6.json"
TE = "configs/p10-tenor-extend.json"


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def _p10_thread():
    c = case("case:P10")
    sid = c["suppliers"][0]
    opening = msg("open", ("offer:70410-0", {"unit_price": 32.2, "lead_time_days": 54, "volume_per_year": 19890,
                                            "contract_months": 12}))
    return c, sid, opening


def test_v6_differs_from_v5_only_in_the_posterior():
    v5 = json.loads(Path(V5).read_text())
    v6 = json.loads(Path(V6).read_text())
    assert {k: v6[k] for k in v6 if k != "cost_target_posterior"} == {
        k: v5[k] for k in v5 if k != "cost_target_posterior"}
    assert v6["cost_target_posterior"] == 0.1 and v5["cost_target_posterior"] == 0.15
    assert PolicyConfig.load(V6).tenor_extend_types == ()
    te = json.loads(Path(TE).read_text())
    assert {k: te[k] for k in te if k != "tenor_extend_types"} == v6
    assert PolicyConfig.load(TE).tenor_extend_types == ("capacity",)


def test_p10_first_offer_unchanged_second_offer_extends_to_36_months():
    c, sid, opening = _p10_thread()
    a5 = PackageAgent(policy=PolicyConfig.load(V5), claims=False)
    a6 = PackageAgent(policy=PolicyConfig.load(TE), claims=False)
    first5 = a5.propose(c, {sid: [opening]}, sid)["message"]["term_sheets"][0]["terms"]
    first6 = a6.propose(c, {sid: [opening]}, sid)["message"]["term_sheets"][0]["terms"]
    assert first6 == first5 and first6["contract_months"] == 24
    ours = {"from": "buyer", "term_sheets": [{"terms": {**first6, "lead_time_days": 56, "unit_price": 27.62}}]}
    reply = msg("open", ("offer:70410-1", {"unit_price": 32.0, "lead_time_days": 56, "volume_per_year": 23400,
                                           "contract_months": 24}))
    events = {sid: [opening, ours, reply]}
    second5 = a5.propose(c, events, sid)["message"]["term_sheets"][0]["terms"]
    second6 = a6.propose(c, events, sid)["message"]["term_sheets"][0]["terms"]
    assert second5["contract_months"] == 24
    assert second6["contract_months"] == 36
    assert second6["volume_per_year"] == 23400 and second6["lead_time_days"] == second5["lead_time_days"]
    assert second6["unit_price"] == second5["unit_price"]  # months are cost-neutral: same price step
    # the extension is not given back for free and never repeated as a further switch
    final = msg("final_offer", ("offer:70410-2", {"unit_price": 31.8, "lead_time_days": 56,
                                                  "volume_per_year": 23400, "contract_months": 24}))
    ours2 = {"from": "buyer", "term_sheets": [{"terms": {**second6, "unit_price": 29.07}}]}
    move = a6.propose(c, {sid: [opening, ours, reply, ours2, final]}, sid)
    assert move.get("close") or move["message"].get("action", {}).get("type") == "accept"


def test_tenor_extend_leaves_other_types_alone():
    c = case("case:P07")
    sid = c["suppliers"][0]
    events = {sid: [msg("open", ("offer:0", {"unit_price": 5.74, "payment_days": 30, "contract_months": 12}))]}
    a5 = PackageAgent(policy=PolicyConfig.load(V5), claims=False)
    a6 = PackageAgent(policy=PolicyConfig.load(TE), claims=False)
    first = a5.propose(c, events, sid)
    assert a6.propose(c, events, sid) == first
    ours = {"from": "buyer", **first["message"]}
    reply = msg("open", ("offer:1", {"unit_price": 5.6, "payment_days": 90, "contract_months": 24}))
    assert a6.propose(c, {sid: [events[sid][0], ours, reply]}, sid) == a5.propose(
        c, {sid: [events[sid][0], ours, reply]}, sid)
