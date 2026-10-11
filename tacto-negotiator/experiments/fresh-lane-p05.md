# Fresh lane P05 — `supplier_payment_trade` (+ `claim_pacing`) on score-push-v3 base

Worktree `/Users/sametdegirmenci/Downloads/ysamet-lane-p05/tacto-negotiator`, commit `f5c3c43`
(dirty only by the untracked `data` symlink). Configs `configs/fresh-h3-run.json` (score-push-v3 +
`supplier_payment_trade`) and `configs/fresh-h3h1-run.json` (same + `claim_pacing`) passed inline to
`lab run --config` (json.loads, no `@file`) plus `trace_dir=experiments/traces/<run-name>` so decision
events land in `experiments/traces/<run-name>/trace.jsonl` inside the worktree. `ARENA_DATA` = main
checkout `data/package`. Runner `async`. Budget: max 3 practice sessions.

References: P05 best 0.8136 = run `p05-fast-payment-O` (archive `ysamet-run-archive/ysamet-p05/runs/
e287dd70-…`, session `0da0416bc3b03ba2`, config = hold + rival-offer + history + undercut re-anchor +
data claims + `fast_payment_types: ["rfq"]`, LLM on): sup:70210 36.00 → 32.00/30d → 28.50/30d →
(we: 26.79 / **14d** / 35d, PPI-D351 claim) → **28.00/14d/35d** "The 14 days payment term is good for
us, so I can come down to €28.00 for that" → accepted. Best non-fast-payment P05 = 0.7723.

Sessions used so far: **0 practice** (+1 sandbox, free).

## Step 0 — sandbox mechanics (free)

### run `051d7188-7aab-4cfb-a9e3-bd1ccc8c626a` — `fresh-sandbox-p05lane-s1`, D02 (2-supplier RFQ), session `9ff66067d5ff93e1`
- replay <https://arena.tacto.ai/replay/9ff66067d5ff93e1>, commit `f5c3c43`, config fresh-h3-run.json + trace_dir.
- Completed, `error: None`, 0 timeouts, 7 rounds, 64.5 s, score 0.5239, deal DEMO-J1 15.20 / 30d / 28d / DAP.
- Trace `supplier_payment_trade` fired once per thread, both `trigger: signal`:
  - DEMO-J1: prev 60 → 30 d, rate 0.08, value_parity 14.95 = cost_parity 14.95 → offered 14.95/30d after
    its 15.70/30d. Verbatim: "Thanks for agreeing to the 30 days payment, that helps us out. I can meet you
    at 15.30 EUR" → 15.20 → accepted.
  - DEMO-C1: prev 60 → 14 d, 13.93 (parity) after its 16.80/60d | 16.70/45d. Verbatim: "we appreciate your
    willingness to offer 14-day payment terms, which allows us to provide a more competitive price. We can
    offer EUR 16.60" → 16.40/14d.
- Claims: rival-offer citations only (offer:DEMO-C1-0, offer:DEMO-J1-1/-2), all `verified`. No
  `contradicted`. Message body carries the "We can pay within N days; the attached unit price reflects
  that faster payment." line. → proceed to practice.

## Step 1 — practice P05, `fresh-h3-run.json`

### run `7d01d937-af2e-4d13-9b2c-f948eef23d72` — `fresh-p05-h3-s1`
- session `e76ada1d818ad035`, replay <https://arena.tacto.ai/replay/e76ada1d818ad035>, commit `f5c3c43`,
  config = `configs/fresh-h3-run.json` + `trace_dir=experiments/traces/fresh-p05-h3-s1`.
- **Score 0.6086** (0.8136 best −0.205; 0.7723 non-fast-payment best −0.164). Deal offer:70210-2 =
  **30.09 / 30d / 35d**, c_deal 255,570 (c_open 305,545, c_best 223,424; payment_terms +1,685, quality +1,129).
- 7 rounds (only 2 buyer moves per thread), 51.6 s, 0 timeouts, `error: None`, must-haves ok. Round 1 at
  t+0, round 2 at t+1–3 s, 70210 "agreed" reply, close (accept offer:70210-2) at t+48 s.

