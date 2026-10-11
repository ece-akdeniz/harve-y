# Fresh lane P18 — reciprocal_schedule (H2) / + claim_pacing (H1H2)

Worktree: `/Users/sametdegirmenci/Downloads/ysamet-lane-p18/tacto-negotiator` @ commit `ead972d` (detached, source untouched).
Budget: max 3 practice sessions. Baseline reference P18: best 0.5200 (`c3d8d00deef782f2`), typical 0.39–0.41 with score-push-v3.
Configs: `configs/fresh-h2-run.json` = score-push-v3 + `reciprocal_schedule`; `configs/fresh-h1h2-run.json` = + `claim_pacing`.
CLI note: `lab run --config` only accepts inline JSON (no `@file`); passed via `"$(cat …)"`. `trace_dir` is not in the configs, so it was injected inline (`experiments/traces/<name>`) to get the decision trace.

## Step 0 — sandbox mechanics (free)

### Run `2769d374-5cf4-4abb-986f-cdf444ae43e4` — fresh-sandbox-h1h2-s1 (no trace_dir)
- D01 `698a4d20b5089fa2` completed, deal, score 0.8060, 7 rounds, 0 timeouts, no error.
- D02 `9f0b6e4e6ce55da0` completed, deal, score 0.5239, 9 rounds, 0 timeouts, no error. Claims: all `verified` (J1 ×1, C1 ×3), none contradicted.

### Run `2f6ca29a-7154-444a-838c-29d77de88f6f` — fresh-sandbox-h1h2-s2 (trace_dir injected)
- D01 `5d2229537e6f0a21` 0.8060; D02 `53ca5f2ed5d4d44e` 0.5239. No errors/timeouts, same claim results (all `verified`).
- D01 price path: supplier 52.9→52.2→51.8→51.6→51.5→51.4→51.3(final, accepted); us 46.55→47.25→47.65→47.85→47.95→48.05. Our step mirrored theirs exactly (0.7, 0.4, 0.2, 0.1, 0.1).
- Trace: 10 `decision/reciprocal` events (their_step/step/held present; held=True twice when supplier stood still → token step 0.02–0.03), 10 `evidence_selection` events, 4 `rival_offer_claim`. Mechanics confirmed.
- Server practice counter moved 337→336 during this sandbox run; local practice count 0 — attributed to another key user, not to this lane.

Practice sessions used so far: **0 / 3**.

## Step 1 — P18, H2 only (`reciprocal_schedule`) — PRACTICE session 1/3

- Run `3b3e6345-b7e4-4430-94cb-6fec7909e864` (fresh-p18-h2-s1), session `b1f6aa5ca78a0d5e`, replay https://arena.tacto.ai/replay/b1f6aa5ca78a0d5e, commit `ead972d`, config `configs/fresh-h2-run.json` (+ inline `trace_dir=experiments/traces/fresh-p18-h2-s1`). Quota 336→335.
- **Score 0.4530612521** (baseline best 0.5200, typical 0.39–0.41). Identical to prior score-push-v3 P18 sessions `e41ef29dac7b3dd2`, `68e50dcda140695c`, `5d758509978bcc9b` (all 0.4530612521) → the lever changed nothing measurable.
- Final: 5.40 / 90d / 24m / AS-14404 clause share 0.45, deadband 0, base 2026-08. Supplier `agreed` at round 4 (our accept). c_deal 262,316 vs c_alt 301,088, c_best 222,651; index clause cost 6,911 + index risk 1,152. 0 timeouts, 46 s, 0 model calls.
- Price sequence (supplier ask → our offer):
  - r0 supplier 6.10 (30d, 12m, no clause).
  - r1 us 5.37 (no clause, 90d, 24m) + 2 index claims.
  - r2 supplier 5.50 (90d, 24m, clause db0) + alt 5.50 (30d, clause db5). Step −0.60.
  - r2 us 5.39. Step +0.02. Trace `reciprocal`: ask=5.50, their_step=0.60, scheduled=5.39, step=0.02, held=false → **no effect** (schedule step already smaller than theirs).
  - r3 supplier 5.40 (90d, 24m, clause db0) + alt 5.50 (clause db5). Step −0.10 on main sheet.
  - r3 us 5.40. Trace `reciprocal`: ask=5.50 (!), their_step=0.0, scheduled=5.42, step=0.01, held=true → token step produced 5.40 instead of 5.42.
  - r4 supplier 5.40 db0 only (restated: "we cannot offer a fixed price for a 24-month duration and must include the AS-14404 index clause. Please confirm your acceptance"). Status still `open`, never `final_offer`.
  - r4 us: accept (`gap closed`) → `agreed`.
