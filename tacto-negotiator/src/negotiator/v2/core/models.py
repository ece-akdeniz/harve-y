"""Strict immutable V2 value objects for contracts, terms, and evidence refs."""

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)

from .serialization import decimal_text, semantic_hash

SCHEMA_VERSION = "negotiator-v2/1"
TermField = Literal[
    "unit_price", "payment_days", "lead_time_days", "volume_per_year",
    "contract_months", "effective_date", "index_clause", "incoterm",
    "tooling_eur", "ppm_commitment", "chargeback_eur_per_complaint",
]
IssueCode = Literal[
    "missing_source", "source_conflict", "stale_source", "future_source",
    "unknown_basis", "scope_mismatch", "unsupported_capability", "invalid_schema",
    "infeasible", "nonfinite_cost", "uncertified_price", "unsupported_claim",
    "private_disclosure", "stale_state", "deadline_exhausted", "rounds_unknown",
    "operation_pending", "model_timeout", "model_invalid", "ungrounded_output",
    "store_conflict", "recovery_required", "invalid_terminal_proof", "not_applicable",
]


class FrozenModel(BaseModel):
    """Base for immutable, strict domain models."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", allow_inf_nan=False)
    schema_version: Literal["negotiator-v2/1"] = SCHEMA_VERSION

    @field_serializer("*", when_used="json")
    def canonical_decimal_fields(self, value):
        return decimal_text(value) if isinstance(value, Decimal) else value

    @field_validator("*")
    @classmethod
    def strict_identity_fields(cls, value, info: ValidationInfo):
        name = info.field_name
        if name.endswith(("_id", "_hash", "_fingerprint")) or name in {"fingerprint", "context_version"}:
            if value is not None and isinstance(value, str):
                if not value.strip() or value != value.strip():
                    raise ValueError(f"{name} must be a nonempty unpadded identifier")
                if name.endswith(("_hash", "_fingerprint")) or name == "fingerprint":
                    if not re.fullmatch(r"[0-9a-f]{64}", value):
                        raise ValueError(f"{name} must be a SHA-256 hex digest")
        return value


def _finite_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("amount must be finite")
    return value


class PriceBasis(FrozenModel):
    currency: Literal["EUR"]
    price_unit: Annotated[int, Field(gt=0)]
    part_ids: tuple[str, ...]
    quantity_basis: str
    source_refs: tuple[str, ...]

    @field_validator("price_unit", mode="before")
    @classmethod
    def reject_bool_price_unit(cls, value):
        if isinstance(value, bool):
            raise ValueError("price_unit must be an integer")
        return value

    @field_validator("part_ids", "source_refs")
    @classmethod
    def require_tuple_inputs(cls, value):
        if not isinstance(value, tuple):
            raise ValueError("domain collections must be immutable tuples")
        return value

    @field_validator("part_ids", "source_refs")
    @classmethod
    def require_parts(cls, value, info: ValidationInfo):
        if (info.field_name == "part_ids" and not value) or any(
            not item.strip() or item != item.strip() for item in value
        ):
            raise ValueError("part_ids must be nonempty")
        return value

    @field_validator("quantity_basis")
    @classmethod
    def require_quantity_basis(cls, value):
        if not value.strip():
            raise ValueError("quantity_basis must be nonempty")
        return value


class Price(FrozenModel):
    amount: Decimal
    basis: PriceBasis

    @field_validator("amount", mode="before")
    @classmethod
    def strict_amount(cls, value, info: ValidationInfo):
        if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
            raise ValueError("amount must be a Decimal")
        if isinstance(value, str):
            if info.mode != "json":
                raise ValueError("Python amount values must be Decimal")
            try:
                value = Decimal(value)
            except Exception as exc:
                raise ValueError("amount must be a decimal string") from exc
        _finite_decimal(value)
        if value <= 0:
            raise ValueError("price must be positive")
        return value


class Money(FrozenModel):
    amount: Decimal
    currency: Literal["EUR"] = "EUR"

    @field_validator("amount", mode="before")
    @classmethod
    def strict_amount(cls, value, info: ValidationInfo):
        if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
            raise ValueError("amount must be a Decimal")
        if isinstance(value, str):
            if info.mode != "json":
                raise ValueError("Python amount values must be Decimal")
            try:
                value = Decimal(value)
            except Exception as exc:
                raise ValueError("amount must be a decimal string") from exc
        return _finite_decimal(value)


class IndexClause(FrozenModel):
    series: str
    material_share: Decimal
    deadband_pct: Decimal
    base_month: str

    @field_validator("series")
    @classmethod
    def nonempty_series(cls, value):
        if not value.strip():
            raise ValueError("series must be nonempty")
        return value

    @field_validator("material_share", "deadband_pct", mode="before")
    @classmethod
    def strict_finite_decimal(cls, value, info: ValidationInfo):
        if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
            raise ValueError("value must be a Decimal")
        if isinstance(value, str):
            if info.mode != "json":
                raise ValueError("Python values must be Decimal")
            try:
                value = Decimal(value)
            except Exception as exc:
                raise ValueError("value must be a decimal string") from exc
        return _finite_decimal(value)

    @field_validator("material_share")
    @classmethod
    def share_in_range(cls, value):
        if not Decimal("0") <= value <= Decimal("1"):
            raise ValueError("material_share must be in [0, 1]")
        return value

    @field_validator("deadband_pct")
    @classmethod
    def nonnegative_deadband(cls, value):
        if value < 0:
            raise ValueError("deadband_pct must be nonnegative")
        return value

    @field_validator("base_month")
    @classmethod
    def real_month(cls, value):
        if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) or value.startswith("0000-"):
            raise ValueError("base_month must be YYYY-MM")
        return value


class TermBinding(FrozenModel):
    field: TermField
    value: int | Decimal | str | date | IndexClause | None

    @model_validator(mode="before")
    @classmethod
    def validate_field_value(cls, data, info: ValidationInfo):
        if not isinstance(data, dict) or "field" not in data or "value" not in data:
            return data
        field, value = data["field"], data["value"]
        integer_fields = {"payment_days", "lead_time_days", "volume_per_year", "contract_months", "ppm_commitment"}
        decimal_fields = {"unit_price", "tooling_eur", "chargeback_eur_per_complaint"}
        if field in integer_fields:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field} must be an integer")
            minimum = 1 if field in {"volume_per_year", "contract_months"} else 0
            if value < minimum:
                raise ValueError(f"{field} must be >= {minimum}")
        elif field in decimal_fields:
            if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
                raise ValueError(f"{field} must be a Decimal")
            if isinstance(value, str):
                if info.mode != "json":
                    raise ValueError(f"Python {field} values must be Decimal")
                try:
                    value = Decimal(value)
                except Exception as exc:
                    raise ValueError(f"{field} must be a decimal string") from exc
                data = {**data, "value": value}
            _finite_decimal(value)
            if field != "unit_price" and value < 0:
                raise ValueError(f"{field} must be nonnegative")
            if field == "unit_price" and value <= 0:
                raise ValueError("unit_price must be positive")
        elif field == "effective_date":
            if info.mode == "json" and isinstance(value, str):
                try:
                    parsed = date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError("effective_date must be an ISO date") from exc
                if parsed.isoformat() != value:
                    raise ValueError("effective_date must be a real ISO date")
                data = {**data, "value": parsed}
            elif type(value) is not date:
                raise ValueError("effective_date must be a date")
        elif field == "index_clause":
            if value is not None and not isinstance(value, IndexClause) and not (
                info.mode == "json" and isinstance(value, dict)
            ):
                raise ValueError("index_clause must be an IndexClause or null")
        elif field == "incoterm":
            if value not in {"EXW", "FCA", "DAP"}:
                raise ValueError("incoterm must be EXW, FCA, or DAP")
        return data


class Package(FrozenModel):
    bindings: tuple[TermBinding, ...]
    price_basis: PriceBasis
    fingerprint: str = ""

    @model_validator(mode="after")
    def verify_fingerprint(self):
        projection = {"bindings": sorted(self.bindings, key=lambda binding: binding.field),
                      "price_basis": self.price_basis}
        expected = semantic_hash(projection)
        if self.fingerprint and self.fingerprint != expected:
            raise ValueError("package_fingerprint_mismatch")
        object.__setattr__(self, "fingerprint", expected)
        return self

    @field_validator("bindings")
    @classmethod
    def immutable_bindings(cls, value):
        if not isinstance(value, tuple):
            raise ValueError("bindings must be an immutable tuple")
        fields = [binding.field for binding in value]
        if len(fields) != len(set(fields)):
            raise ValueError("package bindings must have unique fields")
        return value


class SourceRef(FrozenModel):
    record_id: str
    canonical_id: str | None = None

    @field_validator("record_id")
    @classmethod
    def nonempty_record_id(cls, value):
        if not value.strip():
            raise ValueError("record_id must be nonempty")
        return value

    @field_validator("canonical_id")
    @classmethod
    def nonempty_canonical_id(cls, value):
        if value is not None and not value.strip():
            raise ValueError("canonical_id must be nonempty when supplied")
        return value


class MessageSpan(FrozenModel):
    session_id: str
    thread_id: str
    message_id: str
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    quote: str

    @field_validator("session_id", "thread_id", "message_id")
    @classmethod
    def nonempty_message_identity(cls, value):
        if not value.strip():
            raise ValueError("message identity values must be nonempty")
        return value

    @field_validator("start", "end", mode="before")
    @classmethod
    def reject_bool_offsets(cls, value):
        if isinstance(value, bool):
            raise ValueError("span offsets must be integers")
        return value

    @model_validator(mode="after")
    def ordered_offsets(self):
        if self.end - self.start != len(self.quote):
            raise ValueError("span offsets must match the Unicode quote length")
        return self


Citation = SourceRef | MessageSpan
TermValue = int | Decimal | str | date | IndexClause | None


class SnapshotRef(FrozenModel):
    run_id: str
    session_id: str
    state_version: Annotated[int, Field(ge=0)]
    context_version: str
    config_hash: str
    case_contract_hash: str

    @field_validator("state_version", mode="before")
    @classmethod
    def reject_bool_version(cls, value):
        if isinstance(value, bool):
            raise ValueError("state_version must be an integer")
        return value


class Issue(FrozenModel):
    code: IssueCode
    severity: Literal["error", "warning"]
    component: str
    refs: tuple[str, ...]
    detail: str

    @field_validator("refs")
    @classmethod
    def immutable_refs(cls, value):
        if not isinstance(value, tuple):
            raise ValueError("refs must be an immutable tuple")
        return value


class GroundedObservation(FrozenModel):
    observation_id: str
    kind: Literal[
        "request", "refusal", "conditional_offer", "constraint",
        "approval_requirement", "stated_driver", "ambiguity",
    ]
    dimension: TermField | None
    summary: str
    citations: tuple[Citation, ...]
    package_fingerprint: str | None = None

    @field_validator("observation_id", "summary")
    @classmethod
    def required_observation_text(cls, value):
        if not value.strip():
            raise ValueError("observation identity and summary must be nonempty")
        return value

    @field_validator("citations")
    @classmethod
    def grounded_citations(cls, value):
        if not value:
            raise ValueError("observations require at least one citation")
        return value


class ReportedConstraint(FrozenModel):
    constraint_id: str
    dimension: TermField
    op: Literal["==", "!=", "<=", ">="]
    value: TermValue
    condition_observation_refs: tuple[str, ...]
    citations: tuple[Citation, ...]
    authority: Literal["supplier_reported"]
    status: Literal["active", "stale", "superseded"]

    @field_validator("value", mode="before")
    @classmethod
    def structured_reported_value(cls, value, info: ValidationInfo):
        if "dimension" not in info.data:
            return value
        raw = {"field": info.data["dimension"], "value": value}
        binding = (TermBinding.model_validate_json(json.dumps(raw)) if info.mode == "json"
                   else TermBinding.model_validate(raw))
        return binding.value

    @field_validator("constraint_id")
    @classmethod
    def required_constraint_id(cls, value):
        if not value.strip():
            raise ValueError("constraint_id must be nonempty")
        return value

    @field_validator("condition_observation_refs")
    @classmethod
    def immutable_condition_refs(cls, value):
        if any(not ref.strip() for ref in value):
            raise ValueError("condition observation refs must be nonempty strings")
        return value

    @model_validator(mode="after")
    def active_constraint_is_grounded(self):
        if self.status == "active" and not self.citations:
            raise ValueError("active reported constraints require citations")
        return self


class EstimatedEffect(FrozenModel):
    low: Decimal
    high: Decimal
    unit: str
    basis: PriceBasis | None = None
    method_id: str
    citations: tuple[Citation, ...]

    @field_validator("low", "high", mode="before")
    @classmethod
    def finite_effect_bound(cls, value, info: ValidationInfo):
        if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
            raise ValueError("effect bounds must be Decimal values")
        if isinstance(value, str):
            if info.mode != "json":
                raise ValueError("Python effect bounds must be Decimal")
            try:
                value = Decimal(value)
            except Exception as exc:
                raise ValueError("effect bounds must be decimal strings") from exc
        return _finite_decimal(value)

    @field_validator("unit", "method_id")
    @classmethod
    def nonempty_effect_labels(cls, value):
        if not value.strip():
            raise ValueError("effect unit and method_id must be nonempty")
        return value

    @model_validator(mode="after")
    def ordered_effect_bounds(self):
        if self.low > self.high:
            raise ValueError("effect low must not exceed high")
        return self


class PreferenceHypothesis(FrozenModel):
    hypothesis_id: str
    dimension: TermField | None
    relation: Literal["prefers", "avoids", "requires", "unknown"]
    direction: Literal["increase", "decrease", "enumerate", "unknown"]
    summary: str
    supporting_refs: tuple[Citation, ...]
    contradicting_refs: tuple[Citation, ...]
    confidence: Literal["low", "medium", "high", "unknown"]
    status: Literal["active", "stale", "superseded", "unknown"]
    numeric_effect: EstimatedEffect | None = None

    @field_validator("hypothesis_id", "summary")
    @classmethod
    def required_hypothesis_text(cls, value):
        if not value.strip():
            raise ValueError("hypothesis identity and summary must be nonempty")
        return value

    @model_validator(mode="after")
    def active_hypothesis_is_grounded(self):
        if self.status == "active" and not self.supporting_refs:
            raise ValueError("active hypotheses require supporting refs")
        return self


class AssessmentUncertainty(FrozenModel):
    uncertainty_id: str
    kind: Literal["approval", "conditional", "contradiction", "insufficient_evidence", "missing_source"]
    dimension: TermField | None = None
    summary: str
    citations: tuple[Citation, ...]
    related_observation_refs: tuple[str, ...]
    blocking: bool

    @field_validator("uncertainty_id", "summary")
    @classmethod
    def required_uncertainty_text(cls, value):
        if not value.strip():
            raise ValueError("uncertainty identity and summary must be nonempty")
        return value

    @field_validator("related_observation_refs")
    @classmethod
    def immutable_related_refs(cls, value):
        if any(not ref.strip() for ref in value):
            raise ValueError("related observation refs must be nonempty strings")
        return value


class ClarificationQuestion(FrozenModel):
    question_id: str
    template_id: str
    dimension: TermField | None = None
    citations: tuple[Citation, ...]
    unknown_id: str
    expected_information: str

    @field_validator("question_id", "template_id", "unknown_id", "expected_information")
    @classmethod
    def required_question_text(cls, value):
        if not value.strip():
            raise ValueError("question identifiers and expected information must be nonempty")
        return value


class SupplierAssessment(FrozenModel):
    assessment_id: str
    supplier_id: str
    snapshot: SnapshotRef
    revision: Annotated[int, Field(gt=0)]
    observations: tuple[GroundedObservation, ...]
    reported_constraints: tuple[ReportedConstraint, ...]
    hypotheses: tuple[PreferenceHypothesis, ...]
    uncertainties: tuple[AssessmentUncertainty, ...]
    questions: tuple[ClarificationQuestion, ...]
    unknowns: tuple[str, ...]
    status: Literal["ok", "fallback", "insufficient_evidence"]
    interpreter_id: str
    model_call_id: str | None
    parent_assessment_id: str | None = None

    @field_validator("revision", mode="before")
    @classmethod
    def reject_bool_revision(cls, value):
        if isinstance(value, bool):
            raise ValueError("revision must be a positive integer")
        return value

    @field_validator("assessment_id", "supplier_id", "interpreter_id")
    @classmethod
    def required_assessment_identity(cls, value):
        if not value.strip():
            raise ValueError("assessment identity values must be nonempty")
        return value

    @field_validator("unknowns")
    @classmethod
    def nonempty_unknown_labels(cls, value):
        if any(not item.strip() for item in value):
            raise ValueError("unknown labels must be nonempty strings")
        return value


class AssessmentDraft(FrozenModel):
    observations: tuple[GroundedObservation, ...]
    reported_constraints: tuple[ReportedConstraint, ...]
    hypotheses: tuple[PreferenceHypothesis, ...]
    uncertainties: tuple[AssessmentUncertainty, ...]
    questions: tuple[ClarificationQuestion, ...]
    unknowns: tuple[str, ...]

    @field_validator("unknowns")
    @classmethod
    def nonempty_unknown_labels(cls, value):
        if any(not item.strip() for item in value):
            raise ValueError("unknown labels must be nonempty strings")
        return value


DecisionStageName = Literal[
    "evidence", "assessment", "proposal", "generation", "evaluation",
    "selection", "rendering", "validation", "execution", "feedback",
]
DecisionStageStatus = Literal["planned", "completed", "failed", "skipped"]
DECISION_STAGE_ORDER = (
    "evidence", "assessment", "proposal", "generation", "evaluation",
    "selection", "rendering", "validation", "execution", "feedback",
)
ARTIFACT_REF_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _validate_artifact_ref(value: str) -> str:
    if not ARTIFACT_REF_PATTERN.fullmatch(value):
        raise ValueError("artifact references must be sha256:<64 lowercase hex>")
    return value


class DecisionStage(FrozenModel):
    schema_version: Literal["negotiator-v2/1"]
    name: DecisionStageName
    status: DecisionStageStatus
    artifact_refs: tuple[str, ...]
    issue_codes: tuple[IssueCode, ...]

    @field_validator("artifact_refs")
    @classmethod
    def valid_stage_artifact_refs(cls, value):
        for ref in value:
            _validate_artifact_ref(ref)
        if len(value) != len(set(value)):
            raise ValueError("stage artifact references must be unique")
        return value

    @model_validator(mode="after")
    def status_has_artifacts_or_reason(self):
        if self.status == "completed" and not self.artifact_refs:
            raise ValueError("completed stages require artifacts")
        if self.status in {"failed", "skipped"} and not self.issue_codes:
            raise ValueError("stage_issue_required")
        if self.status == "planned" and (self.artifact_refs or self.issue_codes):
            raise ValueError("planned stages cannot have artifacts or issues")
        return self


class DecisionRecord(FrozenModel):
    schema_version: Literal["negotiator-v2/1"]
    record_id: UUID
    decision_id: UUID
    snapshot: SnapshotRef
    revision: Annotated[int, Field(gt=0)]
    parent_record_hash: str | None
    fixture_input_hash: str
    config_artifact_ref: str
    case_artifact_ref: str
    evidence_artifact_ref: str | None
    assessment_artifact_refs: tuple[str, ...]
    intent_artifact_refs: tuple[str, ...]
    candidate_artifact_refs: tuple[str, ...]
    evaluation_artifact_refs: tuple[str, ...]
    selection_artifact_ref: str | None
    rendered_artifact_ref: str | None
    validation_artifact_ref: str | None
    operation_artifact_ref: str | None
    execution_artifact_refs: tuple[str, ...]
    feedback_artifact_refs: tuple[str, ...]
    model_call_refs: tuple[str, ...]
    model_output_hashes: tuple[str, ...]
    issues: tuple[Issue, ...]
    stages: tuple[DecisionStage, ...]
    semantic_hash: str
    record_hash: str

    @field_validator("revision", mode="before")
    @classmethod
    def reject_bool_revision(cls, value):
        if isinstance(value, bool):
            raise ValueError("revision must be a positive integer")
        return value

    @field_validator(
        "fixture_input_hash", "semantic_hash", "record_hash", "parent_record_hash",
    )
    @classmethod
    def valid_content_hash(cls, value):
        if value is not None and not HASH_PATTERN.fullmatch(value):
            raise ValueError("hashes must be 64 lowercase hexadecimal characters")
        return value

    @field_validator(
        "config_artifact_ref", "case_artifact_ref", "evidence_artifact_ref",
        "assessment_artifact_refs", "intent_artifact_refs", "candidate_artifact_refs",
        "evaluation_artifact_refs", "selection_artifact_ref", "rendered_artifact_ref",
        "validation_artifact_ref", "operation_artifact_ref", "execution_artifact_refs",
        "feedback_artifact_refs",
    )
    @classmethod
    def valid_record_artifact_refs(cls, value):
        if value is None:
            return value
        refs = value if isinstance(value, tuple) else (value,)
        for ref in refs:
            _validate_artifact_ref(ref)
        if isinstance(value, tuple) and len(value) != len(set(value)):
            raise ValueError("record artifact references must be unique")
        return value

    @field_validator("model_call_refs")
    @classmethod
    def nonempty_model_call_refs(cls, value):
        if any(not ref.strip() for ref in value):
            raise ValueError("model call refs must be nonempty")
        return value

    @field_validator("model_output_hashes")
    @classmethod
    def valid_model_output_hashes(cls, value):
        if any(not HASH_PATTERN.fullmatch(item) for item in value):
            raise ValueError("model output hashes must be 64 lowercase hexadecimal characters")
        return value

    @model_validator(mode="after")
    def record_invariants(self):
        actual_order = tuple(stage.name for stage in self.stages)
        if len(self.stages) != len(DECISION_STAGE_ORDER) or actual_order != DECISION_STAGE_ORDER:
            raise ValueError("stage_order")
        if (self.revision == 1) != (self.parent_record_hash is None):
            raise ValueError("revision_parent_mismatch")

        by_name = {stage.name: stage for stage in self.stages}
        for index, stage in enumerate(self.stages):
            if stage.status != "completed" and any(
                later.status == "completed" for later in self.stages[index + 1 :]
            ):
                raise ValueError("downstream_stage_completed_after_incomplete_stage")
        if by_name["selection"].status == "planned" and any(
            stage.status != "planned" for stage in self.stages[6:]
        ):
            raise ValueError("downstream_stage_before_selection")
        if self.selection_artifact_ref is not None and not self.evaluation_artifact_refs:
            raise ValueError("orphan_selection")
        if self.selection_artifact_ref is not None and by_name["selection"].status != "completed":
            raise ValueError("orphan_selection")
        if by_name["selection"].status == "completed" and (
            by_name["evaluation"].status != "completed" or not self.evaluation_artifact_refs
        ):
            raise ValueError("orphan_selection")
        if by_name["selection"].status == "completed" and self.selection_artifact_ref is None:
            raise ValueError("selection_artifact_required")
        validation_completed = by_name["validation"].status == "completed"
        if validation_completed and (
            self.validation_artifact_ref is None
            or self.rendered_artifact_ref is None
            or by_name["rendering"].status != "completed"
        ):
            raise ValueError("validation_without_rendering")
        executed = bool(self.execution_artifact_refs) or by_name["execution"].status == "completed"
        if executed and (self.validation_artifact_ref is None or self.operation_artifact_ref is None):
            raise ValueError("execution_requires_validated_operation")
        if executed and by_name["validation"].status != "completed":
            raise ValueError("execution_requires_validated_operation")
        if by_name["execution"].status == "completed" and not self.execution_artifact_refs:
            raise ValueError("execution_requires_artifact")
        if by_name["feedback"].status == "completed" and (
            by_name["execution"].status != "completed" or not self.execution_artifact_refs
        ):
            raise ValueError("feedback_requires_execution")

        stage_artifact_refs = {
            "evidence": (self.evidence_artifact_ref,) if self.evidence_artifact_ref else (),
            "assessment": self.assessment_artifact_refs,
            "proposal": self.intent_artifact_refs,
            "generation": self.candidate_artifact_refs,
            "evaluation": self.evaluation_artifact_refs,
            "selection": (self.selection_artifact_ref,) if self.selection_artifact_ref else (),
            "rendering": (self.rendered_artifact_ref,) if self.rendered_artifact_ref else (),
            "validation": (self.validation_artifact_ref,) if self.validation_artifact_ref else (),
            "execution": self.execution_artifact_refs,
            "feedback": self.feedback_artifact_refs,
        }
        if any(
            by_name[name].artifact_refs != refs
            for name, refs in stage_artifact_refs.items()
        ):
            raise ValueError("stage_artifact_reference_mismatch")

        expected_hash = semantic_hash(self.model_dump(mode="json", exclude={"record_hash"}))
        if self.record_hash != expected_hash:
            raise ValueError("record_hash_mismatch")
        return self


class EffectiveConfig(FrozenModel):
    _verified_hash: str | None = PrivateAttr(default=None)
    _verified_strategy_ids: tuple[str, ...] = PrivateAttr(default=())

    @field_validator("retry_limit", mode="before")
    @classmethod
    def strict_retry_limit(cls, value):
        if type(value) is not int:
            raise ValueError("retry_limit must be an integer")
        return value

    schema_version: Literal["negotiator-v2/1"]
    strategy_id: str
    selection_id: Literal["deterministic-v1"]
    estimate_mode: Literal["disabled_explicit", "nominal_explicit", "robust_scenarios"]
    model_mode: Literal["fake"]
    compute_limit_s: Annotated[int, Field(gt=0)]
    interpreter_limit_s: Annotated[int, Field(gt=0)]
    selection_limit_s: Annotated[int, Field(gt=0)]
    candidate_limit: Annotated[int, Field(gt=0)]
    fallback_reserve_s: Annotated[int, Field(gt=0)]
    submission_reserve_s: Annotated[int, Field(gt=0)]
    price_tick: Decimal
    price_min: Decimal
    price_max: Decimal
    retry_limit: Literal[0]
    provider_id: str | None = None
    protocol_id: str | None = None
    prompt_version: str | None = None
    config_hash: str

    @field_validator("price_tick", "price_min", "price_max", mode="before")
    @classmethod
    def strict_config_decimal(cls, value, info: ValidationInfo):
        if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
            raise ValueError("price config values must be Decimal")
        if isinstance(value, str):
            if info.mode != "json":
                raise ValueError("Python price config values must be Decimal")
            try:
                value = Decimal(value)
            except Exception as exc:
                raise ValueError("price config values must be decimal strings") from exc
        return _finite_decimal(value)

    @field_validator("price_tick", "price_min", "price_max")
    @classmethod
    def positive_config_decimal(cls, value):
        if value <= 0:
            raise ValueError("price config values must be positive")
        return value

    @field_validator("config_hash")
    @classmethod
    def valid_config_hash(cls, value):
        if not HASH_PATTERN.fullmatch(value):
            raise ValueError("config_hash must be 64 lowercase hexadecimal characters")
        return value

    @field_validator("provider_id", "protocol_id", "prompt_version")
    @classmethod
    def nonempty_optional_model_ids(cls, value):
        if value is not None and not value.strip():
            raise ValueError("optional model identifiers must be nonempty when supplied")
        return value

    @model_validator(mode="after")
    def ordered_price_bounds(self):
        if self.price_min > self.price_max:
            raise ValueError("price_min must not exceed price_max")
        return self


class EvidenceScope(FrozenModel):
    supplier_ids: tuple[str, ...]
    part_ids: tuple[str, ...]
    level: Literal["supplier", "part", "basket", "case", "global"]
    case_id: str | None = None

    @field_validator("supplier_ids", "part_ids")
    @classmethod
    def valid_scope_ids(cls, value):
        if any(not item.strip() or item != item.strip() for item in value):
            raise ValueError("scope identifiers must be nonempty and unpadded")
        return value


class Provenance(FrozenModel):
    layer: Literal["base", "release", "case", "session", "derived"]
    source_version: str
    content_hash: str
    locator: str
    parent_refs: tuple[SourceRef, ...]
    parser_version: str | None = None

    @field_validator("locator")
    @classmethod
    def logical_locator(cls, value):
        if "://" in value:
            raise ValueError("locator must be a logical source location, not a URL")
        return value

    @field_validator("source_version", "locator", "parser_version")
    @classmethod
    def valid_provenance_labels(cls, value):
        if value is not None and not value.strip():
            raise ValueError("provenance labels must be nonempty when supplied")
        return value


class TemporalValidity(FrozenModel):
    status: Literal["current", "stale", "future", "unknown"]
    freshness_rule_id: str
    observed_at: datetime | None = None
    published_at: datetime | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    data_as_of: date | None = None

    @field_validator("observed_at", "published_at")
    @classmethod
    def utc_timestamps(cls, value):
        if value is not None and (value.utcoffset() is None or value.utcoffset() != timedelta(0)):
            raise ValueError("domain timestamps must be UTC with an offset")
        return value


class DisclosureRule(FrozenModel):
    classification: Literal["public", "supplier_own", "internal", "reveals_rival", "restricted"] = "restricted"
    permitted_recipients: tuple[str, ...]
    purpose: tuple[str, ...]

    @field_validator("permitted_recipients", "purpose")
    @classmethod
    def valid_disclosure_labels(cls, value):
        if any(not item.strip() or item != item.strip() for item in value):
            raise ValueError("disclosure labels must be nonempty and unpadded")
        return value


def _evidence_id(value: str) -> str:
    if not value.strip() or value != value.strip():
        raise ValueError("identifier must be nonempty and unpadded")
    return value


def _evidence_label(value: str) -> str:
    if not value.strip():
        raise ValueError("source label must be nonempty")
    return value


def _evidence_decimal(value, info: ValidationInfo):
    if info.mode == "json":
        if not isinstance(value, str):
            raise ValueError("JSON decimals must be strings")
        try:
            value = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("invalid decimal string") from error
    elif not isinstance(value, Decimal):
        raise ValueError("Python decimals must be Decimal objects")
    return _finite_decimal(value)


def _evidence_month(value: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) or value[:4] == "0000":
        raise ValueError("month must be YYYY-MM with a real year and month")
    return value


def _evidence_quarter(value: str) -> str:
    if not re.fullmatch(r"[0-9]{4}Q[1-4]", value) or value[:4] == "0000":
        raise ValueError("quarter must be YYYYQ1..4 with a real year")
    return value


_EvidenceId = Annotated[str, AfterValidator(_evidence_id)]
_EvidenceLabel = Annotated[str, AfterValidator(_evidence_label)]
_EvidenceDecimal = Annotated[Decimal, BeforeValidator(_evidence_decimal)]
_EvidencePercent = Annotated[_EvidenceDecimal, Field(ge=0, le=100)]


class IndexFact(FrozenModel):
    kind: Literal["index"]
    series: _EvidenceId
    month: Annotated[str, AfterValidator(_evidence_month)]
    value: _EvidenceDecimal
    unit: _EvidenceLabel


class ScorecardFact(FrozenModel):
    kind: Literal["scorecard"]
    supplier: _EvidenceId
    quarter: Annotated[str, AfterValidator(_evidence_quarter)]
    window_months: Annotated[int, Field(gt=0)]
    otd_pct: _EvidencePercent | None = None
    ppm: Annotated[int, Field(ge=0)] | None = None


class CostFact(FrozenModel):
    kind: Literal["cost"]
    part: _EvidenceId
    supplier: _EvidenceId | None = None
    unit_cost: Price
    confidence_pct: _EvidencePercent | None = None
    cost_base: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None


class QuoteFact(FrozenModel):
    kind: Literal["quote"]
    supplier: _EvidenceId
    part_ids: tuple[_EvidenceId, ...]
    price: Price
    observed_terms: tuple[TermBinding, ...]
    validity: TemporalValidity | None = None

    @model_validator(mode="after")
    def consistent_parts_and_fields(self):
        if not self.part_ids or len(set(self.part_ids)) != len(self.part_ids):
            raise ValueError("quote parts must be nonempty and unique")
        if set(self.part_ids) != set(self.price.basis.part_ids):
            raise ValueError("quote parts must match the price basis")
        if len({term.field for term in self.observed_terms}) != len(self.observed_terms):
            raise ValueError("quote term fields must be unique")
        return self


class ContractFact(FrozenModel):
    kind: Literal["contract"]
    supplier: _EvidenceId
    part_ids: tuple[_EvidenceId, ...]
    notice_days: Annotated[int, Field(ge=0)] | None = None
    clause_refs: tuple[SourceRef, ...]

    @field_validator("part_ids")
    @classmethod
    def unique_parts(cls, value):
        if not value or len(set(value)) != len(value):
            raise ValueError("contract parts must be nonempty and unique")
        return value


class ForecastFact(FrozenModel):
    kind: Literal["forecast"]
    part: _EvidenceId
    period: Annotated[str, AfterValidator(_evidence_month)]
    quantity: Annotated[_EvidenceDecimal, Field(ge=0)] | None = None
    change_pct: Annotated[_EvidenceDecimal, Field(ge=-100)] | None = None


class OrderPriceFact(FrozenModel):
    kind: Literal["order_price"]
    supplier: _EvidenceId
    part: _EvidenceId
    price: Price
    order_date: date
    quantity: Annotated[_EvidenceDecimal, Field(gt=0)] | None = None

    @model_validator(mode="after")
    def part_in_basis(self):
        if self.part not in self.price.basis.part_ids:
            raise ValueError("order part must occur in the price basis")
        return self


class TextRecord(FrozenModel):
    kind: Literal["text"]
    title: _EvidenceLabel
    text: str
    document_kind: _EvidenceLabel
    declared_role: _EvidenceLabel | None = None


class NamedEstimate(FrozenModel):
    name: Literal["full_cost", "interest_rate", "usual_rate", "ppm", "extra_per_unit"]
    value: _EvidenceDecimal
    unit: Literal["EUR_per_price_unit", "fraction", "ppm"]
    range_low: _EvidenceDecimal | None = None
    range_high: _EvidenceDecimal | None = None
    basis: PriceBasis | None = None

    @model_validator(mode="after")
    def registered_units_and_bounds(self):
        expected = {"full_cost": "EUR_per_price_unit", "extra_per_unit": "EUR_per_price_unit",
                    "interest_rate": "fraction", "usual_rate": "fraction", "ppm": "ppm"}
        if self.unit != expected[self.name]:
            raise ValueError("estimate unit must match the registered name")
        if self.unit == "EUR_per_price_unit" and self.basis is None:
            raise ValueError("per-price-unit estimates require a declared basis")
        if (self.range_low is None) != (self.range_high is None):
            raise ValueError("estimate bounds must both be supplied or both absent")
        if self.range_low is not None and not self.range_low <= self.value <= self.range_high:
            raise ValueError("estimate value must lie within its bounds")
        for value in (self.value, self.range_low, self.range_high):
            if value is not None and (
                self.name == "full_cost" and value <= 0
                or self.name not in {"full_cost", "extra_per_unit"} and value < 0
            ):
                raise ValueError("estimate values and bounds must respect the registered domain")
        return self


class EstimateRecord(FrozenModel):
    kind: Literal["estimate"]
    method_id: Literal["fixture-point-v1", "source-cost-v1", "supplier-scenarios-v1"]
    values: tuple[NamedEstimate, ...]
    assumptions: tuple[SourceRef, ...]

    @model_validator(mode="after")
    def nonempty_unique_estimates(self):
        if not self.values or len({value.name for value in self.values}) != len(self.values):
            raise ValueError("estimate values must be nonempty with unique registered names")
        if not self.assumptions:
            raise ValueError("estimate assumptions must cite source or assumption records")
        return self


EvidencePayload = Annotated[
    IndexFact | ScorecardFact | CostFact | QuoteFact | ContractFact | ForecastFact
    | OrderPriceFact | TextRecord | EstimateRecord,
    Field(discriminator="kind"),
]


class EvidenceRecord(FrozenModel):
    record_id: _EvidenceId
    canonical_id: _EvidenceId | None = None
    kind: Literal["canonical", "supplier_statement", "estimate", "hypothesis"]
    payload: EvidencePayload
    scope: EvidenceScope
    provenance: Provenance
    temporal: TemporalValidity
    disclosure: DisclosureRule
    supersedes: _EvidenceId | None = None

    @model_validator(mode="after")
    def evidence_kind_and_scope(self):
        if isinstance(self.payload, EstimateRecord) and self.kind not in {"estimate", "hypothesis"}:
            raise ValueError("estimate payloads remain estimates or hypotheses")
        if self.supersedes == self.record_id:
            raise ValueError("an evidence record cannot supersede itself")
        if isinstance(self.payload, ScorecardFact) and self.scope.level in {"part", "basket"}:
            raise ValueError("supplier scorecards cannot carry part or basket scope")
        return self


class Conflict(FrozenModel):
    canonical_id: _EvidenceId
    candidate_record_ids: tuple[_EvidenceId, ...]
    winning_record_id: _EvidenceId | None = None
    rule_id: _EvidenceId
    blocking: bool
    reason_code: _EvidenceLabel

    @model_validator(mode="after")
    def conflict_membership(self):
        if len(self.candidate_record_ids) < 2 or len(set(self.candidate_record_ids)) != len(self.candidate_record_ids):
            raise ValueError("a conflict needs at least two unique candidates")
        if self.winning_record_id is not None and self.winning_record_id not in self.candidate_record_ids:
            raise ValueError("conflict winner must belong to its candidates")
        if self.blocking and self.winning_record_id is not None:
            raise ValueError("unresolved blocking conflicts cannot declare a winner")
        return self


class RelevanceRecord(FrozenModel):
    record_id: _EvidenceId
    topic: _EvidenceLabel
    reason_code: _EvidenceLabel
    rank: Annotated[int, Field(ge=0)]
    polarity: Literal["supports", "contradicts", "neutral", "unknown"]


class EvidenceContext(FrozenModel):
    context_version: _EvidenceId
    case_id: _EvidenceId
    supplier_ids: tuple[_EvidenceId, ...]
    part_ids: tuple[_EvidenceId, ...]
    as_of: datetime
    prepared_artifact_id: str
    records: tuple[EvidenceRecord, ...]
    conflicts: tuple[Conflict, ...]
    gaps: tuple[Issue, ...]
    relevance: tuple[RelevanceRecord, ...]
    source_versions: tuple[_EvidenceLabel, ...]

    @field_validator("as_of")
    @classmethod
    def utc_as_of(cls, value):
        if value.utcoffset() is None or value.utcoffset() != timedelta(0):
            raise ValueError("evidence context time must be UTC")
        return value

    @field_validator("prepared_artifact_id")
    @classmethod
    def prepared_content_ref(cls, value):
        return _validate_artifact_ref(value)

    @model_validator(mode="after")
    def unique_records_and_relevance(self):
        identities = {record.record_id for record in self.records}
        if len(identities) != len(self.records):
            raise ValueError("context record identities must be unique")
        if any(item.record_id not in identities for item in self.relevance):
            raise ValueError("relevance references must resolve to context records")
        return self


class ResolvedCostInput(FrozenModel):
    unit_cost: Price
    source_refs: tuple[SourceRef, ...]
    scope: EvidenceScope
    temporal: TemporalValidity
    issues: tuple[Issue, ...]

    @field_validator("source_refs")
    @classmethod
    def nonempty_cost_sources(cls, value):
        if not value:
            raise ValueError("cost input requires source revision references")
        return value


class PartIdentity(FrozenModel):
    part_id: _EvidenceId
    price_basis: PriceBasis
    unit_label: _EvidenceLabel | None = None

    @model_validator(mode="after")
    def declared_part(self):
        if self.part_id not in self.price_basis.part_ids:
            raise ValueError("part identity must occur in its price basis")
        return self


def _bound_values(data, info: ValidationInfo, collection: bool):
    if not isinstance(data, dict) or "field" not in data:
        return data
    key = "values" if collection else "value"
    if key not in data:
        return data
    values = data[key] if collection else (data[key],)
    if collection and info.mode != "json" and not isinstance(values, tuple):
        raise ValueError("option values must be tuples")
    converted = []
    for value in values:
        raw = {"field": data["field"], "value": value}
        binding = (TermBinding.model_validate_json(json.dumps(raw)) if info.mode == "json"
                   else TermBinding.model_validate(raw))
        converted.append(binding.value)
    return {**data, key: tuple(converted) if collection else converted[0]}


class TermOption(FrozenModel):
    field: TermField
    values: tuple[TermValue, ...]
    allow_verified_standard: bool

    @model_validator(mode="before")
    @classmethod
    def typed_options(cls, data, info: ValidationInfo):
        return _bound_values(data, info, True)

    @model_validator(mode="after")
    def unique_options(self):
        if not self.values or len({semantic_hash(TermBinding(field=self.field, value=v))
                                   for v in self.values}) != len(self.values):
            raise ValueError("option values must be nonempty and unique")
        return self


class MustHave(FrozenModel):
    field: TermField
    op: Literal["<=", "<", ">=", ">", "==", "!="]
    value: TermValue

    @model_validator(mode="before")
    @classmethod
    def typed_constraint(cls, data, info: ValidationInfo):
        return _bound_values(data, info, False)

    @model_validator(mode="after")
    def ordered_domain(self):
        if self.field in {"incoterm", "index_clause"} and self.op not in {"==", "!="}:
            raise ValueError("ordered comparisons require a numeric or date field")
        return self


class FreightRate(FrozenModel):
    incoterm: Literal["EXW", "FCA", "DAP"]
    eur_per_unit: Annotated[_EvidenceDecimal, Field(ge=0)]


class IndexPath(FrozenModel):
    series: _EvidenceId
    delta_fraction: Annotated[_EvidenceDecimal, Field(ge=-1)]


class FieldOrigin(FrozenModel):
    field: TermField
    source_kind: Literal["sheet", "fixed", "quote", "master", "buyer_default"]
    source_refs: tuple[SourceRef, ...]

    @field_validator("source_refs")
    @classmethod
    def required_origin(cls, value):
        if not value:
            raise ValueError("every field needs a source origin")
        return value


def _check_origins(bindings, origins):
    fields = tuple(t.field for t in bindings)
    origin_fields = tuple(t.field for t in origins)
    if len(set(fields)) != len(fields) or len(set(origin_fields)) != len(origin_fields):
        raise ValueError("term bindings and origins must be unique")
    if set(fields) != set(origin_fields):
        raise ValueError("each term must have exactly one origin")


class ResolvedTerms(FrozenModel):
    bindings: tuple[TermBinding, ...]
    origins: tuple[FieldOrigin, ...]
    version_hash: str

    @model_validator(mode="after")
    def consistent_origins(self):
        _check_origins(self.bindings, self.origins)
        return self


class ResolvedStandards(FrozenModel):
    bindings: tuple[TermBinding, ...]
    field_origins: tuple[FieldOrigin, ...]
    version_hash: str

    @model_validator(mode="after")
    def consistent_origins(self):
        _check_origins(self.bindings, self.field_origins)
        return self


class AvailableAlternative(FrozenModel):
    kind: Literal["available"]
    ref: SourceRef | None = None
    terms: ResolvedTerms
    basis: PriceBasis
    provenance_refs: tuple[SourceRef, ...]

    @model_validator(mode="after")
    def sourced_price(self):
        if not self.provenance_refs or "unit_price" not in {t.field for t in self.terms.bindings}:
            raise ValueError("available alternatives require provenance and a complete priced term set")
        return self


class UnavailableAlternative(FrozenModel):
    kind: Literal["unavailable"]
    reason_code: _EvidenceLabel


ExecutableAlternative = Annotated[AvailableAlternative | UnavailableAlternative, Field(discriminator="kind")]


class BuyerEconomics(FrozenModel):
    category_goal: Literal["routine", "leverage", "quality_first", "stabilise", "secure_supply"]
    need_per_year: Annotated[_EvidenceDecimal, Field(gt=0)]
    horizon_years: Annotated[_EvidenceDecimal, Field(gt=0)]
    current_price: Price | None = None
    fallback_price: Price
    interest_rate: Annotated[_EvidenceDecimal, Field(ge=0)]
    reference_payment_days: Annotated[int, Field(ge=0)]
    need_lead_time_days: Annotated[int, Field(ge=0)]
    fallback_risk_pct: Annotated[_EvidenceDecimal, Field(ge=0)]
    index_risk_pct: Annotated[_EvidenceDecimal, Field(ge=0)]
    late_cost_per_day: Money
    cost_per_defect: Money
    sustainable_margin_pct: _EvidencePercent | None = None
    relationship_eur_per_point: Money | None = None
    freight: tuple[FreightRate, ...]
    index_paths: tuple[IndexPath, ...]
    must_haves: tuple[MustHave, ...]
    alternative: ExecutableAlternative

    @model_validator(mode="after")
    def buyer_domains(self):
        if self.current_price is not None and self.current_price.basis != self.fallback_price.basis:
            raise ValueError("current and fallback prices require the same basis")
        if len(self.freight) != 3 or {x.incoterm for x in self.freight} != {"EXW", "FCA", "DAP"}:
            raise ValueError("freight requires exactly EXW/FCA/DAP")
        if len({x.series for x in self.index_paths}) != len(self.index_paths):
            raise ValueError("index paths must be unique")
        if any(x is not None and x.amount < 0 for x in
               (self.late_cost_per_day, self.cost_per_defect, self.relationship_eur_per_point)):
            raise ValueError("buyer penalties must be nonnegative")
        return self


class CaseContract(FrozenModel):
    case_id: _EvidenceId
    case_type: Literal["capacity", "price_increase", "bundling", "quality", "raw_material", "renewal", "rfq"]
    title: _EvidenceLabel
    supplier_ids: tuple[_EvidenceId, ...]
    parts: tuple[PartIdentity, ...]
    negotiable_fields: tuple[TermField, ...]
    options: tuple[TermOption, ...]
    fixed_terms: tuple[TermBinding, ...]
    buyer: BuyerEconomics
    round_limit: Annotated[int, Field(gt=0)]
    case_facts: tuple[EvidenceRecord, ...]
    refs: tuple[_EvidenceId, ...]
    contract_hash: str

    @model_validator(mode="after")
    def case_domains(self):
        for values in (self.supplier_ids, tuple(p.part_id for p in self.parts), self.negotiable_fields):
            if not values or len(set(values)) != len(values):
                raise ValueError("case suppliers, parts and negotiable fields must be nonempty and unique")
        fixed = tuple(t.field for t in self.fixed_terms)
        options = tuple(t.field for t in self.options)
        if len(set(fixed)) != len(fixed) or len(set(options)) != len(options):
            raise ValueError("fixed and option fields must be unique")
        if set(fixed).intersection(self.negotiable_fields) or not set(options).issubset(self.negotiable_fields):
            raise ValueError("fixed and negotiable fields must be disjoint; options must be negotiable")
        ids = {p.part_id for p in self.parts}
        if any(not set(p.price_basis.part_ids).issubset(ids) for p in self.parts):
            raise ValueError("part bases must name declared case parts")
        if not set(self.buyer.fallback_price.basis.part_ids).issubset(ids):
            raise ValueError("buyer price basis must name declared case parts")
        return self


class SupplierEstimate(FrozenModel):
    estimate_id: _EvidenceId
    supplier_id: _EvidenceId
    basis: PriceBasis
    full_cost: Price
    full_cost_low: Price
    full_cost_high: Price
    interest_rate: Annotated[_EvidenceDecimal, Field(ge=0)]
    usual_rate: Annotated[_EvidenceDecimal, Field(ge=0)]
    ppm: Annotated[int, Field(ge=0)] | None = None
    standard: ResolvedStandards
    assumption_refs: tuple[SourceRef, ...]
    method_id: _EvidenceId
    uncertainty_kind: Literal["scenario_range", "calibrated_interval", "unknown"]
    extra_per_unit: _EvidenceDecimal | None = None

    @model_validator(mode="after")
    def estimate_domains(self):
        if any(p.basis != self.basis for p in (self.full_cost, self.full_cost_low, self.full_cost_high)):
            raise ValueError("supplier estimate prices require one basis")
        if not self.full_cost_low.amount <= self.full_cost.amount <= self.full_cost_high.amount:
            raise ValueError("supplier full cost must lie in the declared range")
        if not self.assumption_refs:
            raise ValueError("supplier estimates require assumption/source references")
        return self


_CostKind = Literal["price", "uncovered_need", "fallback_risk", "payment_terms", "freight",
                    "late_delivery", "quality", "tooling", "index_clause", "index_risk", "relationship"]


class CostComponent(FrozenModel):
    kind: _CostKind
    amount: Money


class OfficialCostResult(FrozenModel):
    total: Money
    components: tuple[CostComponent, ...]

    @model_validator(mode="after")
    def component_parity(self):
        from decimal import ROUND_HALF_EVEN, localcontext
        from typing import get_args

        if len(self.components) != 11 or {c.kind for c in self.components} != set(get_args(_CostKind)):
            raise ValueError("official result requires all eleven unique cost components")
        with localcontext() as ctx:
            ctx.prec = max(50, sum(len(c.amount.amount.as_tuple().digits) for c in self.components) + 10)
            total = sum((c.amount.amount for c in self.components), Decimal(0)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN,
            )
        if total != self.total.amount:
            raise ValueError("official result must match the cent-rounded component sum")
        return self


class SupplierStandards(FrozenModel):
    supplier_id: _EvidenceId
    standards: ResolvedStandards


class EstimateScenario(FrozenModel):
    scenario_id: _EvidenceId
    estimate_ids: tuple[_EvidenceId, ...]

    @model_validator(mode="after")
    def unique_estimates(self):
        if not self.estimate_ids or len(set(self.estimate_ids)) != len(self.estimate_ids):
            raise ValueError("scenario requires nonempty unique estimates")
        return self


class ScenarioPolicy(FrozenModel):
    mode: Literal["disabled_explicit", "nominal_explicit", "robust_scenarios"]
    scenarios: tuple[EstimateScenario, ...]
    required_supplier_ids: tuple[_EvidenceId, ...]

    @model_validator(mode="after")
    def policy_domains(self):
        if len({s.scenario_id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("scenario IDs must be unique")
        if len(set(self.required_supplier_ids)) != len(self.required_supplier_ids):
            raise ValueError("required suppliers must be unique")
        if self.mode == "disabled_explicit":
            if self.scenarios or self.required_supplier_ids:
                raise ValueError("disabled estimates require empty scenarios/suppliers")
        elif not self.required_supplier_ids or not self.scenarios or (
            self.mode == "nominal_explicit" and len(self.scenarios) != 1
        ):
            raise ValueError("enabled policy requires suppliers and the declared scenario count")
        return self


class PriceInterval(FrozenModel):
    minimum: Price
    maximum: Price

    @model_validator(mode="after")
    def interval_domain(self):
        if self.minimum.basis != self.maximum.basis or self.minimum.amount > self.maximum.amount:
            raise ValueError("price interval requires matching basis and ordered bounds")
        return self


class CostPolicy(FrozenModel):
    policy_id: _EvidenceId
    comparison: Literal["nominal", "robust_scenarios"]
    ceiling: Money | None = None
    price_bounds: PriceInterval
    tick: Annotated[_EvidenceDecimal, Field(gt=0)]
    fallback_rule: Literal["preserve_baseline_if_feasible"]
    alternative_rule: Literal["compare_executable_else_no_deal_score"]

    @model_validator(mode="after")
    def policy_domain(self):
        if self.tick != Decimal("0.01") or self.ceiling is not None and self.ceiling.amount < 0:
            raise ValueError("v1 requires cent tick and nonnegative ceiling")
        return self


class EconomicContext(FrozenModel):
    case: CaseContract
    standards_by_supplier: tuple[SupplierStandards, ...]
    estimates: tuple[SupplierEstimate, ...]
    scenario_policy: ScenarioPolicy
    cost_policy: CostPolicy
    fingerprint: str
    issues: tuple[Issue, ...]

    @model_validator(mode="after")
    def economic_joins(self):
        keys = [s.supplier_id for s in self.standards_by_supplier]
        ids = [e.estimate_id for e in self.estimates]
        if len(set(keys)) != len(keys) or not set(keys).issubset(self.case.supplier_ids):
            raise ValueError("standards require unique case supplier keys")
        if len(set(ids)) != len(ids):
            raise ValueError("estimate IDs must be unique")
        basis = self.case.buyer.fallback_price.basis
        for e in self.estimates:
            if e.supplier_id not in self.case.supplier_ids or e.basis != basis:
                raise ValueError("estimate supplier/basis must join the case")
        policy = self.scenario_policy
        if policy.mode == "disabled_explicit" and self.estimates:
            raise ValueError("disabled policy has no estimates")
        if (self.cost_policy.comparison == "robust_scenarios") != (policy.mode == "robust_scenarios"):
            raise ValueError("robust comparison requires robust scenario mode")
        if not set(policy.required_supplier_ids).issubset(self.case.supplier_ids):
            raise ValueError("required suppliers must belong to case")
        by_id = {e.estimate_id: e for e in self.estimates}
        for scenario in policy.scenarios:
            if not set(scenario.estimate_ids).issubset(by_id):
                raise ValueError("scenario estimate refs must resolve")
            suppliers = [by_id[i].supplier_id for i in scenario.estimate_ids]
            if len(set(suppliers)) != len(suppliers) or set(suppliers) != set(policy.required_supplier_ids):
                raise ValueError("scenario must cover required suppliers exactly once")
        return self


class ScenarioCost(FrozenModel):
    scenario_id: _EvidenceId
    estimate_id: _EvidenceId | None = None
    cost: Money
    supplier_value: Price | None = None
    margin_pct: _EvidenceDecimal | None = None
    components: tuple[CostComponent, ...]

    @model_validator(mode="after")
    def scenario_parity(self):
        if len({c.kind for c in self.components}) != len(self.components):
            raise ValueError("scenario components must be unique")
        if self.components:
            from decimal import ROUND_HALF_EVEN
            if sum((c.amount.amount for c in self.components), Decimal(0)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN,
            ) != self.cost.amount:
                raise ValueError("scenario components must sum to rounded cost")
        return self


class PackageEvaluation(FrozenModel):
    package_fingerprint: str
    resolved_terms: ResolvedTerms
    nominal_cost: Money | None = None
    components: tuple[CostComponent, ...]
    scenario_costs: tuple[ScenarioCost, ...]
    must_haves_ok: bool
    numerically_valid: bool
    basis_verified: bool
    assumption_refs: tuple[SourceRef, ...]
    economic_fingerprint: str
    issues: tuple[Issue, ...]

    @model_validator(mode="after")
    def evaluation_domain(self):
        if self.numerically_valid:
            if self.nominal_cost is None:
                raise ValueError("valid numerical result requires cost")
            OfficialCostResult(total=self.nominal_cost, components=self.components)
        elif self.nominal_cost is not None or self.components or self.scenario_costs or not any(
            i.code == "nonfinite_cost" and i.severity == "error" for i in self.issues
        ):
            raise ValueError("numeric failure requires empty costs and nonfinite_cost error")
        if len({s.scenario_id for s in self.scenario_costs}) != len(self.scenario_costs):
            raise ValueError("scenario cost IDs must be unique")
        return self


# Contracts consumed by the finite candidate/used-action boundary.
def _slice_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return value


class _BoundaryModel(FrozenModel):
    @model_validator(mode="after")
    def boundary_invariants(self):
        _boundary_invariants(self)
        return self


class StrategyIntent(_BoundaryModel):
    intent_id: _EvidenceId
    strategy_id: _EvidenceId
    supplier_id: _EvidenceId
    snapshot: SnapshotRef
    kind: Literal['keep', 'exchange', 'evidence_challenge', 'clarify', 'request_close', 'propose_package']
    dimension: TermField | None = None
    direction: Literal['increase', 'decrease', 'enumerate', 'unchanged']
    observation_refs: tuple[_EvidenceId, ...]
    evidence_refs: tuple[SourceRef, ...]
    question_id: _EvidenceId | None = None
    rationale: Annotated[_EvidenceLabel, Field(max_length=1000)]
    supersedes_refusal_id: _EvidenceId | None = None
    proposed_bindings: tuple[TermBinding, ...] = ()
    proposal_citations: tuple[MessageSpan, ...] = ()

    @model_serializer(mode="wrap")
    def preserve_historic_intent(self, handler):
        result = handler(self)
        for key in ("proposed_bindings", "proposal_citations"):
            if key not in self.model_fields_set:
                result.pop(key, None)
        return result


class OfferAction(_BoundaryModel):
    kind: Literal['offer']
    packages: tuple[Package, ...]
    claim_ids: tuple[_EvidenceId, ...]
    question_id: _EvidenceId | None = None


class QuestionAction(_BoundaryModel):
    kind: Literal['question']
    question_id: _EvidenceId
    claim_ids: tuple[_EvidenceId, ...] = ()


class CloseRequest(_BoundaryModel):
    kind: Literal['request_close']
    reason_code: _EvidenceLabel


CandidateContents = Annotated[OfferAction | QuestionAction | CloseRequest, Field(discriminator='kind')]


class CandidateAction(_BoundaryModel):
    candidate_id: _EvidenceId
    intent_id: _EvidenceId
    supplier_id: _EvidenceId
    snapshot: SnapshotRef
    contents: CandidateContents
    construction_refs: tuple[_EvidenceId, ...]
    candidate_builder_id: _EvidenceId


class GenerationResult(_BoundaryModel):
    intent_id: _EvidenceId
    candidates: tuple[CandidateAction, ...]
    rejections: tuple[Issue, ...]
    search_scope: Literal['finite', 'proven_monotonic', 'bounded_scan']
    search_complete: bool


class EvaluatedCandidate(_BoundaryModel):
    evaluation_id: _EvidenceId
    candidate: CandidateAction
    disposition: Literal['approved', 'rejected']
    economic: tuple[PackageEvaluation, ...]
    issues: tuple[Issue, ...]


class EvaluationBatch(_BoundaryModel):
    snapshot: SnapshotRef
    items: tuple[EvaluatedCandidate, ...]
    issues: tuple[Issue, ...]
    batch_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class NegotiationDecision(_BoundaryModel):
    decision_id: UUID
    snapshot: SnapshotRef
    candidate_id: _EvidenceId
    evaluation_id: _EvidenceId
    approved_batch_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    selector_id: _EvidenceId
    rationale: Annotated[_EvidenceLabel, Field(max_length=1000)]
    citations: tuple[Citation, ...]
    fallback_code: _EvidenceLabel | None = None


class ObservedSheet(_BoundaryModel):
    offer_id: _EvidenceId | None = None
    bindings: tuple[TermBinding, ...]
    complete_bindings: tuple[TermBinding, ...] = ()
    source_message_ref: MessageSpan
    standing: bool
    parse_issues: tuple[Issue, ...]


class DocumentRecord(_BoundaryModel):
    attachment_id: _EvidenceId
    name: _EvidenceLabel
    media_type: _EvidenceLabel
    bytes_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    text_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None
    text: str | None = None
    structured_refs: tuple[SourceRef, ...]
    parse_status: Literal['ok', 'partial', 'unsupported', 'failed']
    issues: tuple[Issue, ...]


class ClaimCheckResult(_BoundaryModel):
    argument_index: Annotated[int, Field(ge=0)]
    result: Literal['verified', 'contradicted', 'irrelevant', 'duplicate', 'unknown']
    source_message_ref: MessageSpan


class ConversationMessage(_BoundaryModel):
    session_id: _EvidenceId
    thread_id: _EvidenceId
    message_id: _EvidenceId
    speaker: Literal['buyer', 'supplier', 'arena']
    supplier_id: _EvidenceId
    role: _EvidenceLabel | None = None
    from_name: _EvidenceLabel | None = None
    body: str
    observed_sheets: tuple[ObservedSheet, ...]
    attachments: tuple[DocumentRecord, ...]
    claim_results: tuple[ClaimCheckResult, ...]
    server_at: Annotated[datetime, AfterValidator(_slice_utc)] | None = None
    received_at: Annotated[datetime, AfterValidator(_slice_utc)]
    in_reply_to: _EvidenceId | None = None
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ConversationView(_BoundaryModel):
    status: Literal["open", "final_offer", "agreed", "walked_away", "no_bid"] = "open"
    session_id: _EvidenceId
    thread_id: _EvidenceId
    messages: tuple[ConversationMessage, ...]
    version_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ClockEvidence(_BoundaryModel):
    server_deadline_at: Annotated[datetime, AfterValidator(_slice_utc)] | None = None
    seconds_left: Annotated[_EvidenceDecimal, Field(ge=0)] | None = None
    snapshot_requested_at: Annotated[datetime, AfterValidator(_slice_utc)]
    snapshot_received_at: Annotated[datetime, AfterValidator(_slice_utc)]
    server_at: Annotated[datetime, AfterValidator(_slice_utc)] | None = None
    kind: Literal['thread', 'wave']
    source_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    conservative_deadline_at: Annotated[datetime, AfterValidator(_slice_utc)] | None = None
    confidence: Literal['authoritative', 'conservative', 'unknown']


class RoundEvidence(_BoundaryModel):
    limit: Annotated[int, Field(gt=0)]
    server_rounds_used: Annotated[int, Field(ge=0)] | None = None
    accepted_buyer_messages: Annotated[int, Field(ge=0)]
    timeout_rounds: Annotated[int, Field(ge=0)] | None = None
    conservative_remaining: Annotated[int, Field(ge=0)] | None = None
    source_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    confidence: Literal['authoritative', 'conservative', 'unknown']


class TerminalEvidence(_BoundaryModel):
    session_id: _EvidenceId
    status: Literal['ended']
    proof_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    source_kind: Literal['gateway_response', 'gateway_observation']
    observed_at: Annotated[datetime, AfterValidator(_slice_utc)]
    deal: bool | None = None
    offer_id: _EvidenceId | None = None
    supplier_id: _EvidenceId | None = None
    score: _EvidenceDecimal | None = None
    cost: Money | None = None
    end_reason: _EvidenceLabel | None = None


class ServerThread(_BoundaryModel):
    thread_id: _EvidenceId
    supplier_id: _EvidenceId
    status: Literal['open', 'final_offer', 'agreed', 'walked_away', 'no_bid']
    standing_offer_id: _EvidenceId | None = None
    conversation: ConversationView
    rounds: RoundEvidence
    clock: ClockEvidence
    standards: ResolvedStandards
    closed_reason: _EvidenceLabel | None = None


class ServerState(_BoundaryModel):
    session_id: _EvidenceId
    case_id: _EvidenceId
    status: Literal['open', 'ended', 'unknown']
    threads: tuple[ServerThread, ...]
    wave_clock: ClockEvidence | None = None
    terminal: TerminalEvidence | None = None
    observed_at: Annotated[datetime, AfterValidator(_slice_utc)]
    observation_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AcceptPayload(_BoundaryModel):
    type: Literal['accept']
    term_sheet_id: _EvidenceId


class WalkPayload(_BoundaryModel):
    type: Literal['walk_away']


class OutboundAttachment(_BoundaryModel):
    name: _EvidenceLabel
    media_type: _EvidenceLabel
    content_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    disclosure: DisclosureRule


WireAction = Annotated[AcceptPayload | WalkPayload, Field(discriminator='type')]


class MessagePayload(_BoundaryModel):
    subject: str
    body: str
    packages: tuple[Package, ...]
    refs: tuple[_EvidenceId, ...]
    action: WireAction | None = None
    attachments: tuple[OutboundAttachment, ...]


class RenderedAction(_BoundaryModel):
    decision_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None
    close_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None
    snapshot: SnapshotRef
    supplier_id: _EvidenceId
    kind: Literal['offer', 'question', 'accept', 'walk_away']
    payload: MessagePayload
    claim_ids: tuple[_EvidenceId, ...]
    template_version: _EvidenceId
    render_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class CheckOutcome(_BoundaryModel):
    check_id: _EvidenceId
    passed: bool
    refs: tuple[Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...]
    detail_code: _EvidenceLabel


class ValidationReport(_BoundaryModel):
    check_version: _EvidenceId
    snapshot: SnapshotRef
    checks: tuple[CheckOutcome, ...]
    issues: tuple[Issue, ...]


class ValidatedAction(_BoundaryModel):
    rendered: RenderedAction
    report: ValidationReport
    payload_bytes_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    payload_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    economic_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    expires_at: Annotated[datetime, AfterValidator(_slice_utc)]
    validator_version: _EvidenceId


class ValidActionResult(_BoundaryModel):
    kind: Literal['valid']
    action: ValidatedAction


class InvalidActionResult(_BoundaryModel):
    kind: Literal['invalid']
    report: ValidationReport


class DecisionBudget(_BoundaryModel):
    deadline_at: Annotated[datetime, AfterValidator(_slice_utc)]
    compute_limit_s: Annotated[_EvidenceDecimal, Field(gt=0)]
    model_call_limit: Annotated[int, Field(ge=0)]
    model_time_limit_s: Annotated[_EvidenceDecimal, Field(gt=0)]
    candidate_limit: Annotated[int, Field(gt=0)]
    fallback_reserve_s: Annotated[_EvidenceDecimal, Field(ge=0)]
    submission_reserve_s: Annotated[_EvidenceDecimal, Field(ge=0)]
    clock_refs: tuple[Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...]


class PendingOperation(_BoundaryModel):
    operation_id: UUID
    kind: Literal['open', 'send', 'close']
    case_id: _EvidenceId
    session_id: _EvidenceId | None = None
    supplier_id: _EvidenceId | None = None
    endpoint_kind: Literal['open_case', 'send_message', 'close_session']
    payload_bytes_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    payload_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    validation_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None
    source_state_version: Annotated[int, Field(ge=0)]
    commit_state_version: Annotated[int, Field(ge=0)]
    created_at: Annotated[datetime, AfterValidator(_slice_utc)]
    submitted_at: Annotated[datetime, AfterValidator(_slice_utc)] | None = None
    status: Literal['prepared', 'submitted', 'acknowledged', 'rejected', 'uncertain']
    response_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None
    attempt_count: Annotated[int, Field(ge=0)]


class StrategyAttempt(_BoundaryModel):
    attempt_id: UUID
    intent_id: _EvidenceId
    candidate_id: _EvidenceId
    package_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    operation_id: UUID
    status: Literal['prepared', 'submitted', 'acknowledged', 'rejected', 'uncertain']
    response_refs: tuple[Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...]


class RefusedExchange(_BoundaryModel):
    refusal_id: _EvidenceId
    supplier_id: _EvidenceId
    dimension: TermField | None = None
    package_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    attempt_refs: tuple[UUID, ...]
    citations: tuple[Citation, ...]
    scope: Literal['package', 'dimension', 'conditional', 'unknown']
    assessment_id: _EvidenceId


class ClaimUsage(_BoundaryModel):
    claim_id: _EvidenceId
    canonical_ids: tuple[_EvidenceId, ...]
    scope_key: _EvidenceId
    operation_id: UUID
    status: Literal['reserved', 'sent', 'unknown', 'released']
    recipient_id: _EvidenceId


class OutstandingQuestion(_BoundaryModel):
    question_id: _EvidenceId
    operation_id: UUID
    status: Literal['submitted', 'answered', 'ambiguous']
    response_refs: tuple[Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...]


class StrategyMemory(_BoundaryModel):
    strategy_id: _EvidenceId
    record_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    parent_ref: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")] | None = None
    payload_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class PackageChange(_BoundaryModel):
    field: TermField
    before: TermBinding | None = None
    after: TermBinding | None = None
    source_refs: tuple[Citation, ...]


class ClaimAttribution(_BoundaryModel):
    claim_id: _EvidenceId | None = None
    argument_index: Annotated[int, Field(ge=0)] | None = None
    result: Literal['verified', 'contradicted', 'irrelevant', 'duplicate', 'unknown']
    citations: tuple[Citation, ...]


class HypothesisSupport(_BoundaryModel):
    hypothesis_id: _EvidenceId
    relation: Literal['supports', 'contradicts', 'unknown']
    citations: tuple[Citation, ...]


class QuestionUpdate(_BoundaryModel):
    question_id: _EvidenceId
    status: Literal['answered', 'ambiguous']
    citations: tuple[Citation, ...]


class FeedbackObservation(_BoundaryModel):
    operation_id: UUID
    decision_id: UUID
    response_refs: tuple[Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...]
    package_changes: tuple[PackageChange, ...]
    claim_attributions: tuple[ClaimAttribution, ...]
    hypothesis_support: tuple[HypothesisSupport, ...]
    question_updates: tuple[QuestionUpdate, ...]
    issues: tuple[Issue, ...]
    causality_status: Literal['observed_sequence']


class StrategicState(_BoundaryModel):
    assessments: tuple[SupplierAssessment, ...]
    attempts: tuple[StrategyAttempt, ...]
    refusals: tuple[RefusedExchange, ...]
    claim_usage: tuple[ClaimUsage, ...]
    outstanding_questions: tuple[OutstandingQuestion, ...]
    feedback: tuple[FeedbackObservation, ...]
    memory: tuple[StrategyMemory, ...]


class NegotiationState(_BoundaryModel):
    run_id: _EvidenceId
    attempt_id: UUID
    case: CaseContract
    server: ServerState | None = None
    strategic: StrategicState
    operations: tuple[PendingOperation, ...]
    version: Annotated[int, Field(ge=0)]
    config_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    runtime_status: Literal['ready', 'deciding', 'awaiting', 'recovery_required', 'ended']
    issues: tuple[Issue, ...]


class NegotiationContext(_BoundaryModel):
    snapshot: SnapshotRef
    case: CaseContract
    evidence: EvidenceContext
    economic: EconomicContext
    capabilities: tuple[_EvidenceId, ...]
    as_of: Annotated[datetime, AfterValidator(_slice_utc)]


ValidationResult = Annotated[ValidActionResult | InvalidActionResult, Field(discriminator='kind')]


def _boundary_invariants(v):
    """Shape and cross-field checks; hashes/capability issuance belong to services."""
    name = type(v).__name__

    def require(condition):
        if not condition:
            raise ValueError(f"{name} violates its boundary contract")

    def unique(items):
        require(len(items) == len(set(items)))

    def errors(issues):
        return any(i.severity == "error" for i in issues)

    if name == "StrategyIntent":
        require(bool(v.proposed_bindings) == (v.kind == "propose_package"))
        if v.kind == "propose_package":
            require(v.direction == "enumerate" and v.dimension is None)
            unique(tuple(t.field for t in v.proposed_bindings))
        else:
            require(not v.proposal_citations)
        require((v.kind == "clarify") == (v.question_id is not None))
        if v.kind in ("keep", "request_close"):
            require(v.direction == "unchanged")
        if v.kind == "exchange":
            require(v.dimension is not None and v.direction != "unchanged"
                    and bool(v.observation_refs or v.evidence_refs))
        if v.kind == "evidence_challenge":
            require(bool(v.evidence_refs))
    if name in ("OfferAction", "QuestionAction", "RenderedAction"):
        require(len(v.claim_ids) <= 3)
        unique(v.claim_ids)
    if name == "OfferAction":
        require(1 <= len(v.packages) <= 3)
        unique(tuple(p.fingerprint for p in v.packages))
    if name == "GenerationResult":
        unique(tuple(c.candidate_id for c in v.candidates))
        require(all(c.intent_id == v.intent_id for c in v.candidates))
        require(bool(v.candidates) or any(i.severity == "error" and i.code in ("infeasible", "unsupported_capability")
                                        for i in v.rejections))
    if name == "EvaluatedCandidate":
        if v.candidate.contents.kind == "offer":
            require(tuple(e.package_fingerprint for e in v.economic) ==
                    tuple(p.fingerprint for p in v.candidate.contents.packages))
        else:
            require(not v.economic)
        if v.disposition == "approved":
            require(not errors(v.issues) and all(e.numerically_valid and e.basis_verified and e.must_haves_ok
                                               and not errors(e.issues) for e in v.economic))
        else:
            require(errors(v.issues))
    if name == "EvaluationBatch":
        unique(tuple(i.candidate.candidate_id for i in v.items))
        unique(tuple(i.evaluation_id for i in v.items))
        require(all(i.candidate.snapshot == v.snapshot for i in v.items))
    if name == "ObservedSheet":
        unique(tuple(t.field for t in v.bindings))
    if name == "DocumentRecord":
        if v.parse_status != "ok":
            require(bool(v.issues))
        if v.text is not None:
            require(v.text_ref == "sha256:" + hashlib.sha256(v.text.encode()).hexdigest())
    if name == "ConversationMessage":
        require(all(s.source_message_ref.session_id == v.session_id and
                    s.source_message_ref.thread_id == v.thread_id and
                    s.source_message_ref.message_id == v.message_id for s in v.observed_sheets))
        require(all(r.source_message_ref.session_id == v.session_id and
                    r.source_message_ref.thread_id == v.thread_id and
                    r.source_message_ref.message_id == v.message_id for r in v.claim_results))
    if name == "ConversationView":
        unique(tuple(m.message_id for m in v.messages))
        require(all(m.session_id == v.session_id and m.thread_id == v.thread_id for m in v.messages))
    if name == "ClockEvidence":
        require(v.snapshot_received_at >= v.snapshot_requested_at)
        if v.confidence == "authoritative":
            require(v.server_deadline_at is not None or v.seconds_left is not None)
        if v.confidence == "conservative":
            require(v.conservative_deadline_at is not None)
    if name == "RoundEvidence":
        require(all(x is None or x <= v.limit for x in (v.server_rounds_used, v.accepted_buyer_messages,
                                                      v.timeout_rounds, v.conservative_remaining)))
        require(v.confidence != "authoritative" or v.server_rounds_used is not None)
    if name == "TerminalEvidence" and v.deal is True:
        require(v.offer_id is not None and v.supplier_id is not None)
    if name == "ServerThread":
        require(v.thread_id == v.conversation.thread_id)
        require(all(m.supplier_id == v.supplier_id for m in v.conversation.messages))
    if name == "ServerState":
        unique(tuple(t.thread_id for t in v.threads))
        unique(tuple(t.supplier_id for t in v.threads))
        require(all(t.conversation.session_id == v.session_id for t in v.threads))
        require((v.status == "ended") == (v.terminal is not None))
        require(v.terminal is None or v.terminal.session_id == v.session_id)
    if name == "OutboundAttachment":
        require(v.content_ref == "sha256:" + v.hash)
    if name == "MessagePayload":
        require(len(v.subject) <= 300 and len(v.body) <= 8000 and len(v.packages) <= 3
                and len(v.refs) <= 20 and len(v.attachments) <= 5 and not (v.packages and v.action))
    if name == "RenderedAction":
        close = v.kind in ("accept", "walk_away")
        require((v.close_ref is not None) == close and (v.decision_ref is not None) != (v.close_ref is not None))
        require(bool(v.payload.packages) == (v.kind == "offer"))
        require((v.payload.action is not None) == close)
        require(not close or v.payload.action.type == v.kind)
    if name == "ValidationReport":
        unique(tuple(c.check_id for c in v.checks))
        require(all(c.passed for c in v.checks) or errors(v.issues))
    if name == "ValidatedAction":
        require(v.rendered.snapshot == v.report.snapshot and bool(v.report.checks)
                and all(c.passed for c in v.report.checks) and not errors(v.report.issues)
                and v.payload_bytes_ref == "sha256:" + v.payload_hash)
    if name == "InvalidActionResult":
        require(errors(v.report.issues))
    if name == "DecisionBudget":
        require(v.model_call_limit <= 2 and v.fallback_reserve_s + v.submission_reserve_s <= v.compute_limit_s)
    if name == "PendingOperation":
        require(v.commit_state_version == v.source_state_version + 1 and
                v.payload_bytes_ref == "sha256:" + v.payload_hash)
        require(v.endpoint_kind == {"open": "open_case", "send": "send_message", "close": "close_session"}[v.kind])
        require(all(x is None for x in (v.session_id, v.supplier_id, v.validation_ref)) if v.kind == "open"
                else all(x is not None for x in (v.session_id, v.supplier_id, v.validation_ref)))
        require(v.submitted_at is None or v.submitted_at >= v.created_at)
        if v.status in ("submitted", "acknowledged"):
            require(v.submitted_at is not None and v.attempt_count >= 1)
        if v.status in ("acknowledged", "rejected"):
            require(v.response_ref is not None)
    if name == "StrategyAttempt" and v.status in ("acknowledged", "rejected"):
        require(bool(v.response_refs))
    if name in ("RefusedExchange", "ClaimAttribution", "HypothesisSupport", "QuestionUpdate"):
        require(bool(v.citations))
    if name == "RefusedExchange":
        require(v.scope != "package" or v.package_fingerprint is not None)
        require(v.scope != "dimension" or v.dimension is not None)
    if name == "ClaimUsage":
        unique(v.canonical_ids)
    if name == "OutstandingQuestion" and v.status in ("answered", "ambiguous"):
        require(bool(v.response_refs))
    if name == "StrategyMemory":
        require(v.record_ref == "sha256:" + v.payload_hash)
    if name == "PackageChange":
        require(v.before is not None or v.after is not None)
        require(all(b is None or b.field == v.field for b in (v.before, v.after)))
        require(v.before is None or v.after is None or v.before.value != v.after.value)
    if name == "FeedbackObservation":
        require(bool(v.response_refs))
        unique(tuple(c.field for c in v.package_changes))
        unique(tuple(q.question_id for q in v.question_updates))
    if name == "StrategicState":
        for items, key in ((v.assessments, "assessment_id"), (v.attempts, "attempt_id"),
                           (v.refusals, "refusal_id"), (v.outstanding_questions, "question_id"),
                           (v.memory, "record_ref")):
            unique(tuple(getattr(x, key) for x in items))
    if name == "NegotiationState":
        pending = tuple(o for o in v.operations if o.status in ("prepared", "submitted", "uncertain"))
        require(len(pending) <= 1 and all(o.case_id == v.case.case_id for o in v.operations))
        require(v.server is not None or v.runtime_status in ("ready", "awaiting", "recovery_required"))
        require((v.runtime_status == "ended") == (v.server is not None and v.server.status == "ended"))
        require(v.runtime_status != "awaiting" or bool(pending))
        if v.server:
            require(v.server.case_id == v.case.case_id)
            require(all(o.session_id is None or o.session_id == v.server.session_id for o in v.operations))
    if name == "NegotiationContext":
        require(v.case == v.economic.case and v.snapshot.case_contract_hash == v.case.contract_hash
                and v.evidence.case_id == v.case.case_id and v.snapshot.context_version == v.evidence.context_version)
        require(set(v.evidence.supplier_ids) <= set(v.case.supplier_ids) and
                set(v.evidence.part_ids) <= {p.part_id for p in v.case.parts})


class IntentBatch(FrozenModel):
    snapshot: SnapshotRef
    intents: tuple[StrategyIntent, ...]
    issues: tuple[Issue, ...]

    @model_validator(mode="after")
    def consistent_intents(self):
        if (len({i.intent_id for i in self.intents}) != len(self.intents)
                or any(i.snapshot != self.snapshot for i in self.intents)):
            raise ValueError("intent batch must have unique IDs and matching snapshots")
        return self


class FileDigest(FrozenModel):
    path: _EvidenceId
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    byte_length: Annotated[int, Field(ge=0)]

    @field_validator("path")
    @classmethod
    def relative_source_path(cls, value):
        if value.startswith("/") or "\\" in value or "\x00" in value or any(
            part in ("", ".", "..") for part in value.split("/")
        ):
            raise ValueError("source path must be relative POSIX without traversal")
        return value


class SourceManifest(FrozenModel):
    source_id: _EvidenceId
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    files: tuple[FileDigest, ...]
    data_as_of: date | None = None
    declared_version: _EvidenceLabel | None = None

    @model_validator(mode="after")
    def unique_paths(self):
        if len({f.path for f in self.files}) != len(self.files):
            raise ValueError("duplicate source paths")
        return self


class ScopeIndex(FrozenModel):
    kind: Literal["supplier", "part", "canonical_id"]
    key: _EvidenceId
    record_ids: tuple[_EvidenceId, ...]

    @model_validator(mode="after")
    def unique_records(self):
        if len(set(self.record_ids)) != len(self.record_ids):
            raise ValueError("duplicate index record IDs")
        return self


class PreparedEvidence(FrozenModel):
    artifact_id: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    base_manifest: SourceManifest
    release_manifest: SourceManifest | None = None
    parser_versions: tuple[_EvidenceLabel, ...]
    records: tuple[EvidenceRecord, ...]
    indexes: tuple[ScopeIndex, ...]
    prepared_at: Annotated[datetime, AfterValidator(_slice_utc)]
    integrity_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @model_validator(mode="after")
    def preparation_links(self):
        ids = {r.record_id for r in self.records}
        if len(ids) != len(self.records) or len(set(self.parser_versions)) != len(self.parser_versions):
            raise ValueError("duplicate preparation record/parser IDs")
        if len({(i.kind, i.key) for i in self.indexes}) != len(self.indexes):
            raise ValueError("duplicate scope indexes")
        if any(not set(i.record_ids) <= ids for i in self.indexes):
            raise ValueError("scope index references absent records")
        return self


class DecisionSnapshot(FrozenModel):
    context: NegotiationContext
    state: NegotiationState
    target_supplier_id: _EvidenceId
    conversation: ConversationView
    budget: DecisionBudget

    @model_validator(mode="after")
    def consistent_snapshot(self):
        ref = self.context.snapshot
        state = self.state
        server = state.server
        if (server is None or server.status != "open" or state.case != self.context.case
                or state.run_id != ref.run_id
                or state.config_hash != ref.config_hash or server.session_id != ref.session_id
                or self.target_supplier_id not in state.case.supplier_ids):
            raise ValueError("decision requires a consistent identified open session")
        thread = next((t for t in server.threads if t.supplier_id == self.target_supplier_id), None)
        if (thread is None or thread.status not in ("open", "final_offer", "agreed")
                or self.conversation != thread.conversation or self.conversation.session_id != ref.session_id):
            raise ValueError("decision conversation must match its target server thread")
        return self


class SelectedOutcome(FrozenModel):
    kind: Literal["selected"]
    decision: NegotiationDecision


class RequestCloseOutcome(FrozenModel):
    kind: Literal["request_close"]
    reason_code: _EvidenceLabel
    snapshot: SnapshotRef


class HoldOutcome(FrozenModel):
    kind: Literal["hold"]
    reason_code: _EvidenceLabel
    recheck_at: Annotated[datetime, AfterValidator(_slice_utc)]
    snapshot: SnapshotRef


class CannotDecideOutcome(FrozenModel):
    kind: Literal["cannot_decide"]
    issues: tuple[Issue, ...]
    snapshot: SnapshotRef

    @model_validator(mode="after")
    def error_required(self):
        if not any(i.severity == "error" for i in self.issues):
            raise ValueError("cannot-decide requires an error issue")
        return self


DecisionOutcome = Annotated[
    SelectedOutcome | RequestCloseOutcome | HoldOutcome | CannotDecideOutcome, Field(discriminator="kind"),
]


class InterpretInput(FrozenModel):
    kind: Literal["interpret"]
    snapshot: SnapshotRef
    supplier_id: _EvidenceId
    conversation: ConversationView
    evidence: tuple[EvidenceRecord, ...]
    previous: SupplierAssessment | None = None
    citation_catalog: tuple[tuple[str, MessageSpan], ...] = ()

    @field_validator("citation_catalog", mode="before")
    @classmethod
    def freeze_catalog(cls, value):
        return tuple(value.items()) if isinstance(value, dict) else value

    @field_serializer("citation_catalog", when_used="json")
    def catalog_json(self, value) -> dict[str, MessageSpan]:
        # Preserve the versioned wire mapping while keeping runtime DTOs immutable.
        return dict(value)

    thread_status: str | None = None


class SelectionOption(FrozenModel):
    candidate_id: _EvidenceId
    evaluation_id: _EvidenceId
    summary: _EvidenceLabel
    citations: tuple[Citation, ...]


class SelectInput(FrozenModel):
    kind: Literal["select"]
    snapshot: SnapshotRef
    approved_batch_hash: str
    options: tuple[SelectionOption, ...]
    assessment: SupplierAssessment
    conversation: ConversationView | None = None
    thread_status: str | None = None

    @model_validator(mode="after")
    def unique_options(self):
        if (not self.options or len({o.candidate_id for o in self.options}) != len(self.options)
                or len({o.evaluation_id for o in self.options}) != len(self.options)):
            raise ValueError("nonempty unique candidate/evaluation IDs required")
        return self


class SimulateInput(FrozenModel):
    kind: Literal["simulate"]
    snapshot: SnapshotRef
    candidate_id: _EvidenceId
    package: Package
    citations: tuple[Citation, ...]
    question: _EvidenceLabel


class ProposeInput(FrozenModel):
    kind: Literal["propose"]
    snapshot: SnapshotRef
    supplier_id: _EvidenceId
    conversation: ConversationView
    assessment: SupplierAssessment
    negotiable_fields: tuple[TermField, ...]
    options: tuple[TermOption, ...]
    citation_catalog: tuple[tuple[str, MessageSpan], ...]
    must_haves: tuple[MustHave, ...]
    prior_evaluations: tuple[str, ...] = ()


class CommercialReference(FrozenModel):
    """Public commercial reference terms, derived only from an observed supplier offer."""
    kind: Literal["observed_supplier_offer", "unavailable"]
    bindings: tuple[TermBinding, ...] = ()
    source_message_id: _EvidenceId | None = None


class CommercialTermEffect(FrozenModel):
    field: TermField
    before: TermBinding | None
    buyer_direction: Literal["favorable", "unfavorable", "mixed", "unknown"]
    supplier_direction: Literal["potentially_favorable", "potentially_unfavorable", "unknown"]
    note: Annotated[str, Field(max_length=180)]


class ProposeInputV2(FrozenModel):
    """Versioned proposal projection carrying code-derived commercial effects."""
    kind: Literal["propose"]
    snapshot: SnapshotRef
    supplier_id: _EvidenceId
    conversation: ConversationView
    assessment: SupplierAssessment
    negotiable_fields: tuple[TermField, ...]
    options: tuple[TermOption, ...]
    citation_catalog: tuple[tuple[str, MessageSpan], ...]
    must_haves: tuple[MustHave, ...]
    commercial_reference: CommercialReference
    commercial_effects: tuple[CommercialTermEffect, ...]


class ProposalResponseV2(FrozenModel):
    bindings: Annotated[tuple[TermBinding, ...], Field(min_length=1, max_length=11)]
    citation_ids: Annotated[tuple[str, ...], Field(max_length=8)]
    buyer_requests: Annotated[tuple[TermField, ...], Field(max_length=11)]
    buyer_offers: Annotated[tuple[TermField, ...], Field(max_length=11)]
    supplier_value_unknown: Annotated[tuple[TermField, ...], Field(max_length=11)]
    rationale: Annotated[str, Field(min_length=1, max_length=1000)]


class ProposalResponseV3(FrozenModel):
    """Bindings and evidence only; commercial direction is derived by code."""
    bindings: Annotated[tuple[TermBinding, ...], Field(min_length=1, max_length=11)]
    citation_ids: Annotated[tuple[str, ...], Field(max_length=8)]
    rationale: Annotated[str, Field(min_length=1, max_length=1000)]


class ProposalResponse(FrozenModel):
    bindings: Annotated[tuple[TermBinding, ...], Field(min_length=1, max_length=11)]
    citation_ids: Annotated[tuple[str, ...], Field(max_length=8)]
    rationale: Annotated[str, Field(min_length=1, max_length=1000)]


ModelInput = InterpretInput | SelectInput | SimulateInput | ProposeInput | ProposeInputV2


class ModelRequest(FrozenModel):
    call_id: UUID
    task: Literal["interpret", "select", "simulate", "propose"]
    task_schema_version: _EvidenceId
    prompt_version: _EvidenceId
    input: ModelInput
    provider_id: _EvidenceId
    model_id: _EvidenceId
    protocol_id: _EvidenceId
    effort: _EvidenceLabel | None = None
    output_schema_hash: str
    correlation_id: UUID

    @model_validator(mode="after")
    def matching_task(self):
        if self.task != self.input.kind:
            raise ValueError("task must match input kind")
        return self


class ModelBudget(FrozenModel):
    deadline_at: Annotated[datetime, AfterValidator(_slice_utc)]
    time_limit_s: Annotated[_EvidenceDecimal, Field(gt=0)]
    max_tokens: Annotated[int, Field(gt=0)]
    max_calls: Annotated[int, Field(gt=0, le=2)]
    retry_limit: Literal[0]

    @field_validator("retry_limit", mode="before")
    @classmethod
    def integer_zero(cls, value):
        if type(value) is not int or value != 0:
            raise ValueError("retry limit must be integer zero")
        return value


class ModelUsage(FrozenModel):
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    reported_cost: Money | None = None

    @model_validator(mode="after")
    def nonnegative_cost(self):
        if self.reported_cost is not None and self.reported_cost.amount < 0:
            raise ValueError("negative reported cost")
        return self


class ModelSuccess(FrozenModel):
    kind: Literal["success"]
    call_id: UUID
    model_id: _EvidenceId
    elapsed_s: Annotated[_EvidenceDecimal, Field(ge=0)]
    issues: tuple[Issue, ...]
    raw_response_json: str
    response_hash: str
    usage: ModelUsage

    @model_validator(mode="after")
    def raw_digest(self):
        import hashlib
        if hashlib.sha256(self.raw_response_json.encode("utf-8")).hexdigest() != self.response_hash:
            raise ValueError("raw response digest mismatch")
        return self


class _ModelFailure(FrozenModel):
    call_id: UUID
    model_id: _EvidenceId
    elapsed_s: Annotated[_EvidenceDecimal, Field(ge=0)]
    issues: tuple[Issue, ...]

    @model_validator(mode="after")
    def required_error(self):
        code = {"refused": "model_invalid", "invalid": "model_invalid", "timeout": "model_timeout",
                "capacity_unavailable": "unsupported_capability", "transport_failure": "recovery_required"}[self.kind]
        if not any(i.severity == "error" and i.code == code for i in self.issues):
            raise ValueError("required model failure issue missing")
        return self


class ModelRefused(_ModelFailure):
    kind: Literal["refused"]


class ModelInvalid(_ModelFailure):
    kind: Literal["invalid"]


class ModelTimeout(_ModelFailure):
    kind: Literal["timeout"]


class ModelCapacityUnavailable(_ModelFailure):
    kind: Literal["capacity_unavailable"]


class ModelTransportFailure(_ModelFailure):
    kind: Literal["transport_failure"]


ModelResult = Annotated[
    ModelSuccess | ModelRefused | ModelInvalid | ModelTimeout | ModelCapacityUnavailable | ModelTransportFailure,
    Field(discriminator="kind"),
]


class SelectorResponse(FrozenModel):
    selected_id: _EvidenceId
    supporting_quote: str
