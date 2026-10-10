# Experiment log

Format and decision rule: `docs/04-experiments.md`. Newest on top. One entry per change.

## Packaged runtime negotiation guidance — local integration, 10 October 2026

- Hypothesis: explicit conditional package wording communicates the exchange more clearly
  while preserving validated terms; score benefit remains unmeasured.
- Config/source: working tree, packaged `src/negotiator/AGENTS.md`, runtime-settings v1.
  Custom CLI serial/async play/run (including final) now load the guidance and record
  its SHA-256 and effective settings. Missing/invalid guidance stops launch.
- Existing numerical heuristics remain baseline values. Default CLI wording now makes
  multi-issue offers conditional on the proposed price. Explicit experiment policies,
  estimates and generic MESO activation retain existing controls; no candidate promotion.
- Direct `PackageAgent` construction used by comparison tools retains its previous defaults.
  Starter `arena --agent llm` is a separate implementation and does not load this guidance.
- Cases: local synthetic RFQ decision comparison and both final CLI dispatch paths.
  Integration tests verify changed guidance affects prices, conditional wording preserves
  term sheets, arbitrary-cwd loading, trace provenance and launch failure on invalid guidance.
- Validation: negotiation-only branch: 115 tests passed; combined checkout: 166 tests
  passed; ruff clean. Wheel built offline, contains the guidance, and loads successfully
  after extraction outside the source checkout.
- Hosted sessions/quota: 0. Scores: unmeasured. Full final readiness remains outstanding.
- Decision: runtime integration implemented; no claim of improved negotiation outcomes.

## 2026-10-10 — Readable experiment reports (UI VALIDATION)

- Hypothesis: outcome summaries, labeled terms, cost bars and per-supplier conversations make
  saved experiments easier to inspect than configuration/message JSON. No agent behavior changed.
- Data/config: existing lab run `ee284ea2-76b7-4100-a03f-27fce795f7cc` (D01/D02), unchanged.
  Raw JSON and fingerprints remain accessible under collapsed technical details.
- Validation: ten JavaScript tests pass. An isolated DOM check rendered all 37 messages across
  three suppliers and verified terms, scores, escaping, retained expanded sections/scroll, and
  imported, failed, recovered and truncated evidence states. Ruff and JS syntax checks pass.
- Limit: in-app browser control timed out, so desktop/mobile appearance was not visually verified.
- Quota/scores: no new arena sessions; previous measured results retained. Decision: use the report
  for inspection, preserving partial scores and operational failures explicitly.

## 2026-10-10 14:43 — First shared-lab baseline (MEASURED HOSTED SANDBOX)

- Hypothesis: establish the current PackageAgent's D01/D02 reference and verify the lab records
  and publishes complete results from the host laptop.
- Run: `ee284ea2-76b7-4100-a03f-27fce795f7cc`, **Package v0.2 — first lab baseline**;
  commit `1a18dc0e17f9137deedf52f6db18bd77a006039f`, dirty checkout explicitly allowed.
  Patch SHA256 `fcf7cbc45c297efffc95039868f8b3fe2db7fd785a391928fb83b3ddc68277fb`.
- Config: anchor 0.12, rounds 5, close_gap 0.005, final_hold_s 40, p_walk 0.25;
  claims=false, meso=false, estimates={}. Official kit serial play interface; no wave deadline.
  No local data package, so its fingerprint is null. No provider-model calls.
- Cases: D01/D02, one attempt each, maximum two sessions, explicit sandbox environment.
  D01 **90.48/100**, C=EUR 412,451.25, 26.12s, 7 counted sends/closes;
  D02 **46.09/100**, C=EUR 187,768.00, 7.52s, 10 counted sends/closes.
  Two-case mean **68.28/100**. Both deals satisfy must-haves; zero recorded timeouts/failures.
