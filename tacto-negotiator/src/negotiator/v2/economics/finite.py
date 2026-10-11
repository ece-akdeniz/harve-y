"""Finite supplied candidates and certification through the official evaluator."""

from ..core import models as m
from ..core.certificates import (
    batch_hash,
    candidate_id,
    evaluation_id,
    issue,
    policy_issues,
)
from ..core.errors import ContractViolation
from ..core.question_actions import QUESTION_TEMPLATES


class SuppliedCandidateGenerator:
    """Testing seam: supplied packages, never search, repair, or optimize terms."""

    def __init__(self, *, packages: tuple[m.Package, ...]):
        if not isinstance(packages, tuple) or len(packages) > 20 or any(not isinstance(p, m.Package) for p in packages):
            raise ValueError("supply at most twenty validated packages")
        if len({p.fingerprint for p in packages}) != len(packages):
            raise ValueError("duplicate supplied package")
        self.packages = packages

    def generate_candidates(
        self,
        intent: m.StrategyIntent,
        context: m.NegotiationContext,
        state: m.NegotiationState,
        budget: m.DecisionBudget,
    ) -> m.GenerationResult:
        if intent.snapshot != context.snapshot or intent.supplier_id not in context.case.supplier_ids:
            raise ContractViolation("stale_state: intent does not belong to context")
        contents = ()
        if intent.kind == "keep":
            contents = tuple(m.OfferAction(kind="offer", packages=(p,), claim_ids=()) for p in self.packages)
        elif intent.kind == "clarify" and intent.question_id in QUESTION_TEMPLATES:
            contents = (m.QuestionAction(kind="question", question_id=intent.question_id),)
        if len(contents) > budget.candidate_limit:
            contents = ()  # Do not hide truncation as complete finite enumeration.
        candidates = []
        for content in contents:
            c = m.CandidateAction(
                candidate_id="pending",
                intent_id=intent.intent_id,
                supplier_id=intent.supplier_id,
                snapshot=context.snapshot,
                contents=content,
                construction_refs=(),
                candidate_builder_id="finite-supplied-v1",
            )
            candidates.append(c.model_copy(update={"candidate_id": candidate_id(c)}))
        return m.GenerationResult(
            intent_id=intent.intent_id,
            candidates=tuple(candidates),
            rejections=() if candidates else (issue("unsupported_capability", "intent/scope exceeds finite slice"),),
            search_scope="finite",
            search_complete=bool(candidates),
        )


def evaluate_candidates(
    evaluator,
    candidates: tuple[m.CandidateAction, ...],
    context: m.NegotiationContext,
) -> m.EvaluationBatch:
    if len(candidates) > 20:
        raise ContractViolation("unsupported_capability: supplied batch exceeds twenty candidates")
    items = []
    for c in candidates:
        if c.snapshot != context.snapshot or c.candidate_id != candidate_id(c):
            raise ContractViolation("invalid_schema: stale or edited candidate")
        results = []
        problems = []
        if c.supplier_id not in context.case.supplier_ids:
            problems.append(issue("scope_mismatch", "candidate recipient not in case"))
        if c.contents.kind == "offer":
            for p in c.contents.packages:
                try:
                    results.append(evaluator.evaluate_package(p, c.supplier_id, context.economic))
                except ContractViolation as error:
                    # Preserve the exact cardinality contract: malformed package joins cannot
                    # produce a fabricated PackageEvaluation without complete resolved terms.
                    raise ContractViolation(f"{error}; candidate batch not certified") from error
            problems.extend(policy_issues(results, context.economic))
        elif c.contents.kind != "question" or c.contents.question_id not in QUESTION_TEMPLATES:
            problems.append(issue("unsupported_capability", "only registered clarification supported"))
        if getattr(c.contents, "claim_ids", ()):
            problems.append(issue("unsupported_claim", "factual claims unsupported in used slice"))
        item = m.EvaluatedCandidate(
            evaluation_id="pending",
            candidate=c,
            economic=tuple(results),
            disposition="rejected" if problems else "approved",
            issues=tuple(problems),
        )
        items.append(item.model_copy(update={"evaluation_id": evaluation_id(item)}))
    b = m.EvaluationBatch(snapshot=context.snapshot, items=tuple(items), issues=(), batch_hash="0" * 64)
    return b.model_copy(update={"batch_hash": batch_hash(b)})
