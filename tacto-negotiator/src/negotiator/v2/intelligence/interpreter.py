"""LLM draft interpretation with explicit input admission and bounded grounding checks."""

import asyncio
import hashlib
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError

from ..core import models as m
from ..core.diagnostics import rejection
from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash
from ..core.supplier_grounding import _PRIVATE, ground
from .fallback import fallback


class InterpreterConfig(m.FrozenModel):
    provider_id: str
    protocol_id: str
    model_id: str
    prompt_version: str
    task_schema_version: str
    max_tokens: int
    time_limit_s: Decimal
    approved_message_hashes: tuple[str, ...]
    max_input_chars: int = 16000
    max_output_chars: int = 32000

    def checked(self):
        if (self.time_limit_s <= 0 or type(self.max_tokens) is not int or self.max_tokens <= 0
                or self.max_input_chars <= 0 or self.max_output_chars <= 0
                or not all((self.provider_id, self.protocol_id, self.model_id,
                            self.prompt_version, self.task_schema_version))):
            raise ValueError("explicit compatible interpreter configuration required")
        return self




def project(context, conversation, supplier_id, config):
    """Fail closed on unsupported history; never rewrite a source under its hash."""
    if conversation.session_id != context.snapshot.session_id:
        raise ContractViolation("scope_mismatch: foreign conversation")
    total = 0
    full = config.prompt_version.endswith("-v3")
    for msg in conversation.messages:
        total += len(msg.body)
        if ((msg.speaker not in {"supplier", "buyer", "arena"} if full else msg.speaker != "supplier")
                or (not full and (msg.attachments or msg.observed_sheets or msg.claim_results
                                 or msg.role is not None or msg.from_name is not None))
                or msg.supplier_id != supplier_id
                or msg.content_hash != hashlib.sha256(msg.body.encode()).hexdigest()
                or msg.content_hash not in config.approved_message_hashes
                or _PRIVATE.search(msg.body)):
            raise ContractViolation("private_disclosure: source requires an approved purpose projection")
    if total > config.max_input_chars or not conversation.messages:
        raise ContractViolation("unsupported_capability: empty/oversized input")
    # Raw evidence and previous assessment may contain private prose/numeric effects.
    # This increment excludes them entirely; runtime still preserves parent linkage.
    from ..core.supplier_grounding import safe_projection as _safe
    from .citations import citation_catalog
    _safe(conversation.model_dump(mode="json"))
    if len(conversation.model_dump_json()) > config.max_input_chars:
        raise ContractViolation("unsupported_capability: full observation exceeds input bound")
    return m.InterpretInput(kind="interpret", snapshot=context.snapshot, supplier_id=supplier_id,
                            conversation=conversation, evidence=(), previous=None,
                            citation_catalog=citation_catalog(conversation),
                            thread_status=conversation.status)