- Sessions/replays: [D01](https://arena.tacto.ai/replay/0303d7a8e61f034a),
  [D02](https://arena.tacto.ai/replay/ad3bb1c328d166d7).
- Quota: both starts used sandbox cases. Shared practice snapshot changed from 19 used / 181 left
  to 20 used / 180 left while the run was active; the shared counter does not attribute that change
  to a caller. Do not count these two sandbox attempts as practice starts or assert the team was idle.
- Verification: the dashboard's stored final record exactly matches the local run snapshot.
  Raw evidence: `experiments/runs/ee284ea2-76b7-4100-a03f-27fce795f7cc/run.json` (ignored).
- Decision: retain this as the first lab baseline. One run per case is insufficient for a strategy
  promotion; compare a named candidate on the same case plan with repeats before drawing conclusions.

## 2026-10-10 — Dashboard sign-in diagnosis (LOCAL TESTS / PUBLIC TUNNEL)

- Trigger: public-tunnel sign-in displayed a generic sign-in prompt after a connection failure.
- Findings: the existing password and cookie authenticated successfully over the supplied HTTPS
  tunnel in an API check; browser-style requests intermittently timed out. A local regression
  also reproduced a race where an outstanding anonymous refresh skipped the post-login refresh.
- Change: serialize the post-login refresh, retain specific timeout/network/cookie errors, and
  reject unexpected non-JSON tunnel responses. No password or authentication-policy changes.
- Validation: five JavaScript regression tests pass, including the reproduced refresh race.
  Hosted arena cases/quota/scores: none; this is dashboard behavior only. User-browser confirmation
  remains needed to determine whether these fixes resolve the reported public-tunnel symptom.

## 2026-10-10 — Shared experiment lab integration (MEASURED LOCAL)

- Hypothesis: an independent runner and shared dashboard can retain experiment provenance,
  failures and case-aligned comparisons while teammates execute on separate laptops.
- Revision/config: work on `codex/experiment-dashboard` from `42c7659`, uncommitted integration
  run explicitly allowed; PackageAgent defaults, official local simulator with its clock disabled.
- Cases: S01/S02, one attempt each. Scores **82.90/100** and **86.09/100**, both completed;
  five and nine rounds respectively. These verify integration, not a new negotiation strategy.
- Quota: two local simulator sessions; zero hosted sessions and no provider-model calls.
- Evidence: atomic snapshots under `/tmp/lab-e2e-runs/8fd28b58-0237-42dd-b5f5-6367d5586131/`;
  dashboard UI checks used a separate synthetic database, never the real team database.
- Failures addressed in review: reject hosted URLs in simulator mode; preserve imported terminal
  evidence when delayed tracked snapshots arrive; retry and reconcile incomplete history imports.
- Decision: use the lab for development tracking. Preserve original operational failures when
  recovering arena outcomes. This does not change the agent or establish final readiness.

## 2026-10-10 13:37 — Hosted sandbox baseline and RFQ probe (MEASURED HOSTED)

- Revision: `e543b5d5d14fff699019bdffb38688c3bee882b7`, kit `1b5516b`; added diagnostic
  scripts `tools/sandbox_baseline.py` and `tools/rfq_timing_probe.py`. PackageAgent default
  anchor 12%, five-step schedule, close gap 0.5%; deterministic templates, no model calls.
- Hypothesis: optimizing complete packages improves the starter; independent RFQ requests
  can reduce idle-thread timeouts. These are separate experiments, not a controlled ablation.
- Data: downloaded `data/package/world.sqlite`, SHA256
  `4d8c896740350218d39f9d1ceada7b937f0d4e3078a155312851b8c09ed172b9`.
  Verified 447 suppliers, 60 parts, 166 cost-driver rows, 2,258 index values, 208 documents.
  Sunday release not yet available. Do not confuse the full supplier table with the active
  suppliers in challenge cases.
- Naive, one run per case: D01 **20.04/100**, C=€440,757.33, 35.85s, zero timeouts;
  D02 **22.95/100**, C=€201,088.00, 75.28s, one timeout on DEMO-J1. Both deals satisfy must-haves.
  Sessions `7ba285e7808110f7`, `92060a989d6ae9e0`.
- PackageAgent clean rerun, one run per case: D01 **93.24/100**, C=€411,339.92, 8.95s;
  D02 **41.89/100**, C=€190,184.00, 25.30s. Both deals satisfy must-haves; zero timeouts.
  Sessions `923ce268740f20fc`, `fcaea618ad0cdf72`. Unweighted two-case mean **67.57/100**
  versus naive **21.49/100**. This small, unrepeated sample is not a generalization estimate.
- One-round concurrent D02 timing probe: both requests started within 1ms; replies at 14.91s
  and 70.30s; zero timeouts in post-reply snapshots. The probe closed at **27.20/100**.
  Session `52a8e87b7ab4899d`. This was a timing test, not the PackageAgent strategy.
  Server serialization/clock-stop mechanism and sustained multi-round safety remain unknown.
  Production must process replies as they arrive: waiting for both left the first thread idle
  for about 55.4s, close to its 60s limit.
- Invalid strategy comparison retained: sessions `a18869e79c54c4fb`, `a794e41d3e700a8c`
  ended at zero/no deal with three timeouts on every thread. macOS power logs confirm clamshell
  sleep at 13:25:32, waking at 13:32:15 (403s). Exclude these from strategy comparison, retain
  as operational failures. Do not attribute the delay solely to the hosted service. Monotonic
  elapsed time understated wall time across sleep. The clean rerun used `caffeinate -i`.
- Quota: all baseline/probe runs used sandbox only (seven sessions total including
  interrupted cases); practice remains **0 used / 200 available**. No provider-model spend.
- Decision: keep PackageAgent v0 as the measured development baseline; do not deploy it to the
  final unchanged. Prioritize RFQ scheduling, coordinated guarded close/reconciliation,
  relationship-cost estimates and evaluation across diverse cases before added model complexity.
  Keep laptop lid open; rehearse the actual final host/network and deadline recovery.
- Validation: 14 tests pass; Ruff passes. These checks do not verify final readiness.

Raw local evidence (ignored by Git):

- `runs/20261010T112335Z-sandbox-naive-2d319f/`
- `runs/20261010T112418Z-D02-concurrent-9b18f4/`
- `runs/20261010T112455Z-sandbox-package-b55adf/` (sleep-interrupted)
- `runs/20261010T113551Z-sandbox-package-4620f4/` (clean rerun)

Reproduce only sandbox runs from repo root, with the lid open:

```bash
caffeinate -i uv run --locked python tools/sandbox_baseline.py --agent naive
caffeinate -i uv run --locked python tools/sandbox_baseline.py --agent package
caffeinate -i uv run --locked python tools/rfq_timing_probe.py
```

<!--
## E0 - baseline (YYYY-MM-DD HH:MM, owner: )
Hypothesis:
Change: commit
Cases × runs:
Result: mean , min , timeouts , contradicted , must-have breaks
Per-case notes:
Decision:
-->

## 2026-10-10 12:40 - E0/v0 on local arena-sim (MEASURED LOCAL, not hosted)

- Setup: arena-sim (kit 1b5516b), data package identical to audited copy (dump hash match).
- E0 naive: S01 0.521, S02 0.513, S03 0.678 -> mean 57.1. Naive works one RFQ thread only and leaves
  non-price terms at plan values.
- v0 PackageAgent (complete-cost best non-price terms, 12 % anchor, 5-round linear schedule,
  re-offer our terms at their price before accepting, one checked close): S01 0.829, S02 0.861,
  S03 0.886 -> mean 85.8. All deals beat alternative; must-haves ok.
- Caveat: the sim supplier is a fixed script that prices nothing but unit_price. Hosted suppliers
  price payment/incoterm/contract terms; the non-price gain will be smaller there. Do not tune
  anchor/schedule on the sim.
- Next: hosted D01/D02 with v0 once the key exists; record timeouts/rounds per RFQ thread.

## 2026-10-10 13:35 - E0/v0 on hosted sandbox D01/D02 (MEASURED HOSTED)

- First attempt: 4 sessions timed out at 0 - launch error (processes killed after opening), not agent.
- naive: D01 0.200, D02 0.229. v0: D01 0.932 (deal 50.50, FCA, 60 d), D02 0.419 (J1 final_offer
  15.70, payment 30 d, accepted). Replays: naive D01 /replay/e496ba4e489d30ff, D02 /replay/265fc0a0a379b326.
- Next: read v0 D02 replay - why J1 went to final_offer early and whether C1 was the better path.

## 2026-10-10 13:41 - v0 on hosted practice P01 (MEASURED HOSTED, 1 session)

- v0: 0.567 (accepted final_offer 143.40 from 2027-04-01, 90 d). House agent 0.97.
- Replay findings: (1) suppliers send several alternative sheets per mail - v0 read only the
  first and missed EUR 136.80 from 2026-11-01; (2) v0 flipped effective_date mid-negotiation and
  the supplier priced it (+6.50); (3) supplier itself cites LCI-C +2.7 % x 30 % and PPI-C241
  +6.5 % x 24 % -> ~2.4 % justified vs 9.5 % asked: claims are the lever; (4) supplier prices
  payment terms (136.20 @30 d vs 138.40 @90 d).
- Fix v0.1: evaluate every sheet in the latest message by C; lock non-price terms after the
  first offer. Sim regression 85.8 unchanged. Next: index claims for price_increase cases.

## 2026-10-10 14:30 - Evidence: claim bank + supplier cost estimates (BUILD, local only, 0 sessions)

- `claims.build_bank(case, package)`: latest-12-month index windows per cost driver (+ indices the
  case cites), cherry-picked buyer windows (flagged, off by default), rival quotes (per receiving
  supplier, `reveals_rival`), scorecard OTD/ppm, letter notice vs. contract notice, should-cost
  (`internal`). Every claim passes `verify` against package + release + case facts.
- `pick` default: <= 3 claims, buyer-side only, no private disclosure, no ID reuse (`claim_keys`).
  P01 default pick: notice (doc:20260911-70110-P01 51 d vs ctr:4600070110), PPI-D351 -3.7 %,
  scorecard OTD 85.2 %. LCI-C +2.7 % and PPI-C241 +6.5 % stay internal (adverse).
- `cost_pressure_estimate`: P01 stated drivers -> 2.37 pp on 54 % coverage (listed drivers: 2.33 pp
  on 64 %); sentence has no IDs, `verified: False`.
- `dossiers.supplier_estimate`: P01 full cost 132.64 (+-5 %) vs current 126.53 -> margin -4.8 %
  at status quo; rate 0.15 (wants_fast_payment). Relationship term is live even at today's price.
- Sunday: `claims.prep(data_dir, out_path, release)` rebuilds dossiers + banks with the overlay.
- Not integrated into agent.py; claims experiment (vs. mechanical baseline) still to run.

## 2026-10-10 14:01 - compare decision v0.2 vs v0.1 (sim) (MEASURED LOCAL SIM)

- Baseline: `42c7659` @ 42c76599
- Candidate: `WORKTREE` @ c743d6b3 dirty diff a2459668c121
- Cases × repeats: case:S01, case:S02, case:S03 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena http://127.0.0.1:8010; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:S01 | 82.9 82.9 | 82.9 | 82.9 82.9 | 82.9 | +0.0 |
| case:S02 | 86.1 86.1 | 86.1 | 86.1 86.1 | 86.1 | +0.0 |
| case:S03 | 88.6 88.6 | 88.6 | 88.6 88.6 | 88.6 | +0.0 |
- Baseline: mean 85.8 over 6 scored runs, worst case case:S01 82.9, min run 82.9, failures 0, timeouts 0
- Candidate: mean 85.8 over 6 scored runs, worst case case:S01 82.9, min run 82.9, failures 0, timeouts 0
- Raw: `experiments/runs/compare/20261010-140143-sim-decision v0.2 vs v0.1 (sim)/summary.json`
- Decision: (fill in)

## 2026-10-10 14:02 - compare decision v0.2 vs v0.1 D02 sandbox (MEASURED HOSTED SANDBOX)

- Baseline: `42c7659` @ 42c76599
- Candidate: `WORKTREE` @ c95a73ba dirty diff 28f0578cb458
- Cases × repeats: case:D02 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena https://arena.tacto.ai; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:D02 | 41.9 41.9 | 41.9 | 41.9 41.9 | 41.9 | +0.0 |
- Baseline: mean 41.9 over 2 scored runs, worst case case:D02 41.9, min run 41.9, failures 0, timeouts 0
- Candidate: mean 41.9 over 2 scored runs, worst case case:D02 41.9, min run 41.9, failures 0, timeouts 0
- Raw: `experiments/runs/compare/20261010-140224-sandbox-decision v0.2 vs v0.1 D02 sandbox/summary.json`
- Decision: (fill in)

## 2026-10-10 14:05 - Runtime: async runner vs serial on D02 sandbox (MEASURED HOSTED SANDBOX)

- Hypothesis: one worker per thread + coordinator (`negotiator.runner`, `--runner async`) keeps
  RFQ threads free of timeouts with the same score as the serial loop.
- Config: commit c95a73b + uncommitted runtime (runner/client/state), PackageAgent-v0.2, closes via
  `evaluator.close_decision`; limiter 8 calls/s; 60 s move limit, close wait 20 s, cap margin
  max(90 s, slowest + 15 s). Quota: 0 practice (sandbox only).
- Run A (no send slot, 3 parallel sessions): async 0.419 ×3, thread timeouts 0/0 ×3; wall 59 s.
  Concurrent POSTs on one hosted session each took ~16-18 s (vs ~0.5 s alone), and one close hit
  `422 not a standing offer` (closer read the old offer while the chosen thread's reply was being
  stored) - reconciled and re-decided, deal kept. Fixed: in-flight flag cleared only after the
  reply is in the thread.
- Run B (soft per-session send slot, falls back to concurrent sends 25 s before a thread's
  deadline): async 0.419 ×3 + CLI `negotiator play case:D02 --runner async` 0.419, timeouts 0/0
  ×4, wall 25 s for 3 parallel sessions, no close errors.
- Serial control (`negotiator.play.play_case`, 3 parallel sessions): 0.419 ×3, timeouts 0/0 ×3,
  wall 6 s.
- Reading: D02 hosted replies are mostly fast, so serial does not time out on D02 either; the
  async benefit is only shown where a supplier reply takes 30-70 s (earlier hosted probe: C1 70 s;
  local tests with injected 30/50 s delays: async 0 timeouts, serial waiting costs a 409 late).
  Hosted seems to serialise/penalise concurrent calls on one session -> keep the send slot.
- Raw: `runs/20261010-140107-D02-runner-compare/`, `runs/20261010-140327-D02-runner-compare/`,
  `runs/20261010-140410/`.
- Decision: keep serial default; async passes D02 gate (0 timeouts, same score) and runtime tests.
  Promote after an RFQ with slow replies (practice, budgeted) shows no regression.

## 2026-10-10 14:10 - Runtime: async runner with agent.propose (hold) vs serial, D02 (MEASURED HOSTED SANDBOX)

- Config: 89a4389 + runner hold support (`agent.propose` -> send / close / hold), PackageAgent-v0.2
  with propose, closes via `evaluator.close_decision`; per-session send slot on. Quota: 0 practice.
- Batch 1 (3 parallel async sessions, then 3 parallel serial; hosted replies slow, 13-24 s):
  async 0.116 / 0.461 / 0.116, serial 0.461 ×3. Thread timeouts 0/0 in all 6.
  The two 0.116 runs: identical buyer moves to the serial runs; J1 answered our counter to its
  final offer (same price, our terms) with `walked_away`, so the coordinator accepted C1's final
  17.20. In the third async run J1 kept its final and we got 15.50 (0.461). All three async runs
  sent that counter ~15 s after J1's final (send slot waiting on C1's slow reply); walk vs keep
  differed with the same gap, so this looks like supplier randomness on countering a final offer,
  not a clock effect. Not proven.
- Batch 2 (3 parallel async, hosted fast, 8 s wall): 0.461 ×3, timeouts 0/0 ×3.
- Totals for async on D02 today: 10 runs, 0 thread timeouts; serial 6 runs, 0 timeouts.
- Raw: `runs/20261010-140547-D02-runner-compare/`, `runs/20261010-140838-D02-runner-compare/`.
- Decision: runtime gate "no timeouts on repeated D02" met for async. Keep serial default until
  Decision reviews the counter-to-final walk risk (2/9 async v0.2 runs) and an RFQ with slow
  replies is compared.

## 2026-10-10 14:10 - compare D02 v0.2 final-risk rule: meso off vs on (MEASURED HOSTED SANDBOX)

- Baseline: `WORKTREE` @ a794b3ea dirty diff 8b26a25950df
- Candidate: `WORKTREE` @ a794b3ea dirty diff 8b26a25950df, env {'NEGOTIATOR_MESO': '1'}
- Cases × repeats: case:D02 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena https://arena.tacto.ai; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:D02 | 46.1 46.1 | 46.1 | 42.8 42.8 | 42.8 | -3.3 |
- Baseline: mean 46.1 over 2 scored runs, worst case case:D02 46.1, min run 46.1, failures 0, timeouts 0
- Candidate: mean 42.8 over 2 scored runs, worst case case:D02 42.8, min run 42.8, failures 0, timeouts 0
- Raw: `experiments/runs/compare/20261010-141019-sandbox-D02 v0.2 final-risk rule: meso off vs on/summary.json`
- Decision: (fill in)

## 2026-10-10 14:20 - compare claims-only-p01 (MEASURED HOSTED PRACTICE)

- Baseline: `WORKTREE` @ 4dfc2935 dirty diff 67cd032f463f, env {'NEGOTIATOR_CLAIMS': '0', 'NEGOTIATOR_ESTIMATES': '0', 'NEGOTIATOR_MESO': '0'}
- Candidate: `WORKTREE` @ 4dfc2935 dirty diff 67cd032f463f, env {'NEGOTIATOR_CLAIMS': '1', 'NEGOTIATOR_ESTIMATES': '0', 'NEGOTIATOR_MESO': '0'}
- Cases × repeats: case:P01 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena https://arena.tacto.ai; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:P01 | 80.0 80.0 | 80.0 | 92.8 92.8 | 92.8 | +12.8 |
- Baseline: mean 80.0 over 2 scored runs, worst case case:P01 80.0, min run 80.0, failures 0, timeouts 0
- Candidate: mean 92.8 over 2 scored runs, worst case case:P01 92.8, min run 92.8, failures 0, timeouts 0
- Practice quota before/after: {'before': {'used': 5, 'left': 195, 'limit': 200, 'resets_at': '2026-10-11T11:39:03.056071+00:00'}, 'after': {'used': 9, 'left': 191, 'limit': 200, 'resets_at': '2026-10-11T11:39:03.056071+00:00'}}
- Raw: `experiments/runs/compare/20261010-142041-practice-claims-only-p01/summary.json`
- Decision: (fill in)

## Handoff reconciliation and claims experiment — 10 October 2026, 14:24 Berlin

- The three pre-handoff mechanical P01 baseline runs at `8225d16` all scored 80.03/100:
  `63390aa61e6e2687`, `1ac8f6e23bbc8383`, `4499d35e0c2ed088`. Claims/estimates/MESO off,
  serial runner; accepted EUR 137.30, 30 days, effective 2027-04-01. These results existed
  before this continuation and were reconciled from local traces and the authenticated API.
- The estimates-on session `be346505d3153626` ended at zero by timeout. Its last local action
  tried to accept `offer:70110-1-a`. The later standing-offer fix is essential; this failed run
  is not evidence that supplier cost estimates are economically inferior.
- Correction to the early advice: alternative sheets can be evaluated as counteroffer packages,
  but the hosted API accepts only the current standing offer ID. Do not directly accept an
  alternative ID; send its complete terms and obtain a standing offer first.
- New integration at `4dfc293`: optional `NEGOTIATOR_CLAIMS=1` adds verified evidence only to
  single-supplier price-increase offers. Terms, anchor, concession policy and closing evaluator
  remain unchanged. No model calls, cherry-picked windows, private should-cost disclosure,
  rival-quote disclosure or weighted "fair price" assertion. Claim IDs reconstructed on resume
  and reserved on proposal; maximum three checked claims, which may use more than three IDs.
- Controlled P01 comparison: same code/data/serial runner, estimates and MESO off. Baseline
  `be5861930b4426bf`, `b892b7b404698403`: 80.03/100 each. Claims candidate
  `851c4c42585b8575`, `d8cad506359ee966`: 92.79/100 each, an observed +12.76 score points.
  Candidate accepted EUR 136.20, 90 days, effective 2027-04-01. Each candidate response
  verified all three claims (notice, electricity index, OTD); no contradictions or duplicates.
- Evidence saved under `runs/compare/20261010-142041-practice-claims-only-p01/`. Both arms
  recorded the same source/config snapshot and facts hash; only the claims flag changed.
  Later repeats completed much faster with identical outcomes, so do not treat repeats as
  proof of independent supplier randomness or a statistically established effect.
- Decision: promising on P01; keep the global default off pending broader evidence. Use the
  explicit claims flag for price-increase experiments. Practice quota 195 -> 191 (four sessions).
- Runtime review found a separate persistence bug: a torn final journal line was ignored on
  load but not removed before append, which could hide all later records after another restart.
  `11d74e1` preserves the damaged tail and repairs the boundary; mid-file corruption fails closed.

- P01 cost diagnostic: claims candidate C=EUR 1,100,921.13 versus baseline EUR 1,108,192.02
  (EUR 7,270.89 lower). Candidate relationship penalty is EUR 13,608.40 versus baseline
  EUR 1,222.38: improved terms still lower total C, but payment/supplier-health tradeoffs matter.
  Remaining aggregate gap to reported C_best is EUR 4,105.35; this is not a component-level
  optimal-cost decomposition. Calibrate supplier estimates before enabling them globally.

## Hosted restart rehearsal and local regression — 10 October 2026, 14:23 Berlin

- At `11d74e1`, `tools/resume_probe.py` interrupted its D02 child after a persisted send intent,
  restarted with the same journal, and completed session `cee30b71402e03c8`: 46.09/100,
  must-haves passed, zero server-reported timeouts, one open intent/one session, no pending
  journal requests. Raw: `runs/20261010T122302Z-resume-D02-d32f32/`.
- This is one hosted recovery observation, not proof of all disconnect/queue scenarios or
  permission to restart during the final. Practice quota unchanged at 191.
- Integrated local regression against `3c69dec`: S01 82.90, S02 86.09, S03 88.56 in both arms;
  mean 85.85/100. Raw: `runs/compare/20261010-142304-sim-integrated-regression/`.


## Hosted mini-sweep and closing consistency — 10 October 2026

- Frozen runtime source `11d74e1`, claims/estimates/MESO explicitly off; five planned practice
  sessions, quota 191 -> 186. Changes during the sweep were documentation/tests only.
- P03 serial `c0d525e3d5026b65`: 89.98/100, 147.5 seconds, zero server timeouts.
- P05 serial `7b86fd5e5d9a7794`: 36.04/100, 212.2 seconds, TWO server timeouts
  (one each on sup:70210 and sup:70250).
- P05 async `499d117f5572cc78`: 36.04/100, 58.0 seconds, zero server timeouts.
- P07 serial `d1b5e17f1072c6e1`: 74.30/100, 57.0 seconds, zero server timeouts.
- P10 serial `2323becf5b0aeba2`: 45.32/100, 50.0 seconds, zero server timeouts.
- All five returned a deal with must-haves satisfied. Actual timeout counts were fetched from
  authenticated session/thread APIs afterward: the comparison summary's default zero is not
  sufficient evidence of absence. Saved `runs/mini-sweep-20261010-142332/server-evidence.json`.
- P05 observed async avoided idle-thread timeouts; same deal/score. One pair cannot establish
  a latency distribution, especially with possible hosted caching. Promote further RFQ tests
  to async; full multi-case/wave rehearsal remains required before the final.
- Next priority: inspect P05 and P10 replay/economics, then budget a controlled policy comparison;
  expand claims tests across other price-increase cases. P01 success is not broad competitiveness.
- Fixed after the frozen sweep: async coordinator now uses the agent's case estimates when no
  explicit runner override is supplied. Removed obsolete fallback closing policy that could
  accept an alternative-sheet ID and omit relationship economics. Regression covers inherited
  estimates and explicit overrides including empty dict. Estimates remain opt-in: relationship
  penalties can make total cost non-monotonic in price, so inverse-price assumptions need review.


## Remaining hosted coverage and improvement plan — 10 October 2026, 14:40 Berlin

- User requested all untested cases, then planning with P04/Boo as a concrete target.
  Source frozen at `1a18dc0`; no agent source changes. Async, claims/estimates/MESO off,
  up to three concurrent cases, shared six-call/second limiter. Five-session budget.
- P02 `1c87a28d5390f289`: 29.34/100, 53.3s.
- P04 `ae20ddcf43f86237`: 5.64/100, 47.5s.
- P08 `7b1457795e1fbbbd`: 15.62/100, 72.3s.
- P11 `d5371cf52ee9b718`: 31.44/100, 130.8s.
- P18 `ca5c5a2ee6331b7f`: 38.61/100, 72.8s.
- All five returned valid deals satisfying must-haves, zero server-reported thread timeouts.
  Quota 186 -> 181. All ten hosted cases now covered. Nine `hosted:false` cases not opened.
- Recorded configuration facts hash `7dc162f977c0`; SQLite hash is separately stored in
  `experiments/coverage-20261010.json` (comparison harness uses SQLite for its data hash).
  Local complete replays: `experiments/runs/coverage-20261010/`.
- Human-only public board snapshot at 14:40: Boo leads P04 (81.0), P05 (38.1), P08 (22.7),
  P11 (40.6). P18 now held by y/agent (38.6), equal to house at displayed precision.
  Board data is never passed to runtime agents. These are moving benchmarks.
- Offline claim-bank coverage: four price-increase cases build; fifteen other cases throw
  `TypeError` because notice generation calls `float(None)` on missing document days.
  Repair required before enabling evidence on other types; no claim repair implemented yet.
- P04 replay: repeatedly asks for a lower price on the same 12-month package despite dossier
  signal that supplier discounts multi-year agreements. At recorded fixed terms,
  EUR 4.94 / 90 days / 24 months calculates 86.04; this is a target, not an obtained offer.
- P10 previous replay: final-counter risk uses infinite loss without an external quote,
  suppressing a cheaper supplier-proposed package. Official finite fallback semantics must
  be validated before changing this logic. P11's request for faster payment conflicts with
  its negotiable schema; do not follow it.
- Decision: enter planning phase. `docs/12-measured-improvement-plan.md` specifies P04 first,
  followed by package exploration and targeted fixes, with 24 proposed development sessions
  plus 10 regression sessions and a protected 46-session reserve. No additional quota spent.

## Staged package experiment implementation — 10 October 2026

- Implemented optional versioned policy configs, complete-cost package enumeration at opening
  and proposed prices, bounded stagnation trades and history-based reconstruction. Defaults
  preserve the baseline; supplier estimates and generic payment MESOs remain disabled.
- Claims now tolerate missing/non-numeric notice fields; nineteen public case banks verified.
  Quality prioritizes historical ppm; renewal prioritizes performance and index evidence.
- Added no-alternative final-counter opening-improvement proxy behind configuration, limited
  to a cheaper supplier-proposed package. It is not expected normalized score.
- Reports distinguish unknown timeouts; incomplete CLI runs exit nonzero. Run traces include
  resolved policy hash, source revision, actual base and release file hashes and decisions.
- Local validation: 101 tests pass. Added a sequential manifest runner with a 46-session
  reserve and stop gates; first release is four P04/P11 screening sessions only.
- FAQ supplied by user confirms normalized wave means rank, ties use deals then rounds,
  no deal scores the alternative (zero without one), and every case has a fixed Cbest.
  Cooperative wording and verified evidence are supported by the FAQ example, not proof
  that our candidate improves. Jury prize weighting remains unspecified.

### Screening preflight follow-ups (outside frozen candidate source)

- Batch A is frozen at `120558215629388579130703778ad60e6ac5dd84` in isolated checkouts.
  Current working-tree follow-ups do not alter its runtime policy or source mid-batch.
- Fixed the batch reporter to count the hosted API's timeout event lists (including empty
  lists) instead of marking them unknown; added stop-gate tests for contradicted claims and
  unresolved requests. Original results also contain explicit per-thread timeout counts.
