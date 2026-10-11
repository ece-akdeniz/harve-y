"""Supplied-candidate minimum-cost test baseline, not negotiation intelligence."""

from uuid import NAMESPACE_URL, uuid5

from ..core import models as m
from ..core.certificates import QUESTION_ID, verify_batch
from ..core.errors import ContractViolation
from ..core.ports import CandidateResearch
from ..core.serialization import semantic_hash


class MinimumCostTestSelector:
    async def select_action(
        self,
        candidates: m.EvaluationBatch,
        assessment: m.SupplierAssessment,
        state: m.NegotiationState,
        budget: m.DecisionBudget,
        research: CandidateResearch,
    ) -> m.NegotiationDecision:
        verify_batch(candidates)
        if any(i.severity == "error" for i in candidates.issues):
            raise ContractViolation("infeasible: batch contains unresolved errors")
        approved = [i for i in candidates.items if i.disposition == "approved"]
        offers = [i for i in approved if i.candidate.contents.kind == "offer"]
        # Questions are an explicit fallback category, never a zero-cost offer.
        if offers:

            def key(i):
                costs = [r.nominal_cost.amount for r in i.economic]
                return min(costs), i.candidate.candidate_id

            chosen = min(offers, key=key)
        else:
            questions = [i for i in approved if i.candidate.contents.kind == "question"]
            if not questions:
                raise ContractViolation("infeasible: no admissible candidate")
            chosen = min(questions, key=lambda i: i.candidate.candidate_id)
        return m.NegotiationDecision(
            decision_id=uuid5(NAMESPACE_URL, candidates.batch_hash + chosen.evaluation_id),
            snapshot=candidates.snapshot,
            candidate_id=chosen.candidate.candidate_id,
            evaluation_id=chosen.evaluation_id,
            approved_batch_hash=candidates.batch_hash,
            selector_id="minimum-cost-test-v1",
            rationale="Test baseline chooses supplied admissible cost minimum.",
            citations=(),
        )


class SuppliedIntentTestPolicy:
    """Fixed test intents for supplied packages; performs no supplier inference."""

    def __init__(self, *, supplier_id: str, include_question: bool = False):
        self.supplier_id = supplier_id
        self.include_question = include_question

    async def propose_strategies(
        self,
        context: m.NegotiationContext,
        assessment: m.SupplierAssessment,
        state: m.NegotiationState,
        budget: m.DecisionBudget,
        research: CandidateResearch,
    ) -> m.IntentBatch:
        if self.supplier_id not in context.case.supplier_ids:
            raise ContractViolation("scope_mismatch: test policy recipient outside case")
        intents = []
        for kind in ("keep", "clarify") if self.include_question else ("keep",):
            intent = m.StrategyIntent(
                intent_id="pending",
                strategy_id="supplied-intents-test-v1",
                supplier_id=self.supplier_id,
                snapshot=context.snapshot,
                kind=kind,
                direction="unchanged",
                observation_refs=(),
                evidence_refs=(),
                question_id=QUESTION_ID if kind == "clarify" else None,
                rationale="Fixed testing intent over supplied actions; no inferred negotiation policy.",
            )
            intents.append(
                intent.model_copy(
                    update={
                        "intent_id": "sha256:"
                        + semantic_hash(
                            intent.model_dump(mode="json", exclude={"intent_id"}),
                        )
                    }
                )
            )
        return m.IntentBatch(snapshot=context.snapshot, intents=tuple(intents), issues=())
