# Improvement plan after full hosted coverage

> Superseded for execution by [the staged experiment contract](13-staged-experiments.md).
> The observations below remain historical evidence.

Planning snapshot: 10 October 2026, 14:40 Europe/Berlin. No policy changes implemented by
this plan. Evidence: [machine-readable measurements](../experiments/coverage-20261010.json),
[experiment log](../experiments/LOG.md), and the session IDs below.

## Decision

First improve P04, then generalize package exploration to P08, P02, P05 and P10.
The current agent executes reliably in these observations but often negotiates price while
ignoring the commercial trade that could unlock a concession. A larger model alone will not
fix that. Keep numeric decisions in code; make supplier constraints affect candidate packages.

All ten hosted cases now have measurements. Nine other dataset cases are explicitly
`hosted: false`: P06, P09, P12–P17 and P19. They have not been negotiated on the hosted
arena. Offline claim-bank checks covered all nineteen; no simulator score substitutes for
an unavailable hosted test.

## New measurements

Frozen source `1a18dc0`, PackageAgent-v0.2, claims/estimates/MESO off, async runner,
three concurrent sessions maximum, one shared limiter at six calls/second. Five sessions:

- P02: **29.34/100**, session `1c87a28d5390f289`, 53.3 seconds.
- P04: **5.64/100**, session `ae20ddcf43f86237`, 47.5 seconds.
- P08: **15.62/100**, session `7b1457795e1fbbbd`, 72.3 seconds.
- P11: **31.44/100**, session `d5371cf52ee9b718`, 130.8 seconds.
- P18: **38.61/100**, session `ca5c5a2ee6331b7f`, 72.8 seconds.

All five: deal, must-haves satisfied, zero server-reported thread timeouts. Quota **186 -> 181**.
Local raw evidence: `experiments/runs/coverage-20261010/`; compact results above are tracked.
This is coverage and a small concurrency observation, not a ten-session final-wave rehearsal.

The best observed mean across all ten is **45.91/100**, mixing configurations and prior
runs (including claims-on P01). It is not the mean of one frozen release candidate.
P11 and P18 match the displayed house scores to four decimal places. That is a benchmark
observation, not proof of optimality. The public board changes: at 14:40 Boo held P04 at
81.0, P05 at 38.1, P08 at 22.7 and P11 at 40.6. Public benchmark data stays in human
planning artifacts and is never loaded by the negotiation runtime.

## P04: beat Boo by changing the package

**Measured failure:** opening EUR 4.96 / 30 days / 12 months; we proposed 90 days and
kept 12 months throughout. Supplier repriced to EUR 5.02 and stayed there. Our offers rose
4.36 -> 4.50 -> 4.63 without any new reason to concede. Accepted C = EUR 198,715.67.

**Relevant dossier evidence:** `doc:20260627-70620-M2` says discounts require multi-year
volume agreements. Other notes describe account refocusing and a willingness to discuss
costs. Treat these as hypotheses about receptiveness, not guaranteed discounts. Annual
volume is fixed at 20,000; never promise additional annual volume to obtain a price.

**Mechanism:** `best_terms` selects non-price fields at the supplier's current quote price.
At that price a shorter commitment can be economically rational. The agent then anchors
lower but retains the package. It does not explore the multi-year package that could make
the lower price attainable. `revealed_deltas` currently logs supplier prices for term changes;
it does not use those observations to propose a new trade.

**Concrete acceptance targets, calculated offline:** C_open = EUR 198,846.33 and
C_best = EUR 196,529.32, so the score denominator is only EUR 2,317.01. Matching Boo's
displayed 81.0 requires C <= EUR 196,969.55, or EUR 1,746.12 below our result.
With the recorded fixed/default terms, including 150 ppm:

- EUR **4.94 / 90 days / 24 months** calculates to C = EUR 196,852.67, score **86.04**.
- EUR **4.93 / 90 days / 12 months** calculates to C = EUR 196,927.67, score **82.81**.
- EUR **4.87 / 30 days / 24 months** calculates to C = EUR 196,668.67, score **93.99**.

These are hypothetical packages, not supplier commitments or inferred house-agent terms.
The displayed competitor score is rounded; use >82 as a practical minimum and >86 as a
stretch target. Do not hard-code these case prices or C_best into the agent.

**Implementation plan:**

1. Generate package candidates at plausible opening/anchor prices, not just the supplier's
   opening price. Retain 12-, 24- and 36-month choices where permitted. Coverage is priced,
   not enforced as an unconditional rule. Evaluate the exact complete C for every package.
2. Use the multi-year signal to open a conditional trade: a permitted longer agreement at
   the unchanged annual volume in exchange for a better unit price. Compare 30/60/90-day
   payment packages; do not assume the supplier grants 90 days without a premium.
3. After two unchanged counteroffers, switch one relevant package dimension while there
   are rounds left. Explicitly explain the exchange; do not just increase our price again.
4. Keep every offered field within case options. Alternative supplier sheets remain counter-
   proposals until issued as an acceptable standing offer. Re-evaluate before closing.
5. Generalize the policy by case options, observed quote differences and supplier evidence,
   not by a `case:P04` special branch. Reconstruct package/stagnation state from journal
   history after restart so resume does not restart experimentation.

