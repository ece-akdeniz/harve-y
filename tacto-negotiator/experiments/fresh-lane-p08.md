# Fresh lane P08 — `reciprocal_schedule` + `claim_pacing` (score-push-v3 base)

Worktree `/Users/sametdegirmenci/Downloads/ysamet-lane-p08/tacto-negotiator`, commit `ead972d`
(dirty only by the untracked `data` symlink; `source.patch` empty). Config
`configs/fresh-h1h2-run.json` passed inline (the `lab run --config` flag does `json.loads`, no `@file`
support) plus `trace_dir` so that decision/evidence events are written to
`experiments/traces/<run-name>/trace.jsonl` inside the worktree. `ARENA_DATA` = main checkout
`data/package`. Budget: max 2 practice sessions. Baseline reference P08 best 0.5930 =
5.31 / db0 / 90d / 24m, C 1,031,778 (supplier sup:70710 opens 6.05).

Sessions used so far: **1 practice** (+2 sandbox, free).

## Step 0 — sandbox mechanics (free)

### run `4d2a1b77-71c5-4771-aad5-87fdac0536b0` — `fresh-sandbox-p08lane-s1`, D01, session `aa63c8ef6ae44af6`
- Completed, `error: None`, score 0.9324, deal 50.50 / 60d / 24m. No `trace_dir` in the stock config, so no
  trace file; reciprocal behaviour visible in the transcript anyway: supplier steps 0.7/0.6/0.4/0.3/0.2 and our
  steps 0.70/0.60/0.40/0.30/0.20 (46.55 → 47.25 → 47.85 → 48.25 → 48.55 → 48.75), supplier final at 50.50
  (round 7), accepted. No claims sent on D01 (empty bank), so no claim results.

### run `a7d347d0-0093-4c36-8f3e-14dd2975a04c` — `fresh-sandbox-p08lane-s2`, D01, session `3bd94d3a68f83fab`
- Same config + `trace_dir`. Completed, `error: None`, score 0.8060, deal 51.30 / 60d / 24m.
- Trace shows `decision` kind `reciprocal` every round (`their_step` 0.7/0.4/0.2/0.1/0.1, `step` identical,
  `scheduled` 47.68 → 48.65 → 49.58 → 50.51 → 51.40 vs actual price 47.25 → 47.65 → 47.85 → 47.95 → 48.05) and
  `evidence_selection` (queue `deep`, `selected: []`). No `evidence` events: D01 has no usable bank.
- Side observation: a stingier sandbox supplier (steps 0.4/0.2/0.1) was mirrored exactly, the supplier went
  final at 51.30 in round 7 and we accepted — 0.806 vs 0.932 above. The sandbox supplier is stochastic, so
  n=1 each, but mirroring tiny steps can leave us far from the schedule when the final offer arrives.
- No `contradicted` results anywhere → proceed to practice.

## Step 1 — practice P08

### run `9a4fbb93-2f73-44fc-bdc7-a8c121b23fea` — `fresh-p08-h1h2-s1`
- session `a64f027775b49028`, replay <https://arena.tacto.ai/replay/a64f027775b49028>, commit `ead972d`,
  config = `configs/fresh-h1h2-run.json` + `trace_dir=experiments/traces/fresh-p08-h1h2-s1`.
- **Score 0.5044** (baseline best 0.5930, −0.089). Deal: offer:70710-3 = **5.39 / AS-14404 index clause db0
  base 2026-08 / 90d / 24m**, c_deal 1,047,322 (c_open 1,135,887, c_alt 1,157,020, c_best 960,309).
  Cost breakdown: price 1,021,944; payment −6,813; index_clause +27,592; index_risk +4,599.
- 4 rounds, 56 s, 0 timeouts, no attempt error, must-haves ok, 0 LLM calls.

Price sequence (supplier ask → our offer):

