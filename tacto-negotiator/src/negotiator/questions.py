"""Registered clarification actions carried with a complete, legal package."""

import hashlib
import json
import re

FIELD_LABELS = {"lead_time_days": "delivery schedule", "contract_months": "contract term",
                "payment_days": "payment schedule", "volume_per_year": "annual volume"}
MAX_QUESTIONS = 1


def catalog(events, baseline, packages):
    """A yes answer supports the candidate; no retains a feasible baseline.

    Do not ask about a term already explicitly supplied or repeat an acknowledged
    question. Every question is attached to the candidate it could clarify.
    """
    buyer_bodies = [e.get("body") or "" for e in events if e.get("from") == "buyer"]
    if sum("Could you confirm whether the attached" in body for body in buyer_bodies) >= MAX_QUESTIONS:
        return {}
    latest_supplier = max((i for i, e in enumerate(events) if e.get("from") != "buyer"), default=-1)
    latest_buyer_question = max((i for i, e in enumerate(events) if e.get("from") == "buyer"
                                 and "Could you confirm whether the attached" in (e.get("body") or "")), default=-1)
    if latest_buyer_question > latest_supplier:
        return {}  # one unresolved question at a time
    supplier_text = " ".join(e.get("body") or "" for e in events if e.get("from") != "buyer")
    out = {}
    for package_id, terms in packages.items():
        changed = [field for field in FIELD_LABELS if terms.get(field) != baseline.get(field)]
        if len(changed) != 1:
            continue
        field = changed[0]
        value = terms[field]
        if re.search(rf"(?<!\d){re.escape(str(value))}(?!\d)", supplier_text):
            continue
        sentence = (f"Could you confirm whether the attached {FIELD_LABELS[field]} "
                    "resolves the constraint you described?")
        if any(sentence in body for body in buyer_bodies):
            continue
        question_id = "question_" + hashlib.sha256(json.dumps(
            [field, value, package_id], sort_keys=True).encode()).hexdigest()[:12]
        out[question_id] = {"package_id": package_id, "field": field, "value": value,
                            "text": sentence, "yes_action": package_id, "no_action": "keep"}
        if len(out) >= 4:
            break
    return out
