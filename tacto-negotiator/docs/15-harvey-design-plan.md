# harve/y: integrated design and delivery plan

Team: y/agent. Proposed on 10 October 2026; this document is a plan, not an implementation claim.
It incorporates the brainstorming notes, both negotiation experiment logs, the runtime review,
and Barış's newly published y/agent lab. No hosted runs are authorized by this document.

## Decision

Use Samet's current main as the negotiation/runtime base, integrate Barış's lab as the shared
experiment and feedback system, and port our response-aware evidence checks and regression
fixtures. Keep one deterministic decision owner per case. Add a bounded model for interpreting
replies and an offline feedback agent only after the numerical/runtime contracts are enforced.

The system has two paths:

1. Live: versioned data -> case context -> interpreted reply -> deterministic package search ->
   validated proposal -> case coordinator -> arena -> durable trace.
2. Learning: traces and authoritative outcomes -> deterministic audit -> feedback findings ->
   controlled comparison -> reviewed policy/lesson release -> next run's pinned context.

The lab and feedback model must not be dependencies for completing an active negotiation.

## Evidence that sets the priorities

- P04: 5.64 -> 86.04 in both development lines. Our original deal covered only 12 months of
  a two-year need, leaving EUR 94,000 uncovered purchasing cost plus EUR 4,700 fallback risk.
  Contract coverage is a first-class calculation, not a preference inferred from price alone.
- P08: our targeted candidate reached 52.71; Samet's package candidate reached 59.30 in repeated
  comparisons against 15.62. Keep the package exploration work, with its measured configuration.
- P11: ours reached 40.64; Samet's lower-chargeback refinement reached 70.99. A harsher clause
  is not automatically a better negotiated outcome: the supplier prices the package.
- P10: our 45.32 required operator-assisted recovery after an alternative-sheet acceptance
  returned 422. Preserve the original failure separately from the recovered outcome.
- P18: zero -> 40.62 in our single targeted retest after package/final-offer changes. This supports
  further testing of flexible clause handling, not a causal attribution to one feature.
- Broad P01 evidence underperformed its baseline, 70.62 vs 77.60, in one pair. Samet's P04
  evidence arm tied package-only; P02 claims and P05 faster-payment experiments were unchanged.
  Verify arguments, then test whether they help; more claims are not inherently better.
- Main's free D01/D02 restart rehearsal passed. Our additional local fault injection still found
  an open server session recorded as finished after persistent close rejections. Happy-path
  recovery does not establish all failure paths are safe.

These observations use different revisions/configurations. Do not pool their best scores into a
claimed combined-agent result. Samet's combined candidate remains unpromoted pending regression.

## 1. Ingest fresh data into a versioned evidence store

Extend main's `DataPackage`/`dossiers.py`/`claims.py`; do not build a second ingestion system.
Support both a completely new package and additive release data. The audited kit describes
Sunday news/letters as an overlay, while unseen cases can carry additional facts. Neither format
may assume previously known supplier IDs or practice-case prices.

For each ingestion, produce a manifest: schema version, base/release file hashes, source locations,
ingestion time, effective/as-of dates and validation results. A case context references this
manifest plus the hash of its case facts and current quote documents. Separate source precedence
by field: case contract defines allowed terms; current quote supplies defaults; case-specific
facts have local scope; releases supplement package evidence; learned hypotheses never override
current authoritative terms. Preserve conflicting versions and flag ambiguity rather than
silently overwriting facts. A duplicate ID is not proof that the newest file is correct.

Store evidence as typed records with ID, supplier/part scope, value and units where applicable,
document/message pointer, publication and effective dates, supersession/expiry, and one of:
verified fact, supplier statement, derived estimate, or hypothesis. Dates matter: an old quote is
historical evidence, not a live competing offer; a personnel change invalidates older authority
assumptions, not every fact about the company.

Build case-scoped dossiers on demand, including unseen suppliers with only case facts. Current
main primarily builds detailed master-data suppliers; it needs a minimal dossier fallback.
Retain contact-change notes: `SKIP_SUBJECTS` currently excludes "New contact person". Extract
named role, stated authority and changed responsibilities only when sourced. Treat bargaining
preferences as observations, not certain personality diagnoses.

