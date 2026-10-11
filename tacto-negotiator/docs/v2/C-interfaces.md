# C — Interface and domain specification

**Implementation contract:** `negotiator-v2/1`. Architecture approved in principle; defaults frozen for implementation handoff. No production implementation is supplied here. [Plan](../21-negotiation-v2-plan-2026-10-10.md) · [Architecture](B-architecture.md) · [Roadmap](D-roadmap.md).

This document is the common implementation handoff. Model tables specify fields omitted from the illustrative Python sketches. Changes to a field's meaning, source authority or outcome semantics require a recorded contract revision. First implement the minimal subset in M1; do not fabricate unsupported optional capabilities to satisfy a generic interface.

## 1. Universal contract rules

1. Boundary objects use strict, frozen Pydantic models, tuples, tagged unions, finite numbers and forbidden extra fields. Freeze nested values too; a frozen object containing a mutable dictionary is not immutable. Lists/maps may exist inside adapters but are converted before crossing a port.
2. Serialize versioned UTF-8 JSON. Decimal monetary/price values are canonical decimal strings in domain/storage JSON; dates are ISO dates, times are UTC with offset, and enums are strings. No NaN/infinity. Official Arena numeric JSON is generated only by its adapter using checked two-decimal values. Hash canonical sorted-key JSON with SHA-256; hashes exclude machine-local absolute roots, credentials and incidental receipt times unless time is part of the object's meaning.
3. Every durable envelope has `schema_version`. Stable content IDs identify evidence revisions, candidates and evaluations. UUIDs identify events, decisions, operations and attempts. Official IDs are opaque and session-scoped where appropriate; a `message_id` alone does not identify a message across sessions.
4. The only strategic-state writer is the coordinator through the state store. Components return values or proposed events. The only official-state writer is application of gateway observations. Components may keep bounded immutable caches; caches cannot change strategy after eviction or restart.
5. Typed results distinguish empty/infeasible/rejected/unknown/fallback/recovery-required/terminal. Missing data is never a numeric zero, no executable alternative is never mathematical infinity, and a proposed action is never a sent action.
6. A snapshot has a source `state_version` (event sequence), context/config/contract hashes, session identity and clock evidence. Candidates, evaluations and decisions bind to it. A stale object cannot authorize dispatch.
7. Significant assessment/intent/selection assertions cite existing message spans or evidence revisions. Validation can prove attribution and numeric calculations; human/local behavioral labels test semantic entailment. Rationale is an internal bounded summary, never executable code or private chain-of-thought.
8. Domain ports expose narrow capabilities. A strategy can evaluate hypothetical packages through a read-only port; it cannot access live transport, raw database handles, mutation methods, credentials or public results.

### IDs and immutable values

Use validated string wrappers/type aliases for `RunId`, `AttemptId`, `CaseId`, `SessionId`, `ThreadId`, `SupplierId`, `PartId`, `MessageId`, `OfferId`, `RecordId`, `ClaimId`, `IntentId`, `CandidateId`, `EvaluationId`, `DecisionId`, `EventId`, `OperationId`, `SourceVersion`, `ContextVersion`, `ConfigHash`, and `Sha256`. Official prefixes are not invented for provider/local objects. Candidate IDs hash `(contract, snapshot, intent, target, action contents)`; a matching package across turns has a separate `package_fingerprint` for refusal/repetition matching.

## 2. Core schemas

The sketches show the shape and important types. All auxiliary types are specified in the tables below; `core` may depend on standard Python and Pydantic only.

```python
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field

class FrozenModel(BaseModel):
    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", allow_inf_nan=False
    )

class PriceBasis(FrozenModel):
    currency: Literal["EUR"]
    price_unit: int                  # positive number of physical units per quoted price
    part_ids: tuple[str, ...]        # nonempty; basket basis must be explicitly declared
    quantity_basis: str              # validated ID of official case quantity convention
    source_refs: tuple[str, ...]

class Price(FrozenModel):
    amount: Decimal                 # finite, > 0; outbound tick is 0.01
    basis: PriceBasis

class Money(FrozenModel):
    amount: Decimal                 # finite; signed cost components allowed
    currency: Literal["EUR"] = "EUR"

class IndexClause(FrozenModel):
    series: str
    material_share: Decimal         # [0, 1]
    deadband_pct: Decimal            # >= 0
    base_month: str                  # YYYY-MM

TermField = Literal[
    "unit_price", "payment_days", "lead_time_days", "volume_per_year",
    "contract_months", "effective_date", "index_clause", "incoterm",
    "tooling_eur", "ppm_commitment", "chargeback_eur_per_complaint",
]
TermValue = int | Decimal | str | date | IndexClause | None

class TermBinding(FrozenModel):
    field: TermField
    value: TermValue                 # field-specific type validation, never bool-as-int

class Package(FrozenModel):
    bindings: tuple[TermBinding, ...] # unique fields; explicit null index_clause allowed
    price_basis: PriceBasis
    fingerprint: str                # canonical ordered bindings + basis

class SourceRef(FrozenModel):
    record_id: str                   # immutable evidence revision, not only canonical ID
    canonical_id: str | None = None

class MessageSpan(FrozenModel):
    session_id: str
    thread_id: str
    message_id: str
    start: int                       # Python Unicode character offsets
    end: int                         # exclusive; must reproduce exact quote
    quote: str

Citation = SourceRef | MessageSpan

class SnapshotRef(FrozenModel):
    run_id: str
    session_id: str
    state_version: int
    context_version: str
    config_hash: str
    case_contract_hash: str

class EvidenceRecord(FrozenModel):
    record_id: str
    canonical_id: str | None
    kind: Literal["canonical", "supplier_statement", "estimate", "hypothesis"]
    payload: "EvidencePayload"      # discriminated typed union specified below
    scope: "EvidenceScope"
    provenance: "Provenance"
    temporal: "TemporalValidity"
    disclosure: "DisclosureRule"
    supersedes: str | None = None

class GroundedObservation(FrozenModel):
    observation_id: str
    kind: Literal[
        "request", "refusal", "conditional_offer", "constraint",
        "approval_requirement", "stated_driver", "ambiguity"
    ]
    dimension: TermField | None
    summary: str
    citations: tuple[Citation, ...]  # nonempty
    package_fingerprint: str | None = None

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
    numeric_effect: "EstimatedEffect | None" = None

class SupplierAssessment(FrozenModel):
    assessment_id: str
    supplier_id: str
    snapshot: SnapshotRef
    revision: int
    observations: tuple[GroundedObservation, ...]
    reported_constraints: tuple["ReportedConstraint", ...]
    hypotheses: tuple[PreferenceHypothesis, ...]
    uncertainties: tuple["AssessmentUncertainty", ...]
    questions: tuple["ClarificationQuestion", ...]
    unknowns: tuple[str, ...]
    status: Literal["ok", "fallback", "insufficient_evidence"]
    interpreter_id: str
    model_call_id: str | None
    parent_assessment_id: str | None = None

class StrategyIntent(FrozenModel):
    intent_id: str
    strategy_id: str
    supplier_id: str
    snapshot: SnapshotRef
    kind: Literal["keep", "exchange", "evidence_challenge", "clarify", "request_close"]
    dimension: TermField | None
    direction: Literal["increase", "decrease", "enumerate", "unchanged"]
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[SourceRef, ...]
    question_id: str | None
    rationale: str                  # internal, bounded
    supersedes_refusal_id: str | None = None

class OfferAction(FrozenModel):
    kind: Literal["offer"]
    packages: tuple[Package, ...]   # 1..3 complete outbound packages
    claim_ids: tuple[str, ...]
    question_id: str | None = None

class QuestionAction(FrozenModel):
    kind: Literal["question"]
    question_id: str
    claim_ids: tuple[str, ...] = ()

class CloseRequest(FrozenModel):
    kind: Literal["request_close"]
    reason_code: str

CandidateContents = Annotated[
    OfferAction | QuestionAction | CloseRequest, Field(discriminator="kind")
]

class CandidateAction(FrozenModel):
    candidate_id: str
    intent_id: str
    supplier_id: str
    snapshot: SnapshotRef
    contents: CandidateContents
    construction_refs: tuple[str, ...]
    candidate_builder_id: str

class EvaluatedCandidate(FrozenModel):
    evaluation_id: str
    candidate: CandidateAction
    disposition: Literal["approved", "rejected"]
    economic: tuple["PackageEvaluation", ...] # empty for questions/close requests
    issues: tuple["Issue", ...]

class NegotiationDecision(FrozenModel):
    decision_id: str
    snapshot: SnapshotRef
    candidate_id: str
    evaluation_id: str
    approved_batch_hash: str         # registered final candidate-set identity
    selector_id: str
    rationale: str
    citations: tuple[Citation, ...]
    fallback_code: str | None = None
```

`TermBinding` accepts the union for a finite closed set of fields, then validates each field's type: integers for timing/volume/ppm/commitment; ISO date for effective date; structured clause or explicit null for index; enum for incoterm; Decimal for price/tooling/chargeback. Missing field is distinct from a null binding. Package contains only explicitly transmitted negotiable terms. `ResolvedTerms` contains typed full bindings including closing defaults and each field's origin. An incoming sheet need not be a valid outgoing Package; use `ObservedSheet` with typed parse issues rather than silently snapping it.

### Supporting models: exact field inventory

Required fields are listed without `?`; `?` means optional with null default. Tuple fields are present even when empty. Each model carries `schema_version="negotiator-v2/1"` in serialized envelopes; implementations may inherit that field once. Owners create new immutable revisions instead of modifying values.

