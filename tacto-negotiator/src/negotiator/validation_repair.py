"""One bounded model repair of a rejected strategy or final-offer suggestion.

The repair model can select only a code-generated package. The originating adviser
revalidates its answer; this module never authorizes a negotiation move itself.
"""

import copy
import os
import time

from .advice import AdviceCompletion, digest
from .package_advisor import bounded_call, failure_reason
from .skill_docs import load_skill, skill_prompt

CONTRACT = "validation-repair-v1"
TIMEOUT_S = 6.0


def system_prompt(expected_hash):
    return skill_prompt("validation", "validation-repair", expected_hash)


def response_schema(context):
    source = context["source_context"]
    ids = ["keep", *source["approved_packages"]]
    properties = {
        "selected_id": {"type": "string", "enum": ids},
        "message_index": {"type": "integer"},
        "quote": {"type": "string"},
    }
    if context["original_contract"] == "negotiation-strategy-v1":
        properties["selected_id"]["enum"].extend(source["registered_questions"])
        properties["kind"] = {"type": "string", "enum":
                              ["none", "objection", "conditional_trade", "question", "stated_terms"]}
    if source.get("write_response") is True:
        properties["body"] = {"type": "string"}
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def repair(complete_fn, source_context, rejected_response, reason, *, supplier_id,
           update_hash, remaining_s, budget=None, clock=time.monotonic):
    """Return one model answer and a trace, or None when repair cannot safely run."""
    trace = {"status": "skipped", "reason": "repair_unavailable", "contract": CONTRACT}
    if complete_fn is None:
        return None, trace
    skill = load_skill("validation", "validation-repair")
    context = {"response_contract": CONTRACT, "skill_sha256": skill.sha256,
               "original_contract": source_context["response_contract"],
               "source_context": source_context, "rejected_response": rejected_response,
               "rejection_reason": reason}
    allowance = min(TIMEOUT_S, remaining_s - 22.0)
    if allowance < 2.0:
        return None, {**trace, "reason": "deadline_reserve"}
    request_digest = digest(context)
    if budget is not None:
        allowed, why, _ = budget.reserve(CONTRACT, supplier_id, update_hash, request_digest,
                                         allowance, remaining_s=remaining_s)
        if not allowed:
            return None, {**trace, "reason": why}
    started = clock()
    trace.update(status="fallback", reason=None, request_digest=request_digest,
                 skill_sha256=skill.sha256,
                 model=os.environ.get("VALIDATION_LLM_MODEL") or os.environ.get("LLM_MODEL"),
                 route="independent" if os.environ.get("VALIDATION_LLM_BASE_URL") else "shared")
    try:
        response = bounded_call(complete_fn, copy.deepcopy(context), allowance)
        if budget is not None:
            budget.artifact(CONTRACT, request_digest, context,
                            response=response.response if isinstance(response, AdviceCompletion) else response)
        if clock() - started >= allowance:
            raise TimeoutError("late validation repair")
        usage = response.usage if isinstance(response, AdviceCompletion) else {}
        answer = response.response if isinstance(response, AdviceCompletion) else response
        tokens = ({key: usage[key] for key in ("prompt_tokens", "completion_tokens")
                   if type(usage.get(key)) is int and usage[key] >= 0}
                  if isinstance(usage, dict) else {})
        trace.update(status="ok", reason="reviewed", elapsed_s=clock() - started,
                     usage=tokens)
        return answer, trace
    except Exception as exc:
        if budget is not None:
            budget.artifact(CONTRACT, request_digest, context, error=exc)
        trace.update(reason=failure_reason(exc), elapsed_s=clock() - started)
        return None, trace