| round | supplier (status) | our offer | their step | our step | reciprocal event |
|---|---|---|---|---|---|
| 1 | 6.05 / 30d / 12m / no clause (open) | 5.31 / 90d / 24m / no clause + claim quote:7300008 | — | — | n/a (round 1 schedule) |
| 2 | 5.43 db0 **or** 5.55 db5 / 90d / 24m (open) | 5.36 / no clause + claim sc:70710@2026Q3 | 0.62 (primary); agent measured 0.48 on the 5.55 variant | +0.05 | ask 5.55, last 5.31, their_step 0.48, scheduled 5.36, step 0.05 → 5.36 |
| 3 | 5.39 db0 (open) | 5.36 / no clause (unchanged) | 0.04 (agent measured 0.16: 5.55→5.39) | 0.00 | ask 5.39, last 5.36, their_step 0.16, scheduled 5.36, step 0.0 → 5.36 |
| 4 | 5.39 db0 (**final_offer**) | accept | 0.00 | — | final_accept_safe: gain 32,191, loss 109,698, p_walk 0.25 → accept |

Claims and arena results:
- Round 1 `own_quote` `quote:7300008` (5.45, note "own quote of 2026-09-10; not in case refs") →
  **`irrelevant`**. Supplier verbatim: "The rival quote data you cite does not concern this part or our
  company. Which figures is that based on? Please send us the data." It then still dropped 6.05 → 5.43 and
  made the AS-14404 clause mandatory for 24m ("we must include an AS-14404 index clause to manage raw
  material volatility").
- Round 2: both history claims skipped by design (`history_claim_skipped` po_history 5.45 / own_quote 5.45
  vs ask 5.43 — the figure is already above the ask). Deep queue picked `scorecard_otd` `sc:70710@2026Q3`
  (88.0 % OTD) → **`verified`**. Supplier verbatim: "We have reviewed the delivery scorecard data you
  provided; while we continuously work on improvements, our overall performance standing remains solid."
  Price moved 5.43 → 5.39 ("In response to your revised offer"), clause still mandatory.
- Round 3: `evidence_selection` `selected: []` (nothing left in the paced bank). No claim sent.
- No `contradicted`, no `duplicate`.

Supplier final-offer trigger (verbatim, round 4): "We note that your proposal remains unchanged from the
previous round. Having already made significant concessions, we must maintain our offer of EUR 5.39 per
unit. This is our final offer (letztes Angebot). Please decide." We accepted (all final offers).

Diagnosis:
- `reciprocal_schedule` never bound: the fixed schedule's own step was already the minimum (0.05 in round 2,
  0.00 in round 3 because `scheduled` plateaued at 5.36). So the lever changed nothing here; what hurt was the
  schedule plateau + repeating 5.36 verbatim, which the supplier read as a stall and answered with a final
  offer at 5.39 db0 after only 4 rounds. Baseline runs reached 5.31–5.32 db0 over more rounds.
- Measurement artefact: `_supplier_asks` tracks the equal-cost variant (5.55 db5) rather than the primary
  5.43 db0 sheet, so `their_step` was 0.48/0.16 instead of 0.62/0.04. Harmless here (schedule step was
  smaller anyway) but it would misfire on a case where mirroring binds.
- `claim_pacing` H1 (one verified claim per round) did not materialise: the own-quote claim is rated
  `irrelevant` because quote:7300008 is not in the case refs, and the supplier parsed it as a rival quote.
  From round 2 on both history claims were skipped because the supplier's ask (5.43) already undercut the
  5.45 figure, so the "deep bank" was exhausted after one shot; the verified scorecard claim did not move price.
- Net: 5.39 db0 vs baseline 5.31 db0 → −0.089. Step 2 condition (beat 0.5930) not met → stopped, 1 practice
  session kept in reserve.

Recommendation: do not spend the second session on this config. Keep `reciprocal_schedule` off for P08 (no
effect, latent variant-ask bug) and drop the own-quote claim unless the quote id is in case refs (it rates
`irrelevant` and reads as a rival quote). Any P08 retry should target the stall → final-offer pattern
(never repeat an identical sheet while open; token step or a variant instead) rather than evidence.

## 2026-10-11 — Step 2: retry at `3bf3959` (three P08 fixes), 1 practice session

