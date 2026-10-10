"""Keep recovered owned-session outcomes separate from original runner evidence."""

import copy
import math

RECONCILIATION_KEYS = {"reconciled_result", "reconciliation_note"}
RECONCILIATION_NOTE = "Recovered from owned session history; original local attempt evidence is preserved."


def known_score(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1


def recovered_result(attempt: dict) -> dict | None:
    result = attempt.get("result", {}).get("reconciled_result")
    return result if isinstance(result, dict) and known_score(result.get("score")) else None


def original_result(result: dict) -> dict:
    return {key: value for key, value in result.items() if key not in RECONCILIATION_KEYS}


def official_result(attempt: dict) -> dict | None:
    if attempt.get("status") == "completed" and known_score(attempt.get("score")):
        result = copy.deepcopy(original_result(attempt.get("result", {})))
        result["score"] = attempt["score"]
        return result
    recovered = recovered_result(attempt)
    return copy.deepcopy(recovered) if recovered else None


def attach_recovered(attempt: dict, outcome: dict) -> bool:
    if not isinstance(outcome, dict) or not known_score(outcome.get("score")):
        return False
    previous = recovered_result(attempt)
    if previous:
        if any(key in outcome and outcome[key] != value for key, value in previous.items()):
            raise ValueError("recovered outcome is immutable")
        outcome = {**previous, **outcome}
        if outcome == previous:
            return False
    attempt["result"] = {
        **attempt.get("result", {}),
        "reconciled_result": copy.deepcopy(outcome),
        "reconciliation_note": RECONCILIATION_NOTE,
    }
    return True


def preserve_recovered(before: dict, after: dict) -> None:
    outcome = recovered_result(before)
    if outcome:
        incoming = recovered_result(after)
        if incoming:
            holder = {"result": copy.deepcopy(before["result"])}
            attach_recovered(holder, incoming)
            outcome = holder["result"]["reconciled_result"]
        after["result"] = {
            **after.get("result", {}),
            "reconciled_result": copy.deepcopy(outcome),
            "reconciliation_note": RECONCILIATION_NOTE,
        }