| Model | Fields and validation | Owner / authority |
|---|---|---|
| `Issue` | `code: IssueCode`, `severity: error/warning`, `component: str`, `refs: tuple[str]`, `detail: str`; bounded sanitized detail | Producing component; structured diagnosis |
| `EvidenceScope` | `supplier_ids: tuple[SupplierId]`, `part_ids: tuple[PartId]`, `level: supplier/part/basket/case/global`, `case_id?: CaseId`; no fabricated part scope for supplier scorecards | Resolver |
| `Provenance` | `layer: base/release/case/session/derived`, `source_version: str`, `content_hash: Sha256`, `locator: str`, `parent_refs: tuple[SourceRef]`, `parser_version?: str`; locator is logical path/page/row, not credential URL | Source adapters/resolver |
| `TemporalValidity` | `observed_at?: datetime`, `published_at?: datetime`, `valid_from?: date`, `valid_to?: date`, `data_as_of?: date`, `status: current/stale/future/unknown`, `freshness_rule_id: str`; historical records remain usable for historical questions, never silently current | Resolver |
| `DisclosureRule` | `classification: public/supplier_own/internal/reveals_rival/restricted`, `permitted_recipients: tuple[SupplierId]`, `purpose: tuple[str]`; unknown original text defaults restricted | Evidence classification |
| `EvidencePayload` | Tagged union: `IndexFact(series,month,value,unit)`; `ScorecardFact(supplier,quarter,window_months,otd_pct?,ppm?)`; `CostFact(part,supplier?,unit_cost: Price,confidence_pct?,cost_base?)`; `QuoteFact(supplier,part_ids,price,observed_terms,validity?)`; `ContractFact(supplier,part_ids,notice_days?,clause_refs)`; `ForecastFact(part,period,quantity?,change_pct?)`; `OrderPriceFact(supplier,part,price,order_date,quantity?)`; `TextRecord(title,text,document_kind,declared_role?)`; `EstimateRecord(method_id,values: tuple[NamedEstimate],assumptions)` | Source adapters; no raw universal dict payload |
| `NamedEstimate` | `name: Literal[full_cost,interest_rate,usual_rate,ppm,extra_per_unit]` (registered methods/units in §8.9), `value: Decimal`, `unit: str`, `range_low?: Decimal`, `range_high?: Decimal`, `basis?: PriceBasis`; bounds ordered | Estimate builder; explicitly hypothetical |
| `Conflict` | `canonical_id`, `candidate_record_ids`, `winning_record_id?`, `rule_id`, `blocking: bool`, `reason_code`; unresolved critical conflict blocks dependent calculation | Resolver |
| `PreparedEvidence` | `artifact_id`, `schema_version`, `base_manifest`, `release_manifest?`, `parser_versions`, `records`, `indexes: tuple[ScopeIndex]`, `prepared_at`, `integrity_hash`; immutable content, preparation time excluded from semantic hash | Preparation service |
| `ScopeIndex` | `kind: supplier/part/canonical_id`, `key: str`, `record_ids: tuple[RecordId]` | Preparation service |
| `SourceManifest` | `source_id`, `content_hash`, `files: tuple[FileDigest]`, `data_as_of?`, `declared_version?`; every consumed file has relative path/digest | Data adapter/preflight |
| `FileDigest` | `path: relative str`, `sha256`, `byte_length: int`; no symlink/path escape | Data adapter |
| `EvidenceContext` | `context_version`, `case_id`, `supplier_ids`, `part_ids`, `as_of`, `prepared_artifact_id`, `records`, `conflicts`, `gaps: tuple[Issue]`, `relevance: tuple[RelevanceRecord]`, `source_versions`; includes supporting and adverse records | Context builder |
| `RelevanceRecord` | `record_id`, `topic`, `reason_code`, `rank: int`, `polarity: supports/contradicts/neutral/unknown`; rank is retrieval policy, not source truth | Relevance builder |
| `CaseContract` | `case_id`, `case_type`, `title`, `supplier_ids`, `parts: tuple[PartIdentity]`, `negotiable_fields`, `options: tuple[TermOption]`, `fixed_terms`, `buyer: BuyerEconomics`, `round_limit`, `case_facts`, `refs`, `contract_hash`; unknown commercial fields fail capability preflight | Official case adapter |
| `PartIdentity` | `part_id`, `price_basis`, `unit_label?`; for baskets require explicitly declared aggregate basis, never assume first part describes all | Data/case adapter |
| `TermOption` | `field`, `values: tuple[TermValue]`, `allow_verified_standard: bool`; standards exceptions have source refs and exact value | Case adapter |
| `MustHave` | `field`, `op: <=/< />=/ >/==/!=`, `value: TermValue`; validate operator applicability | Case adapter |
| `BuyerEconomics` | `category_goal`, `need_per_year`, `horizon_years`, `current_price?: Price`, `fallback_price: Price`, `interest_rate`, `reference_payment_days`, `need_lead_time_days`, `fallback_risk_pct`, `index_risk_pct`, `late_cost_per_day: Money`, `cost_per_defect: Money`, `sustainable_margin_pct?`, `relationship_eur_per_point?: Money`, `freight: tuple[FreightRate]`, `index_paths: tuple[IndexPath]`, `must_haves`, `alternative: ExecutableAlternative`; preserve official case quantity/price convention | Case adapter; private economics |
| `FreightRate`, `IndexPath` | Freight: `incoterm, eur_per_unit: Decimal`; index path: `series, delta_fraction: Decimal`; finite; conversions respect official basis | Case adapter |
| `ExecutableAlternative` | Tagged `available(ref?,terms,basis,provenance_refs)` or `unavailable(reason_code)`; operational fallback and no-deal scoring stored separately | Case/economic adapter |
| `ConversationMessage` | `session_id`, `thread_id`, `message_id`, `speaker: buyer/supplier/arena`, `supplier_id`, `role?`, `from_name?`, `body`, `observed_sheets`, `attachments`, `claim_results`, `server_at?`, `received_at`, `in_reply_to?`, `content_hash`; empty text valid | Gateway/source adapter |
| `ObservedSheet` | `offer_id?`, `bindings`, `source_message_ref`, `standing: bool`, `parse_issues`; no implicit acceptance eligibility | Gateway |
| `DocumentRecord` | `attachment_id`, `name`, `media_type`, `bytes_hash`, `text_ref?`, `structured_refs`, `parse_status: ok/partial/unsupported/failed`, `issues`; formulas remain attributed strings unless trusted parser derives explicit arithmetic | Evidence document adapter |
| `ClaimCheckResult` | `argument_index: int`, `result: verified/contradicted/irrelevant/duplicate/unknown`, `source_message_ref`; does not prove persuasion or a known claim ID match | Gateway |
| `ConversationView` | `session_id`, `thread_id`, `messages: tuple[ConversationMessage]`, `version_hash`; includes truncation metadata if a projection is bounded | Coordinator |
| `ClockEvidence` | `server_deadline_at?`, `seconds_left?`, `snapshot_requested_at`, `snapshot_received_at`, `server_at?`, `kind: thread/wave`, `source_ref`, `conservative_deadline_at?`, `confidence: authoritative/conservative/unknown`; never use late receipt as window origin | Gateway/budget service |
| `RoundEvidence` | `limit`, `server_rounds_used?`, `accepted_buyer_messages`, `timeout_rounds?`, `conservative_remaining?`, `source_ref`, `confidence`; attempts are separate from accepted rounds | Gateway/projector |
| `ServerState` | `session_id`, `case_id`, `status: open/ended/unknown`, `threads: tuple[ServerThread]`, `wave_clock?`, `terminal?: TerminalEvidence`, `observed_at`, `observation_hash` | Gateway observations only |
| `ServerThread` | `thread_id`, `supplier_id`, `status`, `standing_offer_id?`, `conversation`, `rounds`, `clock`, `standards: ResolvedStandards`, `closed_reason?`; status vocab preserves official values | Gateway/projector |
| `TerminalEvidence` | `session_id`, `status: ended`, `proof_ref`, `source_kind: gateway_response/gateway_observation`, `observed_at`, optional deal/offer_id/supplier_id/score/cost/end_reason; exact types in §8.9; proof authority verified by projector/store | Gateway/coordinator |
| `ResolvedStandards` | `bindings`, `field_origins`, `version_hash`; quote fields over master estimates, each field attributable | Evidence/estimate adapter |
| `ResolvedTerms` | `bindings: tuple[TermBinding,...]`, `origins: tuple[FieldOrigin,...]`, `version_hash: Sha256`; explicit validated sheet -> fixed -> quote -> buyer defaults | Economic adapter |
| `FieldOrigin` | `field`, `source_kind: sheet/fixed/quote/master/buyer_default`, `source_refs` | Resolution service |
| `EstimatedEffect` | `low`, `high`, `unit`, `basis?`, `method_id`, `citations`; not a binding price; numeric willingness absent by default | Interpreter/research hypothesis |
| `ClarificationQuestion` | `question_id`, `template_id`, `dimension?`, `citations`, `unknown_id`, `expected_information: str`; template args restricted to approved domain values | Interpreter/policy |
| `SupplierEstimate` | `estimate_id`, `supplier_id`, `basis`, `full_cost: Price`, `full_cost_low: Price`, `full_cost_high: Price`, `interest_rate`, `usual_rate`, `ppm?`, `standard`, `assumption_refs`, `method_id`, `uncertainty_kind: scenario_range/calibrated_interval/unknown`, `extra_per_unit?: Decimal`; no silent first-part mapping | Evidence-derived estimator |
| `EconomicContext` | `case`, `standards_by_supplier: tuple[SupplierStandards,...]`, `estimates: tuple[SupplierEstimate]`, `scenario_policy: ScenarioPolicy`, `cost_policy`, `fingerprint`, `issues`; mandatory estimate mode rejects unavailable critical estimate | Economic input builder |
| `CostPolicy` | `policy_id`, `comparison: nominal/robust_scenarios`, `ceiling?: Money`, `price_bounds: PriceInterval`, `tick: Decimal`, `fallback_rule`, `alternative_rule`; private code-approved policy, no LLM-authored budgets | Resolved config/economics |
| `PriceInterval` | `minimum: Price`, `maximum: Price`; same basis, positive ordered bounds; scan bounded by budget | Economics |
| `PackageEvaluation` | `package_fingerprint`, `resolved_terms`, `nominal_cost: Money | None`, `components: tuple[CostComponent]`, `scenario_costs`, `must_haves_ok`, `numerically_valid`, `basis_verified`, `assumption_refs`, `economic_fingerprint`, `issues: tuple[Issue]`; sum/rounding parity with kit; numeric failure has null nominal_cost and empty components | Economic evaluator |
| `CostComponent`, `ScenarioCost` | Component: `kind` from official 11 components, `amount: Money`; scenario: `scenario_id`, `estimate_id?`, `cost: Money`, `supplier_value?: Price`, `margin_pct?: Decimal`, `components`; no inferred acceptance probability | Economic evaluator |
| `GenerationResult` | `intent_id`, `candidates`, `rejections: tuple[Issue]`, `search_scope: finite/proven_monotonic/bounded_scan`, `search_complete: bool`; empty result is explicit infeasible/unsupported, never a default invalid package | Candidate generator |
| `IntentBatch`, `EvaluationBatch` | Intent batch: `snapshot`, `intents`, `issues`; evaluation batch: `snapshot`, `items`, `issues`, `batch_hash`; exact candidate-set identity binds selection | Policies/economics |
| `StrategyAttempt` | `attempt_id`, `intent_id`, `candidate_id`, `package_fingerprint?`, `operation_id`, `status: prepared/submitted/acknowledged/rejected/uncertain`, `response_refs`; proposal alone is not an attempted exchange | State projector |
| `RefusedExchange` | `refusal_id`, `supplier_id`, `dimension?`, `package_fingerprint?`, `attempt_refs`, `citations`, `scope: package/dimension/conditional/unknown`, `assessment_id`; broad inference labelled, not hard legal constraint | Strategic projector |
| `ClaimUsage` | `claim_id`, `canonical_ids`, `scope_key`, `operation_id`, `status: reserved/sent/unknown/released`, `recipient_id`; same-ID replay never consumes twice | Transactional store |
| `OutstandingQuestion` | `question_id`, `operation_id`, `status: submitted/answered/ambiguous`, `response_refs` | Feedback/state |
| `StrategicState` | `assessments`, `attempts`, `refusals`, `claim_usage`, `outstanding_questions`, `feedback`, `memory: tuple[StrategyMemory]`; all reconstructed independently of optional policy activation | Pure event projector |
| `StrategyMemory` | `strategy_id`, `schema_version`, `record_ref`, `parent_ref?`, `payload_hash`; payload is a separately registered strict strategy schema, not arbitrary cross-module dict | Strategy proposes; store commits |
| `NegotiationState` | `run_id`, `attempt_id`, `case`, `server?: ServerState` (null only before identified session), `strategic`, `operations`, `version: int`, `config_hash`, `runtime_status: ready/deciding/awaiting/recovery_required/ended`, `issues`; derived snapshot | Coordinator/store |
| `NegotiationContext` | `snapshot`, `case`, `evidence`, `economic`, `capabilities: tuple[str]`, `as_of`; full private internal input; do not serialize this into a provider prompt | Coordinator |
| `DecisionSnapshot` | `context`, `state`, `target_supplier_id`, `conversation`, `budget`; state/context identities must match | Coordinator; immutable |
| `DecisionBudget` | `deadline_at`, `compute_limit_s`, `model_call_limit`, `model_time_limit_s`, `candidate_limit`, `fallback_reserve_s`, `submission_reserve_s`, `clock_refs`; runtime monotonic remaining derived by injected Clock | Budget service |
| `CloseDecision` | `close_id`, `snapshot`, `action: Accept/WalkAway`, `evaluated_offer_refs`, `alternative_comparison`, `reason_code`, `policy_id`; only close evaluator creates binding recommendation | Deterministic closing service |
| `Accept`, `WalkAway` | Accept: `kind=accept`, `supplier_id`, `offer_id`, `evaluation_id`; walk: `kind=walk_away`, `supplier_id`, `reason_code`; recipient and offer must match current case | Closing service |
| `DecisionOutcome` | Tagged `selected(decision)`, `request_close(reason_code,snapshot)`, `hold(reason_code,recheck_at,snapshot)`, `cannot_decide(issues,snapshot)`; hold consumes time and is budgeted | Decision engine |
| `VerifiedClaim` | `claim_id`, `kind`, `source_refs`, `scope`, `figure?: Decimal`, `unit`, `basis?`, `window?`, `canonical_sentence`, `disclosure`, `verification_version`, `context_version`; historical internal Claim adapted, no arbitrary sentence | Claim verifier |
| `RenderedAction` | `decision_ref` or `close_ref` (exactly one), `snapshot`, `supplier_id`, `kind: offer/question/accept/walk_away`, `payload: MessagePayload`, `claim_ids`, `template_version`, `render_hash` | Renderer |
| `MessagePayload` | `subject`, `body`, `packages`, `refs`, `action?: AcceptPayload/WalkPayload`, `attachments: tuple[OutboundAttachment]`; exact protocol DTO, no unknown keys | Renderer/protocol adapter |
| `OutboundAttachment` | `name`, `media_type`, `content_ref`, `hash`, `disclosure`; initially empty; no arbitrary upload capability | Renderer/evidence |
| `ValidationReport` | `check_version`, `snapshot`, `checks: tuple[CheckOutcome]`, `issues`; report never repairs payload | Validator |
| `CheckOutcome` | `check_id`, `passed: bool`, `refs`, `detail_code` | Validator |
| `ValidatedAction` | `rendered`, `report`, `payload_bytes_ref`, `payload_hash`, `economic_fingerprint`, `expires_at`, `validator_version`; issued only by validator; execution checks artifact provenance/hash, never trusts caller flag | Validator |
| `PendingOperation` | `operation_id` (= logical move ID), `kind: open/send/close`, `case_id`, `session_id?`, `supplier_id?`, `endpoint_kind`, `payload_bytes_ref`, `payload_hash`, `validation_ref?`, `source_state_version`, `commit_state_version`, `created_at`, `submitted_at?`, `status`, `response_ref?`, `attempt_count`; open intent exists before session ID is known | Store/executor |
| `DispatchPermit` | `operation_id`, `commit_state_version`, `payload_hash`, `expires_at`, `lease_ref`, `fresh_observation_hash`; owned local capability, never created by a model | Store/coordinator |
| `ExecutionResult` | Tagged `acknowledged(operation_id,response_ref,terminal?,observation_events)`, `rejected(operation_id,status,proof_ref,issues)`, `uncertain(operation_id,cause_code,recovery_required=True)`; no fabricated commercial result | Executor/recovery |
| `NegotiationEvent` | `event_id`, `schema_version`, `run_id`, `session_id?`, `local_seq`, `occurred_at?`, `recorded_at`, `source_key?`, `correlation_id`, `parent_event_ids`, `payload: EventPayload`; exact tags below | Store commits; components propose |
| `EventPayload` | `SessionObserved`, `MessageObserved`, `DocumentObserved`, `AssessmentRecorded`, `DecisionRecorded`, `OperationPrepared`, `OperationSubmitted`, `OperationAcknowledged`, `OperationRejected`, `OperationUncertain`, `ClaimReserved`, `ClaimReleased`, `FeedbackObserved`, `TerminalConfirmed`, `RecoveryRequired`; each references typed artifacts described above | Schema registry; pure projector |
| `FeedbackObservation` | `operation_id`, `decision_id`, `response_refs`, `package_changes`, `claim_attributions`, `hypothesis_support`, `question_updates`, `issues`; causality status `observed_sequence`, never default causal | Feedback processor |

`IssueCode` is a closed versioned enum initially including `missing_source`, `source_conflict`, `stale_source`, `future_source`, `unknown_basis`, `scope_mismatch`, `unsupported_capability`, `invalid_schema`, `infeasible`, `nonfinite_cost`, `uncertified_price`, `unsupported_claim`, `private_disclosure`, `stale_state`, `deadline_exhausted`, `rounds_unknown`, `operation_pending`, `model_timeout`, `model_invalid`, `ungrounded_output`, `store_conflict`, `recovery_required`, and `invalid_terminal_proof`. Do not classify unrelated provider errors with free-form strings alone.

## 3. Port sketches and module contracts

Async interfaces are used for I/O and optional model-capable policies. Pure economics, resolution, validation and projection remain synchronous and independently callable. CPU-bound work is admitted/bounded; moving it into a thread does not cancel it. The loop controls absolute deadlines via the injected Clock and supervised tasks. Domain ports do not assume asyncio/provider internals.

```python
class ContextBuilder(Protocol):
    def build_context(
        self, prepared: PreparedEvidence, case: CaseContract,
        server: ServerState, documents: tuple[DocumentRecord, ...],
        as_of: datetime,
    ) -> EvidenceContext: ...

class SupplierInterpreter(Protocol):
    async def interpret(
        self, context: NegotiationContext, conversation: ConversationView,
        previous_assessment: SupplierAssessment | None,
        budget: DecisionBudget,
    ) -> SupplierAssessment: ...

class StrategyProposalPolicy(Protocol):
    async def propose_strategies(
        self, context: NegotiationContext, assessment: SupplierAssessment,
        state: NegotiationState, budget: DecisionBudget,
        research: CandidateResearch,
    ) -> IntentBatch: ...

class CandidateGenerator(Protocol):
    def generate_candidates(
        self, intent: StrategyIntent, context: NegotiationContext,
        state: NegotiationState, budget: DecisionBudget,
    ) -> GenerationResult: ...

class EconomicEvaluator(Protocol):
    def evaluate_package(
        self, package: Package, supplier_id: str, context: EconomicContext,
    ) -> PackageEvaluation: ...

    def evaluate_candidates(
        self, candidates: tuple[CandidateAction, ...],
        context: NegotiationContext,
    ) -> EvaluationBatch: ...

class ActionSelectionPolicy(Protocol):
    async def select_action(
        self, candidates: EvaluationBatch, assessment: SupplierAssessment,
        state: NegotiationState, budget: DecisionBudget,
        research: CandidateResearch,
    ) -> NegotiationDecision: ...

class CandidateResearch(Protocol):
    async def evaluate_intents(
        self, intents: IntentBatch, budget: DecisionBudget,
    ) -> EvaluationBatch: ...
    # Bound to one snapshot; code generates/prices; no live replies/state writes.

class ClosingEvaluator(Protocol):
    def decide_close(
        self, context: NegotiationContext, state: NegotiationState,
        reason_code: str,
    ) -> CloseDecision: ...

class ClaimVerifier(Protocol):
    def verify(
        self, candidate: ClaimCandidate, evidence: EvidenceContext,
        recipient_id: str, usage: tuple[ClaimUsage, ...],
    ) -> ClaimVerificationResult: ...

class ActionRenderer(Protocol):
    def render(
        self, decision: NegotiationDecision | CloseDecision,
        selected: EvaluatedCandidate | None,
        claims: tuple[VerifiedClaim, ...], context: NegotiationContext,
    ) -> RenderedAction: ...

class ActionValidator(Protocol):
    def validate_action(
        self, action: RenderedAction, context: NegotiationContext,
        state: NegotiationState, budget: DecisionBudget,
    ) -> ValidationResult: ...

class DecisionEngine(Protocol):
    async def decide(self, snapshot: DecisionSnapshot) -> DecisionOutcome: ...

class FeedbackProcessor(Protocol):
    def process_feedback(
        self, previous_state: NegotiationState, operation: PendingOperation,
        response: ConversationMessage,
    ) -> tuple[EventProposal, ...]: ...

class StateProjector(Protocol):
    def apply_event(
        self, state: NegotiationState, event: NegotiationEvent,
    ) -> NegotiationState: ...

class StateStore(Protocol):
    async def load_state(self, run_id: str, case_id: str) -> NegotiationState: ...
    async def persist_state(
        self, expected_version: int, commit: DecisionCommit,
    ) -> CommitResult: ...
    async def append_observations(
        self, expected_version: int, events: tuple[EventProposal, ...],
    ) -> CommitResult: ...
    async def pending_operations(self, run_id: str) -> tuple[PendingOperation, ...]: ...

class ActionExecutor(Protocol):
    async def execute_action(
        self, action: ValidatedAction, permit: DispatchPermit,
        operation: PendingOperation, budget: TransportBudget,
    ) -> ExecutionResult: ...
    async def reconcile(
        self, operation: PendingOperation, context: NegotiationContext | None,
        state: NegotiationState, budget: TransportBudget,
    ) -> ExecutionResult: ...

class ArenaGateway(Protocol):
    async def observe(self, session_id: str, budget: TransportBudget) -> ServerObservation: ...
    async def submit(self, operation: PendingOperation, budget: TransportBudget) -> GatewayResult: ...
    async def fetch_document(
        self, session_id: str, attachment_id: str, budget: TransportBudget,
    ) -> DocumentBytes: ...

class ModelGateway(Protocol):
    async def complete(
        self, request: ModelRequest, budget: ModelBudget,
    ) -> ModelResult: ...
```

`ValidationResult` is tagged `valid(action: ValidatedAction)` or `invalid(report: ValidationReport)`. `ClaimVerificationResult` is tagged `verified(claim)` or `rejected(issues)`. `ClaimCandidate` has the VerifiedClaim commercial fields but no verification certificate and its proposed sentence is ignored/recomputed. `EventProposal` has event kind/artifact refs/source key/correlation/parent refs/timestamps but no assigned local sequence. `DecisionCommit` contains run/case IDs, expected config/context hashes, decision/artifact refs, event proposals, optional validated action, and proposed claim reservations; exactly one operation may be prepared in first-slice scope. `CommitResult` is `committed(new_state,operation?,permit?)` or `conflict(current_version,issues)`.

`TransportBudget` contains absolute `deadline_at`, request/reconciliation attempt limits, submission and terminal-read reserves, lease identity and clock evidence. `ServerObservation` carries parsed case/session/threads/doc descriptors, raw response hashes, source keys and clock evidence; adapters store raw JSON bytes for audit. `GatewayResult` distinguishes authoritative response, definite rejection, and unknown outcome. `DocumentBytes` contains session/attachment identity, byte reference/hash/media type/receipt metadata, never a live client object.

`ModelRequest` contains task/schema/prompt versions, a purpose-specific `ModelInput` tagged union, provider/model configuration, correlation ID and output schema hash. `ModelResult` is tagged success with validated response bytes/usage/latency/call ID, refused, invalid, timeout, capacity-unavailable, or transport failure. No secrets appear in either. `ModelBudget` gives absolute deadline, max tokens, max calls and retry policy (zero initial retries). `ModelInput` is an interpreter/selector/simulator projection; it is not NegotiationContext serialized verbatim.

### Evidence/context contract

**Owns:** static preparation, layered resolution, case/supplier/part relevance, freshness/basis/disclosure and canonical evidence representation. **May call:** injected source/document ports; canonical verifier. **May not call:** strategies, model provider, executor or state writes.

`prepare(source manifests)` builds typed records/indexes before opening, not an offline strategy decision. `build_context` receives PreparedEvidence, complete case and current observed messages/documents. Precedence for identical canonical IDs is **case > release > base**; replace the record rather than silently filling missing case fields from older data. Attribute-level merging requires an explicit registered source contract with per-field provenance. Resolve supplier-specific versus generic cost by applicability/specificity after layered ID resolution; prefer applicable supplier-plant records over base-country estimates, then documented layer/validity within that scope. Same-priority conflicting rows become a blocking Conflict, not arbitrary SQL order.

Base SQL and release CSV facts are normalized into the same record index for families used by V2. Missing unused table coverage is a gap, not permission to query stale SQL for a “better” value. Current quote standards remain a separate typed contractual view; they do not override unrelated canonical facts. Identical record revisions are shared by estimator and claim builder.