Worktree detached at `3bf3959` (`codex/fresh-pacing`: own_quote only from case refs/alternative; supplier
step measured on the standing sheet; never resend an identical sheet while open — +0.01 above a plateaued
schedule or match the supplier price on our terms). `uv sync --locked`; focused tests
`test_fresh_pacing.py` + `test_reciprocal_schedule.py` 16 passed. Same config `configs/fresh-h1h2-run.json`
(v3 + `claim_pacing` + `reciprocal_schedule`, `supplier_payment_trade` absent/off) passed inline with
`trace_dir`, same launch command pattern as run 9a4fbb93 (`ARENA_DATA` = main checkout `data/package`,
`--agent negotiator.agent:configured_agent --runner serial --allow-dirty`). Sessions used in this step:
**1 practice** (+1 sandbox, free). Lane total: 2 practice.

### sandbox `9a709301-c639-4db2-ae24-773e6e54170c` — `fresh-sandbox-p08lane-s3`, D01, session `fa8bd72749ce584f`
- Completed, `error: None`, score 0.8060, deal 51.30 / 60d / 24m (same as s2). Standing-sheet fix visible:
  round 2 `their_step` 0.7 (52.9 → 52.2 primary) although a 51.8 variant was on the table. `held_by_schedule`
  false every round (schedule far above the mirrored path). No claims (D01 bank empty). Proceeded to practice.

### run `f5852936-092b-4975-9b7d-9fae0ade8576` — `fresh-p08-h1h2-s2`
- session `756caaee0d8a1275`, replay <https://arena.tacto.ai/replay/756caaee0d8a1275>, commit `3bf3959`
  (dirty only by the untracked `data` symlink / traces), quota after: 270 used / 330 left.
