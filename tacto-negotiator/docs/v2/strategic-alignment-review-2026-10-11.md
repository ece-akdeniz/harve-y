# V2 strategic alignment and architecture review

11 October 2026, Europe/Zurich. **Review and proposals for approval; no implementation or contract revision.**

Assessed a88bf86 plus the existing working tree, including addendum K–M. Production code,
existing specifications, tests, fixtures, dependencies and defaults were left unchanged.
This document is the only repository addition made by the review. Verification scripts,
exported baselines and test reports are in /tmp. No inference or Arena service was called.
Primary research publication pages were consulted through the web.

## 1. Executive assessment

**Keep the architecture, change the development objective and next gate.** The working V2
provides a useful economic and admission foundation. It has not demonstrated supplier
understanding, strategic adaptation to language, persuasion, or negotiation performance.
The next substantial investment should produce a grounded LLM decision and a small independent
benchmark. Completing persistence, all DTOs, every codec binding, or deterministic capacity
heuristics first would delay the most informative experiment.

Five findings drive the recommendation:

1. **Economics and provenance are real; intelligence is absent.** The resolver-to-estimate
   relationship-cost reversal is useful and reproducible. The actual interpreter echoes text,
   the proposal policy emits fixed intents, and the selector minimizes the cost of supplied
   packages. Neither the reversal nor the thousand passing V2 tests establishes bargaining skill.
2. **Three local correctness gaps remain inside the implemented slice.** Direct probes
   reproduced ignored CaseContract.case_facts, admission of an incomplete outgoing sheet,
   and failure to enforce a configured price tick. Close these narrowly before expanding
   model-driven offers. These are consumer checks, not another framework project.
3. **The fastest intelligence experiment needs no redesign.** Implement the existing model
   envelopes, a cancellable gateway, a grounded interpreter and an approved-ID LLM selector.
   Use affordable legal alternatives and questions whose selection must respond to supplier
   conditions even when the cheapest package stays unchanged. Retain fixed templates.
4. **Meaningful proposal generation needs a small, explicit contract revision.** The gateway
   has no propose task, and StrategyIntent exposes a single dimension/direction without
   structured joint conditions or price-search instructions. Existing Python ports can host
   an LLM implementation, but their current gateway projection cannot naturally express it.
   Do not disguise proposal generation as select, simulate, or a generic payload.
5. **Competitive progress needs outcomes and a realistic release horizon.** Start labels and
   decision comparisons with the first model component; add reactive multi-turn evaluation
   before claiming effectiveness. The repository declares a noon freeze today. The multi-day
   V2 plan below cannot credibly be presented as a fully ready Sunday competition replacement.

The immediate sequence is: **three bounded correctness fixes → grounded interpreter →
language-conditioned selector with held-out evaluation → LLM-directed legal proposal generation**.
Durable sending remains essential before real V2 execution, but is outside the offline
intelligence critical path.

If “remaining time” means the current event, keep V2 offline unless the full operational gates
are independently satisfied before freeze. Any near-term experiment using the already integrated
V1 adviser is a separate, explicitly funded and rehearsed release choice; its historical evidence
does not establish readiness of this working branch. If development continues beyond the event,
use the six capability milestones in §7.

## 2. Current capability assessment

### Investigation and verification

Read root/package AGENTS, docs/README and the implementation checklist; V2 A–F, C's exact
contracts, roadmap/task/implementation/test guides, tracker and addendum; every working V2
component; representative direct/integration/unfinished tests; the saved source-47 trace;
and V1 agent, adviser, economics, evidence/context/dossiers, inference, runner, memory and
Lab integration code. References to historical baseline and official kit were followed.

The scoped V2 command in the addendum, requiring all implemented modules and consumed
contracts, reproduced **1,013 passed, 364 xfailed in 5.76 seconds**. The xfails are explicit
unfinished features. V2 Ruff and frozen V1 first-message replay pass. The existing 28-case
offline integration group is included in that run. The saved
/tmp/v2-offline-source-47-trace.json parses, verifies its digests, and contains:

- Eight diagnostic stages: snapshot through validation.
- An uninterpreted ambiguity observation, one fixed keep intent and two supplied offers.
- EUR 429,044.44 for EUR 45/unit versus EUR 401,600 for EUR 49/unit.
- Selection by minimum-cost-test-v1, a valid certificate and exact fixed-template message bytes.

This is an **offline decision**, not the specified complete ten-stage loop: execution and
feedback are absent. JSON trace reload proves diagnostic consistency, not durable operation
ownership or independent source authenticity.

| Capability | Actual state and evidence | What remains unproved or absent |
|---|---|---|
| Values, assessment contracts, records/config shapes | Strict immutable models, canonical hashes, Protocol declarations and config resolver; exercised contracts | Working record storage and full executable config/factory wiring |
| Layered resolution | Real precedence, collisions, scope-after-precedence, preserved kinds and source revisions; direct negative tests | Real file/source preparation and authentication |
| Context/recorded assembly | Real typed focused codec and assembler; rejects document hydration; explicit nominal/disabled contexts | Complete recorded fixture contract, freshness rules, relevance ranking; case-fact consumer gap below |
| Source-cost economics | Real canonical cost admission and explicit assumption-based estimates; source revisions reach economics | CostFact is not proof of full supplier cost; no learned valuations, broad estimates or automatic uncertainty scenarios |
| Official arithmetic/evaluation | Pinned kit oracle, economic term resolution, components, candidate batches and cost-policy admission; direct parity tests | General closing evaluation, multiple robust scenarios, broad joins; configured tick gap below |
| Supplier interpretation | InputEchoTestInterpreter: cited raw messages, fallback status, unknowns | Semantic extraction, roles/conditions/preferences, live-provider quality |
| Strategy proposal/selection | Fixed supplied-intent policy and nominal minimum-cost selector; interchangeable test implementations | Language-driven judgment, concession planning, supplier-reaction estimates |
| Candidate generation | At most 20 distinct supplied packages or one registered question | New offers, legal option/tick search, combined trades, useful question catalog |
| Rendering/validation | Exact no-claim templates; recomputation, snapshots, ownership, clocks/rounds, recipient and exact bytes | Full-sheet admission gap; claims, arbitrary prose, close/accept/walk, raw-wire convenience |
| Orchestration | Injected one-decision coordinator, eight stages, deadline checks, diagnostic rejections and cancellation propagation | Model call/token accounting and fallback reserves; hold/close handling, research registration, execution, feedback |
| Memory/persistence/runtime | Schema shapes and prior assessment linkage; immutable recorded history | Working projector/store, memory loading, operation transactions, gateway/executor/recovery and multi-turn loop |
| Evaluation | Contract, arithmetic, safety and economic counterfactual tests | Independent semantic scores, measured language adaptation, reactive outcomes and held-out performance |

Most implemented modules are adequately tested for their declared bounded behavior. The three
probes below expose important omissions despite those tests. Model/provider behavior and
competitive performance are entirely unavailable, not merely under-tested implementations.

### Reproduced discrepancies inside V2

