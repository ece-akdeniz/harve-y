# V5 capacity adviser: implementation and local evidence

11 October 2026, Europe/Zurich. Implemented locally on `codex/v5-intelligence`, based on
`77b42a4e5fa72bffe9d8c6705a8d76a249500aa6`, in `/tmp/harvey-v5-intelligence`.
The original V2 checkout and the existing V5 policy configuration are unchanged.

## Behavior

`configs/score-push-v5-intelligence.json` is an opt-in candidate. It retains V5's existing
case policies and enables `combined-v1` advice for serial, single-supplier capacity cases.
The CLI and Lab's existing `policy_config` interface load these settings; default/final
policy selection remains `score-push-v5.json`. No hosted run or deployment is authorized
by this file. Async package advice remains disabled by the existing runner.

The agent prepares its normal move in a draft. One bounded call then returns supplier
observations and a selected code-generated package ID, or `keep`. Supplier observations
must cite exact spans at supplier-message indexes or supplier-scoped public document IDs.
The model receives dated public dossier notes, allowed options, must-haves, preferred delivery,
complete candidate terms, code-derived commercial directions and acknowledged buyer packages. It receives
no buyer cost ceiling, reservation costs, credentials or executable tools. The separate
ModelAssist reader is suppressed on this path, including the serial runner's preparation hook.

Candidates include complete current supplier exchanges, existing cost-neutral exchanges,
and bounded one/two-field changes. Price-only alternatives are excluded. There are at most 16 candidates.
The supplied candidate configuration permits up to **1% higher complete evaluated cost than
the scheduled move on that turn**, always below an executable outside alternative when one
exists. This is a per-turn envelope, not a cumulative session concession ceiling. The field
defaults to zero and validates at no more than 3%; the 1% setting is a hypothesis, not tuned
or commercially validated. Relationship estimates enter full-cost evaluation; no inverse
price search is used when those costs may be nonmonotonic. Previously acknowledged exact
packages are excluded from the alternative menu. `keep` retains V5's own strategic behavior.

The response contract is now `capacity-advice-v2`; `combined-v1` remains the opt-in integration
setting. The original hosted trial used the earlier response contract. Conditional statements stay in source quotes;
citations verify provenance, not semantic correctness or supplier willingness. A selected
package needs supporting evidence from the current supplier update covering every changed
non-price field. Quoted terms are classified separately from objections and additionally
require cited historical trade/constraint evidence. A price increase also requires a current
conditional trade and an exact complete supplier sheet. Raw model prose is
never outgoing email. A deterministic acknowledgement and full package description replace
the base offer body only when advice changes the package. Existing evidence enrichment runs
once, after selection, and may append verified claims without changing the approved terms.

Proposal bookkeeping and claim reservations remain staged until the serial pre-dispatch
check validates the observation, exact enriched payload, deadline, package legality and,
for changed packages, fresh full cost and the concession envelope. This check runs before
`table.send`/`table.close`; it is not a replacement for transport/journal ownership or a new
check inside the HTTP client's pacing layer. An uncertain write still belongs to the existing
runner. Direct callers of `decide` using this opt-in mode must call `validate_decision` before
sending, as `play_case` now does.

Malformed/refused advice, an unavailable endpoint, exhausted advice limits or ordinary model
timeout preserve the prepared V5 move. Stale observations or an expired execution window
raise `AdviceExecutionBlocked`, which bypasses the generic crash-and-send fallback. A model
timeout disables further advice in that agent; late results cannot change live state.
External cancellation is not caught as a recoverable model failure.

Limits: at most eight admitted attempts per agent, eight seconds per call, 24 reserved
inference seconds in total, a 20-second fallback/submission reserve, 900 output tokens per
provider request and a 40,000-character input-context bound. Oversized history abstains
without silently dropping earlier refusals. Advice budget reservations are conservative
and are not refunded. Limits and once-per-update admission are in-memory, not durable across
process restart. This slice does not port V2's full persisted inference ledger.