Before opening a case, prepare relevant parts, supply importance, alternatives, performance,
contract history, news, liquidity/capacity signals and contact constraints. On each reply, update
current offers, objections and hypotheses incrementally. Freeze the data/model/policy versions
for comparability; explicit permitted updates create a new context version and trace event.

For the arena, news should first come from its supplied news, letters, notes and releases: the
companies are fictional and citable assertions are checked against supplied facts. General web
news must not be attached to a fictional supplier or substituted for frozen arena indices.
A later real-world deployment can add registry/company-news connectors with entity matching,
source quality and expiry checks; that is outside the final-critical implementation.

Acceptance: ingest renamed/unseen suppliers, missing optional tables, new case facts, stale news,
conflicting IDs and a replacement package. Retain usable facts when optional data is missing;
omit unsupported claims. Reproduce the exact context from its manifest without practice history.

## 2. Deterministic economics and contract search

Keep the official cost implementation as the arithmetic authority. Expose small pure interfaces:

- `resolve_terms(case, quote, proposed)` -> complete terms with source for every field.
- `evaluate(package, context, supplier_scenario)` -> feasibility, cost components, coverage,
  alternative comparison and assumptions.
- `enumerate_packages(context)` -> bounded feasible alternatives using the actual term options.
- `price_for_budget(package, cost_limit, context)` -> checked price or explicit infeasibility.
- `select_move(state, candidates, policy)` -> offer, question, hold or closing proposal.
- `validate_close(state)` -> best currently acceptable primary sheet across all live suppliers,
  or checked walk-away; used by normal, agreed, deadline and recovery paths alike.

Compare every package over the same buyer need and horizon, including price-unit conversion,
effective date, annual volume, covered/uncovered demand, freight, financing/payment, quality,
chargebacks, indexation and the official relationship terms. Avoid double-counting components.
Use the kit's rounding semantics and validate the rounded payload again before sending.

For 12/24/36-month choices, report coverage and residual purchases explicitly. Do not multiply
annual volume when extending tenor; do not value coverage beyond the scoring horizon unless the
contract explicitly requires it. Select from feasible packages, not a universal "longer is better"
rule. Existing P04 behavior becomes a regression fixture; its IDs/prices never become policy.

Generate packages at the proposed bid, not just at the supplier's quote. Retain a small diverse
frontier, typically up to three: best modeled buyer cost, a justified supplier-preference trade,
and a relationship/uncertainty alternative where relevant. Supplier preference is uncertain;
do not discard a potentially acceptable package solely because another has lower buyer cost.
Examples: shorter payment for a computed price reduction; longer coverage for a discount;
lower chargeback for a priced concession; an index clause with a computed compensating price.

Code computes all opening prices, concession limits and break-even prices. The existing 12%
anchor is a baseline heuristic, not an optimal price. Keep configurable bounded concessions
based on observed responses and comparable packages. Do not let a model supply a target price
or silently alter terms in prose. Give the writer approved term literals and claim sentences;
validate those literals against the outgoing sheets or use a deterministic template.

Keep buyer economics separate from supplier acceptance predictions. Estimates of financing,
cost and capacity need provenance and low/base/high scenarios. Do not turn a should-cost upper
bound into a known supplier margin floor. Relationship penalties can make cost non-monotonic
in price: use bisection only with verified monotonicity; otherwise evaluate a bounded grid and
relevant breakpoints, refine, then recheck. A solver must return infeasible rather than fabricate
a price when no package meets the target.

After a final offer, conservative acceptance remains the default when it is valid and beats
the alternative. A risky counter requires an explicit policy, valid fallback and evaluated
sensitivity; the assumed 0.25 withdrawal probability is not established for unseen suppliers.
Never accept an alternative sheet merely because it is cheaper: offer its exact terms back
when appropriate; accept only the server's eligible standing offer ID.

Acceptance: compare component calculations against the pinned kit and saved hosted outcomes;
exercise horizon/volume/date/unit boundaries, nonlinear relationship cases and infeasible prices.
Every outgoing sheet must pass options/must-have checks; every close must use fresh global state.

## 3. Reply interpretation and argument selection

Use one bounded interpreter, not a swarm of negotiating agents. It returns structured fields:
explicit objection, requested trade, cited constraint, apparent negotiable dimension, authority
statement, supporting message spans and uncertainty. Term sheets/status remain authoritative;
prose does not create a binding offer. Missing/late/invalid model output falls back to templates
and deterministic policy within the existing end-to-end time budget.

