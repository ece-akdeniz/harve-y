"""Strict immutable V2 value objects for contracts, terms, and evidence refs."""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

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

    @field_validator("part_ids")
    @classmethod
    def require_parts(cls, value):
        if not value or any(not item for item in value):
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
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
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
            elif not isinstance(value, date):
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
    fingerprint: str

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
