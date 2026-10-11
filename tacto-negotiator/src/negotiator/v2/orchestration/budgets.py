"""Decision-scoped admission and cancellation; unknown usage consumes its reservation."""

import asyncio
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from pydantic import TypeAdapter, ValidationError, model_serializer

from ..core import models as m
from ..core.diagnostics import AdmissionDiagnostic
from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash


class ModelCallTrace(m.FrozenModel):
    request: m.ModelRequest
    request_hash: str
    result_kind: Literal[
        "success", "refused", "invalid", "timeout", "capacity_unavailable", "transport_failure", "cancelled",
    ]
    usage: m.ModelUsage
    charged_tokens: int
    elapsed_s: Decimal
    response_hash: str | None = None
    permitted_raw_response: str | None = None
    cause: str | None = None
    consumer_admitted: bool | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    diagnostic: AdmissionDiagnostic | None = None

    @model_serializer(mode="wrap")
    def preserve_historic_projection(self, handler):
        result = handler(self)
        additions = {"consumer_admitted", "fallback_used", "fallback_reason", "diagnostic"}
        # Old persisted traces have a hash over the old projection. Preserve those bytes'
        # semantic projection on export; absence means unknown admission, never success.
        if not additions & self.model_fields_set:
            for key in additions:
                result.pop(key, None)
        return result


def failure(request, kind, detail, elapsed=Decimal("0")):
    cls, code = {
        "invalid": (m.ModelInvalid, "model_invalid"),
        "refused": (m.ModelRefused, "model_invalid"),
        "timeout": (m.ModelTimeout, "model_timeout"),
        "capacity_unavailable": (m.ModelCapacityUnavailable, "unsupported_capability"),
        "transport_failure": (m.ModelTransportFailure, "recovery_required"),
    }[kind]
    return cls(kind=kind, call_id=request.call_id, model_id=request.model_id, elapsed_s=elapsed,
               issues=(m.Issue(code=code, severity="error", component="model", refs=(), detail=detail),))