- Claims: r1 `idx:AS-14404@2026-06→2026-09 −5.5 %` → **verified**; `idx:PPI-C2431@2026-06→2026-08 −2.3 %` → **verified**. No claims in r2/r3 (`evidence_selection.selected = []`, preferred queue empty). No contradicted/irrelevant/duplicate.
- Supplier verbatim reactions: r2 "We welcome your proposal for a 24-month contract, which enables us to offer a more favorable base price. Acknowledging the recent index decreases you verified, we are pleased to offer a revised unit price of EUR 5.50 … we must include an AS-14404 index clause and request to maintain our standard 30-day payment terms." It still restated "AS-14404 rose 5.9 % in twelve months … That remains." r3: "we cannot offer a fixed price for this duration and must include an AS-14404 index clause … lower our price to EUR 5.40 … Which volume can you commit to?" r4: "We appreciate your agreement to the EUR 5.40 unit price …".
- Diagnosis:
  - The reciprocal lever can only *slow* our steps (`min(sched_step, their_step)`); the score-push-v3 schedule on P18 already moves 0.02/0.03 per round, so H2 is a no-op here. Its one visible effect (5.40 vs 5.42 in r3) was neutral: both land on the supplier's 5.40 sheet.
  - The `ask` it reasons about is `_ask_on` = cheapest-by-C sheet mapped onto our package = the **5.50/db5 alternative**, not the 5.40/db0 main sheet. So `their_step` read 0.60 then 0.00 ("held") while the supplier actually moved 6.10→5.50→5.40. The lever is measuring the wrong sheet.
  - Real loss: in r3 we offered exactly 5.40 (no clause); the supplier re-sent 5.40 *with* clause and we accepted a sheet costing ~€8k more (index clause) than our own 5.40 offer, because `gap closed` compares nominal price on our terms, not C. The 0.5200 run shows this supplier still has 5.30 in it (6.10→5.50→5.40→5.30 final) if we stay below 5.40 in r3.
- Sessions used so far: **1 / 3**.

## Step 2 — P18, H1H2 (`reciprocal_schedule` + `claim_pacing`) — PRACTICE session 2/3

- Run `129ce820-9562-4993-85e7-394bf2109755` (fresh-p18-h1h2-s1), session `6cae513938471768`, replay https://arena.tacto.ai/replay/6cae513938471768, commit `ead972d`, config `configs/fresh-h1h2-run.json` (+ inline `trace_dir=experiments/traces/fresh-p18-h1h2-s1`). Quota 335→334.
- **Score 0.5324730606** — new P18 best (+0.0124 vs 0.5200; +0.0794 vs 0.4531). 5 rounds, 0 timeouts, 95 s, 0 model calls.
- Final: 5.40 / 90d / 24m / AS-14404 clause share 0.45, **deadband 5.0**, base 2026-08 (`offer:70740-4`, supplier `agreed`). c_deal 256,557 (c_alt 301,088, c_best 222,651). Index clause 1,152 + risk 1,152 (vs 6,911 + 1,152 for the db0 clause in step 1). Nominal price same as step 1; the whole gain is the deadband-5 clause.
- Price sequence (supplier main sheet / alt → our offer):
  - r0 supplier 6.10 (30d, 12m, no clause).
  - r1 us 5.37 no clause + 1 claim (AS-14404 −5.5 %).
  - r1 supplier **5.40 db0** / alt 5.50 db5 (90d, 24m). Step −0.70 on main (vs −0.60 to 5.50 in step 1 with two claims at once).
  - r2 us 5.39 + 1 claim (PPI-C2431 −2.3 %). Trace `reciprocal`: ask=5.50 (alt), their_step=0.60, scheduled=5.39, step=0.02 → no effect (only reciprocal event of the run).
  - r2 supplier **5.30 db0** / alt 5.40 db5. Step −0.10.
  - r3 us 5.40 no clause (reason `gap closed: their price, our terms`) + deep-bank claim (scorecard OTD 81.0 %). No reciprocal (gap path).
  - r3 supplier 5.30 db0 / alt 5.40 db5 — **held**, verbal only.
  - r4 us 5.40 **db5** (reason `gap closed: take alternative`; the db5 alt is cheaper by C than 5.30 db0: 256,557 vs ≈257,577).
  - r4 supplier `agreed` 5.40 db5. Never went `final_offer`.