Cache prep by content manifests/parser/schema versions; cache context by prep/case/live-message/document/freshness-rule/as-of evaluation inputs. Load the prep artifact explicitly at runtime, verify hashes before clocks, and reject mismatched frozen sources. Source changes invalidate dependent estimate, claim and candidate evaluations. Do not recompute an entire package tree hash on every turn. Missing optional evidence yields gaps and reduced capabilities; missing schema, basis or required cost source blocks dependent action. Test overlay replacement, SQL-vs-fact collisions, hidden suppliers, multiple parts, stale/future data, and shared claim/estimate resolution.

### Interpreter contract

**Owns:** attributed commercial observations and separate preference hypotheses. **May call:** injected ModelGateway and deterministic fallback. **State:** none beyond version-keyed cache. Inputs include the conversation, previous assessment, and filtered evidence view; outputs cite source spans/revisions.

Async model request with an initial eight-second maximum subject to the smaller total remaining budget. Cancellation prevents result application; no daemon thread may later change state. Validate schema, ID scope, quote spans, enum fields and unknown-vs-observed distinctions. Exact quote alone does not prove entailment or sender approval authority. Supplier statements remain statements even if forcefully expressed; supporting/contradictory canonical data is retained. Do not turn “longer term might help” into an observed 5% discount. Fallback returns `status=fallback`, preserves previous valid hypotheses with stale labels, and extracts only safely observed structured fields/known literal signals. If nothing is grounded, output explicit unknowns; do not synthesize a successful interpretation.

Tests use fake model transports for output/control faults and manually labelled recorded/edited P10 replies for semantics. Live model evaluation is a separately authorized future activity. External text has data delimiters, bounded input, no transport tools and no credential/private-economic input.

### Strategy proposal and selection contracts

Register vetted `StrategyBundle(id, version, proposal_policy, selection_policy, supported_case_types, required_capabilities, memory_schema?, config_schema, prompt_versions)` in a local Python registry. Resolve configuration before opening; unknown bundles and incompatible capabilities fail preflight. No arbitrary model-selected Python imports or service plugins.

Proposal and selection are separate replaceable policies but can share a bundle's private pure algorithm. Proposal emits nonbinding intent kinds/dimensions/directions and evidence refs; it supplies neither authoritative prices nor arbitrary contractual values. Selection may choose only approved items from the exact batch hash. A selected question/close request may have no package cost; that must not become zero cost in ranking. V1Adapter wraps its existing deterministic decision and passes it to the same economic/validation boundary; it is distinct from the pure `baseline` strategy ported for V2 fallback. A legacy hold becomes a typed hold; a legacy close/accept/walk recommendation becomes a request for the coordinator's fresh closing evaluation, with the original recommendation retained as a diagnostic artifact. Legacy offer sheets become candidates and must pass independent checks. Legacy body text is retained for comparison but adapted execution uses the reviewed renderer; that can change behavior and is recorded as `v1-adapted`, never silently relabelled `v1-legacy`.

`CandidateResearch` is a closure over the same snapshot and bounded candidate/evaluation budget. It lets lookahead/optimization request more intent-generated candidates. Additional candidates pass the same evaluator and are added to an auditable batch before final selection. The facade registers the immutable union of evaluated batches; `approved_batch_hash` identifies that final registered set, and the engine checks both ID membership and evaluation identity against it. A selector cannot choose an ID from an unrecorded simulation. Strategy implementations can run private opponent simulation through an injected model gateway, but simulated replies are tagged hypothetical and never passed as authoritative `ServerObservation`.

Failures: empty proposals use baseline intent; unsupported intent yields a rejection; selection timeout/invalid ID/edited economics uses deterministic approved fallback. If no approved action exists, request deterministic close evaluation or recovery/cannot-decide rather than emit an invalid package. A previous dimension-level refusal blocks that exchange under the policy unless new cited evidence justifies reopening; repeating a package for transport replay is the same operation and is not a new strategic trial.

Contract tests substitute deterministic, fixture-adviser and research dummy bundles without editing evidence/economics/runtime. Selection tests assert candidate membership and immutable package hashes, not model prose. Baseline remains available independently of any model.

### Candidate/economic contract

**Owns:** legal option generation, numeric construction, complete official cost evaluation, estimate scenarios and economic certificates. **May call:** official kit adapter and evidence-derived typed estimates; no LLM. **State:** none; caches keyed by full economic fingerprint.

Generate within case schema, legal standards exceptions and bounds from CostPolicy. Include at least the valid baseline package and grounded one-dimension capacity variants where available; the initial scan is bounded by `candidate_limit`. Interpret infeasibility as a return reason, never snap untrusted values. Multi-sheet cost evaluates each sheet separately; no sum across mutually exclusive packages. Alternatives supplied by the supplier cannot be directly accepted unless they are current standing offers.

Initial relationship pricing: enumerate a deterministic finite code-derived set of positive two-decimal prices (scheduled/base price, applicable quoted price, anchored and bounded concession ticks, plus an admitted local refinement set), evaluate every retained package with nominal and scenario estimates, and choose only certified candidates. If no candidate satisfies the relevant ceiling, return an explicit rejection or a clarification/quote-request candidate. This is a bounded feasible search, not a claim of global optimum. Do not depend on current `price_for_cost`.

Before enabling a general solver, specify `mode=equal_cost` versus `mode=cost_ceiling`, positive bounded domain, preferred reference branch, no-solution/minimum semantics, output tick rules and exact official rounded-cost certification. Preserve a reference already satisfying the request. For nonmonotonic cost, return feasible intervals/roots only within a documented search scope; cost-decreasing branches mean flooring price is not necessarily conservative. A finite scan cannot prove the absence of all roots. A budget-exhausted search yields `search_complete=False`, never guaranteed infeasibility.

Compare EUR cost with explicit official rounding to cents; monetary certification must not accidentally reject a legal reference because binary floating subtraction exceeds a cent. Preserve official arithmetic inputs without dividing all quantities/prices by `price_unit`. Conversion at fact joins records both original basis and explicit comparable price. Unsupported basket basis blocks associated price estimates/claims while other legal case-level actions can still be supported.

`evaluate_package` works without a strategy or runtime. `evaluate_candidates` retains rejected entries with issue codes; it never returns “approved” when must-haves/schema/basis/numerics fail. The first slice can use nominal selection with scenario costs visible; choosing robust-scenario ranking is an explicit experiment treatment. Supplier-health penalty is soft economics, not a hard sustainable price floor. Independent tests verify kit parity, standard/fixed precedence, scenario ranking, unreachable ceilings, valid roots/ticks and missing estimates.

### Closing contract

`decide_close` resolves and revalidates all eligible standing sheets across live threads, validates recipient/session/offer ownership, and compares complete costs under the same estimate/scenario policy used in offers. An ordinary `agreed` response is not an exception. Unresolved operations are an operational gate enforced by validator/store/executor, not an invitation to select a conflicting close.

An executable alternative comparison is strict `deal_cost < alternative_cost`. With no executable alternative, use a named policy, initially accept a finite eligible standing deal if the configured must-haves/estimate policy admit it; otherwise walk away. Record operational fallback procurement cost separately. No-deal official score is an evaluation outcome, not an available quote or an invented expected utility. Additional risk-sensitive final counters require their own bounded policy and uncertain withdrawal model; they are outside the first default slice.

### Renderer/validator contract

Renderer owns wording but not numeric decisions. It assembles deterministic approved packages, canonical sentences and typed template questions; the model's rationale or supplier prose is never copied into outgoing text. It produces the exact final payload before validation, including evidence appended after package selection. If claims would exceed limits, the coordinator reruns selection with fewer claims; the validator does not silently strip IDs while leaving the assertion.

Validator calls injected economic and claim verification ports. It checks all new actions and admitted replays independently of their originating agent. Offers carry exactly all negotiable fields; accept/walk payloads exclude offer sheets and unintended mixed actions. Current official message limits are **subject ≤300 characters, body ≤8,000 characters, ≤3 term sheets, ≤20 refs, ≤5 attachments and ≤3 checked factual arguments**; the alternative structured-move route has different limits and is not initially exposed. Template brevity may be a configurable style target, never mistaken for protocol.

Verify explicit standard-value exceptions against the recipient's current quote/official contract; reject arbitrary outside-options values. Validate complete types/index-clause fields/must-haves, positive finite two-decimal price, permissible fixed/negotiable separation, cost/basis, evidence provenance/freshness/usage and confidentiality, supported action/status, rounds/deadlines, current snapshot, ownership and pending operations. Accept must match the recipient's live standing ID and recomputed economics; a valid offer on another supplier does not authorize this recipient.

Disclosure uses typed content lineage plus template allowlists. Regex leak patterns are supplemental; they cannot prove arbitrary model text safe. Claim reservation is a transaction with operation preparation, not a side effect of proposed claim selection. Released reservations require proof of no transmission; sent or unknown claims remain consumed conservatively. Claim results are mapped only when argument alignment is known; ambiguous mapping stays unknown.

Validation returns issues, never repaired prices or packages. Test it directly without engine/runtime, then assert every supported execution path calls it with the final payload, including questions, fallback, close and replay admission.

### State and feedback contract

`apply_event` is pure and rejects invalid sequence/session/schema transitions. `load_state` projects the latest valid snapshot plus subsequent events. `persist_state` is the atomic expected-version commit boundary; callers cannot persist arbitrary altered server status. Assessment/decision artifacts can be stored without advancing the negotiation head; committing their strategic meaning and operation together advances local sequence, avoiding self-invalidating snapshots.

Store assigns contiguous sequence under transaction; unique `(run,event_id)` and official source keys deduplicate repeats. Out-of-order message arrivals are recorded with original server order/ref, then reconciled before new decisions. Duplicate event application is idempotent by ID; mismatched contents for one source key create a conflict. Persist UTC/server evidence and derive local elapsed time with Clock. Claim reservations/attempts move to submitted/acknowledged based on proven execution events, not strategy calls.

Feedback returns EventProposals and writes nothing. It joins operation/decision/candidate/response, records actual package differences (single-field or combined), explicit question-response linkage, claim-result alignment and structured observed support/contradiction. Semantic refusal/answer/support attribution comes from the next validated assessment, not an unimplemented deterministic understanding of arbitrary prose; applying `AssessmentRecorded` produces the source-linked strategic refusal revision. A later price reduction is an observation, not an estimated causal effect of an argument. Refusals and source messages survive restart. Recompute assessments using raw evidence; never rewrite canonical facts to agree with a model.

Test projection roundtrip, crash at every transaction/dispatch boundary, duplicate/out-of-order events, refused exchange after restart, claim reservations with unsent/unknown outcomes, schema upgrade and corrupt/truncated legacy logs. Startup does not forget unsupported events; it refuses unsafe projection and preserves files for diagnosis.

### Executor, recovery and gateway contract

The executor does not change the selected strategy, packages, claims or wording. It accepts only a validator-issued action linked to a committed operation and valid dispatch permit. Exact canonical payload bytes/hash and logical ID are persisted before any POST. It verifies permit/state/context/economic freshness after limiter queue; for first serial scope the coordinator retains ownership while awaiting transport. New server observations invalidate unsent stale permits.

If the action was proven never dispatched, invalidate that operation and create a newly validated action/ID for changed state. If possibly dispatched, preserve its ID/payload and reconcile; do not mutate it into a different action. Recovery fetches permitted authoritative state and operation evidence. A same-ID replay requires ownership plus safe protocol/validation admission; if the old accept is stale and its prior fate is unknown, keep uncertainty rather than manufacture a replacement close. Idempotent cached success records original response timing, not a fresh deadline.

Gateway exposes only session/message/document/case/quota methods actually needed, with path allowlisting. Public leaderboard/events/screen/backoffice/results routes are absent from the live capability surface. Official terminal information from an owned session is allowed; spectator result endpoints are not. An open intent is durable before session creation; unclear open outcome cannot cause a fresh duplicate open.

On transport timeout/cancellation: return uncertain, preserve ownership and reservations, bound retries/reads within TransportBudget, and return recovery-required when exhausted. On definite rejection: retain evidence and free ownership only when definitively safe. On terminal proof: store ended once; score/result enrichment may follow without reopening the case. Collect/cancel local tasks in guaranteed cleanup without asserting remote cancellation. Tests assert bounded exit and durable ambiguity rather than insisting every injected fault yields a deal.

## 4. Configuration and provider projections

`EffectiveConfig` fields: `schema_version`, `agent_id/version`, `strategy_bundle_id/version`, `interpreter_id/version`, `selector_id/version`, `evidence_policy/version`, `template_version`, `sources: tuple[SourceManifest]`, `prep_hash`, `economic_policy`, `closing_policy`, `fallback_policy`, `runtime_mode`, `capabilities`, `budgets`, `model: ModelConfig?`, `provenance: tuple[ConfigOrigin]`, `config_hash`. Model config contains provider/protocol/base endpoint identity/model/effort/sampling/max tokens/timeouts/schema support; credentials are references supplied only to infrastructure. `ConfigOrigin` names file/CLI/env/default origin and public field value. No ambient variable is read during decision generation.

Interpreter input: source-linked supplier prose/roles, permitted non-private case dimensions/options, relevant disclosed-or-approved internal contextual snippets, prior observed/hypothesized assessment, and unknowns. It excludes buyer reservation/target, no-alternative disclosure, urgency, official score/Cbest and full supplier-cost estimates.

Selector input, if enabled: approved candidate IDs/packages, grounded assessment and attempted/refused history, bounded relative economic descriptors (`cost_delta`, admissible/uncertain and scenario ordering) rather than absolute reservation/fallback values. Runtime code may use full private costs internally. Numeric terms remain approved package data; model may only return ID/citations/rationale. Raw notes require classification because historical text can contain private values.

Simulator input, later: same permissible projection plus tagged synthetic prior responses and bounded horizon. Simulated willingness/probabilities remain hypotheses. All provider calls record model/protocol/prompt/schema identities, latency, cache status, usage and fallback without secret-bearing request headers.

## 5. Independent implementation boundaries

| Team responsibility | Receives / produces | Contract tests it owns | Existing useful code |
|---|---|---|---|
| Domain/backbone | Frozen schemas, fixture codec, ports/errors | JSON strictness/hash/version roundtrip; imported dependency boundaries | Lab StrictModel patterns, current records |
| Evidence | SourceManifest + case/server -> PreparedEvidence/EvidenceContext/VerifiedClaim | Source priority, same claim/estimate records, scope/basis/freshness/conflicts | DataPackage/readers, Claim render/check |
| Interpretation | Context/conversation/previous -> SupplierAssessment | Grounding and A–F semantic labels; timeout/refusal/invalid fallbacks | Adviser output/schema/quote pattern, trait source refs |
| Strategy | Context/assessment/state -> intents; approved batch -> ID | Candidate membership, refusal avoidance, counterfactual responsiveness, interchangeable bundles | Pure portions of schedule/adviser/trades |
| Economics | Intent -> candidates; Package -> independent evaluations/close | Official parity, legal ticks, scenario costs, infeasibility and eligibility | Official arithmetic, option enumeration |
| Execution/runtime | Rendered -> Validated -> committed exact operation -> outcome | Every path validation, recipient/close authority, crash/replay/time/uncertainty | HTTP and journal concepts, simulated server |
| State/feedback | Typed events -> state; action/response -> observations | Restart identity, dedupe, preserved refusal/claim/question/operation state | Journal tests, revealed_deltas |
| Evaluation/Lab | Trace/attempt/config -> comparable outcomes | Complete manifests, failure inclusion, session joins, UI final-action view | Existing Lab models/stores/checkpoint/campaign/UI |

Owners can implement internals independently using shared model/port fixtures. A fake implementation must use the same typed result/error behavior as a real implementation. No module may add a hidden dict/ambient-environment shortcut to get around a missing agreed contract.

## 8. Frozen implementation defaults and executable binding

This section resolves the earlier sketches and takes precedence where they leave a choice open. [Test catalog](test-catalog.md), [task specifications](task-specs.md), and [implementation instructions](implementation-guide.md) are extensions of A–F. No separate architecture is introduced. Contract changes require a dated decision, fixture migration and affected-consumer list; an agent must not choose a different schema to simplify its implementation.

### 8.1 Minimal contract, strict parsing and errors

Keep the single `core/models.py` until its size justifies a reviewed split. Implement models in the ordered batches in D and task-specs; do not invent service bases, dependency containers, agents, routers or arbitrary plugin loaders. Schema version is the literal `negotiator-v2/1`, inherited by serialized domain models. Fixture envelope version is separately `negotiator-v2-fixtures/1`. `core/ports.py` uses the exact names, argument order and sync/async forms in `tests/v2/support.py:PORT_SIGNATURES`; unresolved model annotations may initially be strings. Do not replace typed port parameters with generic dictionaries.

Validate through `model_validate_json` at the JSON boundary. JSON arrays become immutable tuples. Domain Python constructors require Decimal/date/tuple values; wire floats are converted from their decimal text only inside adapters. TermBinding validates by field before the broad union can mistake price strings for ordinary text. Reject booleans as integer/Decimal values, unknown fields, nonfinite amounts and ambiguous types. Core Price is positive/finite; the final validator additionally requires two-decimal ticks. Incoterm starts with EXW/FCA/DAP. Package bindings have unique names and contain exactly the transmitted negotiable fields; fixed fields belong in ResolvedTerms. Package fingerprints hash sorted bindings and declared basis, excluding the fingerprint itself. Explicit null index clauses are legal; omitted index binding is distinct. Index dates are YYYY-MM and effective dates are real ISO dates.

`ResolvedTerms` has `bindings: tuple[TermBinding,...]` and `origins: tuple[FieldOrigin,...]`, exactly one origin for each resolved field. Incoming malformed/outside-option sheets are ObservedSheet plus issues. The replay codec must preserve P10's 54-day incoming lead, never turn it into an outgoing Package. The case adapter retains original raw case bytes separately and projects only known fields; unknown commercial fields block capability preflight. Noncommercial official metadata such as `set`, briefing and trigger_doc remains in the raw artifact and is not rejected merely for existing there.

