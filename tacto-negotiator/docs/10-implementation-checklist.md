# Implementation checklist — read before coding

Snapshot: documentation finalized against scaffold on 10 October 2026. This is an explicit
backlog, not a claim the agent works. Update boxes only with test/run evidence.

## Current implementation

PackageAgent v0 and custom play/run commands execute through the official kit. Deterministic
non-price optimization, concession scheduling and basic closing checks exist. The kit runner
still services one RFQ thread at a time. Async runtime, persistent recovery, full relationship
cost integration, claim verification and prep/report remain unfinished. See the dated
[experiment log](../experiments/LOG.md) for actual hosted results, including interrupted runs.

## Gate A — setup and measured baseline (Runtime + Evaluation)

- [ ] Run root README setup and local checks; record installed kit revision.
- [x] Complete official D01; record serial D02 timing and a one-round concurrent probe.
  See experiment log; sustained concurrency and queued closing remain unverified.
- [ ] Record organizer responses for session queuing, clock start, wave-cap acceptance and units.
- [ ] Agree shared records and module owners in 02 before separate implementations.

## Gate B — economics and closing (Decision + Runtime)

- [ ] Resolve latest quote standards and fixed terms; validate exactly permitted negotiable fields.
- [ ] Compute all C components, must-haves and alternative; handle no alternative explicitly.
- [ ] Per-supplier cost/value estimates with uncertainty for stabilise/secure_supply.
- [ ] Correct exact payment threshold and its current approximation-based test. For the general
  payment comparison, compute both complete costs; x/(1+x) assumes starting at reference terms
  and no other price-linked effects.
- [ ] Margin reference uses cost/(1-m), not cost*(1+m); optimize soft penalty rather than hard floor.
- [ ] Coordinator is sole owner of accept AND walk-away; validate agreed and fallback paths alike.
- [ ] Reconcile stale/in-flight offers and compare all eligible RFQ packages before closing.

## Gate C — runtime (Runtime)

- [ ] Async client, bounded workers, key-wide limiter, no state locks across awaits.
- [ ] Persist logical request ID + exact payload before send; retry idempotently.
- [ ] Restart reconstructs UTC/server deadlines; does not reuse old monotonic timestamps.
- [ ] Reconcile pending operations, existing sessions and server-counted rounds after errors.
- [ ] End-to-end buyer deadline includes model/parsing/limiter time; bounded fallback.
- [ ] Wave watchdog accounts for queuing; no unvalidated use of kit closing_move.
- [ ] CLI actually dispatches prep/play/run/report and returns useful exit codes.

## Gate D — evidence and model (Evidence + Evaluation)

- [ ] Merge base/release/case context with provenance; include overlay CSVs/documents.
- [ ] Match supplier-specific should-cost rows and price_unit; no double country adjustment.
- [ ] Calendar-aware index windows; unknown data flagged rather than silently zero-filled.
- [ ] Separate external Claim, ProposedTerms and PrivateDecision values.
- [ ] Claim scope ledger includes per-recipient rival quote exception and valid live offer IDs.
- [ ] Unsupported assertion rejected/replaced; ID stripping alone is insufficient.
- [ ] Model receives bounded context; typed reply interpretation is a hypothesis, not authority.
- [ ] Deterministic template reproduces validated packages/claims when model fails.

## Gate E — measured candidate and final readiness (Evaluation + all)

- [ ] Develop against the chosen subset; freeze a holdout before tuning.
- [ ] Compare candidate and baseline with quota-aware repeats and per-case failure analysis.
- [ ] Run concurrent rehearsal and targeted failure tests from 04-experiments.md.
- [ ] Report realized components and aggregate regret separately; no invented optimal components.
- [ ] Produce one replay showing evidence, two candidate packages and actual closing rationale.
- [ ] Sunday overlay + final machine preflight; submit and execute 06-final-runbook.md.

## Scaffold mismatches to fix while implementing

- runner.py docstring reserves only accept and references kit closing_move: update to coordinator
  ownership of both closing actions and our full evaluator.
- guards.check docstring enforces monotonicity and strips IDs: replace with corrected policy.
- claims.build_bank includes weighted decomposition: keep internal unless supported as a checked claim.
- optimizer.payment_breakeven_pct and test currently assert approximation; change together.
- report docstring suggests optimal component regret: output only what actual results support.
- config needs complete model/release wiring; state needs versioning, claim scopes and journal.

Documentation changes do not implement these fixes. Do not mark readiness from passing the
existing scaffold suite alone.