| supplier | r0 ask | our r1 | r2 ask | our r2 (trigger) | r3 ask |
|---|---|---|---|---|---|
| 70210 | 36.00 | 31.68/90d/35 + rival offer:70240-0 @31.50 | 32.00/30d/35 (verified) | **30.09/30d/35** `supplier_payment_trade` trigger `trait:offers_skonto`, prev 90→30, rate **0.30** (skonto cap), value_parity 30.09, cost_parity 31.26 → 30.09; + sc:70210@2026Q3 80.8 % | **agreed** at 30.09/30d |
| 70240 | 31.50/52d | 27.72/90d/35 + sc:70240@2026Q3 62.5 % | 34.00/90d \| 33.50/45d (verified) "90 days payment is way too long for us … Faster payment is welcome" | **27.25/14d/35** trigger `signal`, prev 90→14, rate 0.08, value=cost parity 27.25; + rival offer:70210-1 @32.00 | 33.00/14d (verified) — open |
| 70250 | 38.50 | 33.88/90d/35 + rival offer:70240-0 | 34.00/30d/35 (verified) "Faster payment is welcome" | 34.00/90d "gap closed: their price, our terms" (no trade: gap-closed branch precedes `_payment_trade`) + rival offer:70210-1 | 33.00/30d (verified) — open |

Verbatim reactions to the payment term:
- 70210 (round 2 → agreed): "you got me there with the delivery numbers, I checked and you are right. … We
  can accept your terms and await your order. Ourangebot is a price of €30.09 per unit, Zahlungsziel 30 days
  net, Lieferzeit 35 days. We keep the 30 days payment and 35 days lead time, let's get this done."
- 70240: "Thanks for offering 14 days payment, that really helps us out! With the 14 days payment, I can drop
  the price to €33.00 per unit." (33.50/45d → 33.00/14d: 0.50 for 31 days faster).
- 70250: "If you can pay in 30 days, I can drop the price to €33.00 per unit." (we never offered 30 d to it).

Claims: all `verified` (rival offer:70240-0 ×2, sc:70240 62.5 %, sc:70210 80.8 %, rival offer:70210-1 ×2).
No `contradicted`/`irrelevant`. No walk-aways, no final offers; coordinator closed on "sup:70210 agreed".

Diagnosis:
- The lever fired for 70210 at the first opportunity (round 2, trait trigger, no supplier signal needed) and
  priced the 90→30 d switch with the skonto-implied rate capped at 0.30: 31.68/90d → 30.09/30d (−1.59). That
  is 1.17 below our own cost parity (31.26), i.e. we gave away C-value to the supplier, and — worse — 30.09 at
  its own standard 30 d was inside 70210's acceptance zone, so it accepted instantly. The thread never reached
  the rival re-anchor cascade (32.00 → 28.50 → 28.00) that produced 0.8136; there 14 d was offered only at
  round 3 after 28.50, from a 26.79 anchor.
- Early acceptance by the leader closes the case (coordinator accepts on "agreed"); 70240/70250 were still
  open at 33.00. Net effect −0.16 vs the best non-payment config.
- 70250 never got a payment swap: its 34.00/30d reply closed the gap against our 33.88/90d, so the
  gap-closed branch returned first (34.00/90d "their price, our terms").
- 0.08-rate swaps (70240) are cost-neutral for us and bought only 0.50; the 0.30-rate swap (70210) was the
  costly one and the one that ended the case.

Sessions used so far: **1 practice** (+1 sandbox).

## Step 2 — practice P05, `fresh-h3h1-run.json` (+ `claim_pacing`)

### run `d098b465-211f-46c1-8140-b2799fd32d25` — `fresh-p05-h3h1-s1`
- session `e6f78cf1558cf48f`, replay <https://arena.tacto.ai/replay/e6f78cf1558cf48f>, commit `f5c3c43`,
  config = `configs/fresh-h3h1-run.json` + `trace_dir=experiments/traces/fresh-p05-h3h1-s1`.
