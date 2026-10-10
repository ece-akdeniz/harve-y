import json
from pathlib import Path

import pytest
from arena_kit.cost import total_cost
from test_evaluator import msg, ours

from negotiator import value_swap
from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig


@pytest.fixture(scope="module")
def p11():
    data = json.loads(Path("tests/fixtures/practice_cases.json").read_text())
    return next(c for c in data if c["case_id"] == "case:P11")


QUOTE = {"unit_price": 47.0, "ppm_commitment": 6400}
HELD = {"unit_price": 48.0, "ppm_commitment": 300, "chargeback_eur_per_complaint": 500.0}


def thread(*held):
    events = [msg("open", ("o:0", QUOTE))]
    for i, t in enumerate(held, 1):
        events += [ours({"ppm_commitment": 300, "chargeback_eur_per_complaint": 500, "unit_price": 41.0 + i}),
                   msg("open", (f"o:{i}", t))]
    return events


def test_quoted_ppm_from_standard_then_first_sheet():
    assert value_swap.quoted_ppm([], {"ppm_commitment": 900}) == 900
    assert value_swap.quoted_ppm(thread(HELD), {}) == 6400
    assert value_swap.quoted_ppm([msg("open", ("o:0", {"unit_price": 5.0}))], {}) is None


def test_holds_counts_repeated_standing(p11):
    assert value_swap.holds(p11, thread(HELD)) == 0
    assert value_swap.holds(p11, thread(HELD, HELD)) == 1
    assert value_swap.holds(p11, thread(HELD, {**HELD, "unit_price": 47.5})) == 0
    assert value_swap.holds(p11, thread({**HELD, "unit_price": 49.0}, HELD, HELD)) == 1


def test_swap_prices_chargeback_at_quoted_ppm(p11):
    terms, trace = value_swap.swap(p11, thread(HELD, HELD), HELD, {})
    # supplier value unchanged: 48.00 - 6400/1e6 * 500 = 44.80 at no chargeback
    assert terms["chargeback_eur_per_complaint"] == 0
    assert terms["ppm_commitment"] == 300
    assert terms["unit_price"] == pytest.approx(44.80)
    assert trace["quoted_ppm"] == 6400
    assert total_cost(p11, terms) < total_cost(p11, HELD)


def test_swap_split_concedes_part_way_and_takes_cheapest_ppm(p11):
    held = {**HELD, "ppm_commitment": 1500, "unit_price": 48.5}
    terms, trace = value_swap.swap(p11, thread(held, held), held, {}, last_price=44.22, split=0.5)
    assert trace["ceiling"] == pytest.approx(45.30)
    assert terms["unit_price"] == pytest.approx(44.76)
    assert terms["ppm_commitment"] == 300 and terms["chargeback_eur_per_complaint"] == 0
    full, _ = value_swap.swap(p11, thread(held, held), held, {}, last_price=44.22)
    assert full["unit_price"] == pytest.approx(45.30)


def test_swap_skips_without_lower_chargeback(p11):
    base = {**HELD, "chargeback_eur_per_complaint": 0.0}
    terms, trace = value_swap.swap(p11, thread(base, base), base, {})
    assert terms is None and trace["skip"]


def test_value_swap_policy_validation():
    assert PolicyConfig.from_dict({"version": 1}).value_swap_types == ()
    cfg = PolicyConfig.from_dict({"version": 1, "value_swap_types": ["quality"], "value_swap_holds": 2})
    assert cfg.value_swap_types == ("quality",) and cfg.value_swap_holds == 2
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "value_swap_types": ["nope"]})
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "value_swap_holds": 0})
    assert PolicyConfig.from_dict({"version": 1, "value_swap_split": 0.5}).value_swap_split == 0.5
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "value_swap_split": 0})


def _agent(**kw):
    return PackageAgent(policy=PolicyConfig(package_types=("quality",), **kw))


def test_agent_swaps_once_after_hold(p11):
    sid = p11["suppliers"][0]
    agent = _agent(value_swap_types=("quality",))
    move = agent.propose(p11, {sid: thread(HELD, HELD)}, sid)
    sheet = move["message"]["term_sheets"][0]["terms"]
    assert sheet["chargeback_eur_per_complaint"] == 0 and sheet["unit_price"] == pytest.approx(44.80)
    again = agent.propose(p11, {sid: thread(HELD, HELD, HELD)}, sid)
    assert again.get("message", {}).get("term_sheets", [{}])[0].get("terms") != sheet


def test_agent_off_by_default_and_waits_for_hold(p11):
    sid = p11["suppliers"][0]
    for agent, events in [(_agent(), thread(HELD, HELD)), (_agent(value_swap_types=("quality",)), thread(HELD))]:
        move = agent.propose(p11, {sid: events}, sid)
        terms = (move.get("message") or {}).get("term_sheets", [{}])[0].get("terms", {})
        assert terms.get("unit_price") != pytest.approx(44.80)
