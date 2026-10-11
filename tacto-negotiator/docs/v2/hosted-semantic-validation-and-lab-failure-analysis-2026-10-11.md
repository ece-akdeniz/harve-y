# Hosted semantic validation preparation and Lab failure analysis

11 October 2026, Europe/Zurich. **Local analysis and executable experiment preparation completed;
real inference awaits explicit authorization.** No Arena negotiation, new simulator session,
remote Lab read/write, publication, promotion, validator relaxation, frozen-label modification,
new deterministic negotiation strategy or Assignment 4 implementation occurred. V1 failures
remain outside this V2 assignment, as requested.

Reviewed repository/package guidance, `LAB_PLAYBOOK.md`, documentation index/checklist,
V2 interfaces/task specifications, strategic alignment review, hosted readiness/results and
the latest stabilization report. Retained existing Python ports, economic oracle, context
assembly, consumer grounding, budgets, rendering, validation and Lab persistence interfaces.
Added experiment tools, a separate semantic review, focused tests and documentation. One narrow
provider-schema change omits non-validating title/description annotations to fit the existing
reservation; every field, enum, type, constraint, DTO identity and independent validator is preserved.

## 1. Why the three negotiations ended without agreement

The authoritative runs are those named in `/tmp/v2-lab-stabilization-final/report.json`:

| Arm | Run ID | Rounds | Valid actions | Deal | Timeouts |
|---|---|---:|---:|---|---:|
| Minimum cost | c089eba7-6109-4e2f-8460-f7369be76e7f | 6 | 6 | No | 0 |
| Direct scripted selection | 8fa9ad14-e2b6-4307-8d17-f0b5545603f7 | 6 | 6 | No | 0 |
| Interpretation-assisted scripted selection | 12bf923e-ddee-4fe3-868e-628df57bbff3 | 6 | 6 | No | 0 |

Each original `runs/<run-id>/run.json` retains the supplier thread under
`attempts[0].threads["sup:70410"].messages`. The read-only analyzer verifies all 18 original
trace digests/certificates and finds **identical transcripts** across the three arms.
It selects only the report's run IDs, not other exploratory directories in the same root.

The initial supplier message is “Simulated supplier. Our quote is attached.” Its price is
EUR 32.88. Each buyer response says “Please consider the proposed terms in the attached term
sheet.” It repeats exactly EUR 27.60, 23,400/year, 36 months and 56-day delivery. Six counteroffers
produce this progression; indexes refer to the original saved message array:

| Buyer message index | Preceding supplier price/status | Next acceptance threshold | Buyer price | Supplier response |
|---:|---|---:|---:|---|
| 1 | 32.88 / open | 32.22 | 27.60 | Counteroffer 32.22, message 2 |
| 3 | 32.22 / open | 31.56 | 27.60 | Counteroffer 31.56, message 4 |
| 5 | 31.56 / open | 30.90 | 27.60 | Counteroffer 30.90, message 6 |
| 7 | 30.90 / open | 30.24 | 27.60 | Counteroffer 30.24, message 8 |
| 9 | 30.24 / open | 29.59 | 27.60 | Final offer 29.59, message 10 |
| 11 | 29.59 / final_offer | 29.59 | 27.60 | “We end here.” / walked_away, message 12 |

These thresholds are reproduced from the pinned installed `arena_kit.sim` constants and
`Sim._answer`: each sheet lowers the price by 2% of opening, bounded below by 90% of opening;
prices round to two decimals. The branch checks a qualifying buyer sheet **before** checking
whether the preceding status is final. At round six a below-threshold sheet triggers walk-away.
The original result records `ended=true`, `deal=false`, score 0, `c_deal=null`, and the final
thread status `walked_away`. The saved result does not expose a session end reason; the
transcript/code establish the supplier's walk-away branch without inventing a missing field.

### Fixed strategy limitation: an agreement is unreachable in this universe

The three supplied package prices are **28.34, 28.34 and 27.60**. Even the largest is below
EUR 29.59. There is no offer in this universe that the script can accept on any round.
Changing IDs or selecting the delivery-preference package cannot fix that. The mock interpreter
reports ambiguity; mock selection explicitly chooses the cost minimum. Their admission success
provides no evidence of bargaining adaptation or live LLM skill. Clarification is available,
but cannot itself produce a new price in this fixed generator.

