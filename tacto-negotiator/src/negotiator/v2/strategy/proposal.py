"""Bounded model proposals over existing ports; no execution or arithmetic authority."""

from uuid import UUID

from pydantic import ValidationError

from ..core import models as m
from ..core.certificates import QUESTION_ID, policy_issues
from ..core.diagnostics import rejection
from ..core.errors import ContractViolation
from ..core.question_actions import QUESTION_TEMPLATES
from ..core.serialization import semantic_hash
from ..economics.effects import commercial_effects, expected_trade_labels, supplier_reference
from .selection import _safe
from .testing import MinimumCostTestSelector


class BoundedProposalPolicy:
    def __init__(self, *, model, clock, config, evaluator, projector):
        self.model, self.clock, self.config = model, clock, config
        self.evaluator = evaluator
        self.projector = projector

    @staticmethod
    def _clarification_fallback(context, assessment, state):
        """One bounded clarification after proposal failure; never resend a package."""
        thread = next(t for t in state.server.threads if t.supplier_id == assessment.supplier_id)
        messages = thread.conversation.messages
        already_asked = any(
            msg.speaker == "buyer" and any(template in msg.body for template in QUESTION_TEMPLATES.values())
            for msg in messages
        )
        remaining = thread.rounds.conservative_remaining
        if remaining is None and thread.rounds.server_rounds_used is not None:
            remaining = thread.rounds.limit - thread.rounds.server_rounds_used
        if already_asked or remaining is None or remaining <= 1 or thread.status != "open":
            raise ContractViolation("unsupported_capability: proposal fallback exhausted; closing required")
        intent = m.StrategyIntent(
            intent_id="pending",
            strategy_id="proposal-failure-clarify-v1",
            supplier_id=assessment.supplier_id,
            snapshot=context.snapshot,
            kind="clarify",
            direction="unchanged",
            observation_refs=(),
            evidence_refs=(),
            question_id=QUESTION_ID,
            rationale=("Proposal generation failed; ask one registered clarification instead of repeating "
                       "a rejected package."),
        )
        intent = intent.model_copy(update={"intent_id": "sha256:" + semantic_hash(
            intent.model_dump(mode="json", exclude={"intent_id"})
        )})
        return m.IntentBatch(snapshot=context.snapshot, intents=(intent,), issues=())

    def decision_scope(self, ledger):
        return self.model.decision_scope(ledger)

    async def propose_strategies(self, context, assessment, state, budget, research):
        call_id = None
        stage = "projection"
        try:
            thread = next(t for t in state.server.threads if t.supplier_id == assessment.supplier_id)
            source = self.projector(context, thread.conversation, assessment.supplier_id, self.config)
            # No buyer-private costs, alternative, targets, supplier estimates or raw case facts.
            reference = supplier_reference(source.conversation, context.case.negotiable_fields)
            projection = m.ProposeInputV2(
                kind="propose",
                snapshot=context.snapshot,
                supplier_id=assessment.supplier_id,
                conversation=source.conversation,
                assessment=assessment,
                negotiable_fields=context.case.negotiable_fields,
                options=context.case.options,
                citation_catalog=source.citation_catalog,
                must_haves=context.case.buyer.must_haves,
                commercial_reference=reference,
                commercial_effects=commercial_effects(reference, context.case.negotiable_fields),
            )
            _safe(projection.model_dump(mode="json"))
            if len(projection.model_dump_json()) > self.config.max_input_chars:
                raise ContractViolation("unsupported_capability: proposal input exceeds bound")
            call_id = UUID(hex=semantic_hash((projection, self.config.model_id, "bounded-proposal-v3"))[:32])
            request = m.ModelRequest(
                call_id=call_id,
                task="propose",
                input=projection,
                task_schema_version="proposal-response-v3",
                prompt_version="bounded-proposal-v3",
                provider_id=self.config.provider_id,
                model_id=self.config.model_id,
                protocol_id=self.config.protocol_id,
                output_schema_hash=semantic_hash(m.ProposalResponseV3.model_json_schema()),
                correlation_id=call_id,
            )
            budget_factory = getattr(self.model, "model_budget", None)
            if not callable(budget_factory):
                raise ContractViolation("unsupported_capability: decision budget owner is unavailable")
            mb = budget_factory(task="propose", max_tokens=self.config.max_tokens,
                                time_limit_s=self.config.time_limit_s)
            stage = "execution"
            result = await self.model.complete(request, mb)
            if result.kind != "success":
                raise ContractViolation("model_invalid: proposal unavailable")
            if result.call_id != call_id or result.model_id != self.config.model_id:
                raise ContractViolation("model_invalid: foreign response")
            if self.clock.utcnow() >= mb.deadline_at:
                raise ContractViolation("model_timeout: late proposal")
            stage = "schema"
            if len(result.raw_response_json) > self.config.max_output_chars:
                raise ContractViolation("model_invalid: oversized proposal")
            response = m.ProposalResponseV3.model_validate_json(result.raw_response_json)
            _safe(response.model_dump(mode="json"))
            stage = "grounding"
            catalog = dict(source.citation_catalog)
            if any(c not in catalog for c in response.citation_ids):
                raise ContractViolation("missing_source: foreign proposal citation")
            if any(msg.speaker == "buyer" for msg in source.conversation.messages) and not response.citation_ids:
                raise ContractViolation("ungrounded_output: later proposal changes need supplier evidence")
            stage = "grounding"
            changed, requests, offers = expected_trade_labels(reference, response.bindings)
            stage = "consumer"
            if {t.field for t in response.bindings} != set(context.case.negotiable_fields):
                raise ContractViolation("invalid_schema: proposal must contain exactly all negotiable fields")
            package = m.Package(bindings=response.bindings, price_basis=context.case.parts[0].price_basis)
            evaluation = self.evaluator.evaluate_package(package, assessment.supplier_id, context.economic)
            if policy_issues((evaluation,), context.economic):
                raise ContractViolation("infeasible: independently evaluated proposal rejected")
            intent = m.StrategyIntent(
                intent_id="pending",
                strategy_id="bounded-proposal-v3",
                supplier_id=assessment.supplier_id,
                snapshot=context.snapshot,
                kind="propose_package",
                direction="enumerate",
                observation_refs=(),
                evidence_refs=(),
                rationale=(f"{response.rationale} Code-derived buyer requests: {sorted(requests)}; "
                           f"buyer offers: {sorted(offers)}; supplier value unknown for changed fields: "
                           f"{sorted(changed)}."),
                proposed_bindings=response.bindings,
                proposal_citations=tuple(catalog[c] for c in response.citation_ids),
            )
            intent = intent.model_copy(
                update={"intent_id": "sha256:" + semantic_hash(intent.model_dump(mode="json", exclude={"intent_id"}))}
            )
            self.model.admit_raw(call_id, result.raw_response_json)
            return m.IntentBatch(snapshot=context.snapshot, intents=(intent,), issues=())
        except (ContractViolation, ValidationError, ValueError, TimeoutError) as error:
            code = str(error).split(":", 1)[0]
            if code not in m.IssueCode.__args__:
                code = "model_invalid"
            if call_id is not None:
                diagnostic = rejection(error, stage)
                self.model.reject_raw(call_id, code, diagnostic)
            else:
                diagnostic = rejection(error, stage)
            try:
                fallback = self._clarification_fallback(context, assessment, state)
            except ContractViolation:
                raise
            return fallback.model_copy(update={"issues": (m.Issue(
                code=code, severity="warning", component="strategy.proposal", refs=(),
                detail=(f"proposal rejected ({diagnostic.stage}/{diagnostic.category}); one registered "
                        "clarification selected; no package repeated"),
            ),)})


