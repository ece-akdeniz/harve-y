"""Bounded approved-ID selection. Supplier willingness remains a fallible hypothesis."""

import asyncio
import hashlib
import re
from datetime import timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import ValidationError

from ..core import models as m
from ..core.certificates import verify_batch
from ..core.diagnostics import rejection
from ..core.errors import ContractViolation
from ..core.ports import CandidateResearch
from ..core.serialization import semantic_hash
from ..core.supplier_grounding import ground
from ..core.supplier_grounding import safe_projection as _safe
from .questions import QUESTION_TEMPLATES
from .testing import MinimumCostTestSelector


class SelectorConfig(m.FrozenModel):
    """Explicit source authorization and provider limits, with no ambient credentials."""

    provider_id: str
    protocol_id: str
    model_id: str
    prompt_version: str
    task_schema_version: str
    max_tokens: int
    time_limit_s: Decimal
    approved_message_hashes: tuple[str, ...]
    full_observations: bool = False
    max_input_chars: int = 16000
    max_output_chars: int = 32000

    def checked(self):
        if (
            self.time_limit_s <= 0
            or type(self.max_tokens) is not int
            or self.max_tokens <= 0
            or self.max_input_chars <= 0
            or self.max_output_chars <= 0
            or not all(
                (self.provider_id, self.protocol_id, self.model_id, self.prompt_version, self.task_schema_version)
            )
        ):
            raise ValueError("explicit compatible selector configuration required")
        return self


_DIMENSIONS = {
    "lead_time_days": r"\b(delivery|lead time)\b",
    "contract_months": r"\b(commitment|contract|months)\b",
    "payment_days": r"\bpayment\b",
    "volume_per_year": r"\b(volume|units)\b",
    "unit_price": r"\b(price|EUR|€)\b",
}
_COMMERCIAL = re.compile(
    r"\b(prefer|rather|must|require|cannot|can't|refuse|only|if|unless|provided|subject to)\b", re.I
)




def _sources(assessment, state, config):
    thread = (
        next((t for t in state.server.threads if t.supplier_id == assessment.supplier_id), None)
        if state.server
        else None
    )
    if thread is None or state.server.session_id != assessment.snapshot.session_id:
        raise ContractViolation("scope_mismatch: selection source thread missing")
    messages = {msg.message_id: msg for msg in thread.conversation.messages}
    if len(messages) != len(thread.conversation.messages):
        raise ContractViolation("ungrounded_output: duplicate source identity")

    def citation(c):
        msg = messages.get(c.message_id) if isinstance(c, m.MessageSpan) else None
        if (
            msg is None
            or msg.speaker != "supplier"
            or msg.supplier_id != assessment.supplier_id
            or msg.session_id != assessment.snapshot.session_id
            or c.session_id != msg.session_id
            or c.thread_id != msg.thread_id
            or msg.content_hash not in config.approved_message_hashes
            or msg.content_hash != hashlib.sha256(msg.body.encode()).hexdigest()
            or (not config.full_observations and (msg.attachments or msg.observed_sheets or msg.claim_results
                                                  or msg.role is not None or msg.from_name is not None))
            or c.end > len(msg.body)
            or msg.body[c.start : c.end] != c.quote
        ):
            raise ContractViolation("ungrounded_output: unapproved or forged supporting source")
        _safe(msg.body)
        # Keep conditional antecedents, even when a short quote happens to be exact.
        if re.search(r"\b(if|unless|provided|subject to|conditional)\b", msg.body, re.I) and (
            c.start != 0 or c.end != len(msg.body)
        ):
            raise ContractViolation("ungrounded_output: conditional scope omitted")
        return c

    return thread, citation


