"""Fixture normalization only. Expected outputs never enter the production replay codec.

Stage fault injection is supplied as an explicit replay failure schedule; the offline runner
must implement it via injected port doubles, not conditional branches in live components.
"""

import copy
import json


def normalize_fixture(fixture):
    raw = copy.deepcopy(fixture)
    # Evaluation labels and historical baseline answers must not influence decisions.
    raw.pop("expected_evidence", None)
    raw.pop("official_cost_goldens", None)
    variants = raw.pop("variants", [])
    variant_id = raw.pop("model_fixture_id", "greeting")
    selected = next((v for v in variants if v["id"] == variant_id), {})
    raw.setdefault("reply", selected.get("body", ""))
    raw.setdefault("model_response", selected.get("model_response", {}))
    raw["wire_message"] = {
        "subject": "Offer", "body": "Our proposal follows.",
        "term_sheets": [{"terms": raw.pop("wire_terms", copy.deepcopy(raw["packages"][0]))}],
        "refs": [], "attachments": [],
    }
    wire = raw["wire_message"]
    fault = raw.pop("validation_fault", None)
    positive = raw.pop("validation_positive", None)
    value = fault or positive
    if value == "missing_field":
        wire["term_sheets"][0]["terms"].pop("contract_months")
    elif value == "mixed_accept_offer":
        wire["action"] = {"type": "accept", "term_sheet_id": "offer:valid-standing"}
    elif value in {"subject_300", "subject_301"}:
        wire["subject"] = "x" * int(value.split("_")[1])
    elif value in {"body_8000", "body_8001"}:
        wire["body"] = "x" * int(value.split("_")[1])
    elif value in {"three_sheets", "four_sheets"}:
        wire["term_sheets"] *= 3 if value == "three_sheets" else 4
    elif value in {"refs_20", "refs_21"}:
        wire["refs"] = [f"doc:fixture-{index}" for index in range(int(value.split("_")[1]))]
    elif value == "attachments_6":
        wire["attachments"] = [{"name": f"fixture-{index}.txt", "text": "approved"} for index in range(6)]
    elif value == "private_body":
        wire["body"] = "Our reservation cost is EUR 999999."
    elif value in {"internal_claim", "hallucinated_claim", "stale_claim", "claims_4"}:
        wire["body"] = " ".join(f"Verified claim fixture {i}." for i in range(4 if value == "claims_4" else 1))
        wire["refs"] = ["cost:310010" if value == "internal_claim" else "doc:claim-fixture"]
    elif value == "question":
        wire.pop("term_sheets")
        wire["body"] = "Which commitment duration can you approve?"
    # These flags change typed input state or claim/certificate fixtures, never expected outcomes.
    raw["input_mutation"] = value
    raw["wire_payload_json"] = json.dumps(wire, ensure_ascii=False, allow_nan=False)
    raw["replay_schedule"] = raw.pop("gateway_scenario", "acknowledged_send")
    raw["port_failure_schedule"] = raw.pop("runtime_fault", None)
    return raw