class ProposedCandidateGenerator:
    def __init__(self, *, fallback):
        self.fallback = fallback

    def generate_candidates(self, intent, context, state, budget):
        if not intent.proposed_bindings:
            return self.fallback.generate_candidates(intent, context, state, budget)
        if (
            intent.snapshot != context.snapshot
            or intent.supplier_id not in context.case.supplier_ids
            or {t.field for t in intent.proposed_bindings} != set(context.case.negotiable_fields)
        ):
            raise ContractViolation("invalid_schema: stale or incomplete generated proposal")
        package = m.Package(bindings=intent.proposed_bindings, price_basis=context.case.parts[0].price_basis)
        candidate = m.CandidateAction(
            candidate_id="pending",
            intent_id=intent.intent_id,
            supplier_id=intent.supplier_id,
            snapshot=context.snapshot,
            contents=m.OfferAction(kind="offer", packages=(package,), claim_ids=()),
            construction_refs=(),
            candidate_builder_id="bounded-proposal-v3",
        )
        from ..core.certificates import candidate_id

        candidate = candidate.model_copy(update={"candidate_id": candidate_id(candidate)})
        return m.GenerationResult(
            intent_id=intent.intent_id,
            candidates=(candidate,),
            rejections=(),
            search_scope="bounded_scan",
            search_complete=False,
        )


class ProposalSelector(MinimumCostTestSelector):
    """Only one model package reaches selection, after independent economic approval."""

    async def select_action(self, candidates, assessment, state, budget, research):
        decision = await super().select_action(candidates, assessment, state, budget, research)
        model_intent = next(
            (
                i
                for i in candidates.items
                if i.candidate.candidate_id == decision.candidate_id
                and i.candidate.candidate_builder_id == "bounded-proposal-v3"
            ),
            None,
        )
        if model_intent:
            decision = decision.model_copy(
                update={
                    "selector_id": "bounded-proposal-certified-v3",
                    "rationale": "Single model proposal independently admitted by official economics and validation.",
                    "citations": tuple(c for o in assessment.observations for c in o.citations)[:8],
                }
            )
        return decision
