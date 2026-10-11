"""Small traceable boundary between an approved decision and its transport payload."""

from .advice import digest
from .message_prose import mandatory_content


def decision_record(agent, case, threads, decision, *, runner):
    pending = getattr(agent, "_advice_pending", None) or {}
    message = decision["message"]
    budget = getattr(agent, "model_budget", None)
    return {"schema": "buyer-decision-v1", "case_id": case.get("case_id"),
            "supplier_id": decision["supplier_id"], "runner": runner,
            "state_digest": digest([case, threads]),
            "baseline_move_digest": pending.get("baseline_payload") or digest(decision),
            "selected_action": (message.get("action") or {}).get("type", "offer"),
            "selected_id": pending.get("selected_id"),
            "evaluated_candidate_count": pending.get("candidate_count"),
            "supporting_observation_ids": pending.get("evidence_ids", []),
            "mandatory_content": mandatory_content(message.get("body") or ""),
            "model_budget": budget.metrics() if budget else None,
            "validation": "fresh_validated", "final_payload_digest": digest(message)}
