"""Shared bounded model client for the opt-in `model_*` policy features.

The model only interprets text and chooses among code-priced options. Every call has a hard
timeout (default 8 s), returns one strict-JSON object, records its latency and raises on any
failure so that the caller falls back to today's deterministic path. A per-decision budget
skips calls once the decision has already spent its model time or the thread/wave window is low.
"""

import json
import os
import threading
import time

import httpx

from .package_advisor import bounded_call

CALL_TIMEOUT_S = 8.0
DECISION_BUDGET_S = 8.0  # model time per buyer decision; the 60 s message limit must never be at risk
MIN_WINDOW_S = 25.0  # skip model calls when the thread's reply window is shorter than this
MAX_TRACE = 500


class LlmUnavailable(RuntimeError):
    pass


def configured() -> bool:
    return all(os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


def _request(context, timeout_s):
    system, payload, schema, name = context
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key, model = os.environ.get("LLM_API_KEY"), os.environ.get("LLM_MODEL")
    if not base or not key or not model:
        raise LlmUnavailable("LLM endpoint, key and model must be configured")
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        "max_completion_tokens": 600,
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
    }
    if effort := os.environ.get("LLM_EFFORT"):
        body["reasoning_effort"] = effort
    with httpx.Client(timeout=httpx.Timeout(timeout_s, connect=min(2.0, timeout_s))) as client:
        response = client.post(base + "/chat/completions", json=body, headers={"Authorization": "Bearer " + key})
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        if message.get("refusal"):
            raise ValueError("model refused")
        out = json.loads(message["content"])
        if not isinstance(out, dict):
            raise ValueError("model response must be an object")
        usage = data.get("usage") or {}
        out["_usage"] = {"input": usage.get("prompt_tokens"), "output": usage.get("completion_tokens")}
        return out


class LlmClient:
    """`call` returns the parsed object or raises; latency and outcome are recorded per call kind."""

    def __init__(self, complete_fn=None, timeout_s=CALL_TIMEOUT_S):
        self.complete_fn = complete_fn or _request
        self.timeout_s = max(0.01, min(float(timeout_s), CALL_TIMEOUT_S))
        self._lock = threading.Lock()
        self.calls = []  # [{kind, elapsed_s, ok, error_type}]
        self.tokens = {"input": 0, "output": 0}

    def call(self, kind, system, payload, schema, name="response", timeout_s=None):
        started = time.monotonic()
        ok, error = False, None
        try:
            out = bounded_call(self.complete_fn, (system, payload, schema, name),
                               min(self.timeout_s, timeout_s or self.timeout_s))
            usage = out.pop("_usage", None) if isinstance(out, dict) else None
            with self._lock:
                for k in ("input", "output"):
                    if isinstance((usage or {}).get(k), int):
                        self.tokens[k] += usage[k]
            ok = True
            return out
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            with self._lock:
                if len(self.calls) < MAX_TRACE:
                    self.calls.append({"kind": kind, "elapsed_s": round(time.monotonic() - started, 3),
                                       "ok": ok, "error_type": error})

    def metrics(self):
        with self._lock:
            calls = list(self.calls)
        latency = [c["elapsed_s"] for c in calls]
        return {"calls": len(calls), "fallbacks": sum(not c["ok"] for c in calls), "latency_s": latency,
                "max_latency_s": max(latency) if latency else 0.0, "by_kind": _by_kind(calls),
                "input_tokens": self.tokens["input"], "output_tokens": self.tokens["output"]}


def _by_kind(calls):
    out = {}
    for c in calls:
        k = out.setdefault(c["kind"], {"calls": 0, "fallbacks": 0, "max_latency_s": 0.0})
        k["calls"] += 1
        k["fallbacks"] += not c["ok"]
        k["max_latency_s"] = max(k["max_latency_s"], c["elapsed_s"])
    return out


class TurnBudget:
    """Model time available for one buyer decision; `allow(kind)` is checked before every call."""

    def __init__(self, budget_s=DECISION_BUDGET_S, clock=time.monotonic):
        self.budget_s, self.clock = budget_s, clock
        self.started = clock()
        self.spent = 0.0
        self.skipped = []

    def remaining(self):
        return self.budget_s - self.spent

    def allow(self, kind, *, window_s=None, need_s=1.0):
        """False (and recorded) when the decision budget or the thread/wave window is too short."""
        if self.remaining() < need_s:
            self.skipped.append({"kind": kind, "reason": "decision budget spent"})
            return False
        if window_s is not None and window_s < MIN_WINDOW_S:
            self.skipped.append({"kind": kind, "reason": f"window {window_s:.0f}s"})
            return False
        return True

    def timeout_for(self, default=CALL_TIMEOUT_S):
        return max(0.5, min(default, self.remaining()))

    def charge(self, elapsed_s):
        self.spent += max(0.0, elapsed_s)

    def timed(self, fn, *args, **kwargs):
        started = self.clock()
        try:
            return fn(*args, **kwargs)
        finally:
            self.charge(self.clock() - started)
