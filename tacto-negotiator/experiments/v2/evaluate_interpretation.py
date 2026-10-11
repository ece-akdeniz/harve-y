"""Score exported assessments against provisional labels; never used by production prompts.

Usage: .venv/bin/python experiments/v2/evaluate_interpretation.py predictions.json
Predictions are a list of {id, assessment: <SupplierAssessment JSON>, critical_errors: []}.
Critical-error annotations require external review; missing annotations stay unreviewed.
"""

import argparse
import json
from pathlib import Path

from negotiator.v2.core.models import SupplierAssessment


def evaluate(labels, predictions):
    by_id = {p["id"]: p for p in predictions}
    if len(by_id) != len(predictions) or not set(by_id) <= {s["id"] for s in labels["examples"]}:
        raise ValueError("duplicate/unknown prediction IDs")
    tp = fp = fn = abstentions = grounding = unsupported = missing = fallbacks = unreviewed = 0
    critical = correct = 0
    categories = {}
    for example in labels["examples"]:
        record = by_id.get(example["id"])
        expected = set(example["observation_kinds"])
        if record is None:
            missing += 1
            fn += len(expected)
            continue
        assessment = SupplierAssessment.model_validate_json(json.dumps(record["assessment"]))
        observed = {o.kind for o in assessment.observations} if assessment.status == "ok" else set()
        spans = [c for o in assessment.observations for c in o.citations if hasattr(c, "quote")]
        bad_spans = [c for c in spans if example.get("text", "")[c.start:c.end] != c.quote]
        condition_lost = example.get("condition_required", False) and any(
            c.start != 0 or c.end != len(example["text"]) for c in spans
        )
        missing_unknowns = set(example["unknowns"]) - set(assessment.unknowns)
        expected_relation = example.get("hypothesis_relation")
        relation_ok = expected_relation is None or any(h.relation == expected_relation for h in assessment.hypotheses)
        expected_constraints = example.get("reported_constraints")
        constraint_ok = expected_constraints is None or sorted(
            (c.dimension, c.op, str(c.value), bool(c.condition_observation_refs))
            for c in assessment.reported_constraints
        ) == sorted((c["dimension"], c["op"], str(c["value"]), c["conditional"]) for c in expected_constraints)
        expected_preferences = example.get("preference_dimensions")
        preferences_ok = expected_preferences is None or set(expected_preferences) == {
            h.dimension for h in assessment.hypotheses if h.relation == "prefers"
        }
        contradiction_ok = not example.get("blocking_contradiction", False) or any(
            u.kind == "contradiction" and u.blocking for u in assessment.uncertainties)
        correct += (assessment.status == "ok" and observed == expected and not missing_unknowns
                    and not bad_spans and not condition_lost and relation_ok
                    and constraint_ok and preferences_ok and contradiction_ok)
        abstentions += assessment.status != "ok"
        fallbacks += assessment.status == "fallback"
        grounding += bool(bad_spans or condition_lost or "ungrounded_output" in assessment.unknowns
                          or "missing_source" in assessment.unknowns)
        unsupported += "unsupported_claim" in assessment.unknowns
        tp += len(expected & observed)
        fp += len(observed - expected)
        fn += len(expected - observed)
        categories.setdefault(example["group"], []).append({
            "id": example["id"], "expected": sorted(expected), "observed": sorted(observed),
            "missing_unknowns": sorted(missing_unknowns), "bad_spans": len(bad_spans),
            "condition_lost": condition_lost, "hypothesis_relation_ok": relation_ok,
            "status": assessment.status, "constraints_ok": constraint_ok,
            "preferences_ok": preferences_ok, "blocking_contradiction_ok": contradiction_ok,
        })
        if "critical_errors" not in record:
            unreviewed += 1
        else:
            critical += len(record["critical_errors"])
    return {"label_review": labels["review_status"], "denominator": len(labels["examples"]),
            "prediction_count": len(predictions), "missing": missing,
            "structural_admission_rate": (len(predictions) - abstentions) / len(predictions) if predictions else None,
            "semantic_correct": correct,
            "accuracy": correct / len(labels["examples"]) if predictions and labels["examples"] else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "abstentions": abstentions, "fallbacks": fallbacks, "grounding_failures": grounding,
            "unsupported_claim_failures": unsupported, "critical_errors": critical,
            "critical_review_missing": unreviewed, "categories": categories,
            "claim_scope": "measured exported outputs only; scripted drafts do not measure model understanding"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    labels = json.loads((root / "tests/fixtures/v2/interpretation-pilot.json").read_text())
    print(json.dumps(evaluate(labels, json.loads(args.predictions.read_text())), indent=2))


if __name__ == "__main__":
    main()