class GroundedInterpreter:
    def __init__(self, *, model, clock, config: InterpreterConfig):
        self.model = model
        self.clock = clock
        self.config = config.checked()

    def decision_scope(self, ledger):
        return self.model.decision_scope(ledger)

    async def interpret(self, context, conversation, previous_assessment, budget):
        supplier_id = next((t.supplier_id for t in conversation.messages),
                           context.case.supplier_ids[0] if len(context.case.supplier_ids) == 1 else None)
        if supplier_id not in context.case.supplier_ids:
            raise ContractViolation("scope_mismatch: unidentified interpretation target")
        call_id = None
        stage = "projection"
        try:
            if previous_assessment is not None and (
                previous_assessment.supplier_id != supplier_id
                or previous_assessment.snapshot.run_id != context.snapshot.run_id
                or previous_assessment.snapshot.session_id != context.snapshot.session_id
                or previous_assessment.snapshot.state_version > context.snapshot.state_version
            ):
                raise ContractViolation("stale_state: previous assessment scope/version mismatch")
            projection = project(context, conversation, supplier_id, self.config)
            # Content-derived call identity supports recorded replay without provider-generated IDs.
            digest = semantic_hash((projection, self.config.model_dump(exclude={"approved_message_hashes"})))
            call_id = UUID(hex=digest[:32])
            from .citations import wire_schema
            request = m.ModelRequest(
                call_id=call_id, task="interpret", task_schema_version=self.config.task_schema_version,
                prompt_version=self.config.prompt_version, input=projection,
                provider_id=self.config.provider_id, model_id=self.config.model_id, protocol_id=self.config.protocol_id,
                output_schema_hash=semantic_hash(wire_schema() if self.config.prompt_version.endswith("-v3")
                                                 else m.AssessmentDraft.model_json_schema()), correlation_id=call_id,
            )
            budget_factory = getattr(self.model, "model_budget", None)
            if callable(budget_factory):
                mb = budget_factory(task="interpret", max_tokens=self.config.max_tokens,
                                    time_limit_s=self.config.time_limit_s)
            else:
                reserves = float(budget.fallback_reserve_s + budget.submission_reserve_s)
                seconds = min(float(self.config.time_limit_s), float(budget.model_time_limit_s),
                              float(budget.compute_limit_s) - reserves,
                              (budget.deadline_at - self.clock.utcnow()).total_seconds() - reserves)
                if budget.model_call_limit < 1 or seconds <= 0:
                    raise ContractViolation("model_timeout: no inference allowance remains")
                mb = m.ModelBudget(deadline_at=self.clock.utcnow() + timedelta(seconds=seconds),
                                   time_limit_s=Decimal(str(seconds)), max_tokens=self.config.max_tokens,
                                   max_calls=1, retry_limit=0)
            stage = "execution"
            result = await self.model.complete(request, mb)
            if result.call_id != call_id or result.model_id != self.config.model_id:
                raise ContractViolation("model_invalid: call/model mismatch")
            if result.kind != "success":
                raise ContractViolation(result.issues[0].code + ": inference unavailable")
            if self.clock.utcnow() >= mb.deadline_at:
                raise ContractViolation("model_timeout: late result")
            stage = "format"
            if (len(result.raw_response_json) > self.config.max_output_chars
                    or _PRIVATE.search(result.raw_response_json)):
                raise ContractViolation("private_disclosure: unsafe/oversized model output")
            stage = "schema"
            from .citations import resolve_citations
            raw = (resolve_citations(result.raw_response_json, dict(projection.citation_catalog))
                   if self.config.prompt_version.endswith("-v3") else result.raw_response_json)
            draft = m.AssessmentDraft.model_validate_json(raw)
            stage = "grounding"
            draft = ground(draft, projection)
            stage = "consumer"
            assessment = m.SupplierAssessment(
                assessment_id="pending", supplier_id=supplier_id, snapshot=context.snapshot,
                revision=previous_assessment.revision + 1 if previous_assessment else 1,
                **draft.model_dump(exclude={"schema_version"}), status="ok", interpreter_id="grounded-interpreter-v1",
                model_call_id=str(call_id),
                parent_assessment_id=previous_assessment.assessment_id if previous_assessment else None,
            )
            self.model.admit_raw(call_id, result.raw_response_json)
            return assessment.model_copy(update={
                "assessment_id": "sha256:" + semantic_hash(
                    assessment.model_dump(mode="json", exclude={"assessment_id"}),
                ),
            })
        except asyncio.CancelledError:
            raise
        except (ContractViolation, ValidationError, ValueError, TimeoutError) as error:
            code = str(error).split(":", 1)[0]
            if code not in m.IssueCode.__args__:
                code = "model_invalid"
            if call_id is not None:
                self.model.reject_raw(call_id, code, rejection(error, stage))
            return await fallback(context, conversation, previous_assessment, budget, supplier_id, code,
                                  str(call_id) if call_id else None)