**R1 — case facts do not enter context resolution.** In
[evidence/context.py](../../src/negotiator/v2/evidence/context.py), build_context resolves
prepared.records and never consumes case.case_facts. C's recorded binding explicitly puts
base/release in preparation and case facts in CaseContract. Moving the saved case EUR 47
record into that field, while retaining prepared release EUR 43 and recomputing hashes,
resolves EUR 43. The demonstration passes because its private recorded fixture places the
case override inside preparation. The resolver algorithm works; its consumer misses the
public case-fact route. Fix the join before relying on normal case overlays.

**R2 — economic completeness is mistaken for outgoing completeness.** In
[execution/validation.py](../../src/negotiator/v2/execution/validation.py), offers are
recomputed economically without an exact outgoing-field check. The evaluator fills omitted
terms from standards/defaults. Removing payment_days from the saved package, regenerating
its fingerprint and render hash, produces a valid validation result, although the case
requires both price and payment. Keep economic resolution of partial observed sheets;
require every negotiable field on each transmitted sheet and prohibit fixed/extra fields.

**R3 — configured ticks are ignored.**
[economics/official.py](../../src/negotiator/v2/economics/official.py) tests price modulo
Decimal("0.01") rather than the supplied cost policy tick. With a valid policy tick of
EUR 0.05, EUR 49.01 remains numerically valid and must-have compliant. Enforce the declared
tick and protocol cent precision. Reject or explicitly declare unsupported tick conventions;
do not snap an inadmissible output.

These are direct service reproductions using validated/reparsed inputs and refreshed identity
hashes, not failures hidden behind stale hashes. Probe output is
/tmp/v2-review-safety-probes.txt; the reproducible script is
/tmp/v2_review_boundary_probes.py, using the existing saved trace. No production/test change
was made to reproduce them.

Further bounded limitations matter for planning:

- OfflineDecisionCoordinator rejects a supplied CandidateResearch implementation outright.
  The research port is declared, not executable in this coordinator.
- It produces selected/cannot-decide outcomes; schemas for hold/request-close do not establish
  implemented decision paths. Hold is not an outgoing package candidate.
- Async work shares compute/deadline time, but the coordinator does not itself enforce
  model-call/token totals or preserve configured fallback/submission reserves. Current
  zero-call components cannot prove those obligations.
- EvidenceContext.relevance is empty. Assembly globally blocks error gaps/conflicts;
  unrelated unusable evidence can block an otherwise evaluable decision. This is a
  conservative availability limitation, not permission to discard adverse evidence.
- Multiple robust scenarios and the documented kit/Decimal half-cent mismatch fail explicitly.
  Preserve those failures; do not repair numbers to obtain apparent parity.

### Documentation status

Addendum K–M is substantially accurate about the bounded demonstration and unfinished intelligence.
Its general used-action/context claims need the qualifications above. Earlier summaries lag:
docs/README says V2 is unimplemented; B's status and the tracker introduction do likewise;
D's latest bounded completion remains K; tracker rows still describe batches/strategy paths
that L/M subsequently implemented. These mix historical and current snapshots.

After approval, update a short current capability table and link dated evidence. Preserve
historical entries. Do not infer parent completion from D2/D11 schema completion, a factory.py
filename, diagnostic reload, or test counts.

### Regression classification against actual baselines

The initial current legacy run, outside the socket-restricted sandbox, reproduced
**328 passed, 19 skipped, 17 failed**. Combined with scoped V2, this accounts for the reported
**1,341 passed, 19 skipped, 364 xfailed, 17 failed** without attributing failures by directory alone.

To remove data-discovery differences, exported committed trees, selected each tree's source
through PYTHONPATH, used the same interpreter/dependencies, supplied the pinned local
ARENA_DATA path, removed incidental inference/agent/release environment configuration,
and reran all 364 non-V2 tests with localhost access:

| Source | Passed | Failed | Skipped | Comparison |
|---|---:|---:|---:|---|
| Current working tree | 348 | 16 | 0 | Same failures and messages as committed baseline |
| Pristine a88bf86 | 348 | 16 | 0 | All 16 match current |
| Historical 3653046 | 362 | 2 | 0 | Only the two missing-uv failures |

The six historical modules cited in A also reproduce **60 passed**. Relevant legacy
source/test files have no changes from 4c905b1 to a88bf86 or from a88bf86 to the working
V2 changes. Thus **no newly introduced legacy regression was detected in this V2 increment**.
Fourteen non-environment expectation failures predate it and differ from historical main.
That establishes provenance; it does not establish whether every old expectation is still
correct after remediation.

| Failure group | Classification and nature | Priority |
|---|---|---|
| Context mocked-agent test (1), inference mocked-agent tests (4) | Confirmed inherited; PackageAgent.propose reconstructs history before patched _propose, so empty threads raises KeyError | Fix/test compatibility when using these paths; not a V2 intelligence blocker |
| Evaluator inverse test (1) | Confirmed inherited arithmetic/search regression: ordinary target returns None instead of the known EUR 15 root | Blocking if invoked; keep V2 independent of this helper |
| Evaluator final-offer tests (2) | Confirmed inherited behavior mismatch; reconstruction overrides directly assigned memory and changes counter/rival action | Settle acknowledged-history semantics before releasing that V1 path |
| Runner closing tests (5) | Confirmed inherited differences: pending close returns no deal, stale-close cases lack expected deal result, closing trigger differs | Release-critical if these paths are used; whether each expectation should change remains unresolved |
| Scaffold payment test (1) | Inherited formula/expectation disagreement; code returns exact ratio 1.011878… while test expects obsolete 1.0222 approximation | Verify independently and revise together separately; do not restore a wrong formula |
| Lab subprocess tests (2) | Environment-dependent in all three trees: missing uv, before intended worker/checkpoint behavior runs | Provide locked tooling before release; underlying assertions remain untested here |
| P01 context test (1 in initial 17) | Environment-dependent missing default data package; passes with explicit pinned data | Use explicit data configuration in verification and launch |

Repository-wide Ruff reports four findings in unchanged evaluator/guards/runner files; V2
Ruff is clean. Track and resolve them for the selected release. The current directory is not
historical main. Passing historical tests does not negate the original audit's correctness defects.

Reports: /tmp/v2-review-regression-comparison.json, the three
/tmp/v2-review-*-fixed-data.txt/.xml files, and runner /tmp/v2_review_regressions.py.
The initial sandbox-only legacy run was interrupted after localhost failures/stalling and
is not counted as a completed comparison.

## 3. Architectural assessment

The core separation is commercially useful: models can vary while arithmetic, evidence
authority and admission remain constant. The risk is treating interfaces as an already capable
negotiator, or forcing all future strategy into a weak single-dimension intent language.

