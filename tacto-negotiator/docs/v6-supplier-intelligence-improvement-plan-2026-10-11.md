# V6 supplier intelligence improvement plan

Date: 11 October 2026 (Europe/Zurich). Status: **local reliability candidate implemented;
hosted evaluation and promotion pending**. See the
[implementation record](v6-supplier-intelligence-reliability-implementation-2026-10-11.md).

Scope: the current `codex/v6-supplier-intelligence-plan` worktree, including its
uncommitted supplier-intelligence changes. This plan follows the code review of
the strategy adviser, final-offer adviser, supplier briefs and response writer.
It supplements the [original plan](v6-supplier-intelligence-plan-2026-10-11.md).

## Objective

Make supplier intelligence reliably improve an approved negotiation decision or
message. Preserve deterministic economics, one closing authority, source
provenance, deadline protection and durable transport recovery. More model calls,
more fluent prose and more agent roles are not success criteria.

The first deliverable is a locally verified candidate with stronger semantic
checks, constrained writing, shared model budgets and useful failure diagnostics.
Commercial improvement is a separate claim requiring a controlled comparison.

## Review evidence and limitations

- A direct local reproduction showed that `checked_body` accepts an unsupported
  promise to buy additional volume and unsupported qualitative supplier claims.
- A direct local reproduction showed that assessment admission accepts “We need
  payment in 30 days.” as evidence for `lead_time_days`. Both field patterns match
  “days.” This proves an admission defect, not an observed erroneous live trade.
- The latest logged skilled three-case practice admitted zero model-written
  emails. P10 fell back after prose rejection and a final-adviser `ValueError`;
  its score was 0.5546564482 versus 0.6472939821 in the preceding briefed run.
  This unpaired comparison does not establish a causal effect.
- The all-case writer has local validation, not measured hosted effectiveness.
- During review, 70 focused tests passed with two async RFQ tests excluded. The
  initial run encountered an async failure followed by a stall and was interrupted.
  Async readiness remains unresolved; the cause was not established.

Original outcomes and limitations are in [the experiment log](../experiments/LOG.md).

## Current architecture and boundaries

```text
Versioned data -> source-linked supplier brief
                            |
Owned thread -> deterministic V6 draft + evaluated candidate menu
                            |
                 strategy OR final adviser
                            |
                 semantic and economic checks
                            |
                 optional response writer
                            |
             fresh validation -> journal -> dispatch
                            |
                    owned supplier reply
```

The all-case configuration broadens writing eligibility. Strategy and final advice
remain limited to supported serial single-supplier capacity and renewal cases.
The existing coordinator retains acceptance and walk-away authority. Supplier
text and model output remain untrusted evidence. No new orchestration framework
or additional reviewer agent is needed for this plan.

## Delivery sequence

| Phase | Priority | Deliverable | Dependency |
| --- | --- | --- | --- |
| 0 | P0 | Reproducible baseline and diagnostic failures | None |
| 1 | P0 | Field-specific assessment admission | Phase 0 |
| 2 | P0 | Constrained, intent-preserving response writing | Phase 0; reuse Phase 1 evidence |
| 3 | P0 | Shared durable model-call budget | Phase 0 |
| 4 | P1 | Explicit decision record and stage boundaries | Phases 1–3 |
| 5 | P1 | Constraint-led candidate generation and brief selection | Phases 1 and 4 |
| 6 | P1 | Separately evaluated final-counter risk policy | Phases 3–4 |
| 7 | P1 | Controlled evaluation and release decision | Relevant earlier gates |

Execute as small sequential changes. Finish the P0 reliability work before
changing candidate economics or expanding adviser coverage.

## Phase 0 — Capture the baseline and expose failures

Primary files: `experiments/LOG.md`, source manifests, `package_advisor.py`,
`strategy_advisor.py`, `final_advice.py`, `response_writer.py`.

