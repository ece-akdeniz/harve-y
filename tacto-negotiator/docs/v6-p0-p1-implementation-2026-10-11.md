# V6 P0 and P1 implementation record

Date: 11 October 2026. Base: `279f7a8348f4f94f0de650cb5f990aeaff794ab4`.
Control policy: `configs/score-push-v6.json` (SHA-256
`d093a41d23b0a8e4b9c08046ae5eaf9ed74b85b16646e82f586878b5aa56591d`).
The default final policy remains V6. The V6 pin is the control, not a new score claim.
Candidate config SHA-256: `ee82a755f7945e0bc0e480e7d1149c080db459aa88a1e1948408e7dcdff41903`.
The provider model, settings and supplied data release remain unpinned until a separately
authorized latency experiment; the dry run uses only the checked-in practice fixture.

## P0: control and request accounting

- `experiments/v6-exposure-manifest.json` marks all 19 checked-in practice cases and
  their suppliers as development exposure. The saved P10 trace and earlier experiment
  records are development evidence. No hosted hidden case is claimed as a holdout.
- `agent_metrics.model` measures ModelAssist only. `agent_metrics.package_advice` now
  separately measures the legacy or guarded adviser: attempts, fallbacks, latency,
  reported tokens, and attempts with unknown usage. Feedback keeps these two paths
  separate. A reported zero token count has a different meaning from unknown usage.
- `scripts/probe_advice_latency.py` reconstructs six provider requests from the saved
  P10 opening: three development variants × legacy and combined contracts. It prints
  only request digests/sizes in dry run. The exact original failed provider request was
  not saved, so these are explicitly reconstructions. `--execute --allow-calls 30
  --repeats 5 --output PATH` is the proposed 30-call exploratory provider probe;
  execution requires a separate call/spend allowance. It makes no Arena sessions.
  Requests run sequentially with a fresh HTTP client per call. The present probe
  measures provider HTTP plus parsing together and records that timing gap.

## P1: guarded serial execution

- `configs/score-push-v6-guarded.json` opts into `guarded-v1` for one serial capacity
  supplier with zero allowed cost increase. Unsupported paths retain V6. The async
  runner continues to disable package advice.
- A draft copy prepares the V6 move once. The copy isolates proposal bookkeeping,
  the V6 fixed-volume cache, target/trait caches, supplier note state, and model
  context. A failed, skipped or `keep` response uses that prepared move. The selected
  package is checked against legal options, must-haves, complete cost and the outside
  alternative. Only selected proposal state and claim reservations are committed at
  pre-dispatch validation.
- A changed history, payload or elapsed deadline blocks a new send. The generic
  crash fallback does not convert this guard failure into another move. The existing
  coordinator retains acceptance and walk-away authority; final offers bypass advice.

Initial validation was local. The saved P10 fixture and synthetic replies check package
admission, fallback parity, stale-state blocking and deadline behavior. Ninety-one
focused tests pass and Ruff passes. One async model test stalls in this environment;
one dashboard test cannot bind a local socket under the sandbox. Two data-package
tests require a package absent from this worktree. These checks do not establish
supplier acceptance, inference reliability or commercial gain. A subsequent single
guarded P10 practice session is recorded in [the experiment log](../experiments/LOG.md).
It did not change the package. Outcome-reason telemetry was added after that run;
the saved run does not contain a precise fallback reason.
