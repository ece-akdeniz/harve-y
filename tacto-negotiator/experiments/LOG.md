# Experiment log

Format and decision rule: `docs/04-experiments.md`. Newest on top. One entry per change.

## 2026-10-10 15:14 — Pre-meeting targeted retest (MEASURED HOSTED)

- Candidate revision `25fe977`: package/final-offer fixes, trade packages, and
  supplier-cost estimates. Exactly one session each for five cases; no replacement sessions.
- Comparison with previous `ba1b242` sweep (unpaired, single runs; not a causal estimate):
- case:P04: 5.64 -> **86.04/100**, session `79050b92d7a60489`.
- case:P08: 15.62 -> **52.71/100**, session `0d5ecfc4055c87af`.
- case:P10: 0.00 -> **45.32/100**, session `79c3a047f6c4a906`.
- case:P11: 31.44 -> **40.64/100**, session `ac9fe2be921b9ed3`.
- case:P18: 0.00 -> **40.62/100**, session `14b3fbcb0087b661`.

- Reconciled five-case mean **53.07/100**, five deals,
  all must-haves satisfied, zero recorded timeouts (including recovered P10).
- P10 was NOT an uninterrupted autonomous success. The API returned HTTP 422 when
  accepting `offer:70410-1-a` despite the alternative being shown in the supplier email.
  Operator-assisted reconciliation fetched current session state and accepted its primary
  standing offer `offer:70410-1` in the SAME session. This closed at 45.32/100.
  The initial script exit status was 1; raw error and recovered state are both retained.
- Added GuardedRemoteTable after this incident: on rejected alternative acceptance,
  fetch authoritative state, stop if ended, find the current primary offer, resolve documents,
  recheck must-haves and alternative cost, and only then submit a new acceptance action.
  This new recovery code is locally tested, not separately arena-tested. It is wired into
  play, sandbox/practice run, and practice_sweep; final play_waves remains kit-managed.
- Tests after recovery fix: **43 pass**, Ruff passes. Regression coverage includes both
  valid recovery and rejection of a primary offer above the alternative. No extra quota.
- Raw run: `runs/20261010T131141Z-practice-a04138/`. `summary.json` preserves the initial
  P10 failure; `summary-reconciled.json` explicitly labels its recovery.
- Team quota after: 60 used, 140 left; this sweep created exactly five sessions.
- Stop here for the team meeting. Next architecture/scope decisions come from the team.

## 2026-10-10 14:58 — One pass over all hosted practice cases (MEASURED HOSTED)

- Policy revision `ba1b242`: favorable, recipient-aware index evidence enabled; same
  PackageAgent numerical policy. Rising indices are omitted; hedge/irrelevance statements,
  contradicted claims and final statuses suppress new index arguments. 33 tests and Ruff pass.
- Hypothesis: avoid strengthening the supplier's position with positive cost-driver claims;
  stop index arguments when the recipient explicitly rejects their relevance.
- Ran exactly one session per hosted case, three cases concurrently, no model calls.
  The nine other listed practice cases are not hosted and were not opened.
- Mean **37.41/100**, 8 deals, 2 no-deals, zero recorded timeouts in all threads.
  All eight deals passed must-haves. This is one unrepeated sweep, not an improvement estimate.

- case:P01: **87.49/100**, session `174500003290252d`, 123.05s.
- case:P02: **29.34/100**, session `322a15e441eac92c`, 7.94s.
- case:P03: **89.98/100**, session `605286747cc78d67`, 11.74s.
- case:P04: **5.64/100**, session `60eb9fa51f0e38b8`, 6.66s.
- case:P05: **41.19/100**, session `5ef6c1f3da1cab3c`, 176.20s.
- case:P07: **73.40/100**, session `af00461c2632436f`, 59.56s.
- case:P08: **15.62/100**, session `5d1eb9688d46277d`, 4.04s.
- case:P10: **0.00/100**, session `0bb925de9d587f14`, 19.15s.
- case:P11: **31.44/100**, session `5e8b89b0308337e7`, 4.99s.
- case:P18: **0.00/100**, session `cbf98484048a9282`, 17.52s.

- P01's 87.49 is above the previous broad-evidence run's 70.62, but below the team's
  previous best; stochastic and unpaired runs do not establish causality.
- P04 accepted 12 months against a two-year need: EUR 94,000 uncovered need plus
  EUR 4,700 fallback risk. Non-price negotiation/coverage deserves review.
- P10 supplier withdrew after we countered a final offer. P18 supplier required an
  AS-14404 index clause; the fixed initial non-price package kept rejecting it and lost the deal.
  Next priorities: final-offer handling and economically evaluated non-price adaptations.
- P05 completed in 176.20s with no recorded RFQ timeouts despite serial thread servicing;
  one success does not validate sustained concurrency or final recovery.
- Quota observed 22 -> 34, 178 -> 166 left. This script opened exactly 10 sessions;
  two additional uses occurred outside this sweep. Team credentials are shared.
