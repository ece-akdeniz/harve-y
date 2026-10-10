# E — Architectural, behavioral and negotiation evaluation plan

**Status:** proposed evaluation; no hosted or inference allowance supplied. [Plan](../21-negotiation-v2-plan-2026-10-10.md) · [Contracts](C-interfaces.md) · [Tasks](D-roadmap.md).

## 1. Separate the claims being tested

There are four different deliverables: correct domain/transport behavior; semantically grounded interpretation; appropriate commercial adaptation; and improved negotiation outcomes. Passing one does not establish the others. In particular, fixtures using replayed model outputs do not prove a live model interprets correctly; replaying a historical supplier reply does not establish how the supplier would answer a different offer.

| Evaluation level | Inputs | Output claim it can support | Cannot establish |
|---|---|---|---|
| Contract and fault tests | Local typed fixtures/fake transports/clocks/events | Legal economics, validation, ownership, recovery and bounded fallback | Hosted persuasion or real provider quality |
| Interpreter semantic benchmark | Independently labelled text/evidence; fake outputs for controls, authorized model runs for quality | Grounding, refusal/condition recognition, uncertainty and latency | Agreement or score improvement |
| Behavioral counterfactual tests | Same legal case with controlled supplier messages and source changes | Decisions respond appropriately to information | Real supplier's counterfactual reply |
| Local multi-turn scenarios/simulator | Scripted suppliers, actual schemas and official arithmetic | Loop integration, state, valid adaptation and termination | General hosted negotiation performance |
| Frozen hosted study | Specifically authorized original sessions and fixed configuration | Outcome/latency/spend comparison within sampled cases | Generalization outside sample or causal effects without design |

Existing [tests](../../tests), saved practice cases, [experiment log](../../experiments/LOG.md), and Lab schemas/gates are retained. Extend them with independent V2 tests; do not repurpose failing legacy expectations into weaker assertions. Source changes get their own hypothesis/completion record.

## 2. Capacity vertical-slice fixtures

Use the actual `case:P10` contract from `tests/fixtures/practice_cases.json`: allowed lead 35/42/56, commitment 12/24/36, volume 16,379/19,890/23,400; must-have volume >=22,230; payment 30 and DAP fixed. Only 23,400 is a compliant offered volume. Preserve the actual price basis, two-year demand and supplier-health inputs. An observed supplier's 54-day quote is source data, not an allowed outgoing option.

Build one original recorded reply reference plus controlled variants. Label modified text as synthetic and retain source hashes/edits. Three independent paraphrases per A–F family give an initial **18-fixture** suite; expand with multilingual/role/conditional variants after the first gate. These are engineering fixtures, not 18 independent hosted samples. Hold out at least one paraphrase per family before tuning prompts/rules, and keep expected economic calculations independently computed through the kit.

| Scenario | Assessment requirement | Decision requirement | Negative/control assertions |
|---|---|---|---|
| A — Delivery constraint | Identify current near-term limitation with exact span and source role; do not invent a discount | Generate/evaluate allowed 56-day flexibility and associated late cost; choose exchange only if admitted by cost/scenario policy, else clarify/keep | Never send 54 days or unauthorized volume; compute €33,600 late component at 56 vs 42 days under unchanged P10 late rate |
| B — Commitment preference | Record longer-term request; possible price benefit is hypothetical unless explicitly quoted | Evaluate 24/36-month options, coverage/complete cost and stated condition; do not promise extra annual quantity | Payment is fixed; supplier request is not legal permission to add other terms; horizon cap does not erase stated duration |
| C — Explicit refusal | Link refusal to last package/dimension/condition; distinguish broad rejection from rejection at one price | Exclude unsupported repeated exchange and prefer another legal candidate or clarification; require new evidence to reopen | Repeat after restart behaves the same; retry of the same uncertain operation is not a new strategic attempt |
| D — Contradictory evidence | Preserve supporting and opposing cost-driver information with scope/date; reject unsupported “entirely due to material” as established fact | Change assessment/clarification or intent relevance appropriately; select verified outward claims only if disclosable | No automatic 12% anchor change from a partial index; a wage rise must not vanish because unfavorable to buyer |
| E — Malicious/irrelevant instructions | Extract commercial request separately from attempted rule override/data request; keep observations source-linked | Same valid commercial exchange as clean control where applicable, or safe clarification | No private values, instruction execution, invented terms, external requests or spectator endpoint calls |
| F — Model failure | Explicit fallback status for timeout/refusal/schema/grounding failure | Valid deterministic approved action within budget, or deterministic close/recovery outcome when no action is valid | No fallback to unvalidated legacy output; late model completion cannot overwrite selected/sent action |

Include a missing-source/basis variant and a genuinely infeasible must-have variant. Expected results are admissible sets/relationships, not brittle exact model wording. For example, A need not always select 56 days; a relationship-cost scenario or refusal may make clarification better. The test must prove the trade was considered with correct cost and exclusion reason.

