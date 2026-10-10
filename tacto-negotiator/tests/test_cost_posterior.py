"""In-session supplier-cost posterior (opt-in `cost_target_posterior`), P02-shaped public fixture."""
import json

import pytest
from test_cost_target import CONFIG, EST, SID, STD, buyer, case, sup_msg, t

from negotiator import cost_target as ct
from negotiator.agent import configured_agent
from negotiator.policy import PolicyConfig


def agent(s_max=0.15):
    a = configured_agent({**json.loads(CONFIG.read_text()), "cost_target_posterior": s_max}, estimates={}, meso=False)
    a._target_cache[("case:P02", SID)] = EST
    return a


def price(move):
    return move["message"]["term_sheets"][0]["terms"]["unit_price"]


def test_flag_validates_and_defaults_off():
    assert PolicyConfig.from_dict({"version": 1}).cost_target_posterior == 0.0
    for bad in (True, -0.1, 2, "0.1"):
        with pytest.raises(ValueError):
            PolicyConfig.from_dict({"version": 1, "cost_target_posterior": bad})


def test_refusals_raise_the_posterior_cost():
    c = case()
    prior = ct.scenarios(EST)
    post = ct.posterior(c, STD, EST, [(t(360.0), False)], 0.15, prior)
    mean = sum(s["_w"] * s["full_cost"] for s in post) / sum(s["_w"] for s in post)
    assert mean > 374.95
    acc = ct.posterior(c, STD, EST, [(t(360.0), True)], 0.15, prior)
    assert sum(s["_w"] * s["full_cost"] for s in acc) / sum(s["_w"] for s in acc) < 374.95


def test_opening_below_prior_target_and_offers_rise_only_after_refusals():
    c, a = case(), agent()
    first = a.decide(c, {SID: [sup_msg([(0, t(370.96, 30, None))])]})
    p0 = price(first)
    assert 360 < p0 < 366.23  # self-consistent price sits below the prior optimum
    ev = [sup_msg([(0, t(370.96, 30, None))]), buyer(t(p0)), sup_msg([(1, t(372.0))])]
    p1 = price(a.decide(c, {SID: ev}))
    assert p0 < p1 <= 366.23  # a refusal lifts us, but never above the prior-target ceiling


def test_accepts_supplier_sheet_at_or_below_posterior_price():
    c, a = case(), agent()
    ev = [sup_msg([(0, t(370.96, 30, None))]), buyer(t(363.0)), sup_msg([(1, t(363.0))], status="agreed")]
    move = a.decide(c, {SID: ev})
    assert move["message"]["action"]["type"] == "accept"


def test_off_keeps_prior_opening():
    c, a = case(), agent(0.0)
    assert price(a.decide(c, {SID: [sup_msg([(0, t(370.96, 30, None))])]})) == 366.23