def project_selection(batch, assessment, state, config):
    verify_batch(batch)
    assessment = m.SupplierAssessment.model_validate_json(assessment.model_dump_json())
    if (
        assessment.snapshot != batch.snapshot
        or state.run_id != batch.snapshot.run_id
        or state.version != batch.snapshot.state_version
        or state.config_hash != batch.snapshot.config_hash
        or assessment.supplier_id not in state.case.supplier_ids
        or assessment.assessment_id
        != "sha256:" + semantic_hash(assessment.model_dump(mode="json", exclude={"assessment_id"}))
    ):
        raise ContractViolation("stale_state: selection assessment identity mismatch")
    _safe(assessment.model_dump(mode="json"))
    thread, validate = _sources(assessment, state, config)
    refs = []
    for item in (
        *assessment.observations,
        *assessment.reported_constraints,
        *assessment.uncertainties,
        *assessment.questions,
    ):
        refs.extend(validate(c) for c in item.citations)
    for h in assessment.hypotheses:
        if h.numeric_effect is not None:
            raise ContractViolation("private_disclosure: supplier estimate effects are not authorized")
        refs.extend(validate(c) for c in (*h.supporting_refs, *h.contradicting_refs))
    if assessment.status == "ok":
        # The selector does not elevate previously unchecked model interpretations.
        ground(
            m.AssessmentDraft(
                **assessment.model_dump(
                    include={
                        "observations",
                        "reported_constraints",
                        "hypotheses",
                        "uncertainties",
                        "questions",
                        "unknowns",
                    }
                )
            ),
            m.InterpretInput(
                kind="interpret",
                snapshot=batch.snapshot,
                supplier_id=assessment.supplier_id,
                conversation=thread.conversation,
                evidence=(),
            ),
        )
    approved = [i for i in batch.items if i.disposition == "approved"]
    if (
        not approved
        or len(approved) > 20
        or any(i.severity == "error" for i in batch.issues)
        or any(i.candidate.supplier_id != assessment.supplier_id for i in approved)
    ):
        raise ContractViolation("scope_mismatch: unavailable or mixed-recipient selection batch")
    offers = [i for i in approved if i.candidate.contents.kind == "offer"]
    costs = [r.nominal_cost.amount for i in offers for r in i.economic]
    currencies = {r.nominal_cost.currency for i in offers for r in i.economic}
    if len(currencies) > 1:
        raise ContractViolation("unsupported_capability: relative costs require common currency")
    minimum = min(costs) if costs else None
    history = []
    # Only acknowledged actions with scoped operation proof become past attempts.
    ops = {
        o.operation_id: o
        for o in state.operations
        if o.status == "acknowledged"
        and o.supplier_id == assessment.supplier_id
        and o.session_id == batch.snapshot.session_id
        and o.case_id == state.case.case_id
        and o.kind == "send"
        and o.commit_state_version <= state.version
    }
    for attempt in state.strategic.attempts:
        if attempt.status == "acknowledged" and attempt.operation_id in ops:
            history.append(f"acknowledged attempt={attempt.attempt_id}; package={attempt.package_fingerprint}")
    history_refs = []
    for refusal in state.strategic.refusals:
        if refusal.supplier_id == assessment.supplier_id and refusal.assessment_id == assessment.assessment_id:
            history_refs.extend(validate(c) for c in refusal.citations)
            history.append(
                f"reported refusal={refusal.refusal_id}; scope={refusal.scope}; dimension={refusal.dimension}"
            )
    if len(history) > 12:
        raise ContractViolation("unsupported_capability: scoped history exceeds bound")
    options = []
    for item in approved:
        content = item.candidate.contents
        if content.kind == "offer":
            description = []
            for package, result in zip(content.packages, item.economic, strict=True):
                if not (
                    result.nominal_cost and result.numerically_valid and result.basis_verified and result.must_haves_ok
                ):
                    raise ContractViolation("infeasible: uncertified economics")
                terms = ", ".join(f"{t.field}={t.value}" for t in sorted(package.bindings, key=lambda t: t.field))
                description.append(
                    f"package={package.fingerprint}; {terms}; official buyer cost delta from cheapest="
                    f"{result.nominal_cost.amount - minimum} {result.nominal_cost.currency}"
                )
            summary = "Offer: " + " | ".join(description)
        elif content.kind == "question" and content.question_id in QUESTION_TEMPLATES:
            summary = f"Question {content.question_id}: {QUESTION_TEMPLATES[content.question_id]}; no monetary ranking"
        else:
            raise ContractViolation("unsupported_capability: unregistered selection action")
        if history:
            summary += "; relevant scoped history: " + " | ".join(history)
        options.append(
            m.SelectionOption(
                candidate_id=item.candidate.candidate_id,
                evaluation_id=item.evaluation_id,
                summary=summary,
                citations=tuple(dict.fromkeys(history_refs)),
            )
        )
    projection = m.SelectInput(
        kind="select",
        snapshot=batch.snapshot,
        approved_batch_hash=batch.batch_hash,
        options=tuple(options),
        assessment=assessment,
        conversation=thread.conversation if config.full_observations else None,
        thread_status=thread.status if config.full_observations else None,
    )
    _safe(projection.model_dump(mode="json"))
    if len(projection.model_dump_json()) > config.max_input_chars:
        raise ContractViolation("unsupported_capability: selection input exceeds bound")
    return projection, tuple(dict.fromkeys((*refs, *history_refs)))