## 3. Independent correctness contracts

| Area | Required local cases | Acceptance evidence |
|---|---|---|
| Domain | Serialization, unknown keys, mutable nested input, bool-as-price/int, null versus missing fields, invalid dates/index shapes, decimal/nonfinite values | Strict rejection or explicit unsupported input; stable roundtrip/version/hash |
| Evidence | Case/release/base ID override; appended supplier-specific row; same-priority collision; deleted required field; current/old/future date; missing supplier/part; multiple parts | Shared claim/estimate source IDs/values; blocking conflicts visible; adverse evidence retained |
| Preparation | Cold artifact creation, warm loading, changed source/parser/case/message/doc, explicit missing base/release, corrupt artifact | Warm/cold decision equivalence; correct invalidation; source prep consumed before open, not merely generated |
| Price basis | Price units 1/100/1000; EUR versus other currency; scope/basket mismatch; current and should-cost basis joins | No blind whole-case normalization; unsupported joins block dependent claims/economics; source and rendered units explicit |
| Economics | Cost components against official fixture totals; complete-term precedence; partial quote standard; supplier estimate/scenarios; missing estimate; uncovered demand | Official parity at final cents; correct standard reference changes supplier cash value/relationship penalty |
| Price candidates | Rounded plateaus, known valid price, unreachable ceiling, two relationship roots, reference branch, tick rounding, zero/negative, bounded scan exhaustion | Every retained output finite/positive/legal and certified; no false global optimum/no-root claim; scope/unknown search recorded |
| Options/must-haves | All actual P10 combinations, illegal 54-day lead, impossible volume/other constraints, missing negotiable field, extra fixed field | No unchecked best-terms fallback; explicit rejected intent/no candidate |
| Closing | Wrong supplier/session/offer, non-standing alternative, stale ID, agreed bad deal, all-thread ranking, missing alternate versus fallback/no-deal | Identical deterministic legality/cost authority on all triggers; no undefined infinity arithmetic |
| Claims/rendering | Tampered figure/sentence/IDs, stale scope, internal/rival disclosure, >3 arguments or >20 refs, mixed body and action | Recompute canonical assertions; no unsupported assertion left after ID removal; correct final payload limits |
| Plugin boundaries | Dummy alternate proposal/selector/interpreter, bounded research evaluation | No changes in evidence/economics/validator/gateway implementation needed; stable contract fixtures |

Cost/validation tests invoke these services directly without the strategy engine. Use an independently assembled official calculation as oracle, not the implementation's intermediate function as its own expected value. Strategy tests use fixed typed economic results only where isolating policy logic; end-to-end behavior tests use the actual official adapter.

## 4. Strategic behavior and semantics

Label each observation with source span, request/refusal/condition category, stated role/approval boundary and observed versus inferred status. Assess hypotheses for support, contradiction, scope, temporal applicability and absence of invented numeric willingness. Keep annotations and evaluation fixtures versioned and private where needed. A second reviewer resolves ambiguous cases; “unknown” is a correct label when appropriate.

Metrics: observation precision/recall by category, valid citation rate, unsupported assertion rate, condition/role attribution accuracy, contradiction retention, explicit abstention/fallback rate, and live-model schema-validity rate. Confidence labels are not probabilities; calibration is a future study. Do not demand a numerical confidence score that has not been calibrated.

Behavioral checks are metamorphic:

- Change only a delivery statement to a commitment statement: change relevant intent/candidate reasoning while preserving case/economic values.
- Add a refusal: stop repeating that exchange without new cited justification; preserve a price-specific conditional refusal's limited scope.
- Add valid new supplier condition after refusal: a reopened exchange cites the new evidence rather than forgetting history.
- Add adverse canonical driver data: context and assessment retain it; outbound disclosure can remain restricted; strategy may ask a more specific question.
- Remove provenance or alter price basis: dependent claim/candidate loses approval; fallback remains legal.
- Remove/timeout model: deterministic choice still obeys state and validator; measured semantic capability is degraded rather than silently labelled successful.
- Restart at identical acknowledged state: generic attempts/refusals/evidence/questions and deterministic decision are equivalent. Model variance is measured separately, not hidden by assertion of exact prose equality.

Initial engineering gate: zero transmitted invalid actions, zero unsupported critical numeric/approval assertions in labelled cases, all significant interpretations attributable, and correct A–F contract behavior. Semantic aggregate targets (such as recall) must be pre-registered after an initial independent label review; do not choose thresholds after observing a candidate. An exact-quote pass alone cannot pass the semantic gate.

## 5. Runtime fault and restart matrix

Use fake clock, event barriers, fake Arena/model transports and crash injection. Do not rely on tiny real sleeps for interleavings. Assert bounded operational completion and recovery state, not a forced agreement for every fault.

