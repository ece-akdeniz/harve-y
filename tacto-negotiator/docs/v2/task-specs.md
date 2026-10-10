# V2 implementation task specifications

This expands [D](D-roadmap.md), not the scope. Contracts are [C §8](C-interfaces.md); test names/files are in the [catalog](test-catalog.md). All tasks are **planned**. Current tests/fixtures and documentation are preparation, not production implementation. All paths below are relative to tacto-negotiator. Use the existing locked Python/Pydantic environment. No dependency changes, V1 behavior edits, hosted calls, default promotion or branch merge are included.

## Common task contract

Inputs/outputs are `negotiator-v2/1`; fixtures are `negotiator-v2-fixtures/1`. Preserve existing assertions. Each assignment has one owner, exact files, preceding contract dependencies, positive/negative tests and exclusions. The allowed imports are executable in test_boundaries.py: core→stdlib/Pydantic/core; feature→core/own package; adapters→core/adapters/existing libraries; factory→selected components. Cross-feature services are injected through ports. No dynamic imports, provider chosen imports, production imports from tests, or hidden data/config discovery.

For every task record its source revision, targeted passing tests, remaining expected failures, legacy result classification, known limitations and changed files in D/main tracker. Completion means the owning tests pass with its module prefix required; no expected failure can count as completion. Other missing modules may remain expected failures, and existing incomplete modules may fail until their later subtask is implemented. Report that explicitly. Do not return a misleading globally green status. The exact reproduction commands are in implementation-guide.md.

## M1 small assignments, in order

### T1.1a — Immutable values, terms and canonical bytes

**Files:** create src/negotiator/v2/__init__.py (empty), core/__init__.py, core/models.py, core/errors.py, core/serialization.py. **Dependencies:** none after contract handoff. **Imports:** stdlib/Pydantic only. **Schemas:** FrozenModel, PriceBasis, Price, Money, IndexClause, TermBinding, Package, SourceRef, MessageSpan, SnapshotRef, Issue, IssueCode. Follow C §1–2/8.1. Snapshot version is nonnegative; basis has nonempty parts/positive unit; prices reject nonfinite/zero/bool; unique package bindings; dates/months validate strictly. Monetary storage is decimal strings. Implement canonical_json(value)->bytes and semantic_hash(value)->hex, with sorted UTF-8 JSON and forbidden NaN. Do not silently quantize a Price to make a later validator pass.

**Reuse:** Pydantic already installed; stdlib Decimal/hashlib/json. No import of PackageAgent or arena_kit. **Tests:** foundation price/basis/term/roundtrip/canonical tests with core.models/core.serialization required; guardrail expected-failure self-tests; boundary scanner tests. **Accept:** both valid unit 1/100/1000 roundtrips and every bad boundary value behave exactly as asserted. **Exclude:** economics, assessment, transport, service classes and future capability registries. This creates a usable strict value layer, not all core models.

### T1.1b — Assessment schemas and exact ports

**Files:** extend core/models.py; create core/ports.py. **Dependencies:** T1.1a. **Imports:** core/stdlib/Pydantic. **Schemas:** GroundedObservation, ReportedConstraint, PreferenceHypothesis, AssessmentUncertainty, ClarificationQuestion, EstimatedEffect, SupplierAssessment, AssessmentDraft. Use C §8.2 fields; nonempty citations for observed/reported/active inferred assertions; distinguish constraints and approval unknowns; numeric willingness absent by default. Add all existing C protocol signatures and C §8.4 oracle/clock protocols with typed forward annotations where a later schema is not yet implemented. Do not create placeholder production classes that claim to implement a port.

**Reuse:** only source/citation patterns from existing adviser; no adviser provider code. **Tests:** exact_port_signatures (all parameters), import graph, strict model boundary additions and stored synthetic draft decoding. Interpretation behavior tests remain unimplemented until T3.2. **Accept:** schema JSON makes the four collections distinct; ports expose typed shapes and no mutable/provider/transport capability. **Exclude:** model calls, regex strategy, inferred hard constraints, pricing and projection algorithms.

### T1.1c — Decision records and effective configuration

**Files:** extend core/models.py and core/serialization.py; create config.py. **Dependencies:** T1.1a/b. **Schemas:** DecisionStage, DecisionRecord, EffectiveConfig, optional explicit ModelConfig identifiers; C §8.3/8.5. Implement literal versions, stage order, parent/revision rules, selection→evaluation and execution→validation dependencies, precise failed/skipped issue requirements, strict config, derived config hash. Store hash validation is completed by T1.4; schema-only record references need not exist on disk.