- Claims (one per message, as designed):
  - r1 `idx:AS-14404@2026-06→09 −5.5 %` → **verified**. Supplier: "We checked the index change data you cited; it holds and we took it into account … adjusted our pricing to reflect both the extended term and the recent AS-14404 index decrease … Our offer is a price of €5.40 per unit". Still "AS-14404 rose 5.9 % in twelve months … That remains."
  - r2 `idx:PPI-C2431@2026-06→08 −2.3 %` → **verified**. Supplier: "We have verified the PPI-C2431 index decrease you cited and have adjusted our base price accordingly … reduced base price of EUR 5.30 per unit". Also: "Material accounts for about 45 % of our cost; more detail we do not share."
  - r3 `sc:70740@2026Q3` OTD 81.0 % (deep bank, `supplier_own`) → **verified**. Supplier: "We have reviewed the delivery performance data you provided and are committed to improving our on-time delivery rate … we maintain our offer of EUR 5.30 per unit". No price move.
  - Deep bank skipped `po_history` (figure 5.84 > ask 5.30) twice — correct, our old PO price is above the ask.
  - No contradicted / irrelevant / duplicate.
- Supplier at agreement: "We are pleased to accept your proposal of EUR 5.40 per unit with the AS-14404 index clause, 90-day payment terms, and a 24-month contract … Which figures is that based on? Please send us the data."
- Diagnosis:
  - **claim_pacing is the active lever.** Spreading the two verified index claims over two messages got two sequential concessions (→5.40, →5.30 on the main sheet) where step 1 (both claims in one message) got 5.50 then 5.40. The supplier appears to concede ~0.10 per *newly verified* claim, and each message's acknowledgement names exactly one claim.
  - The third (deep-bank scorecard) claim was verified but bought nothing on price — the supplier answered on delivery, not cost.
  - `reciprocal_schedule` fired once and was a no-op again (our schedule step 0.02 < their 0.60).
  - Residual: we never countered below the supplier's alt price. r3 jumped straight to 5.40 (gap-closed path) and r4 took the db5 alt at 5.40. Supplier had 5.30 db0 on the table; a 5.30/5.35 db5 counter was never tried. Nominal price identical to the 0.4531 baseline; the entire +0.079 is the clause deadband 0→5 (≈€5.8k less index cost) obtained because the supplier offered the db5 alt at 5.40 after the second claim.
- Sessions used so far: **2 / 3**.

## Step 3 — P18, H1H2 repeat — PRACTICE session 3/3

- Run `e7045989-3313-4623-bb3c-8bcdd3ba88ca` (fresh-p18-h1h2-s2), session `98f007bf25a16be3`, replay https://arena.tacto.ai/replay/98f007bf25a16be3, commit `ead972d`, config `configs/fresh-h1h2-run.json` (+ inline `trace_dir=experiments/traces/fresh-p18-h1h2-s2`). Quota 334→333.
- **Score 0.5324730606** — identical. All 11 messages (bodies and term sheets, both sides) byte-identical to step 2; same claim results (3× verified), same trace (1 no-op `reciprocal` event, deep-bank scorecard in r3, `po_history` skipped twice), 0 timeouts, 11 s.
- Confirms the supplier is deterministic for identical message sequences (as step 1 reproduced the 0.4531 path exactly). The repeat measures reproducibility, not variance; no new information about the supplier's floor.
- Sessions used: **3 / 3** (budget exhausted; sandbox: 2 runs / 4 sessions, free).

## Summary