def support_selection(selected, baseline, quote, refs, baseline_item):
    citations = tuple(c for c in refs if c.quote == quote) if quote else ()
    if quote and not citations:
        raise ContractViolation("ungrounded_output: supporting quote is not an approved exact span")
    content = selected.candidate.contents
    if content.kind == "question":
        cue = {
            "clarify:approval": r"approv|authori|manager|sign.off",
            "clarify:conditions": r"\b(if|unless|provided|subject to|conditional)\b",
            "clarify:terms": r"\b(terms|flexible|unclear|condition|require)\b",
        }[content.question_id]
        if not citations or not re.search(cue, quote, re.I):
            raise ContractViolation("ungrounded_output: clarification lacks material support")
    elif selected.candidate.candidate_id != baseline.candidate_id:
        if not citations or not _COMMERCIAL.search(quote):
            raise ContractViolation("ungrounded_output: departure lacks a commercial reason")
        # A quotation must address at least one changed permitted dimension. This is
        # a bounded relevance check, not proof of arbitrary entailment or acceptance.
        if baseline_item is None:
            raise ContractViolation("ungrounded_output: comparison unavailable")
        before = {t.field: t.value for p in baseline_item.candidate.contents.packages for t in p.bindings}
        after = {t.field: t.value for p in content.packages for t in p.bindings}
        changed = {field for field in after if before.get(field) != after[field]}
        if not any(re.search(_DIMENSIONS.get(field, r"(?!)"), quote, re.I) for field in changed):
            raise ContractViolation("ungrounded_output: quotation unrelated to changed terms")
        # Reject explicit correct-quote/wrong-option counterexamples. These narrow
        # phrase checks are grounding admission, not supplier utility or strategy rules.
        patterns = {
            "lead_time_days": r"(?:delivery|lead time)(?: is| in| of)? (\d+) days",
            "contract_months": r"(?:contract|commitment)(?: commitment)?(?: is| of| in)? (\d+) months",
            "payment_days": r"payment(?: is| in| of)? (\d+) days",
            "unit_price": r"(?:price(?: is| of)?|EUR) (\d+(?:\.\d+)?)",
        }
        conditional = bool(re.search(r"\b(if|unless|provided|subject to)\b", quote, re.I))
        refusing = bool(re.search(r"\b(cannot|can't|refuse|won't|not accept)\b", quote, re.I))
        for field in changed:
            match = re.search(patterns.get(field, r"(?!)"), quote, re.I)
            if match:
                value = Decimal(match.group(1))
                if refusing and not conditional and after[field] == value:
                    raise ContractViolation("ungrounded_output: refused option cannot support its selection")
                if not refusing and after[field] != value:
                    raise ContractViolation("ungrounded_output: explicit condition does not support selected option")
    return citations