**Reuse:** existing guidance is only an explicitly mapped V1 source; V2 does not read its ambient env. **Tests:** guardrails record-schema/negative tests, effective config extras/unknown IDs/environment independence, foundation canonical hashes. **Accept:** decision-record.json validates/roundtrips; reordered/orphaned/unknown-version records fail; raw config block resolves identically despite legacy flags. **Exclude:** SQLite, coordinator, launch changes, provider credentials, trace UI and all V1 constructor changes.

### T1.1d — Remaining pipeline/state DTOs

**Files:** extend core/models.py; create core/events.py if event definitions become substantial. **Dependencies:** a–c. **Instructions:** implement remaining C tables in four serial, reviewable batches: (1) evidence/case/economic context, (2) intents/candidates/evaluations/selection, (3) rendering/validation/operations/budgets, (4) state/events/feedback and gateway/model results. Each batch is a separate handoff of at most 10–15 closely related models; list exports and examples before coding. No generic payload dictionary replaces the declared tagged union. Event tags/transitions follow C §8.7. Raw ModelResult retains malformed content for interpreter validation. Models alone must not set server terminal truth.

**Reuse:** official case/message fields, not existing mutable runtime classes. **Tests:** foundation/ports/record tests; add decoding examples in fixture bindings for each batch, preserving immutable tuple fields. **Accept:** the T1.2 codec can assemble typed P10, STABILISE, action, event and stage objects without model_construct. **Exclude:** every component algorithm. These batches are a shared-contract dependency, not parallel edits to models.py.

### T1.2a — Test fixture bindings and recorded codec

**Files:** create adapters/recorded.py; extend tests/v2/builders.py and add tests/v2/bindings.py if needed. Do not weaken existing tests. **Dependencies:** T1.1d. **Imports:** adapter→core/stdlib; test helpers may import V2 models and fakes. **Interface:** load_inputs(normalized_fixture)->RecordedInputs with C §8.5 inventory. **Instructions:** preserve raw case, incoming 54-day sheet, source layers, message bytes, exact quote offsets and declared price basis. Remove answers before the adapter sees data. Assemble strict typed objects, deterministic fixture UUIDs/content refs and bounded UTC/monotonic evidence. Provide a minimal typed reference for every port and attach all artifact bytes referenced by test commits/records. Raw validation bytes stay raw until validate_wire. Model responses stay raw until interpreter. No source winner, cost optimization, assessment extraction or validation answer is computed in the codec.

Implement test bindings for every label in test-catalog.md: input_mutation changes actual data/state/claim metadata; replay_schedule builds explicit fake gateway frames; port_failure_schedule injects a failing port in the offline root. Place those transformations in tests/v2, not live modules. Prepared layers retain independent records; baseline mock context may use its scripted fixture artifact but must be identified as mock. **Tests:** foundation fixture/golden integrity, guardrail normalizer, typed direct codec examples; all later component tests can now instantiate their own data. **Accept:** a missing or malformed source is represented, not replaced with an expected successful result. **Exclude:** golden expected-output import into production, model_construct, network, live data preparation.

### T1.2b — Complete injected offline loop

**Files:** create orchestration/loop.py, factory.py; extend adapters/recorded.py only for declared replay DTO support. **Dependencies:** T1.2a/T1.3/T1.4 basic storage. **Interfaces:** DecisionEngine.decide, OfflineRuntime.run_once, ReplayResult; named composition seams in C §8.4. **Instructions:** context construction, mock assessment, proposal, generation, evaluation, selection, renderer, validator, fake executor and feedback run through their exact typed ports. M1 uses injected scripted/mock components; arithmetic oracle may be real, advanced ports are explicit fixtures. Build the ten-stage record, verify candidate/evaluation identity and persist final output. Errors produce a failed stage and typed cannot-decide/recovery outcome. No alternate hidden legacy send path.

**Tests:** integration typed_complete_offline_loop_and_trace, frozen_replay, model_variability and final_record restart; active fake routing test is an example, not substitute acceptance. **Accept:** P10 demo returns 28.34/42/23400/24, €1,335,154.08, one scripted acknowledgment, all ten stage links and saved record. **Exclude:** production Arena/model adapters, real interpretation/strategy learning, multi-turn/recovery deployment. Every mock stage is visibly identified.

### T1.3 — Resolve config and injected composition

**Files:** config.py, factory.py; future CLI/Lab modifications deferred to T6.2. **Dependencies:** T1.1c plus available port contracts. **Instructions:** no implicit env/default discovery; inject clock/model/arena/store, frozen case capability and named bundle. Create only selected available implementations; importing factory must not import unimplemented optional features. Offline root cannot construct real transports or credentials. read-only evaluate_and_select uses generation/evaluation/selection ports and returns a certified evaluated candidate for behavioral comparisons. Prefix-require failures stay visible; missing functions aren't new expected-failure conditions.