## Fixes needed before broadening evidence

Offline `build_bank` succeeds on the four price-increase cases but raises `TypeError` on
the other fifteen: a trigger document has `days: null`, then notice logic calls `float(None)`.
P01's good result therefore does not establish a usable claim bank for renewals or quality.

- Skip notice claims when either notice value is missing/non-numeric; preserve valid index
  and scorecard claims instead of failing the whole bank. Regression: all nineteen case banks
  build, and no malformed notice claim is emitted. Check every selected claim numerically.
- Enable additional case types one experiment at a time. P04's 85.0% OTD may be usable;
  do not invent a declining bearing-price index. P02's copper increases support its supplier:
  test other relevant verified facts and clause/payment trades, not a false cheap-copper story.
- Keep internal should-cost private. Avoid the old shorthand that partial weighted index
  changes establish a fully justified price. No blanket rollout of claims or supplier estimates.

## Improvements after P04, ordered by evidence

**P08 — explore term and index trades.** Current C = EUR 1,108,464.80 includes EUR 542,256
uncovered need and EUR 16,267.68 fallback risk. This identifies a coverage trade to investigate,
not guaranteed savings: full coverage at the same expensive price need not be better.
Test longer agreements with an actual price concession and eligible index-clause packages.
Compare clause cost plus risk against the discount. Reuse the package policy learned on P04.

**P02 — stop repeating an unsupported discount request.** Supplier held near EUR 373.65
after repricing 90-day payment. Claims are already supported for this type; use a paired
claims-only check first, then separately test fixed price versus the allowed copper clause.
Use exact supplier offer prices and buyer index paths; acknowledge adverse commodity data.

**P10 — repair the no-alternative risk calculation.** Recorded `final_accept_safe` says
`loss: Infinity`: `alternative_cost` returns infinity when there is no external quote. This
means any positive walk probability blocks a final counter even though the case describes
finite fallback procurement. The supplier offered EUR 32.10 / 54 days as an alternative;
our standing deal was EUR 35.10 / 35 days. Holding recorded other terms constant, the
alternative calculates EUR 112,536 cheaper, but was not directly acceptable by ID.
First define no-deal cost from the official fallback contract and validate it against sandbox
outcomes. Keep that economic quantity separate from 'no executable alternate quote'. Then
test converting the supplier's own alternative into a standing offer. Do not simply set walk
probability to zero; requesting its own package still has transaction/withdrawal risk.

**P05 — price cash and delivery explicitly.** Supplier replies repeatedly link discounts to
30/45-day payment; we keep asking for 90. Test one conditional faster-payment trade and
then an authorized, current rival-offer claim. Use complete cost, preserve lead-time
must-haves, and do not reuse the regressed generic payment-MESO configuration globally.

**P11 — respect the schema despite supplier prose.** Supplier repeatedly requests faster
payment, but payment is not negotiable in this case. Do not change it or promise it in prose.
Explore only price, ppm and chargeback combinations (ppm <=1500). At chargeback >=450,
the formula's residual defect cost is zero; 500 may impose a supplier burden without extra
buyer benefit. However 450 is not an option, so compare permitted 300 versus 500 explicitly.
Use actual prices and quality evidence; retain the valid 31.44 baseline as the control.

## Experiment sequence and budget

Proposed next tranche: **24 development sessions**, then **10 regression sessions**, with
the existing **46-session reserve protected**. No additional sessions spent by this plan.
At 181 remaining, executing the full tranche would leave 147.

1. P04: baseline, package-only, evidence-only, combined; two runs each = **8**. Keep source,
   data, runner, model usage and all non-tested flags fixed. Interleave order; record full costs,
   verified/contradicted claims, terms, latency, closes and actual thread timeouts.
2. P08 and P02: strongest relevant candidate versus frozen baseline, two each = **8**.
3. P10 and P05: candidate versus baseline, two each = **8**. If a previous stage fails,
   stop its rollout and preserve the unused budget rather than consuming it automatically.
4. Freeze the candidate, then one run on each of the ten hosted cases = **10**. Use this
   common-configuration mean to evaluate readiness; do not substitute the leaderboard's
   best-of-history mean. All cases are now seen, so call this regression, not an unseen holdout.

Promotion: improve the targeted case across observed repetitions, no new invalid actions,
timeouts or contradictions, and no material cross-case regression. P04 must beat the
contemporaneous displayed Boo benchmark, not only the historical 81.0 snapshot. Repeats
may be cached/deterministic; treat them as reproducibility checks, not independent samples.
Large unexplained regressions require investigation before promotion.

## Boundaries and release gates

No agent code changed in this planning pass. Next work is implementation of the bounded
package experiment and claim-bank repair, followed by the first eight-session P04 tranche.
Model interpretation can be added later only if deterministic signals demonstrably fail;
it must not override field permissions, validated numbers or the closing evaluator.

Before final deployment: key-wide concurrency rehearsal with ten cases, wave-cap closure,
restart/reconciliation under load, Sunday release provenance, and a single frozen configuration.
Three concurrent successful cases today do not establish those gates. Track and overall
jury outcomes remain separate; current practice records do not establish a winning probability.