All arms use the same package with forecast official cost EUR 1,333,891.20. This is an
independently evaluated **proposal cost**, not realized agreement cost. The no-deal outcome
must not be replaced by that number. The simulator's hidden script is examined here for
failure analysis; it is not supplied as a negotiation-model feature or a new heuristic.

### Integration limitations: current observations are incomplete for strategy research

The Lab preserves complete supplier term sheets, attachment text and original statuses, but
`LocalV2LabAgent` builds a body-only conversation with empty `observed_sheets`, `attachments`
and claim results. It reconstructs its authoritative server context from the reviewed offline
P10 dataset and updates identity/history/counts, not the changing live supplier offers. Thus
an LLM sees repetitive prose without the price progression. It also receives supplier-only
history: acknowledged buyer actions are not recorded as V2 operations. The selector's existing
scoped-history projection has no acknowledged action sequence to expose. Assessment parent
linkage is retained in runtime traces; the current interpretation-purpose projection deliberately
omits the previous assessment itself.

The bridge retains the input DTO's actionable open-thread representation at final offer.
The actual `final_offer` is available in original Lab records, but not faithfully represented
in this V2 decision input. It has no validated close/accept/walk authority. These are verified
scope limitations, not transport faults: all 18 certified byte payloads reached Sim, observations
advanced through six state versions, and terminal outcomes were retrieved without timeouts.

These gaps would obstruct an adaptive future strategy even with a richer candidate universe.
They are **not needed to explain the particular no-deal outcomes**: every current package
already fails the script's price threshold. Nor is accepting a standing quote a safe quick fix:
the initial attached quote defaults to 16,379/year, below P10's 22,230/year must-have. Full terms
and independent closing checks must precede any acceptance.

The simulator ignores persuasion and nonprice utility in its agreement branch. It is suitable
for contract/round/terminal-state tests, not measuring supplier understanding, relationship
utility or capacity negotiation effectiveness. A deal against its script would not establish
real supplier intelligence.

Reproduce the analysis without opening any session:

```bash
.venv/bin/python -m experiments.v2.analyze_lab_failures \
  --source /tmp/v2-lab-stabilization-final \
  --out /tmp/v2-lab-failure-analysis-2026-10-11-new.json
```

Captured analysis: `/tmp/v2-lab-failure-analysis-2026-10-11.json`. Original artifacts are unchanged.

## 2. Exact runnable 19-call hosted experiment

`experiments/v2/run_semantic_validation.py` reuses the existing HTTP transport, spend guard,
interpreter, ledger, P10 composition, semantic evaluator and final validator. Its default mode
uses `httpx.MockTransport`; it does not load `.env`, require credentials or send network requests.
Hosted mode requires an exact matching authorization file and the existing explicitly configured
OpenAI credentials. It never creates an Arena client or a Lab publisher.

| Order | Purpose | Maximum calls | Consumer review |
|---|---|---:|---|
| 1 | Strict selection connectivity, one permitted minimum ID, empty quote | 1 | Exact ID, empty quote, DTO validation; stop on failure |
| 2 | Fourteen development supplier texts, interpretation only | 14 | Admission, citations, meaning, negation, conditional scope, authority and uncertainty |
| 3 | Two original P10 supplier messages, interpretation then selection | 4 | Same-input deterministic baseline, unchanged official universe, selected terms/citation/delta and independent final validation |
| Total | Offline model evaluation; zero negotiations | **19** | No retries or automatic continuation/relaunch |

The 14 development texts cover preference, multiple preferences, refusal, conditional refusal,
combined/nested conditions, contradiction, approval, ambiguity, cost claim, greeting, injection,
supplier volume question and conditional commitment. Their labels and scripted control drafts
are never model inputs. The eight held-out selection examples remain unchanged and receive
**zero calls**. Their canonical digest is verified before and after execution.