class DecisionModelLedger:
    # Historical reviewed caps, now owned in one place and clipped by the live
    # decision remainder. A later measured policy can replace these values once.
    stage_caps_s = {"interpret": 8.0, "propose": 4.0, "select": 4.0}

    def __init__(self, *, budget: m.DecisionBudget, clock, token_limit: int):
        if type(token_limit) is not int or token_limit <= 0:
            raise ValueError("explicit positive decision token limit required")
        self.budget = m.DecisionBudget.model_validate_json(budget.model_dump_json())
        self.clock = clock
        self.token_limit = token_limit
        self.started = clock.monotonic()
        self.calls = 0
        self.tokens = 0
        self.model_seconds = 0.0
        self.traces: list[ModelCallTrace] = []
        self.seen = set()
        self.busy = False
        self.disabled_reason: str | None = None

    def remaining(self):
        reserves = float(self.budget.fallback_reserve_s + self.budget.submission_reserve_s)
        return min(
            (self.budget.deadline_at - self.clock.utcnow()).total_seconds() - reserves,
            float(self.budget.compute_limit_s) - (self.clock.monotonic() - self.started) - reserves,
            float(self.budget.model_time_limit_s) - self.model_seconds,
        )

    def model_budget(self, *, task, max_tokens, time_limit_s):
        remaining = min(self.remaining(), float(time_limit_s), self.stage_caps_s.get(task, float(time_limit_s)))
        if remaining <= 0:
            raise ContractViolation("model_timeout: no model time remains after reserves")
        return m.ModelBudget(deadline_at=self.clock.utcnow() + timedelta(seconds=remaining),
                             time_limit_s=Decimal(str(remaining)), max_tokens=max_tokens, max_calls=1, retry_limit=0)

    def disable(self, reason, transport=None):
        if self.disabled_reason is None:
            self.disabled_reason = reason
        stopper = getattr(transport, "stop_model_calls", None)
        if callable(stopper):
            stopper(reason)

    async def invoke(self, request, budget, transport):
        request = m.ModelRequest.model_validate_json(request.model_dump_json())
        budget = m.ModelBudget.model_validate_json(budget.model_dump_json())
        timeout = min(self.remaining(), float(budget.time_limit_s),
                      (budget.deadline_at - self.clock.utcnow()).total_seconds())
        if getattr(transport, "stopped", False) and self.disabled_reason is None:
            self.disabled_reason = "transport_unavailable"
        if (self.disabled_reason is not None or self.busy or request.call_id in self.seen
                or self.calls >= self.budget.model_call_limit
                or self.tokens + budget.max_tokens > self.token_limit):
            reason = self.disabled_reason or "decision call/token capacity exhausted"
            result = failure(request, "capacity_unavailable", reason)
            self._record(request, result, 0, 0.0)
            return result
        if timeout <= 0:
            result = failure(request, "timeout", "decision reserves/deadline exhausted")
            self._record(request, result, 0, 0.0)
            return result
        # Reserve before any await, including queue time; never retry a call identity.
        self.busy = True
        self.seen.add(request.call_id)
        self.calls += 1
        self.tokens += budget.max_tokens
        started = self.clock.monotonic()
        loop_started = asyncio.get_running_loop().time()
        cancelled = False
        try:
            # Do not wait indefinitely for a cancellation-resistant child.
            # A detached late child is observed and never admitted.
            task = asyncio.create_task(transport(request, budget))
            done, _ = await asyncio.wait({task}, timeout=timeout)
            if not done:
                task.cancel()
                task.add_done_callback(_consume)
                self.disable("model_timeout", transport)
                result = failure(request, "timeout", "transport exceeded model deadline")
            else:
                result = TypeAdapter(m.ModelResult).validate_json(task.result().model_dump_json())
                elapsed = max(self.clock.monotonic() - started, asyncio.get_running_loop().time() - loop_started)
                if (elapsed >= timeout or float(result.elapsed_s) >= timeout
                        or self.remaining() <= 0 or self.clock.utcnow() >= budget.deadline_at):
                    result = failure(request, "timeout", "late model result rejected")
                elif result.call_id != request.call_id or result.model_id != request.model_id:
                    result = failure(request, "invalid", "call/model identity mismatch")
                elif result.kind == "success" and any(i.severity == "error" for i in result.issues):
                    result = failure(request, "invalid", "successful transport contains error issues")
                if result.kind in {"timeout", "transport_failure"}:
                    self.disable(result.kind, transport)
        except asyncio.CancelledError:
            cancelled = True
            # Revoke admission synchronously. The caller may fall back, but no stage in
            # this decision can reserve another request while cleanup is still running.
            self.disable("caller_cancelled", transport)
            task.cancel()
            task.add_done_callback(_consume)
            raise
        except (ValidationError, ValueError, TypeError, AttributeError):
            result = failure(request, "invalid", "malformed transport envelope")
        except TimeoutError:
            result = failure(request, "timeout", "transport timeout")
            self.disable("model_timeout", transport)
        except Exception:
            result = failure(request, "transport_failure", "transport failed; details withheld")
            self.disable("transport_failure", transport)
        finally:
            elapsed = max(0.0, self.clock.monotonic() - started,
                          asyncio.get_running_loop().time() - loop_started)
            self.model_seconds += elapsed
            self.busy = False
            if cancelled:
                self.traces.append(ModelCallTrace(
                    request=request, request_hash=semantic_hash(request), result_kind="cancelled", usage=m.ModelUsage(),
                    charged_tokens=budget.max_tokens, elapsed_s=Decimal(str(elapsed)), cause="cancelled",
                ))
        charged = budget.max_tokens
        if result.kind == "success":
            usage = result.usage
            if usage.input_tokens is not None and usage.output_tokens is not None:
                actual = usage.input_tokens + usage.output_tokens
                if actual <= budget.max_tokens:
                    charged = actual
                    self.tokens -= budget.max_tokens - actual
                else:
                    # Report overrun truthfully and block subsequent admissions.
                    self.tokens += actual - budget.max_tokens
                    charged = actual
                    self._record(request, result, charged, elapsed)
                    return failure(request, "invalid", "reported usage exceeds reservation")
        self._record(request, result, charged, elapsed)
        return result

    def _record(self, request, result, charged, elapsed):
        self.traces.append(ModelCallTrace(
            request=request, request_hash=semantic_hash(request), result_kind=result.kind,
            usage=result.usage if result.kind == "success" else m.ModelUsage(), charged_tokens=charged,
            elapsed_s=Decimal(str(elapsed)), response_hash=result.response_hash if result.kind == "success" else None,
            cause=result.issues[0].code if result.issues else None,
            diagnostic=(AdmissionDiagnostic(stage="execution", category="execution_failure", error_type="execution")
                        if result.kind != "success" else None),
        ))

    def reject_raw(self, call_id, code, diagnostic=None):
        for index, trace in enumerate(self.traces):
            if trace.request.call_id == call_id:
                self.traces[index] = trace.model_copy(update={"cause": code, "permitted_raw_response": None,
                    "consumer_admitted": False, "fallback_used": True, "fallback_reason": code,
                    "diagnostic": diagnostic or AdmissionDiagnostic(stage="consumer", category="unattributable",
                                                                    error_type="unknown")})
                return

    def admit_raw(self, call_id, raw):
        for index, trace in enumerate(self.traces):
            if trace.request.call_id == call_id and trace.result_kind == "success":
                self.traces[index] = trace.model_copy(update={"permitted_raw_response": raw, "consumer_admitted": True})
                return


def _consume(task):
    if not task.cancelled():
        task.exception()