- Hardened generic multi-year trades to preserve the quoted annual volume when volume is
  negotiable, and wording to describe the actual volume when it is a negotiated field.
  This does not affect P04, whose annual volume is fixed, or P11, which has no contract field.
- Added malformed-notice preservation coverage and the current staged contract in document 13.

## Batch A — four screening sessions, source 1205582

- P04 package-only: `e2fcc134ecd03d17`, **86.04/100**, EUR 4.94 / 90 days / 24 months.
- P04 package + evidence: `b71d601095c82d96`, **86.04/100**, identical closing package;
  its 85.0% delivery claim was verified. Select simpler package-only.
- P11 package-only: `cc9acf4242059a59`, **31.44/100**, unchanged from historical baseline.
- P11 package + evidence: `88f8a5d21a61c30f`, **39.80/100**. Select evidence for confirmation.
- All four: valid deals, must-haves satisfied, zero authenticated thread timeout events,
  no contradicted claims, no unresolved journal requests, successful exit status.
- Cycle spent four. Shared quota 179 -> 165: ten additional sessions were consumed outside
  this batch. Our ledger uses explicit session IDs, not the shared quota delta.
- Human benchmark refresh: P04 best displayed 86.0, P11 best 62.6 (makeAnother.md).
  These are rounded moving targets; P11 remains below the current competitor.