| config | session | score | deal |
|---|---|---|---|
| fresh-h2 (reciprocal only) | `b1f6aa5ca78a0d5e` | 0.4531 | 5.40 / 90d / 24m / AS-14404 db0 |
| fresh-h1h2 (+ claim_pacing) | `6cae513938471768` | **0.5325** | 5.40 / 90d / 24m / AS-14404 db5 |
| fresh-h1h2 repeat | `98f007bf25a16be3` | **0.5325** | identical |

- `reciprocal_schedule`: no measurable effect on P18. It only shrinks our step to ≤ theirs; our score-push-v3 step is already 0.01–0.02. It also reads the ask off the cheapest-by-C sheet (the db5 alternative), so `their_step`/`held` describe the wrong sheet (reported held=true while the main sheet moved 5.50→5.40). Neutral; not harmful here.
- `claim_pacing`: +0.0794 vs the 0.4531 baseline, +0.0124 vs the previous best 0.5200. Mechanism: one verified index claim per message → one acknowledged concession per message (5.40 then 5.30 on the main sheet), and the db5 alternative dropped to 5.40, which is cheaper by C than 5.30 db0. The deep-bank scorecard claim was verified but produced only a verbal response.
- Left on the table: we never countered below the supplier's standing/alternative price once the gap-closed path triggered (r3 → 5.40 no clause, r4 → 5.40 db5). Supplier never said `final_offer`; its 5.30 db0 main sheet shows room for a 5.30 db5 ask (~€4.7k ≈ +0.06 score if accepted).
- Recommendation: `claim_pacing` is a merge candidate for P18 on the score-push-v3 base (2/2 identical 0.5325, deterministic). `reciprocal_schedule` can be dropped or kept off (no effect). Next lever (separate budget): on a `gap closed: take alternative` where the main sheet's nominal price is lower than the alternative's, counter once with the alternative's clause at the main sheet's price (5.30 db5) before taking the alternative; and fix `_supplier_asks` to track the standing sheet when measuring reciprocity.

## 2026-10-11 — P18, `alt_clause_counter` (5.30 + db5 counter before taking the alt) — PRACTICE session 1

Worktree: `/Users/sametdegirmenci/Downloads/ysamet-p18-db5/tacto-negotiator`, branch `codex/fresh-p18-db5` @ `335de9e` (= `3bf3959` codex/fresh-pacing with the P08 fixes + one commit: policy flag `alt_clause_counter`, default off). Config `configs/p18-alt-counter.json` = `fresh-h1h2-run.json` (the 0.5325 config: score-push-v3 + `reciprocal_schedule` + `claim_pacing`) + `alt_clause_counter: true`; `trace_dir` injected inline (`experiments/traces/fresh-p18-altdb5-s1`). `ARENA_DATA` = main checkout `data/package`. Budget: 1 practice session.

### Mechanism
On `gap closed: take alternative` while the supplier is `open` and more than two of our moves remain, counter ONCE with the alternative's package at the standing sheet's nominal price (here 5.30 with the deadband-5 clause) before taking the alternative; never on a `final_offer`; once per thread (rebuilt from history after a restart); never a sheet already sent; only when the counter beats the alternative by C. If the supplier stays `open` without taking it, the next decision takes the alternative as today (`alt clause counter declined: take alternative`); a `final_offer` runs today's `_final_counter`/accept. Unit tests `tests/test_alt_clause_counter.py` (8). Offline: 25 saved P01–P11 replays and 6 older P18 replays identical flag on/off.

### Replay gate (rebased code, before launching)
`tools/replay_decisions.py --cases case:P18`, A = `fresh-h1h2-run.json`, B = `p18-alt-counter.json`, on the two 0.5325 transcripts (`6cae513938471768`, `98f007bf25a16be3`): A reproduces the saved transcript in every round (sheets, action, refs and body: r1 `idx:AS-14404@2026-06→09`, r2 `idx:PPI-C2431@2026-06→08`, r3 `sc:70740@2026Q3`, r4 5.40 db5, r5 accept) — the P08 fixes (own_quote gating, standing-sheet step, no identical resend) do not touch P18's path: P18 never cited an own_quote, and the r2 reciprocal step was 0.02 before and after (their_step now read 0.70 off the standing sheet instead of 0.60 off the alt, still ≫ our schedule step). B differs from A only at r4: 5.40 db5 → 5.30 db5. Gate passed → session launched on the rebased commit.

