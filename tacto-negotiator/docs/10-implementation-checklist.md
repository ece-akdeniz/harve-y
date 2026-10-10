# Implementation checklist — read before coding

Snapshot: documentation finalized against scaffold on 10 October 2026. This is an explicit
backlog, not a claim the agent works. Update boxes only with test/run evidence.

## Current implementation

PackageAgent v0.2 uses one closing evaluator through both serial and async orchestration.
The async runner journals requests, reconciles and resumes; one hosted D02 crash/restart
completed the same session with zero timeouts. Prep, reporting and the replay viewer execute.
Verified claims are integrated behind NEGOTIATOR_CLAIMS=1, limited to single-supplier
price-increase cases. P01 improved from 80.0 to 92.8 in a two-repeat comparison. Estimates,
MESOs and claims remain off by default; model interpretation/writing is not implemented.
Full final-machine, wave-cap, concurrent-load and Sunday-release rehearsal remains outstanding.
See the [experiment log](../experiments/LOG.md) for exact scopes and limitations.

Only a supplier's standing (first) sheet is directly acceptable on the hosted API. Other
valid sheets are candidate counteroffer packages, not IDs the agent may accept directly.

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
- [x] Shared evaluator handles accept and walk-away, including deadline closure.
- [ ] Reconcile stale/in-flight offers and compare all eligible RFQ packages before closing.

## Gate C — runtime (Runtime)

- [ ] Async client, bounded workers, key-wide limiter, no state locks across awaits.
- [x] Async runner persists logical request ID + exact payload and retries idempotently.
- [ ] Restart reconstructs UTC/server deadlines; does not reuse old monotonic timestamps.
- [ ] Reconcile pending operations, existing sessions and server-counted rounds after errors.
- [ ] End-to-end buyer deadline includes model/parsing/limiter time; bounded fallback.
- [ ] Wave watchdog accounts for queuing; no unvalidated use of kit closing_move.
- [x] CLI dispatches prep/play/run/report. Failure exit-code consistency still needs review.

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

- Shared closing evaluator is now required; obsolete runner fallback removed. Async closing
  uses the same case estimates as the decision policy (explicit runner overrides take precedence).
- guards.check docstring enforces monotonicity and strips IDs: replace with corrected policy.
- claims.build_bank includes weighted decomposition: keep internal unless supported as a checked claim.
- optimizer.payment_breakeven_pct and test currently assert approximation; change together.
- report docstring suggests optimal component regret: output only what actual results support.
- config needs complete model/release wiring; state needs versioning, claim scopes and journal.

Documentation changes do not implement these fixes. Do not mark readiness from passing the
existing scaffold suite alone.