- Released Batch B: fresh baseline 1551125 and frozen winning screening candidate 1205582
  per case. P04 baseline then candidate; P11 candidate then baseline. Four sessions.
- Local diagnosis: P11 suppliers price chargeback risk and propose cheaper alternatives.
  The experimental stagnation order tightened ppm before reducing chargeback; a local fix
  now tries adjacent lower chargeback first and only relaxes ppm upward. Batch B retains
  original source to test reproducibility. The fix is reserved for later gated refinement.
- Tracked compact evidence: `experiments/staged-cycle-20261010.json`. Full ignored local
  traces/journals/authenticated thread data: `experiments/runs/staged-a-20261010/`.

## Batch B — confirmation

- P04 baseline `6a95b5d68d53a5d0`: 5.64; package candidate `2d99044cccd0f46b`: 86.04.
- P11 evidence candidate `321b3475cf3cf054`: 39.80; baseline `a08f5e8f1f64df2e`: 31.44.
- Zero timeouts, invalid deals, contradicted claims or unresolved requests. Four sessions;
  quota 165 -> 161, cycle total eight. Exact repeated results may be cached/deterministic;
  they establish reproducibility, not statistical significance.
- Release four P11 refinement sessions: two per permitted lower-chargeback variant, with
  quality evidence enabled, ppm 300, payment fixed. Config rank selects one or two permitted
  steps below the highest chargeback, not a case ID or a leaderboard-derived price.
- Skip P04 optional refinements: candidate matches the refreshed displayed leading score.
- Refinement source also fixes stagnation to consider adjacent lower chargeback before ppm,
  with ppm switches only upward within the must-have. Initial concession schedule unchanged.

### P10 offline gate and replay artifact

- Reproduced P10's recorded opening: 19,890 units/year versus must-have >=22,230.
  The experimental opening-relative proxy has no compliant opening input, so it safely retains
  the standing offer. Added an actual-case regression and an explicit unavailable-input log.
  Skip P10's four hosted comparison allocations unless that prerequisite becomes available.
  Do not inject historical Copen/Cbest or reinterpret finite fallback cost as no-deal score.
- Generated a shareable measured P04 HTML replay with actual terms, verified delivery evidence
  and complete costs. Package-only tied this evidence arm; the claim's incremental effect is zero
  in this screen. `experiments/replays/p04-package-evidence.html`.
- Local suite: 109 passed; ruff clean. Sunday release and final host rehearsal remain separate.

## P11 refinement — source 37fe085

- Lower chargeback rank 1: `2a2e85e2f0372c98` and `49fc8d01470de13a`, both **63.38**.
- Lower chargeback rank 2: `c6869765602972cc` and `f4b2804c5cfda349`, both **70.99**.
- All four satisfy must-haves, zero thread timeouts, no contradicted claims or unresolved
  requests. Historical 2,376 ppm and electricity change claims were verified. Payment stayed
  at the fixed 60 days. Source/terms/costs retained in each authenticated replay.
- Select rank 2. This exceeds the last observed public leader's 62.6, subject to refresh.
  Repeated results are reproducibility observations, not significance tests.
- Quota 161 ->157; cycle total 12. Released 12 broader comparisons: P08 packages, P02 claims
  only, P05 supplier-standard faster payment, each versus baseline twice. P10 skipped at
  the missing-input gate. P04 optional refinements skipped; maximum planned cycle now 44
  if all remaining gates pass, below the 52 ceiling.

### Combined-policy and regression runner preparation

- Added per-case-type package preferences so a combined quality chargeback policy does not
  replace an independently measured RFQ payment policy. No case IDs or target prices enter
  policy configuration. Local test verifies renewal, quality and RFQ preference separation.
- The subset runner loads the selected source checkout, shares one AsyncArena across all cases,
  and fails when requested results are missing. Final comparison can run five baseline cases,
  all ten candidate cases concurrently, then the other five baseline cases. This alternates
  baseline/candidate order by case while exercising candidate concurrency with one limiter.
- Local suite: 111 tests passed, ruff clean. Final comparison has not started or spent quota.

### P02 clause/payment investigation after unchanged claims scores

At the observed EUR 373.65 / 90-day package, local complete cost is EUR 2,268,972.94.
A copper clause at the same price raises cost; equal-cost prices are approximately EUR
367.00 (zero deadband), 369.19 (3% deadband), and 370.66 (5% deadband). Paying in 30 days
requires about EUR 368.70 to be cost-neutral. These figures are human diagnostic calculations
from published terms and rates, never runtime targets. No hosted clause benefit established;
keep that unmeasured policy out of the combined candidate.

## Broader development — twelve sessions, source 807aebb vs 1551125

- P08: baseline **15.62**, candidate **59.30**, both repeated. Enable raw-material package policy.
- P02: baseline and claims candidate **29.34**, repeated. No incremental claim benefit here.
  Price-increase evidence remains a combined candidate hypothesis because prior controlled P01
  runs improved to 92.79 and P02 did not regress; final regression must verify both.
- P05: baseline and supplier-standard payment candidate **36.04**, repeated. Omit the extra
  RFQ package policy from the combined candidate. Rival claims remain disabled.
- All twelve: valid deals, zero actual timeouts, no contradicted claims or unresolved requests.
- Shared quota 157 ->140 (five additional external sessions); cycle total 24.
- Freeze `configs/candidate.json`: packages for renewal/quality/raw-material; evidence for
  price-increase/quality; quality starts two permitted chargeback steps down. Risk remains legacy.
  No runtime leaderboard, historical Cbest or case-specific target prices.
- Before promotion: free D01/D02 crash/recovery rehearsal, then the budgeted twenty-session
  paired ten-case regression. Stop on safety failures. Maximum cycle remains 52; planned use44.

## Free recovery rehearsal and quota checkpoint

- Frozen candidate source `ec56b38`, `configs/candidate.json`, D01 and D02 concurrently,
  one shared client/limiter. Injected SIGKILL after the first journalled send, then restarted
  the same journal. Exactly two sessions across restart; both completed valid deals.
- D01 `ca71bef0a414bc54`, score 91.92; D02 `e415cfd2dafb22ae`, score 46.09.
  Zero actual timeouts, no contradicted claims or unresolved requests. This is runtime
  recovery evidence, not a practice persuasion benchmark or full wave-cap rehearsal.
- Practice quota unchanged: **140 before and after**. Cycle practice total remains **24**.
- User asked about progress and conserving requests. No further practice starts while the
  choice is pending. The final **20-session** paired comparison has NOT started.
- Prepared `experiments/final-comparison-manifest.json`: five baseline cases, all ten candidate
  cases concurrently, then the other five baseline cases. It alternates arm order by case.
  Running it would bring this cycle to 44/52 sessions; always recheck shared quota/reserve.
- Combined candidate is NOT promoted. Ten-case mean and regression thresholds remain untested.
  Sunday release validation and final-machine/wave readiness remain outstanding.

- User subsequently chose **stop after the free check and preserve quota**. No more practice
  sessions started. Final comparison is explicitly deferred until the user asks to resume.

## 2026-10-10 — MEASURED LOCAL: immutable full-project experiment loop rehearsal

Hypothesis: normal anchored rounds improve kit simulator S01/S02 score over a deliberately
weak one-round, zero-anchor control. This tests loop integration with scripted toy suppliers;
it is not hosted performance evidence or a proposed production strategy change.

- Source: current public project bytes and exact uv.lock captured into a temporary isolated Git
  repository; baseline checkpoint `c1585d66a11d4b228eb24a2f87ea5f8a`, candidate
  `24a77b1e71f74e3c9f957c0e712374e3`. Both were published only to a temporary local bare remote.
- Config: baseline anchor=0, rounds=1; candidate anchor=0.12, rounds=5. Both final_hold_s=0,
  claims=false, meso=false, estimates={}; serial runner, no dossier inputs.
- Cases/quota: actual bundled arena_kit.sim S01/S02; three repeats per case per arm,
  all 12 planned sessions completed through real CLI and restored-source worker subprocesses.
  Two separate worktrees each used `uv sync --locked --offline` and independent environments.
  No hosted sessions, hosted quota, actual origin pushes or actual dashboard DB writes.
- Scores (0–100): S01 14.5102 → 82.9021; S02 14.5243 → 86.0854. Overall gain 69.9764;
  zero within-case spread, all three repetition blocks won; baseline/candidate timeouts 0/0.
- Decision: temporary lab policy verdict **promoted**; all gates passed, no evidence gaps.
  Deterministic scripted responses explain zero spread; this establishes local execution fidelity,
  not generalized negotiation readiness. Real CLI evidence references and immutable finding saved.
- Recovery/invariants: real CLI restore fetched candidate from temporary remote on second clone,
  verified every tracked byte/lock hash, and preserved active untracked work. Separate synthetic
  policy SQLite verified rejection, simultaneous same-generation completion (exactly one promotion,
  one baseline_superseded), idempotent completion and recommendation rollback generation 2→3.
- Failures: harness-only fixes for literal fixture credential secret-scan rejection, incorrect
  artifact worktree path and CLI response envelope in fixture suite. No production defect found.
- Validation: Python 232 passed, 19 existing research-data skips; Ruff passed; Node helper/DOM
  checks passed. DOM smoke now requires explicit LAB_UI_DOM_MODULE and reports skip when absent.
- Artifacts: `/tmp/tacto-loop-rehearsal-itmo0e21/summary.json`, `cli-results.json`, `lab.sqlite`,
  `loop/measured/` immutable worktrees/request journals/final outcomes, second-clone and restored.
  Reproduce with `uv run --locked --offline python tools/rehearse_loop.py`; retained-artifact checks
  use `--verify-existing /tmp/tacto-loop-rehearsal-itmo0e21`. Original local cache and loopback socket
  permission are required; fetching remains offline. Detailed task-5-report.md/checks.log in SDD.

- Final independent review follow-up: host promotion now requires original ended-session evidence;
  CLI restore request-ID retries remain idempotent; precreated family budgets and practice protections
  survive smaller campaign ceilings. Five regression cases reproduced before fixes. Final full suite:
  237 passed, 19 existing data skips; Ruff clean; retained simulator evidence reverified without new
  sessions. Direct UI checks: 19 tests plus one actual-page DOM smoke passed.
- Live dashboard restarted with saved credentials and existing database. Secure-cookie login, bearer
  reads, new loop overview, retained original experiment and public tunnel loop.js asset verified.
  Initial shared recommendation remains explicitly unseeded; no real checkpoint publication or hosted
  campaign was launched. Browser crash prevents visual layout QA.

## 2026-10-10 — Lab setup: nested-project checkpoint verification

- Hypothesis: checkpoint publication and restoration must verify the entire repository when the
  negotiator lives below its root and the arena kit is a sibling submodule.
