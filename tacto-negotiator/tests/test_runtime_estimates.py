import pytest
from arena_kit.cost import total_cost
from test_runner import ScaledClock, SimArena

from negotiator.agent import PackageAgent
from negotiator.evaluator import close_decision
from negotiator.runner import CaseRunner
from negotiator.state import Journal


@pytest.mark.parametrize("override", [None, {}, {"explicit": {"full_cost": 2}}])
async def test_async_close_uses_same_estimates_as_agent(tmp_path, override):
    clock = ScaledClock()
    arena = SimArena(clock)
    estimates = {"sentinel": {"full_cost": 1}}
    received = []

    def close(case, threads, estimates=None, reason=""):
        received.append(estimates)
        return close_decision(case, threads, estimates, reason)

    agent = PackageAgent(estimates=estimates)
    result = await CaseRunner(arena, "case:S01", agent, Journal(tmp_path / "j.jsonl"),
                              clock=clock, close_fn=close, estimates=override).run()
    assert result["deal"]
    assert received and all(value == (estimates if override is None else override) for value in received)


def test_relationship_cost_can_make_cost_nonmonotonic():
    # Document why inverse-price interpolation must not assume monotonic C when
    # supplier estimates are switched on. This is a property of the arena formula.
    from test_evaluator import ESTIMATE, STABILISE

    supplier = ESTIMATE["sup:F"]
    assert total_cost(STABILISE, {"unit_price": 20}, supplier=supplier) > total_cost(
        STABILISE, {"unit_price": 40}, supplier=supplier
    )