Expected commercial failures return existing tagged results and IssueCodes: missing/unsupported evidence, infeasibility, rejected action, unavailable alternative, model fallback and uncertain execution. Broken programmer invariants raise `ContractViolation(ValueError)`; duplicate conflicting artifacts/record identities raise ValueError, not an expected-failure marker. Store CAS conflicts return `conflict`. Coordinator catches unexpected stage failures at the case boundary, records a failed stage and returns recovery_required without sending. The executor does not retry application bugs as transport faults. No bare exception handler substitutes zero costs or successful terminal results.

### 8.2 Supplier assessment: four separate collections

| Collection | Additional frozen fields/rules | Authority |
|---|---|---|
| observations | Existing GroundedObservation; nonempty citations; span offsets refer to original, unnormalized Unicode text; condition/refusal observations retain the exact statement | What the supplier said, never independent proof of the claim |
| reported_constraints | `ReportedConstraint(constraint_id, dimension: TermField, op: ==/!=/<=/>=, value: TermValue, condition_observation_refs: tuple[str], citations: tuple[Citation], authority: supplier_reported, status: active/stale/superseded)` | An attributed reported limitation; cannot change CaseContract, options or must-haves |
| hypotheses | Existing PreferenceHypothesis plus `direction: increase/decrease/enumerate/unknown`; active inferred preferences require supporting refs; numeric_effect absent unless an explicitly supported estimate method supplies it | Inference, with supporting AND contradicting refs and confidence label |
| uncertainties | `AssessmentUncertainty(uncertainty_id, kind: approval/conditional/contradiction/insufficient_evidence/missing_source, dimension?: TermField, summary, citations, related_observation_refs, blocking: bool)` | A gap or unresolved conflict; does not disappear on successful JSON parsing |

All tuple fields are supplied even when empty. unknowns remains a concise tuple of stable gap labels (for example approval, discount); it supplements the typed uncertainties. Citation equality does not establish semantic entailment. A reported 56-day limit conditional on 24 months must retain the condition reference. A stated need for manager approval is an observation/uncertainty; it does not turn the sender into an approver. “Might help” cannot become an observed discount or calibrated probability. Fallback includes a new assessment ID/revision, original model-call ref and issues in the decision record; retain earlier valid hypotheses as stale. The projector appends the new assessment and parent link; it never replaces historical assessments. No prompt/provider metadata belongs in CaseContract, Package or these commercial assertions.

Interpreter ModelInput is `AssessmentDraft` projection input: scoped supplier text and approved evidence citations only. Its response is exactly `observations, reported_constraints, hypotheses, uncertainties, questions, unknowns`; the interpreter supplies trusted snapshot, supplier, revision and call identity. Reject response extras such as action, reservation_cost and unit_price. The controlled model responses in p10.json demonstrate this draft schema. Provider ModelResult holds raw response JSON, so malformed model content can reach interpreter validation rather than being rejected by the replay codec first.

### 8.3 DecisionRecord: persistent artifact graph, not diagnostic prose

The [golden schema record](../../tests/fixtures/v2/decision-record.json) is normative for field names. It is a structural fixture, not evidence that its hash references are stored objects or that V2 executed a decision.

`DecisionRecord` fields: schema_version, record_id (UUID), decision_id (UUID), snapshot, revision (positive int), parent_record_hash (nullable), fixture_input_hash, config_artifact_ref, case_artifact_ref, evidence_artifact_ref (nullable), assessment_artifact_refs, intent_artifact_refs, candidate_artifact_refs, evaluation_artifact_refs, selection_artifact_ref (nullable), rendered_artifact_ref (nullable), validation_artifact_ref (nullable), operation_artifact_ref (nullable), execution_artifact_refs, feedback_artifact_refs, model_call_refs, model_output_hashes, issues, stages, semantic_hash, record_hash. The tuple fields are never omitted. References use `sha256:<64 lowercase hex>` for immutable stored bytes; official/correlation IDs remain inside referenced artifacts.

`DecisionStage` fields: schema_version, name, status, artifact_refs, issue_codes. Every revision lists these ten stages in this exact order: evidence, assessment, proposal, generation, evaluation, selection, rendering, validation, execution, feedback. Status is planned/completed/failed/skipped. Completed stages have artifacts; failed stages have issue codes. A skipped stage records a reason issue; it cannot masquerade as completed. Before selection, downstream stages are planned. Selecting requires nonempty evaluated-candidate refs; validation requires rendering; execution requires validated payload plus operation; feedback requires execution provenance. Failure never creates fabricated successful downstream stages. A selected strategy holds no execution authority.

Append revisions at meaningful boundaries. Revision 1 has no parent; revision n+1 references n's record_hash and retains the same decision ID. `record_hash` hashes canonical record JSON excluding record_hash itself. `semantic_hash` hashes an explicit semantic projection of config/case/input/context, assessment content, intent content, candidate packages and costs, selected contents, final payload hash, model output hashes, execution/feedback status and issues. Exclude UUIDs, local paths, receipt/export timestamps and incidental transport-attempt counters. Resolve content references before forming that semantic projection; do not hash unrelated arbitrary metadata out of every object. Do not omit model output variability. The schema-only golden's semantic_hash is a declared placeholder; storage/replay integration tests require a recomputed real projection.

SQLite persists artifact bytes and decision record revisions from M1. Reject conflicting contents for an existing record/revision/hash. Exact duplicate writes are idempotent. A record may describe an unresolved decision without changing the case to ended. M5 adds the atomic operation/state/claim transaction, using the same database and identity rules. No second trace store becomes state authority. Existing V1 traces remain readable under their original schema.

### 8.4 Composition seams and concrete names

| Path / exported constructor | Dependencies / additional API |
|---|---|
| evidence/context.py `LayeredContextBuilder()` | ContextBuilder; calls pure resolver/registered freshness rules, no raw SQL |
| evidence/claims.py `EvidenceProjections()` | `internal_cost_claim(context, canonical_id)` and `cost_input(context, canonical_id)` return typed ClaimCandidate/ResolvedCostInput from the same resolved record |
| evidence/claims.py `CanonicalClaimVerifier(*, oracle)` | ClaimVerifier; injected CanonicalClaimOracle, never legacy package discovery |
| adapters/claims.py `LegacyClaimOracle()` | Existing canonical render/check via a resolved facts-only view; no base-SQL fallback |
| adapters/official.py `OfficialArithmetic()` | OfficialCostOracle: `evaluate(case, terms, supplier) -> OfficialCostResult(total, components)`; converts to pinned kit arguments internally; preserve quote-reference standards in supplier estimate |
| economics/official.py `OfficialEconomicEvaluator(*, oracle)` | EconomicEvaluator; official oracle is mandatory injection, no direct kit import |
| economics/candidates.py `FiniteCandidateGenerator(*, evaluator)` | CandidateGenerator; finite positive ticks, baseline plus grounded allowed options, current budget |
| intelligence/interpreter.py `GroundedInterpreter(*, model, clock)` | SupplierInterpreter; purpose-specific projection, bounded validation/fallback |
| strategy/capacity.py `GroundedExchangePolicy()` | StrategyProposalPolicy; first capability is capacity, core remains generic |
| strategy/selection.py `DeterministicSelector()` | ActionSelectionPolicy; stable approved membership and case-cost tie order |
| strategy/selection.py `BoundedModelSelector(*, model, clock)` | Same port, optional T4.4; explicit fallback_code on invalid selection |
| execution/validation.py `FinalActionValidator(*, evaluator, claim_verifier)` | ActionValidator; additionally `validate_wire(payload_bytes, context, state, budget)` parses untrusted wire JSON into a valid or invalid result; parse failure cannot bypass the typed validator |
| orchestration/state.py `EventStateProjector()` | StateProjector; append-only assessments, truthful server projection |
| adapters/sqlite.py `SQLiteStateStore(path)` | StateStore plus async initialize(state), put_artifact(ref, bytes), get_artifact(ref), save_decision_record(record), decision_records(run_id, case_id), aclose() |
| config.py `resolve_config(raw, *, supported_strategy_ids=("baseline-v1","grounded-exchange-v1"))` | EffectiveConfig; reject extras and unsupported IDs, no environment reads |
| factory.py `build_offline_runtime(*, fixture, model, arena, clock, database_path)` | OfflineRuntime below; explicit injected replay ports only; no credentials/network provider construction |
| factory.py `build_decision_services(*, config, model)` | Typed services; `evaluate_and_select(intents, recorded_inputs) -> EvaluatedCandidate` runs generation/evaluation/selection, for read-only fixture comparisons |

Add OfficialCostOracle, CanonicalClaimOracle and Clock protocols to core/ports.py with these narrow signatures. Clock exposes utcnow()->datetime and monotonic()->float. FakeClock advances both; deadlines derive from observed UTC plus elapsed monotonic duration. Module imports are enforced by test_boundaries.py. Only adapters import arena_kit, legacy negotiator modules, httpx, SQLite or process/network APIs. All feature packages import core and their own package; factory imports implementations. Do not give economics a hidden default adapter or strategy a live-client attribute.

### 8.5 Fixture/replay binding and M1 scope

`adapters/recorded.py:load_inputs(normalized_fixture) -> RecordedInputs` is a codec and assembler for offline recorded inputs, not a strategy or implementation test oracle. It returns typed `prepared, case, server, documents, as_of, context, conversation, previous_assessment, state, budget, transport_budget, config, snapshot, research, packages, intent, candidate, assessment, evaluation_batch, rendered, wire_payload, model_result, selector_model_result, gateway_observations, gateway_results, artifacts, commit, record, conflicting_record, message_event, assessment_event, next_assessment_event, unproven_terminal_event`. Optional scenario-only entries may be null outside the tests requiring them. This is an adapter DTO, not a new domain mega-model or public live-engine input. Build typed objects with validated JSON/model constructors; never use model_construct to evade validation. Every artifact reference must resolve in integration/store tests.

Test-only builders.py removes expected outputs, chooses controlled raw model replies and constructs raw wire faults before calling the codec. `input_mutation` selects a **typed input fixture** (stale version, pending operation, claim attributes, recipient or standing-offer state), not an expected failure response. `replay_schedule` provides scripted raw server frames and `port_failure_schedule` supplies injected failing port doubles in the offline composition only. Implement their fixture bindings in tests/v2; live components must never inspect these labels. The codec preserves source layers independently, assigns deterministic content IDs and projects declared fields; it must not resolve winning facts, choose strategies or decide what a validator ought to return. Missing codec bindings are implementation work, not an excuse to skip a test.

OfflineRuntime exposes inputs, store, `run_once(snapshot)->ReplayResult`, `resume()->ReplayResult`, `close(*,reason_code)->ReplayResult`, and `aclose()`. M1 implements run_once and record storage with recorded/mock port dependencies; M5 completes resume/close and transactional runtime. ReplayResult has outcome, record, selected?, validated?, execution?, state, terminal?, close_decision?. Run_once connects actual typed ports and final persisted result. M1 scripted gateway acknowledgements are explicitly fake and never counted as Arena deals. The complete M1 demonstration uses the first frozen package (28.34/42/23400/24), cost €1,335,154.08 with estimates explicitly disabled; it does not claim strategic improvement or supplier health. It differs intentionally from V1's 35-day first move. Context/assessment are recorded mock components until their owning milestones replace them.

EffectiveConfig field inventory is the p10.json config block plus derived config_hash and optional explicit provider/protocol/prompt identifiers, never secrets. Minimum deadlines: 35-second compute cap, 8-second interpreter cap, 4-second optional selector cap, at most two model calls total, no automatic model retries, 5-second fallback reserve and 5-second submission reserve. candidate_limit=64; EUR price tick 0.01; minimum 0.01, maximum explicitly case-bound. Only fixture replay uses estimate_mode=disabled_explicit. Relationship-sensitive live readiness requires approved scenario estimates or a documented degraded-mode scope. Cache eviction and machine path never alter semantic decisions.

Tie defaults: preserve baseline when no grounded affordable trade exists; retain cited conditional/approval uncertainty as clarification; among economically approved supported exchanges use complete cost, then unchanged package, then canonical bindings, then candidate ID. A question has no monetary cost and is selected by its strategy purpose, never as a zero-cost offer. Controlled-candidate fixtures restrict variants to the grounded direction while retaining the baseline. A dimension refusal suppresses unsupported repetition; contradictory approval blocks the exchange pending clarification. These are first-slice policy defaults, not legal invariants or a learned supplier model.

### 8.6 Ownership, uncertainty and closing defaults

One outstanding logical operation per case. Persist exact request bytes and operation ID before dispatch. Unknown transport outcomes remain owned after retry exhaustion; never release claims or infer cancellation. Reconciliation reuses original ID/bytes only when current admissibility and idempotency evidence permit it; otherwise retain recovery_required. Unknown open cannot create another open. A stale pending accept against a replaced standing sheet cannot be retried. Durable definitive rejection may release a reservation only with proof of no transmission.

Only server terminal response/observation evidence changes server.status to ended. Three rejected closes with authoritative status open leave the case resumable. All close triggers invoke the same ClosingEvaluator and FinalActionValidator on fresh state, with current standing supplier/offer identity, full legal terms, current quote defaults, must-haves, basis, complete economic comparison and scenario policy. A missing executable alternative is tagged unavailable; operational fallback and no-deal score are separate values. Worker/proposal/parser/evaluator failure is supervised and recorded, never a completed commercial result. M5's failure tests govern serial runtime; async scheduling remains deferred.

### 8.7 Event hydration and transition rules

Pure projection needs the typed values, not just unresolved file references. Event payloads contain the following value plus its immutable artifact_ref; the store verifies their content agreement when committing. Tag field is `kind`, with these literal names. All previously listed envelope IDs/timestamps/source keys still apply.

| Event kind | Typed payload beyond kind/artifact_ref | State effect |
|---|---|---|
| SessionObserved | server: ServerState | Replace only official server projection, retain strategic history |
| MessageObserved | message: ConversationMessage, thread_state: ServerThread, rounds: RoundEvidence | Append/dedupe official message; use observed authoritative or conservative round evidence |
| DocumentObserved | document: DocumentRecord | Add attributed parse result; no inferred binding terms |
| AssessmentRecorded | assessment: SupplierAssessment | Append immutable revision, verify supplier/snapshot/parent identity |
| DecisionRecorded | record_ref: str | Reference stored DecisionRecord; not acknowledgement or terminal proof |
| OperationPrepared | operation: PendingOperation, claim_usage: tuple[ClaimUsage] | One new owned outbox operation with reserved usage, ready→awaiting |
| OperationSubmitted | operation_id, submitted_at: datetime | Record attempt, prepared→submitted; round not yet consumed without proof |
| OperationAcknowledged | operation_id, response_ref, server: ServerState | submitted/uncertain→acknowledged; update only parsed official state; repeated ack idempotent |
| OperationRejected | operation_id, proof_ref, definitely_not_applied: bool, issues | Definitive rejection recorded; unknown transmission remains owned |
| OperationUncertain | operation_id, cause_code: IssueCode | prepared/submitted→uncertain; preserve exact bytes/reservations; runtime recovery_required |
| ClaimReserved | usage: ClaimUsage | Same scope/operation reserve is idempotent |
| ClaimReleased | claim_id, scope_key, operation_id, no_transmission_proof_ref | Release only with authoritative no-transmission proof |
| FeedbackObserved | feedback: FeedbackObservation | Append observed-sequence feedback, no inferred causal gain |
| TerminalConfirmed | terminal: TerminalEvidence | ended only after validated parsed terminal evidence; cannot be supplied by supplier prose |
| RecoveryRequired | operation_id?: str, issues | Nonterminal operational return; retain official status and ownership |

TerminalEvidence contains session_id, status=`ended`, proof_ref, source_kind=`gateway_response`/`gateway_observation`, observed_at, optional deal/offer_id/supplier_id/score/cost/end_reason fields. proof_ref points to the raw authoritative gateway artifact, never a local attempted close. Missing optional score does not negate a proven terminal status and never becomes zero. Store/coordinator verify ownership/session and raw parsed proof; projector rejects an absent/mismatched proof. The fake codec can explicitly create unproven_terminal_event solely as a negative fixture. Strategy/interpreter cannot emit TerminalConfirmed.

Local sequence must be contiguous, duplicate event/source key contents identical, and events belong to the run/session. A new source-key collision with different contents is conflict, not dedupe. CAS uses expected version before the operation transaction; DispatchPermit refers to the committed version and original validated source snapshot. Saving an independent record does not advance that head. Restore from persisted accepted events regardless of experimental policy activation.

Record validation diagnostic strings are frozen for schema tests: `orphan_selection`, `stage_order`, `stage_issue_required`; unsupported literal versions identify schema_version. Recompute record_hash when making a negative structural fixture so a hash mismatch cannot hide a missing stage validator.

PreparedArtifactCodec in evidence/prepare.py exposes `encode(prepared)->bytes` and `decode(blob, *, expected_base_hash, expected_release_hash, expected_parser_versions)->PreparedEvidence`. It is a pure codec; filesystem/source loading remains in adapters. Verify content integrity, declared source manifests, parser versions and schema. Frozen runtime mismatches raise ValueError; an explicit pre-clock preparation command may rebuild. Never silently discover another package.

Interpreter/optional model selector constructors also require `clock` injection alongside model; C §8.4's constructors are `GroundedInterpreter(*,model,clock)` and `BoundedModelSelector(*,model,clock)`. Grounding schema checks and supplied deadline/clock are independent of provider identity. FakeClock advances UTC and monotonic elapsed together. A hung model is cancelled by the bounded waiter; a late result is discarded after checking elapsed/deadline before application, even if it is syntactically valid.

### 8.8 Remaining adapter-envelope defaults

For the remaining named DTOs, use the field inventory in §2/§3 with these resolved encodings. They are concrete boundary values, not extra service layers.

