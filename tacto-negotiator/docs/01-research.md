# 01 - Research findings

Each finding carries a label (FACT / INFERRED / HYPOTHESIS) and how to reproduce it.

## R1. The kit's play loop is serial - RFQ threads will collect timeouts (INFERRED, high confidence)

- `arena_kit.play.play()` decides one move, sends it, and **blocks** on that supplier's reply
  (up to ~1 min). `LLMAgent` and `NaiveAgent` pick **one** supplier per decision.
- `arena_kit.sim._tick` (the simulator mirrors the arena's rules): every thread whose clock passes
  60 s since the supplier's last move gets a timeout, **repeatedly every 60 s**; each timeout uses
  a round; 3 in a row or one after the last round close the thread. A buyer move resets the count.
- So in a 2-3 supplier RFQ, idle threads burn rounds and can close while we wait on another.
- **Action:** bounded per-thread scheduling plus one closing coordinator. The official client warns
  about per-session queuing; async alone does not establish that clocks stop while queued. Verify on sandbox
  `case:D02` (free) in the first hour with the key.

## R2. Plan initially for 4–6 messages; measure actual budget (INFERRED)

8 min cap − 90 s kit close margin ≈ 6.5 min of play. Each round ≈ decision (5-30 s) + supplier
reply (up to ~60 s). Expect **4-6 buyer messages per thread**. Round 1 must carry information
(MESO probes, a question, the strongest claim). Plan the concession path for 4 steps.

## R3. Lever magnitudes (MEASURED LOCAL; baseline-dependent)

Explicit audit baseline for S03: price €229, payment 60 days, contract 24 months, DAP;
fixed case terms retained. C = €3,888,420. This is illustrative, not a hosted quote.

| Change | ΔC |
|---|---|
| Price −1% | −€38,884.20 |
| Payment 60→14 days | +€39,748.29 |
| Payment 60→90 days | −€25,922.80 |
| Contract 24→12 months | +€288,337.38 |
| DAP→EXW | +€110,879.40 |

Lead time is fixed at 35 days in S03, so its €200/day late coefficient is not a negotiable lever.
`tools/lever_sensitivity.py` uses a different baseline (current price ×1.05 and complete_offer
defaults); its deltas must not be mixed with this table.

- For a move from reference payment terms with other effects fixed: let x = r · days_saved / 360.
  Exact discount = x/(1+x), or 1.01188% for 60→14 days at 8%. The existing helper returns the
  approximation x; update it and its test before treating it as an exact threshold.
  Use the case's `interest_rate`, not 8 % by default.
- Coverage and Incoterm errors dwarf price haggling. Guards must check them on every accept.
- "Always cover the full need" is usually right because fallback > deal price, but it is a
  per-case computation, not a rule (HYPOTHESIS until checked per case).

## R4. Supplier personas are built from ~20 note templates (FACT)

`tools/build_dossiers.py`. Meeting/call notes are templated per trait; suppliers combine traits.
The brief says up to a third of hidden cases combine supplier and case types unseen in practice,
so **classify traits, don't memorise suppliers**.

| Trait id | Note template (abridged) | n | Lever hypothesis |
|---|---|---|---|
| `pricing_committee` | price changes > 2 % need pricing committee approval (meets every 2 weeks) | 17 | ask about approval; sub-2% steps are not a proven bypass |
| `wants_fast_payment` | "pay within 10 days, we'd grant a cash discount" | 16 | short payment_days ↔ price; cheap if their rate > ours |
| `volume_focus` | reviewing small accounts, focus on customers with volume | 11 | volume/contract length/bundling |
| `open_book` | owner offers to walk through calculation | 11 | ask for cost breakdown XLSX, argue line items |
| `idle_capacity` | second shift on hold, can take parts at short notice | 10 | volume fills capacity → price |
| `reference_customer` | Hollerau is an important reference customer | 8 | appreciation, relationship tone |
| `overdue_invoices` | complains our invoices are overdue | 7 | don't ask for longer terms; promise punctual payment |
| `partnership_owner` | kept old price for a quarter in 2022, expects partnership | 5 | reciprocity; avoid squeezing below margin |
| `liquidity_crisis` | bank watching every month, can't sign lower margin | 5 | test faster payment for a cash-value-preserving price trade |
| `stale_index_owner` | asks where we get index figures; own spreadsheet 2 years old | 4 | verified index data disarms |
| `not_tracking_costs` | hasn't followed material/energy prices since 2022 | 4 | same |
| `hedged_inputs` | bought material/energy forward until <date>, "not our reality" | 4+2 | indices may not persuade; verify checker outcome separately |
| `price_freeze` | head office froze reductions until Dec 2027; open on payment, call-off | 4 | price immobile; trade terms |
| `fixed_price_list` | price list applies to all customers; happy to discuss logistics/payment | 2 | same |
| `commitment_for_capacity` | additional volumes only against binding 12-month commitment | 3 | commitment + lead time |
| `multi_year_only` | standard items not discounted; only multi-year volume agreements | 3 | contract_months |
| `not_strategic` | our volumes "not strategic" any more, replies slower | 3 | weak leverage; may walk; close earlier |
| `idle_shop_floor` | half the shop floor idle, MD talks about cash and banks | 2 | distress: cash > price |

News topics per supplier (`news.topic`): `credit_downgrade`, `credit_watch`, `restructuring`,
`succession`, `short_time_work`, `free_capacity`, `full_order_book`, `allocation`, `chip_shortage`,
`energy_contract`, `refocus`, `big_order`, `new_plant`, `new_owner`, `approvals`, `renamed`.
`noise` (10 items) and `market` (7) are not supplier signals.

Other signals: `supplier_intel` (owner type, staff, equity ratio, credit index now vs. 12 m ago -
sup:70350 248→343, sup:70280 230→302), `negotiation_history` (asked vs. settled per renewal;
20 rows "accepted below full cost to keep the volume"), `invoices` (our payment lateness),
`scorecards` (colour, OTD, ppm), `should_cost` (5 % error for strategic/bottleneck parts' own
supplier plant, 5-15 % otherwise; country factors in `company.md`).

## R5. Partial index proxy vs. asked change (FACT for the arithmetic; relevance per supplier is HYPOTHESIS)

`tools/index_justified.py`: Σ weight × 12-month change over `cost_drivers` (weights sum < 1;
the calculation assigns zero change to the unmodeled portion; that is an assumption).

| Case | Asked | Partial proxy | Interpretation hypothesis |
|---|---|---|---|
| P01 Brandlhuber, volute casing 310010 | +9.5 % | +2.3 % | strong pushback with data |
| P13 Lindlbauer, coupling hub 320060 | +7.0 % | +4.6 % | moderate pushback |
| P17 Platinenwerk, PCBA 350030 | +8.0 % | +7.9 % | consistent with proxy; still evaluate competition and package trades |
| P02 Nordmark, motor 350011 | +6.5 % | **+11.2 %** | copper-based pushback is weak; other leverage may remain |
| P14 motor cable 350040 renewal | - | +27 % (copper) | consider index clause economics |

- These are **partial cost proxies**: driver weights cover only 57-75 % of cost for these parts;
  the calculation assigns zero change to the unmodeled portion; that is an assumption. Series end at different months (copper Sep 2026,
  producer prices Aug 2026, labour Jun 2026) - each claim window must end within the last
  12 months of *that* series. Independently reproduced by a second review (kit commit 1b5516b).
- Window choice is allowed: any two months of one series ≤ 12 apart, ending in the last 12
  months. From-peak moves: nickel −13.2 %, aluminium −10.4 %, AS-14404 −5.5 %, iron ore −10 %.
  Whether a cherry-picked window persuades is the supplier's business (HYPOTHESIS: test).
- FX: ECB-TRY +15.5 % (euro buys more lira → Turkish lira costs cheaper in €), PLN +2 %,
  CNY −7.6 %, HUF −6.8 %. FX series are **not** in `cost_drivers` → may read `irrelevant`. Test.
- Index clause in C: `new · share · max(0, |path| − deadband) · sign(path) + new · share · index_risk`.
  With other terms fixed, the clause alone helps when a fall exceeds deadband plus risk.
  A package with a clause may still win through a sufficient price concession. Compare total C.

## R6. Worked dossier: Brandlhuber (P01) (FACT)

- Should-cost `cost:310010` = €132.64 (own plant, ~5 % error) vs. current €126.53 and asked €138.55
  → current price is below this uncertain estimate; history: 4 × "accepted below full cost to keep the volume".
- Owner works from a 2-year-old spreadsheet and hasn't followed energy/material prices
  (`stale_index_owner`, `not_tracking_costs`) → verified PPI-D351 −3.7 % may disarm him.
- Asked us to pay within 10 days for a cash discount (`wants_fast_payment`).
- "Expects partnership in return" (`partnership_owner`); category castings = `stabilise` →
  relationship charge if we push him below sustainable margin.
- HYPOTHESIS: best package = index argument + faster payment + later effective date, price
  between should-cost and ask; pushing toward €126 stalls him and costs relationship.

## R7. Literature (FACT about the papers; transfer to this arena is HYPOTHESIS)

- **Deterministic offers + LLM narration**: OG-Narrator raised buyer deal rate 26.7 % → 88.9 %
  with ~10× profit (Xia et al., arXiv 2402.15813). Matches the kit's "numbers from code".
- **MESOs** (2-3 equivalent packages at once): stronger anchors, perceived sincerity, more joint
  value, better relationship (Leonardelli, Gu, McRuer, Medvec, Galinsky 2019, OBHDP 152:64-83;
  Medvec & Galinsky 2005). Supports sending up to 3 term sheets - equal C for us, different mixes.
- **LLM failure modes**: anchor at extremes, ignore leverage, rarely probe/listen (<5 % vs 30 %
  of human strategies) (arXiv 2512.13063); 40 %+ of failed open-model deals were within one
  concession (AgenticPay, arXiv 2602.06008); buyers leak budgets when asked (arXiv 2506.00073);
  unstable anchoring/backtracking (MERIT, ACL 2026). → explicit close-the-gap rule, monotone
  concessions enforced in code, leak guard, ask questions.
- **Price-increase practice** (procurement playbooks: exosproc, Procurement Academy, Karrass):
  decompose by cost-driver weight, challenge the unexplained residual ("our decomposition
  supports ~X %, what accounts for the rest?"), trade structure (timing, term, payment, symmetric
  index clause with deadband), require a "get" for every concession.

## R8. Models and latency (FACT as of 10 Oct 2026 public leaderboards; measure ourselves)

- 60 s per move. Reasoning models at high effort can take 20 s - minutes before the first answer
  token (Artificial Analysis TTFT includes reasoning). Low effort / non-reasoning modes answer in
  ~1-20 s. **Measure p50/p95 with our actual prompt size from the venue network** before choosing.
- Kit default: `LLM_PROVIDER=anthropic`, `LLM_EFFORT=low`. Kit timeout 45 s, then naive fallback.
- Decision: one fast in-loop writer (p95 ≤ 20 s), one strong prep model offline (no clock).

## R9. Arena status (FACT, Sat 11:24)

`/health` ok; Sunday release not public until 06:00 UTC; practice leaderboard had 0 teams.
`/live` shows "House agent beaten" - Tacto runs a house baseline agent; beat it early.

## R10. Data and prototype limitations

- Listed weights cover 57–75% for the five examples. Copper ends September 2026, producer
  prices August, labor June. Do not call this a complete fair-price calculation or normalize
  the partial weights to 100% without evidence. Cite supported component claims externally.
- Latest copper year-over-year is +47.73%. TRY per EUR +15.515% implies unchanged TRY costs
  are 13.431% cheaper in euros; inflation, imported inputs and hedging remain unknown.
- company.md and row-level should_cost distinguish supplier-specific plant estimates (~5% error)
  from German-base estimates (5–15%). Join on supplier and part, inspect price_unit and avoid
  applying country factors twice. Neither is the supplier's known private floor.
- Existing dossier tooling reads base SQLite only. Sunday facts, CSVs and letters require an
  overlay loader. Existing index tooling assumes 13 observations span a year and defaults missing
  series to zero; production validation must use calendar months and flag missing data explicitly.
- Claim verification is not persuasion. A hedge can weaken an argument without making its
  arithmetic false or its checker status irrelevant. Template recognition is a first pass;
  unfamiliar/contradictory wording needs an uncertainty-aware interpretation fallback.
- Literature findings motivate experiments; benchmark gains are not predicted arena results.

Primary audited source: kit commit 1b5516bb95ef28e37f69aa446dc62168864bca53. See docs/README.md.
