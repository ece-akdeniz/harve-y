"""Fixed no-claim templates over exact registered selections."""

from ..core import models as m
from ..core.certificates import verify_batch
from ..core.errors import ContractViolation
from ..core.question_actions import QUESTION_TEMPLATES
from ..core.serialization import semantic_hash

TEMPLATE_VERSION = "email-templates-v2"
OFFER_BODY = "Please consider the proposed terms in the attached term sheet."
QUESTION_BODY = "Could you clarify which permitted terms are flexible?"
SUBJECT = "Negotiation"


def render_hash(action):
    return semantic_hash(action.model_dump(mode="json", exclude={"render_hash"}))


def offer_body(package, *, revised):
    """Professional email reconstructed only from the approved package."""
    labels = {
        "unit_price": "Unit price (EUR)", "payment_days": "Payment in days",
        "contract_months": "Contract term (months)", "volume_per_year": "Annual volume",
        "lead_time_days": "Lead time (days)", "effective_date": "Effective date",
        "incoterm": "Incoterm", "tooling_eur": "Tooling (EUR)", "index_clause": "Index clause",
    }
    values = {item.field: item.value for item in package.bindings}
    lines = [f"- {labels.get(field, field.replace('_', ' ').capitalize())}: {values[field]}"
             for field in sorted(values)]
    opening = "Thank you for your response. We propose the following package:" if revised else \
        "We are pleased to submit the following proposal:"
    return ("Guten Tag,\n\n" + opening + "\n" + "\n".join(lines) +
            "\n\nCould you confirm whether you can accept these terms as set out in the attached term sheet?" +
            "\n\nKind regards,\nProcurement team")


def question_body(question):
    return "Guten Tag,\n\n" + QUESTION_TEMPLATES[question] + \
        "\n\nThank you for your clarification.\n\nKind regards,\nProcurement team"


class TemplateActionRenderer:
    def __init__(self, *, batch):
        verify_batch(batch)
        self.batch = batch

    def render(self, decision, selected, claims, context) -> m.RenderedAction:
        verify_batch(self.batch)
        if claims or selected is None or selected not in self.batch.items or selected.disposition != "approved":
            raise ContractViolation("unsupported_claim: only approved no-claim selections supported")
        if (
            decision.approved_batch_hash != self.batch.batch_hash
            or decision.snapshot != context.snapshot
            or decision.snapshot != self.batch.snapshot
            or decision.candidate_id != selected.candidate.candidate_id
            or decision.evaluation_id != selected.evaluation_id
        ):
            raise ContractViolation("invalid_schema: selection is not a registered approved member")
        c = selected.candidate
        if c.contents.kind not in ("offer", "question") or getattr(c.contents, "claim_ids", ()):
            raise ContractViolation("unsupported_capability: used-action template unavailable")
        if c.contents.kind == "question" and c.contents.question_id not in QUESTION_TEMPLATES:
            raise ContractViolation("unsupported_capability: unregistered question")
        payload = m.MessagePayload(
            subject=SUBJECT,
            body=offer_body(c.contents.packages[0], revised=context.snapshot.state_version > 0)
            if c.contents.kind == "offer" else question_body(c.contents.question_id),
            packages=c.contents.packages if c.contents.kind == "offer" else (),
            refs=(),
            attachments=(),
        )
        action = m.RenderedAction(
            decision_ref="sha256:" + semantic_hash(decision),
            snapshot=context.snapshot,
            supplier_id=c.supplier_id,
            kind=c.contents.kind,
            payload=payload,
            claim_ids=(),
            template_version=TEMPLATE_VERSION,
            render_hash="0" * 64,
        )
        return action.model_copy(update={"render_hash": render_hash(action)})
