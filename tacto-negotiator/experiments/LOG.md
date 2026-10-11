# Experiment log

Format and decision rule: `docs/04-experiments.md`. Newest on top. One entry per change.

## V2 evidence-to-economics causal comparison — local experiment, 10 October 2026

- Hypothesis: a canonical cost revision can affect admitted supplier estimates and official
  complete-cost comparison without modifying buyer economics or legal package terms.
- Source/config: `a88bf86` plus preserved working changes; source-cost-v1 explicit assumptions,
  unchanged pinned oracle and evaluator; existing relationship fixture buyer/terms.
- Cases: release cost43 versus case override47; unchanged price45/49 packages; exact-component
  parity, source-only revisions, irrelevant text, disabled estimates, missing assumptions,
  claims/conflicts/scope/basis/temporal failures and illegal package control.
- Assumptions: source cost mapped explicitly to full cost; declared point bounds, rates0.08/0.08,
  ppm0, extra0. Unknown uncertainty; no margin/reservation/preference inference.
- Quota: zero hosted/model calls. No negotiation score, strategy selection or promotion measured.
- Results: 25 direct pass; consumed DTO gate380 pass/483 unimplemented xfail; full scoped V2
  727 pass/603 unimplemented xfail. Ruff/frozen V1 replay pass. Complete costs: cost43 gives
  369,600 vs401,600 EUR; cost47 gives429,044.44 vs401,600 EUR, reversing the cheaper package.
  Disabled-estimate costs stay369,600/401,600; source-only changes preserve costs but change IDs.
- Limits: explicit single-part mapping, declared metadata only, no calibrated uncertainty or
  automatic scenario endpoints; multiple-scenario nominal ambiguity unchanged.