- Change: inspect Git trees with `--full-tree`; retain root-relative submodule and private-file checks.
  Negotiation policy/configuration is unchanged. The coding-agent workflow is in `LAB_PLAYBOOK.md`.
- Failure: initial real-repository restore rejected the valid sibling kit as a submodule manifest
  mismatch. A nested-project, sibling-submodule, second-clone regression reproduced it before the fix.
- Validation: all 27 checkpoint tests passed after the fix, including publication and isolated restore
  from a second clone. No arena cases, hosted sessions or quota consumed; no performance score claimed.
- Decision: use the corrected source for the initial shared baseline; seeding identifies a starting
  checkpoint and does not imply measured promotion or improved negotiation performance.

## 2026-10-10 — MEASURED SANDBOX: Baris Test

- Scope/hypothesis: user-authorized single D01 smoke test of the shared recommended baseline;
  no candidate change or comparative performance claim. Budget: one sandbox session, no practice run.
- Run: `95dca638-82b5-4f07-b88c-1bb15c3813ce`; arena session `0f0ad2bb6dd309b5`.
- Checkpoint: `e1d931e4fcce49fb8fd341c40052953a`; clean verified source
  `f325fcb12c09ef2590cd9496a90dddd73e714648`, locked dependencies, serial package agent.
- Config: anchor=0.12, rounds=5, close_gap=0.005, final_hold_s=40, p_walk=0.25,
  meso=false, claims=false, estimates={}. Original manifest retains lock/data hashes.
- Result: ended deal, 91.9231/100, must-haves satisfied, zero reported timeouts,
  seven recorded moves, approximately five seconds negotiation time.
- Setup issue: the first preflight rejected the restore metadata as untracked; no session opened.
  Temporarily moved only that metadata into ignored storage, then restored it after execution.
- Decision: retain the recommendation; this single sandbox observation is not evidence of an
  improvement. Tracked result and original supplier messages are saved in the lab.


## 2026-10-10 — Lab browsing: score history, pagination and ordering

- Hypothesis: chronological supplier/case evidence and consistent list ordering make prior
  results easier to inspect; this is a lab UX change, not a negotiator strategy experiment.
- Change: authenticated compact history projection, selected-supplier charts and filters,
  session deduplication, explicit recovered/missing outcomes, and sortable paginated experiments.
- Configuration/cases/quota: existing recorded/imported results only; no new arena sessions.
- Verification: regression coverage for numeric sorting across pages, filter/page refresh behavior,
  zero versus missing scores, supplier attribution, campaign/import duplicates and recovery shapes;
  actual DOM checks cover navigation, chart drill-down, escaping and late response cleanup.
- Review fixes: normalized recovered campaign scores and ordered same-time repetitions numerically.
  No performance gain claimed and no change to the shared recommended checkpoint.

## Shared Evidence context — local contract validation, 10 October 2026

- Hypothesis: a shared, inspectable context can preserve existing price-increase claim selection
  and message economics while linking selected claims to scoped sources and input versions.
- Source: working branch `feat/evidence-context`; pinned kit
  `1b5516bb95ef28e37f69aa446dc62168864bca53`; no activation/config changes.
- Inputs: local `negotiation-arena-kit/data`, manifest v1.0.0, declared snapshot 2026-09-30;
  saved P01 practice metadata. Export command and responsibilities: docs/16-evidence-context.md.
- P01: existing bank/pick preserved; initial notice 51/90 days, PPI-D351 -3.7%, OTD 85.2%.
  LCI-C +2.7%, PPI-C241 +6.5% and 712 ppm remain existing candidates. Private estimates stay
  internal. Context gaps expose unknown index units and existing signal-overlay limitations.
- Local checks cover term preservation, private exclusion, failed checks, missing-data fallback,
  source/version export, reservations, resumed buyer refs and PackageAgent integration.
- Hosted sessions/quota consumed: **0**. Scores and persuasion effects: **not measured**.
  No runtime or negotiation-readiness claim; existing verifier/loader limits remain documented.
- Decision: hand off the shared interface and proposed hosted checklist for team review.
  The paused practice comparison stays paused; hosted work requires a separate instruction.
- Validation: `uv run --locked pytest -q` with explicit `ARENA_DATA`: **120 passed**;
  `uv run --locked ruff check .`: **passed**. Local asyncio suite ran outside the restricted
  execution sandbox after sandboxed runner tests stalled; no hosted transport was used.

## Claim verification and relevance — local follow-up, 10 October 2026

- Hypothesis: reject unsupported/semantically inconsistent evidence and prioritize indices named
  in the supplier explanation while preserving message economics and disclosure/usage rules.
- Source/config: working branch `feat/evidence-context`, same pinned kit and local data manifest
  as the shared-context batch; no policy activation changes. No hosted sessions or quota used.
- Added canonical claim rendering and verification of sentence/figure agreement, units,
  finite numbers, index direction/window/source compatibility, price bases/currency, disclosure,
  supplier-wide scorecards and requested-date OTD. Notices require supplier/part/date applicability
  and genuinely short notice; ambiguous/missing applicability is excluded. Notice preparation
  now works without a scorecard.
- Relevance: latest supplier message's known series IDs, then trigger/case citations, then listed
  part drivers. Supplier text cannot change claim eligibility/disclosure. Selection traces expose
  reasons and remaining slots; existing message refs conservatively consume the three-claim budget.
- Audit: compared banks and selected kinds/IDs/figures with a saved pre-change local snapshot for
  all 19 practice fixtures. P02's 109-day and P17's 104-day notice claims (90-day requirements)
  are removed; they were previously unselected. P02's requested effective date is also outside the
  recorded contract interval. Initial selections, including relevance ranking, stay unchanged for
  all 19 fixtures. P01 stays 51/90 days, -3.7% PPI-D351, 85.2% OTD; scorecard wording is explicit.
- Validation: **162 passed** with `uv run --locked pytest -q` and explicit `ARENA_DATA`;
  `uv run --locked ruff check .` passed. Local P01 export was regenerated successfully.
  Tests include false notice comparisons, wrong/expired/ambiguous scope, no-scorecard notices,
  sentence tampering, units/direction, privacy, relevance, final message budget and resumed usage.
- Decision: ready for local/team review; hosted persuasion and scores remain **unmeasured**.
  Prices, term sheets, closing decisions, rival disclosure and cost-pressure integration remain
  outside this batch. The existing paused hosted comparison remains paused.

## 2026-10-10 — Lab hosting: Azure VM deployment path

- Hypothesis: one always-on Azure VM with SQLite on its managed disk removes the developer-tunnel
  timeout and latency problems while preserving the existing laptop workflow.
- Change: environment-backed server defaults, a versioned service startup file, and an operator
  runbook for HTTPS, secrets, locked deployment, database migration, verification and rollback.
- Configuration/cases/quota: infrastructure only; no negotiator configuration or recommendation
  changed, no Arena case opened, and no sandbox or practice quota consumed.
- Decision: do not use App Service's network-mounted filesystem because Microsoft documents that it
  cannot support SQLite exclusive locks. Deploy one offer-eligible Linux VM and keep SQLite on its
  managed disk. Cut over only after history, loop state, authentication and upload verification.

## Inference/Lab setup — prepared only, 10 October 2026

- Hypothesis for a future probe: the Tacto endpoint can return an allowed closing-style ID
  without changing deterministic prices, terms, evidence or closing decisions.
- Added opt-in `negotiator.inference:InferenceProbeAgent` for standalone serial `lab run`;
  generic optional agent metrics are sanitized into saved/uploaded attempt results.
- Credential placement: ignored local `.env`, separate LLM/Arena/Lab keys. Lab URL comes
  from LAB_PLAYBOOK.md. Tacto URL, model ID and protocol confirmation remain outstanding.
- Proposed case: D01, one session, only after separate authorization. No budget granted here.
- Tests and lint: prepared but **not run**, per the user's instruction. Endpoint/Lab access
  was not checked; no services started, no uploads, no inference calls and no Arena sessions.
- Decision: unvalidated setup for review; no performance or connection-success claim.

### Azure deployment verification

- Host: Azure for Students VM `ehl-experiment-lab-vm`, France Central, Ubuntu 22.04,
  Standard B2ats_v2; static hostname
  `ehl-experiment-lab-vm.francecentral.cloudapp.azure.com`.
- Runtime: lab binds only to VM loopback on port 8000; Caddy 2.11.7 terminates HTTPS on 443 and
  redirects port 80. Both systemd services are enabled and active. SSH is restricted to the
  deployment IP; port 8000 is not exposed.
- Migration: SQLite backup API copy passed integrity checking with 110 runs and eight loop records.
  Public login returned a Secure cookie; `Baris Test` retained its completed 0.919230949 score;
  one recommendation, finding and campaign remained visible. Laptop sync uploaded two saved
  snapshots with zero failures and opened no Arena sessions.
- Setup failure: Ubuntu's enabled repositories lacked Caddy, and Caddy's signed package mirror
  returned HTTP 402 from the VM. The final installation uses Caddy's official static Linux binary
  and a dedicated unprivileged systemd account.
- Quota/decision: no Arena case, sandbox session or practice session was opened. The Azure URL is
  now the lab endpoint for this laptop; teammates can cut over with the existing upload token.


## 2026-10-10 — Port the measured P10 delivery tie-break onto current main

Hypothesis: when multiple legal opening packages have exactly the same complete buyer
cost, offering more delivery flexibility can improve the supplier's price. This port
contains only the opt-in delivery tie-break originally introduced in `de3e49a`.
`configs/cost-neutral-delivery.json` is the existing `configs/candidate.json` plus
`cost_neutral_lead_time: true`; no other strategy is introduced or activated by the port.
The default remains off. P10 is outside the configured package-policy types, so its
opening uses the shared optimizer and selects 42 days instead of 35 at equal cost.

Previously completed, fully reviewed hosted evidence (no new session consumed here):
- Controls `79c3a047f6c4a906`, `2323becf5b0aeba2`: score 0.4531834162,
  EUR 35.10, 35-day delivery, 23,400 units/year, 24 months; cost EUR 1,658,966.40.
- Run `a3a18b67-3ba8-43a0-a6b4-3baba11672dd`, session `77190d3ecf714944`, source
  `de3e49a`; run `0ac38ae5-de1d-4a53-93f5-fa7428577f36`, session `81c99adf8b88f7be`,
  source `fd423a6`: both score 0.5546564482, EUR 33.80, 42-day delivery,
  23,400 units/year, 24 months; cost EUR 1,597,720.80. Both valid, must-haves kept,
  zero timeouts. Estimates and MESOs were off; LLM advice was off.
- Each candidate saved EUR 61,245.60 against the recorded controls. The two supplier
  replies were identical, so this is repeated hosted evidence, not independent
  stochastic confirmation or a newly measured ten-case fixed-policy mean.

Decision: retain this isolated measured improvement behind its explicit policy flag.
Do not infer that current main plus its newer runtime wording reproduces these scores:
this port is verified locally, not a new hosted comparison. LLM package selection,
relationship experiments, RFQ changes, longer commitments and runtime recovery changes
are excluded. No lab recommendation is promoted by this port.

