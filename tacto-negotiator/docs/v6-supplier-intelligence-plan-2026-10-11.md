# V6 supplier assessment and action selection

Date: 11 October 2026. Status: **P0–P5 local opt-in implementation; P6 provider probe failed the inference gate; Arena comparison and promotion withheld**.

Branch: `codex/v6-supplier-intelligence-plan`.
Base: `43ea2052de86b1c0077567b4c73e785e260deda2`, policy `configs/score-push-v6.json`.
Worktree: `/tmp/harvey-v6-supplier-intelligence-plan`.

## 1. Objective and decision

Improve adaptation to unfamiliar supplier constraints while preserving V6's economics,
execution controls, and demonstrated behavior when the new layer abstains or is disabled.
Success means evidence changes the next action usefully, without unsupported concessions,
missed deadlines, or loss of a valid agreement. More model calls or more persuasive prose
are not success criteria.

Keep V6 as the negotiator. Add one bounded supplier-assessment and action-selection layer.
The model interprets evidence and recommends a code-defined action; code generates prices,
evaluates complete packages, checks authority, and executes. The existing coordinator owns
both acceptance and walk-away. No second orchestrator or wholesale V2 merge.

Deliver in stages: reliable inference, source-linked assessment, supported package selection,
targeted questions, then a separately evaluated final-counter policy. Preserve ordinary
V6 closing until the final-counter stage passes its own gates.

The original planning branch contained documentation only. The subsequent P0/P1
implementation is recorded in [its implementation record](v6-p0-p1-implementation-2026-10-11.md).
The initial implementation included no provider calls or Arena sessions. A subsequent
single P10 practice run is recorded in [the experiment log](../experiments/LOG.md).
No promotion or change to the final launch configuration followed.
The subsequent local implementation of P2–P5 and the P6 gate audit are recorded in
[the implementation and gate record](v6-p2-p6-implementation-2026-10-11.md).
Any future implementation uses explicit opt-in configuration. A proposed test budget below
is a design input, not an allowance to consume quota.
The subsequent opt-in [strategy LLM layer](v6-strategy-llm-layer-2026-10-11.md)
adds a packaged negotiation skill and a smaller review contract for prepared
nonclosing moves. It has local checks only; no provider or Arena result is claimed.
The later [supplier brief architecture](v6-supplier-brief-architecture-2026-10-11.md)
adds versioned source-linked briefs from the permanent data package to that
reviewer and the final-offer reviewer. Its provider-only compilation and local
checks are recorded separately from live negotiation results.

## 2. Evidence informing the design

| Observation | Implication |
|---|---|
| V6 changes the P02 posterior parameter from 0.15 to 0.10; other policy settings remain V5's. | Preserve the configured baseline and isolate intelligence effects from economic retuning. |
| The later release record at `423a55e` reports ten cases run on clean `43ea205`: mean 0.78619355, all must-haves met, zero Arena timeouts. | V6 is a strong practice control, not evidence of hidden-case generalization. |
| Legacy capacity advice already generates the P10 EUR27.62/56-day package. Its saved successful trace used `gpt-6.1-sol`. | The useful trade does not require a new optimizer; context, selection, model settings, and latency matter. |
| Our combined-adviser trial selected an unsupported price-only increase; its repaired rerun on `b789414` timed out after 8.003 seconds using `gpt-6-sol`. Both closed at score 0.5546564482. | Prevent unsupported concessions and prove inference usability before another commercial experiment. The model comparison was not matched. |
| P10's tested 36-month extension tied the 24-month result; some commitment-heavy openings received immediate finals. | Longer commitments and stronger wording are hypotheses, not universal supplier value. |
| The legacy final-counter calculation can have infinite loss without an executable alternative, and the adviser skips final offers. | Better interpretation alone will not change final-counter behavior; that policy needs separate design and evaluation. |
| The review reproduced inconsistent briefing multipliers/units passing the new volume plan's upper-bound check. | Validate factual units before giving those commitments to an adviser or renderer. |

References:

