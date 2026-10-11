"""Bounded stage artifacts for the existing Lab JSON record; no rejected raw model content."""


def decision_evidence(trace):
    trace.verify()
    decision = trace.decision
    selected_fallback = bool(
        decision
        and (decision.fallback_code is not None or decision.selector_id.endswith(":fallback"))
    )
    fallback_calls = [
        {"task": call.request.task, "reason": call.fallback_reason}
        for call in trace.model_calls
        if call.fallback_used
    ]
    proposal_admitted = any(call.request.task == "propose" and call.consumer_admitted for call in trace.model_calls)
    fallback_action = (
        selected_fallback
        or any(call["task"] == "propose" for call in fallback_calls)
        or bool(fallback_calls) and not proposal_admitted
    )
    return {
        "trace_hash": trace.trace_hash,
        "input_hash": trace.input_hash,
        "state_version": trace.snapshot.state_version,
        "assessment_json": trace.assessment.model_dump_json() if trace.assessment else None,
        "intents_json": trace.intents.model_dump_json() if trace.intents else None,
        "evaluations_json": [item.model_dump_json() for item in trace.evaluations.items] if trace.evaluations else [],
        "decision_json": trace.decision.model_dump_json() if trace.decision else None,
        "validation_json": trace.validation.model_dump_json() if trace.validation else None,
        "action_origin": "fallback" if fallback_action else "model_or_deterministic",
        "fallback_action": fallback_action,
        "fallback_reasons": fallback_calls,
        "issues": [issue.model_dump(mode="json") for issue in trace.issues],
        "stages": [stage.model_dump(mode="json") for stage in trace.stages],
        "model_usage": [
            {
                "task": call.request.task,
                "provider": call.request.provider_id,
                "model": call.request.model_id,
                "usage": call.usage.model_dump(mode="json"),
                "elapsed_s": str(call.elapsed_s),
                "consumer_admitted": call.consumer_admitted,
                "fallback_used": call.fallback_used,
            }
            for call in trace.model_calls
        ],
    }
