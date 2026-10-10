# Team and build sequence

All times Europe/Berlin, 10–11 October 2026. Assign the three unnamed roles at kickoff;
roles are ownership assignments, not assumptions about teammates' skills.

| Owner | Modules | First deliverable |
|---|---|---|
| Samet — Decision/integration | optimizer, policy, guards; shared contracts | Complete-package evaluator and one safe close |
| Runtime | client, runner, state, trace, config, cli | D02 timing evidence, coordinator and durable request journal |
| Evidence | dossiers, traits, claims, Sunday overlay | Typed provenance and supplier-specific estimates |
| Evaluation/pitch | writer, beliefs with Samet, report, experiments, replay, slides | Baseline report and reproducible comparison |

One owner per module. Agree on records in 02-architecture.md before splitting work. Coordinate
interface changes directly. The evaluator and coordinator integrate first; do not postpone
closing authority or relationship-aware evaluation until after parallel execution.

## Milestones, in order

| Gate | Target | Evidence required |
|---|---|---|
| M0 | First hour | Environment works; official D01 completes; D02 instrumented; design questions asked |
| M1 | Saturday afternoon | Custom single case completes; all close paths validated; coordinator present |
| M2 | Saturday early evening | RFQ and multi-case run; recovery/fallback checks; no observed hard failures |
| M3 | Saturday evening | Typed claims + supplier estimates + one selected package-policy experiment |
| M4 | Before overnight break | Holdout comparison; stable candidate; one trace-backed demo; slide outline |
| M5 | Sunday 08:00–08:30 | Release loaded; new facts/documents visible; targeted regressions |
| M6 | Sunday 09:00 | Exact final machine/config preflight and measured model latency |
| M7 | Sunday 10:30 | Feature freeze; only validated fixes afterward |
| M8 | Sunday 11:30 | Submission ready, revision recorded, runner started and waiting |
| Final | Sunday 12:00 | Code/slides frozen; autonomous final; observe only |

If behind, remove optional features, not acceptance checks, persistence or deadline handling.
Do not chase the wall-clock targets by calling an incomplete milestone complete.

## Scope control

Must ship: complete economics, shared closing authority, valid claims, deadline management,
request reconciliation, trace, final runner. Then add the highest-value measured policy change.
Stretch: rich viewer, many persona rules, a second model, sophisticated opponent learning.
No model training or framework migration on the critical path.

Reserve a short daily integration slot and protected rest before final operations. Named owners
handoff with commit/config, last successful run, open failures and quota left. No speculative
overnight experiment loop consuming the protected reserve.

The overall-title story requires a small replay from actual logs. Evaluation owns it from day
one; Samet should not also own the entire frontend and runtime implementation.
