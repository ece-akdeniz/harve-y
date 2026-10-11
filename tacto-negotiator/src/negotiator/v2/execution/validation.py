"""Independent no-claim offer/question validation; no dispatch authority."""

import hashlib
import json
from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from ..core import models as m
from ..core.certificates import policy_issues
from ..core.errors import ContractViolation
from ..core.ports import Clock, EconomicEvaluator
from ..core.question_actions import QUESTION_TEMPLATES
from .render import SUBJECT, TEMPLATE_VERSION, offer_body, question_body, render_hash


def payload_bytes(payload):
    """Exact Arena message bytes for this limited no-action/no-attachment scope."""

    def encode(value):
        if isinstance(value, Decimal):
            number = float(value)
            if Decimal(str(number)) != value:
                raise ContractViolation("unsupported_capability: wire number cannot preserve declared value")
            return number
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, m.IndexClause):
            return value.model_dump(mode="python", exclude={"schema_version"})
        raise TypeError(type(value).__name__)

    return json.dumps(
        {
            "subject": payload.subject,
            "body": payload.body,
            "term_sheets": [{"terms": {t.field: t.value for t in p.bindings}} for p in payload.packages],
            "refs": list(payload.refs),
        },
        default=encode,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


class FinalActionValidator:
    def __init__(self, *, evaluator: EconomicEvaluator, clock: Clock, claim_verifier=None):
        self.evaluator = evaluator
        self.clock = clock
        # Full claim verification is deliberately unavailable in this used-action slice.

    def validate_action(
        self,
        action: m.RenderedAction,
        context: m.NegotiationContext,
        state: m.NegotiationState,
        budget: m.DecisionBudget,
    ) -> m.ValidationResult:
        issues = []
        checks = []

        def check(key, passed, code, detail):
            checks.append(m.CheckOutcome(check_id=key, passed=passed, refs=(), detail_code=code))
            if not passed:
                issues.append(
                    m.Issue(code=code, severity="error", component="execution.validation", refs=(), detail=detail)
                )

        # Revalidate frozen objects: model_copy is not an independent validation certificate.
        try:
            action = m.RenderedAction.model_validate_json(action.model_dump_json())
            context = m.NegotiationContext.model_validate_json(context.model_dump_json())
            state = m.NegotiationState.model_validate_json(state.model_dump_json())
            budget = m.DecisionBudget.model_validate_json(budget.model_dump_json())
        except ValidationError:
            report = m.ValidationReport(
                check_version=TEMPLATE_VERSION,
                snapshot=context.snapshot,
                checks=(),
                issues=(
                    m.Issue(
                        code="invalid_schema",
                        severity="error",
                        component="execution.validation",
                        refs=(),
                        detail="malformed boundary DTO",
                    ),
                ),
            )
            return m.InvalidActionResult(kind="invalid", report=report)
        now = self.clock.utcnow()
        check(
            "snapshot",
            action.snapshot == context.snapshot
            and state.run_id == context.snapshot.run_id
            and state.version == context.snapshot.state_version
            and state.config_hash == context.snapshot.config_hash
            and state.case == context.case
            and state.server is not None
            and state.server.session_id == context.snapshot.session_id,
            "stale_state",
            "action/context/state do not share a current snapshot",
        )
        check(
            "ownership",
            state.runtime_status in ("ready", "deciding")
            and not any(o.status in ("prepared", "submitted", "uncertain") for o in state.operations),
            "operation_pending",
            "state is not available for a new action",
        )
        thread = (
            next((t for t in state.server.threads if t.supplier_id == action.supplier_id), None)
            if state.server
            else None
        )
        check(
            "recipient",
            action.supplier_id in context.case.supplier_ids
            and thread is not None
            and thread.status in ("open", "final_offer", "agreed")
            and state.server.status == "open",
            "scope_mismatch",
            "recipient lacks an identified open thread",
        )
        check(
            "deadline",
            now < budget.deadline_at and now >= context.as_of,
            "deadline_exhausted",
            "absolute decision deadline exhausted",
        )
        deadlines = [budget.deadline_at]
        if thread:
            for proof in (thread.clock, state.server.wave_clock):
                if proof is None:
                    continue
                deadline = (
                    proof.server_deadline_at
                    if proof.confidence == "authoritative"
                    else proof.conservative_deadline_at
                    if proof.confidence == "conservative"
                    else None
                )
                check(
                    "clock:" + proof.kind,
                    deadline is not None and now < deadline,
                    "deadline_exhausted",
                    "declared server clock lacks a usable unexpired deadline",
                )
                if deadline is not None:
                    deadlines.append(deadline)
            rounds = thread.rounds
            remaining = (
                rounds.limit - rounds.server_rounds_used
                if rounds.confidence == "authoritative" and rounds.server_rounds_used is not None
                else rounds.conservative_remaining
                if rounds.confidence == "conservative"
                else None
            )
            check(
                "rounds", remaining is not None and remaining > 0, "rounds_unknown", "no proven remaining buyer round"
            )
        check(
            "scope",
            action.kind in ("offer", "question"),
            "unsupported_capability",
            "closing requires full closing validation",
        )
        check("hash", render_hash(action) == action.render_hash, "invalid_schema", "rendered content hash mismatch")
        check(
            "claims",
            not action.claim_ids and not action.payload.refs,
            "unsupported_claim",
            "claims/reference disclosure not supported",
        )
        check(
            "disclosure",
            not action.payload.attachments
            and action.payload.subject == SUBJECT
            and (action.kind == "offer" and len(action.payload.packages) == 1
                 and action.payload.body == offer_body(
                     action.payload.packages[0], revised=context.snapshot.state_version > 0)
                 or action.kind == "question" and not action.payload.packages
                 and action.payload.body in {question_body(question) for question in QUESTION_TEMPLATES})
            and action.template_version == TEMPLATE_VERSION,
            "private_disclosure",
            "only exact approved no-claim templates are admissible",
        )
        results = []
        if action.kind == "offer":
            for package in action.payload.packages:
                check(
                    "outgoing_fields:" + package.fingerprint,
                    {binding.field for binding in package.bindings} == set(context.case.negotiable_fields),
                    "invalid_schema",
                    "outgoing sheet must contain exactly every negotiable field",
                )
                try:
                    results.append(self.evaluator.evaluate_package(package, action.supplier_id, context.economic))
                except ContractViolation as error:
                    code = str(error).split(":", 1)[0]
                    if code not in m.IssueCode.__args__:
                        code = "invalid_schema"
                    check("package:" + package.fingerprint, False, code, str(error))
            economic_issues = policy_issues(results, context.economic)
            issues.extend(economic_issues)
            check(
                "economics",
                len(results) == len(action.payload.packages) and not economic_issues,
                "infeasible",
                "independent complete package/policy evaluation failed",
            )
        report = m.ValidationReport(
            check_version=TEMPLATE_VERSION, snapshot=context.snapshot, checks=tuple(checks), issues=tuple(issues)
        )
        if issues:
            return m.InvalidActionResult(kind="invalid", report=report)
        try:
            wire = payload_bytes(action.payload)
        except ContractViolation as error:
            check("wire", False, "unsupported_capability", str(error))
            report = m.ValidationReport(
                check_version=TEMPLATE_VERSION, snapshot=context.snapshot, checks=tuple(checks), issues=tuple(issues)
            )
            return m.InvalidActionResult(kind="invalid", report=report)
        digest = hashlib.sha256(wire).hexdigest()
        validated = m.ValidatedAction(
            rendered=action,
            report=report,
            payload_bytes_ref="sha256:" + digest,
            payload_hash=digest,
            economic_fingerprint=context.economic.fingerprint,
            expires_at=min(deadlines),
            validator_version=TEMPLATE_VERSION,
        )
        return m.ValidActionResult(kind="valid", action=validated)
