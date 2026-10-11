"""Bounded model prose for an already approved, single-sheet buyer message."""

import copy
import json
import threading
import time

from .advice import AdviceCompletion, digest
from .message_prose import checked_body, mandatory_content
from .package_advisor import bounded_call, complete, failure_reason
from .skill_docs import load_skill, skill_prompt

CONTRACT = "buyer-response-v1"


def system_prompt(expected_hash):
    return skill_prompt("response", "buyer-response-writer", expected_hash)


def response_schema(_context):
    return {"type": "object", "additionalProperties": False,
            "properties": {"body": {"type": "string"}}, "required": ["body"]}


class ResponseWriter:
    """Per-supplier admission and a deterministic fallback on every failure."""

    def __init__(self, complete_fn=complete, *, timeout_s=6.0, max_calls_per_supplier=2):
        self.complete_fn = complete_fn
        self.timeout_s = timeout_s
        self.max_calls_per_supplier = max_calls_per_supplier
        self.skill = load_skill("response", "buyer-response-writer")
        self.lock = threading.Lock()
        self.calls = {}
        self.seen = set()
        self.outcomes = []
        self.input_tokens = self.output_tokens = self.usage_reported_calls = 0

    def metrics(self):
        with self.lock:
            return {"contract": CONTRACT, "skill_sha256": self.skill.sha256,
                    "calls": sum(self.calls.values()), "outcomes": list(self.outcomes),
                    "reported_input_tokens": self.input_tokens,
                    "reported_output_tokens": self.output_tokens,
                    "usage_reported_calls": self.usage_reported_calls,
                    "unknown_usage_calls": sum(self.calls.values()) - self.usage_reported_calls}

    @staticmethod
    def eligible(message, remaining_s):
        sheets = message.get("term_sheets") or []
        return (not message.get("action") and len(sheets) == 1
                and not message.get("refs") and not message.get("attachments")
                and isinstance(message.get("body"), str)
                and len(message["body"]) <= 2500 and remaining_s > 24)

    def write(self, case, events, sid, message, *, brief=None, remaining_s=0):
        trace = {"status": "skipped", "reason": "ineligible", "body_source": "deterministic"}
        if not self.eligible(message, remaining_s):
            return None, trace
        terms = message["term_sheets"][0].get("terms") or {}
        if not isinstance(terms, dict) or not terms:
            return None, trace
        latest = next(((i, e) for i, e in reversed(list(enumerate(events)))
                       if e.get("from") != "buyer"), None)
        if latest is None or len(latest[1].get("body") or "") > 3000:
            return None, trace
        index, supplier = latest
        update = digest([case.get("case_id"), sid, index, supplier.get("body"),
                         supplier.get("term_sheets"), terms, message.get("body")])
        context = {"response_contract": CONTRACT, "skill_sha256": self.skill.sha256,
                   "case_type": case.get("type"), "supplier_id": sid,
                   "latest_supplier_message": {"message_index": index,
                                               "body": supplier.get("body") or ""},
                   "approved_terms": terms, "prepared_body": message["body"],
                   "message_contract": {"approved_terms": terms,
                                        "mandatory_content": mandatory_content(message["body"]),
                                        "permitted_acknowledgements": ["Thank you for your response.",
                                                                       "Thank you for clarifying your position."],
                                        "allowed_commitments": [], "validated_claim_refs": []},
                   "supplier_brief": (brief if isinstance(brief, dict)
                                      and brief.get("supplier_id") == sid else None)}
        if len(json.dumps(context, ensure_ascii=False).encode()) > 12000:
            return None, {**trace, "reason": "context_bound"}
        with self.lock:
            if update in self.seen or self.calls.get(sid, 0) >= self.max_calls_per_supplier:
                return None, {**trace, "reason": "admission_closed"}
            if budget := getattr(self, "model_budget", None):
                allowed, reason, _ = budget.reserve(CONTRACT, sid, update, digest(context),
                                                    min(self.timeout_s, remaining_s - 20),
                                                    remaining_s=remaining_s, optional=True)
                if not allowed:
                    return None, {**trace, "reason": reason}
            self.seen.add(update)
            self.calls[sid] = self.calls.get(sid, 0) + 1
        started = time.monotonic()
        trace = {"status": "fallback", "reason": None, "body_source": "deterministic_fallback",
                 "request_digest": digest(context), "skill_sha256": self.skill.sha256}
        try:
            answer = bounded_call(self.complete_fn, copy.deepcopy(context),
                                  min(self.timeout_s, remaining_s - 20))
            if budget:
                budget.artifact(CONTRACT, trace["request_digest"], context,
                                response=answer.response if isinstance(answer, AdviceCompletion) else answer)
            if isinstance(answer, AdviceCompletion):
                usage = answer.usage
                if all(type(usage.get(k)) is int and usage[k] >= 0
                       for k in ("prompt_tokens", "completion_tokens")):
                    with self.lock:
                        self.input_tokens += usage["prompt_tokens"]
                        self.output_tokens += usage["completion_tokens"]
                        self.usage_reported_calls += 1
                answer = answer.response
            if not isinstance(answer, dict) or set(answer) != {"body"}:
                trace["reason"] = "response_fields"
                return None, trace
            check = {}
            body = checked_body(answer["body"], terms, prepared_body=message["body"],
                                reason_out=check)
            if not body:
                trace["reason"] = "invalid_prose"
                trace["prose_check"] = check.get("check")
                return None, trace
            trace.update(status="ok", reason="model_body", body_source="model")
            return body, trace
        except Exception as exc:
            if budget:
                budget.artifact(CONTRACT, trace["request_digest"], context, error=exc)
            trace["reason"] = failure_reason(exc)
            return None, trace
        finally:
            trace["elapsed_s"] = time.monotonic() - started
            with self.lock:
                self.outcomes.append(dict(trace))