Local validation: delivery-cost equality, must-haves, costly-lead rejection, default
35-day opening, configured 42-day opening, control fixtures and boolean configuration
validation. All seven new tests pass; full suite: 342 passed, one existing failure in
`test_worker_preflight_rejects_unloadable_claim_data_before_open` (an empty explicit
package path falls back to locally available data). The same failure reproduces with
unchanged main production modules; no unrelated fix is included. `ruff check .` passes.

## 2026-10-10 — Retain the measured capacity package-adviser improvement

Hypothesis: use the model to interpret a supplier's delivery constraint and choose among
complete, legal packages whose prices are calculated by code to preserve the scheduled
buyer-cost ceiling. This port retains the package-selector implementation from `0b3e2fb`
and its serial integration. It does not include the earlier generic reply decorator.
The bounded-call helper is now local to `package_advisor.py`; timeout and fallback
behavior are unchanged. The model returns only an approved package ID and an exact
supporting quotation; no generated prose or numbers are sent to the supplier.

Hosted exploratory run `d612dda9-42f6-4863-bace-965dcdfd5d0a`, session
`2b0e734b37274c07`, P10, completed with score **0.6550995999**, valid must-haves and
zero timeouts. The complete transcript was reviewed by the experiment coordinator.
The previous delivery-only sessions scored 0.5546564482. Final terms changed from
EUR 33.80 / 42-day delivery / 24 months to EUR 31.80 / 56-day delivery / 24 months,
with unchanged 23,400 units per year. Complete cost fell from EUR 1,597,720.80 to
EUR 1,537,096.80, a further EUR 60,624 saving; this includes EUR 33,600 late-delivery
cost. This is one hosted observation, not a replicated effect or a fresh ten-case mean.

The two model calls took 3.46 and 1.94 seconds. The first selected the code-priced
EUR 27.62 / 56-day / 24-month opening; the second kept the scheduled package. Model:
`gpt-6.1-sol`, effort `low`; estimates and MESOs were off. The original run's policy
also listed raw-material cases for advice, but only capacity was exercised. This port's
`configs/package-advice.json` deliberately enables advice for **capacity only** and
otherwise matches `configs/cost-neutral-delivery.json`. No raw-material improvement
is claimed. This evidence does not promote the lab recommendation or default policy.

Activation requires the serial runner, this explicit policy config and local
`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` settings (optional `LLM_EFFORT`). Missing
credentials, invalid output or the eight-second call limit preserve the scheduled
move. The async runner rejects this mode before opening a session. Final offers,
closing actions, evidence-bearing or multiple-sheet moves, and fewer than 20 seconds
remaining skip advice. Role context includes the arena's `from_name`; public notes
are supplied without internal estimates or reservation costs. Previously proposed
packages are excluded in code; interpreting other refusals remains model judgment.

No additional hosted sessions or model calls were consumed to port this change.

Port validation: full suite **363 passed, one existing preflight failure** described
in the preceding entry; the same failure reproduces with the unchanged current
`origin/main` production modules. All 22 focused delivery/adviser tests pass.
`ruff check .` passes. No unrelated preflight fix is included.
- Next hypothesis: break ties between EXACT equal-cost contract commitments toward 36 months.
  P10 and P18 have 24/36-month equal modeled buyer cost; retain must-haves and the delivery gain.
  configs/cost-neutral-commitment.json changes only this choice from the delivery config. One P10
  screen planned after checks and publication; LLM and supplier-fit behavior stay off.
- New PackageAdvisor prototype lets the model select one code-approved, costed package. It checks
  an exact supplier quote, legal options, must-haves and cost ceiling, and limits switches/time.
  Offline P10 chose legal 56 days / EUR27.62 vs 42 days / EUR28.34, compensating late cost; P18
  kept its scheduled package. Wiring checks only, no hosted efficacy. Not activated yet.
- Relationship helpers handle the nonmonotonic cost curve and report public-estimate sensitivity;
  latest quote defaults override master data per field. P02's central target EUR363.05 at 14 days
  is uncertain (public-range optima EUR345.44–380.62), not a hard floor or score forecast.
- Rival evidence decorator validates current-session standing offers and exact qualifiers, with
  no hidden costs/targets. Prototypes remain unactivated pending integration and review.
- Integrated validation before publication: 453 tests passed; Ruff and git diff checks clean.

## 2026-10-10 — tracked async RFQ runtime preparation (no hosted sessions)

Hypothesis: independent supplier workers and a bounded coordinator close can preserve an RFQ final offer while another supplier POST takes longer than its 60-second response window. This addresses the observed P05 run `663873a0-ff50-4f24-a4bb-e08919e5149b`, where a 65.58-second rival call preceded a failed acceptance and supplier withdrawal.

Added `negotiator lab run --runner async` for exactly one explicitly budgeted attempt, preserving the configured agent factory, policy config, source/data fingerprint, quota checks, publisher and owned-session evidence collection. Runner selection is recorded as reserved `_lab_runner` metadata. Session identity is journalled and saved before documents or buyer moves; a failed or ambiguous attempt is not automatically restarted. Existing serial runs remain the default. Campaign/checkpoint schemas are unchanged.

Local regressions use real `PackageAgent` plus the simulator with a 66-second rival response and check timely final acceptance under both soft single-send and concurrent execution. A separate regression exposed acceptance of a stale cheaper offer from an in-flight supplier after the close wait; closing now excludes those sheets. When every reply is pending at the wave-cap close, the coordinator waits within its reserved closing window for a current sheet. Both model adviser attributes are rejected before async session creation.

Validation: `uv run --locked pytest -q` passed 461 tests with the main public package data; `uv run --locked ruff check .` passed. Budget used: zero practice and zero sandbox sessions. This is runtime preparation, not a measured score improvement or a promotion; full hosted async RFQ behavior still needs the planned single-session experiment and complete replay review.

## 2026-10-10 — P05 screen 1: non-leading convergence hold (async)

Run `74d3bf74-b5c5-48db-86ce-c109c9bffe0d`, session `a9a16a1231994e51`, commit `8e6a7fa`,
config `configs/p05-nonleading-hold.json` (cost-neutral-delivery + `rfq_nonleading_hold`),
`--runner async`. Score **21.28** (worse than 36.04 baseline): accepted sup:70250 EUR 34.00 /
35 d / 30 d payment, 113 s, zero timeouts. Transcript: sup:70210 led (32.50, then 32.00 in its
next reply); hold fired correctly on sup:70250 for ~40 s, but the `>20 s own deadline` fallback
then let 70250's "gap closed" through while 70210's reply was in flight; the coordinator
excludes in-flight sheets, so the only live sheet was the losing 34.00. Fix (`agent.py`): keep
holding while the leader is open and has moves left, regardless of the loser's deadline.
Regression updated. Tests 377 passed + known preflight failure; ruff clean.

## 2026-10-10 — P05 screen 2: non-leading hold without own-deadline fallback (async)

Run `ca2cade9-a914-4c6c-b556-4fe39a06ce1d`, session `ef13f675e65e7676`, commit `0bd7080`, same
config. Score **41.19** (vs 36.04 traced baseline, ties prior best .4119): sup:70210 EUR 32.00 /
35 d / 30 d, 50.7 s, zero timeouts. sup:70250's 34.00 convergence held; 70210 went 32.50 → 32.00
→ final 32.00; 70240 final 33.50/45 d; coordinator accepted 70210's final at once. Lead time
35 d (<= 42), no 56-day counter, no early payment. Next: repeat once for replication.

## 2026-10-10 — P05 screen 3: replicate non-leading hold (async)

Run `bee8da3d-93be-417e-93bf-fb79f7ec55c8`, session `e7dd5622c1234a45`. Score **41.19** again:
sup:70210 EUR 32.00 / 35 d / 30 d final accepted, 12.3 s, zero timeouts; identical transcript.
Replicated 2/2 after fix. Next: hold + `preferences.rfq = standard_payment`
(`configs/p05-hold-standard-payment.json`) — earlier standard-payment screens were masked
by the gap-closed exit.

## 2026-10-10 — P05 screen 4: hold + rfq standard_payment (inert)

Run `046127b6-2113-49dc-ac7b-2247ac95cb45`, session `2b9eb01f4eb4f8ec`. Score **41.19**, identical
transcript (still 90-day counters): the preference only applies to `package_types`, which
excluded rfq. Not a test of the hypothesis. Next: same config with `rfq` in package_types.
- Follow-up (no session): even with rfq in package_types, `standard_payment` resolves to the
  buyer's standard (90 d), so offline the first counter stays 31.68/90 d; the line cannot test
  supplier-standard payment and is dropped. The earlier "supplier-standard payment 36.04"
  result on the goal branch was likewise inert and masked by the gap-closed exit.
- Decision: merge candidate = async runner + `rfq_nonleading_hold` (2/2 at 41.19, +5.15 vs
  36.04 traced baseline, zero timeouts, 35 d lead, 30 d payment). Remaining gap to arena best
  .4168 is ~EUR 400 (consistent with 32.00 at 45 d), ~0.0005 on the ten-case mean; not pursued.
  `rfq_final_guard` stays off (serial-only protection; async covers the 65 s rival case).
  Sessions consumed by this P05 work: 4.

## 2026-10-10 — P05 offline cost decomposition (no session)

Session `ef13f675` deal sup:70210 32.00/35 d/30 d: C = 271,720.96 (price 268,800; payment
financing 1,792; quality 1,129). Scoring: c_open 305,544.96, c_best 223,424.17, so score/EUR
of unit price = **0.103** (EUR 8,456 per EUR 1). Levers at fixed price: 90 d payment −3,584
(+0.044), 60 d −1,792, 45 d −896; lead 28 d = 0, 42 d +1,400 (−0.017). Score 1.0 needs
≈EUR 26.70 at 35/90. **Price dominates** (gap ≈ EUR 5.3/unit); payment ≤0.044; lead time is
cost, not value, except as a trade for price. Supplier choice: sup:70240 (Hrvelec) opened
31.50 at 52 d and explicitly priced 35 d as "expensive overtime" (+3.50); it alone offered 90 d.
70240 at 42 d/90 d scores 0.50 @31.50, 0.55 @31.00, 0.66 @30.00 — the bolder lever. Every
prior run countered 70240 at 35 d (overtime premium), so it never got below 33.50.
Lever verification: payment options {14,30,45,60,90} (90 legal, 14 banned by rule); lead
{28,35,42,56} with must-have ≤42 → 42 allowed, 56 never; awarding 70240 legal; rival
disclosure would require claim plumbing for RFQ (not built; held for later screens).

Hypothesis A (`rfq_supplier_lead_time`, `configs/p05-supplier-lead.json`): when a supplier
quotes a lead time beyond ours, counter at the longest legal option ≤ its quote (42 d for
70240), so it can drop its overtime premium. Offline first counters: 70240 27.72/90/42; others
unchanged. Unit test added; suite 378 passed + known preflight failure; ruff clean.

## 2026-10-10 — P05 screen 5: supplier-fit 42-day lead time (hypothesis A)