- **Score 0.5930** (0.5929541836 — identical to the v3 baseline 0.5929541836; +0.089 vs run 1's 0.5044).
  Deal: offer:70710-4 = **5.31 / AS-14404 index clause db0 base 2026-08 / 90d / 24m**, c_deal 1,031,778
  (c_open 1,135,887, c_alt 1,157,020, c_best 960,309). Cost breakdown: price 1,006,776; payment −6,712;
  index_clause +27,183; index_risk +4,530.
- 5 rounds, 80.9 s, 0 timeouts, no attempt error, must-haves ok, 0 LLM calls. Lead time 10 d (supplier's own).

Price sequence (supplier ask → our offer), run 2 vs run 1:

| round | supplier (status) | our offer (reason) | their_step (standing sheet, our terms) | our step | run 1 for comparison |
|---|---|---|---|---|---|
| 1 | 6.05 / 30d / 12m / no clause (open) | 5.31 + claim po_history ×4 @ 5.45 (round 1 schedule) | — | — | 5.31 + own_quote quote:7300008 |
| 2 | **5.45 db0** or 5.57 db5 / 90d / 24m (open) | 5.36 + claim sc:70710@2026Q3 (round 2 schedule) | 0.58 (ask-on-our-terms 5.57, last 5.31, scheduled 5.36, step 0.05, held_by_schedule false) | +0.05 | supplier 5.43 db0; their_step 0.48 on db5 variant |
| 3 | **5.36 db0** or 5.48 db5 (open) | 5.38, no claim (round 3 schedule) | 0.09 (ask 5.48, last 5.36, scheduled 5.38, step 0.02, held_by_schedule false) | +0.02 | supplier 5.39 db0; our 5.36 repeated (step 0.00) |
| 4 | **5.31 db0** or 5.43 db5 (open) | 5.31 no clause ("gap closed: their price, our terms") | n/a (reciprocal path not entered) | −0.07 | supplier 5.39 db0 **final_offer** → accept |
| 5 | 5.31 db0 (**final_offer**) | accept (final_accept_safe: gain 31,713, loss 125,242, p_walk 0.25) | — | — | — |

Our sequence 5.31 → 5.36 → 5.38 → 5.31 (vs run 1 5.31 → 5.36 → 5.36). Supplier 6.05 → 5.45 → 5.36 → 5.31 →
5.31 final (vs 6.05 → 5.43 → 5.39 → 5.39 final).

Which fixes fired:
- **own_quote from case refs only — fired.** No `own_quote` claim anywhere; `evidence_selection` round 1
  (queue `deep`, 1 slot) picked `po_history` po:4500014284-20/4500014305-10/4500014391-10/4500014455-10 @ 5.45
  (`in_case_refs: false`, `disclosure: supplier_own`) → arena **`verified`**. Supplier verbatim: "We checked the
  price history data you cited; it holds, but it does not change our calculation. Our price follows our main
  cost drivers: AS-14404, PPI-C2431, LCI-C." and "Acknowledging your previous orders at EUR 5.45, we can offer
  EUR 5.57 per unit for this extended, indexed package." Its primary sheet landed exactly on the cited 5.45 db0
  (run 1 with the `irrelevant` rival-read quote: 5.43 db0). It still made the AS-14404 clause mandatory for 24m.
- **supplier step on the standing sheet — fired.** `their_step` 0.58 in round 2 (6.05 → 5.45 db0 both mapped
  on our 90d/24m/no-clause terms; run 1 read 0.48 off the db5 variant) and 0.09 in round 3 (5.45 → 5.36 db0,
  i.e. 5.57 → 5.48 on our terms). Mirroring still never bound: the schedule's own step (0.05, 0.02) was smaller
  both times, so `reciprocal_schedule` again changed nothing on P08.
- **never resend identical sheet — not exercised.** `held_by_schedule` false in both reciprocal events and no
  "match" reason event: the k/rounds schedule itself advanced 5.36 → 5.38 this time (scheduled 5.38 in round 3
  vs the 5.36 plateau in run 1, because the supplier's round-3 ask was 5.36 db0, not 5.39). No identical resend
  occurred; round 4 went through the pre-existing "gap closed: their price, our terms" path (5.31 without
  clause). The supplier's `final_offer` in round 5 was a *terms* stand (clause), not a price-stall reaction,
  and it came at the price we had just proposed — verbatim: "We note your proposal, but as previously stated,
  we cannot offer a fixed price for a 24-month contract and must include an AS-14404 index clause. … We maintain
  our offer of EUR 5.31 per unit with the AS-14404 index clause, 90 days payment, and a 24-month term. … This is
  our final offer (letztes Angebot). Please decide." Accepted (all final offers).

Claim verdicts: round 1 `po_history` → **verified**; round 2 `scorecard_otd` sc:70710@2026Q3 (88.0 %) →
**verified** (supplier verbatim: "We checked the delivery record data you cited; it holds, but it does not
change our calculation. … this metric does not alter our underlying cost structure."; price nevertheless moved
5.45 → 5.36 db0 in that reply). Rounds 3–4: `history_claim_skipped` po_history 5.45 vs ask 5.36 / 5.31 (figure
above the ask) and `evidence_selection selected: []` (deep bank exhausted). No `irrelevant`, no `contradicted`,
no `duplicate`. The round-4 concession 5.36 → 5.31 came with no claim and an unexplained "can adjust our Angebot";
the supplier asked for a binding higher volume ("A binding higher volume would help us and can improve the
price. Which volume can you commit to?").

**Verdict: better than run 1 (0.5044 → 0.5930, +0.089); equal to the v3 baseline (0.5930, same 5.31 / db0 /
90d / 24m sheet, same C 1,031,778).** `claim_pacing` + `reciprocal_schedule` wins vs v3 on P08: **n = 0** (1
loss at `ead972d`, 1 tie at `3bf3959`); the merge condition (n = 2 wins) is not met and the lever shows no
P08-specific lift — reciprocal mirroring never bound in either hosted run and both verified claims were
answered with "does not change our calculation". The three fixes are correct hygiene (no rival-read quote, no
variant-measured step, no identical resend) and removed the run-1 regression, but they only restore the
baseline outcome. Do not spend further P08 sessions on this config; any P08 gain has to come from the clause
(db0 mandatory for 24m, +27 k) or the volume lever the supplier keeps asking about, not from pacing.