- Live board at 14:58: y/agent #1, rounded mean 0.55, six records, all ten covered;
  Boo 0.49 and makeAnother.md 0.47. Our P05 result set the new 0.41 case record.
  The team's P04 best rose to 0.86 in another run, not this sweep's 0.0564 result.
  The page also changed from played-case means to all-ten means during this work.
  Spectator observations were never passed to the negotiation agent.
- Raw evidence: `runs/20261010T125400Z-practice-fcac37/` contains metadata, requests,
  per-case state/threads, decision traces and summary. No failed-case retries.
- Entire Graph v0.4.0 and Brain v0.1.0 installed. A clean local committed snapshot
  built all Brain components successfully without backfill/model calls or a daemon.
  Graph located evidence selection/callers/tests; Brain remembered and retrieved the
  earlier evidence failure with session IDs. Capturing this desktop chat still requires
  Codex hook approval; imported history is not proof the current chat is captured.

## 2026-10-10 14:46 — Hosted evidence comparison (MEASURED HOSTED)

- Baseline revision: `9181aaa`; candidate is this entry's commit on
  `codex/verified-negotiation-evidence`. No model calls; same numerical policy.
- Hosted P01 refs omit index IDs. The initial evidence candidate would send no claims.
  Fixed relevance lookup to include base-package cost-driver series for case parts;
  added a regression test excluding unrelated parts. 28 tests and Ruff pass.
- D01 baseline smoke: **91.92/100**, C=EUR 411,869.83, 71.26s,
  session `bfc28153ceb2ab7b`. D01 lacks index refs/eligible part mappings, so an
  evidence comparison there would not exercise the feature.
- P01 baseline: **77.60/100**, C=EUR 1,109,578.24, 50.10s,
  session `a75ba2622c5509e7`.
- P01 evidence: **70.62/100**, C=EUR 1,113,553.62, 95.46s,
  session `7c56746f591c3513`. Opening observations: electricity -3.72%, wages +2.66%;
  a further metal-price observation was sent on round two. The supplier verified the
  opening claims but explicitly noted that the rising driver supports its position.
- All three closed with must-haves satisfied and zero recorded thread timeouts.
  Evidence scored 6.98 points lower and cost EUR 3,975.38 more in this single pair.
  No repeats or statistical/causal claim: supplier outputs are variable.
- Quota: one sandbox plus two practice sessions; practice usage moved 19 -> 21,
  leaving 179. The original no-evidence candidate was skipped before opening a session.
- Decision: keep evidence opt-in. Next test supplier-aware argument selection;
  verified arithmetic alone does not imply persuasive value. Do not promote to final.
- Raw ignored evidence: `runs/evidence-comparison/20261010T124227Z/` (baseline)
  and `runs/evidence-comparison/20261010T124446Z/` (candidate); each includes request
  records, final state, threads and decision traces. Machine kept awake with caffeinate.

## 2026-10-10 — Verified index evidence candidate (MEASURED LOCAL)

- Configuration: branch `codex/verified-negotiation-evidence`, opt-in `--evidence`;
  official kit remains pinned to `1b5516b`. Baseline remains the default.
- Hypothesis: case-relevant index observations plus a cost-breakdown question improve
  price-increase negotiations without changing the numerical offer policy.
- Implementation: derive exact calendar-year changes from finite positive values;
  require matching ID/series/month metadata and a recent window; recompute before
  rendering; select at most two observations; exclude prior buyer citations case-wide.
  Base/release facts come through DataPackage, with case facts overriding them.
- Validation: 27 local tests pass, including malformed data, tampering, relevance,
  staleness, overlay precedence, cross-thread duplicate suppression, deterministic
  retry proposals, and unchanged offer terms with evidence enabled. Ruff passes.
- Cases/quota: synthetic evidence fixtures and kit S01 decision tests only; no hosted
  sessions, no quota consumed, no model calls. No new negotiation scores measured.
- Limitations: no supplier hedge/motivation interpretation, no full claim bank,
  no persistent retry journal or concurrent citation reservation. True positive index
  changes can support the supplier; persuasion is unproven.
- Decision: retain as an opt-in candidate pending a planned baseline/evidence comparison
  on sandbox and diverse price-increase cases. Do not infer final readiness.

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

## 2026-10-10 — Pre-meeting package fixes (candidate, before hosted test)

- Hypothesis: accepting actual final sheets avoids preventable walkaways; calculating
  opening packages at our bid and offering cost-bounded alternatives improves tradeoffs.
- Fixes: no counter to final_offer; validate every standing sheet; remove preview-induced
  lock; counter from supplier package; allow up to three independently valid trade packages;
  prefer less strict PPM when modeled quality cost ties; supplier/part-specific should-cost
  upper confidence bound in closing costs, with buyer financing rate as a stated proxy.
- Tests: 41 pass; Ruff passes. Regression fixtures are public Tacto practice case inputs.
- Planned experiment: one run each of P04, P08, P10, P11, P18, five practice sessions.
  Results to be recorded after completion; no improvement or final-readiness claim yet.