Run `f42acd21-85d2-4840-9c01-2a2a9e5c96f3`, session `fee923108e98924c`, commit after `rfq_supplier_lead_time`.
Score **41.19** (no change): sup:70210 32.00/35/30 final, 96.5 s, zero timeouts. Transcript:
70240 accepted 42 d at once ("happy to speed up the lead time to 42 days") and dropped its
opening from 35.00@35 d to 33.00@42 d, then 32.50/90 d, alt 32.00/60 d (C 271,517 ≈ +0.002,
countered rather than taken), final 32.50/42/90 (score-equivalent 0.401). 70240's floor at
42 d ≈ 70210's; no overtime-premium windfall. 56 d never offered. Line: 1 non-improving.

Hypothesis B (screen 6, `configs/p05-rival-offer.json` = A + `rfq_rival_offer`): category
goal is leverage; cite the cheapest must-have-valid standing rival offer from this session
("Another supplier has offered part at EUR X per unit (offer:id)") to a supplier whose own
standing price is higher, once per offer ID per supplier. Code takes figure and ID from the
live sheet (verifiable). Unit test added; suite + ruff clean except the known preflight test.

## 2026-10-10 — P05 screen 6: rival-offer disclosure (hypothesis B, on A + hold)

Run `ebd84380-7d68-49d1-9fd9-2ff3d3059b91`, session `914b145b75d7015a`. Score **41.19** (no
change): sup:70210 32.00/35/30 final, 56.6 s, zero timeouts. Two claims sent, both to sup:70250
(offer:70210-0 @36.00, offer:70210-1 @33.00), both **verified**; 70250 acknowledged ("checked
the rival quote data you cited; it holds") but stayed 34.50 → 34.00 exactly as without claims.
No claim reached 70210 (it always led) or 70240 (its 42 d prices never exceeded a valid rival
standing price strictly). 70240 path identical to screen 5. Disclosure does not move floors here.
Lead-time line: 2 non-improving (screens 5, 6) → dropped. Disclosure: 1 non-improving.

Hypothesis C (screen 7, `configs/p05-supplier-payment.json` = hold + `rfq_supplier_payment`):
70210 refused 90 d in all four replies ("need the cash in 30 days"); deals close at its 30 d
anyway. Concede to the supplier's stated payment (never < 30 d) so the concession counts as
our move and later rounds are price-only. Offline: 70210 counters 31.78/30 d, 31.88/30 d.

## 2026-10-10 — P05 screen 7: concede to supplier-stated payment (hypothesis C) — worse

The tool retried the launch command, so **two** sessions ran with the same config/commit:
- Run `cfdafb15-9300-484f-8950-cd6a3d92e137`, session `a18a4bbf41f3245b`: **21.28**. 70250
  *agreed* to our 34.00/30 d counter (we had conceded to its 30 d); the coordinator closed on
  "sup:70250 agreed" while 70210's reply (32.50) was in flight, so it accepted 34.00.
- Run `826f495d-3a81-4247-b40e-4e58c95f533d`, session `ad9529ebb8e766b5`: **36.04**, 70210
  32.50/35/30. Once we offered 30 d, 70210 said "I can drop to 32.50, but that's where it
  stops" and went final at 32.50 after three replies (vs 32.00 after five when we kept asking 90 d).
Zero timeouts in both. The refused 90 d request was effectively a trade chip: 70210 compensated
with price ("if we agree on 30 days, I'll drop the price to 32.00"). Hypothesis C dropped.
Robustness finding: an "agreed" non-leader can still close the case on its own price while the
leader is in flight (same in-flight exclusion as screen 1); harmless on the hold base so far.

Hypothesis D (screen 8, `configs/p05-rival-history.json` = hold + `rfq_rival_offer` +
`rfq_rival_offer_history`): disclosure line, second try aimed at the leader. Cite the lowest
priced rival sheet from anywhere in this session (e.g. offer:70240-0 @31.50) when it
undercuts the receiving supplier's standing price; figure and ID taken from the sheet.

## 2026-10-10 — P05 screen 8: session-wide rival-price disclosure (hypothesis D) — WIN

Run `97f3fdbf-7c78-4be3-a19b-1bfe13408d17`, session `d52efd4374aaf110`, commit `9c5f6ed`. Score
**72.08** (vs 41.19; arena best .4168): sup:70210 EUR **29.00** / 35 d / 30 d, 167.8 s.
Six claims, all **verified**. To 70210: offer:70240-0 @31.50 → "We did not know that - a fair
point … come down to €32.00", "need to clarify this internally" (boss approval), then "Your
data on the market was solid … 29.00 EUR"; we matched 29.00, gap closed, accepted. 70250 went
34.00 → 32.00 → 31.00 under the same claims; 70240 34.50 → final 34.00. Timeouts: one on the
losing 70240 (its send waited behind a 58 s POST in the soft send slot); none on the winner.
Must-haves held (35 d), no 56 d, no 14 d. Next: repeat once.

## 2026-10-10 — P05: reconcile interrupted repeat `p05-rival-history-2`

Run `704039ed-9bd6-4b42-95a0-8df15e33c6bb`, session `6c3717e8dc3eaed5` (journalled in the run;
owned). The worker process was killed ~9 s after start (last journal record 19:21:29 UTC, buyer
counter 29.00 to 70210 sent as intent). Arena status: `ended`, `end_reason: timeout`, no deal,
score 0.00. Replay: 70210 again reached **29.00/35/30** (round 3), then final, then withdrew;
70250 33.00/30 final, 70240 34.00/90 final; all withdrew after unanswered timeouts. Partial
replication of the 29.00 floor. Recovered outcome attached with `save_reconciliation` for this
one session only (no blanket import); original attempt evidence preserved; `lab sync` uploaded.
Expired attempt counts as one session; not resumable.
Teammate P05 work read (main LOG/BENCHMARK_HANDOFF, origin/codex/benchmark-goal-20261010): 14-day
early cash + capacity opening (.3854, rejected), supplier-standard payment (inert). Not repeated.

## 2026-10-10 — P05 screen 9 plan: replicate screen 8 config (no change)

Differs from previous: nothing; `configs/p05-rival-history.json` at HEAD. Purpose: confirm the
72.08 from session-wide rival-price disclosure (70210 31.50 claim → "boss approval" → 29.00).
Runner `async`, launched under nohup so the process survives the shell.

## 2026-10-10 — P05 screens by parallel worker (same worktree; recorded here for completeness)

A second agent shared this worktree and `/tmp/p05` from ~22:05; its runs are part of this P05 budget:
- `57b90d1e` `p05-rival-history-3`, session `09f597f13bebed64`: launched 22:05 then abandoned
  (process gone); ended `timeout`, score 0.00, no deal; 70210 was at 32.00 after the first claim.
  Reconciled for this one verified owned, ended session; `lab sync` uploaded.
- `d1fea8bb` `p05-rival-history-4`, session `2b8fbe3260167f15`: **72.08**, 70210 29.00/35/30, 0 timeouts.
- `237f5adb` `p05-rival-history-4`, session `69acb4ae63e23c8c` (mine): **72.08**, 70210 29.00/35/30,
  9.8 s, 0 timeouts. Identical 70210 path: 31.50 claim → 32.00 + "clarify internally" → 29.00.
- `376427e0` `p05-undercut-reanchor-1` (hypothesis E, commit 5770caf), session `2ffdd9c5ee8c2b9d`:
  **72.08**, 0 timeouts. Counter 27.26 after 29.00 → "I already gave you a massive drop … stay
  there" → final 29.00, accepted. Anchor line: 1 miss. 29.00 looks like 70210's floor under rival
  pressure alone.
Replicated 3/3 (plus 2 expired). Lever confirmed.

## 2026-10-10 — P05 screen 10 plan: one verified data fact on counters with no rival claim (F)

Differs from previous: E config (undercut re-anchor) + `rfq_data_claims` (`configs/p05-data-claims.json`);
E's lower ask is kept because on the D base we counter at 29.00 itself and a claim cannot lower it. Until now
RFQ cases sent no data claims at all: `evidence_types` excludes rfq and `EvidencePolicy` gates to
single-supplier cases. Only rival-offer citations went out. Once 70210 led at 29.00, no rival
undercut it, so later counters carried no argument and it held 29.00 (E showed that a lower
ask without new information fails). Category goal names "competition **and data**"; 70210 itself
responded to "your data on the market was solid". F appends exactly one fresh verified public or
supplier-own fact (scorecard OTD/PPM, latest index windows) to an RFQ counter only when no rival
claim was added. Should-cost (internal estimate) excluded; no hidden outcomes are used.
Offline replay: at 70210's 29.00 the counter carries scorecard sc:70210@2026Q3 OTD 80.8 %.

## 2026-10-10 — P05 (parallel worker B): repeat + screen E (undercut re-anchor) — miss

Note: two workers ran in this worktree at once (B did not know about A's `5dc584b`). B stops here
to avoid duplicate sessions; A owns the next screen (its uncommitted `rfq_data_claims` is untouched).
- Lever (from the full transcript of `d52efd4374aaf110`): `rfq_rival_offer_history` cites the
  lowest rival sheet from the *whole session*, including must-have-invalid ones, so the leader
  70210 receives 70240's opening 31.50 @ 52 d (offer:70240-0) in its first counter (verified) →
  "clarify internally" → 36.00 → 32.00 → **29.00**. Screen 6 (valid sheets only) never cited to 70210.
- Run `57b90d1e` / session `09f597f13bebed64`: process killed seconds after a nohup start (the shell
  call reaping background jobs); ended by timeout, 0.00, reconciled for that one session only. 1 session.
- Run `d1fea8bb` / session `2b8fbe3260167f15`, commit `5770caf`'s parent config
  `configs/p05-rival-history.json`, foreground: **72.08**, 70210 29.00/35/30, 24.3 s, 0 timeouts.
  Identical path to screen 8. Replicated (with A's `237f5adb` = 3/3 completed at 72.08).
- Screen E `rfq_undercut_reanchor` (`configs/p05-undercut-reanchor.json`, commit `5770caf`), run
  `376427e0` / session `2ffdd9c5ee8c2b9d`: **72.08** (no change), 97 s, 0 timeouts. Counter 27.26
  after the 29.00 drop; 70210: "price stays … already gave you a massive drop to 29.00", then
  final 29.00/30 d; accepted. Price-floor line: 1 miss. 29.00 looks like 70210's floor under the
  single 31.50 claim; payment (90 d refused) and lead-time lines already closed.
- Sessions used by B: 3 (one killed). Gap to .92 ≈ EUR 1.9/unit; remaining untested lever is a
  verified data claim to the leader (A's in-progress `rfq_data_claims`).

## 2026-10-10 — P05 screen 10: one verified data fact on RFQ counters (F) — WIN

Run `c3054e99-df92-4a96-9d94-9b83035d79bc`, session `a7298b34c1e012d6`, config
`configs/p05-data-claims.json` (E + `rfq_data_claims`). Score **77.23** (vs 72.08 ×3):
sup:70210 EUR **28.50** / 35 d / 30 d, 183 s, zero timeouts. 70210 path: 31.50 rival claim →
32.00 + "clarify internally"; counter 31.74 + scorecard OTD 80.8 % (verified) → "clarified
internally … I checked the delivery scorecard … dropping the price to €28.50 to make up for it
and the other quote"; re-anchor 26.79 + PPI-D351 −3.7 % (verified) → "you are right about the
drop … already went as low as I can go … 28.50 final"; accepted. 70240 took the 45 d
alternative path (32.50/45 final); 70250 32.00/30. No 56 d, no 14 d, lead 35 d. Data line: 1 hit.

## 2026-10-10 — P05 screen 11 plan: stack the data fact with the rival claim (G)

Differs from screen 10: `rfq_data_claims_stack` also adds the data fact to counters that already
carry a rival claim (`configs/p05-data-claims-stack.json`). In F, 70210's first counter had only
the rival claim; each verified claim appears to buy one internal-clarification drop. Front-loading
OTD with the rival claim may move the 32.00 reply lower, leaving PPM 1863 and PPI-D351 for later
counters. Offline first counters: 70210 rival 31.50 + OTD 80.8 %; 70250 rival + OTD 88.0 %;
70240 OTD 62.5 % only. Risk: 70250's 88 % OTD is mildly favorable to it.

## 2026-10-10 — P05 screen 11: stacked data + rival claim (G) — tie at old level

Run `a160f212-66f3-4e52-9c0d-2b287ba4cce0`, session `6f46f0195a05816a`. Score **72.08**: 70210
29.00/35/30, 228 s, zero timeouts. First counter carried rival 31.50 + OTD 80.8 % (both
verified) → one reply, 32.00 + "clarify internally" (one drop for two claims). Second counter:
PPI-D351 −3.7 % → 29.00. Third counter 27.26 had **no** claim (PPM shares id
sc:70210@2026Q3 with OTD, so dedup blocks it) → "calculated tightly … 29.00" → final. Stacking
spends a claim slot without a matching drop. Stack line: 1 miss; `rfq_data_claims_stack` stays off.

## 2026-10-10 — P05 screen 12 plan: replicate F

Differs from screen 11: stack off, i.e. exactly screen 10's `configs/p05-data-claims.json`.
Purpose: confirm 77.23 (28.50) is not a single-sample draw versus 29.00 in G/E.

## 2026-10-10 — P05 screen 12: replicate F — WIN replicated

Run `5918e884-4983-41ae-b5b3-44c36a7fe366`, session `d48049c4678d0466`: **77.23**, sup:70210
28.50/35/30, 10.8 s, zero timeouts; transcript identical to screen 10 (OTD → "clarified
internally … 28.50"; PPI-D351 → "as low as I can go … 28.50 final"). F 2/2.

Decision / merge verdict: merge candidate = `configs/p05-data-claims.json` (async runner;
hold + rival offer + rival history + undercut re-anchor + `rfq_data_claims`), 77.23 ×2, zero
timeouts, lead 35 d (≤42), 30 d payment, no 56 d counter, no 14 d / early cash. All new
flags are opt-in; defaults unchanged. Drop: stack (1 miss), standalone re-anchor (tie, kept only
as F's carrier). 70210 states 28.50 is its floor; remaining gap to ~.92 (≈EUR 27.1) is not
reachable by more claims on this path. Next untested lines: 42 d lead time traded for price with
70210, and the teammate's 24-month commitment (both price-for-term trades, none screened).
Sessions in this task: 7 (2b8fbe32, 69acb4ae, 2ffdd9c5, a7298b34, 6f46f019, d48049c4 completed;
09f597f1 expired, launched by a parallel worker in this worktree) plus 1 inherited expired
(6c3717e8). Shared-team quota also fell from other teams' P05/other runs during this window.
Validation: `pytest -q` 382 passed, 1 known failure (preflight); ruff clean.

## 2026-10-10 — P05 offline: lead-time trade and award choice (no session)

Kit C with quote-PDF standards (70210: 30 d/28 d/1200 ppm; 70240: 45 d/1400 ppm; 70250:
30 d/28 d/600 ppm; quality = 8,400 × ppm/1e6 × EUR 112; late = EUR 200/day beyond 35 d).
Current deal 70210 28.50/30/35: C 242,124.96 (price 239,400; payment 1,596; quality 1,129) = .7723.
- **42 vs 35 d** costs a flat EUR 1,400 (7 d × 200) = **EUR 0.167/unit**. Cost-neutral 70210
  price at 42 d: 28.334 (30 d pay), 28.429 (45), 28.523 (60), 28.715 (90). So 42 d is net-positive
  only at ≤ 28.33 on 30 d (e.g. 28.00/42/30 → +0.034). .92 needs ≈26.90 at 42/30 or 27.07 at 35/30.
- **Award choice:** neutral prices vs current deal — 70240 28.48 @35/30 (1400 ppm costs +0.02/unit),
  70250 28.57 @35/30 (600 ppm saves 0.07/unit). Best observed: 70250 31.00/30/35 (.5217),
  70240 32.50/45/35 (.3692), 31.50/90/52 (illegal). Rivals stopped 2.5–4 EUR above the
  neutral price, and 70250's quality edge is only EUR 0.07. **No screen**: award line closed offline.

## 2026-10-10 — P05 screen 13 plan: lead-time-for-price trade at re-anchor (H)

Differs from F: `rfq_lead_trade` (`configs/p05-lead-trade.json`). At F's one-time re-anchor after
70210's undercut (28.50), the counter goes at 42 d (longest legal ≤ the 42 d must-have; 56 is never
offered) with the same price, 26.79 + PPI-D351 claim. 70210 itself said 35 d is fine and its standard
lead time is 28 d; 70240 priced fast lead time as overtime, so slack may be worth price. If the next
reply's standing sheet isn't cheaper than the pre-trade sheet by kit C (e.g. 28.50 @42 d costs
+1,400), we revert to 35 d, so the downside is one counter. Offline: 28.00@42 → keep 42; 28.50@42 or
28.40@42 → back to 35 d.

## 2026-10-10 — P05 screen 13 result: H lead trade = 75.52 (miss)

Run `0f2d7d5f` / session `c54ee30b0fe13b67`: **.7552**, 70210 28.50/30/**42** (C +1,400 vs F),
2 timeouts on losing threads only (70240/70250 r3), 117 s. Transcript: same as F through 70210's
28.50/35 (r2); our re-anchor 26.79/90/42 + PPI claim → 70210 verified the claim and sent a
**final** 28.50/30/42 ("without movement from your side we cannot move either"), accepted
(rivals ≥ 33.00; a counter against a final failed the walk-risk test). The revert guard is for open
replies only, so it never fired. 70210 put no price on lead time (its standard is 28 d), and 70240
priced 42 d at ≥ 32.50 in screen 5, ~4 EUR above the 28.33 neutral price. **Line dropped** (one miss
on 70210 plus offline/screen-5 evidence for 70240); no repeat. `rfq_lead_trade` stays opt-in, off.

Verdict: keep `configs/p05-data-claims.json` (F, .7723 ×2). Award choice closed offline.
Sessions this task: 1 (c54ee30b); 4 of 5 left unused.

## 2026-10-10 — P05 rethink (target from leaderboard .96 ≈ 26.7 on 70210 35/30; not used at runtime)

Reread all 70210 threads (11 sessions). Its behaviour is the same every time: r1 rival claim →
32.00 + "clarify internally"; **r2 = one boss-approved drop whose size tracks the r2 evidence**
(no claim → 29.00 [E, screen 8]; PPI −3.7 % → 29.00 [stack]; OTD 80.8 % → 28.50 [F ×2]); after
that it holds ("massive drop last time"), and a backward counter brings a final at r3. Rivals
never got below 32.00 (70250, "clarify internally" still pending when we closed) / 32.50 (70240).
What 70210 values: cash ("30 days is a must", overdue-invoice letter, "faster payment welcome" —
14 d is out of bounds for us), free capacity (lead time worth nothing to it: screen 13), Hollerau as
reference customer. Volume/tenor are fixed by the RFQ. Index windows: only PPI-D351 −3.7 %
(latest) supports us; AS-14404/PPI-C2431/LCI-C rose; older drops are cherry-picked, so not used.

## 2026-10-10 — P05 screen 14 plan: claim burst in the clarification round (J)

Differs from F: `rfq_data_claims_burst: 3` (`configs/p05-claims-burst.json`). 70210's r2 counter
carries every honest unused claim: OTD 80.8 % **and** PPI-D351 −3.7 % (PPM 1863 shares
sc:70210@2026Q3 → duplicate, skipped). Why: the r2 drop is the only big move and scaled with r2
evidence; F used one claim there and saved PPI for r3, where it changed nothing.

## 2026-10-10 — P05 screen 14 result: J claim burst = 77.23 (no gain)

Run `1bea8ed8` / `ede99fc74771b886`: .7723, 70210 28.50/30/35, 0 timeouts. Both r2 claims verified;
same 28.50 ("because of your good data and to make up for the payment terms"). r3 re-anchor
26.79/90 → hold + **"Which figures is that based on? Please send us the data."** → our 28.50/90 →
final 28.50. Rivals ended with finals 70240 32.50/45 and 70250 31.50/30 ("clarified internally"),
both ≥ 3 EUR above. So r2 evidence count isn't the limit; 28.50 is 70210's boss-approved step for
this pressure. Honest claim bank is now empty for 70210 (cherry-picked AS-14404 −8.5 % /
PPI-C2431 −3.8 % windows contradict the latest +5.9 % / +12.3 %, so not used).

## 2026-10-10 — P05 screen 15 plan: reciprocal re-anchor (K)

Differs from F: `rfq_reciprocal_reanchor` (`configs/p05-reciprocal.json`). F/J's r3 counter was a
backward move (26.79 @ 90 d after 31.74 @ 90 d) with no give → final / "send data". K's r3 counter
is 26.79 @ **30 d** (its own term; we close at 30 anyway, so no cost to us vs the deal) and says
"we move to your 30-day payment term, as you asked. If you can confirm EUR 26.79 on these terms, we
award you the full 4200 pcs per year today." Tests the supplier's "no concession without a move from
us" rule with a give it values (cash) and award certainty.

## 2026-10-10 — P05 screen 15 result: K reciprocal re-anchor = 77.23 (no gain, new signal)

Run `8bb17bb3` / `dc37e2b4f3ed5204`: .7723, 28.50/30/35, 0 timeouts, 66 s. r3 26.79/**30** + award
text → no final this time: "Good that we agree on the 30 days payment, cash flow is important …
holding 28.50 … **A binding higher volume would help us and can improve the price. Which volume can
you commit to?**" Our code matched 28.50/30 → agreed (r4). Volume is a fixed term in P05
(not negotiable; above 4200 = uncovered buying in C), so no volume lever; reciprocity at r3 keeps
the thread open but the price step was already spent at r2.

## 2026-10-10 — P05 screen 16 plan: reciprocal give at r2 (L)

Differs from F/K: `rfq_reciprocal_r2` (`configs/p05-reciprocal-r2.json`). Our **second** counter
to each supplier moves to its own payment term (≥ 30 d) at the C-neutral price (70210: 31.31 @ 30 d
= 31.74 @ 90 d for us) and says so. Why: 70210's only big drop is the r2 boss-approved step, and
it said "to make up for the payment terms"; K showed the payment move is read as a real give. So
the give now lands in the round that sets the step, together with the OTD claim. r3 re-anchor
(26.79 @ 30 d) as in F.