- [ ] Capture commit, current diff, untracked runtime files, resolved config,
  dependency lock, data identity, model settings and skill hashes. A commit alone
  does not identify the current candidate.
- [ ] Preserve distinct controls: default V6, the briefed candidate, the skilled
  candidate and the all-case candidate. Do not treat them as interchangeable.
- [ ] Add regression fixtures for the two reproduced admission defects and safe
  neighboring examples. Include unsupported nonnumeric commitments and claims.
- [ ] Emit stable reasons for provider refusal, empty output, invalid JSON, schema
  rejection, invalid citation, semantic mismatch, prose rejection, stale state,
  timeout and budget denial. Record the failing field/check without credentials.
- [ ] Retain bounded request/response diagnostic artifacts in the existing local
  evidence store, with access and retention appropriate for buyer-private context;
  expose sanitized summaries in shared reports.
- [ ] Reproduce each async RFQ test separately with a bounded timeout. Establish
  whether the problem is environment, simulator timing or application behavior.

Acceptance: both admission defects have executable regressions; fallback causes
are distinguishable; async limitations have a recorded diagnosis or remain an
explicit release blocker for the affected path.

## Phase 1 — Validate what the supplier actually said

Primary files: `assessment.py`, `strategy_advisor.py`, `final_advice.py`,
`questions.py`, their focused tests.

- [ ] Define a small observation record: issue/field, requested direction, optional
  value and unit, polarity, condition, source span and explicit/inferred status.
- [ ] Require field-specific support. “Days” alone must not identify payment or
  delivery. Mixed statements must identify the span supporting each field.
- [ ] Preserve conditional antecedent and consequence; do not equate an exact
  substring match with a correct interpretation or fulfilled condition.
- [ ] Handle negation, corrected statements and superseded constraints explicitly.
  Ambiguity yields abstention or an existing registered clarification question.
- [ ] Reuse the same admission logic in strategy and final review. Keep legal
  package validation and complete-cost evaluation independent.
- [ ] Test English and German expressions represented in the supplied evidence,
  payment/delivery confusion, partial conditions and contradictory updates.

Acceptance: payment-only evidence cannot authorize a delivery change; unresolved
conditions cannot justify a concession; supported trades remain admissible;
rejection preserves the prepared move. No model observation changes terms directly.

## Phase 2 — Preserve intent while constraining buyer prose

Primary files: `message_prose.py`, `response_writer.py`, role prompts,
`agent.py` serial/async writing handoffs, writer tests.

- [ ] Give the writer a structured message contract: approved terms, permitted
  acknowledgements, validated claim references, allowed commitments and mandatory
  questions/conditions. Keep private targets and reservations out of the prompt.
- [ ] Render factual claims, commitments, numbers and required questions from
  validated data. Limit free-form generation to bounded connective wording.
  Claims in free text need explicit support; a phrase blacklist is insufficient.
- [ ] Preserve the selected action's intent. A rewrite must not remove a registered
  question, weaken a condition, add volume or imply acceptance.
- [ ] Separate prose rejection from decision rejection: retain a valid selected
  package and render deterministic text when writing fails.
- [ ] Include the complete final message in fresh validation and payload hashing.
  Verify evidence decoration and async preview matching preserve the contract.
- [ ] Test unsupported qualitative claims, paraphrased commitments, spelled-out
  quantities, required-question removal and safe ordinary language.

Acceptance: the reproduced additional-volume promise and unsupported supplier
claims are rejected; valid acknowledgements remain possible; writer failures do
not discard valid decisions or alter attached terms.

## Phase 3 — Share one durable model-call budget

Primary files: `package_advisor.py`, `advice.py`, `final_advice.py`,
`response_writer.py`, `model_assist.py`, `play.py`, `runner.py`.

- [ ] Introduce one session budget keyed by session, supplier, update, role and
  request digest. Include every enabled live model path, including legacy advice
  and optional ModelAssist. Account for offline brief compilation separately.
