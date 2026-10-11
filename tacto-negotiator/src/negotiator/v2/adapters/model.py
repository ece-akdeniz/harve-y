"""Provider-independent async transport seam. No credentials, retries or import calls."""

from contextlib import contextmanager
from contextvars import ContextVar

from ..core import models as m
from ..core.errors import ContractViolation

_scope = ContextVar("v2_gateway_decision_ledger", default=None)


class AsyncModelGateway:
    def __init__(self, *, transport, ledger=None):
        self.transport = transport
        self.ledger = ledger

    async def complete(self, request: m.ModelRequest, budget: m.ModelBudget) -> m.ModelResult:
        ledger = _scope.get() or self.ledger
        if ledger is None:
            raise ContractViolation("unsupported_capability: gateway requires a decision-scoped ledger")
        return await ledger.invoke(request, budget, self.transport)

    def model_budget(self, *, task, max_tokens, time_limit_s):
        ledger = _scope.get() or self.ledger
        if ledger is None:
            raise ContractViolation("unsupported_capability: gateway requires a decision-scoped ledger")
        return ledger.model_budget(task=task, max_tokens=max_tokens, time_limit_s=time_limit_s)

    @contextmanager
    def decision_scope(self, ledger):
        token = _scope.set(ledger)
        try:
            yield
        finally:
            _scope.reset(token)

    def admit_raw(self, call_id, raw):
        ledger = _scope.get() or self.ledger
        if ledger is not None:
            ledger.admit_raw(call_id, raw)

    def reject_raw(self, call_id, code, diagnostic=None):
        ledger = _scope.get() or self.ledger
        if ledger is not None:
            ledger.reject_raw(call_id, code, diagnostic)