- ModelRequest fields: schema_version, call_id, task (`interpret`/`select`/`simulate`), task_schema_version, prompt_version, input (typed purpose projection), provider_id, model_id, protocol_id, effort (nullable), output_schema_hash, correlation_id. Credentials/headers are held by the injected provider adapter, never this DTO. ModelBudget fields: deadline_at, time_limit_s, max_tokens, max_calls, retry_limit=0. ModelUsage fields: input_tokens?, output_tokens?, reported_cost? (Money). ModelResult tagged kind is success/refused/invalid/timeout/capacity_unavailable/transport_failure; all variants have call_id/model_id/elapsed_s and issues. Success additionally has raw_response_json (string), response_hash and usage. This string may be malformed provider content; interpreter validation owns its schema. Selector response is exactly selected_id plus supporting_quote, no economics or custom fields.
- PreparedEvidence.parser_versions is an immutable tuple of `name/version` strings. Provenance field parser_version may be null. Every payload subtype has a literal `kind` (index/scorecard/cost/quote/contract/forecast/order_price/text/estimate); outer EvidenceRecord.kind still distinguishes canonical/statement/estimate/hypothesis. Physical price units and quantity_basis are declared by the case/source adapter; unsupported joins block economics rather than guessing a divisor.
- DecisionCommit extends §3 with operation_id? and proposed_operation?: PendingOperation. Either both are absent for a record-only commit, or they agree with one exact validated action/preflight open payload and source snapshot. IDs are generated before committing. Never generate a fresh ID when replaying an existing commit. StateStore persists the proposed operation in the same CAS transaction and verifies byte/artifact identity before issuing DispatchPermit.
- NegotiationState.server is nullable **only before a session is authoritatively identified**. Before open, no commercial DecisionSnapshot/action may be created. Unknown open remains a pending open with session_id null and runtime recovery_required. ActionExecutor.reconcile accepts `context: NegotiationContext | None` for this open recovery; known-session send/close requires the full context. The normal decision ports continue requiring a known-session snapshot. This avoids invented session identities to represent a lost open response.
- Raw validator parse/type problems use invalid_schema; a finite numeric nonpositive or sub-cent outbound price uses uncertified_price; a typed outside-option/must-have/close-cost failure uses infeasible. Unknown claims use unsupported_claim, undisclosable known claims/private template content use private_disclosure, temporal claim mismatch uses stale_source/future_source. Collect relevant issues; the test-specified issue must not be replaced by a generic failure.

Assessment/model/record/state fixture bindings belong to the owned task before their component gate; no production component may import expected_evidence, official_cost_goldens or test-manifest. Strict input parsing, concrete field-specific unions, typed result failures and explicit composition are the sufficient foundation. Do not expand these DTOs into a generic multi-agent framework.

Numerical failure is representable: PackageEvaluation.nominal_cost is null only when numerically_valid is false, with empty components/scenarios and nonfinite_cost issues. A valid evaluation requires finite nominal/component values. Catch explicit arithmetic domain failures (including zero supplier cash value even at a positive unit price and overflow), record the rejected evaluation and do not create a zero/infinite cost or approve the candidate. Unexpected non-arithmetic implementation failures remain supervised case errors. Economic fingerprints include actual buyer rates/basis/resolved terms/standards/estimates and cost-source revisions, excluding unrelated greeting/body prose.

The replay codec projects normalized evidence_layers.case into CaseContract.case_facts and base/release into PreparedEvidence without resolving winners. Synthetic STABILISE has an explicitly declared fixture-only part basis because its original test case lacks parts; never inherit P10's basis. Its nominal_explicit point estimate uses the supplied47-cost hypothesis (unknown uncertainty; fixture bounds may coincide), not disabled_explicit or robust_scenarios. Price_max is55.00 for that fixture,37.36 for P10. These arithmetic controls make no live supplier-health assurance.

ResolvedCostInput is the narrow typed projection returned by EvidenceProjections.cost_input: unit_cost:Price, source_refs:tuple[SourceRef], scope:EvidenceScope, temporal:TemporalValidity, issues:tuple[Issue]. It contains the exact record revision used by internal_cost_claim; do not confuse PriceBasis.source_refs (declared basis IDs) with economic evidence SourceRefs. Monetary/Decimal serializers use non-scientific canonical strings without insignificant fractional zeroes (28.3400→28.34); outbound price formatting/tick checks remain separate. Negative zero serializes as0. This does not repair invalid prices.

For validate_wire tests, RecordedInputs.wire_payload is the UTF-8 **internal action frame**, not a recipient-free Arena message: `{supplier_id, snapshot, kind, decision_ref, close_ref, template_version, claim_ids, message}`. The codec binds the raw wire_message under message and trusted source metadata separately; wrong-recipient/stale variants alter the relevant frame/state input. validate_wire parses that frame without snapping, then calls the same validate_action checks. Its successful certificate payload_bytes_ref/hash identifies only the exact outgoing Arena message bytes, not the internal frame. Render hash is recomputed from raw contents in fixture assembly so a generic hash mismatch cannot mask the intended invalid price/field/privacy assertion. Live renderer output follows the typed RenderedAction path; raw parse convenience never adds transmission authority.

IssueCode additionally contains not_applicable for a deliberately skipped stage; it is a reason, not a successful execution. Missing critical economic data or unsupported required scenario inputs block closing with ContractViolation/recovery_required rather than manufacturing a walk-away based on unevaluable costs. A walk-away is valid when known evaluable/legally unusable offers fail the closing policy; failed arithmetic is recorded explicitly.

### T1.1a–c foundation hardening decisions — 10 October 2026

These clarifications apply to `negotiator-v2/1`; no Protocol signature changes or golden
fixture revisions are required.

- Decimal identity uses finite, non-scientific strings without insignificant fractional
  zeroes; signed zero becomes `0`. Normalization must not round through the ambient Decimal
  context. Typed Decimal values retain their original coefficient/exponent in memory for
  provenance; JSON is canonical. Raw supplier quotes remain in MessageSpan/source artifacts.
  Ordinary text strings are never interpreted as numbers by the generic hash function.
- Package construction derives the fingerprint from field-sorted typed bindings and the
  declared PriceBasis, excluding the fingerprint. A supplied fingerprint must match. Binding
  order and equivalent Decimal representations do not change package identity; explicit null
  remains distinct from an omitted binding. Basis source references remain in the projection.
- Structured terms require real ISO calendar dates, real base months (years 0001–9999),
  nonnegative payment/lead/ppm values and charges, positive volume/contract duration and price.
  Identifiers must be nonempty and unpadded; content hashes are lowercase SHA-256 hex.
  Booleans never stand in for numeric values, including retry_limit=0.
- Raw supplier statements may be incomplete, ambiguous or malformed. Preserve those statements
  as cited observations/ambiguities/unknowns. ReportedConstraint is a structured assertion:
  its dimension/value must meet the same field typing and validity as TermBinding, even when
  stale or superseded. This validation conveys no legal or binding authority. Its authority
  remains supplier_reported; it cannot change case options, must-haves or contractual terms.
- EffectiveConfig parsing establishes schema validity only. `resolve_config` validates the
  explicit supported-strategy registry and verifies or derives the canonical config hash,
  marking the resulting immutable object as verified in private, nonserialized metadata.
  `require_verified_config` is the mandatory gate before future executable construction:
  reject parsed/reloaded-only objects, revalidate schema/registry/hash and reject copies whose
  contents changed after verification. Reloaded configuration must pass through resolve_config.
  No runtime constructor exists in T1.1a–c; future factory/composition must call this gate.
  This is a Python application trust boundary, not a security sandbox against arbitrary code
  that deliberately mutates private internals or bypasses model validation.


### 8.9 Final remaining T1.1d field contracts — 10 October 2026

**Status:** specification/test handoff only, based on `a88bf86`. No production DTOs are
implemented by this revision. This section supersedes ambiguous sketches/tables for remaining
DTOs; T1.1a–c and the four completed evidence metadata DTOs remain unchanged. Consumer list:
recorded codec, evidence resolver/preparation/projections, official-cost/estimate/candidate/
selection services, renderer/validator, projector/store/executor/recovery, model adapters,
feedback and offline factory. Protocol names, arguments and sync/async forms stay frozen.
There is no golden migration: existing golden objects contain none of the changed DTO shapes.

The normative field tables below and `tests/v2/dto-contracts.json` give the same closed inventory.
The JSON is **test-only**, never a production registry, loader, service base or DTO generator.
`tests/v2/dto_spec.py:example(name)` hydrates a concrete valid JSON example of every export;
`negative_example(name)` applies the exact listed invalid field mutation. These objects are
schema examples, not source-winner, strategy, persuasion or execution answers.

#### Exact type notation, defaults, serialization and ownership

Every concrete model extends existing FrozenModel (strict/frozen/extra-forbid), inheriting
schema_version=`negotiator-v2/1`. Required fields must not be inferred/defaulted. Nullable fields and their null defaults
are listed explicitly below. Here `?` means optional with **default null**; the only other default is
QuestionAction.claim_ids=(). `T[X]` means immutable `tuple[X,...]`, required even when empty.
`L[a,b]` means `Literal["a","b"]`; `L[True]` means strict boolean literal True. Tags are required.
All other model names denote those exact models; unions use Annotated[...,Field(discriminator)]
with the discriminator declared below. No dict/Any payload or unknown-tag fallback is permitted.

| Token | Exact Python/domain contract and JSON |
|---|---|
| Id | str; nonempty, no leading/trailing whitespace; official IDs remain opaque (no invented prefix regex) |
| Label | str; nonempty after whitespace check; retain original source spelling; never executive authority |
| Summary | str; nonempty, at most 1000 Unicode characters; internal/canonical bounded text, never model chain-of-thought |
| str | strict str; empty allowed for raw text/subject/body/quotes |
| Hash | str matching `[0-9a-f]{64}` |
| ArtifactRef | str matching `sha256:[0-9a-f]{64}`; referenced bytes immutable, existence checked by owning adapter/store |
| UUID | uuid.UUID; JSON canonical UUID string, Python constructor requires UUID, never bool or arbitrary local ID |
| bool | strict bool, never 0/1 |
| Decimal | decimal.Decimal finite; Python requires Decimal, JSON requires decimal string; existing canonical normalization, no implicit float/bool/string Python coercion |
| NonnegativeDecimal / PositiveDecimal | Decimal with >=0 / >0, respectively |
| Percent | Decimal in [0,100]; percent points, not fraction or probability |
| NonnegativeInt / PositiveInt / ZeroInt | strict int >=0 / >0 / exactly 0; bool and float rejected |
| Date | datetime.date; real exact YYYY-MM-DD JSON; Python requires date excluding datetime |
| UTC | timezone-aware datetime.datetime with zero UTC offset; ISO JSON with UTC offset; Python requires datetime; naive/nonzero offset rejected |
| Month / Quarter | str, real `YYYY-MM` / `YYYYQ[1-4]`, ASCII year 0001..9999 |
| CountryCode | str, exactly two uppercase ASCII letters; source country label (DE etc.), not a cost value |
| RelativePath | str; nonempty relative POSIX path; reject absolute/backslash/NUL/dot/dotdot path segments; adapter checks symlinks against root |
| TermField / TermValue / Citation / IssueCode | unchanged foundation aliases; field-dependent values always validate through TermBinding semantics |

Tuple IDs/keys that identify members are unique wherever listed below. Ordered histories and
source-ref tuples are not globally reordered or deduplicated. Null numeric data remains null.
Money may be signed; penalties/usage costs explicitly declared nonnegative are checked by
containing models. Arithmetic/option eligibility, entitlement, registry approval, raw bytes,
proof content and current state are verified by their **service owners**; parsing a DTO never
issues a runtime certificate. Format and specified intra-object invariants are DTO-owned.
Hashes explicitly service-owned below are **not** recomputed by schema constructors. Package
fingerprint construction, Decimal hashes and verified EffectiveConfig gates remain unchanged.

Ownership: D1/D2 source adapters/evidence resolver/preparation; D3 official case adapter;
D4 evidence-derived estimator/economic input builder/official-cost adapter; D5 proposal/
generator/evaluator/selector; D6 gateway/coordinator; D7 claim verifier/closing evaluator;
D8 renderer/final validator; D9 budget service/store; D10 feedback/projector; D11 coordinator;
D12 gateway/provider projections; D13 provider adapter; D14/D15 event proposer/store/projector;
D16 executor/recovery/offline assembler. A source claim never acquires authority through types.

#### Resolved design decisions (preserve existing interfaces)

- **NamedEstimate.name:** registered closed enum, not arbitrary validated string. Registered
  methods `fixture-point-v1`, `source-cost-v1`, `supplier-scenarios-v1` accept the five exact
  names below. Units/ranges/basis are checked by name. Adding a method/name is an explicit
  contract revision; no dynamic registry/plugin framework. Estimates remain hypotheses.
- **EconomicContext.scenario_policy:** concrete ScenarioPolicy plus EstimateScenario.
  Scenario IDs refer to explicit SupplierEstimate IDs; no weights/acceptance probabilities.
  Disabled, nominal and robust modes retain their distinct current EffectiveConfig meanings.
  Missing required estimate/supplier coverage fails construction, never silent disabled mode.
- **standards_by_supplier:** tuple[SupplierStandards,...], with unique supplier keys and typed
  ResolvedStandards. No frozen model containing a mutable dict.
- **ResolvedTerms:** use `origins` from §8.1. ResolvedStandards retains `field_origins`.
- **TerminalEvidence:** use §8.7's status/proof_ref/source_kind/observed_at shape, replacing
  earlier source/official_result_ref/result_hash sketch. Missing score is null. DTOs can hold
  unverified proof references; only store/projector content validation establishes termination.
- **V1 data compatibility:** CostFact.cost_base is a source country code, as in dossiers._cost_row,
  not EUR. confidence_pct is uncertainty half-width, not calibrated probability. Quarter strings
  follow claims.py YYYYQn; forecast/order quantities may be fractional. Evidence percentage
  numerics are Decimal; adapters explicitly convert official numeric text. Canonical cost/index
  facts remain attributed source facts, not supplier willingness or executable offer terms.
- **Action encoding:** MessagePayload uses packages and an optional WireAction typed union;
  Arena adapter alone converts to term_sheets/terms JSON. No Protocol signature changes.
  construction_refs remains tuple[str,...] from the CandidateAction sketch, naming construction
  source IDs. UUID decision/event/operation/attempt IDs follow universal rules.
- **ModelSuccess:** response_hash hashes exact raw UTF-8 response text. Malformed JSON is a
  valid transport success example and reaches interpreter schema validation. Timeout/refusal/
  invalid/capacity/transport variants are separate typed results, never numeric zero outputs.
- **Feedback:** explicit PackageChange/ClaimAttribution/HypothesisSupport/QuestionUpdate values;
  causality_status is always observed_sequence. Null claim_id retains uncertain attribution.
- **Capabilities:** schema preserves known official category/case/thread values. Capability
  preflight still restricts actual services to their approved slice; a valid CaseContract is
  not a declaration that RFQ/bundling/quality behavior is implemented.

#### Exact remaining exports, examples and invalid mutations

Each row names its batch, exact fields, DTO invariants and invalid example mutation.
All tuples are immutable; field defaults follow the notation above. Definitions are ordered
by handoff, not necessarily by within-file declaration; forward references are resolved once
all models of that handoff exist. Every union member is a separately tested concrete export.
The 50 additional cases in the JSON handoff exercise registry/bounds, fractional quantities,
source labels, nominal/robust coverage, standing-sheet preservation, raw provider content and
message/close authority. They supplement the individual export tests rather than replace them.

##### D1

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `IndexFact` | `kind: L[index]; series: Id; month: Month; value: Decimal; unit: Label` | Finite index value; no guessed conversion or unit. Month is YYYY-MM, year 0001..9999. **Negative:** `{"month":"2026-13"}` |
| `ScorecardFact` | `kind: L[scorecard]; supplier: Id; quarter: Quarter; window_months: PositiveInt; otd_pct?: Percent; ppm?: NonnegativeInt` | Supplier-level fact; missing metric remains null. PPM is a count per million, not a percent. **Negative:** `{"otd_pct":"101"}` |
| `CostFact` | `kind: L[cost]; part: Id; supplier?: Id; unit_cost: Price; confidence_pct?: Percent; cost_base?: CountryCode` | cost_base is the two-uppercase-letter source country code (e.g. DE), matching V1 should-cost data; null is unknown. confidence_pct is source uncertainty half-width percent, not calibrated probability. unit_cost is the declared priced basis. **Negative:** `{"confidence_pct":"-1"}` |
| `QuoteFact` | `kind: L[quote]; supplier: Id; part_ids: T[Id]; price: Price; observed_terms: T[TermBinding]; validity?: TemporalValidity` | Nonempty unique part_ids equal the set in price.basis; unique typed observed term fields; validity is source timing, not standing-offer eligibility. **Negative:** `{"part_ids":[]}` |
| `ContractFact` | `kind: L[contract]; supplier: Id; part_ids: T[Id]; notice_days?: NonnegativeInt; clause_refs: T[SourceRef]` | Nonempty unique parts. clause_refs name immutable evidence revisions containing clause text, not unverified commercial bindings. **Negative:** `{"notice_days":true}` |
| `ForecastFact` | `kind: L[forecast]; part: Id; period: Month; quantity?: NonnegativeDecimal; change_pct?: Decimal` | Quantity may be fractional; change_pct is signed percentage points, finite with lower bound -100. Null is unknown, never zero. **Negative:** `{"change_pct":"-101"}` |
| `OrderPriceFact` | `kind: L[order_price]; supplier: Id; part: Id; price: Price; order_date: Date; quantity?: PositiveDecimal` | Quantity may be fractional; part must occur in price.basis.part_ids. **Negative:** `{"order_date":"2026-02-30"}` |
| `TextRecord` | `kind: L[text]; title: Label; text: str; document_kind: Label; declared_role?: Label` | document_kind/declared_role are open nonempty source labels. Unknown labels convey no authority. Empty text is valid; preserve formulas and malformed statements verbatim. **Negative:** `{"document_kind":""}` |