- [ ] Reserve calls and time durably before dispatch; restore reservations after
  restart. Unknown attempts stay charged. Distinguish reservation from actual usage.
- [ ] Prioritize actionable strategy/final decisions over optional rewrites; reserve
  time for validation, limiter waits, sending and closing against the actual deadline.
- [ ] Replace detached timeout handling with a transport lifecycle that requests
  cancellation, discards late results and bounds resource occupancy. If server-side
  completion cannot be cancelled, report that uncertainty rather than assuming it stopped.
- [ ] Record per-role calls, latency, token usage when reported, capacity rejection,
  late completion and budget consumption. Include writer calls in session totals.
- [ ] Exercise concurrent suppliers, provider stalls, restart during a call and
  execution near the deadline using deterministic clocks/fakes where appropriate.

Acceptance: roles cannot collectively exceed the configured budget; restarting
does not reset writer allowances; late responses cannot mutate decisions; repeated
timeouts cannot create unbounded background work or consume the closing reserve.

## Phase 4 — Make decision stages explicit

Primary files: `agent.py`, `advice.py`, `play.py`, `runner.py` and a small shared
decision-contract module if needed.

- [ ] Define a decision record with state/version digest, baseline move, evaluated
  menu, selected action, supporting observations, mandatory message content,
  budget reservation, validation outcomes and final payload identity.
- [ ] Extract context preparation, advice admission and message composition from
  `agent.py` incrementally. Avoid a broad rewrite of working negotiation policies.
- [ ] Commit draft state only after fresh validation. Preserve one logical POST
  identity and exact payload for uncertain-send recovery and retries.
- [ ] Emit an effective capability manifest at launch: enabled roles, supported
  case types, runner restrictions, policy limits and prompt/skill versions.
- [ ] Keep deprecated config modes readable while validating incompatible options
  explicitly; avoid silent activation or disabling of economically relevant roles.

Acceptance: replayed non-target decisions retain their terms and actions; disabled
features preserve baseline behavior; serial/async authority is visible; state
mutation and transport journaling still have one clearly defined owner.

## Phase 5 — Improve the choices and evidence presented to the adviser

Primary files: `advice.py`, `package_advisor.py`, `supplier_briefs.py`,
`strategy_advisor.py` and candidate/brief tests.

- [ ] Generate candidates around admitted supplier constraints, including coherent
  multi-issue trades. Retain complete-cost checks and allowed-option validation.
- [ ] Rank and diversify the bounded menu before truncation. Record which issues
  are covered and why candidates were excluded; avoid fixed enumeration order
  deciding which useful trades the model can see.
- [ ] Keep the current zero-concession setting as a control. Any nonzero economic
  envelope becomes a separate opt-in treatment with explicit limits and rollback.
- [ ] Select brief excerpts by current issue, part, source authority, freshness and
  conflict coverage. Preserve conditions and relevant contradictory source pairs.
- [ ] Keep sourced statements, model interpretations and proposed tactics distinct.
  Historical tactics cannot independently authorize a current changed offer.
- [ ] Measure menu coverage on annotated saved replies and brief retrieval quality
  before measuring downstream selection. Do not attribute missing options to the model.

Acceptance: labeled useful legal trades appear in bounded menus; unrelated options
do not crowd them out; contradictions survive relevant context selection; rejected
or stale packages remain excluded. Commercial benefit still requires Phase 7.

## Phase 6 — Isolate final-counter risk policy

Primary files: `final_review.py`, `final_advice.py`, explicit policy configs and
final-review tests.

- [ ] Preserve the distinction between an executable outside offer and the
  case-priced no-deal scenario. Never convert a modeled fallback into a supplier quote.
- [ ] Report counter upside, potential loss, break-even walk probability, remaining
  time and uncertainty in the decision record.
- [ ] Keep exploratory loss-envelope mode explicitly experimental. Do not describe
  its configured limit as an estimated or calibrated supplier walk probability.
