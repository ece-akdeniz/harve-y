"""Bounded rejection metadata. Never serialize exception messages or supplied field names."""

from typing import Annotated, Literal

from pydantic import Field, ValidationError

from . import models as m


class AdmissionDiagnostic(m.FrozenModel):
    stage: Literal["projection", "execution", "format", "schema", "grounding", "consumer"]
    category: Literal[
        "invalid_json", "schema_mismatch", "missing_field", "invalid_type", "invalid_enum",
        "semantic_relationship", "unsupported_claim", "missing_evidence", "invalid_quote",
        "candidate_id_mismatch", "unsupported_economics", "grounding_failure", "disclosure_violation",
        "consumer_validation", "execution_failure", "unattributable",
    ]
    field: Annotated[str, Field(max_length=160, pattern=r"^[A-Za-z0-9_.*$]+$")] = "$"
    error_type: Literal["validation", "contract", "timeout", "execution", "unknown"]
    union_errors: tuple[str, ...] = ()


def rejection(error, stage):
    if isinstance(error, ValidationError):
        errors = error.errors(include_input=False, include_context=False, include_url=False)
        # Prefer the branch matching a message citation; retain bounded safe branch paths.
        branch = "function-after[ordered_offsets(), MessageSpan]"
        first = next((e for e in errors if "MessageSpan" in e["loc"] or branch in e["loc"]), errors[0])
        errors = [first, *(e for e in errors if e is not first)]
        category = {
            "json_invalid": "invalid_json", "missing": "missing_field", "literal_error": "invalid_enum",
            "enum": "invalid_enum", "value_error": "semantic_relationship",
        }.get(first["type"], "invalid_type" if first["type"].endswith("_type") else "schema_mismatch")
        # Only schema-owned names may enter persisted paths; extra keys can contain secrets.
        schema = m.AssessmentDraft.model_json_schema()
        allowed = set(schema["properties"])
        for definition in schema.get("$defs", {}).values():
            allowed.update(definition.get("properties", {}))
        allowed.update(m.SelectorResponse.model_json_schema()["properties"])
        allowed.update({"SourceRef", "MessageSpan"})
        allowed.add(branch)
        def safe_part(x):
            return "MessageSpan" if x == branch else str(x) if isinstance(x, int) else x if x in allowed else "*"
        path = [safe_part(x) for x in first["loc"][:8]]
        return AdmissionDiagnostic(stage="format" if category == "invalid_json" else "schema",
                                   category=category, field=(".".join(path) or "$")[:160], error_type="validation",
                                   union_errors=tuple(".".join(
                                       safe_part(x) for x in e["loc"][:8])[:160]
                                                      for e in errors[:8]))
    text = str(error)  # Used only for matching code-authored fixed reasons; never persisted.
    category = "consumer_validation"
    for marker, value in (
        ("private_disclosure", "disclosure_violation"), ("selected ID outside", "candidate_id_mismatch"),
        ("message span", "invalid_quote"), ("supporting quote", "invalid_quote"),
        ("missing_source", "missing_evidence"), ("numeric", "unsupported_economics"),
        ("antecedent", "semantic_relationship"), ("conditional scope", "semantic_relationship"),
        ("contradict", "semantic_relationship"), ("unsupported_claim", "unsupported_claim"),
        ("unsupported explicit constraint", "unsupported_claim"),
        ("dimension/operator", "unsupported_claim"),
        ("observation kind", "semantic_relationship"),
        ("unconditional", "semantic_relationship"),
        ("uncalibrated", "unsupported_economics"),
        ("ungrounded_output", "grounding_failure"),
    ):
        if marker in text:
            category = value
            break
    if stage == "execution":
        category = "execution_failure"
    return AdmissionDiagnostic(stage=stage, category=category,
                               error_type="timeout" if isinstance(error, TimeoutError) else "contract")
