# Experiment log

Format and decision rule: `docs/04-experiments.md`. Newest on top. One entry per change.

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