| Failure point | Required observable result |
|---|---|
| Before atomic decision commit | No pending operation/claim consumption; recompute from current state |
| After commit before dispatch | Durable exact operation exists; proof of no dispatch permits invalidation/revalidation; restart never duplicates logical ID |
| After server accepts POST before local reply | Same ID/bytes survive; outcome reconciled or stays uncertain; no conflicting next action |
| Repeated reply loss/read failure | Bounded recovery-required return with pending operation owned; original run does not hang indefinitely |
| Open reply lost | Do not create a fresh session; recover same open intent or remain unresolved |
| Close rejected repeatedly while session open | Not `ended`, no fabricated walk-away/result; owned session remains resumable |
| Close success missing required terminal/result proof | Fetch owned authoritative state; uncertain until proof, not success by HTTP status alone |
| Unexpected proposal/evaluator/parser failure | Collect exception/tasks; valid admitted fallback only if evaluator remains sound; otherwise reconcile and recover |
| Model queue/time budget exhausted | No retries outside budget; deterministic fallback has reserve; late result discarded |
| State changes during interpretation/limiter wait | CAS or freshness check rejects stale intent; no POST of obsolete package/close |
| Cached idempotent reply after long delay | Original timing retained; no fresh invented thread deadline |
| 409/5xx/quota conflict | Classified and reconciled; attempted message not automatically added to accepted history |
| Lost round evidence | Conservative documented remaining budget or recovery-required; never reset from guessed history |
| Restart after refusal/question/claim | Same strategic observations and exact claim scope usage; unknown claim results not treated verified |
| Duplicate/out-of-order messages | Deduplicated source keys; source-order/conflict evidence retained; no repeated round increment |
| Snapshot/schema mismatch or corrupt legacy log | Refuse unsafe projection; preserve diagnostic input; no automatic terminal import |
| Two local launchers same key | Common lease blocks second supported execution owner |
| Export/trace upload fails | Negotiation state remains durable; diagnostic export failure is separate; no fresh attempt to replace outcome |

For later async admission also exercise normal watchdog completion with blocked worker, worker exception, in-flight close ambiguity, two-thread version changes, no lock over await, capped wave admission, limiter starvation, queued late cases, and ten-session capacity. Those tests do not block the first offline/serial intelligence demonstration, but do block async/final claims.

## 6. V1/V2 comparison and ablations

Name each treatment explicitly:

| Arm | Purpose |
|---|---|
| `v1-legacy` | Frozen existing PackageAgent + original config/runtime, historical baseline behavior |
| `v1-adapted` | Same strategy through new economic/validator/execution boundaries; isolate correctness/runtime changes |
| `v2-baseline` | New pipeline using pure deterministic schedule and fallback interpretation |
| `v2-interpreted` | Grounded interpreter with deterministic capacity proposer/selector |
| `v2-evidence` | Same interpretation/policy with added relevant canonical and adverse evidence |
| `v2-stateful` | Full persistent refusal/attempt/feedback handling; initial full candidate |
| `v2-selected` | Optional LLM selection from identical approved candidates |
| `v2-research-X` | One named research variation using same foundations |

Run a few chosen ablations that answer a specific question; do not spend budget on the full Cartesian product. Removing state/evidence for an ablation never removes hard validation or ownership. For offline fixed inputs, keep legal candidate universe/economic policies constant when isolating selector impact. For hosted studies, state/evidence/interpretation may change offered trajectories; record that and do not pretend replies are identical.

A benchmark manifest freezes source/kit/lock, data/release/prep hashes, case list, scenario/repeat order, agent/strategy/config/template/claim/interpreter/prompt/model versions, effort/sampling, model/server cache metadata, runner/key-owner policy, expected attempts, quota/spend ceiling, metrics and promotion criteria. Official Cbest/score and public benchmark artifacts enter human evaluation only, never runtime strategy inputs.

## 7. Hosted performance plan and promotion requirements

Only after local gates and separate authorization: run a small endpoint/protocol/clock contract study if needed, then a bounded frozen capacity comparison. A successful old connectivity probe is insufficient to validate strict interpreter/selector protocol. Record allowance for both inference calls and Arena sessions; an API cap is not permission.

Compare original completed outcomes against a frozen baseline, interleave/counterbalance arms where permitted, retain every failure and unresolved attempt, and collect per-session traces. Record official score, agreement rate, complete cost/components, must-have status, scenario-estimated supplier margin/relationship cost (label estimated), rounds/timeouts, inference latency/calls/tokens/actual reported spend, invalid action rate, operational failure rate and fallback frequency.

