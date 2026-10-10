# Supplier memory experiment history

## 2026-10-10 — Experimental cited memory and unseen-supplier evaluation

- Hypothesis: consistent preference statements from diverse discovery suppliers may improve
  first-package selection for unseen suppliers when the preferred current terms are valid and
  have no greater complete buyer cost. Historical offers alone do not imply a preference.
- Branch/config: `codex/supplier-memory`; explicit immutable `config.memory` or ordinary
  `--memory-file`, absent by default. Snapshot/evidence hashes, full discovery cohorts, checkpoint
  source-tree/config/lock/data fingerprints and per-run traces pin inputs. Action vocabulary is
  only higher/lower contract months or payment days in the standard initial-package path;
  unsupported contexts and the separate TradePolicy path abstain. No free-form supplier text
  enters runtime instructions or changes closing authority.
- Synthetic cases: diverse `case:one`/`case:two` discovery, S03 with `sup:unseen`, contradictory,
  sparse, duplicate, recovered, tampered and contaminated evidence; supplier/case-disjoint held-out
  promotion fixtures and both serial/async final CLI factories without live sessions. Dashboard
  fixtures cover 61 observations, filters/25-row pages, citations, hostile text, authentication,
  logout and stale responses. A WAL concurrent-build regression reproduces and fixes the
  read-to-write upgrade lock conflict by reserving the writer before snapshot projection.
- Bounds/quota: at most 64 KiB, 512 evidence rows, three distinct supporting suppliers across two
  discovery cases; held-out evaluation requires at least three disjoint suppliers across two
  disjoint cases and all existing comparison gates. Hosted sessions **0**; sandbox/practice quota
  **0**; no hosted score gain measured; no deployment, push or merge in this trial.
- Validation: final full Python suite **464 passed**; all lab Node tests **42 passed, zero skips**;
  ruff passed. Focused memory/CLI/guidance/auth and DOM checks plus exact RED/GREEN commands are
  recorded in the Task 3 report. This is synthetic/local verification,
  not a measured negotiation result. No hosted trial was authorized or performed.
- Decision: keep experimental. Explicitly choose and budget a separate held-out suite; its
  recommendation does not update the D01/D02 suite pointer. D01/D02 alone, ten practice suppliers
  and adaptive human holdout tuning limit generalization claims. Final readiness remains unproven.


### 2026-10-10 — Discovery provenance final-review fix

- Hypothesis: preserving authoritative discovery rosters independently of collected messages
  prevents an unseen-supplier comparison from accepting a supplier seen during discovery.
- Source/config: `codex/supplier-memory`, final-review fix on `2ca31c9`; no runtime, memory
  schema, checkpoint configuration, dependencies or UI changes. Snapshot builds retain all
  roster/selected/known thread identities and refuse an unverifiable selected discovery cohort.
  Older ended transcripts without a complete authoritative roster remain inspectable but cannot
  establish new snapshots. Existing content-addressed snapshots remain immutable.
- Cases: synthetic tracked/imported runs and original campaign outcomes; missing/partial message
  collection, unknown and malformed rosters, selected/thread identity contradictions, explicit
  legacy missing-roster records, and held-out `sup:X` present only in discovery metadata.
- Validation: focused RED **38 failed, 84 passed**, including six false promotion approvals;
  focused GREEN **122 passed**; full Python suite **500 passed**; Ruff and `git diff --check`
  passed. No UI change; prior **42 passing Node checks** apply. Full commands and logs are in
  `.superpowers/sdd/2026-10-10-supplier-memory/final-fix-report.md` at repository root.
- Budget/scores/failures: hosted sessions **0**, sandbox/practice quota **0**, no measured score
  improvement. All new regressions pass after the fix. Pre-fix snapshots with potentially
  incomplete discovery provenance must be rebuilt and reevaluated before relying on holdout
  results; this fix does not rewrite or retrospectively certify them.
- Decision: retain the experimental branch for scoped re-review. No hosted trial, deployment,
  push or merge; final readiness remains unproven.