Combine Samet's broader claim bank with our response-aware vetoes. Eligibility requires verified
arithmetic, correct audience/part, current evidence, permission to disclose and no repeated use.
Rank eligible arguments by buyer benefit, relevance to the latest objection, direct support and
novelty. Separate "arithmetically correct", "supplier acknowledged", and "concession followed".

Examples: a hedging objection stops repeating input-index arguments; switch to verified quality
history or a costed payment trade if supported. Liquidity pressure motivates a payment package,
not an unsupported claim about insolvency. An index-clause requirement triggers a priced clause
comparison rather than perpetual rejection. Track these as hypotheses with evidence spans.

## 4. Extend y/agent lab with objective feedback

Barış's branch already supplies run records, session history import, conversations, comparisons,
immutable checkpoints, paired campaigns, evidence references, findings, budgets and recommendation
history. Reuse those records and APIs. The host stores results; workers execute on teammates'
machines. Local persistence and asynchronous upload keep a lab outage out of the negotiation path.

Add a post-run feedback stage with two layers:

1. Deterministic audit recomputes action legality, primary-sheet eligibility, must-haves, modeled
   costs, unexplained package changes, citation checks, source freshness, known timeouts, unresolved
   moves, completeness and operator assistance. At each decision, compare with actual eligible
   standing offers available then. Label this "missed available offer" cost, not regret against
   an unknown optimum. Preserve unavailable/truncated evidence as unknown.
2. A feedback model summarizes that audit and cited messages into keep/change/test findings.
   Each must state the observation, interpretation, affected decision, supporting and conflicting
   evidence, confidence basis, proposed change and next experiment. A reviewer rechecks citations
   and calculated numbers; unsupported conclusions remain hypotheses.

For P10, feedback must say both "recovered deal at 45.32" and "original acceptance failed; assisted
recovery". For P04 it should identify uncovered demand, not merely praise the higher later score.
For P11 it may propose testing lower chargeback; it cannot infer that this always improves results.
Unknown timeout counts must never be presented as zero. Identical cached repeats are not independent
evidence of generalization.

Use existing lab `Finding` fields first: observation, hypothesis, change, next_test, confidence,
disposition and attempt/supplier/message references. Extend versioned schemas only for structured
audit categories, decision/candidate references, applicability, contradictory evidence, expiry and
promotion evidence. Historical imports lack some original provenance; keep that limitation. Do
not forge campaign/checkpoint identity to fit old runs into new findings. Add a distinct historical
audit reference type if needed.

Separate memory into three scopes:

- Session memory: live facts/offers, objections, citation usage and pending moves; coordinator-owned.
- Supplier memory: dated sourced facts and observed preferences, scoped to supplier AND data version.
- General lessons: conditions -> tested tactic -> outcomes and counterevidence; transfer by case
  features, not supplier/case ID. Retrieve a bounded brief of relevant, approved lessons.

Findings progress from observed/proposed to reviewed, experimentally tested and policy-approved;
retain rejected/superseded records. Model confidence is not a statistical probability. New feedback
does not edit a running policy or promote a candidate. Pin approved lesson and policy versions at
run start. Keep spectator scores/evaluation-only records out of live retrieval; expose only the
permitted fact/lesson projection. Entire Brain retains developer decisions; it is not the production
supplier database. Graph supports implementation/test impact review, not price calculation.

For the lab UI, prioritize an experiment's Decision review and a supplier's Profile/History/Lessons.
Show chosen vs considered packages, full cost, evidence, supplier reaction, outcome and feedback
confidence. Barış's current dashboard is the foundation; a second dashboard is unnecessary.

## 5. Integration and delivery order

P0 — Runtime/Decision: start an integration branch from pinned main. Integrate the lab commit;
port our narrow evidence checks and tests, not our older runner wholesale. Resolve overlapping
CLI/compare/docs changes; document 12/13 names overlap across branches. Keep both logs with their
source provenance. Fix false completion on open sessions, server-deadline resets and unresolved
request handling. Use one evaluator for every close, including serial/final/recovery paths.
Gate: persistent close rejection stays resumable; old cached replies cannot grant extra time;
same logical retry cannot duplicate a move; no alternative-sheet acceptance.

