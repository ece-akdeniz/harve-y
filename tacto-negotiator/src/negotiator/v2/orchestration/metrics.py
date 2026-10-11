"""Safe descriptive operational/economic metrics; human judgments remain unreviewed."""


def decision_metrics(trace):
    selected = next((i for i in trace.evaluations.items if trace.decision
                     and i.candidate.candidate_id == trace.decision.candidate_id), None) if trace.evaluations else None
    offers = ([i for i in trace.evaluations.items if i.disposition == "approved" and i.economic]
              if trace.evaluations else [])
    minimum = min((r.nominal_cost.amount for i in offers for r in i.economic), default=None)
    cost = selected.economic[0].nominal_cost.amount if selected and selected.economic else None
    baseline_id = min(offers, key=lambda i: (min(r.nominal_cost.amount for r in i.economic),
                                           i.candidate.candidate_id)).candidate.candidate_id if offers else None
    calls = trace.model_calls
    selections = [c for c in calls if c.request.task == "select"]
    proposals = [c for c in calls if c.request.task == "propose"]
    return {
        "trace_hash": trace.trace_hash,
        "state_version": trace.snapshot.state_version,
        "transport_success": sum(c.result_kind == "success" for c in calls),
        "calls": len(calls),
        "interpretation_admitted": any(
            c.request.task == "interpret" and c.consumer_admitted is True for c in calls
        ),
        "proposal_admitted": any(c.consumer_admitted is True for c in proposals) if proposals else None,
        "selection_admitted": (any(c.consumer_admitted is True for c in selections)
                               if selections and all(c.consumer_admitted is not None for c in selections) else None),
        "fallbacks": sum(c.fallback_used for c in calls),
        "final_action_valid": trace.validation is not None and trace.validation.kind == "valid",
        "latency_s": sum(float(c.elapsed_s) for c in calls),
        "charged_usage": sum(c.charged_tokens for c in calls),
        "usage_known": all(c.usage.input_tokens is not None and c.usage.output_tokens is not None for c in calls),
        "inference_expenditure": 0 if all(c.request.provider_id == "local-fixture" for c in calls) else None,
        "official_cost": str(cost) if cost is not None else None,
        "cost_delta": str(cost - minimum) if cost is not None and minimum is not None else None,
        "different_from_cost_minimum": (selected.candidate.candidate_id != baseline_id
                                        if selected and baseline_id else None),
        "semantic_review": "unreviewed",
        "strategic_justification_review": "unreviewed",
        "diagnostics": [c.diagnostic.model_dump(mode="json") if c.diagnostic else
                        {"stage": "consumer", "category": "unattributable", "error_type": "unknown", "field": "$"}
                        for c in calls if c.diagnostic or c.consumer_admitted is None],
    }