### Run `a2becc8e-ef00-4f07-8d0c-50161bbaaa74` — fresh-p18-altdb5-s1
- Session `8d99154852112dbf`, replay https://arena.tacto.ai/replay/8d99154852112dbf, commit `335de9e` (clean). Quota 329→328.
- **Score 0.5324730606** — identical to the 0.5325 best (delta 0.0000). Winner `offer:70740-4`: 5.40 / 90d / 24m / AS-14404 share 0.45, **deadband 5.0**, base 2026-08. c_deal 256,557.24 (c_alt 301,088, c_best 222,651, c_open 295,173); index clause 1,152 + risk 1,152; payment −1,706. 5 rounds, 0 timeouts, 41 s wall, 0 model calls, no error.
- Sequence (supplier main / alt → ours):
  - r0 supplier 6.10 (30d, 12m, no clause).
  - r1 us 5.37 no clause + `idx:AS-14404@2026-06→09 −5.5 %` → **verified**. Supplier 5.40 db0 / alt 5.50 db5 (90d, 24m).
  - r2 us 5.39 + `idx:PPI-C2431@2026-06→08 −2.3 %` → **verified**. Supplier 5.30 db0 / alt 5.40 db5.
  - r3 us 5.40 no clause (`gap closed: their price, our terms`) + `sc:70740@2026Q3` OTD 81.0 % → **verified**. Supplier held 5.30 db0 / 5.40 db5, status `open`.
  - r4 us **5.30 db5** — `alt_clause_counter` fired (trace: standing_price 5.30, alt_price 5.40, c_counter 251,806 vs c_alt_sheet 256,557, moves_left 7). Identical to the 0.5325 runs up to here (byte-identical messages r1–r3).
  - r4 supplier **`final_offer` 5.40 db5** (alt dropped, main sheet replaced): "This is our final offer (letztes Angebot). Please decide. … We note your preference for the AS-14404 index clause with a 5 % deadband, which requires a price of €5.40 per unit. You mentioned an unchanged annual volume; please provide the exact volume figures … A binding higher volume would help us and can improve the price. … valid for 7 days."
  - r5 us accept (`final_accept_safe`: gain 0.0, loss 44,531, p_walk 0.25 → `all final offers`) → `agreed`. The fallback (`alt clause counter declined`) did not run — the supplier went `final_offer`, so today's final path accepted.
- Claims: 3/3 verified (same three as the 0.5325 run), none contradicted/irrelevant/duplicate. No claim attached to the r4 counter (deep bank exhausted / `po_history` skipped).
- Diagnosis:
  - The anticipated risk materialised exactly: the supplier answered 5.30 db5 with a `final_offer` at 5.40 db5 — the same sheet we would have taken anyway — and dropped the 5.30 db0 main sheet. Net effect zero: same deal, same C, same score, one extra round (5 vs 5 rounds counted; +1 supplier message). It did not walk and did not worsen the sheet, so the counter is free downside-wise on this supplier but bought nothing.
  - The supplier's text names the 5.30/5.40 split as a fixed pricing of the deadband ("5 % deadband … requires a price of €5.40"): the db5 clause is priced at +0.10 and it does not trade it against the base price. Its only stated lever for a lower price is a binding higher volume.
  - Confirms `final_offer_risk` handling: `_final_counter` saw gain 0 (its final is already the cheapest sheet on our terms) and accepted without a counter, as designed.
- Verdict vs 0.5325: **equal** (0.5324730606 vs 0.5324730606, delta 0). n = 1 session, 0 wins, 1 tie.
- Merge recommendation: **do not merge yet** (needs n = 2 wins; current n = 1, tie). The flag is harmless on this supplier (deterministic: the same message sequence reproduces exactly, so a repeat would also tie) — a second identical session cannot produce a win. To get a different outcome the counter would need to change the supplier's input: e.g. (a) counter with a volume commitment sentence (the supplier explicitly asks for binding volume to improve price; `bundle_volume`/`bundle_commitment_types` is only wired for `bundling`), or (b) counter at 5.35 db5 (split) instead of 5.30 — untested, speculative. Keep `alt_clause_counter` off in the shared config; keep the code (flag-gated, 758 tests green) for a volume-backed variant.