Report complete planned mean only if the entire planned original sample completed. Partial scored outcomes are `observed_mean`, with denominator and failure counts. Recovered outcomes remain separately identified and do not rewrite original operational success. Identical/cache-hit supplier trajectories are grouped as potentially dependent samples, with effective sample size/independence uncertainty stated. Do not combine historical best scores across configurations or treat within-case paraphrases as independent hosted evidence.

The existing D01/D02 suite has three repeats per arm, at least one score-point mean gain, at most two-point case regression, wins in at least two-thirds of repeat blocks, valid must-haves and known nonincreasing timeouts. Those are **implemented gates for that suite**, not evidence that D01/D02 establishes capacity quality. Retain them for that workflow. A capacity suite needs a reviewed manifest/case scope/budget; creating a new family must not evade prior quota limits.

Minimum evidence before making V2 the default for a scope:

1. All deterministic contract/fault/A–F gates pass; no validator bypass or unresolved-operation conflict; required suite/static checks complete with declared baseline issues resolved for the selected release.
2. Live-provider labelled interpreter results and protocol/latency/fallback evidence exist for the exact prompt/model/config when a live interpreter is part of the release.
3. Full frozen baseline/candidate outcome manifest with at least three original repeat blocks, known timing/invalid-action results, and no mixed config means. Repeats must have defensible independence; cached identical repeats alone are insufficient.
4. Pre-registered case-regression, mean-gain, timeout/runtime-failure and inference-cost limits are met. Add uncertainty estimates and sample limitations; deterministic gates alone are not a statistical significance claim.
5. Held-out category/supplier or independently varied negotiation evidence supports the intended scope. P10-only results can justify an opt-in P10/capacity pilot, not a broad default for all categories. If no additional independent capacity cases exist, record the generalization gap and retain pilot status.
6. Trace review confirms changes were commercially grounded, actual payload/cost is correct, and sustainability/basis uncertainty is disclosed internally. A good score cannot override a violated hard constraint.
7. Store a cited finding, experiment-log entry, approved source/config selection and tested rollback/recovery plan. Recommendation, code merge, deployment and default activation are separate operations.

No performance verdict is supplied by this planning task. If funded evidence is inconclusive, keep V2 opt-in and continue local research rather than treating architectural elegance as a measured win.

## 8. Lab integration and evaluation artifacts

Reuse Run/Attempt/campaign/fingerprint/gate records. Add versioned V2 trace attachments and a turn view showing evidence -> assessment -> intents -> rejected/approved candidates -> cost/scenarios -> selection -> validated payload -> submitted/acknowledged outcome -> feedback. Show the actual final payload rather than the initial pre-adviser decision. Filter/join by run/attempt/session/operation, not just case.

Required artifacts: contract fixture pack; annotated semantic corpus and split manifest; local correctness/fault report; behavior/ablation report; frozen launch-parity/config report; provider report when funded; original hosted session/attempt manifest when funded; promotion/rejection note and rollback record. Each artifact has source/config/schema hashes. JSONL remains convenient export; authoritative state/outcomes come from committed store records.

UI/report changes use existing Python and JavaScript tests and browser verification where appropriate. Do not create a second dashboard to get a V2 trace view. A report should explicitly show unsupported/model-fallback/recovery-required paths; missing metrics remain unknown, not zero.

## 8. Executable preparation now available

[tests/v2](../../tests/v2) supplies the contract, integration and acceptance groups. The [catalog](test-catalog.md) maps fixtures, expected invariants and failure conditions to task owners; its [expanded manifest](../../tests/fixtures/v2/test-manifest.json) lists every collected parameter case. Source assertions are executable specifications, not smoke-test descriptions. Tests remain independent of future provider wording and use actual P10 options, complete official costs, synthetic supplier responses and fake gateway outcomes.

M1 now owns actual typed full-loop wiring, effective config, versioned fixtures, deterministic replay, model-output variability accounting and basic persistent DecisionRecords. M5 adds full state/operation transactions and recovery, using the same identities/store. Engineering reproducibility is no longer delayed to M6. The initial reply fixtures have eight controlled variants; the earlier eighteen-paraphrase quality benchmark remains T3.1 expansion, not a falsely claimed completed dataset.

Only missing V2 modules produce explicit UNIMPLEMENTED expected failures. Use required-prefix gates per task and require all at the final implemented gate. Current active tests validate fixture integrity, independent arithmetic, fake routing, architectural scanner and expected-failure discipline; they do not establish that missing production modules work. Local socket access is blocked for V2 tests. No budget/dependency/provider call is required.

A §7 freezes historical main and separately classifies the four inherited current-branch failures. Never report those as V2 regressions or reuse the current branch as historical main. New tests cannot weaken old assertions. Additional unimplemented tests for source preflight, crash barriers, queue/round timing, endpoint canonicalization, feedback, launch parity and later extension/solver behavior have explicit catalog IDs and owners; implement those bindings before their corresponding feature. Hosted persuasion, live semantic quality and async load retain their separate gates.
