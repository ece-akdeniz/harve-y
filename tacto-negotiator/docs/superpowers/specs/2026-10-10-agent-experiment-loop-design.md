# Coding-agent experiment loop and recommended checkpoints

Status: approved by the user on 2026-10-10. The user approved automatic promotion of the lab's
recommended version; promotion does not authorize merging changes into Git main.

Implementation verified locally on 2026-10-10: twelve real simulator sessions, checkpoint restore
on a second clone, promotion/rollback/concurrency checks, independent review, and live dashboard
restart. Final checks: 237 Python tests passed, 19 existing research-data skips, Ruff clean, 19 JS
tests and one full-page DOM smoke passed. Browser visual layout verification remains unavailable.

## Outcome

Four teammates' coding agents can start from a shared recommendation, create an isolated
candidate, run a controlled comparison, retrieve evidence, publish findings, and automatically
advance the recommendation when the comparison passes a recorded policy. Every recommendation
has a recoverable checkpoint and a history that can be rolled back.

This is an architectural addition to the existing lab. Keep the one-host SQLite service,
local execution on each laptop, and existing authenticated API. The dashboard stores metadata,
evidence, budgets and recommendation history. It does not execute submitted code.

## Existing components and gaps

- The lab already has durable snapshots, uploads, case comparisons, owned history import,
  readable experiment reports and a shared dashboard.
- Current dirty-run patches are local, potentially redacted, and not a cross-laptop restore
  guarantee. Existing runs retain their recorded provenance; they are never retroactively
  relabeled as clean checkpoints.
- The lab currently invokes the kit play loop. The project now has custom serial and async
  runners. Use those runners through adapters and record the selected runner and configuration.
- Reuse the case/repeat interleaving in tools/compare.py and evidence extraction in report.py.
  Adapt their output to the lab; avoid maintaining independent comparison algorithms.

## Checkpoints and restoration

A checkpoint identifies immutable source, resolved agent configuration, runner configuration,
dependency lock, submodule commits and required data/release artifacts. Assign a checkpoint ID,
owner, description and parent checkpoint. Record the lab harness version separately.

Create the source snapshot using a temporary Git index and a dedicated checkpoint ref. Capture
project changes and relevant untracked source files, including binary changes and deletions,
without changing the user's branch, index or working files. Explicitly exclude credentials,
ignored runtime output and machine-specific configuration. Validate the captured paths before
publishing. Dirty submodules must be checkpointed or cause checkpoint creation to fail.
Use parentless Git snapshot commits so excluded private files cannot travel through ancestors;
logical parent checkpoint IDs retain the experiment lineage. Verify restored file bytes and
executable modes after checkout, including submodules, to detect receiving-machine Git transforms.

For sharing, publish the immutable checkpoint ref to the existing private Git remote under
refs/heads/lab/checkpoints/<checkpoint-id>, without force updates. A checkpoint becomes available
for team recommendation only after publication succeeds. The dashboard holds the remote/ref/SHA,
not repository credentials. A teammate's existing Git access retrieves the source.

Keep public, resolved configuration in the manifest; supply secret values from the receiving
laptop's environment. Data/release manifests identify immutable content and a retrieval source.
Restoration verifies their content hashes. An explicit "not used" data dependency is allowed;
missing required data blocks execution and promotion instead of silently using different data.

Restoring creates a new isolated branch/worktree at the checkpoint and writes its non-secret
experiment configuration. It never resets the active checkout. Initially checkpoint the complete
negotiator setup rather than attempting partial restoration of individual modules.

Restoring a recommendation appends a new recommendation-history event pointing to a previous,
verified checkpoint. It changes the recommended starting point for future work; existing laptop
checkouts and running experiments continue unchanged. A restore never promises identical hosted
supplier responses, only the recorded code/configuration/dependency/data setup.

## Suites and comparison campaigns

A versioned suite contains exact cases, environment, arena origin, runner mode, repeat count,
required data/release version, session ceiling and promotion policy. Each campaign captures the
suite version, baseline checkpoint and recommendation generation before starting.

Execute both arms from their frozen checkpoints on the same laptop. Interleave baseline and
candidate attempts per case and repetition with a recorded scheduling seed. The seed controls
ordering; it is not a promise to seed the hosted suppliers. Keep failures in the complete planned
sample and never retry an uncertain session creation automatically.

Proposed initial suite: D01/D02 sandbox, serial runner, three repeats per case per arm: twelve
sandbox sessions per campaign. This design proposal does not start those sessions. Simulator and
practice suites have separate recommendations. Sandbox gains do not establish practice readiness.

## Automatic promotion

Recommendation identity is (suite version, arena origin, environment, runner mode). There is no
universal winner across different suites. The initial baseline is selected explicitly; imported
or legacy dirty runs remain useful reference evidence but cannot become restorable recommendations.