- [Release implementation and evidence](../experiments/RELEASE-v5.md), especially sections 8–9.
- [V6 confirmation recorded after the base commit](https://github.com/ece-akdeniz/harve-y/blob/423a55e/tacto-negotiator/experiments/RELEASE-v5.md#10-ten-case-practice-confirmation-of-v6-at-main-43ea205-2026-10-11-06200624-cest).
- [P02/P10 experiments](../experiments/V5.md) and [saved P10 trace](../experiments/traces/v6-p10-s1/trace.jsonl).
- [Previous adviser design](https://github.com/ece-akdeniz/harve-y/blob/7f94f5e/tacto-negotiator/docs/v5-intelligence-architecture-2026-10-11.md).
- [Previous repaired-adviser trial](https://github.com/ece-akdeniz/harve-y/blob/7f94f5e/tacto-negotiator/docs/v5-intelligence-p10-repair-trial-2026-10-11.md).
- Local review: 110 focused tests passed; 20 decisions matched the original V5 base with
  provider output stubbed. These are regression checks, not live generalization evidence.

Measurement caution: `agent_metrics.model.calls` counts ModelAssist, not necessarily the
legacy PackageAdvisor. Zero in that field cannot establish that no inference occurred.
Instrument both paths before using call counts or latency to compare arms.

## 3. Architecture and authority

```text
Owned history + standing sheets + bounded supplier-scoped public evidence
                              |
             Snapshot/version + deterministic factual ledger
                              |
           V6 draft + complete code-costed action candidates
                              |
       One bounded call: assessment delta + recommended action ID
                              |
       Citation/condition checks + code admission + fresh economics
                              |
       Selected draft + deterministic message + verified claims
                              |
         Existing coordinator, journal and dispatch/recovery
                              |
             Acknowledged response updates owned history
```

V6 still supplies a complete fallback. Prepare it once on isolated draft state; do not call
the live agent twice to obtain alternative proposals. An unselected draft cannot update
`prev`, concessions, final counters, or claim reservations. Record intended actions separately
from acknowledged history. The transport's existing journal owns uncertain sends and recovery.

The adviser receives no client, credentials, executable tools, private reservation values,
post-run score fields, or spectator data. Supplier text and documents are untrusted evidence.
Standing structured sheets determine executable terms; conflicting prose remains an explicit
ambiguity for strategy. A cheaper alternative sheet is not directly acceptable if the API
permits accepting only the first standing sheet.

## 4. Supplier assessment contract

Keep a compact assessment per session and supplier, keyed to a specific history version.
Code owns facts about messages, sheets, sent packages, and observed concessions. The model
proposes semantic interpretations; validation admits or rejects each item independently.

| Field | Required semantics |
|---|---|
| Identity | Session, supplier, source history hash, latest supplier message ID/index, schema version. |
| Source | Message/document ID, supplier/part scope, date where available, exact span, source role. |
| Observation | Quoted terms, stated constraint, preference, conditional trade, refusal, question, concession, or contradiction. |
| Interpretation | Explicit statement or inference; do not treat inferred preferences as promises. |
| Terms affected | Registered fields and their relationship to a complete candidate package. |
| Conditions | Antecedent and consequence with source spans; unknown/ambiguous conditions remain unresolved. |
| Lifecycle | Active, contradicted, superseded, resolved, or expired; retain the reason and prior source. |
| Uncertainty | Missing information, conflicts, and unsupported predictions. No invented numeric acceptance probability. |
| Action history | Requested tactic, intended package, acknowledged package, outstanding question, observed reply. |

Example: “additional volume only against a binding 12-month commitment” supports that
conditional requirement. It does not establish a discount for 36 months. A quoted lead time
is a stated term, not automatically a refusal of faster delivery. A historical capacity note
can support a hypothesis, but a newer explicit rejection overrides it.

Exact citations establish provenance, not semantic correctness. Include human-reviewed
examples and adversarial condition-preservation tests. When interpretation cannot be admitted,
retain the source as unresolved and use the baseline or an eligible clarification.

Persist admitted assessment events alongside source identity and schema/prompt versions.
Reconstruct factual state from owned history after restart; discard incompatible or stale
derived state. No automatic cross-session learning or live policy updates in this release.

## 5. Action selection

Code materializes a bounded menu from actual options, existing trade functions, supplier
sheets, and assessment evidence. Case type selects supported capabilities, not assumptions
about willingness to trade. There must be no production branches keyed to P10 or supplier IDs.

| Action | Admission and execution |
|---|---|
| `keep` | Execute the prepared V6 move after fresh validation. |
| `offer_package` | Complete legal terms, source-linked reason, relevant changed fields, cost evaluation, and configured concession bounds. |
| `ask_question` | Registered question ID, actionable missing information, a code-defined decision it could change, and enough time for the answer and another move. |
| `request_close_review` | Coordinator evaluates current standing offers through the shared evaluator; the model cannot accept or walk directly. |
| `request_final_counter_review` | Available only in the separate final-counter experiment; code evaluates a concrete counter and its downside. |

First action-changing slice: `keep` and `offer_package`, serial single-supplier capacity
and renewal cases with supported complete-package economics. Start with capacity for regression
continuity, but require renewal examples before claiming transfer. Unsupported cases, cost-target
paths, and async suppliers retain V6. Log capability skips; do not count them as successful
adaptation on held-out families.

Use a cost-neutral envelope initially. A concession experiment may later permit bounded
increases, with both per-turn and cumulative limits anchored to an acknowledged reference.
Those strategic limits are not universal procurement constraints. A pure price concession
must not be generated merely because the supplier quoted a higher price. Extra commitment
is not automatically compensation for supplier cost.

Keep rejected packages in history. Explicit refusal and superseding evidence affect eligibility;
a repeated package requires a new, cited reason. Log missing useful candidates rather than
letting the model invent terms or recursively call tools to expand the menu.

Questions are a later stage: at most one unresolved question per supplier and a bounded
per-session question count. Exclude information already supplied. Require two plausible
answers to lead to different feasible actions; this is an information-value screen, not
a calibrated expected-value estimate. Prefer a question accompanying a valid package when
the endpoint supports it. Verify message-only semantics before enabling a pure question.

Render with registered templates and approved evidence. Numerical claims, quantities,
commitments, and the attached terms must agree. Model rationale never becomes supplier-facing
text. Evaluate any wording change separately from package choice.

## 6. Latency and failure behavior

Measure the exact request before choosing a different model or increasing a timeout. Reconstruct
the failed P10 request from its frozen source, history, notes, candidate menu and configuration;
label reconstruction explicitly because the original complete provider request was not saved.
Future traces retain a redacted request digest, schema/model/settings and component sizes.

Proposed first provider-only probe: three development payloads × two adviser contracts × five
repeats = **30 calls, zero Arena sessions**, subject to a separate explicit spend/call allowance.
Use the same model/settings for both contracts; label cold/warm requests, sequential versus
concurrent execution, and transport setup. This is exploratory latency evidence, not a reliable
tail estimate. Any model change is its own factor and requires a frozen comparison.

Measure total wall time, context construction, provider request time, response parsing,
validation, token usage when reported, schema validity, and action admission. When the
transport cannot distinguish queuing from inference time, record that gap instead of guessing.
Record late completion and unknown usage separately from zero usage.

Initial limits inherit the prior candidate's bounds: one call per eligible supplier update,
at most eight attempts and 24 reserved inference seconds per session, eight seconds per call,
at most 16 complete packages, and a 20-second dispatch/closing reserve. These are starting
limits to validate, not measured guarantees. Admission uses the earliest absolute thread/wave
deadline; queueing, marshalling and validation consume the same allowance. Never reset the
deadline between stages. Retain unresolved conditions when compacting history; if it cannot
fit safely, abstain rather than silently remove refusals.

Suppress duplicate ModelAssist/PackageAdvisor calls for the same update in enabled mode.
Persist budget reservations and source-version decisions; restart does not refund an unknown
attempt or authorize a duplicate request. Bound global concurrency before async integration.

Timeout, malformed output, unavailable provider, unsupported action, or invalid citations
return to the exact prepared V6 move if it is still valid. A stale snapshot requires a fresh
decision inside the original deadline. Expiry, cancellation, or an unresolved write returns
control to the existing coordinator/recovery path; it must not become an unchecked fallback
send. Quarantine late results from live state. Abstain from further advice after timeout until
the configured recovery policy permits it; initial behavior disables it for the session.

## 7. Final-counter experiment

Implement only after package selection and questions have independent evidence. Assessment
may observe a final offer, but must not delay urgent closing or invalidate an existing offer.

Compare retaining the standing offer with at most one legal counter. Show the proposed gain,
possible loss of the agreement, continuation time, and any executable outside alternative.
If a common utility scale and outcomes are available, derive the break-even walk probability
`p* = gain / (gain + loss)` and show sensitivity. Separate acceptance, continued bargaining,
and walk-away outcomes; a binary approximation must be labelled as such.

Without an executable alternative, model no-deal explicitly on the appropriate objective.
Do not reuse an infinite “no alternative” sentinel as a calibrated downside, replace it with
an arbitrary finite number, or consume hidden `c_best`/post-run evaluation data. If comparable
utility or calibrated risk bounds are unavailable, retain the offer and log why the risky
counter was not admitted. Model confidence is not a supplier walk probability.

Code owns the counter limit, allowable loss/risk envelope, must-haves, fresh offer validity,
remaining time and final accept/walk action. No instruction to always push past the first
counteroffer. Test this policy separately from the opening-package improvement.

## 8. Implementation sequence and completion gates

| Stage | Work and likely seams | Completion gate |
|---|---|---|
| P0 — Freeze control and measure | Pin V6, data/release, model, config and runner; audit legacy/model telemetry; reconstruct latency request; enumerate exposed suppliers/cases. | Disabled mode preserves available saved decisions; request/usage accounting is unambiguous; no hosted call without an allowance. |
| P1 — Reuse guarded execution | Adapt `advice.py`, draft isolation and pre-dispatch checks from `b789414`; merge into V6's actual mutation/evidence paths. | Exact keep/failure parity; no discarded state or claims; stale, cancelled, expired and uncertain operations cannot submit a new move. |
| P2 — Assessment in shadow | Add typed source-linked deltas, lifecycle, persistence and compact reconstruction; improve unit/quantity validation. | Human-reviewed conditions/refusals survive round-trip and restart; conflicts stay visible; shadow output cannot change a sent move. |
| P3 — Select useful packages | Generate complete exchanges from actual case options; use one assessment/selection response; deterministic rendering; capacity then renewal. | Paired evidence changes alter the selected action appropriately; paraphrases preserve economics; no unsupported concessions; live results only after latency gate. |
| P4 — Targeted questions | Add registered questions and decision-branch/time admission to the same call. | Asked once, answer changes an eligible choice, irrelevant answers do not loop, and insufficient time preserves closing. |
| P5 — Final review and wider routing | Add separate final-counter policy; then explicitly integrate cost-target and async/multi-supplier paths. | No private evaluation inputs; risk/deadline checks and supplier isolation pass; enable each capability only after its own ablation. |
| P6 — Frozen holdout evaluation | Run approved matched arms; inspect all outcomes and failure evidence; make a rollback/promotion decision. | Generalization, safety and commercial gates below are met. Otherwise retain V6 as default. |

Each stage is a reviewable change with an experiment-log entry and a source/config identity.
Do not turn stage order into an unbounded multi-agent or multi-call implementation.

Existing seams: `agent.py` (`decide`, `propose`, `_nonprice`, `_enrich_evidence`, `_final_counter`),
`package_advisor.py`, `model_assist.py`, `replies.py`, `policy.py`, `play.py`, `runner.py`,
`claims.py`, `fixed_volume.py`, the shared evaluator and Lab workflow. Introduce a small
assessment/advice module only where these boundaries need one.

Selective V2 references at `75241b5`: `v2/core/supplier_grounding.py`,
`v2/core/question_actions.py`, `v2/intelligence/interpreter.py`,
`v2/orchestration/budgets.py`, and `v2/execution/validation.py`. Read their contracts before
porting. Preserve V6's public API, existing economics and rendering; do not copy V2's package
fallback or orchestration wholesale. Audit V6's new `_fixed_volume_plans` cache and type
normalization when adapting the earlier draft-state mechanism.

## 9. Generalization evaluation

Freeze an exposure manifest before tuning: all cases, suppliers, transcripts, dossiers and
outcomes already inspected by developers or model prompts are development evidence. P10 and
the known leaderboard/practice cohort are not a clean holdout. If prior exposure is uncertain,
label it exposed. Do not claim that official hidden cases have been tested.

Reserve fresh supplier-disjoint examples within supported families and reserve entire case
families for the later capability-expansion stage. Where no genuinely unexposed hosted cases
remain, use sealed, independently specified simulator scenarios and report that limitation.
Only inspect held-out results after freezing source/config/prompts. If results are used to
revise the candidate, retire that cohort into development and reserve another one.

Required local scenario matrix:

| Variation | Expected invariant or adaptation |
|---|---|
| Identical quotation, different supported constraint | Different relevant trade where a feasible one exists. |
| Conditional promise versus unconditional statement | Preserve the condition and require the complete exchange. |
| Explicit rejection of longer commitment | Do not repeat that trade merely because it is cost-neutral. |
| Historical capacity note contradicted by a current reply | Current scoped evidence supersedes the historical inference. |
| Prose contradicts the standing sheet | Binding terms remain authoritative; ambiguity is visible. |
| Names/IDs renamed; harmless wording reordered | Same strategy/economics; no identity-based shortcuts. |
| Per-100/per-1,000 pricing, wrong or missing units | Correctly normalized facts or abstention; never an invented commitment. |
| Immediate final, no alternative, expired offer | Coordinator closes or abstains according to explicit policy and validity. |
| Slow/malformed provider, cancellation, restart, concurrent supplier update | Bounded work, valid fallback, no stale or duplicate send. |
| Missing dossier, missing type, unsupported case path | Explicit uncertainty/capability skip; complete V6 behavior remains available. |

Matched arms:

- A: V6 as shipped, including its legacy package adviser where enabled.
- B: V6 plus assessment in shadow, to measure overhead and interpretation without action changes.
- C: Assessment plus package selection; keep comparable wording to isolate package effects.
- D: C plus targeted questions, in a separate comparison.
- E: C or D plus final-counter policy, in a separate comparison.

Pin provider/model/settings, public data, source, economic configuration and runner across
arms except for the declared factor. Baseline and candidate runs require separate agent
state and sessions. Randomize/counterbalance order and record model/arena variability.
Replay validates decision parity; fixed historical supplier responses cannot establish the
counterfactual outcome of a changed action. Simulator success tests designed behaviors,
not hosted persuasion or the hidden distribution.

Report all cells, including no-deals, provider fallbacks and incomplete sessions. Metrics:
normalized score and full cost; agreement/must-have outcomes; unsupported-concession and
rejected-trade repetition counts; condition/contradiction errors; question usefulness;
candidate-menu coverage; interpretation admitted; actions changed; latency distribution,
deadline violations, API timeouts, token usage and unknown-usage attempts. Separate model
interpretation failure, missing candidate, admission rejection, policy rejection and provider
timeout so failures lead to a specific next change.

## 10. Gates and proposed budgets

Engineering gate: zero illegal/stale/duplicate actions, private-data leaks, or unsupported
commitments in the safety suite; exact disabled/keep/failure parity on supported paths;
successful restart reconstruction. Missing data must abstain predictably.

Inference gate: on a frozen validation batch under representative concurrency, target at
least 95% schema-valid responses within the admitted window and p95 total adviser work
at or below six seconds when eight seconds are available. These are proposed operational
thresholds, not current measurements. Report sample size, cold requests and uncertainty;
the 30-call exploratory probe alone is insufficient to certify tail reliability. Never
trade away the dispatch reserve to meet an admission-rate target.

Behavior gate: demonstrate correct adaptation on paired constraints in both initial supported
families, abstention on contradictory/insufficient evidence, and no critical unsupported
concession in the frozen evaluation set. Report denominators and uncertainty, not only examples.

Commercial gate: honor the applicable Lab gates (complete original outcomes, valid must-haves,
known nonincreasing Arena timeouts, mean gain at least 0.01, no case regression over 0.02,
and wins in at least two-thirds of repeat blocks). Also inspect family-level regressions,
provider timeouts and hidden-evidence contamination. Small samples are screening evidence;
meeting aggregate gates alone does not prove generalization.

Budget proposal after local/latency gates: one two-arm screening comparison on two development
cases × three repeats = **12 Arena sessions**. A later three-case supplier-disjoint comparison
with the same repeat count requires **18 additional sessions**, if clean eligible cases exist.
Question/final-counter arms and deeper repetitions need separate budgets; do not silently
expand the first comparison. At reservation time verify live quota and agree the reserve.
Use tracked Lab commands, immutable source/config and explicit session ceilings. Partial
attempts charge the reservation; reconcile owned sessions rather than starting replacements.

## 11. Rollout and next concrete deliverable

V6 remains the default through shadow and screening stages. Promotion requires the frozen
evidence and explicit rollout authority; the Lab recommendation and the application/final
launch configuration are separate controls. A rollback disables the new mode and returns
to the pinned V6 policy without losing the execution journal or acknowledged history.

The first implementation deliverable is P0 + P1: a V6-based opt-in integration with complete
advice telemetry, a reproducible provider-only latency probe, and verified draft/fallback
semantics. Do not spend another P10 session simply to discover that the adviser still times out.

Before execution, finalize the exposure manifest, provider allowance, economic concession
policy (initially cost-neutral), supported routing, and separately authorized experiment
budget. These are implementation/evaluation decisions; no answer is needed to finish this plan.