| Boundary | Responsibilities, coupling and LLM suitability | Recommendation |
|---|---|---|
| Preparation/resolution | Correct separation of precedence/scope/provenance; no statement promotion. Preparation is still declared/synthetic | Preserve resolver; fix case-fact consumption; wrap pinned readers for first real evidence types |
| Context assembly | Correct immutable snapshot; strict global gates, empty relevance, no documents. Private recorded DTO is focused, not full codec completion | Reuse; add bounded relevance/disclosure projection, not retrieval platform |
| Interpretation | Collections fit requests/refusals/conditions, approval gaps and hypotheses; exact quotes do not establish entailment | Existing port suffices; implement semantic interpreter and independent labels |
| Proposal | Async read-only seam fits. Single dimension/direction cannot explicitly express joint conditional trades/search/priority | Small versioned intent/projection extension in milestone 2; no extra strategy service |
| Generation | Right owner for legal numerical construction. Supplied wrapper is a test implementation | Add bounded legal option/tick construction with incomplete-search diagnostics |
| Economics | Right authority, parity tested. Partial resolution is useful but insufficient for outbound admission | Preserve; correct tick check; settle nominal convention when multiple scenarios are used |
| Selection | Approved-batch seam permits strategic value beyond lowest immediate cost | First LLM ranking experiment here, with relative economics and grounded history |
| Rendering | Templates establish strong boundary. Renderer need not call provider, but signature has no communication-draft artifact | Templates now; narrow draft handoff later, not text hidden in rationale |
| Validation | Correct separate authority; independence does not mean duplicate formulas | Explicit outgoing fields/ticks and later claim/commitment checks |
| Orchestration | Genuine substitution; enough for one offline decision. Research/hold/close paths absent | Local ledger/fallback/capability extensions; keep coordinator |
| Memory/store | Sensible separation of server/strategy/operation truth; schemas do not establish behavior | Supplied history initially; durable state/operations before real sending |
| Model/provider | Typed async gateway and config/results fit provider replacement | Implement consumer closure; register propose only for its consumer |

### Proposal, generation and selection responsibilities

**The LLM chooses the commercial objective and trade hypothesis.** Seek a reduction in return
for legal delivery flexibility; test whether commitment matters; stop repeating a specifically
refused exchange; ask who can approve a condition. It considers offers/concessions, supported
observations, uncertainty and remaining rounds.

**Code constructs exact numerical packages.** It takes allowed option IDs, an explicit
anchor/reference and registered search instructions; creates complete legal tick sheets;
and records explored alternatives/rejected regions. Supplier numbers remain observations
until admitted through code. The model can request an aggressive price band or legal option;
it has no numeric execution authority. This preserves the repository invariant that transmitted
numbers and sheets come from code.

**Economics evaluates concrete packages through the official model.** It does not invent
acceptance probabilities or turn should-cost into a hard supplier floor. Generation may use
bounded economic calls; final evaluation/validation still certify exact retained output.

**Selection chooses the concrete action, including a question.** It may prefer an affordable
higher-cost package when grounded supplier information makes the exchange more credible, or
spend a round clarifying a material ambiguity. Predictions about supplier reactions remain
hypotheses, separate from official buyer cost.

Keep strategic/tactical reasoning inside these ports. No separate strategic-planner service
is needed. Record short explanations connecting observation, exchange and remaining unknown;
do not persist private chain-of-thought.

Do not assign invented acceptance probabilities to optimize “expected negotiation value.”
When calibrated predictions exist, compare terminal cost and no-deal consequences under explicit
assumptions. Until then, use qualitative uncertainty and outcome experiments. Preserve the
difference between buyer cost if accepted and the likelihood/trajectory of acceptance.

Hold belongs to an engine outcome with bounded recheck, not a fake zero-cost candidate.
A close request goes to a fresh deterministic closing evaluator. Models never bind accept/walk
or establish terminal truth.

## 4. Recommended intelligence architecture

~~~mermaid
flowchart TD
    Raw["Immutable messages, sheets and acknowledged history"] --> I["Grounded supplier interpreter"]
    E["Resolved evidence and relevance/disclosure projection"] --> I
    E --> P["LLM strategic proposal policy"]
    I --> A["Assessment: observations, reports, hypotheses, unknowns"]
    A --> P
    H["Read-only attempts, concessions, conditions and questions"] --> I
    H --> P
    P --> G["Code: complete legal options and price-tick candidates"]
    G --> O["Existing official economic evaluation"]
    O --> S["Approved-ID strategic selection"]
    A --> S
    H --> S
    S --> R["Templates first; validated communication draft later"]
    E --> C["Canonical claim and disclosure verification"]
    C --> R
    R --> V["Independent final validation and exact bytes"]
    V --> T["Offline trace and evaluation"]
    V --> X["Later: atomic ownership, executor and recovery"]
    X --> F["Observed feedback and authoritative state"]
    F --> H
    Q["Optional bounded hypothetical lookahead"] -.-> P
    Q -.-> S
~~~

Interpreter, proposer and selector are logical components, not autonomous agents.
One configured model can serve different purpose projections/prompts. Separate interfaces
support fault attribution and ablation without requiring separate providers.

### First LLM decision: two calls, existing tasks

Start with **interpret + select**, using supplied generation as a temporary candidate universe
and a small registered question set. Test whether language changes an affordable choice:
a supplier-relevant exchange versus a cheaper but explicitly unsuitable alternative.
The selector must do more than restate the minimum cost.

Project code-authored descriptions of exact approved packages, relative cost/scenario ordering,
attempts/refusals and grounded assessment. SelectionOption.summary supports a bounded description
today; do not encode an untyped protocol inside it. No absolute reservation/fallback values,
private targets, full estimates, hidden scores or expected-action labels enter provider input.

Implement M's **15 missing gateway exports**, retaining every ModelInput/ModelResult member,
plus SelectorResponse for the next consumer. This is a consumed handoff, not D12/D13 completion.
An interpreter-only feature leaves fixed policy unable to use understanding. A selector-only
direct treatment is a useful cheaper comparison, but not the sole evidence representation.

### Proposal intelligence within the call budget

C permits at most **two calls total**, 35-second compute, initial interpreter/selector caps of
8/4 seconds and fallback/submission reserves. Fresh ModelBudget objects cannot reset the
decision ledger. Separate interpreter→proposer→selector→writer calls conflict with the contract.

For milestone 2, use **interpret + propose**, then a mechanical selector that honors validated
strategic priority and ranks concrete variants economically within an admitted intent. Include
a baseline and clarification fallback. This is a small certification/ranking rule, not a
deterministic negotiation strategy. Keep interpret+select as the comparator.

Later compare a fused assessment/proposal draft plus select if measured latency/quality
justifies adapter coupling. A combined task requires explicit output contract and snapshot
identity; do not invisibly repurpose select. Raising the call cap needs measured benefit,
latency evidence and a deliberate contract/operational decision.

### Interpretation, opponent model and memory

Use existing assessment types:

- Exact offers/requests/refusals/conditions become GroundedObservation with original spans
  and package references when identifiable.
- Numerically explicit supplier constraints become ReportedConstraint, retaining
  supplier_reported authority, conditions and active/stale/superseded status.
