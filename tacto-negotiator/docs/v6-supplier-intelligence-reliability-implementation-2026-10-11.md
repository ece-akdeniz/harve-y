# V6 supplier intelligence reliability candidate

Date: 11 October 2026. Scope: local `codex/v6-supplier-intelligence-plan` worktree.
This record follows the [improvement plan](v6-supplier-intelligence-improvement-plan-2026-10-11.md).
The initial revision was a local safety candidate. A subsequent five-session
practice screen and local repair revision are recorded below; no publication,
recommendation change, or commercial improvement is claimed.

## Candidate and controls

The original V6 default remains the control. The briefed, skilled and all-case
configurations remain separate opt-in controls. This change keeps the zero
concession envelope, supported capacity/renewal adviser types, and existing
final-counter risk limits. The initial reliability byte manifest is
[`experiments/v6-reliability-source-manifest.json`](../experiments/v6-reliability-source-manifest.json).
It records the base commit, tracked patch, dirty/untracked counts, source and
skill hashes, lockfile, data files and nonsecret model settings. The earlier
all-case manifest is the pre-repair identity; neither is a hosted checkpoint.

## Validation repair after the five-case practice screen

The five-case practice screen is recorded separately in `experiments/LOG.md`. It
exposed two rejected model suggestions: an explicit P03 payment alternative was
labeled as a constraint, and an explicit P10 delivery alternative was labeled as
an objection. Their exact saved model answers now pass local replay against the
original supplier threads. P03 selects a 60-day buyer counter at EUR 392.48;
P10 selects a legal 56-day buyer counter at EUR 31.90 derived from the supplier's
54-day alternative. These are counter proposals, not supplier acceptances or
claims about the scores a new hosted run would achieve.

The source-linked assessment now admits explicit alternative offers only for
the non-price fields and values they state. A delivery value outside the buyer's
legal option set can support a counter at the next longer legal value. Exact
source matching, current-message scope, refusal checks, complete-cost ceiling,
must-haves, final-offer risk and the fresh pre-dispatch check still apply.

When a primary strategy or final-review response fails validation, a separate
`validation-repair-v1` role gets one bounded chance to select an approved package
or question using a corrected current-message citation. It can also take over
after a primary provider timeout or response error. The original adviser runs
the same validation and economic checks again on that answer. The shared durable
session ledger keeps a six-second reserve for this role. It uses the existing
provider unless `VALIDATION_LLM_BASE_URL`, `VALIDATION_LLM_API_KEY`, and
`VALIDATION_LLM_MODEL` configure an independent endpoint. The role's skill hash,
route, reason and outcome enter local metrics; its request and response stay in
owner-only bounded evidence files.

The second endpoint improves resilience only if it is independently available.
If both model calls fail, the source is stale, the deadline or model budget is
exhausted, or no legal supported counter exists, the prepared deterministic
decision remains the safe outcome. No new provider or Arena session has tested
this revision. The new source identity is captured in
`experiments/v6-validation-repair-source-manifest.json`.

## Implemented locally

- Assessment uses field-specific payment and delivery cues. Each admitted field
  has a source span, polarity, optional value/unit and requested direction.
  Conditional advice requires a verifiable antecedent satisfied by the selected
  package; ambiguous conditions abstain. German payment/delivery cues and explicit
  corrections are covered. Restart reconstruction rechecks field support.
- Buyer writing receives an explicit message contract. Approved boilerplate and
  validated term numbers are admitted; unsupported free-text claims and commitments
  fall back to deterministic prose. Registered questions and prepared conditions
  must survive exactly. Writing rejection does not reject a legal package.
- All live model roles share one session ledger with an eight-call, 32-second
  default, configurable as `model_budget_max_calls` and `model_budget_total_s`.
  Legacy package advice, strategy, final review, all-case writer and optional
  ModelAssist reserve before dispatch. Optional writing/interpretation leaves one
  call and eight seconds for decision work. Reservations survive a process restart,
  and corrupt ledgers deny additional model calls. Offline brief compilation is
  separate. The serial CLI uses its run directory; the async runner uses its
  transport journal directory.
- Provider refusal, empty output, invalid JSON, schema rejection, capacity denial,
  timeout, citation rejection, field rejection and prose rejection have distinct
  local codes. Private request/response diagnostics are capped at 16,000 characters
  per side, owner-only, ignored by Git and retained for 30 days. Shared traces
  contain digests, counts and codes rather than private text. A timed-out request
  may still finish on the provider: its local result is discarded and its budget
  remains charged. Four in-process slots bound concurrent detached work.
- The serial and async dispatch paths record state and payload digests, selected
  action, mandatory content, budget state and final payload identity. Launch
  traces expose effective role capability and serial-only adviser scope. Bounded
  menus prioritize current issue coverage and diversify issue fields; runtime
  briefs prioritize relevant sources and retain available conflict pairs.
- The async wave-cap closer waits through its reserved closing window when every
  supplier sheet is in flight. This fixes a repeatable local simulator failure
  where the earlier 20-second wait ended before a healthy pending reply.

## Verification and limits

Focused admission, advice, writer, budget, brief and decision tests pass. Two
async RFQ writing tests and an async ModelAssist test were run separately with
bounded timeouts outside the tool sandbox. A minimal `asyncio.to_thread` also
stalls inside that sandbox but succeeds outside it; the tests passed outside.
The wave-cap regression passes outside the sandbox. Ruff passes.

The full local suite result and exact exclusions are recorded in the experiment
log. `uv` is not installed in this environment, so the two lab subprocess tests
that invoke `uv lock --offline` cannot run here, and the prescribed `uv run
--locked` command could not be used. The equivalent installed virtual environment
ran against the current lockfile without installing dependencies. Hosted transport,
provider latency and commercial effects remain unverified.

## Proposed measured gate

Before any provider or Arena call, freeze this manifest with resolved config,
data, model and skill identities; reserve suppliers/cases not used for tuning; and
obtain a separate call/session allowance. The provider-only probe proposal is
**20 calls, zero Arena sessions**: five sequential calls on each of four saved
contracts (capacity strategy, renewal strategy, final review and all-case writer).
Require all 20 responses to parse and meet their role schema, at least 18 to pass
local semantic/prose admission, zero unsupported dispatchable claims, and each
role's observed p95 provider-plus-parse latency below 75% of its configured
timeout. Count refusals, invalid JSON and censored timeouts in the denominator;
stop after the first budget or deadline violation. These are proposed thresholds,
not a call authorization or a prediction of provider performance.

After that gate, isolate one factor per frozen comparison. An initial development
comparison could use one capacity and one renewal case, three repeats per arm,
alternating arm order: `2 × 2 × 3 = 12` Arena sessions maximum. P10/P04 are already
exposed development cases, so their results could diagnose behavior but cannot
support holdout or promotion claims. A promotion comparison needs newly reserved
eligible cases and its own exact session allowance. Preserve every attempt and
report eligible, called, valid, admitted, dispatched and outcome counts by role
and case type. The existing lab promotion gates and final freeze still apply.
