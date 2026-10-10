# Experiment log

Format and decision rule: `docs/04-experiments.md`. Newest on top. One entry per change.

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
# 2026-10-10 — Ece: repeated payment counteroffer response (planned lab comparison)

- Baseline: shared recommendation e1d931e4fcce49fb8fd341c40052953a, generation 1,
  source f325fcb12c09ef2590cd9496a90dddd73e714648; restored in an isolated worktree.
- Hypothesis: after two explicit primary supplier counteroffers repeat a faster payment term,
  switching our primary offer to that term at no greater total buyer cost will improve agreement
  economics on D02 without a material D01 regression. This is a hypothesis, not measured gain.
- Motivation: owned D02 session 2da225d3421b1101 repeatedly quotes 30-day payment while buyer
  offers 60 days. The prior MESO experiment regressed D02; this test changes only the primary
  payment response after repeated binding evidence, not the number of alternative packages.
- Change: payment_response helper consumes at most 64 events, requires two explicit matching
  post-buyer open counteroffers, checks permitted terms/must-haves, solves price deterministically,
  rounds down to cents and rechecks complete buyer cost. No prose interpretation or private data.
- Configuration unchanged: anchor .12, rounds 5, close_gap .005, final_hold_s 40, p_walk .25,
  claims false, meso false, estimates {}; serial runner, empty data manifest.
- Budget: one D01/D02 sandbox campaign, three repeats per case per arm, maximum 12 sessions;
  no practice allowance, no main merge. Family/campaign: ece-payment-response-20261010-01.
- Local validation and measured results will be recorded after checks and the campaign. No hosted
  session has been started for this candidate at the time of this checkpoint description.
- Local validation: full suite 260 passed in 38.23 seconds, Ruff clean. An earlier full run had
  two timing-sensitive failures (scaled slow-reply test and rate-limiter spacing); both passed
  in isolation and in the full rerun. Retain this timing caveat; no runtime changes in this candidate.