- Preferences/willingness/tactical interpretations become PreferenceHypothesis with support,
  contradiction and qualitative confidence. No numeric willingness from tone.
- Approval/scope/contradiction/missing-support ambiguities become unknowns and registered
  clarification opportunities.

An illegal supplier 54-day statement remains evidence of what was said; outgoing construction
still uses legal options. Approval language does not prove authority or a standing acceptable
sheet. Retain every condition; quoting a consequent without its antecedent is not grounded agreement.

The first opponent model is this **qualitative cited assessment over history**. No separate
belief engine is needed. Role changes weaken prior assumptions. Probabilistic utilities,
cross-session learning and imitation remain experiments.

First memory needs raw messages/standing sheets, acknowledged buyer packages and changes,
scoped refusals/conditions, questions/known answers, latest validated assessment and parents,
and claim/operation status when enabled. Draft proposals are not sent actions. Supplied
immutable history suffices for offline multi-turn tests; no database prerequisite.
Later StrategyMemory can reference a strict namespaced hypothesis/plan artifact. Keep raw
contradictions outside any one model's summary; no embedding store or generic memory service.

### Evidence as commercial intelligence

| Evidence effect | Example | Authority |
|---|---|---|
| Changes official economics | Admitted cost plus explicit full-cost/rate assumptions changes relationship penalty | Projection/estimate/oracle path; buyer economics unchanged |
| Changes strategy/argument | Delivery evidence supports a schedule question; notice clause supports timing challenge; opposing drivers weaken a cost-rise account | Cited observations/hypotheses and separately verified outward claims; no automatic cost/price change |

The current demo proves only the first. Build the second with a small packet: applicability,
latest offer/standards, a handful of relevant drivers/contracts/performance observations,
a retained contradiction, gaps and disclosure status. Use existing indexes and deterministic
topic/date/scope selection before semantic retrieval.

Relevance ranks information, not truth. Preserve adverse/contradictory records. Declared
current status is separate from executed freshness rules and authenticated source bytes.
Missing proof stays unknown. Estimates retain distinct assumptions and citations.

Filter provider input recursively, including previous assessment numeric effects and raw
text. Allowlisted fields can contain private prose. Do not alter an EvidenceRecord payload
under its original identity and call that authenticated redaction. Use approved snippets
with lineage, or exclude unsafe records until their projection exists.

Each move should identify the supported opportunity, its limits, and a disclosable argument
if available. An unsupported supplier assertion can justify a question without becoming a
canonical cost or outward verified fact.

### Grounded communication

Keep no-claim templates for milestone 1. Add registered questions and conditional-exchange
explanations with code-inserted terms before unrestricted writing.

Later give a wording model only the selected action, approved claim sentences/IDs, permitted
snippets, tone and communicative objective. Return a strict communication draft with lineage
and no action fields. An adapter injects that artifact into rendering; renderer itself does
not call the provider.

Renderer binds exact terms and claims. Independent validation checks final prose, figures,
confidentiality, conditions/commitments, recipient, usage/limits and exact bytes. Check numbers
against approved terms/claims; stripping IDs cannot leave an unsupported assertion. Nonnumeric
promises need an allowed commitment vocabulary too.

No universal deterministic check proves arbitrary natural-language entailment. Start with
canonical factual/commitment clauses and bounded connective language. A supplemental model
judge is an evaluated aid, not authority making free prose safe. Failed wording uses the
approved template without changing the commercial decision.

## 5. Required architectural changes

These are proposals, not frozen-C amendments. Significant revisions need exact fields,
version/migration and affected-consumer tests before coding.

| Timing | Problem and repository evidence | Alternatives | Recommendation and trade-off |
|---|---|---|---|
| P0 now | R1–R3: case facts, outgoing completeness, ticks | Caller/fixture discipline versus consumer checks | Three narrow fixes/negatives; keep partial incoming economic resolution. No DTO redesign |
| P0 now | Gateway/model components absent; coordinator only bounds total async time | Full-runtime barrier; legacy adviser; injected gateway | Consumed envelopes, async fake transport, shared call/token/time ledger and reserve. No daemon-thread reuse |
| P1 milestone 2 | No propose purpose in C D12/D13 | Provider bypass; overload select/simulate; new registered purpose | Versioned ProposeInput and strict draft. Reuse ModelResult union and current ports |
| P1 milestone 2 | One-dimension StrategyIntent lacks explicit joint bundle/search/priority | Independent intents; rationale parsing; typed directives | Versioned joint directives over legal option IDs, registered price-search instruction and strategic priority. More schema justified by combined trades |
| P1 milestone 2 | Supplied generation; 20-candidate global limit | Universal inverse; unlimited enumeration; finite bounded construction | Generate around observed/acknowledged anchors, legal options and small tick set; certify, retain incomplete coverage, no optimum claim |
| P1 milestone 2/3 | One question, generic body, no draft handoff | Unchecked body in rationale; writer framework; catalog/draft artifact | Catalog first, narrow draft handoff later. Renderer/validator coverage evolves together |
| P2 when used | Coordinator rejects research; main-batch membership excludes research options | Workflow rewrite; arbitrary IDs; registered bounded batches | Snapshot/budget-bound read-only registration, verify selection across registered batches. Not needed for first selector |
| P2 before robust use | Multiple scenarios lack nominal convention | First/average/no-estimate default; explicit designation | Approve nominal estimate/scenario reference, compute every declared scenario. No invented probabilities |
| P2 before sending | Durable ownership, gateway proof and closing incomplete | Mutable V1 runner; distributed stack; existing serial/SQLite direction | Planned transaction/outbox/recovery and fresh closing gates, independent of offline intelligence |

Do not migrate/split the 2,338-line core model file merely for elegance. Avoid speculative
models/stubs; private parser/ranking/search structures belong to their components. Retain
serial shared-contract ownership and import-boundary checks.

Reprioritize “interpreter plus deterministic capacity policy first”: keep the minimum-cost
control/fallback, and test LLM selection in the first intelligent slice. Elaborate deterministic
capacity traits/concession rules have no demonstrated advantage here.

## 6. Research roadmap

Primary publication pages were verified for these references; the 2017 and CaSiNo PDFs
were also consulted. This is method selection, not reproduction or proof of transfer to
Tacto. No cited result establishes that a proposed treatment wins this arena.