**Reuse:** explicit runtime-guidance record only for named legacy adapter. **Tests:** config environment/unknown IDs, integration deterministic replay; actual selection tests join T4.3. **Accept:** two identical frozen configs have equal hashes; unsupported bundle fails before any gateway request. **Exclude:** new default agents, arbitrary plugin containers and provider autodetection.

### T1.4 — M1 persistent artifacts and structured records

**Files:** adapters/sqlite.py, core/serialization.py; schema SQL lives in the adapter. **Dependencies:** T1.1c/d. **Instructions:** implement SQLiteStateStore initialize/artifact bytes/DecisionRecord append/load/aclose first. Content refs are checked hashes; record hash includes full stored revision; semantic projection excludes incidental IDs/time but includes model outputs. Idempotent same bytes/record; reject conflicting existing identities. State head does not advance merely because a diagnostic/assessment record is saved. Later T5.2 extends this same store.

**Reuse:** Lab SQLite transaction conventions, no Lab tables or destructive migrations. **Tests:** decision_records_append_immutable_revisions, final_record restart and frozen replay (targeted required prefix). **Accept:** reopened database preserves bytes/record links and hash; no resend during record reload. **Exclude:** claiming full StateStore recovery or atomic claim/outbox implementation before T5.2. Partial later methods remain incomplete tests, never a global passing claim.

## M2–M7 parent-task contracts

These preserve the existing parent IDs. Large parents split into the listed outputs (one file/port per assignment); complete each dependent output in order. The exact test selectors are the function names in test-catalog.md. Each row includes acceptance and its scope exclusion.

