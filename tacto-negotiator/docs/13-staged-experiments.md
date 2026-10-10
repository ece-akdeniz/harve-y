# Staged implementation and experiment contract

This supersedes the budget and proposed sequence in document 12. Historical observations
in document 12 remain evidence, not runtime inputs. Updated 10 October 2026.

## Implemented, awaiting hosted screening

`--policy-config PATH` on `play` and `run` enables a version-1 JSON policy. Omit it to
preserve existing behavior. `configs/packages.json` enables renewal/quality package trades;
`configs/packages-evidence.json` adds verified renewal/quality evidence to the same policy.
Both leave estimates, generic payment MESOs and experimental final-offer risk disabled.

Packages are evaluated at quote and anchor prices. A multi-year signal selects the shortest
permitted tenor covering the horizon, at unchanged annual volume. Quality can relax to a
permitted ppm commitment if complete cost does not rise. After two non-improving replies,
exploration may switch one permitted dimension, at most twice, with at least three moves
and 20 seconds left. Price is converted through the complete-cost evaluator. Buyer history
reconstructs actual packages and the final-counter budget after restart. Only a standing
supplier sheet is acceptable by ID; alternatives are counteroffers.

Verified evidence supports all nineteen case banks. Missing/non-numeric notice values are
omitted independently. Quality prioritizes historical ppm and renewal prioritizes performance
and relevant indices. Partial weighted changes do not establish a fair price. Evidence keeps
its numerical, disclosure, duplicate-reference and claim-count guards.

Optional `final_offer_risk: opening_proxy` limits a no-alternative final counter to a cheaper
package already offered by that supplier. It evaluates U(C)=max(0,Copen-C), uses assumed
withdrawal probability 0.25, and logs sensitivity at 0.1 and 0.5. This is a decision proxy,
not expected normalized score. Missing inputs or nonpositive expected improvement retain
the standing offer. It is not enabled in screening.

Run traces record the resolved config and hash, source revision, actual data/release hashes,
candidate packages, trades, costs and closing reasons. Unknown timeout counts remain unknown;
incomplete runs exit nonzero. Local validation: 101 tests and ruff passed before screening.

## Budget and release gates

Maximum cycle: 52 sessions, preserve at least 46. Quota was 179 before this cycle; the earlier
181 snapshot predates two sessions outside this cycle. Each new batch rechecks actual quota.

1. Screening, four sequential runs: P04 package-only, P04 plus evidence, P11 package-only,
   P11 plus evidence. Fixed source/data; compare historical baselines only as screening.
2. Confirmation, four: one fresh baseline (`1551125`) and one stronger candidate repeat per
   case, only if screening improves. Prefer package-only within 0.5 points of combined.
3. Optional refinement, up to eight: only improved candidates still below current competitor
   targets. P04 standard payment and longer tenor, two each; P11 lower chargeback, up to four.
4. Broader development, up to sixteen: P08, P02, P05, P10, two baseline and two candidate each.
   Change one policy group. P02 claims first; P05 faster payment while retaining RFQ concurrency
   and delivery constraints. Rival claims remain deferred pending provenance/recipient tests.
5. Final comparison, twenty: a frozen combined candidate and baseline on all ten hosted cases,
   alternating arm order. This is regression, not an unseen holdout. Use candidate runs to test
   the shared limiter and intended concurrency.

Stop new starts on invalid actions, contradicted claims, unresolved requests or runtime failures.
Let already-open sessions finish safely. Failed screening requires local diagnosis before
confirmation. Unused allocations are skipped; 52 is a ceiling, never an instruction to spend.

Promotion requires no new invalid actions, contradicted claims, unresolved failures or must-have
violations; higher ten-case mean; and no case regression over two points without revising or
removing the responsible feature. Report P04/P11 competition separately, using refreshed human
benchmark snapshots. Repeated/cached responses show reproducibility, not statistical significance.

## Execution and sharing

`tools/staged_batch.py MANIFEST --budget N --out ABSOLUTE_NEW_DIRECTORY` runs explicit jobs
with full immutable source SHAs. Each job has `case`, `label`, `ref`, and optional relative
`config`. It saves local traces, journal and authenticated session/thread evidence, checks quota,
and stops on failed checks. Raw journals and credentials remain ignored. Compact measured
results and experiment decisions are committed for the team. Entire checkpoint linkage is
attached before the source SHA is frozen. Check outgoing credentials before every push.

## FAQ implications and final readiness

The organizer FAQ supplied by the user confirms: final score is the sum of five wave means,
up to 500; euros saved do not rank; ties use more deals then fewer rounds. Unopened or still
open cases at the eight-minute cap count as no deal. No deal scores the alternative, zero if
none. Cbest is fixed per case. Cooperative, verified arguments can affect concessions; this
supports the hypothesis, not a promise that the candidate wins.

The agent runs on our machine or VM; submit repository and commit hash on ehl.gg and run that
commit. Jury prize weighting after the top-ten cutoff remains unspecified. Before freeze,
rehearse deadlines and recovery locally/free sandbox, validate the Sunday release and record
provenance. Neither passing tests nor practice wins establish final readiness or the overall prize.

### Refinement controls and measured checkpoint

`preference: lower_chargeback` starts a quality trade at the lowest permitted ppm commitment
and one lower permitted chargeback. `chargeback_steps: 2` tests the next lower chargeback;
valid ranks are 1–3. This is an experimental package preference, not a buyer requirement.
Stagnation trades prioritize adjacent lower chargeback and only relax ppm upward. Volume is
preserved from the quote for multi-year trades, including when annual volume is negotiable.

Eight measured sessions confirmed P04 package-only at 86.04 versus fresh baseline 5.64, and
P11 package + evidence at 39.80 versus 31.44. All had valid deals and zero actual timeouts.
Exact repeats may be cached. P04 matches the refreshed displayed lead; P11 remains below
62.6. Four P11 refinement sessions are released. See the compact cycle ledger and LOG.md.

P10's recorded opening volume (19,890) fails its 22,230 must-have, so no compliant opening
reference is available for the experimental proxy. The missing-input guard retains the standing
offer. Do not substitute historical Copen/Cbest; skip a hosted risk comparison until it can
exercise the intended rule. This is an explicit limitation, not a measured P10 improvement.

A measured [P04 replay](../experiments/replays/p04-package-evidence.html) includes the package
exchange, verified delivery claim, full closing costs and result. Its evidence arm tied the
package-only arm, so the replay does not establish that the delivery claim added savings.