| Priority / technique | Evidence and limits | Procurement use, complexity and failure modes | Seam and evaluation |
|---|---|---|---|
| R0, immediate comparison design | Bianchi et al., [NegotiationArena, ICML 2024](https://proceedings.mlr.press/v235/bianchi24a.html), studies resource/trading/price dialogue and opponent-sensitive tactics. Gains against one model can reflect exploits | Low: compare different supplier behaviors/model families; do not copy deceptive urgency or expose private values | Common strategy ports; cross-opponent and equal-budget comparisons |
| R1, first optional treatment | [MERIT, ACL 2026](https://aclanthology.org/2026.acl-long.1155/) studies utility feedback, preference alignment and opponent awareness in AgoraBench, including prompting/training. Utility/human-preference assumptions differ from procurement costs | Low/moderate: code-derived relative costs/trades plus brief observed-outcome reflection. No training initially; fabricated supplier utility/hidden-score leakage are failures | Proposal/selector with/without feedback; same candidates, provider, token/time budget |
| R2, after useful generation | Leonardelli et al., [MESOs, 2019](https://www.sciencedirect.com/science/article/pii/S074959781630557X), reports six human first-offer experiments with economic/relational benefits. Human effects do not establish bot or later-turn transfer | Moderate: 2–3 complete packages of approximately equal buyer cost with different legal levers. Do not claim equal supplier value; choice may waste leverage | Generator/selector bundle; single versus choice-set offers, same total budget; actual sheet selection/outcomes |
| R3, qualitative opponent model | Baarslag et al., [opponent-modeling survey, 2016](https://homepages.cwi.nl/~baarslag/pub/Learning_about_the_opponent_in_automated_bilateral_negotiation-a_comprehensive_survey_of_opponent_modeling_techniques.pdf), organizes models/evaluation; utility/domain assumptions need informative observations | Low initially: cited preferences/refusals, one-field deltas. Multi-field changes do not identify weights; role changes weaken priors | Assessment/memory; no-model comparison on held-out future quotes and decisions |
| R4, labels and elicitation | [CaSiNo, NAACL 2021](https://aclanthology.org/2021.naacl-main.254/) supplies campsite multi-issue dialogues/persuasion annotations; associations are not procurement causal effects | Low/moderate: annotation ideas plus approval/condition/refusal labels and focused questions. Extra labels/questions must justify round cost | Interpreter/proposal; label ablation, ask-versus-offer under answer/refuse/no-answer counterparts |
| R5, bounded lookahead later | Lewis et al., [Deal or No Deal?, EMNLP 2017](https://aclanthology.org/D17-1259/), demonstrates rollouts in hidden-utility item bargaining. Trained small-domain models/rewards differ from uncertain suppliers | Moderate/high: a few approved candidates and one-step hypothetical replies. Hallucinated acceptance, role drift and self-confirmation are major risks | Simulation/research seam; equal-compute direct ranking, held-out response prediction and deadline stress |
| R6, suitable repeated interactions only | Liu et al., [opponent simulation, ICML 2026](https://proceedings.mlr.press/v306/liu26ef.html), combines in-context imitation and best-of-N search in repeated games. Short procurement threads may lack data | High for present needs: bounded opponent hypotheses, never server truth; nonstationarity/sparse history and call costs threaten value | Namespaced memory/proposal/selector; adaptation versus reset and equal-inference-cost comparisons |

Use [Faratin, Sierra and Jennings, 1998](https://eprints.soton.ac.uk/252117/) for simple
time/behavior concession controls, not a requirement for sophisticated deterministic strategy.
Its formal service-negotiation model supplies baselines, not procurement performance guarantees.

Immediate research investment is comparison design and small feedback/qualitative-model
ablations. Defer utility estimation, extensive reflection, deep rollouts, imitation, training
and account models until a simple LLM treatment exposes a measured gap. Asking can be tested
before lookahead without a calibrated value-of-information solver.

## 7. Updated development roadmap

### Success measures and minimal evaluation

| Objective | Measures and initial gate | Evidence can establish |
|---|---|---|
| Structural correctness | Required consumed contract/module gates, official cents/components, identity consistency, R1–R3 negatives; zero hard-invalid admissions in bounded tests | Correct scope, not language understanding |
| Evidence-grounded reasoning | Source/span validity, support/contradiction/missing distinctions, retained adverse evidence and disclosure | Attribution and measured semantic support on reviewed corpus |
| Supplier understanding | Precision/recall by constraint/refusal/condition/approval/preference category; false approval/invented numbers; unknown/fallback rate | Understanding for the tested held-out corpus/model/prompt |
| Strategic decision quality | Affordable controlled action differences, scoped refusal handling, useful questions, sound trade-offs; expert admissible-set review | Appropriate fixed-input choices, not counterfactual supplier outcomes |
| Negotiation performance | Terminal complete cost, official score where available, agreement/no-deal, meaningful savings/regret, rounds, timeouts, tokens/calls/spend and per-scope downside | Outcomes against tested reactive counterparts; live transfer requires funded original runs |
| Execution reliability | No conflicting/duplicate operations, invalid sends or fabricated terminal; exact ID/bytes across crashes, bounded recovery | Exercised operational capability, not persuasion |

Propose an independently reviewed **24-pair pilot** covering delivery/commitment preferences,
payment trade-offs in a separate legal synthetic case, conditional offers, scoped refusals,
approval ambiguity, conflicting/unsupported evidence, and irrelevant/injected text. These
are new proposed fixtures, not existing completed labels. Preserve P10's fixed payment,
options and compliant volume. Include language-only changes with economics fixed and cost-only
changes with language fixed.

Freeze held-out scenario/phrase groups before tuning; labels never enter production prompts.
Reviewers annotate spans, conditions/authority and admissible action sets, not one exact
demanded response. Include a justified higher-cost affordable exchange and ceiling-dominated
cases. Greetings preserve commercial behavior even if raw/trace hashes differ.

Proposed semantic gate: zero false critical numeric/approval assertions in the safety subset;
report category precision/recall/abstention, with quantitative thresholds agreed after label
review and before scoring. Finite zero failures are not a universal guarantee. Fake/recorded
drafts prove plumbing; authorized unseen-input provider runs measure model understanding.

Compare four arms with common evidence/economics/validation and total budgets:

1. Supplied minimum-cost test strategy.
2. Direct basic LLM selector using permitted raw/source-grounded input.
3. Grounded interpretation plus LLM selector.
4. One later feedback/opponent/proposal treatment.

Use the same candidate universe to isolate selection. For generation, allow new packages but
add a common-universe comparison to separate search coverage from decision skill. Record
provider/protocol/prompt/schema/model, source/case/config hashes, fixed clock, cache information,
permitted raw outputs, usage and all fallbacks. Compare actual costs as well as equal ceilings.

Reactive multi-turn suppliers must answer actual terms/questions. Fixed historical replies
cannot measure effects of a different offer. Withhold counterpart thresholds/preferences
from prompts; use conditional acceptance, refusal to provide information and role changes.
Calculate complete costs independently through the pinned kit. Include failures and no-deal
consequences rather than averaging agreements only.

For separately funded live studies, interleave arms where permitted, retain planned denominator/
original failures, and report paired differences/uncertainty by independent scenario/supplier.
Paraphrases, cache-identical runs and shared trajectories are not independent negotiations.
Post-run score/Cbest never enters strategy input; synthetic utility/regret remains labelled.
Simulator performance, hosted samples and competition results are distinct claims.

Implement manifests, a small evaluator and JSON reports/traces; reuse Lab records later.
No dashboard, agent evaluation framework or vector store is necessary.

### Priority and original-task crosswalk

| Classification | Workstream / existing tasks | Scope and real dependencies |
|---|---|---|
| Essential now | R1–R3; T3.1 labels; consumed T1.1d model envelopes; bounded T3.3 gateway; T3.2 interpreter; bring T4.4 selector/local T6.1 forward | Working economics/validator, purpose projection/shared budget; no full codec/store barrier |
| Essential now, next consumer | Useful T4.2 generation and LLM T4.3 proposal treatment | Explicit propose/intent revision, code-owned domains; only consumer contracts |
| Parallel | Bounded evidence packet/reader subset T2.1/2.2; labels/tool; inherited regression investigation; focused T1.3 composition | Shared contracts remain serial; independent files after handoff |
| Parallel / before multi-turn release | T1.4 artifacts, T5.2 store/outbox, pure feedback/history projection | Helpful early, not first offline decision prerequisite |
| Essential before live execution | Used-source authenticity/freshness; intended-scope T5.1 including close/claims if used; T5.2–5.4; launch T6.2; quota/lease/clock/round/terminal | Owned exact bytes/IDs, authoritative proof, crash/restart gates |
| Research backlog | Feedback/opponent/MESO/elicitation/rollout treatments | Common services and explicit budget; no whole-M5 barrier for read-only experiments |
| Optional/deferred | T4.5 universal inverse; broad T2.4 documents, baskets/categories, learned memory, distributed/async T7 | Concrete requirement or measured gap |
| Simplify/reorder | Full DTO queue, full T1.2a codec before model, elaborate deterministic capacity policy, standalone evaluation platform | Preserve complete unions/implemented contracts; consumer closures/capability gates |
| Historical control; defer migration | Broad T5.5 V1Adapter | Not needed for fixed-input model comparison; useful later for common-runtime attribution |

Full-contract gate and task IDs remain. Partial parents stay in progress. The milestone names
below are proposed capability checkpoints, not silent replacements for M0–M7. After approval,
revise D/task crosswalks and ADR-05 explicitly.

### Milestone 1 — Grounded intelligent offline decision

**Objective/new capability:** language and supported uncertainty change a defensible next action
under fixed legal/economic conditions.

**Deliverables/modules:** R1–R3 in evidence/context, economics/official, execution/validation;
consumed envelopes in core; adapters/model; intelligence/interpreter/fallback; bounded strategy
selector; orchestration/budgets ledger; minimal composition/trace attribution; reviewed labels/
small evaluator.

**Dependencies/order:** fixes and labels immediately → serial consumed contracts → fake gateway/
ledger → interpreter → selector → existing coordinator. Fixed generation is acceptable only
as the labelled temporary candidate universe.

**Acceptance/tests:** consumed DTO negatives, private-input/schema/span/condition/revision
controls, timeout/cancellation/late/refusal/malformed cases; affordable action flips with
unchanged economics; useful approval/condition questions; irrelevant controls; official
recomputation/validation. Genuine LLM capability requires approved held-out provider results.
Fake drafts earn plumbing status only.

**Exclusions:** arbitrary new offers, prose/claims, research simulation, persistence/sending.
**Risks:** hallucination, candidate-set bias, provider latency exceeding 8/4-second caps,
exact quote mistaken for meaning. **Effort:** 3–5 engineer-days including review/fixtures,
assuming an approved compatible provider; coding speed does not remove validation work.

### Milestone 2 — LLM-directed meaningful proposal generation

**Objective/new capability:** new conditional price/term packages from domains/history rather
than only prewritten-package selection.

**Deliverables/modules:** approved ProposeInput/task/draft and joint intent directives;
LLM proposal; economics/candidates/prices; small question catalog; batch-bound rendering/
validation coverage; coordinator capability/budget changes only.

**Dependencies/order:** revision → contracts/projection → legal option/tick generation →
interpret+propose bundle with mechanical priority/cost ranking → milestone-1 arm comparison.
Preserve two-call cap; produce at least one package absent from initial supply.

**Acceptance/tests:** unseen legal synthetic multi-issue cases, exact outgoing fields/ticks/
bounds/must-haves/official costs; beneficial/harmful conditional volume, price-specific versus
broad refusal, incomplete bounded search; no supplier-acceptance claim. Evidence can alter
strategy with disabled-estimate arithmetic unchanged. Impossible needs clarify/cannot-decide.

**Exclusions:** global optimum/inverse, calibrated acceptance/utility, new domains, live close.
**Risks:** unaffordable intentions, missed combinations, refusal mis-scope, dimensionality.
**Effort:** 3–6 engineer-days, one bounded capability before generalization.

### Milestone 3 — Evidence-grounded communication

**Objective/new capability:** credible conditional exchange or verified argument with disclosure.

**Deliverables/modules:** first T2.3 canonical claim/verifier and T5.1 claim subset;
question/exchange catalog and snippets; optional communication-draft handoff; render/validation.
Implement claim-limit/disclosure contracts only with their consumers.

**Dependencies/order:** one argument family → source verification/disclosure → canonical
sentences/templates → final-body checks → optional wording experiment under unchanged call
ceiling. No unbudgeted writer call.

**Acceptance/tests:** wrong figures/IDs, stale/irrelevant/conflicting sources, usage duplicates,
rival-recipient exceptions, private snippets, invented commitments, changed package values and
injection blocked; template fallback; blind clarity/credibility review and reactive ablation.

**Exclusions:** arbitrary attachments, unrestricted prose, broad documents, causal persuasion
guarantee. **Risks:** verified but unhelpful claims, confidential paraphrase, connective prose
adding commitments. **Effort:** 2–4 days for catalog/claim family; 2–4 more if model wording merits it.

### Milestone 4 — Strategy experimentation

**Objective/new capability:** distinguish understanding, decision and outcome improvements.

**Deliverables/modules:** extend evaluator/manifests begun in milestone 1; vetted bundle
registry/config identities; optional bounded research batch registration; one feedback or
small MESO treatment; reuse experiments/Lab reporting.

**Dependencies/order:** labels/baselines → treatment → frozen comparison. Start with milestone
1 and proceed alongside 2/3. Reactive outcomes require the local harness in milestone 5.

**Acceptance/tests:** common economics/admission/clock/budget, equal-compute controls, retained
fallbacks/unresolved cases, held-out per-scope effects/uncertainty and fingerprints. Funded
original live samples require separate manifest/authorization.

**Exclusions:** automatic default/promotion, research portfolio, training, second dashboard.
**Risks:** simulator tactics, tuned labels, unequal candidate universes, dependent repeats.
**Effort:** 1–3 tooling days plus 1–3 per small treatment; provider/review time additional.

### Milestone 5 — Reliable multi-turn negotiation

**Objective/new capability:** adapt to consequences of sent actions, preserve through restart.

**Deliverables/modules:** first an offline reactive counterpart harness over immutable
acknowledged history/official costs; then state/feedback projector, SQLite artifacts/state/
outbox, closing evaluator/validator, allowed gateway, executor/recovery and serial lifecycle.
Reuse low-level readers/transports and trace identities, not mutable V1 decisions.

**Dependencies/order:** harness early alongside milestone 2 → acknowledged feedback/history
→ full used-scope validation/closing → atomic ownership/store → gateway/executor/recovery
→ fault/restart integration. Basic linkage is not learned causal attribution.

**Acceptance/tests:** conditions/refusals/answers alter later choices; unsent drafts do not
become concessions; restart preserves committed history; crashes before/after commit/send/ack,
uncertain open/reply loss/stale accept/missing proof retain original IDs/bytes or recovery.
All close triggers use fresh standing sheets/same official comparison. Faults need not yield deals.

**Exclusions:** concurrent RFQ/wave optimization, cross-session learning, causal attribution.
**Risks:** insufficient remote proof, source order and late results.
**Effort:** 1–2 days for reactive harness; 5–9 additional for durable serial execution/recovery
and meaningful fault coverage.

### Milestone 6 — Scope-specific competition readiness

**Objective/new capability:** authorized rehearsed release with outcome evidence and truthful recovery.

**Deliverables/modules:** exact file/release-byte preparation, supported standards/documents,
freshness/applicability; provider/protocol budget report; intended CLI/Lab config/checkpoint
parity; endpoint/key/session/quota rules; preflight/recovery/rollback; funded original outcome
study. Resolve relevant inherited failures/tooling separately.

**Dependencies/order:** intended intelligence scope and milestone-5 reliability → real source/
provider contracts → exact launch rehearsal → allowed original baseline/candidate trials →
scope-specific promotion before freeze.

**Acceptance/tests:** no spectator access, invalid sends/conflicting operation, fabricated
terminal/round/deadline; actual-basis economic parity, repeatable preparation, measured
fallback/timing/budgets, complete original denominators/holdout. RFQ scope needs all-thread
closing/scheduling checks; otherwise explicitly exclude it.

**Exclusions:** broad promotion from P10, hidden optimum claims, post-freeze changes, API caps
as quota authorization. **Risks:** organizer timing/unit unknowns, simulator transfer, queues/
wave limits. **Effort:** 2–5 engineering/rehearsal days after prerequisites; external approval/
experiment timing cannot be promised.

These estimates are not measured completion times or an event-day promise. Stop/change course
when a treatment does not improve decisions/outcomes; do not finish the inventory for its own sake.

### Reliability cutline and reuse

Offline experiments need filtered strict inputs, grounding checks, official economics, R1–R3,
shared call/token/time limits, cancellation/late-result rejection, validated deterministic
fallback and snapshot consistency. Synthetic evidence stays labelled; self-consistent hashes
are not independent source authentication.

Before real file/provider consumption, verify bytes/config and applicable freshness/disclosure.
Before sending, add ownership/CAS, atomic claim reservation when used, authoritative parsing,
retry/recovery, fresh standing-sheet closing, terminal proof and launch/quota/lease gates.
A database/transport is not needed to test an interpreter on safe recorded input.

Reuse pinned arithmetic/readers, canonical claim/disclosure patterns, adviser ID/quote concepts,
Lab records and low-level HTTP/idempotency patterns. Do not reuse inverse helper, daemon-thread
waiter, mutable proposal memory, base-only cost join or entire V1 runner as trusted V2 services.
Retain historical first-message replay.

## 8. Immediate next implementation assignments

These are proposed tasks after review approval. Preserve all current work; no incidental V1
fixes, dependencies/defaults/CLI changes, golden mutation, hosted calls, quota, commit or push.
Read AGENTS and exact contracts/assertions first. Malformed/missing required symbols fail
ordinarily; no weakened assertions or broad xfails. Add manifest entries/completion notes
for introduced focused tests, retaining partial parent status.

### Assignment 1 — Close three reproduced consumer gaps

**Goal:** enforce actual case-evidence and outgoing admission contracts before intelligent offers.

**Inputs:** scoped suite, saved source-47 trace, R1–R3 reproductions; C's ContextBuilder,
CaseContract, CostPolicy and complete outgoing-sheet requirements.

**Exact files/scope:** evidence/context.py; economics/official.py; execution/validation.py;
focused regression tests and relevant manifest/catalog entries. No shared DTO field, Protocol,
wording, priority rule or official formula change.

**Implementation order:**

1. Resolve prepared records plus case.case_facts through the existing resolver. Preserve
   original records/citations, duplicate/collision behavior, scope-after-priority and no
   resurrection of a lower layer. Do not silently retag layers or promote statements.
2. Independently require each outgoing offer sheet's bindings to equal the exact negotiable
   field set, with no fixed/extra fields. Keep partial incoming economic resolution.
3. Enforce declared tick and protocol cent precision. Settle grid origin from existing
   convention; unsupported conventions fail explicitly, without invented offsets or snapping.

**Interfaces:** unchanged ContextBuilder.build_context, EconomicEvaluator.evaluate_package,
ActionValidator.validate_action.

**Acceptance:** case-only EUR 47 beats prepared EUR 43; out-of-scope/deleted/conflicting winners
fail without reviving base; identical repeats deterministic. Deleting each required outgoing
field is rejected even if standards fill its economic value. EUR 49.01 fails a EUR 0.05
grid; EUR 49.00/49.05 pass; ordinary EUR 0.01 behavior unchanged. Direct tests plus coordinator
tests refresh valid hashes so identity failure cannot mask the defect. Scoped V2, official
parity, Ruff, historical replay and whitespace checks remain passing; report unfinished xfails.

**Non-goals:** intelligence, full preparation, claims/closing/runtime, generic model refactor,
V1 repair. **Effort:** half to one engineer-day including tests/review.

### Assignment 2 — Grounded interpreter and shared model budget

**Goal:** replace echo with a genuine SupplierInterpreter; verify provider plumbing separately
from language quality.

**Inputs/components:** assignment-1 boundary; existing AssessmentDraft/SupplierAssessment,
ConversationView/refs; ModelGateway/SupplierInterpreter/Clock; coordinator and interpreter/
model-budget tests; independent labels prepared alongside coding.

**Exact scope/files:** core/models.py for these 15 exports only: InterpretInput, SelectionOption,
SelectInput, SimulateInput, ModelInput, ModelRequest, ModelBudget, ModelUsage, ModelSuccess,
ModelRefused, ModelInvalid, ModelTimeout, ModelCapacityUnavailable, ModelTransportFailure,
ModelResult. Retain closed complete unions. Add adapters/model.py, intelligence/interpreter.py
and fallback.py, small orchestration/budgets ledger and minimum coordinator/composition integration;
focused tests/labels/evaluator. Shared core edits remain serial.

**Interfaces:** GroundedInterpreter with injected model/clock implements interpret; gateway
complete returns ModelResult under ModelBudget. Explicit provider/protocol/prompt/schema/model
configuration and injected async transport, fake first.

**Constraints:** no ambient credentials/import calls, daemon thread or retries. Filter records,
conversation and prior assessment recursively; exclude private/unapproved snippets. One ledger
per decision retains total calls/tokens/time and reserves; new request objects cannot reset it.
Unknown usage is recorded unknown, not free, and admission uses conservative configured bounds.

Decode raw success in the interpreter; enforce exact fields/spans/scope/IDs/revisions/conditions.
Construct content-derived assessment identity and parent linkage. Preserve ambiguity, reported
authority, contradiction and unknowns; no invented discount/approval/canonical promotion.
Check explicit semantic relationships where supported; evaluate arbitrary entailment against
independent labels. Conservative fallback retains observations, cause and call attribution.

**Acceptance/tests:** all existing DTO negatives/roundtrips for the 15 symbols under explicit
requirements. Fake transport exercises all result variants, malformed JSON, cancellation,
late/hung/queued results, call/model mismatch, private projections, exhausted call/token/time
and reserved fallback. Separate exact-quote-but-wrong-meaning from offset failures. Assessment,
permitted raw response/hash, usage and fallback appear in trace. Default tests never call
providers. Require owned modules and applicable interpreter/budget selectors; implement needed
test bindings without forcing the full recorded codec or bypassing absent bindings.

**Quality experiment:** separately approved endpoint/model and absolute allowance; frozen
held-out precision/recall, critical errors, abstention and latency. Without results report
“fake-transport verified; model quality unmeasured.”

**Non-goals:** strategic heuristics/new prices, propose task, persistence/execution, learned
opponent model, performance/promotion claims. **Effort:** 1.5–3 engineer-days plus label/provider review.

### Assignment 3 — Language-conditioned selector and minimal comparison

**Goal:** supplier-language changes produce defensible affordable offer/question changes through
actual economics/validation.

**Inputs/components:** interpreter/gateway/ledger; EvaluationBatch/SelectInput/SelectionOption;
MinimumCostTestSelector control; fixed snapshot/clock/case/budget; real oracle/evaluator/templates.

**Exact scope/files:** SelectorResponse if absent; bounded selector in owned strategy selection
module; small registered question/generator/render/validator additions for reviewed question IDs;
explicit test composition, paired fixtures and small evaluator/report tool under existing
experiments tooling. No full factory/recorded codec/store prerequisite.

**Interface/constraints:** existing ActionSelectionPolicy.select_action returns the approved
candidate/evaluation ID for exact batch. Existing select task, shared second-call budget.
Code-authored exact package summaries, relative economics and scoped attempts/refusals; no
absolute private limits. Validate membership and exact supporting_quote, then map to a real
source span and commercial assessment. Keep SelectorResponse's existing two commercial fields;
do not add hidden new output fields. Unknown/invalid/refused/late output gets a recorded certified
fallback inside remaining budget.

No term edits/invented IDs, factual claims, arbitrary body, close or expected labels. Each new
approval/condition question ID has a fixed template and independent admission coverage.
Questions are a separate action category, not zero-cost offers.

**Acceptance:** same legal candidate universe/costs under changed delivery versus commitment
preference, broad versus conditional refusal and approval ambiguity. At least one defensible
affordable choice differs from nominal minimum; at least one chooses clarification over an
offer. Greetings preserve package/economics; ceilings/fixed fields dominate. Unsupported
pressure never becomes canonical cost. Forged IDs/edited packages/private/ungrounded output
fail. Run coordinator, actual arithmetic and validator; export every rejection/fallback.

Compare minimum-cost, direct LLM selection and structured-interpreter+selector on frozen
held-out inputs with common total budgets. Report semantics, admissibility and decision quality
separately. Real adaptation requires approved unseen-input model results; recorded drafts prove
routing. Reactive multi-turn outcomes remain necessary for negotiation-performance claims.

**Non-goals:** unrestricted generation, research simulation, database/runtime, writer, live
sending/default activation. **Effort:** 1–2 engineer-days plus approved evaluation. Labels/tools
can start alongside assignment 2; shared contracts integrate in dependency order.

### Gate discipline and review reproduction

Each assignment retains the current scoped full command from addendum L/M and adds its exact
owned module prefixes, test selectors and symbol requirements. Model-envelope gates require
the 15 names explicitly, not all D12/D13. Selector adds SelectorResponse. No existing unfinished
claim/close/store/research test is relabelled complete.

For example, once assignment 2 is implemented, require adapters.model, intelligence.interpreter
and orchestration.budgets alongside the existing modules; run all remaining-DTO contracts with
the explicit model symbol set. New direct/integration tests complement existing interpretation
and model-budget assertions. Do not introduce a module with partial methods that hides broken
imports behind “unimplemented.” Final full-contract requirement remains unchanged.

The review's actual commands/artifacts include:

~~~bash
# Current implemented-scope requirements are the complete L/M addendum recipe.
.venv/bin/ruff check src/negotiator/v2 tests/v2
.venv/bin/python tests/v2/replay_v1_baseline.py
PYTHONPATH="$PWD/src:$PWD" .venv/bin/python /tmp/v2_review_boundary_probes.py
# Three baseline runs use exported source, pinned ARENA_DATA and local socket access.
.venv/bin/python /tmp/v2_review_regressions.py
~~~

Current V2 output: /tmp/v2-review-v2-tests.txt. Three-baseline comparison:
/tmp/v2-review-regression-comparison.json. The scripts install/fetch nothing; regression
tests need localhost permission. They do not modify source or consume inference/Arena quota.
Raw reports remain temporary artifacts, while this review retains results and scope.

## 9. Open decisions and final recommendation

These need user approval; this review does not execute them:

| Decision | Recommended choice and rationale |
|---|---|
| Delivery horizon | Offline intelligence/continuing-development path unless all live gates fit before today's declared freeze; avoid promising multi-day work for current final |
| First strategic treatment | Bring grounded selection alongside interpretation forward; deterministic minimum remains control/fallback. Explicitly revise ADR-05 priority |
| Proposal/intent revision | Small versioned propose purpose, joint directives/search/priority in milestone 2; review exact fields/consumers before changing C |
| External inference | Choose approved endpoint/protocol/model, allowed private-data projection, absolute spend/call/token ceiling and corpus; credentials/API caps imply no allowance |
| More calls/model writer | Two calls/templates initially; raise cap or fuse tasks only with measured quality/latency benefit and retained reserves |
| Multiple robust scenarios | Explicit nominal designation and admitted ranges/scope before enabling; retain current unsupported result until settled |
| Grounded free wording | Catalog/canonical clauses first; later draft handoff and commitment vocabulary need explicit scope |
| Live/competition activation | Separate authorization/original performance manifest; identify supported cases, claims/documents and scheduling |

Ordinary choices—bounded helper layout, immutable supplied history, case joins, exact fields/
ticks, manifests and retaining arithmetic—do not need another design committee.

**The very next implementation step should be Assignment 1: close the three reproduced
consumer gaps in the existing slice.** This small, reviewable prerequisite prevents wrong
evidence and invalid sheets from contaminating the model experiment. Begin labels and the
assignment-2 contract handoff alongside it where dependencies allow, then implement the
grounded interpreter and selector immediately. That is the highest-value next intelligence
investment: test whether the architecture turns language and evidence into better commercial
choices before spending more time on structural completeness.