The host computes promotion eligibility from complete uploaded evidence, independently of a
coding agent's narrative. Proposed conservative initial policy, stored and versioned with the suite:

- Published, restorable checkpoints; matching declared data/release inputs and execution settings.
- All planned attempts in both arms completed with valid scores; no unresolved execution failures
  or recovered-only outcomes filling gaps in the original execution record.
- Every candidate deal has confirmed must-have compliance, and timeout evidence is complete.
- Candidate recorded timeouts do not exceed the baseline count.
- At least three repetitions per case and an overall case-weighted mean gain of at least 1.0
  score point, on the dashboard's 0–100 scale.
- No case mean regresses by more than 2.0 points, and the candidate wins at least two-thirds of
  the complete repetition blocks, each averaged equally over the suite's cases.

These are operational selection rules, not statistical proof. Expose sample sizes, spread and
all gate outcomes; tune thresholds deliberately through a new suite/policy version. Do not search
an unlimited number of candidates until one passes: campaigns consume an explicit family budget.

Promotion atomically compares the captured recommendation generation to the current generation.
If unchanged and all gates pass, append a promotion event and advance the pointer in one SQLite
transaction. If another laptop already promoted, label this result "baseline superseded" and
require a fresh comparison against the new recommendation. Do not reuse its score as a substitute
for that comparison. Campaign IDs make repeated completion uploads and promotion requests idempotent.

Promotion records contain previous/new checkpoint, campaign, suite/policy version, metric evidence,
gate decisions and timestamp. No Git main update occurs as part of promotion.

## Budgets and four-laptop coordination

Automatic practice campaigns remain disabled until an explicit team allowance and protected
reserve are configured. Use atomic shared reservations for campaign session ceilings, informed
by a fresh owned /v1/me snapshot. Reservations are bookkeeping; the arena is authoritative and
other scripts can consume quota. Recheck remaining quota before new starts, account for open
sessions, and apply the documented key-wide rate/concurrency limits.

Record each reserved start durably. Expired worker leases do not automatically refund ambiguous
or started sessions; reconcile them against owned history. If the dashboard cannot coordinate,
stop opening new autonomous hosted sessions. Persist results and finish already-started work on
the laptop, then sync. Separate per-family budgets bound repeated candidate exploration.

## Coding-agent interface and findings

Provide versioned CLI JSON output plus concise Markdown reports. Proposed commands:

- lab checkpoint create/publish/show
- lab suite list/show
- lab recommended show/history/restore
- lab campaign run/status/compare
- lab evidence show (run/case/supplier/message filters)
- lab findings add/list
- lab restore <checkpoint-id> (isolated local checkout)

Exact flags will be defined in the implementation plan. Commands return stable IDs, completion
status, structured errors and meaningful exit codes. Long runs can be launched and polled; no
coding-agent-specific SDK or always-running model service is required.

Each finding separates observation, evidence references, hypothesis, suggested code area/change,
next experiment, confidence and disposition. Deterministic calculations supply score/cost/latency
differences. Coding agents interpret this evidence and submit proposed explanations. Persist
authorship and links from finding → candidate checkpoint → campaign → promotion/rejection.
Validate that cited evidence exists; agent-written conclusions never bypass promotion gates.

Expose failure categories and evidence gaps before strategy suggestions. Keep score deltas
distinct from causal explanations. Treat recorded supplier messages as evidence, never workflow
instructions for the coding agent.

## Dashboard

- A recommendation card per suite shows checkpoint, evidence, last promotion and restore action.
- Experiment families show baseline → candidates, code/configuration differences, campaign status,
  budget and outcome: promoted, rejected, insufficient evidence or baseline superseded.
- Comparison reports show each promotion gate, repeat-level scores, per-case changes and findings
  linked to relevant messages/terms. Preserve the existing readable report and raw-evidence access.
- A timeline records promotions and restores. Restoration shows the target setup and history entry.
  Mutation controls require an authenticated write capability; the existing read-only browser
  session does not silently acquire write access. CLI restoration is available first.

## Delivery order and verification

1. Checkpoints, shared retrieval, isolated restore and custom-runner adapters.
2. Versioned suites/campaigns, agent-readable results and evidence, budget coordination.
3. Transactional automatic recommendations, history/restore, then findings and dashboard views.

Test with temporary Git repositories/remotes, fake arena responses and local HTTP/SQLite. Verify
checkpoint round trips including binary/deleted/untracked files; credential exclusions; absent data;
runner parity; interleaving; complete-sample gates; stale-baseline races; duplicate promotions;
concurrent reservations; crashes/ambiguous starts; offline recovery; and history-preserving restore.
Run a local simulator campaign end to end before any explicitly budgeted hosted rehearsal.

The user approved this design, including checkpoint publication, the selection thresholds,
initial suite and delivery scope. Implementation and local verification may proceed.