class BoundedModelSelector:
    def __init__(self, *, model, clock, config: SelectorConfig):
        self.model, self.clock, self.config = model, clock, config.checked()

    def decision_scope(self, ledger):
        return self.model.decision_scope(ledger)

    async def select_action(
        self,
        candidates: m.EvaluationBatch,
        assessment: m.SupplierAssessment,
        state: m.NegotiationState,
        budget: m.DecisionBudget,
        research: CandidateResearch,
    ) -> m.NegotiationDecision:
        # Compute the certified baseline before any model failure; never change the batch.
        baseline = await MinimumCostTestSelector().select_action(candidates, assessment, state, budget, research)
        call_id = None
        stage = "projection"
        try:
            projection, refs = project_selection(candidates, assessment, state, self.config)
            digest = semantic_hash((projection, self.config.model_dump(exclude={"approved_message_hashes"})))
            call_id = UUID(hex=digest[:32])
            request = m.ModelRequest(
                call_id=call_id,
                task="select",
                task_schema_version=self.config.task_schema_version,
                prompt_version=self.config.prompt_version,
                input=projection,
                provider_id=self.config.provider_id,
                protocol_id=self.config.protocol_id,
                model_id=self.config.model_id,
                output_schema_hash=semantic_hash(m.SelectorResponse.model_json_schema()),
                correlation_id=call_id,
            )
            budget_factory = getattr(self.model, "model_budget", None)
            if callable(budget_factory):
                mb = budget_factory(task="select", max_tokens=self.config.max_tokens,
                                    time_limit_s=self.config.time_limit_s)
            else:
                reserves = float(budget.fallback_reserve_s + budget.submission_reserve_s)
                seconds = min(float(self.config.time_limit_s), float(budget.model_time_limit_s),
                              float(budget.compute_limit_s) - reserves,
                              (budget.deadline_at - self.clock.utcnow()).total_seconds() - reserves)
                if budget.model_call_limit < 1 or seconds <= 0:
                    raise ContractViolation("model_timeout: no selection allowance")
                mb = m.ModelBudget(deadline_at=self.clock.utcnow() + timedelta(seconds=seconds),
                                   time_limit_s=Decimal(str(seconds)), max_tokens=self.config.max_tokens,
                                   max_calls=1, retry_limit=0)
            stage = "execution"
            result = await self.model.complete(request, mb)
            if result.call_id != call_id or result.model_id != self.config.model_id:
                raise ContractViolation("model_invalid: selection call/model mismatch")
            if result.kind != "success":
                raise ContractViolation(result.issues[0].code + ": selection unavailable")
            if self.clock.utcnow() >= mb.deadline_at:
                raise ContractViolation("model_timeout: late selection")
            stage = "format"
            if len(result.raw_response_json) > self.config.max_output_chars:
                raise ContractViolation("model_invalid: oversized selection")
            stage = "schema"
            response = m.SelectorResponse.model_validate_json(result.raw_response_json)
            stage = "grounding"
            _safe(response.model_dump(mode="json"))
            selected = next(
                (
                    i
                    for i in candidates.items
                    if i.disposition == "approved" and i.candidate.candidate_id == response.selected_id
                ),
                None,
            )
            if selected is None:
                raise ContractViolation("invalid_schema: selected ID outside exact approved batch")
            baseline_item = next(i for i in candidates.items if i.candidate.candidate_id == baseline.candidate_id)
            citations = support_selection(selected, baseline, response.supporting_quote, refs, baseline_item)
            decision = m.NegotiationDecision(
                decision_id=uuid5(NAMESPACE_URL, candidates.batch_hash + selected.evaluation_id + str(call_id)),
                snapshot=candidates.snapshot,
                candidate_id=selected.candidate.candidate_id,
                evaluation_id=selected.evaluation_id,
                approved_batch_hash=candidates.batch_hash,
                selector_id="bounded-model-selector-v1",
                rationale=f"Approved-ID selection; model_call_id={call_id}; supplier willingness unverified.",
                citations=citations,
            )
            self.model.admit_raw(call_id, result.raw_response_json)
            return decision
        except asyncio.CancelledError:
            raise
        except (ContractViolation, ValidationError, ValueError, TimeoutError) as error:
            code = str(error).split(":", 1)[0]
            if code not in m.IssueCode.__args__:
                code = "model_invalid"
            if call_id is not None:
                self.model.reject_raw(call_id, code, rejection(error, stage))
            return baseline.model_copy(
                update={
                    "selector_id": "bounded-model-selector-v1:fallback",
                    "fallback_code": code,
                    "rationale": f"Certified minimum-cost fallback; reason={code}; model_call_id={call_id or 'none'}.",
                    "decision_id": uuid5(
                        NAMESPACE_URL, candidates.batch_hash + baseline.evaluation_id + code + str(call_id)
                    ),
                }
            )


class DeterministicSelector(MinimumCostTestSelector):
    """Existing certified minimum-cost control through the public selection seam."""