- [ ] Assess continuation, rejection and delayed replies as distinct outcomes where
  evidence allows; label any retained binary accept/walk approximation.
- [ ] Compare risk policies with adviser, prose and brief settings fixed. Repeated
  acceptance by one exposed supplier does not establish general reliability.

Acceptance: no counter bypasses legal, cost, time or one-counter checks; risk
assumptions are visible; missing inputs abstain; changing risk policy cannot be
mistaken for a benefit from better interpretation or writing.

## Phase 7 — Evaluate the actual contribution of each role

Follow [LAB_PLAYBOOK.md](../LAB_PLAYBOOK.md) and the current recommendation/findings
workflow before experiments. This document authorizes no hosted calls, sessions,
publication or promotion. Existing freeze and final-run rules continue to apply.

### Local verification

- [ ] Run targeted tests for each change, including the reproduced defects.
- [ ] Replay saved negotiations with deterministic provider outputs and compare
  terms, decisions, claims, state changes and final payloads.
- [ ] Run serial and async simulator checks with deadline and restart faults.
  Resolve the review's RFQ failure/stall before claiming async readiness.
- [ ] Run the required locked regression suite and Ruff before publishing a candidate.
  Record exclusions and environment limits rather than counting them as passes.

### Provider and commercial experiments

- [ ] Freeze source/config/data/model/skill identities and an exposure manifest.
  Reserve genuinely unexposed cases/suppliers before further tuning where available;
  otherwise label results as development evidence.
- [ ] First propose a separately budgeted provider-only probe on representative
  contracts. Predeclare sample size, validity threshold, fallback threshold and
  latency gates against the configured execution reserve. Report censored timeouts.
- [ ] Then propose a tracked baseline/candidate comparison changing one factor:
  semantic admission, constrained writing, candidate generation or risk policy.
  Compare model briefs with extractive briefs in their own treatment.
- [ ] Choose cases where the changed role is actually eligible. P07/P11 results
  alone cannot validate the capacity/renewal strategy adviser.
- [ ] Specify case count, repeats, alternating arm order and exact maximum sessions
  before execution: `2 × case count × repeat count`. Existing allowances must be
  checked explicitly; this formula is not a spending authorization.
- [ ] Inspect every failed, partial and completed attempt. Keep outcome reporting
  separate from the runtime agent and preserve original recorded evidence.

Report the funnel **eligible -> called -> valid -> admitted -> dispatched ->
outcome**, split by role and case type. Also report fallback reasons, timeouts,
complete deal cost, score, must-haves, downside exposure and model cost. A valid
response that is never dispatched is not evidence of supplier impact.

Promotion requires the applicable lab gates and original complete outcomes. The
playbook currently specifies at least one point mean gain on the 100-point scale,
no case regression over two points, wins in at least two thirds of repeat blocks,
valid must-haves and known nonincreasing timeouts. Translate score scales explicitly,
verify the current suite policy, and report small-sample/generalization limitations.
Safety repairs without a score gain should be labeled as such, not as commercial wins.

## First implementation slice and completion criteria

Start with Phase 0 and the two reproduced admission failures. Then complete Phases
1–3 without changing risk appetite, economic concession limits or supported case types.

The initial reliability milestone is complete when:

- [ ] Unsupported commitments and field-confused evidence fail the local regressions.
- [ ] Valid decisions survive writing failure with deterministic text.
- [ ] Every live model role uses persisted shared accounting and respects deadlines.
- [ ] Failures produce actionable reasons and reproducible evidence.
- [ ] Relevant serial/async checks pass, or the affected unsupported path remains
  explicitly disabled and documented.
- [ ] A frozen candidate and experiment proposal are ready for review, with no
  commercial improvement claimed before measured evidence supports it.

Rollback uses the prior frozen source/config/data/skill combination. Disable the
affected optional role for new decisions through the existing supported policy
path; reconcile pending sends using their existing persisted payloads. Never
rewrite an in-flight request or alter a recommendation pointer implicitly.