- **Score 0.6086** — identical to Step 1 to the last digit (0.6085543). Deal offer:70210-2 = 30.09 / 30d / 35d,
  c_deal 255,570. 7 rounds, 8.9 s wall, 0 timeouts, `error: None`.
- Transcript is byte-identical to Step 1 in all three threads (same asks, same offers, same supplier prose,
  same `verified` results, same `supplier_payment_trade` events: 70210 `trait:offers_skonto` 90→30 @0.30 →
  30.09; 70240 `signal` 90→14 @0.08 → 27.25; 70250 none). The P05 suppliers are deterministic for a
  deterministic buyer.
- `claim_pacing` had no effect: in both configs `evidence_selection` already reported `available_slots: 1`,
  queue `preferred`, one scorecard claim per message; the "deeper bank" never came into play because the
  case ended after our second move.

Step 3 condition (beat 0.7723) not met → stopped. Sessions used: **2 practice** (+1 sandbox). 1 practice
session of the 3-session budget left unused.

## Conclusion for this lane

- `supplier_payment_trade` as implemented is a regression on P05 (0.6086 vs 0.7723 base, vs 0.8136 best):
  −0.164 / −0.205.
- Mechanism: for 70210 the trait trigger (`offers_skonto` in master data) fires at our first post-opening move
  and prices the 90→30 d switch with the skonto-implied 0.30 rate, i.e. 1.17 €/unit below our own cost parity
  (30.09 vs 31.26). 30 d is 70210's own standard term, so 30.09/30d landed inside its acceptance zone and it
  agreed immediately — before any of the rival re-anchors (31.50 → 32.00 → 28.50 → 28.00) that carried the
  0.8136 run. In that run the 14-day offer came one round later, after 70210 had already said 28.50/30d, and
  at 26.79 (below its standing price), so it answered with a counter (28.00/14d), not an acceptance.
- The 0.08-rate `signal` swap (70240, 90→14 d at 27.25) is cost-neutral for us and bought 0.50 (33.50/45d →
  33.00/14d) — harmless but weak.
- 70250 ("Faster payment is welcome", standard 30 d) never gets the lever: the `gap closed` branch runs first.

Recommendation: do not ship `supplier_payment_trade` for RFQ in this form. If retried (separately budgeted):
(a) gate the trait trigger behind a supplier payment *signal* or behind the re-anchor stage (`sid in
self.reanchored` or ≥ 2 supplier price moves), never on the first counter; (b) price the swap at
`max(value_parity, cost_parity)` or use the public 0.08 rate instead of the capped skonto rate — giving away
value below cost parity is exactly what made the offer acceptable; (c) pick 14 d (the shortest legal term)
rather than the supplier's stated 30 d for 70210, as in the 0.8136 path; (d) consider letting `_payment_trade`
run before the gap-closed branch so 70250's "faster payment welcome" can be answered.

## Step 4 — staged (NOT run): archived 0.8136 lever on v3, `configs/p05-fast-payment.json`

Worktree `ysamet-lane-p05`, detached on `codex/fresh-pacing` f5c3c43. Config = `score-push-v3.json` with
`fast_payment_types: ["price_increase", "rfq"]` (v3 list + `rfq`; for an RFQ case identical to the archive's
`["rfq"]`). `supplier_payment_trade` and `claim_pacing` absent (False). Loads via `PolicyConfig.from_dict` /
`configured_agent`; policy sha256 `8370bb59…13fdc`. Config-key drift vs archive `50b271c:configs/p05-fast-payment.json`:
archive-only `preferences {quality: lower_chargeback}`; v3-only `package_advice_types`, `cost_target_types`,
`cost_target_index_clause`, `cost_target_posterior`, `standard_payment_types`, `recent_index_window_types`,
`bundle_volume_types`, `bundle_commitment_types`, `value_swap_*` — none of these keys covers `rfq`, so no
config-level effect on P05. The archive config itself still validates on the HEAD loader.