Configuration is frozen in `authorization-template.json`: direct OpenAI Chat Completions,
**gpt-4.1-mini-2025-04-14**, v2 prompt hashes, strict derived provider-schema hashes, DTO schema
identities, source hashes, development/P10/review hashes, no retries, maximum 2,048 output tokens,
16,384 reserved total tokens per call, 32,768 per decision, eight-second interpretation/four-second
selection limits. Input-byte accounting includes both messages, the strict schema and 256 framing
reserve. Preparation exports actual local HTTP request bodies and per-request reservations;
selection inputs in the preview are mock-conditioned, while real admitted assessments may differ.
Inspection initially found only 426 output tokens available on the longest interpretation
request. Omitting non-validating provider-schema annotations saves 1,908 input bytes on that
schema, restoring the full 2,048 output allowance for every prepared request without raising
budgets or changing validation constraints. Larger future model-conditioned projections can
still reduce output allowance or fail capacity admission; this is not silently overridden.

Proposed separate absolute allowance: **USD 1.00**, at most **19 attempted calls** and
**311,296 reserved tokens**. A failed/cancelled/unknown-usage attempt remains charged. At current
standard uncached input/output rates of USD 0.40/1.60 per million, the deliberately conservative
reservation charges every reserved token at the higher output rate: **USD 0.4980736** maximum
within the stated convention. Usage-derived cost remains an estimate, not an invoice.
The exact byte/framing convention must be acknowledged in the approval; a provider violation
remains an error and cannot be fixed by increasing bounds during the run. GPT-4.1 mini's listed
snapshot, pricing and structured-output support were checked against [official OpenAI documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Strict schema support is distinct from meaning and grounding, as described in the
[structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).

Prepare a fresh review bundle from the project directory:

```bash
.venv/bin/python -m experiments.v2.run_semantic_validation \
  --out /tmp/v2-semantic-validation-review-UNIQUE
```

**Only after explicit user authorization**, copy its template to a separate authorization JSON
and set only `authorized` and `token_accounting_confirmed` to true, keeping every scope/hash/limit
identical. Then run once into a new directory:

```bash
.venv/bin/python -m experiments.v2.run_semantic_validation \
  --out /tmp/v2-semantic-validation-hosted-UNIQUE \
  --authorization /tmp/v2-semantic-validation-approved.json
```

Existing `.env` settings must specify direct OpenAI and this model family; keys are read locally,
never printed or placed in authorization, preview, report or prompts. Hosted requests pin the
snapshot rather than relying on an alias. A changed source/prompt/schema/dataset/review rejects
approval before transport construction. A fresh output directory is mandatory and an existing
one is refused; the guard has no resume/retry mechanism. A new directory does not itself grant
another allowance: any second hosted attempt requires new explicit authorization. The exhausted
previous 77-call authorization is incompatible and cannot fund this run.

Preparation has completed locally. Its `local-preflight/report.json` is explicitly mock evidence:
19 guarded mock calls; 14/14 admitted development controls and provisional semantic matches;
both P10 interpretations/selections admitted and both final actions valid. The volume question
selects the minimum; the delivery preference selects 42 days at +EUR 1,262.88. These are authored
responses, **not improved hosted reliability**. Failed developmental prepare directories are
retained separately; no hosted transport was created while resolving local rehearsal issues.

## 3. Reliability assessment and preregistered review

The prior hosted evidence remains the only live quality measurement: **74 successful provider
responses, 1/25 admitted interpretations and 26/49 admitted selections**. Benchmark model arms
always ended at minimum; P10 had one grounded selection departure despite interpretation
fallback. Historic rejected raw outputs were not retained, so exact causes remain unattributable.
No current real-inference reliability result exists yet.

`experiments/v2/semantic-expectations-review.json` supplies a second text-based semantic
assessment separate from authored draft outputs. It explicitly declares that the agent reviewer
has seen development labels. It is **not independent human or blind adjudication**. It finds
reasonable commercial expectations, with these representation limits:

- A preference should not become a hard condition; fixed P10 payment terms cannot be changed
  just because a supplier prefers payment in 30 days.
- Conditional refusal must retain antecedent/consequence, including conjunction and nested scope.
  Full-span citation plus an observation link is necessary but insufficient to prove understanding.
- Contradictory requirements must not be resolved by silently discarding one. Approval uncertainty
  is not acceptance. Supplier cost assertions are not verified economics.
- Ambiguity, greetings and injection admit multiple safe representations. Exact observation-kind
  sets and unknown strings are provisional automated representation scores, not semantic gold labels.
- A volume question does not promise a quantity. A conditional 24-month commitment must not become
  unconditional agreement or approval of 36 months.

Freeze expectations and thresholds **before** hosted outputs. Report automatic provisional scores
unchanged, then adjudicate every assessment and both selections against the separate commercial
expectations. Count wrong negation, lost material antecedents, invented authority/commitment,
unsupported economics, forged scope and disclosure as critical errors. Null review fields mean
unreviewed, never zero errors. Safe abstention is safer than fabricated understanding but still
counts as unavailable understanding for the usability denominator.

Proposed limited Assignment 4 research-pilot gate: at least 12/14 development interpretations
both admitted and independently semantically acceptable; zero unresolved critical errors;
refusal/conditional/contradiction/approval/injection cases specifically reviewed without critical
errors; both P10 selections admitted and independently defensible, with valid final actions and
unchanged economics. If the gate misses, identify the specific failing meaning/field and scope a
small correction before a separately authorized rerun. Do not weaken validators, relabel the
held-out set, or tune prompts during this experiment. Passing is a small development screen,
not a calibrated error rate or broad reliability claim.

The 19-call allowance deliberately gives only two substantive selection decisions plus a probe.
It cannot establish broad selection accuracy, performance on the eight held-out examples,
benefit of interpretation over direct selection, or multi-round adaptation. Compare the two P10
messages directly with the previous P10 run; report development counts separately from previous
benchmark counts. The combined prompt/schema update is not a randomized component ablation.

Outputs separate provider status/usage/latency/reservations, safe rejection diagnostics,
consumer admission/fallback, provisional semantic scores, pending independent review,
selected package/economics/citations, and final validation. Partial failures retain reports;
connectivity failure stops remaining calls. Rejected raw model text remains withheld.

## 4. Lab readiness and Assignment 4

| Research requirement | Evidence now | Remaining gap |
|---|---|---|
| Replaceable interpretation/selection | Injected gateway/config and typed policies exercised through recorded coordinator | Hosted understanding unmeasured after stabilization |
| Replaceable strategy proposal | Existing `StrategyProposalPolicy.propose_strategies` returns `IntentBatch`; coordinator injects policy | Default policy emits fixed keep/clarify; Lab factory has no general research-strategy configuration |
| Legal candidate generation | Existing `CandidateGenerator.generate_candidates`, official evaluation and independent certification | Supplied finite packages cannot express new prices/joint packages |
| Model-driven proposal contract | Existing gateway/DTO ownership is explicit | Model task enum is interpret/select/simulate; no propose projection/schema; single-dimension intents lack full joint-condition/search semantics |
| Multi-round meaningful inputs | Lab saves full threads; V2 increments versions/parents/counts | Live sheets/documents/status and acknowledged buyer operations omitted from bridge projections |
| Research/lookahead | Existing `CandidateResearch` port | Coordinator uses `NoAdditionalResearch`; no enabled bounded candidate-research implementation |
| Comparable scenarios/baselines | Existing Lab campaign/checkpoint/data/config/source machinery; same-input offline baseline comparison verified | Current dirty standalone local records are not immutable campaign arms; generic/multipart V2 case loading missing |
| Reactive outcomes | Official Sim retrieves genuine terminal result | Fixed supplier script is not an LLM-strategy efficacy benchmark |
| Real Arena safety | Economics and action validation preserved | Hosted observations, full closing checks/authority, durable feedback/ownership/idempotent execution/reconciliation remain unavailable |

**Conclusion:** the typed coordinator can host interchangeable policy implementations without
architectural replacement. Existing Lab infrastructure can manage comparisons. The particular
P10 demonstration is ready for integration controls, not unrestricted LLM strategy research or
real Arena deployment. Do not read the generic Lab `--agent` factory as proof that any V2 policy
can already be configured and run with complete observations. Full remote readiness is a later
gate and need not delay a bounded offline Assignment 4 pilot after the semantic gate.

Future comparisons should freeze identical source-independent case/data hashes, initial supplier
state, candidate-generation bounds, economics, budgets, inference configuration, terminal rules
and evaluation definitions. Use the existing checkpoint/campaign system with explicit arm
configuration and immutable manifests; group repeats into paired blocks. Reuse minimum-cost and
direct-selection controls. Comparing proposal strategies allows different generated candidates,
but the scenario, legal search envelope and deterministic evaluation must stay identical; do not
force identical generated actions and thereby prevent testing proposal intelligence. For an
interpretation/selection ablation, keep the exact candidate universe identical as in P10.
Keep held-out cases frozen, preregister outcome/admission/semantic criteria, and do not publish
or promote these exploratory dirty-workspace records automatically.

## 5. Recommended next implementation step

**First authorize and review this semantic experiment.** If the limited gate passes, scope one
bounded LLM proposal implementation behind the existing proposal/generator ports: a small typed
`propose` projection/output and DTO-owned admission for cited joint trade suggestions and bounded
price/term requests. Code must still materialize permitted complete packages, compute official
costs, select approved IDs, render fixed text and validate independently. No model-provided
cost, executable plan or acceptance authority. Treat evidence of supplier preferences/constraints
as hypotheses with source/condition/uncertainty, not a new deterministic bargaining library.

Before using that pilot in multi-round Lab efficacy comparisons, complete only the missing inputs
it needs: current sheet/default provenance, explicit terminal status and acknowledged action
history, through existing adapters/state interfaces. Choose an explicitly scoped scenario;
register the research-policy config through the existing agent factory seam. Evaluate the
strategy against frozen controls on text-conditioned offline decisions and then separately
budgeted reactive scenarios. Do not expand journaling/dashboard infrastructure or claim a
winning negotiation policy from admission rates or script-specific price matching.

Validation for this preparation is recorded after the final local gate. No hosted result is
claimed; the deliverable is this runnable, scope-pinned plan and the original-run failure analysis.

## Local validation and review artifacts

- Four focused authorization/schedule/failure-stop/single-use checks pass; combined with existing
  stabilization and Lab controls, **32 passed** before the annotation adjustment.
- All V2 integration tests before that adjustment: **191 passed, 4 expected xfailed**.
- Final provider/grounding/selection/stabilization and new preparation gate after the annotation
  adjustment: **141 passed**; captured in `/tmp/v2-semantic-validation-final-gate.txt`.
- Scoped Ruff and `git diff --check` pass. Catalog refreshed to **1,539** executable contracts.
  This is not a newly claimed full repository or all-milestone acceptance gate.
- Final reviewed preparation: `/tmp/v2-semantic-validation-reviewed-2026-10-11/`, containing
  `authorization-template.json`, `request-preview.json`, `request-reservations.json` and
  `local-preflight/{report,predictions,connectivity,review-pending}.json` plus both P10 model/baseline
  traces. No `hosted-started.json` exists. All 19 prepared requests retain 2,048 output tokens;
  conservative input-byte bounds range from 5,462 to 14,050 and fit the existing 16,384 limit.
- Final source fingerprint:
  `61465b339746c0509360af61d63f481903f7cae71af51f4d9f5a0362c3a1095e`.
  The template still exactly matches the current executable plan; frozen held-out digest is
  `ef9c9d1de0bec90c07ef7185aa12209bd917f4d8bd5325351df6af33316311fc`.
- Original local failure analysis verifies 18 decisions across all three saved runs and opens
  no new session. Independent human semantic adjudication and live inference remain outstanding.

## Subsequently authorized execution

The user separately authorized the exact prepared 19-call configuration. It executed once;
see the [hosted results](hosted-semantic-validation-results-2026-10-11.md). All 19 provider calls
succeeded, but only 1/14 development interpretations was admitted (the empty greeting), and
both P10 interpretations fell back. Both P10 selections reproduce the previous choices.
The usage-derived cost estimate is USD 0.0289556, with USD 0.4980736 conservatively reserved.
The semantic gate is not satisfied and human review remains pending. Assignment 4 remains
blocked on usable supplier understanding; no second inference run or strategy implementation
was performed. This historical preparation section is not authorization for another run.