##### D2

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `NamedEstimate` | `name: L[full_cost,interest_rate,usual_rate,ppm,extra_per_unit]; value: Decimal; unit: L[EUR_per_price_unit,fraction,ppm]; range_low?: Decimal; range_high?: Decimal; basis?: PriceBasis` | Registered names are closed: full_cost/extra_per_unit use EUR_per_price_unit and require basis; full_cost >0; rates use fraction >=0; ppm uses ppm >=0. Both bounds or neither, low<=value<=high, same numeric domain. extra_per_unit is signed. **Negative:** `{"name":"invented_discount"}` |
| `EstimateRecord` | `kind: L[estimate]; method_id: L[fixture-point-v1,source-cost-v1,supplier-scenarios-v1]; values: T[NamedEstimate]; assumptions: T[SourceRef]` | Unique names, nonempty values. Registry v1 allows all NamedEstimate names for these methods; adding methods/names requires a contract revision. Explicit fixture method never implies calibrated uncertainty. Nonempty assumptions citing input facts or explicit documented assumption records. **Negative:** `{"values":[]}` |
| `EvidenceRecord` | `record_id: Id; canonical_id?: Id; kind: L[canonical,supplier_statement,estimate,hypothesis]; payload: EvidencePayload; scope: EvidenceScope; provenance: Provenance; temporal: TemporalValidity; disclosure: DisclosureRule; supersedes?: Id` | EstimateRecord payload requires estimate/hypothesis kind. Supplier statement cannot use estimate payload. No self supersession; canonical_id may be absent for statements; scorecards cannot carry part-level/basket scope. **Negative:** `{"payload.kind":"unregistered"}` |
| `FileDigest` | `path: RelativePath; sha256: Hash; byte_length: NonnegativeInt` | Relative POSIX path; reject absolute, empty, dot/dotdot segments, backslash/NUL. Symlink safety is checked by the data adapter, not inferred from a string. **Negative:** `{"path":"../escape"}` |
| `SourceManifest` | `source_id: Id; content_hash: Hash; files: T[FileDigest]; data_as_of?: Date; declared_version?: Label` | Unique file paths; empty files legal for explicit synthetic source; content_hash verified against consumed bytes by adapter. **Negative:** `{"content_hash":"bad"}` |
| `ScopeIndex` | `kind: L[supplier,part,canonical_id]; key: Id; record_ids: T[Id]` | Unique record IDs; resolve existence when assembled into PreparedEvidence. **Negative:** `{"record_ids":["same","same"]}` |
| `PreparedEvidence` | `artifact_id: ArtifactRef; base_manifest: SourceManifest; release_manifest?: SourceManifest; parser_versions: T[Label]; records: T[EvidenceRecord]; indexes: T[ScopeIndex]; prepared_at: UTC; integrity_hash: Hash` | Unique record IDs/parser names/index (kind,key). Index refs exist. integrity_hash = semantic_hash of JSON excluding prepared_at, integrity_hash, artifact_id; verified by codec, not guessed by DTO. artifact_id is sha256:<integrity_hash>. All preparation hash verification is codec-owned; DTO enforces formats and internal index references only. **Negative:** `{"prepared_at":"2026-10-10T10:00:00"}` |
| `Conflict` | `canonical_id: Id; candidate_record_ids: T[Id]; winning_record_id?: Id; rule_id: Id; blocking: bool; reason_code: Label` | At least two unique candidates; winner if supplied belongs to candidates; unresolved blocking conflicts have no winner. **Negative:** `{"winning_record_id":"absent"}` |
| `RelevanceRecord` | `record_id: Id; topic: Label; reason_code: Label; rank: NonnegativeInt; polarity: L[supports,contradicts,neutral,unknown]` | Rank is retrieval policy only; never authority. **Negative:** `{"rank":true}` |
| `EvidenceContext` | `context_version: Id; case_id: Id; supplier_ids: T[Id]; part_ids: T[Id]; as_of: UTC; prepared_artifact_id: ArtifactRef; records: T[EvidenceRecord]; conflicts: T[Conflict]; gaps: T[Issue]; relevance: T[RelevanceRecord]; source_versions: T[Label]` | Unique record identities; relevance refs exist; conflicts may also reference shadowed input records retained in preparation. Context builder derives version from meaningful evidence/case inputs; no DTO winner selection. **Negative:** `{"as_of":"yesterday"}` |
| `ResolvedCostInput` | `unit_cost: Price; source_refs: T[SourceRef]; scope: EvidenceScope; temporal: TemporalValidity; issues: T[Issue]` | Nonempty source_refs; same record revisions as internal claim projection. **Negative:** `{"source_refs":[]}` |
| `EvidencePayload` | `Annotated[IndexFact / ScorecardFact / CostFact / QuoteFact / ContractFact / ForecastFact / OrderPriceFact / TextRecord / EstimateRecord, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D3

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `PartIdentity` | `part_id: Id; price_basis: PriceBasis; unit_label?: Label` | part_id is included in explicitly declared price_basis.part_ids. **Negative:** `{"part_id":"part:other"}` |
| `TermOption` | `field: TermField; values: T[TermValue]; allow_verified_standard: bool` | Nonempty unique values; validate each by TermBinding(field,value). unit price need not have an option row; verified-standard permission conveys no certificate. **Negative:** `{"values":[true]}` |
| `MustHave` | `field: TermField; op: L[<=,<,>=,>,==,!=]; value: TermValue` | TermBinding validation. Ordered comparisons only numeric/date fields; incoterm/index_clause allow ==/!= only. **Negative:** `{"op":">="}` |
| `FreightRate` | `incoterm: L[EXW,FCA,DAP]; eur_per_unit: NonnegativeDecimal` | Finite EUR per declared physical unit; no implicit divisor. **Negative:** `{"eur_per_unit":"-1"}` |
| `IndexPath` | `series: Id; delta_fraction: Decimal` | Finite forecast change fraction >=-1; signed, not a probability. **Negative:** `{"delta_fraction":"-1.01"}` |
| `AvailableAlternative` | `kind: L[available]; ref?: SourceRef; terms: ResolvedTerms; basis: PriceBasis; provenance_refs: T[SourceRef]` | Nonempty provenance; complete terms contain unit_price. Operational alternative is distinct from fallback scoring. **Negative:** `{"provenance_refs":[]}` |
| `UnavailableAlternative` | `kind: L[unavailable]; reason_code: Label` | No numeric infinity or zero-cost synthetic alternative. **Negative:** `{"reason_code":""}` |
| `FieldOrigin` | `field: TermField; source_kind: L[sheet,fixed,quote,master,buyer_default]; source_refs: T[SourceRef]` | Nonempty source_refs for every field including case-derived buyer defaults. **Negative:** `{"source_refs":[]}` |
| `ResolvedTerms` | `bindings: T[TermBinding]; origins: T[FieldOrigin]; version_hash: Hash` | Unique bindings; exactly one origin for each field, same field set. origins is the frozen §8.1 spelling, not field_origins. Hash derived by resolver over sorted bindings/origins. **Negative:** `{"origins":[]}` |
| `ResolvedStandards` | `bindings: T[TermBinding]; field_origins: T[FieldOrigin]; version_hash: Hash` | Unique bindings; exactly one origin per field. This model retains field_origins from §2. Quote overrides master; resolution is service-owned. **Negative:** `{"field_origins":[]}` |
| `BuyerEconomics` | `category_goal: L[routine,leverage,quality_first,stabilise,secure_supply]; need_per_year: PositiveDecimal; horizon_years: PositiveDecimal; current_price?: Price; fallback_price: Price; interest_rate: NonnegativeDecimal; reference_payment_days: NonnegativeInt; need_lead_time_days: NonnegativeInt; fallback_risk_pct: NonnegativeDecimal; index_risk_pct: NonnegativeDecimal; late_cost_per_day: Money; cost_per_defect: Money; sustainable_margin_pct?: Percent; relationship_eur_per_point?: Money; freight: T[FreightRate]; index_paths: T[IndexPath]; must_haves: T[MustHave]; alternative: ExecutableAlternative` | Same price basis for current/fallback. Cost/risk penalties nonnegative, signed cost components remain legal elsewhere. Freight has exactly EXW/FCA/DAP once each; unique series. Horizon/need may be fractional; preserve official convention. **Negative:** `{"need_per_year":"0"}` |
| `CaseContract` | `case_id: Id; case_type: L[capacity,price_increase,bundling,quality,raw_material,renewal,rfq]; title: Label; supplier_ids: T[Id]; parts: T[PartIdentity]; negotiable_fields: T[TermField]; options: T[TermOption]; fixed_terms: T[TermBinding]; buyer: BuyerEconomics; round_limit: PositiveInt; case_facts: T[EvidenceRecord]; refs: T[Id]; contract_hash: Hash` | Nonempty unique suppliers/parts/negotiable fields; unique option/fixed fields; fixed and negotiable disjoint; options subset negotiable; basis parts declared by case. Schema preserves official case types; executable capability preflight remains restricted to approved slice. contract_hash verified by adapter over full JSON excluding contract_hash/title/refs, with field-sorted terms/options; raw official bytes separate. Schema checks only digest format; the official adapter recomputes the contract hash before construction. No DTO calls kit arithmetic. refs preserves official declared record/document IDs; resolved source revisions belong to evidence/projection SourceRefs. **Negative:** `{"supplier_ids":[]}` |
| `ExecutableAlternative` | `Annotated[AvailableAlternative / UnavailableAlternative, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D4

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `SupplierStandards` | `supplier_id: Id; standards: ResolvedStandards` | Tuple element for EconomicContext.standards_by_supplier; unique supplier keys in parent, no mutable map. **Negative:** `{"supplier_id":""}` |
| `SupplierEstimate` | `estimate_id: Id; supplier_id: Id; basis: PriceBasis; full_cost: Price; full_cost_low: Price; full_cost_high: Price; interest_rate: NonnegativeDecimal; usual_rate: NonnegativeDecimal; ppm?: NonnegativeInt; standard: ResolvedStandards; assumption_refs: T[SourceRef]; method_id: Id; uncertainty_kind: L[scenario_range,calibrated_interval,unknown]; extra_per_unit?: Decimal` | All prices same basis; low<=full_cost<=high; nonempty assumption_refs. Coincident bounds legal for explicit fixture point estimate with unknown uncertainty, never calibrated automatically. **Negative:** `{"full_cost_low.amount":"1000"}` |
| `EstimateScenario` | `scenario_id: Id; estimate_ids: T[Id]` | Nonempty unique estimate IDs; at most one per supplier after EconomicContext resolves IDs. No weights or invented probabilities. **Negative:** `{"estimate_ids":[]}` |
| `ScenarioPolicy` | `mode: L[disabled_explicit,nominal_explicit,robust_scenarios]; scenarios: T[EstimateScenario]; required_supplier_ids: T[Id]` | Disabled: both tuples empty. Nominal: exactly one scenario. Robust: >=1 scenarios. Non-disabled has nonempty unique required suppliers; every scenario covers each required supplier exactly once. Coverage belongs to EconomicContext validator. **Negative:** `{"scenarios":[{"$example":"EstimateScenario"}]}` |
| `PriceInterval` | `minimum: Price; maximum: Price` | Same basis; minimum<=maximum. **Negative:** `{"minimum.amount":"1000"}` |
| `CostPolicy` | `policy_id: Id; comparison: L[nominal,robust_scenarios]; ceiling?: Money; price_bounds: PriceInterval; tick: PositiveDecimal; fallback_rule: L[preserve_baseline_if_feasible]; alternative_rule: L[compare_executable_else_no_deal_score]` | Tick must be 0.01 in contract v1. Ceiling nonnegative if supplied. Price interval is case-bound, no invented default max. **Negative:** `{"tick":"0.001"}` |
| `EconomicContext` | `case: CaseContract; standards_by_supplier: T[SupplierStandards]; estimates: T[SupplierEstimate]; scenario_policy: ScenarioPolicy; cost_policy: CostPolicy; fingerprint: Hash; issues: T[Issue]` | Unique standards supplier keys (case members); unique estimate IDs and case supplier/basis joins. Scenario refs resolve; mandatory required suppliers covered in every scenario. Robust comparison iff robust mode. Disabled has no estimates. Hash checked by builder over economic inputs including source revisions; never greeting prose. **Negative:** `{"standards_by_supplier":[{"$example":"SupplierStandards"},{"$example":"SupplierStandards"}]}` |
| `CostComponent` | `kind: L[price,uncovered_need,fallback_risk,payment_terms,freight,late_delivery,quality,tooling,index_clause,index_risk,relationship]; amount: Money` | Official 11 component names only; signed finite payment/index components allowed. **Negative:** `{"kind":"invented_benefit"}` |
| `ScenarioCost` | `scenario_id: Id; estimate_id?: Id; cost: Money; supplier_value?: Price; margin_pct?: Decimal; components: T[CostComponent]` | Unique components. If components supplied, cent-rounded sum equals cost; finite signed margin, no inferred acceptance probability. **Negative:** `{"margin_pct":"NaN"}` |
| `PackageEvaluation` | `package_fingerprint: Hash; resolved_terms: ResolvedTerms; nominal_cost?: Money; components: T[CostComponent]; scenario_costs: T[ScenarioCost]; must_haves_ok: bool; numerically_valid: bool; basis_verified: bool; assumption_refs: T[SourceRef]; economic_fingerprint: Hash; issues: T[Issue]` | Valid numeric result requires nominal_cost and exactly 11 unique components with half-even cent sum parity. Invalid numeric result requires null cost, empty components/scenarios and nonfinite_cost error. basis_verified/must_haves do not imply approval. **Negative:** `{"numerically_valid":true}` |
| `OfficialCostResult` | `total: Money; components: T[CostComponent]` | Exactly 11 unique component kinds; finite cent-rounded sum parity. **Negative:** `{"components":[]}` |

##### D5

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `StrategyIntent` | `intent_id: Id; strategy_id: Id; supplier_id: Id; snapshot: SnapshotRef; kind: L[keep,exchange,evidence_challenge,clarify,request_close]; dimension?: TermField; direction: L[increase,decrease,enumerate,unchanged]; observation_refs: T[Id]; evidence_refs: T[SourceRef]; question_id?: Id; rationale: Summary; supersedes_refusal_id?: Id` | Clarify requires question_id; other kinds omit question_id. Exchange has dimension and non-unchanged direction with observation/evidence refs. Keep has unchanged direction. request_close has unchanged direction; evidence_challenge requires evidence_refs. rationale is internal text only. **Negative:** `{"direction":"increase"}` |
| `OfferAction` | `kind: L[offer]; packages: T[Package]; claim_ids: T[Id]; question_id?: Id` | 1..3 unique package fingerprints; <=3 unique claim IDs. Packages remain negotiated contents, not resolved fixed terms. **Negative:** `{"packages":[]}` |
| `QuestionAction` | `kind: L[question]; question_id: Id; claim_ids: T[Id] = ()` | At most 3 unique claim IDs; default claim_ids=(). No package/cost authority. **Negative:** `{"question_id":""}` |
| `CloseRequest` | `kind: L[request_close]; reason_code: Label` | Request only; not an Accept/WalkAway. **Negative:** `{"reason_code":""}` |
| `CandidateAction` | `candidate_id: Id; intent_id: Id; supplier_id: Id; snapshot: SnapshotRef; contents: CandidateContents; construction_refs: T[Id]; candidate_builder_id: Id` | Candidate ID is semantic hash of contract/snapshot/intent/target/contents, checked by generator/engine. No transport or model-authored action. **Negative:** `{"contents.kind":"execute"}` |
| `GenerationResult` | `intent_id: Id; candidates: T[CandidateAction]; rejections: T[Issue]; search_scope: L[finite,proven_monotonic,bounded_scan]; search_complete: bool` | Unique candidates for this intent. Empty candidates requires error infeasible/unsupported_capability issue. All candidate.intent_id match intent_id. **Negative:** `{"rejections":[]}` |
| `IntentBatch` | `snapshot: SnapshotRef; intents: T[StrategyIntent]; issues: T[Issue]` | Unique intent IDs; all intent snapshots match. **Negative:** `{"intents.0.snapshot.state_version":99}` |
| `EvaluatedCandidate` | `evaluation_id: Id; candidate: CandidateAction; disposition: L[approved,rejected]; economic: T[PackageEvaluation]; issues: T[Issue]` | Offer has one evaluation per package with matching fingerprints; non-offers have none. Approved offers all numerically_valid/basis_verified/must_haves_ok and no error issue. Rejected requires error issue. **Negative:** `{"disposition":"approved"}` |
| `EvaluationBatch` | `snapshot: SnapshotRef; items: T[EvaluatedCandidate]; issues: T[Issue]; batch_hash: Hash` | Unique candidate/evaluation IDs; every candidate snapshot matches; registered batch hash verified by evaluator/engine over sorted items. **Negative:** `{"items.0.candidate.snapshot.state_version":99}` |
| `NegotiationDecision` | `decision_id: UUID; snapshot: SnapshotRef; candidate_id: Id; evaluation_id: Id; approved_batch_hash: Hash; selector_id: Id; rationale: Summary; citations: T[Citation]; fallback_code?: Label` | Selection certificate refers to an approved registered batch member; DTO shape alone grants no execution capability. decision_id uses UUID per universal ID rule; existing schema-only DecisionRecord unchanged. **Negative:** `{"decision_id":"not-a-uuid"}` |
| `CandidateContents` | `Annotated[OfferAction / QuestionAction / CloseRequest, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D6

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `ObservedSheet` | `offer_id?: Id; bindings: T[TermBinding]; source_message_ref: MessageSpan; standing: bool; parse_issues: T[Issue]` | Unique parseable bindings, outside-option values preserved. Malformed fields absent from bindings and described in issues/raw artifact. Standing alone grants no acceptance eligibility. **Negative:** `{"bindings":[{"$example":"TermBinding"},{"$example":"TermBinding"}]}` |
| `DocumentRecord` | `attachment_id: Id; name: Label; media_type: Label; bytes_hash: Hash; text_ref?: ArtifactRef; structured_refs: T[SourceRef]; parse_status: L[ok,partial,unsupported,failed]; issues: T[Issue]` | Partial/unsupported/failed require issues. Raw bytes remain separate; formulas preserved as attributed source text. **Negative:** `{"parse_status":"failed"}` |
| `ClaimCheckResult` | `argument_index: NonnegativeInt; result: L[verified,contradicted,irrelevant,duplicate,unknown]; source_message_ref: MessageSpan` | Index is response-local, not proof of claim identity or persuasion. **Negative:** `{"argument_index":true}` |
| `ConversationMessage` | `session_id: Id; thread_id: Id; message_id: Id; speaker: L[buyer,supplier,arena]; supplier_id: Id; role?: Label; from_name?: Label; body: str; observed_sheets: T[ObservedSheet]; attachments: T[DocumentRecord]; claim_results: T[ClaimCheckResult]; server_at?: UTC; received_at: UTC; in_reply_to?: Id; content_hash: Hash` | Empty body legal. Referenced message spans use same session/thread/message. Hash checked against stored raw source by gateway. **Negative:** `{"received_at":"2026-10-10T10:00:00"}` |
| `ConversationView` | `session_id: Id; thread_id: Id; messages: T[ConversationMessage]; version_hash: Hash` | Unique scoped message IDs; every message belongs to session/thread. Full view v1, no truncation fields or silent truncation. **Negative:** `{"messages.0.session_id":"other"}` |
| `ClockEvidence` | `server_deadline_at?: UTC; seconds_left?: NonnegativeDecimal; snapshot_requested_at: UTC; snapshot_received_at: UTC; server_at?: UTC; kind: L[thread,wave]; source_ref: ArtifactRef; conservative_deadline_at?: UTC; confidence: L[authoritative,conservative,unknown]` | received>=requested; authoritative requires server_deadline_at or seconds_left; conservative requires conservative_deadline_at. Clock arithmetic belongs to budget service. **Negative:** `{"snapshot_received_at":"2026-10-09T10:00:00Z"}` |
| `RoundEvidence` | `limit: PositiveInt; server_rounds_used?: NonnegativeInt; accepted_buyer_messages: NonnegativeInt; timeout_rounds?: NonnegativeInt; conservative_remaining?: NonnegativeInt; source_ref: ArtifactRef; confidence: L[authoritative,conservative,unknown]` | Counts do not exceed limit; remaining<=limit; authoritative requires server_rounds_used. Submission attempts distinct. **Negative:** `{"accepted_buyer_messages":true}` |
| `TerminalEvidence` | `session_id: Id; status: L[ended]; proof_ref: ArtifactRef; source_kind: L[gateway_response,gateway_observation]; observed_at: UTC; deal?: bool; offer_id?: Id; supplier_id?: Id; score?: Decimal; cost?: Money; end_reason?: Label` | §8.7 supersedes earlier §2 shape. Deal true requires offer/supplier; proof existence/content/session checked by store/projector, never by supplier text. Missing score is null. **Negative:** `{"status":"open"}` |
| `ServerThread` | `thread_id: Id; supplier_id: Id; status: L[open,agreed,walked_away,no_bid]; standing_offer_id?: Id; conversation: ConversationView; rounds: RoundEvidence; clock: ClockEvidence; standards: ResolvedStandards; closed_reason?: Label` | Conversation thread ID matches. Agreed is not session terminal; adapter rejects unsupported server statuses rather than guessing. walked_away/no_bid are official thread closure values; never rewrite to session ended. **Negative:** `{"thread_id":"other"}` |
| `ServerState` | `session_id: Id; case_id: Id; status: L[open,ended,unknown]; threads: T[ServerThread]; wave_clock?: ClockEvidence; terminal?: TerminalEvidence; observed_at: UTC; observation_hash: Hash` | Unique thread/supplier IDs, conversation session matches. ended iff terminal present and matching session. Official state exclusively gateway observations. **Negative:** `{"status":"ended"}` |

##### D7

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `ClaimWindow` | `start: Date; end: Date` | Inclusive window, start<=end. **Negative:** `{"end":"2026-09-01"}` |
| `ClaimCandidate` | `claim_id: Id; kind: L[index,scorecard,cost,quote,contract,forecast,order_price]; source_refs: T[SourceRef]; scope: EvidenceScope; figure?: Decimal; unit: Label; basis?: PriceBasis; window?: ClaimWindow; canonical_sentence: Summary; disclosure: DisclosureRule` | Nonempty source refs. Proposed canonical_sentence remains untrusted and recomputed by verifier. No verification certificate. **Negative:** `{"source_refs":[]}` |
| `VerifiedClaim` | `claim_id: Id; kind: L[index,scorecard,cost,quote,contract,forecast,order_price]; source_refs: T[SourceRef]; scope: EvidenceScope; figure?: Decimal; unit: Label; basis?: PriceBasis; window?: ClaimWindow; canonical_sentence: Summary; disclosure: DisclosureRule; verification_version: Id; context_version: Id` | Nonempty source refs. Only verifier issues; disclosure/recipient and numeric provenance independently checked at final validation. **Negative:** `{"verification_version":""}` |
| `VerifiedClaimResult` | `kind: L[verified]; claim: VerifiedClaim` | No transport authority. **Negative:** `{"kind":"approved"}` |
| `RejectedClaimResult` | `kind: L[rejected]; issues: T[Issue]` | Nonempty error issues. **Negative:** `{"issues":[]}` |
| `Accept` | `kind: L[accept]; supplier_id: Id; offer_id: Id; evaluation_id: Id` | Current standing offer and complete legal/economic evaluation checked by closing service. **Negative:** `{"offer_id":""}` |
| `WalkAway` | `kind: L[walk_away]; supplier_id: Id; reason_code: Label` | Supplier recipient explicit; no cost fabricated for unknown economics. **Negative:** `{"supplier_id":""}` |
| `AlternativeComparison` | `kind: L[executable,no_deal_score]; cost: Money; alternative_ref?: SourceRef; issues: T[Issue]` | Executable kind requires alternative_ref; no_deal_score requires null ref. Operational fallback distinct from scoring cost. **Negative:** `{"kind":"executable"}` |
| `CloseDecision` | `close_id: UUID; snapshot: SnapshotRef; action: ClosingAction; evaluated_offer_refs: T[ArtifactRef]; alternative_comparison: AlternativeComparison; reason_code: Label; policy_id: Id` | Accept requires evaluated_offer_refs; walk may have none. Issuer is closing service; model cannot invent binding recommendation. **Negative:** `{"action.kind":"offer"}` |
| `ClosingAction` | `Annotated[Accept / WalkAway, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |
| `ClaimVerificationResult` | `Annotated[VerifiedClaimResult / RejectedClaimResult, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D8

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `AcceptPayload` | `type: L[accept]; term_sheet_id: Id` | Wire accept uses offer ID as term_sheet_id; no duplicate supplier field in message action. **Negative:** `{"term_sheet_id":""}` |
| `WalkPayload` | `type: L[walk_away]` | No extra numeric fields or invented terms. **Negative:** `{"type":"walk"}` |
| `OutboundAttachment` | `name: Label; media_type: Label; content_ref: ArtifactRef; hash: Hash; disclosure: DisclosureRule` | content_ref digest equals hash; bytes verified by adapter; classified approved attachments only. **Negative:** `{"hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}` |
| `MessagePayload` | `subject: str; body: str; packages: T[Package]; refs: T[Id]; action?: WireAction; attachments: T[OutboundAttachment]` | subject<=300/body<=8000 Unicode chars, packages<=3/refs<=20/attachments<=5; packages and action mutually exclusive; no action with packages. Empty packages/action legal question. Adapter maps Package.bindings to Arena term_sheets and preserves exact bytes. **Negative:** `{"subject":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx… (full mutation in JSON test contract)` |
| `RenderedAction` | `decision_ref?: ArtifactRef; close_ref?: ArtifactRef; snapshot: SnapshotRef; supplier_id: Id; kind: L[offer,question,accept,walk_away]; payload: MessagePayload; claim_ids: T[Id]; template_version: Id; render_hash: Hash` | Exactly one decision_ref/close_ref; close ref iff accept/walk. Offer nonempty packages/no action; question empty packages/no action; accept/walk matching action type/no packages. <=3 unique claims. Hash verified by validator over full rendered JSON excluding render_hash. **Negative:** `{"close_ref":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}` |
| `CheckOutcome` | `check_id: Id; passed: bool; refs: T[ArtifactRef]; detail_code: Label` | Diagnostic only; no repair. **Negative:** `{"passed":1}` |
| `ValidationReport` | `check_version: Id; snapshot: SnapshotRef; checks: T[CheckOutcome]; issues: T[Issue]` | Unique check IDs; failure checks require error issues. **Negative:** `{"checks":[{"$example":"CheckOutcome"},{"$example":"CheckOutcome"}]}` |
| `WireAction` | `Annotated[AcceptPayload / WalkPayload, discriminator="type"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"type":"unregistered"}` |

##### D9

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `ValidatedAction` | `rendered: RenderedAction; report: ValidationReport; payload_bytes_ref: ArtifactRef; payload_hash: Hash; economic_fingerprint: Hash; expires_at: UTC; validator_version: Id` | Matching snapshots; nonempty all-passed checks and no error issues; bytes ref digest matches payload_hash. Issued by validator; DTO does not grant execution. **Negative:** `{"report.snapshot.state_version":99}` |
| `ValidActionResult` | `kind: L[valid]; action: ValidatedAction` | Validator-issued result only. **Negative:** `{"kind":"success"}` |
| `InvalidActionResult` | `kind: L[invalid]; report: ValidationReport` | At least one error issue. **Negative:** `{"report.issues":[]}` |
| `DecisionBudget` | `deadline_at: UTC; compute_limit_s: PositiveDecimal; model_call_limit: NonnegativeInt; model_time_limit_s: PositiveDecimal; candidate_limit: PositiveInt; fallback_reserve_s: NonnegativeDecimal; submission_reserve_s: NonnegativeDecimal; clock_refs: T[ArtifactRef]` | model_call_limit<=2; fallback+submission<=compute limit. No ambient clock calls in DTO. **Negative:** `{"model_call_limit":3}` |
| `TransportBudget` | `deadline_at: UTC; request_attempt_limit: PositiveInt; reconciliation_attempt_limit: PositiveInt; submission_reserve_s: NonnegativeDecimal; terminal_read_reserve_s: NonnegativeDecimal; lease_ref: ArtifactRef; clock_refs: T[ArtifactRef]` | Absolute deadline; attempts separate from server rounds. **Negative:** `{"request_attempt_limit":true}` |
| `PendingOperation` | `operation_id: UUID; kind: L[open,send,close]; case_id: Id; session_id?: Id; supplier_id?: Id; endpoint_kind: L[open_case,send_message,close_session]; payload_bytes_ref: ArtifactRef; payload_hash: Hash; validation_ref?: ArtifactRef; source_state_version: NonnegativeInt; commit_state_version: NonnegativeInt; created_at: UTC; submitted_at?: UTC; status: L[prepared,submitted,acknowledged,rejected,uncertain]; response_ref?: ArtifactRef; attempt_count: NonnegativeInt` | commit=source+1; digest matches bytes ref; endpoint matches kind. Open has no session/supplier/validation; send/close require all three. submitted_at>=created_at; submitted/acknowledged require submitted_at/attempt_count>=1; acknowledged/rejected require response_ref. Unknown open retains original ID/bytes. Null source/commit sessions are only the open case; status uncertain may have no submission timestamp when transport outcome is unknown. **Negative:** `{"session_id":"invented"}` |
| `DispatchPermit` | `operation_id: UUID; commit_state_version: PositiveInt; payload_hash: Hash; expires_at: UTC; lease_ref: ArtifactRef; fresh_observation_hash: Hash` | Ownership/lease and current hash freshness verified by executor after queue; shape not capability provenance. **Negative:** `{"commit_state_version":0}` |
| `ValidationResult` | `Annotated[ValidActionResult / InvalidActionResult, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D10

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `StrategyAttempt` | `attempt_id: UUID; intent_id: Id; candidate_id: Id; package_fingerprint?: Hash; operation_id: UUID; status: L[prepared,submitted,acknowledged,rejected,uncertain]; response_refs: T[ArtifactRef]` | acknowledged/rejected require response refs; proposed intent alone is no attempt. **Negative:** `{"status":"acknowledged"}` |
| `RefusedExchange` | `refusal_id: Id; supplier_id: Id; dimension?: TermField; package_fingerprint?: Hash; attempt_refs: T[UUID]; citations: T[Citation]; scope: L[package,dimension,conditional,unknown]; assessment_id: Id` | Nonempty citations; package scope requires fingerprint, dimension scope requires dimension. Refusal remains inferred/reported evidence, never legal prohibition. **Negative:** `{"citations":[]}` |
| `ClaimUsage` | `claim_id: Id; canonical_ids: T[Id]; scope_key: Id; operation_id: UUID; status: L[reserved,sent,unknown,released]; recipient_id: Id` | Unique canonical IDs; reservations managed atomically by store; same operation never consumes twice. **Negative:** `{"status":"used"}` |
| `OutstandingQuestion` | `question_id: Id; operation_id: UUID; status: L[submitted,answered,ambiguous]; response_refs: T[ArtifactRef]` | answered/ambiguous require response refs. **Negative:** `{"status":"answered"}` |
| `StrategyMemory` | `strategy_id: Id; record_ref: ArtifactRef; parent_ref?: ArtifactRef; payload_hash: Hash` | record_ref digest equals payload_hash; separately registered payload schema validated by owning strategy/store. No arbitrary payload field. **Negative:** `{"payload_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}` |
| `PackageChange` | `field: TermField; before?: TermBinding; after?: TermBinding; source_refs: T[Citation]` | At least one before/after; binding fields equal field; if both present values differ. Null slot means missing field, while TermBinding(null) is explicit null. **Negative:** `{"before":null}` |
| `ClaimAttribution` | `claim_id?: Id; argument_index?: NonnegativeInt; result: L[verified,contradicted,irrelevant,duplicate,unknown]; citations: T[Citation]` | Nonempty citations; nullable claim ID when response index cannot be confidently mapped. **Negative:** `{"citations":[]}` |
| `HypothesisSupport` | `hypothesis_id: Id; relation: L[supports,contradicts,unknown]; citations: T[Citation]` | Nonempty citations; source attribution, no causal learning. **Negative:** `{"citations":[]}` |
| `QuestionUpdate` | `question_id: Id; status: L[answered,ambiguous]; citations: T[Citation]` | Nonempty citations; uncertainty retained. **Negative:** `{"citations":[]}` |
| `FeedbackObservation` | `operation_id: UUID; decision_id: UUID; response_refs: T[ArtifactRef]; package_changes: T[PackageChange]; claim_attributions: T[ClaimAttribution]; hypothesis_support: T[HypothesisSupport]; question_updates: T[QuestionUpdate]; issues: T[Issue]; causality_status: L[observed_sequence]` | Nonempty response_refs; unique changed fields/question IDs. Observed sequence never means causal gain. **Negative:** `{"causality_status":"causal"}` |
| `StrategicState` | `assessments: T[SupplierAssessment]; attempts: T[StrategyAttempt]; refusals: T[RefusedExchange]; claim_usage: T[ClaimUsage]; outstanding_questions: T[OutstandingQuestion]; feedback: T[FeedbackObservation]; memory: T[StrategyMemory]` | Append immutable histories. Assessment ID unique; attempt IDs unique; preserve earlier revisions independently of policy activation. **Negative:** `{"attempts":[{"$example":"StrategyAttempt"},{"$example":"StrategyAttempt"}]}` |
| `NegotiationState` | `run_id: Id; attempt_id: UUID; case: CaseContract; server?: ServerState; strategic: StrategicState; operations: T[PendingOperation]; version: NonnegativeInt; config_hash: Hash; runtime_status: L[ready,deciding,awaiting,recovery_required,ended]; issues: T[Issue]` | Server null only before identified session; case/session operations match. At most one unresolved prepared/submitted/uncertain operation. ended requires ended server; awaiting requires unresolved operation; null server only ready/awaiting/recovery_required. Ended server requires ended runtime; strategic histories never override server status. No synthetic known-session IDs. **Negative:** `{"runtime_status":"ended"}` |

##### D11

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `NegotiationContext` | `snapshot: SnapshotRef; case: CaseContract; evidence: EvidenceContext; economic: EconomicContext; capabilities: T[Id]; as_of: UTC` | case IDs and contract hashes agree across snapshot/case/economic; evidence context version equals snapshot; target scopes consistent. Full private input never serialized verbatim into model request. **Negative:** `{"snapshot.case_contract_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}` |
| `DecisionSnapshot` | `context: NegotiationContext; state: NegotiationState; target_supplier_id: Id; conversation: ConversationView; budget: DecisionBudget` | Known open/agreed session; state/context config/version/case/session agree; target is case member and conversation thread/supplier match. **Negative:** `{"state.server":null}` |
| `SelectedOutcome` | `kind: L[selected]; decision: NegotiationDecision` | Selection only; no implicit dispatch. **Negative:** `{"kind":"sent"}` |
| `RequestCloseOutcome` | `kind: L[request_close]; reason_code: Label; snapshot: SnapshotRef` | No binding commercial action. **Negative:** `{"reason_code":""}` |
| `HoldOutcome` | `kind: L[hold]; reason_code: Label; recheck_at: UTC; snapshot: SnapshotRef` | Future admissibility/time budget checked by engine; no busy loop in DTO. **Negative:** `{"recheck_at":"tomorrow"}` |
| `CannotDecideOutcome` | `kind: L[cannot_decide]; issues: T[Issue]; snapshot: SnapshotRef` | Nonempty error issues; never a commercial terminal. **Negative:** `{"issues":[]}` |
| `DecisionOutcome` | `Annotated[SelectedOutcome / RequestCloseOutcome / HoldOutcome / CannotDecideOutcome, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D12

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `DocumentBytes` | `session_id: Id; attachment_id: Id; bytes_ref: ArtifactRef; bytes_hash: Hash; media_type: Label; received_at: UTC` | bytes_ref digest equals bytes_hash. Bytes stored in artifact port, not a live client. **Negative:** `{"bytes_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}` |
| `ServerObservation` | `server: ServerState; documents: T[DocumentRecord]; raw_response_refs: T[ArtifactRef]; raw_response_hashes: T[Hash]; source_key: Id; clock_evidence: T[ClockEvidence]` | Nonempty equally sized raw refs/hashes with matching digests; parsed observations remain gateway-owned; document descriptors do not authorize execution. **Negative:** `{"raw_response_hashes":[]}` |
| `GatewayResponse` | `kind: L[response]; operation_id: UUID; response_ref: ArtifactRef; observation: ServerObservation; terminal?: TerminalEvidence` | If terminal supplied equals observation.server.terminal. **Negative:** `{"terminal.session_id":"other"}` |
| `GatewayRejection` | `kind: L[rejected]; operation_id: UUID; status: PositiveInt; proof_ref: ArtifactRef; definitely_not_applied: bool; issues: T[Issue]` | HTTP status 400..599; nonempty error issues; must definitely_not_applied=true; unclear application uses GatewayUnknown. **Negative:** `{"definitely_not_applied":false}` |
| `GatewayUnknown` | `kind: L[unknown]; operation_id: UUID; cause_code: IssueCode; issues: T[Issue]` | No invented server observation or terminal proof. **Negative:** `{"cause_code":"network_magic"}` |
| `InterpretInput` | `kind: L[interpret]; snapshot: SnapshotRef; supplier_id: Id; conversation: ConversationView; evidence: T[EvidenceRecord]; previous?: SupplierAssessment` | Purpose-specific grounded input; only approved disclosed/relevant projection, no buyer private budget/economic context. **Negative:** `{"kind":"negotiate"}` |
| `SelectionOption` | `candidate_id: Id; evaluation_id: Id; summary: Summary; citations: T[Citation]` | Fixed approved batch projection; no model numeric edits. **Negative:** `{"candidate_id":""}` |
| `SelectInput` | `kind: L[select]; snapshot: SnapshotRef; approved_batch_hash: Hash; options: T[SelectionOption]; assessment: SupplierAssessment` | Nonempty unique candidate/evaluation IDs. Model chooses one ID; no added candidates. **Negative:** `{"options":[]}` |
| `SimulateInput` | `kind: L[simulate]; snapshot: SnapshotRef; candidate_id: Id; package: Package; citations: T[Citation]; question: Summary` | Private hypothetical projection; cannot generate authoritative evidence/server events. **Negative:** `{"kind":"supplier_truth"}` |
| `GatewayResult` | `Annotated[GatewayResponse / GatewayRejection / GatewayUnknown, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |
| `ModelInput` | `Annotated[InterpretInput / SelectInput / SimulateInput, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D13

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `ModelRequest` | `call_id: UUID; task: L[interpret,select,simulate]; task_schema_version: Id; prompt_version: Id; input: ModelInput; provider_id: Id; model_id: Id; protocol_id: Id; effort?: Label; output_schema_hash: Hash; correlation_id: UUID` | task equals input.kind. No headers, endpoint credentials or provider secret. **Negative:** `{"task":"select"}` |
| `ModelBudget` | `deadline_at: UTC; time_limit_s: PositiveDecimal; max_tokens: PositiveInt; max_calls: PositiveInt; retry_limit: ZeroInt` | max_calls<=2; retry_limit integer zero, boolean false rejected. **Negative:** `{"retry_limit":false}` |
| `ModelUsage` | `input_tokens?: NonnegativeInt; output_tokens?: NonnegativeInt; reported_cost?: Money` | Cost nonnegative if present; absent usage is null, not inferred free. Tokens are strict integers, boolean values rejected. **Negative:** `{"input_tokens":true}` |
| `ModelSuccess` | `kind: L[success]; call_id: UUID; model_id: Id; elapsed_s: NonnegativeDecimal; issues: T[Issue]; raw_response_json: str; response_hash: Hash; usage: ModelUsage` | Raw string may be malformed JSON. response_hash is SHA256 of exact UTF8 raw string (not semantic hash of parsed object). No automatic schema validation here. **Negative:** `{"response_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}` |
| `ModelRefused` | `kind: L[refused]; call_id: UUID; model_id: Id; elapsed_s: NonnegativeDecimal; issues: T[Issue]` | Nonempty error issues; no successful raw output or invented usage. Require at least one error issue with code model_invalid; retain other source diagnostics. **Negative:** `{"issues":[]}` |
| `ModelInvalid` | `kind: L[invalid]; call_id: UUID; model_id: Id; elapsed_s: NonnegativeDecimal; issues: T[Issue]` | Nonempty error issues; no successful raw output or invented usage. Require at least one error issue with code model_invalid; retain other source diagnostics. **Negative:** `{"issues":[]}` |
| `ModelTimeout` | `kind: L[timeout]; call_id: UUID; model_id: Id; elapsed_s: NonnegativeDecimal; issues: T[Issue]` | Nonempty error issues; no successful raw output or invented usage. Require at least one error issue with code model_timeout; retain other source diagnostics. **Negative:** `{"issues":[]}` |
| `ModelCapacityUnavailable` | `kind: L[capacity_unavailable]; call_id: UUID; model_id: Id; elapsed_s: NonnegativeDecimal; issues: T[Issue]` | Nonempty error issues; no successful raw output or invented usage. Require at least one error issue with code unsupported_capability; retain other source diagnostics. **Negative:** `{"issues":[]}` |
| `ModelTransportFailure` | `kind: L[transport_failure]; call_id: UUID; model_id: Id; elapsed_s: NonnegativeDecimal; issues: T[Issue]` | Nonempty error issues; no successful raw output or invented usage. Require at least one error issue with code recovery_required; retain other source diagnostics. **Negative:** `{"issues":[]}` |
| `SelectorResponse` | `selected_id: Id; supporting_quote: str` | Exactly these two commercial fields plus schema_version; membership/quote entailment validated by selector, not provider. **Negative:** `{"selected_id":""}` |
| `ModelResult` | `Annotated[ModelSuccess / ModelRefused / ModelInvalid / ModelTimeout / ModelCapacityUnavailable / ModelTransportFailure, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D14

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `SessionObserved` | `kind: L[SessionObserved]; artifact_ref: ArtifactRef; server: ServerState` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `MessageObserved` | `kind: L[MessageObserved]; artifact_ref: ArtifactRef; message: ConversationMessage; thread_state: ServerThread; rounds: RoundEvidence` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. Message/thread/round identities agree; rounds equals thread_state.rounds. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `DocumentObserved` | `kind: L[DocumentObserved]; artifact_ref: ArtifactRef; document: DocumentRecord` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `AssessmentRecorded` | `kind: L[AssessmentRecorded]; artifact_ref: ArtifactRef; assessment: SupplierAssessment` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `DecisionRecorded` | `kind: L[DecisionRecorded]; artifact_ref: ArtifactRef; record_ref: ArtifactRef` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `OperationPrepared` | `kind: L[OperationPrepared]; artifact_ref: ArtifactRef; operation: PendingOperation; claim_usage: T[ClaimUsage]` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `OperationSubmitted` | `kind: L[OperationSubmitted]; artifact_ref: ArtifactRef; operation_id: UUID; submitted_at: UTC` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `OperationAcknowledged` | `kind: L[OperationAcknowledged]; artifact_ref: ArtifactRef; operation_id: UUID; response_ref: ArtifactRef; server: ServerState` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |

##### D15

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `OperationRejected` | `kind: L[OperationRejected]; artifact_ref: ArtifactRef; operation_id: UUID; proof_ref: ArtifactRef; definitely_not_applied: bool; issues: T[Issue]` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. Nonempty error issues; definitely_not_applied is strict bool and may be false, retaining ownership. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `OperationUncertain` | `kind: L[OperationUncertain]; artifact_ref: ArtifactRef; operation_id: UUID; cause_code: IssueCode` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `ClaimReserved` | `kind: L[ClaimReserved]; artifact_ref: ArtifactRef; usage: ClaimUsage` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `ClaimReleased` | `kind: L[ClaimReleased]; artifact_ref: ArtifactRef; claim_id: Id; scope_key: Id; operation_id: UUID; no_transmission_proof_ref: ArtifactRef` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. Release proof required; never infer no-transmission from local exception. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `FeedbackObserved` | `kind: L[FeedbackObserved]; artifact_ref: ArtifactRef; feedback: FeedbackObservation` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `TerminalConfirmed` | `kind: L[TerminalConfirmed]; artifact_ref: ArtifactRef; terminal: TerminalEvidence` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. terminal.status is ended; proof is checked by projector, so unproven negative event can still be represented. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `RecoveryRequired` | `kind: L[RecoveryRequired]; artifact_ref: ArtifactRef; operation_id?: UUID; issues: T[Issue]` | Artifact ref resolves to canonical typed payload content; store verifies bytes/value match. Transition, proof authority and dedupe are projector/store responsibilities under §8.7, never this DTO. Nonempty error issues. **Negative:** `{"artifact_ref":"local-attempt-is-proof"}` |
| `NegotiationEvent` | `event_id: UUID; run_id: Id; session_id?: Id; local_seq: PositiveInt; occurred_at?: UTC; recorded_at: UTC; source_key?: Id; correlation_id: UUID; parent_event_ids: T[UUID]; payload: EventPayload` | No self parent; unique parents. Local sequence assigned by store; contiguous ordering/ownership/source-key conflicts checked on append. **Negative:** `{"parent_event_ids":["00000000-0000-4000-8000-000000000001"]}` |
| `EventProposal` | `run_id: Id; session_id?: Id; occurred_at?: UTC; recorded_at: UTC; source_key?: Id; correlation_id: UUID; parent_event_ids: T[UUID]; payload: EventPayload` | No event_id/local_seq assigned by components. All hydrated payloads use same tagged EventPayload as stored events. **Negative:** `{"recorded_at":"2026-10-10"}` |
| `DecisionCommit` | `run_id: Id; case_id: Id; expected_config_hash: Hash; expected_context_version: Id; decision_ref: ArtifactRef; artifact_refs: T[ArtifactRef]; event_proposals: T[EventProposal]; validated_action?: ValidatedAction; claim_reservations: T[ClaimUsage]; operation_id?: UUID; proposed_operation?: PendingOperation` | Operation ID/proposed operation both absent or both match. send/close require validated action; open has none. Record-only commit has neither validated action nor reservations. Proposed operation snapshots/config/context, exact byte hashes agree; one OperationPrepared proposal exactly matches operation/reservations. Store verifies existing artifact bytes before atomic CAS. **Negative:** `{"operation_id":"00000000-0000-4000-8000-000000000001"}` |
| `CommittedResult` | `kind: L[committed]; new_state: NegotiationState; operation?: PendingOperation; permit?: DispatchPermit` | Operation and permit either both absent or matching ID/hash/commit state version. **Negative:** `{"operation":{"$example":"PendingOperation"}}` |
| `ConflictResult` | `kind: L[conflict]; current_version: NonnegativeInt; issues: T[Issue]` | Nonempty store_conflict error issues. **Negative:** `{"issues":[]}` |
| `EventPayload` | `Annotated[SessionObserved / MessageObserved / DocumentObserved / AssessmentRecorded / DecisionRecorded / OperationPrepared / OperationSubmitted / OperationAcknowledged / OperationRejected / OperationUncertain / ClaimReserved / ClaimReleased / FeedbackObserved / TerminalConfirmed / RecoveryRequired, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |
| `CommitResult` | `Annotated[CommittedResult / ConflictResult, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |

##### D16

| Export | Exact fields / alias | Invariants / invalid example |
|---|---|---|
| `AcknowledgedExecution` | `kind: L[acknowledged]; operation_id: UUID; response_ref: ArtifactRef; terminal?: TerminalEvidence; observation_events: T[EventProposal]` | Terminal not inferred from ack; if supplied it matches an authoritative terminal observation event. **Negative:** `{"operation_id":"not-uuid"}` |
| `RejectedExecution` | `kind: L[rejected]; operation_id: UUID; status: PositiveInt; proof_ref: ArtifactRef; issues: T[Issue]` | status 400..599; nonempty error issues; proof authoritative definitely-not-applied. **Negative:** `{"issues":[]}` |
| `UncertainExecution` | `kind: L[uncertain]; operation_id: UUID; cause_code: IssueCode; recovery_required: L[True]` | Preserve ownership, never create replacement ID or terminal outcome. **Negative:** `{"recovery_required":false}` |
| `ReplayResult` | `outcome: DecisionOutcome; record: DecisionRecord; selected?: EvaluatedCandidate; validated?: ValidatedAction; execution?: ExecutionResult; state: NegotiationState; terminal?: TerminalEvidence; close_decision?: CloseDecision` | Fake ack is no Arena deal. terminal if present equals state.server.terminal; execution requires validated except record-only/recovery results; record/config/session links checked by offline assembler. **Negative:** `{"terminal":{"$example":"TerminalEvidence"}}` |
| `ExecutionResult` | `Annotated[AcknowledgedExecution / RejectedExecution / UncertainExecution, discriminator="kind"]` | Closed tagged union; unknown tag/extra fields rejected. No fallback generic payload. **Negative:** `{"kind":"unregistered"}` |


#### Canonical projection and reference rules for later service owners

Use existing canonical_json/semantic_hash and normalized typed Decimal JSON. A projection
includes schema_version; explicitly sort named bindings/options/origins by field and keyed
collections by their declared unique key. Preserve sequence order for messages/histories.
Exact artifact/source bytes use SHA256(bytes), not semantic hashing of reparsed JSON.
The DTO schema checks reference syntax; the listed service verifies content/identity before use.

| Identity | Exact projection / verifier |
|---|---|
| EvidenceRecord.record_id | `sha256:` + semantic_hash(record excluding record_id); provenance locator/version and temporal meaning retained; adapter owns derivation; canonical_id denotes family, not revision |
| SourceManifest.content_hash | semantic_hash({schema_version,source_id,files sorted by path,data_as_of,declared_version}); data adapter checks every FileDigest against consumed bytes |
| PreparedEvidence.integrity_hash / artifact_id | semantic_hash(full JSON excluding integrity_hash,artifact_id,prepared_at); codec verifies manifests/parser versions/index integrity; artifact_id is sha256:<integrity_hash> |
| EvidenceContext.context_version | sha256:<semantic_hash(full JSON excluding context_version)>; as_of is meaningful freshness time, not incidental receipt time; context builder resolves supporting/adverse revisions |
| CaseContract.contract_hash | semantic_hash(full JSON excluding contract_hash,title,refs); sort fields/options/parts/suppliers; raw official metadata preserved separately; adapter verifies capability before runtime |
| ResolvedTerms.version_hash / ResolvedStandards.version_hash | semantic_hash(full JSON excluding version_hash), field-sorted bindings and origins/field_origins; resolution service verifies source revisions |
| EconomicContext.fingerprint | semantic_hash({schema_version,case economic projection,standards_by_supplier,estimates,scenario_policy,cost_policy}); case projection is case_id/case_type/supplier_ids/parts/negotiable_fields/options/fixed_terms/buyer/round_limit; exclude title, raw case_facts prose, incidental receipt timestamps, issues and fingerprint; source-cost assumption revisions remain in estimates/origins |
| CandidateAction.candidate_id | sha256:<semantic_hash({schema_version,snapshot,intent_id,supplier_id,contents})>; generator/engine owns verification, matching Package remains independent across turns |
| EvaluatedCandidate.evaluation_id | sha256:<semantic_hash(full evaluated candidate excluding evaluation_id)>; evaluator owns certification |
| EvaluationBatch.batch_hash | semantic_hash({schema_version,snapshot,items sorted by candidate_id,issues}); selector/engine verifies exact approved membership; no unregistered hypothetical additions |
| ConversationMessage.content_hash / ServerState.observation_hash | SHA256 exact authoritative raw source message/response bytes retained as artifact; gateway verifies parser/raw association; conversation version hashes semantic scoped ordered message contents |
| ModelSuccess.response_hash | SHA256(raw_response_json.encode('utf-8')); malformed text is retained, interpreter owns subsequent schema validation |
| render_hash / payload_hash | render_hash hashes full RenderedAction JSON excluding render_hash; payload_hash is exact outbound Arena message bytes after adapter conversion, not internal frame; validator/store/executor verify immutable bytes and certificates |

Clock/reference ownership, state/CAS/terminal proof verification and deterministic economics
remain component gates, not DTO algorithms. Model inputs are purpose projections with no
credentials, raw private BuyerEconomics or mutable live service. Future ModelConfig/ConfigOrigin
expanded configuration sketches are outside T1.1d: EffectiveConfig continues using §8.5's
implemented fixture field inventory and explicit optional provider/protocol/prompt identifiers.
Official raw alternative.kind=none maps to UnavailableAlternative(reason_code=no_executable_alternative);
no alternative price is inferred from fallback_price. Existing source/class tags cannot silently
switch canonical/statement/estimate/hypothesis; evidence service validates origin authority.