Trace/metrics distinguish attempts, admitted responses, changed decisions, fallback, latency,
reserved time, reported token usage and calls with unknown usage. An attempted provider call
is not proof of successful network transport. No price/spend estimate is invented when usage
is unavailable. Existing environment-based provider/model selection remains unchanged.

## Verification

The subsequent [supplier-aware trade repair](v5-intelligence-supplier-trade-repair-2026-10-11.md)
passed **146 focused regressions**, including nine additional cases and saved P10 opening/final
history checks. Both legacy and disabled-advice replays remain identical to the base at all
20 decision points. This repair used no hosted inference or practice sessions. The evidence
below records the initial implementation before that repair.

The existing Python 3.12 virtual environment was used with `PYTHONPATH=src` and
`ARENA_DATA=/home/ugur/harve-y/negotiation-arena-kit/data`; `uv` is unavailable here.

- **25 new tests** cover joint conditional packages, concession/alternative bounds, relationship
  cost handling, malformed/foreign/buyer citations, refusal history, context bounds, timeout and
  late-result isolation, call/time admission, stale/deadline blocking, staged state, deterministic
  messaging, evidence ordering, exact fallback, transport schema, telemetry and actual serial sends.
- **137 focused regressions passed**, covering the new tests plus package advice, ModelAssist,
  policy, serial/async fallback and routing, replay, retained/fixed-volume strategy, Lab runner
  and budget behavior. Local-server tests require execution outside the filesystem/network sandbox.
- A full sandbox attempt stalled in an async simulator test. The unchanged baseline reproduced
  that stall; the same focused tests passed outside the sandbox. Two local Lab server tests also
  failed with sandbox socket permission errors and passed outside it. No assertions were weakened.
- Scoped Ruff and `git diff --check` passed.
- Broader-suite investigation reached **312 passed, two failed** before stopping at the
  two failures: existing campaign subprocess tests require the unavailable `uv` executable
  (`test_subprocess_runs_restored_source_not_mutable_receiver` and
  `test_orphaned_child_holds_lock_and_sync_uploads_only_final_result`). An earlier full attempt
  reached the final portion of the suite but exceeded its 90-second process limit. The full
  suite is therefore not reported as passing. These worker-launch tests do not exercise the
  standalone tracked runner used for the separately requested capability trial.

Replay comparison used an archive of the untouched base source, this source with legacy
settings, and this source with combined advice disabled (`package_advice_max_calls=0`).
All **20 decision points** were identical: 12 from the saved P05 fixture, five from the saved
P18 fixture and three from a synthetic P10 capacity sequence. Legacy provider calls were
stubbed to `keep`; these checks do not exercise real inference. Fixed supplier replies cannot
establish counterfactual negotiation outcomes.

Replay helper: `/tmp/v5-advice-replay.py`. Outputs: `/tmp/v5-advice-baseline-replay.json`,
`/tmp/v5-advice-current-replay.json`, `/tmp/v5-advice-disabled-replay.json`. All have SHA-256
`3f65e86c962c0f5b96a43a9bf5646f9bfd0deba24995c5abe8004d5a81815ead`.
The implementation/config/test manifest is `/tmp/v5-advice-source-manifest.json`.

Read-only Lab metadata review retained the existing recommendation
`e1d931e4fcce49fb8fd341c40052953a`. Earlier rejected global-anchor and payment-response
findings supported choosing a narrow opt-in case family; this work does not promote a new
recommendation. No hosted inference, Arena sessions, Lab publication, Git push or deployment
was performed during implementation. A subsequent user-authorized P10 live capability trial
is recorded separately. Real supplier understanding and improved commercial outcomes remain
unproven by these local checks.

The [live P10 report](v5-intelligence-p10-trial-2026-10-11.md) records successful execution with
one admitted model decision, but no demonstrated commercial improvement. The candidate remains opt-in.

## Remaining scope

Generalization to other case policies (including cost-target paths), async/multi-supplier
selection, persistent semantic memory, automatic research/tool loops, free-form email writing
and durable cross-restart inference accounting remain outside this slice. Run a separately
budgeted, source-frozen comparison against V5 before enabling the candidate operationally.
