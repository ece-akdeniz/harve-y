import asyncio

import pytest

from tests.v2.fakes import FakeClock
from tests.v2.support import inputs, require


@pytest.mark.asyncio
async def test_hung_model_is_cancelled_and_falls_back_within_total_budget(request, p10):
    module = require(request, "intelligence.interpreter")
    p10["config"]["interpreter_limit_s"] = 0.02
    data = inputs(request, p10)

    class HungModel:
        cancelled = False

        async def complete(self, request, budget):
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True

    gateway = HungModel()
    interpreter = module.GroundedInterpreter(model=gateway, clock=FakeClock())
    result = await asyncio.wait_for(
        interpreter.interpret(data.context, data.conversation, None, data.budget), timeout=0.25,
    )
    assert result.status == "fallback"
    assert gateway.cancelled


@pytest.mark.asyncio
async def test_late_success_after_deadline_is_not_applied(request, p10):
    module = require(request, "intelligence.interpreter")
    data = inputs(request, p10)
    clock = FakeClock()

    class LateModel:
        async def complete(self, request, budget):
            clock.advance(60)
            return data.model_result

    interpreter = module.GroundedInterpreter(model=LateModel(), clock=clock)
    result = await interpreter.interpret(data.context, data.conversation, None, data.budget)
    assert result.status == "fallback"
    assert result.snapshot == data.context.snapshot