- Decision: retain bounded integration. Next connect evaluated finite legal candidates with
  independent used-action validation before grounded selection.
  [Completion/trace](../docs/v2/implementation-order-addendum-2026-10-10.md#k-t23-source-cost-estimate--t41-economics-verified-local-implementation).

## V2 direct economic package comparison — local component experiment, 10 October 2026

- Hypothesis: complete legal packages can be compared through one injected official oracle,
  preserving estimate/source attribution and separating legality from arithmetic.
- Source/config: `a88bf86` plus preserved working changes; pinned kit unchanged; explicit
  disabled/single-scenario modes. No V1/runtime/default changes.
- Cases: two P10 packages; existing relationship fixture price-order reversal; provenance,
  standard/fixed/sheet precedence, missing estimates/price, basis/options/must-haves and failures.
- Quota: zero hosted/model calls; no negotiation outcome, score or promotion measured.
- Results: evaluator 15 pass, evaluator+oracle 47 pass; D4 DTO gate 380 pass/483 unimplemented
  xfail; full scoped V2 702 pass/603 unimplemented xfail. V2 Ruff/frozen V1 replay pass.
  P10 costs 1,335,154.08 vs 1,368,754.08 EUR; relationship 45/unit costs 429,044.44,
  49/unit costs 401,600.00 EUR through the existing kit penalty.
- Limits: multiple robust scenarios lack a designated nominal estimate and fail explicitly.
  Value/margin diagnostics are absent from the oracle port. No selection/message certificate.
- Decision: retain bounded package evaluation; next connect source-cost estimate construction
  to direct package comparison. [Completion](../docs/v2/implementation-order-addendum-2026-10-10.md#j-t41-direct-package-evaluation-verified-local-implementation).

## V2 official arithmetic oracle — local parity experiment, 10 October 2026

- Hypothesis: the pinned kit provides a shared economic boundary without copying formulas or
  promoting evidence costs into authoritative buyer economics.
- Source/config: `a88bf86` plus preserved working changes; kit revision
  `1b5516bb95ef28e37f69aa446dc62168864bca53`; unchanged OfficialCostOracle interface.
- Cases: P10 packages/unit conventions, seven relationship points, commercial terms,
  delayed price, index/risk, fractional need, explicit estimate separation and failures.
- Quota: zero hosted sessions/model calls. No negotiation outcome or promotion measured.
- Results: direct adapter 32 pass; DTO gate 341 pass/522 unimplemented xfail; full scoped V2
  648 pass/642 unimplemented xfail. V2 Ruff/frozen V1 replay pass. All eleven components
  and rounded totals match the kit for admitted packages.
- Limits: one part/supplier; no legality certificate. A binary-float half-cent result conflicting
  with the Decimal component-sum contract is explicitly rejected. No substitute economics.
- Decision: retain the oracle; next implement direct package evaluation/comparison with its
  eight consumed contracts, without strategy or orchestration.
  [Completion](../docs/v2/implementation-order-addendum-2026-10-10.md#i-t41-official-arithmetic-verified-local-implementation).

## V2 resolved evidence cost projection — local contract experiment, 10 October 2026

- Hypothesis: the selected canonical cost revision can feed a typed economic input without
  promoting supplier assertions or replacing deterministic official financial calculations.
- Source/config: `a88bf86` plus preserved working changes; existing layered resolver and strict
  `negotiator-v2/1` EvidenceContext/ResolvedCostInput; no V1 flags or launch changes.
- Cases: applicable release EUR 140 versus case EUR 150; revision-only change; irrelevant
  supplier wording; source conflicts/missing/scope/kind/freshness/basis failures; units 1/100/1000.
- Quota: zero hosted sessions/model calls. No Lab campaign or promotion.
- Results: direct acceptance 29 pass; scoped full V2 550 pass/708 unimplemented xfail;
  three-new-symbol DTO gate 275 pass/588 unimplemented xfail. V2 Ruff/frozen V1 replay pass.
  Projection values and canonical hashes change with authoritative cost input/revision,
  and remain stable for unrelated wording. No negotiation score or calculated cost effect claimed.
- Limits: declared metadata/date checks do not verify source bytes or execute freshness rules;
  context error gaps conservatively block projection. Full estimates, claims and financial
  evaluation remain incomplete. Existing legacy failures remain separately classified.
- Decision: retain this bounded consumer; proceed to the existing T4.1 OfficialCostOracle
  adapter with direct kit-parity tests and only its required input/output contracts.
  [Completion](../docs/v2/implementation-order-addendum-2026-10-10.md#h-t23-cost-consumer-verified-local-implementation).

## V2 typed layered evidence resolution — local contract experiment, 10 October 2026

- Hypothesis: resolving canonical identity before applicability, with whole-record replacement,
  prevents stale base cost reuse and preserves the source revision needed for later economic
  and strategy decisions.
- Configuration/source: `a88bf86` plus preserved working changes; strict `negotiator-v2/1`
  models and direct LayeredEvidenceResolver, no V1 feature flags or runtime changes.
- Cases: synthetic cost `cost:310010` at base 132.64/release 140/case 150; source collisions,
  scope mismatches, replay/identity conflicts, statements/hypotheses and price units 1/100/1000.
  All inputs are local validated values; source metadata remains attributed, not new authority.
- Quota: **zero hosted sessions and zero model calls**. No Lab campaign or promotion.
- Results: 53 direct resolver/supplemental safety tests pass; owned remaining-DTO suite
  263 pass/600 explicit unimplemented xfail; scoped full V2 509 pass/720 unimplemented xfail.
  V2 Ruff and frozen V1 replay pass. No negotiation score, persuasion, or performance result.
- Failures/limits: no unexpected V2 failures at completion; legacy four-failure classification
  remains inherited. Freshness derivation, session/derived-layer priority, context/cost consumers,
  orchestration and live execution are incomplete.
- Decision: retain this offline increment. Next connect resolved revisions to the existing
  cost-input projection and direct economic evaluation; A/B component work proceeds together.
  [Completion and reproducible gate](../docs/v2/implementation-order-addendum-2026-10-10.md#g-first-t21-increment-verified-local-implementation).

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

### 2026-10-10 — V2 finite supplied-action boundary (offline)

Hypothesis: resolver-admitted source-cost changes can reverse official complete-cost ranking and
reach a replaceable strategy selector while independent validation still blocks inadmissible output.
Configuration: existing working checkout plus preserved earlier V2 increments; supplied EUR 45/49
packages, source-cost-v1 explicit nominal estimates, minimum-cost-test-v1; no model or live execution.
Cases: unchanged synthetic relationship fixture with source EUR 43/47 plus test-local adversarial
boundary controls. Quota: zero hosted sessions/model calls. Measured: EUR 43 selects EUR 45
(EUR 369,600); EUR 47 selects EUR 49 (EUR 401,600); both independently validated. Direct boundary
19 passed; scoped V2 944 passed/405 explicit missing-component xfails; frozen V1 replay exact.
Evidence: tests/v2/contracts/test_strategy_boundary.py and unchanged test_evidence_economics.py;
docs/v2/implementation-order-addendum-2026-10-10.md §L records gates and exact consumed closure.
Failures/limits: no unexpected scoped failures; full-parent acceptance, grounded interpretation,
claims/close validation, durable artifacts, orchestration and live proof remain incomplete.
Decision: keep as an offline test seam; no promotion or negotiation-performance claim.

### 2026-10-11 — V2 typed recorded inputs and bounded offline coordinator

Hypothesis: typed declared sources, quote standards, message history and server/state inputs can
produce a reproducible independently validated offline decision through replaceable ports,
without completing persistence or introducing negotiation heuristics. Configuration: preserved
working checkout plus §M components, source-cost-v1 nominal/disabled controls, input-echo-test-v1,
supplied-intents-test-v1 and minimum-cost-test-v1; fixed recorded clock. Quota: zero hosted
sessions/model calls. Cases: unchanged synthetic relationship fixture EUR 43/47 costs and EUR
45/49 legal packages; test-local stale/attribution/server/citation/forgery/expiry controls.
Measured: source EUR 43 selects EUR 45; source EUR 47 selects EUR 49; both end in valid offers
with exact message bytes and stable export/reload traces. Direct integration 28 passed;
scoped V2 1,013 passed/364 explicit missing-component xfails; frozen V1 first move unchanged.
Full repository check: 1,341 passed/19 skipped/364 xfailed/17 failures outside V2 in unchanged
legacy tests. Evidence: tests/v2/integration/test_offline_decision.py and addendum §M.
Limits: declarations/hashes do not independently authenticate source/server bytes; test
interpretation does not infer preferences; full fixture codec, research, model budgeting,
semantic grounding, durable records, claims/close validation and execution remain incomplete.
Decision: retain as an offline composition seam; no promotion, persistence guarantee or
negotiation-performance/live-readiness claim.

### 2026-10-11 — V2 Assignment 1 local consumer correctness

Hypothesis: joining public case facts and independently checking outgoing fields/price policy
prevents the review's incorrect source and incomplete-sheet admissions. Working tree a88bf86
plus preserved V2 work; unchanged official relationship fixture and fixed offline clocks/config.
No hosted sessions, inference, quota, checkpoint publication, commit or push.

Implemented only context join/source-version attribution, exact outgoing negotiated fields,
and economic price-policy enforcement. Seventeen regression cases pass; scoped V2 1,030 pass,
364 unfinished xfails; official parity 47 pass; V2 Ruff, frozen V1 replay and whitespace pass.
Decision: retain narrow consumer fixes; no intelligence or performance claim. The review's
0.05 policy bypassed the existing v1 cent-only model validator. Such policies now fail explicitly
at evaluation too; supporting 0.05 requires contract approval and is not claimed complete.

### 2026-10-11 — V2 Assignment 2 fake-transport interpretation

Hypothesis: strict grounded drafts and a decision-scoped ledger can admit attributed supplier
interpretation while preserving economic/validation authority and bounded fallback.
Working tree a88bf86 plus prior preserved V2 changes; fixed clocks and existing official
relationship fixture. Fake transports only; hosted quota/session/call/spend: zero.
No publication, commit, push, default activation or Assignment 3 implementation.

Exactly 15 gateway exports; injected async gateway, ledger, bounded GroundedInterpreter,
fallback and minimal coordinator trace integration. Direct tests 45 pass; scoped V2 1,137
pass / 302 unfinished xfails; consumed contracts 681 pass / 182 xfails. Existing interpreter/
budget selectors retain 19 absent-full-codec xfails. Ruff/replay/whitespace pass.
Eleven provisional semantic examples and a small evaluator were introduced; no independently
reviewed actual-model corpus result exists. Decision: plumbing locally verified, model quality
unmeasured. See docs/v2/assignment-2-completion-2026-10-11.md for bounds and remaining gaps.

### V2 Assignment 3 — offline grounded selection routing, 11 October 2026

Hypothesis: a grounded supplier condition can support a different officially affordable
registered offer or fixed question, while irrelevant language preserves minimum cost.
Configuration: grounded-selection-v1 / selector-response-v1 / injected fake test-model;
existing official arithmetic, supplied synthetic packages, exact template renderer and
independent validator; two calls, 2,048 total reserved tokens, one second total model time.
Working tree preserved; no checkpoint publication, hosted inference, sessions or spend.

24 scenarios / 12 pairs, eight frozen held-out examples; identical economic batches across
minimum/direct/interpreter+selector arms. All 72 actions independently validate. Provisional
set matches 14/24, 24/24, 24/24; scripted model arms each have ten grounded departures and
four selector fallbacks. Calls 0/23/46; unknown usage conservatively charged 0/11,776/23,552
reserved tokens. Latency/individual fallbacks and all traces: /tmp/v2-selection-pilot.
These fake outputs demonstrate routing/rejection, not strategic competence or a performance
advantage. Author labels await independent review; real-model understanding/outcomes unmeasured.

Decision: retain offline opt-in services; no activation/promotion. Grounding is deliberately
narrow, history bounded, confidentiality depends on explicit approved source content.
See docs/v2/assignment-3-completion-2026-10-11.md for implementation, regression gates and
minimal Assignment-4 contract handoff. Assignment 4 was not started.

### First V2 real-LLM readiness experiment — local preflight only, 11 October 2026

Hypothesis: a permitted supplier delivery preference can change an officially evaluated
P10 selection with economics and supplied alternatives fixed. Dataset p10-offline-llm/1,
SHA-256 ce7029a6689450dd3061b5203a44449630ee88b1f89e171ea4f921e9c72e2d7f.
Existing interpret/select prompts, injected chat-completions-json-v1 transport, official
oracle, independent validator; two calls/decision, proposed four calls and 65,536 total
reserved tokens for two inputs. Hosted allowance is NOT granted. Effective LLM key/endpoint/
model and provider/dataset authorization are missing; zero hosted inference calls.

Actual local HTTP mock rehearsal: both decisions valid, no fallback, four explicitly fake
calls. Minimum cost EUR 1,333,891.20; scripted 42-day preference selects EUR 1,335,154.08,
with exact source quote, while every official cost and candidate alternative stays fixed.
Artifacts: /tmp/v2-p10-local-rehearsal. No model competence or hosted compatibility claim.

Actual loopback Lab/Arena-simulator smoke: existing V1 PackageAgent, unchanged P10 case,
one local session, five rounds, zero timeouts, score 0.946157564710246; outcome published and
retrieved from temporary local Lab. Run 9e93d5bd-99d3-43cb-b38b-2a388a64c66b; captured source/
data/lock provenance and outcomes at /tmp/v2-local-lab-smoke. This verifies the Lab runner/
publisher, not V2 live execution. Read-only remote Lab metadata and Arena case-list checks
pass; P10 is practice, D01/D02 are sandbox. No remote sessions/actions/uploads.

Decision: prepared guarded hosted command, but do not run without exact provider/model/data
and absolute allowance approval. Do not begin Assignment 4 based on fake responses. See
docs/v2/real-llm-readiness-2026-10-11.md for runnable setup, transport/accounting assumptions,
remaining negotiation blockers and verification. Existing working tree preserved.

Final verification: **1,203 passed, 298 expected xfailed** in the complete consumed V2
scoped gate, including the two new adapters; **26 passed** in the focused readiness suite;
**167 passed** across Lab runner/server/policy/campaign/CLI/checkpoint/store tests.
Manifest: **1,501 expanded contracts**. Scoped Ruff, frozen V1 replay and whitespace checks
pass. The broader non-V2 regression run returned **350 passed, 14 failed**; every failure
matches the recorded `a88bf86-fixed-data` baseline in
`/tmp/v2-review-regression-comparison.json`. Its two prior Lab campaign failures pass with
the existing uv executable on PATH. No V1 or Lab production source was changed. The four
repository-wide Ruff violations remain inherited. Full legacy-suite success is not claimed.

## GPT-4.1 mini comparison preparation — 11 October 2026

Hypothesis remains that approved supplier language can change a grounded selection under
fixed official economics. Reviewed Assignment 2/3, hosted-readiness and starter-kit guidance.
Prepared one connectivity call, two P10 decisions, and existing 24-example three-arm comparison;
maximum 77 calls / 1,261,568 reserved tokens / $5. Direct OpenAI standard rates, $2.0185088
worst-case reservation charging every token at output rate; unknown and failed calls retain it.
All four LLM settings now present, configured model mismatch; no secret output or dotenv edits.
Added strict documented mini alias/snapshot mapping and experiment-only pre-call dollar guard.
No retries, Arena sending, prompt tuning, proposal generation, or validation bypass.

Local fake preflights saved at /tmp/v2-hosted-comparison-preparation. Full composed HTTP mock
check makes 74 calls; projection rejects the private-disclosure injection before three possible
calls. Existing fake-response benchmark preserves original labels/schedule; real-run semantic
summary separately excludes the two fake-fault-dependent forged labels. Eight held-out examples
remain frozen with independent human review pending. No real scores, latency or spend measured.
Explicit provider/model/projection/$5 approval still pending. See
`docs/v2/hosted-comparison-plan-2026-10-11.md` and the unsigned authorization template.

Follow-up final gate: **1,209 passed, 298 expected xfailed**; 32 focused checks, 1,507
manifest contracts, scoped Ruff/frozen V1 replay/whitespace pass. The user corrected the
model to gpt-4.1-mini; the effective configuration now validates. Hosted approval pending.

Actual approved hosted run completed: direct OpenAI gpt-4.1-mini → documented 2025-04-14
snapshot, 74 calls, 171,436 input / 10,856 output tokens, 117.80 s summed model latency,
zero timeouts/usage gaps, $0.085944 uncached usage estimate, $1.9398656 reserved of $5.
P10 minimum EUR1,333,891.20; preference EUR1,335,154.08 (+EUR1,262.88), both final valid
but both interpreter outputs rejected. Benchmark all three arms 14/24 provisional matches,
2/8 held-out, 12/22 semantic-subset matches; no benchmark language-driven action changes.
Direct selection 10/24 fallback decisions; grounded 15/24 selector fallbacks and 23/24
interpretation fallbacks, with all 24 relying on some model fallback. Interpreter admits
1/25 actual outputs; selection admits26/rejects23 including connectivity/P10. Three potential
calls blocked by private-disclosure projection. All76 decision traces verify; no prompt or
validator changes, retries, Arena actions or Assignment4. Exact artifacts at
/tmp/v2-hosted-comparison-first-run; results/failure attribution in
`docs/v2/hosted-comparison-results-2026-10-11.md`. Improve interpretation and safe rejection
diagnostics; independent human label review and exact rejected-field attribution remain
missing. One-time approval consumed; no further hosted experiment authorized.

## 2026-10-11 — V2 LLM stabilization and tracked local Lab integration

**Hypothesis:** explicit DTO-aligned prompts and admission diagnostics make rejected outputs
attributable without relaxing grounding, and the existing Lab can invoke the bounded V2
pipeline through its stable negotiator interface. Hosted admission/semantic improvement is
unmeasured and awaits a separately authorized experiment.

**Configuration/source:** existing dirty workspace preserved; no checkpoint/publication/promotion.
New versioned supplier/selection v2 prompts; optional DTO-derived strict response format;
shared bounded factory, local-only P10 Lab adapter and explicit `lab run --local-case` mode.
Each run preserves source patch/commit/lock/data hashes in its existing Lab snapshot. The
minimum/direct/grounded arms share the original three P10 packages and official evaluator.
Model: explicitly scripted local ambiguity/minimum fixture, not GPT-4.1 mini. Two-call,
32,768-reserved-token decision ceiling and fallback/submission reserves remain in force.

**Cases/ceiling:** three isolated official in-process Sim P10 sessions, one per arm, six
rounds each. Fourteen additional authored supplier-interpretation controls. Zero hosted
sessions, inference calls, remote action submissions or remote Lab writes. No previous
one-time hosted allowance reused. Additional local regression runs are fixture checks.

**Evidence/results:** final report `/tmp/v2-lab-stabilization-final/report.json`;
minimum run `c089eba7-6109-4e2f-8460-f7369be76e7f`, direct
`8fa9ad14-e2b6-4307-8d17-f0b5545603f7`, grounded
`12bf923e-ddee-4fe3-868e-628df57bbff3`. Actual Lab CLI/RecordingTable/agent/context/interpreter/
strategy/economics/selector/final-validator/Sim boundary crossed. Eighteen validated actions
and independently reloaded/digest-verified traces; 18/18 scripted calls successful and
admitted, zero model fallbacks. Six grounded interpretations and twelve selections admitted.
All three genuine simulator terminal results were **no deal**, zero score, six rounds and
zero timeouts. Minimum package in every arm: official offered cost EUR 1,333,891.20; realized
agreement cost remains null. USD 0 local inference expense; mock token usage unknown and
conservative reservations explicitly reported. No strategic improvement inferred.

**Separate semantics:** `/tmp/v2-semantic-stabilization-final/report.json`, predictions and
null-valued human review artifact. 14/14 authored drafts admitted and matched provisional
semantic checks; deleting a preference hypothesis preserves admission but reduces matches to
13/14. All independent critical/semantic human reviews remain outstanding. No hosted quality
claim and no frozen held-out label/input changes. Historic exact failures stay unattributable;
72 original benchmark trace digests verified without rewriting files.

**Gates/failures:** focused new controls 28 passed; consumed V2 1,237 passed / 298 expected
unimplemented xfailed; manifest 1,535 contracts. Lab 170 passed after restoring the existing
uv PATH and local socket access; frozen V1 replay unchanged (3653046). Scoped Ruff/whitespace
pass; four inherited whole-repository Ruff findings remain. Full regression 1,567 passed,
19 skipped, 298 xfailed, 15 unchanged V1 failures. Initial local mock fixture defects (strict
Decimal envelope type and zero-delta string formatting) were corrected before the final
admission/outcome demonstration. No regressions repaired by altering V1 behavior.

**Decision:** retain the diagnosable local integration. Do not advance to Assignment 4 or
claim semantic reliability/superiority from these controls. Proposed next reviewed experiment:
14 interpretation development examples, two paired P10 decisions and one strict connectivity
probe, at most 19 provider calls, separate data/provider/spend authorization, no Arena/Lab
remote writes. Not launched. Closing/dispatch/authentication/document hydration, generic
scenario mapping and durable V2 restart remain prerequisites for real Arena runs.
Full assessment, integration matrix, exact local commands and remaining dependencies:
`docs/v2/llm-stabilization-and-lab-integration-2026-10-11.md`.

## 2026-10-11 — V2 no-deal analysis and separate semantic experiment preparation

- Hypothesis: the three no-deal controls are explained by the supplied package universe and
  supplier script, while missing live observation fields independently limit future adaptation.
- Scope/config: read-only original minimum/direct/grounded P10 runs
  `c089eba7-6109-4e2f-8460-f7369be76e7f`, `8fa9ad14-e2b6-4307-8d17-f0b5545603f7`,
  `12bf923e-ddee-4fe3-868e-628df57bbff3`. Existing working tree preserved; no checkpoint,
  remote campaign, recommendation query/publication or promotion. Local evidence is not a
  promoted shared baseline. Existing V1 failures remain out of scope.
- Evidence: original run/thread records, pinned official Sim rules and all 18 verified V2 traces.
  Transcripts identical: buyer repeats 27.60, supplier reaches final 29.59 then walks away on
  round six. All supplied prices (27.60, 28.34) are below the script's floor. Zero timeouts,
  zero deals and score zero; proposed cost must not be reported as realized agreement cost.
- Integration findings: body-only V2 projection omits observed sheets/documents and buyer action
  operations; terminal status and production closing authority remain unavailable. These gaps
  are distinct from the sufficient price-universe explanation.
- New preparation: `run_semantic_validation` reuses existing HTTP/consumers/spend guard; strict
  v2 prompts/schemas, pinned gpt-4.1-mini-2025-04-14. Fourteen development interpretations,
  two original P10 two-call decisions and one strict probe; at most 19 attempted hosted calls,
  311296 conservative reserved tokens, proposed separate USD 1.00 limit, no retry. Preparation
  fingerprints source/data/prompts/DTO/provider schemas and verifies unchanged frozen held-out.
- Budget consumed: zero hosted calls, zero new sessions, zero remote writes. Mock-only rehearsal
  covers the full 19-call schedule. Earlier incomplete preparation directories retain local
  adapter/mock debugging evidence; no hosted transport was created.
- Review: separate nonblind agent text-based expectations review; independent human labels and
  output adjudication still pending. Automatic 14/14 scripted controls are not model reliability.
- Decision/next experiment: obtain explicit approval for this exact 19-call semantic development
  evaluation, then review critical meanings before a bounded Assignment 4 proposal pilot. Do
  not add deterministic bargaining tactics, relax validation or infer efficacy from Sim agreement.
- Report: `docs/v2/hosted-semantic-validation-and-lab-failure-analysis-2026-10-11.md`.
  Analysis: `/tmp/v2-lab-failure-analysis-2026-10-11.json`; final prepared plan/preview/control
  evidence: `/tmp/v2-semantic-validation-reviewed-2026-10-11/`. Hosted results: not run.
- Request inspection found a 426-token output allowance on long interpretation inputs. Omitting
  provider-schema title/description annotations saved 1908 bytes, retaining all validation
  constraints and restoring 2048 output tokens without expanding existing budgets.

## 2026-10-11 — Authorized hosted semantic validation, one-time allowance consumed

- Hypothesis/config: the frozen reviewed v2 prompts/strict DTO-derived provider schemas would
  improve interpretation availability while retaining official economics, grounding and final
  validation. User explicitly authorized direct OpenAI gpt-4.1-mini-2025-04-14, maximum 19 calls,
  USD 1.00, 311296 reserved UTF-8 byte/schema/framing tokens, no retries, Arena or remote Lab writes.
  Prepared plan/source/prompt/schema/data equality verified before and after execution; no
  validator, prompt, schema or frozen-label changes occurred. Assignment 4 not implemented.
- Execution: one invocation of `experiments.v2.run_semantic_validation`; exact approval at
  `/tmp/v2-semantic-validation-approved-2026-10-11.json`, hosted output
  `/tmp/v2-semantic-validation-hosted-2026-10-11/`. Source fingerprint
  `61465b339746c0509360af61d63f481903f7cae71af51f4d9f5a0362c3a1095e`.
- Calls/budget: 19/19 provider successes; 16 interpretations, three selections including the
  probe; 311296 tokens/USD 0.4980736 conservatively reserved. Reported usage 52925 input + 4866
  output = 57791 tokens, uncached usage estimate USD 0.0289556, zero missing usage. Summed
  call latency 53.705s. Zero timeouts, retries, negotiations and remote writes.
- Admission: development 1/14 and P10 0/2 interpretations; fifteen schema-stage rejections/
  interpreter fallbacks, all at `observations.0.citations.0.*.session_id`. Only the greeting's
  empty assessment was admitted. Two substantive P10 selections admitted, zero selector fallback;
  probe passed. Both model/baseline traces verify and both final actions remain valid.
- Semantics: automatic provisional development score 1/14, fourteen missing critical-error
  reviews. This is not human semantic accuracy or evaluated zero critical errors. Rejected
  responses remain withheld; fifteen outputs never reached grounding and the only grounded
  interpretation is empty. Independent human adjudication still pending.
- P10: exact same package contents as the previous hosted run: volume question selects minimum
  at EUR1333891.20; delivery preference selects 42-day package at EUR1335154.08 (+EUR1262.88).
  Both interpretation calls still fall back, so no demonstrated interpreter contribution.
- Diagnostic limitation: read-only local synthetic bad-span-length control reproduces the
  same path via SourceRef union-branch extra-field errors, masking a later MessageSpan failure.
  This is a local control, not a reconstructed rejected hosted response. Exact hosted citation
  defects remain unresolved; do not assert wrong session IDs or wrong offsets from this path.
- Decision: do not proceed to Assignment 4. Operational usability misses the predeclared 12/14
  criterion, and human review remains pending. Next scope: copyable deterministic citation
  metadata plus safe union-aware diagnostics/local controls; preserve validators. Any hosted
  revalidation requires fresh explicit authorization; no automatic rerun planned/executed.
- Report: `docs/v2/hosted-semantic-validation-results-2026-10-11.md`. Separate read-only analysis:
  `/tmp/v2-semantic-validation-hosted-analysis-2026-10-11.json`. Originals unchanged, held-out
  digest unchanged and zero held-out calls. No checkpoint/publication/promotion or V1 change.

## V2 Arena observation/citation integration — 2026-10-11

Hypothesis: deterministic whole-message citation IDs and faithful public Arena observations
remove schema/observation interface bottlenecks without altering official economics or action
validation. This is a plumbing experiment, not a strategy superiority test.

Configuration/source: current dirty-workspace Lab provenance; existing P10 finite packages,
`grounded-supplier-v3`, `assessment-citation-ids-v1`, full bounded observation projection,
scripted local ambiguity/minimum responses, official arithmetic and independent validation.
Recommended Lab checkpoint read: `e1d931e4fcce49fb8fd341c40052953a`; three findings reviewed.
No checkpoint publication or promotion. Offline allowance: exactly one simulator negotiation.
Online allowance: one conditional session, stopped before creation because production safety
and a fresh inference budget are missing. No exhausted authorization reused.

Run A: `939a46c9-8689-4aae-8493-a14761fd0d5f`, official arena_kit.sim.Sim/arena-sim engine
0.1.0, pinned kit `1b5516bb95ef28e37f69aa446dc62168864bca53`, in process with clock enabled,
case:P10. Six rounds, six valid actions, zero timeouts, genuine terminal no deal, official
score 0.0, no realized deal cost. Supplier prices 32.88/32.22/31.56/30.90/30.24/29.59;
buyer repeats 27.60 with full terms. V2 receives all prices, final_offer, quote text/provenance
and buyer history; terminal history is preserved. Interpretation 6/6 admitted, selector 6/6,
zero fallbacks; these are scripted controls, not hosted reliability. Twelve scripted calls,
zero hosted calls, model seam latency 0.009638008 s, negotiation elapsed 0.687742498 s,
USD 0 inference. Proposal official cost EUR 1,333,891.20 each round; zero proposal changes.
Every supplier standing sheet fails the volume must-have. No acceptance bypass was attempted.

Run B: online https://arena.tacto.ai credentials and case permissions verified with read-only,
zero-retry transport; snapshot practice quota 303 used/297 left/600 limit. D01, D02 and P10
accessible. Zero session creations or model calls. Blockers: missing fresh inference
configuration/spending authority, V2 production closing authority/checks, durable remote
execution/reconciliation integration and a remote-capable factory/case loader.
No mock hosted outcome. Sandbox network reads first failed; permitted external metadata reads
succeeded, including shared Lab recommendation/findings. Lab availability is not a blocker.

Verification: six original trace digests/certified payloads verify. Focused gate 820 passed,
178 expected xfailed; after final wire/diagnostic/provenance checks, changed DTO/new contracts
691 passed, 178 expected xfailed, and model/selection/provider controls 118 passed. Scoped Ruff
and git diff --check pass. Simulator-creating integration tests were not run, preserving the
one-session allowance. Final authoritative acknowledgement hook was tightened after the
negotiation and tested with nonnetworked stubs; no rerun was performed. Original run provenance
is retained. Attachment text tampering and unknown citations reject without execution.

Decision: offline observation and citation plumbing demonstrated; no live reasoning,
adaptation, online negotiation or superiority demonstrated. Preserve the local-only remote
block. Complete existing safety ports and obtain a fresh bounded inference allowance before
online execution. Detailed interfaces, transcript and evidence:
[results](../docs/v2/arena-integration-results-2026-10-11.md),
`/tmp/v2-arena-integration-offline-2026-10-11/{integration-report,complete-transcript}.json`.

## 2026-10-11 — Bounded adaptive negotiation milestone

Implemented modular citation-grounded proposal generation, independent economics/policy gates,
closing authority, authoritative Lab observations, and conservative journaled online submission
and reconciliation. Genuine hosted inference remains separately gated. Official simulator fixed
baseline scored 0 without a deal; scripted adaptive control agreed after two proposals and scored
0.8094806135901004, with official cost EUR 1,502,401.68. This establishes integration only.
Runs `faa135d5-c8e0-4374-a886-5f63246ddbfd` and
`d482589d-cd1a-443e-9d5e-4bb9973869df` were uploaded after explicit retry authorization and verified
through normal Lab listing, retrieval and comparison. Subsequent finished-attempt enrichment was
rejected with HTTP 409; complete extra evidence is retained locally, not claimed published.
Full V2: 1,257 passed, 298 expected xfailed; latest adaptive/Lab regression gate: 14 passed.
No hosted calls or online sessions. Source-bound offline allowance prepared for explicit approval.
See [milestone report](../docs/v2/intelligent-negotiation-milestone-2026-10-11.md) and
`/tmp/v2-intelligent-negotiation-2026-10-11/{complete-transcript,milestone-report,remote-lab-proof}.json`.

## 2026-10-11 — Hosted sandbox sequence preparation, no hosted execution

Hypothesis: real citation-grounded interpretation and new adaptive packages can negotiate
through official hosted D01/D02 before a separately approved P10 practice run. Extended existing
Lab/V2 adapters for per-bidder RFQ history and economic slices, executable alternatives, grounded
quote defaults, all-thread closing and exact one-session endpoint scope. Corrected Lab completion
ordering: terminal, decision and usage evidence precede immutable completion. Failed offline
development gates remain tracked even without simulator sessions. No deterministic bargaining
library, oracle change, recommendation promotion or validator weakening.

Read-only official metadata verified active credentials, D01/D02 permission, hosted P10 and
286/600 remaining practice sessions. Model metadata and current configured Lab listing returned
HTTP 200. Prior recommendation and findings were reviewed. No hosted inference calls, hosted
Arena sessions, or remote Lab writes in this update. Official-Sim/mock-model tests are conformance
checks only, not negotiation quality results. Full V2: 1,263 passed, 298 expected xfailed;
latest focused checks: 17 passed; local Lab runner regression: 32 passed. Scoped Ruff passes.

Prepared separate unauthorized offline/D01/D02/P10 templates. First approval request: offline
GPT-4.1-mini snapshot, 32 calls, 3,145,728 reserved tokens, USD 2 ceiling, two in-process simulator
sessions, zero hosted sessions and two final Lab publications to the exact configured destination.
No automatic stage progression; original predecessor transcript/Lab proof must be reviewed and
blockers resolved before each fresh hosted allowance. See
[readiness report](../docs/v2/hosted-sandbox-readiness-2026-10-11.md).

### Priority update — direct D01, awaiting approval

User cancelled the proposed 32-call offline evaluation and requested direct hosted learning.
Removed D01's offline-review prerequisite while preserving exact approval, independent validators,
durable submission, no retries, single-session scope and complete final Lab capture. The exception
is explicitly scoped to D01; D02/P10 retain actual predecessor review. Refreshed Arena/model/Lab
access using read-only calls. Four targeted existing adapter/session/gate tests and one existing
uncertain-submission recovery test passed; no broad test suite. Prepared
`/tmp/v2-d01-direct-preparation-2026-10-11/authorization-template.json`: one real D01 sandbox
session, GPT-4.1-mini snapshot, maximum 18 calls/1,769,472 reserved tokens/USD 1, one final Lab
publication to `https://66-201-6-11.sslip.io/`, zero retries/reruns. No inference, hosted sessions
or Lab writes made. Await fresh explicit approval; evaluate actual behavior irrespective of agreement.

### Actual authorized D01 — failure before dispatch

Hypothesis: the existing adaptive V2 strategy can interpret the actual hosted supplier and
propose independently validated legal trades. User explicitly approved the reviewed direct
D01 plan and conservative accounting. Original source hash:
`9d47aec6e5538f5e601f96aa9edb6f76b3ca0ddab6166fd17774a30aa20b25cd`;
dirty patch retained. Exactly one D01 sandbox session `de6f67ea54658727`, actual
GPT-4.1-mini-2025-04-14; no offline experiment, D02, practice or retries.

Lab run `04a6789d-593b-4722-a7f4-5f289da374f1` was published once and retrieval/listing
verified. Interpreter timed out at eight seconds; cancellation race allowed one proposer
call, whose legal proposal was validated but never dispatched. Zero buyer submissions.
Arena later ended after three automatic timeouts: no deal, score 0. The immutable remote
failed record predates terminal expiry; final terminal evidence remains local only.

Two reservations: 196,608 tokens, USD 0.0835584, within 18 calls/1,769,472 tokens/USD 1.
Known proposal usage 3,424 tokens/USD 0.0016828; interpreter usage and total spend unknown.
Unsent proposal EUR 50.50, 45-day payment, 24 months, effective 2027-01-01; nominal cost
EUR 414,299.04. No evidence of supplier acceptance or adaptive negotiation quality.

Decision: stop without another session. Fixed synchronous timeout stop ordering and future
failure terminal capture before publication; two focused regression tests and scoped Ruff
passed. D02 recommendations address hosted latency, payment-direction reasoning, reciprocal
trades and explicit review of this failed predecessor. Fresh D02 authorization remains required.
Full analysis: `docs/v2/hosted-d01-results-2026-10-11.md`; original and exported evidence:
`/tmp/v2-d01-hosted-execution-2026-10-11/`.

## 2026-10-11 — Standalone D01 inference-probe finalization repair (local only)

Hypothesis: executor teardown can hold the standalone probe after its decision finishes, preventing
trace/report persistence; replaying historical server clocks against current UTC separately rejects
its fallback. User authorized repair following the code investigation. Config: existing D01 probe,
35-second compute allowance and two-second supervised cleanup; workspace contains pre-existing V2
changes. No provider/Arena/Lab quota consumed, retries, push or promotion.

Implemented one supervised spawned worker, evidence persistence before async teardown, bounded
termination, explicit recorded-clock replay, durable stop forwarding, corrected usage report access,
null unknown token cost, and sanitized transport exception/status diagnostics. Original consumed
allowance and execution evidence remain unchanged. Initial related checks: 97 passed; updated probe
and hosted-readiness checks: 36 passed; final probe checks including durable stop: 4 passed. Scoped
Ruff and diff checks passed. Scripted preserved-D01 replay selects and validates its fallback.

Decision: local repair verified. Original provider failure remains unidentified; no original stack
was preserved and no new inference was attempted. Fresh exact authorization remains required for
any hosted probe. Details: `docs/v2/inference-probe-finalization-repair-2026-10-11.md`.

## 2026-10-11 — Authorized inference-only D01 probe, retry-01

User approved the exact fresh two-call plan (196,608 tokens / USD 0.0835584 maximum) and granted
standing authority for sandbox runs within agreed limits. Source fingerprint at dispatch:
`43fb20c652fce396e01963edb9df9f558f54cc61a4d3be7db4bbe1eb4b6186d1`.
Execution used provider/network and local-socket permission. Exactly one interpretation request
was reserved; it exceeded the nine-second stage cap and was cancelled. No proposal transport call,
retry, Arena request or Lab write occurred. Unknown usage retains 98,304 tokens / USD 0.0417792;
actual spend is unknown. Runner returned after 9.544 seconds with cleanup complete.

The verified decision trace contains completed fallback interpretation, fixed proposal fallback,
selection and valid independent action validation. No action was submitted. Original report
status is `runner_failed`, error type `KeyError`: report generation raced the cancelled transport's
finally block and accessed latency before it was recorded. This is an original execution failure,
not a successful end-to-end probe. Complete trace and original result remain unchanged under
`/tmp/v2-d01-inference-probe-2026-10-11-retry-01/execution/`.

Fixed reporting locally to use the decision ledger's measured elapsed time while transport cleanup
is pending; regression suite: 5 passed, scoped Ruff passed. No further inference was performed.
A separately labeled report recovered entirely from the saved verified trace and durable ledger is
at `/tmp/v2-d01-inference-probe-2026-10-11-retry-01/offline-report-recovery/result.json`.
It confirms valid offline fallback and partial model execution; it does not supersede the original
failed runner result or demonstrate proposal commercial reasoning. No automatic rerun occurred.

## 2026-10-11 — Real-provider sandbox inference repair verified

User granted standing authority for as many sandbox runs as necessary. Hypothesis: after runner
finalization repairs, request/consumer contract mismatches are causing latency and rejected outputs.
Used four fresh two-call inference-only D01 probes (retry-02–05), same GPT-4.1-mini snapshot,
recorded supplier input, independent economics and validator. Eight calls, known usage, aggregate
estimated token-rate cost USD 0.0174648; no Arena sessions/actions, Lab writes, request retries,
push or promotion. Earlier unknown-usage reservations remain unchanged.

retry-02 completed provider calls but rejected interpretation grounding, then proposal diagnostics
failed because `commercial_effects` was not an allowed diagnostic stage. Its requested longer
measurement limits were also not inherited by spawn. Fixed diagnostic stage and worker plan loading;
clarified exact-source interpreter and complete-binding/trade-direction proposal prompts. retry-03
admitted both outputs and independently validated the model action (6.252-second caller return).
retry-04 under original limits admitted interpretation but rejected missing payment uncertainty,
then independently validated fixed fallback. Clarified uncertainty requirements; retry-05 under
original 9/5-second caps admitted both outputs with valid selected model action, 5.725-second decision,
6.176-second caller return, reported 8,552 tokens and estimated USD 0.0041288. Final terms: EUR 50.00,
45-day payment, 24 months, effective 2026-12-01; not submitted.

Final checks: 77 passed (probe, grounded model, adaptive proposal, commercial effects), scoped Ruff
passed, diff clean. Decision: scoped inference/admission/finalization repair verified; stop probing
once original-budget success is demonstrated. No negotiation-quality or hosted Arena acceptance
claim. Each source fingerprint and exact allowance remain in each attempt's approved-plan.json;
all failed/rejected evidence is preserved. Detailed results and limits:
`docs/v2/inference-probe-finalization-repair-2026-10-11.md`.

## 2026-10-11 — D01 hosted repair trial

Hypothesis: the one-call evidence-preserving adaptive path can submit a validated package and
close a real D01 session without the previous interpreter timeout. One fresh exact allowance was
used for one D01 sandbox session, one final Lab publication, GPT-4.1-mini-2025-04-14, at most 18
calls / 1,769,472 reserved tokens / USD 1, zero retries and no automatic reruns. Source fingerprint:
`300c68189a2c4cfda92eb8b856ed7c8338b02bae2f98ea9a2bf2ad6e792d1d24`.

Run `15500f1f-0048-437d-acad-cfbd79098c8d`, session `21fed09494f89548`, completed with a deal in
two rounds, no timeouts and score 0. The model made one admitted v3 proposal call (3,501 input,
185 output tokens, 2.845 seconds; estimated usage-rate cost USD 0.0016964). It returned exactly
the supplier's opening terms: EUR 52.90, 30-day payment, 12 months, effective 1 December 2026.
The supplier accepted; shared closing independently accepted the standing sheet. The run is an
execution pass but shows no commercial concession or score gain. Fixed candidate minimum cost
was EUR 398,400.00 versus accepted offer cost EUR 448,810.67; the former is not an attainable offer.

Lab item and listing retrieval were verified; complete terminal evidence and no pending write are
saved under `/tmp/v2-d01-repair-execution-2026-10-11-01/`. One call reserved 98,304 tokens /
USD 0.0417792. The immutable remote summary incorrectly marked deterministic evidence copying as
admitted interpretation and named proposal v2. Corrected local metrics now require an admitted
interpreter call and identify v3/evidence-copy; focused regressions passed (28 passed), Ruff passed.
The remote record was not rewritten. Decision: stop after this one trial, preserve the discrepancy,
and review the complete transcript before any further hosted run. Detailed report:
`docs/v2/negotiation-repair-d01-trial-2026-10-11.md`.