| Task / dependencies | Exact owned production paths and instructions / reuse | Required tests / acceptance / excluded work |
|---|---|---|
| T2.1 / T1.1d | evidence/resolver.py then context.py: normalize applicable base/release/case records; resolve ID layers before scope; replace whole record; same-priority conflict blocks; preserve shadowed revisions; injected sources only | contracts/test_evidence.py precedence, replacement, conflict, scope, dates, basis. Same source revision/value reaches downstream. No SQL mutation, default discovery or inferred truth |
| T2.2 / T2.1 | evidence/prepare.py, adapters/data.py: use DataPackage/readers; strict explicit root/release; manifest/parser hashes; load verified prepared artifact before clocks; indexed records, no per-turn tree hashing | Add catalog PREP-01–06 warm/cold/corrupt/parser-change/source-change/explicit-path tests before implementation; prep actually feeds M1 loop. No prep planner or automatic release download |
| T2.3 / T2.1,T4.1 input schema | evidence/claims.py, adapters/claims.py, economics/estimates.py in separate assignments: resolved facts view for canonical checks; current quote field-level standards; estimate scenario range with shared basis/record refs | evidence shared projection and economics quote-standard tests; validation confidentiality/claim cases. Same cost source in claim and estimate, no unsupported basis. No point estimate presented as calibrated interval or internal claim disclosure |
| T2.4 / T2.1–3 | evidence/context.py, documents.py: add dynamic case/session records, whole-ID letter/news replacement, all case parts and parse gaps; formula strings preserved | Add catalog CONTEXT-01–04 document/message/case invalidation, multipart scope, formula provenance; context hash changes for meaningful inputs. No universal workbook intelligence or basket claim fabricated from first part |
| T3.1 / T1.2a | tests/fixtures/v2/p10.json and new held-out-labelled replies: preserve original evidence, exact spans, scenario labels and role/condition uncertainty; labels separate from inputs | Interpretation positive/negative/metamorphic fixtures; collect manifest after additions. No labels learned from the final score or silent edits to existing goldens |
| T3.2 / T1.1b,T1.2a | intelligence/interpreter.py then fallback.py: validate draft schema/spans/IDs/conditions, independent hypotheses, histories; injected ModelGateway; timeout bound; safe fallback plus call identity | contracts/test_interpretation.py, behavior uncertainty/refusal/injection. Grounding valid and numeric discount never invented; no candidate, price or action authority |
| T3.3 / T3.2 | adapters/model.py, orchestration/budgets.py: provider-purpose DTOs, absolute queue+request budget, cancellation and usage trace; mock transport first, no retries | Add MODEL-01–06 timeout/cancel/late result/refusal/partial JSON/queue budget tests; current timeout/malformed/grounding/projection tests pass. No real inference, thread daemon or old probe treated as protocol proof |
| T3.4 / T3.3 + separate funding | labelled evaluator tool under existing experiments tooling; no core modifications; fixed endpoint/prompt/model fingerprints and held-out reports | Local fixture controls before any funded batch; record precision/recall/citation faults/latency. No hosted negotiation or quality claim from fake results |
| T4.1 / T1.1d | adapters/official.py then economics/official.py and closing.py: pinned kit costs/terms/components via oracle; all-field legality, quote-reference estimates; tagged unavailable alternate | contracts/test_economics.py parity, relationship ticks, standards, basis; all closing triggers in recovery. Cost parity to cent. No general inverse, zero-cost unknown or acceptance of nonstanding alternatives |
| T4.2 / T4.1 | economics/prices.py then candidates.py: bounded legal non-price combinations and positive tick set; certify every candidate; no default invalid package; explicit infeasibility | economic generation/budget/impossible-must-have tests; validation negatives. Only P10 legal volume/options, prices certified; no unsafe snap or learned supplier valuation |
| T4.3 / T3.2,T4.2 | strategy/baseline.py, capacity.py, selection.py, registry.py as separate tasks: grounded intent direction, refusal/approval handling, approved batch membership, deterministic cost-ceiling/ties; explicit registered bundle | behavior suite plus deterministic selection tests. Meaningful flip changes intent/affordable choice; greeting changes neither; cost ceiling still dominates. No router, learned acceptance or pricing in model |
| T4.4 / T4.3 | strategy/selection.py optional BoundedModelSelector; read-only CandidateResearch facade injected from loop; one approved ID and fixed-batch checks | selection optional fault cases; add EXT-01 interchangeable dummy bundle. Invalid/edited ID or timeout has certified deterministic fallback. No default activation or unrecorded simulator batch |
| T4.5 / only justified gap | economics/prices.py optional solver subtask; specify branch, bounds, certified residual and tick first | Add NUM-01–05 root/two branches/unreachable/minimum/rounding; known reference preserved. No port to current inverse; finite search remains default |
| T5.1 / T4.1,T2.3 | execution/render.py then validation.py: templates only; typed claims; validate_wire parse wrapper then validate_action; complete independent offer/question/close checks and exact certificate bytes | entire test_validation.py and final payload integration; limits exactly 300/8000/3/20/5/3. Invalid value/action/disclosure rejected; no repair, invented claim or arbitrary model prose |
| T5.2 / T1.4 | adapters/sqlite.py, orchestration/state.py: implement event projection first, then atomic CAS/state/claims/outbox transaction; exact duplicate source dedupe; versioned assessment history | test_state.py, refusal/restart tests; add STORE-01–04 crash barriers/corruption/out-of-order/conflicting key. Same id/bytes survive; no terminal from local journal or caches |
| T5.3 / T5.1–2 | execution/executor.py then recovery.py and adapters/arena.py: typed allowed endpoint gateway, one owned operation, bounded reconciliation; exact payload retries, fresh admissibility and lease/deadline/round inputs | test_recovery.py uncertain/open/changed standing; add TIME-01–04 and ENDPOINT-01; rejection/unknown distinguished. No uncertain abandonment, invented fresh deadline or production credential in tests |
| T5.4 / M1–M4,T5.1–3 | orchestration/loop.py, intelligence/feedback.py, orchestration/budgets.py: serial full lifecycle, supervise faults, all close reasons same evaluator, deterministic feedback attribution; complete resume/close | recovery all reasons/faults/restart and integration full records; add FEEDBACK-01–03 ambiguous claim mapping/multi-field deltas/question answer. No async workers, causal-learning claim or swallowed exception |
| T5.5 / T5.1–4 | adapters/legacy.py only: V1Adapter maps candidate/close requests to new boundary; original bytes/config identity retained; never bypass validator | Add LEGACY-01–03 legacy invalid output/close request/identity difference; baseline replay still exact. No V1 source changes or old terminal state assumed authoritative |
| T6.1 / M5 | local evaluation scripts and tests/fixtures/v2 held-out suite; no new core modules; compare frozen V1, v1-adapted, V2 baseline/adaptive separately | All required contract/integration/acceptance tests; inherited failures reported and selected release gate resolved. No hosted performance claim from scripted replies |
| T6.2 / T1.3,M5 | adapters/lab.py then existing lab/checkpoints.py, worker.py, runner.py and cli.py only under explicit later assignment: versioned selection/config/prep hashes, same V2 factory; legacy schema preserved | Add LAUNCH-01–04 CLI/standalone/checkpoint/installed resource equivalence and old-worker rejection. No default V2, new dashboard, deployment or alteration of historical results |
| T6.3 / T6.1–2 + separate funding | existing Lab campaign manifest/results and experiments/LOG.md; frozen arms/cases/usage/independence, exact registered budget | Planned original-session completeness and timing/failure gates; no cached repeats counted independent. No incidental practice/inference allowance |
| T6.4 / T6.3 | report/finding and tracker, named recommendation only after promotion instruction | Review complete comparable original results and scoped thresholds; no default switch from one P10 observation or inconclusive result |
| T7.1 / stable M5 + category gate | new strategy/<category>.py and relevant evidence projection only; no core rewrites | New per-category contracts/replay/held-out comparisons; no global trait enablement |
| T7.2 / stable M5 + information-value gate | strategy/questions.py, evidence/documents.py known parser; bounded information action | Tests for scarce-round cost, trusted worksheet figures and source scope; no universal document reasoning |
| T7.3 / stable serial M5 | new orchestration scheduling module, gateway/key admission as explicitly reviewed async extension | Worker/watchdog, immutable snapshots/CAS, no lock over await, ten-session/shared-key/deadline tests; no final async use before gates |
| T7.4 / selected F treatment | one strategy module per isolated proposal/selection treatment and preregistered evaluation manifest | Extension contract plus outcome evidence; no multi-agent framework, broad portfolios or learning platform |
| T7.5 / verified quantity/basis | evidence basket/account projections, economics estimates only where typed basis exists | Multipart/unit/account scope and scenario tests; no supplier-wide metric misrepresented as part-specific or invented basket price |

