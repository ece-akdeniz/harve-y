"""Typed dependency boundaries for V2 components."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from . import models


class Clock(Protocol):
    def utcnow(self) -> datetime: ...

    def monotonic(self) -> float: ...


class OfficialCostOracle(Protocol):
    def evaluate(
        self,
        case: models.CaseContract,
        terms: models.ResolvedTerms,
        supplier: models.SupplierEstimate | None,
    ) -> models.OfficialCostResult: ...


class CanonicalClaimOracle(Protocol):
    def verify(
        self,
        candidate: models.ClaimCandidate,
        evidence: models.EvidenceContext,
        recipient_id: str,
        usage: tuple[models.ClaimUsage, ...],
    ) -> models.ClaimVerificationResult: ...


class ContextBuilder(Protocol):
    def build_context(
        self,
        prepared: models.PreparedEvidence,
        case: models.CaseContract,
        server: models.ServerState,
        documents: tuple[models.DocumentRecord, ...],
        as_of: datetime,
    ) -> models.EvidenceContext: ...


class SupplierInterpreter(Protocol):
    async def interpret(
        self,
        context: models.NegotiationContext,
        conversation: models.ConversationView,
        previous_assessment: models.SupplierAssessment | None,
        budget: models.DecisionBudget,
    ) -> models.SupplierAssessment: ...


class StrategyProposalPolicy(Protocol):
    async def propose_strategies(
        self,
        context: models.NegotiationContext,
        assessment: models.SupplierAssessment,
        state: models.NegotiationState,
        budget: models.DecisionBudget,
        research: models.CandidateResearch,
    ) -> models.IntentBatch: ...


class CandidateGenerator(Protocol):
    def generate_candidates(
        self,
        intent: models.StrategyIntent,
        context: models.NegotiationContext,
        state: models.NegotiationState,
        budget: models.DecisionBudget,
    ) -> models.GenerationResult: ...


class EconomicEvaluator(Protocol):
    def evaluate_package(
        self,
        package: models.Package,
        supplier_id: str,
        context: models.EconomicContext,
    ) -> models.PackageEvaluation: ...

    def evaluate_candidates(
        self,
        candidates: tuple[models.CandidateAction, ...],
        context: models.NegotiationContext,
    ) -> models.EvaluationBatch: ...


class ActionSelectionPolicy(Protocol):
    async def select_action(
        self,
        candidates: models.EvaluationBatch,
        assessment: models.SupplierAssessment,
        state: models.NegotiationState,
        budget: models.DecisionBudget,
        research: models.CandidateResearch,
    ) -> models.NegotiationDecision: ...


class CandidateResearch(Protocol):
    async def evaluate_intents(
        self,
        intents: models.IntentBatch,
        budget: models.DecisionBudget,
    ) -> models.EvaluationBatch: ...


class ClosingEvaluator(Protocol):
    def decide_close(
        self,
        context: models.NegotiationContext,
        state: models.NegotiationState,
        reason_code: str,
    ) -> models.CloseDecision: ...


class ClaimVerifier(Protocol):
    def verify(
        self,
        candidate: models.ClaimCandidate,
        evidence: models.EvidenceContext,
        recipient_id: str,
        usage: tuple[models.ClaimUsage, ...],
    ) -> models.ClaimVerificationResult: ...


class ActionRenderer(Protocol):
    def render(
        self,
        decision: models.NegotiationDecision | models.CloseDecision,
        selected: models.EvaluatedCandidate | None,
        claims: tuple[models.VerifiedClaim, ...],
        context: models.NegotiationContext,
    ) -> models.RenderedAction: ...


class ActionValidator(Protocol):
    def validate_action(
        self,
        action: models.RenderedAction,
        context: models.NegotiationContext,
        state: models.NegotiationState,
        budget: models.DecisionBudget,
    ) -> models.ValidationResult: ...


class DecisionEngine(Protocol):
    async def decide(self, snapshot: models.DecisionSnapshot) -> models.DecisionOutcome: ...


class FeedbackProcessor(Protocol):
    def process_feedback(
        self,
        previous_state: models.NegotiationState,
        operation: models.PendingOperation,
        response: models.ConversationMessage,
    ) -> tuple[models.EventProposal, ...]: ...


class StateProjector(Protocol):
    def apply_event(
        self,
        state: models.NegotiationState,
        event: models.NegotiationEvent,
    ) -> models.NegotiationState: ...


class StateStore(Protocol):
    async def load_state(self, run_id: str, case_id: str) -> models.NegotiationState: ...

    async def persist_state(
        self,
        expected_version: int,
        commit: models.DecisionCommit,
    ) -> models.CommitResult: ...

    async def append_observations(
        self,
        expected_version: int,
        events: tuple[models.EventProposal, ...],
    ) -> models.CommitResult: ...

    async def pending_operations(self, run_id: str) -> tuple[models.PendingOperation, ...]: ...


class ActionExecutor(Protocol):
    async def execute_action(
        self,
        action: models.ValidatedAction,
        permit: models.DispatchPermit,
        operation: models.PendingOperation,
        budget: models.TransportBudget,
    ) -> models.ExecutionResult: ...

    async def reconcile(
        self,
        operation: models.PendingOperation,
        context: models.NegotiationContext | None,
        state: models.NegotiationState,
        budget: models.TransportBudget,
    ) -> models.ExecutionResult: ...


class ArenaGateway(Protocol):
    async def observe(self, session_id: str, budget: models.TransportBudget) -> models.ServerObservation: ...

    async def submit(
        self,
        operation: models.PendingOperation,
        budget: models.TransportBudget,
    ) -> models.GatewayResult: ...

    async def fetch_document(
        self,
        session_id: str,
        attachment_id: str,
        budget: models.TransportBudget,
    ) -> models.DocumentBytes: ...


class ModelGateway(Protocol):
    async def complete(self, request: models.ModelRequest, budget: models.ModelBudget) -> models.ModelResult: ...