P1 — Evidence owner (proposed Ece): versioned ingestion, unseen-supplier fallback, contact-change
notes and current-case overlays. Gate: replacement/overlay and unseen-ID fixtures work without
practice history; all claims link to valid sources.

P1 — Samet/Decision: wrap and test complete-package economics, horizon/volume logic, deterministic
prices and nonlinear scenarios. Preserve measured package configuration as the comparison
candidate. Gate: saved P04/P08/P10/P11/P18 failures plus new boundary cases pass offline.

P2 — Barış/Lab plus Evaluation owner: import the existing owned runs; retain original and recovered
outcomes; add deterministic audits and evidence-linked feedback reports. Proposed Evaluation
owner is still to be assigned. Gate: feedback correctly diagnoses the known P04/P10 problems and
does not declare causation for P02/P05 unchanged outcomes or the P04 evidence tie.

P3 — Evidence/Decision: optional bounded reply interpreter, then test reply-aware argument selection
against the same package policy. Gate: fallback, numeric fidelity, wrong/stale citation rejection
and latency tests pass before it is enabled.

P4 — Runtime/Evaluation: exercise the actual combined runtime through the lab. Default lab campaigns
are serial D01/D02, so create an explicit async suite/checkpoint and adapter for the selected
policy configuration and data hashes. Audit adapter parity: same factory, config, runner, closing
path and provenance as intended final execution. Verify campaign execution on the actual macOS
host; Barış records Linux execution evidence and macOS remains unverified in his documentation.
The lab has no final mode; instrument the final runner with the shared event contract without
routing final sessions through the development campaign launcher.

## 6. Evaluation and release gates

Do offline replay/invariant checks first, then a free sandbox rehearsal after runtime integration.
Use local synthetic cases with renamed suppliers, shifted units/dates, new clauses, stale facts
and missing documents to test contracts. This tests robustness, not hosted persuasion.

Compare one hypothesis at a time: package policy; then response-aware evidence; then any approved
feedback-derived policy. Freeze code, config, data, runner and lesson versions. Alternate arms on
the same cases. All ten hosted cases have already informed development, so the ten-case suite is
regression, not an unseen holdout. Keep any genuinely unseen evaluation sealed.

Retain every planned attempt. Separate runtime failures, valid no-deals, automatic recovery and
operator assistance. Report aggregate/per-case scores, completed/planned coverage, cost components,
timeouts, invalid actions, contradicted claims, unresolved requests, latency and rounds. A recovered
positive score must not repair an originally failed sample for promotion.

Use lab promotion gates for its exact suite: complete original ended outcomes, compatible pinned
inputs, no increased known timeouts or constraint failures, at least one point mean improvement,
no case regression over two points, and positive wins in at least two thirds of repetition blocks.
These are engineering thresholds, not statistical proof. Preserve a rollback checkpoint. The
earlier twenty-session practice plan is still deferred; select one explicit campaign protocol
before spending, because the lab's repeated-suite default is a different budget.

Recheck live shared quota and active sessions before any authorized campaign. The recorded 140
remaining is historical. Lab campaign leases/budgets do not cover independent scripts using the
same key; designate one execution owner or bring every launcher under the same coordination.

Before Sunday freeze: validate the actual new release, rerun affected offline checks, rehearse
multi-case deadlines/crash recovery on the intended host, pin the submitted commit and cache the
permitted contexts. A feedback service or lab outage must not stop the agent. If time is tight,
ship reliable package economics, ingestion and deterministic audits; defer automatic policy edits,
personality models, external news connectors and broad autonomous experimentation.

## Source snapshots

- Samet: main `dc3a109`; candidate `ec56b38`, `configs/candidate.json`; experiment LOG and docs 13.
- Our branch: `99cd025`, experiment LOG; targeted run source `25fe977`; rename changes remain local.
- Barış: `08274aa`, `codex/experiment-dashboard`; shared ancestor with main `1a18dc0`. Reviewed docs
  12/13 and lab models/worker/report interfaces. This plan does not claim his full suite was rerun.
- Brainstorming attachment: supplied snapshot plus later runtime review.
- Pinned official kit `1b5516b`: brief/api.md, brief/brief.md, data/README.md and arena_kit/cost.py.
- Local review: main 111 tests and our 43 tests passed with lint; additional fault injection
  reproduced false completion. No test result here certifies the proposed integration.