## Independent work after contracts freeze

T1.1 batches share models.py and merge serially. After T1.1d plus fixture codec, evidence resolver, official-economic adapter, interpreter with fake ModelGateway, final validator with fake economic/claim ports, and state/event store with dummy valid actions can proceed in separate branches. Each owns only its package; changes to shared models/tests require contract-owner review. Strategy begins with recorded assessment/evaluations; interpreter does not wait for a real provider. M1 integration remains its own owner and proves substitutability before modules are combined.

Suggested owners: Decision owns strategy/selection/assessment coordination; Evidence owns resolver/prep/claims; Runtime owns store/coordinator/gateway; Evaluation owns fixture labels/catalog/gates. Names beyond the existing Decision owner are unassigned. The plan prepares delegation; no coding agents were launched in this preparation.

### T1.1d first bounded evidence handoff — approved 10 October 2026

Source: `6880d7a`. The requested inventory is exactly these twelve models:
EvidenceScope, Provenance, TemporalValidity, DisclosureRule, IndexFact, ScorecardFact,
CostFact, QuoteFact, ContractFact, ForecastFact, OrderPriceFact, TextRecord.
The user explicitly requires excluding any member with an unresolved contract.

**Implementable exports (4):** EvidenceScope, Provenance, TemporalValidity, DisclosureRule.
Dependencies: FrozenModel, SourceRef, strict identifier/hash validation and canonical
serialization from T1.1a–c; stdlib date/datetime and Pydantic. No feature services.
Examples/tests: tests/v2/contracts/test_evidence_dtos.py decodes P10 supplier/part scope,
source provenance and temporal/disclosure metadata; round-trip, immutable Python/JSON
boundaries, invalid IDs/hashes/dates/times and enum checks. Run alongside foundation,
hardening, guardrail, boundary tests and the full V2 suite with core/config required.

**Excluded members (8), pending explicit field contracts:**
- IndexFact: value numeric type and month encoding are not specified for this payload.
- ScorecardFact: quarter encoding and numeric types of otd_pct/ppm are not declared.
- CostFact: cost_base type/meaning and confidence_pct type/range are undefined.
- QuoteFact: observed_terms shape and validity type are undefined.
- ContractFact: clause_refs element type (source revision or clause identifier) is undefined.
- ForecastFact: period encoding and quantity/change_pct numeric types are undefined.
- OrderPriceFact: quantity numeric type is undefined; fractional quantities versus counts
  cannot be settled by reusing an unrelated integer term field.
- TextRecord: document_kind and declared_role vocabularies (open strings versus enums)
  are not specified.
No placeholders, partial EvidencePayload union or EvidenceRecord are introduced.
These exclusions are specification gaps, not completed DTOs.

**Later handoffs:** EconomicContext, scenario_policy and standards_by_supplier remain
excluded; their concrete definitions belong to the economic-context batch. NamedEstimate.name
currently says "from method's registered enum". No registry values are declared. The later
contract must explicitly choose a registered method-specific enum (and enumerate values) or
revise to a validated string with defined validation/authority rules. This handoff preserves
the registry requirement and does not silently choose the string alternative.