**Blocker — the archived lever is not on this branch.** 50b271c sits on `archive/codex/score-push-p05`
(forked at a913ac3, never merged). There `fast_payment_types: ["rfq"]` meant `_rfq_fast_payment`: at the
one-time `rfq_undercut_reanchor` counter, move to 14 d iff the supplier wrote "faster payment is welcome" and
the sheet is C-cheaper (fd195f3). On `codex/fresh-pacing` the same key is the P01 lever (04d40ce):
`_fast_payment` gives the shortest legal term from the **first offer** to suppliers with the public
`wants_fast_payment` trait. P05 traits (HEAD data): 70210 `offers_skonto` (no `wants_fast_payment`),
70240 none, 70250 `wants_fast_payment`.

Offline evidence (no src changes):
- `tests/test_score_push_v3.py`, `test_supplier_payment_trade.py`, `test_rfq_final_guard.py`: 26 passed.
- Archived test `test_rfq_fast_payment_only_when_asked_and_cheaper_in_c` (fd195f3) run inline against HEAD +
  this config: re-anchor move = 27.26 / **90 d** (expected 14 d) → FAIL; the late 14-day path does not exist.
- `tools/replay_decisions.py` on the saved 0.8136 transcript (`ysamet-run-archive/ysamet-p05/runs/e287dd70…`),
  A = v3, B = this config: 70210 r7 (saved 26.79/14d re-anchor) → both A and B produce 26.79/**90d**; r10
  (saved 28.00/14d) → 28.00/90d. B differs from A only on 70250: 33.54/**14d** on its *first* offer (r2/r3,
  + "Your note doc:20260904-70250-M4 asked whether we could pay faster…"), then 33.61/14d, 32.88/14d. Same
  pattern on the fresh-p05-h3(h1)-s1 transcripts. I.e. the lever fires early, on the wrong supplier.
- Sandbox D02 (free) `fresh-sandbox-p05fp-s1`, run `09db7fd4-8d75-437b-bc49-19dc8b9bb100`, session
  `7e186d6012ee2c4d`: completed, `error: None`, 0 timeouts, 9 rounds, 8.7 s, 0.5239 (= h3 sandbox; no
  `fast_payment` trace event — DEMO suppliers lack the trait). Mechanics only.

Verdict: a hosted run of this config is **not** a repeat of 0.8136 — expected outcome ≈ the v3/F path
(0.7723) for 70210 plus a 14-day first offer to 70250. A true repeat needs `_rfq_fast_payment` ported into
`agent.py` (src change, separately approved). Hosted session NOT started. Sessions used this lane: 2 practice
(+2 sandbox).

## Step 5 — port the archived lever, repeat 0.8136 (n=2) — branch `codex/fresh-p05-fp`

Branch `codex/fresh-p05-fp` from `codex/fresh-pacing` 3bf3959 (incl. P08 fixes), worktree `ysamet-lane-p05`.
Commits: e592dc5 (cherry-pick of the staging config), **e8b0396** (port), + log commit.

Port: `_rfq_fast_payment` from fd195f3 verbatim into `agent.py`, under the NEW flag
`rfq_fast_payment_reanchor: bool = False` (`policy.py` field + bool validator). Hooked only inside the
one-time `rfq_undercut_reanchor` branch: iff the supplier's own e-mails contain "faster payment is welcome"
and the re-anchored sheet at the shortest legal term is C-cheaper than its standing sheet → 14 d, body gets
"You wrote that faster payment is welcome: we offer payment within 14 days; the attached unit price
reflects that discount.", `self.prev` keeps 14 d, revert guard `fast_payment_traded` (as the archived
`lead_traded`) restores the old package if the next reply is not cheaper. `fast_payment_types` untouched
(P01 trait lever; config keeps v3's `["price_increase"]`). `supplier_payment_trade`/`claim_pacing` off.
Trace events: `undercut_reanchor`, `rfq_fast_payment`, `rfq_fast_payment_revert`.

Tests: `tests/test_rfq_fast_payment_reanchor.py` (4): flag validation; archived
`test_rfq_fast_payment_only_when_asked_and_cheaper_in_c` on the new flag; never before the re-anchor / never
for a supplier that did not ask (rival asked only → 90 d); saved 0.8136 transcript (fixture
`tests/fixtures/p05_fast_payment_run.json`) replays 26.79/14d at r7 and 28.00/14d at r10 with the flag, and
with the flag off equals the recorded 3bf3959 decisions. `ruff check src tests tools` clean; `pytest -q`
**756 passed**. Byte-identical check: `tools/replay_decisions.py` A=v3 on the ported code vs A=v3 on a
3bf3959 worktree → 12/12 rounds identical. B = v3 + flag: first A≠B at r7 (70210 payment 90 → 14), r10
28.00/14d; 70240/70250 rounds identical to A (70250 never gets 14 d).

Config `configs/p05-fast-payment.json` = `score-push-v3.json` + `rfq_fast_payment_reanchor: true`
(policy sha256 `b5b81dff4b65…`). Single diff vs v3; vs the archive config the only P05-relevant difference is
the flag name (`fast_payment_types: ["rfq"]` → `rfq_fast_payment_reanchor: true`).

### run `a1c2e3ea-a3bc-4284-86d1-33f0abc7d977` — `fresh-p05-fp-s1`, practice P05
- session `1cde0b704685b2bd`, replay <https://arena.tacto.ai/replay/1cde0b704685b2bd>, commit `e8b0396`
  (dirty only by untracked `experiments/traces/`), config above + `trace_dir=experiments/traces/fresh-p05-fp-s1`,
  runner async, `ARENA_DATA` = main checkout `data/package` (sha `dfcb322f…`), LLM 0 calls.
- **Score 0.8136** (0.8135787539306429 — identical to the archive run to the last digit). Deal
  offer:70210-4 = **28.00 / 14d / 35d**, c_deal **238,733.23** (c_open 305,544.96, c_best 223,424.17;
  payment_terms 2,404.27, quality 1,128.96). 13 rounds, 42.8 s, 0 timeouts, `error: None`, must-haves ok.
- 70210: 36.00 → we 31.68/90 (+rival offer:70240-0 @31.50) → 32.00/30 (verified) → we 31.74/90
  (+sc:70210 80.8 %) → **28.50/30** "Faster payment is welcome; we can reflect it in the price" →
  **we 26.79/14/35** (trace `undercut_reanchor` their 28.5 ours_last 31.74 counter 26.79; `rfq_fast_payment`
  14 d @26.79) + PPI-D351 −3.7 % claim → **28.00/14/35** open: "The 14 days payment term is good for us, so I
  can come down to €28.00 for that. … Let's lock this in" → we match 28.00/14 → agreed → accept.
- 70240: 31.50/52d → we 27.72/90 (+sc 62.5 %) → 34.00/90 | 33.50/45 → we 28.88/45 (+offer:70210-1) →
  33.00/45 → we 29.83/45 (+offer:70210-2) → 32.50/45 → we 30.59/45 (+offer:70210-3) → 32.50/45 **final**.
- 70250: 38.50 → we 33.88/90 (+offer:70240-0) → 34.00/30 → we 34.00/90 (+offer:70210-1) → 33.00/30 →
  we 33.00/90 (+offer:70210-2) → 32.00/30 → we 32.00/90 (+offer:70210-3) → 30.00/30 **final**.
- Claims: 11 results, all `verified` (rival offers ×7, scorecards ×2, PPI-D351 ×1 …). No contradicted.
- Transcript is identical to the archive run (0da0416bc3b03ba2) in every 70210/70240 message; 70250 got one
  more round (30.00/30 final) because the case ran one round longer before close. Deterministic suppliers.

Comparison: 0.8136 archive (n=1) → **0.8136 repeat (n=2)**; v3/F 0.7723 → +0.0413 (C −3,391.73). The
0.6086 `supplier_payment_trade` path is −0.205 below.

**Verdict: 0.8136 repeated (n=2) — merge YES** (`rfq_fast_payment_reanchor: true` for the P05 config; flag
off is byte-identical to `codex/fresh-pacing`). Sessions used this lane: 3 practice (+2 sandbox); lane
budget exhausted. Open: the remaining .96 gap (~26.7 @ 14 d) — r4 matched 28.00 instead of pushing once
more; untested, separately budgeted.
