# 03 - Negotiation playbook

Everything here is HYPOTHESIS until an experiment in `experiments/LOG.md` supports it.
Policies are written so code can implement them; the LLM only words them.

## Hard checks and closing authority

1. Only the case coordinator may accept **or walk away**. Workers propose actions.
2. Every closing path—including `agreed`, deadline fallback and recovery—checks current offer
   validity, complete terms, must-haves, full C including supplier estimates, the alternative,
   other RFQ offers and unresolved requests. An agreement is not an instruction to accept.
3. Reject malformed/out-of-option packages and unsupported numerical claims. Removing an ID
   does not repair a false assertion. Render facts and our proposed terms from separate typed records.
4. Max 3 checked claims per message. Track used IDs per case, except eligible rival quotes/offers
   per recipient. Reserve usage atomically across workers.
5. Keep budgets, reservation/target prices, urgency and lack of alternatives private. Permit
   deliberate disclosure of a valid rival quote/offer, with a recorded reason.
6. Coverage, monotone concessions, three-package offers and trait responses are policies to
   evaluate, not hard constraints. A costlier offer may repair an infeasible standing package.
7. Initially reserve max(90 s, slowest round +15 s) before the wave cap. Measure queued acceptance
   and adjust. The fallback must use our relationship-aware evaluator, not kit closing_move unchanged.
8. On final_offer, compare safe acceptance against the estimated gain and risk of another move.
   On agreed, submit a closing proposal. Never assume a universal number of extra pushes is safe.
9. Polite, factual, concise language; <=150 words is a team target, not an arena limit.

## Round plan (budget ~5 messages per thread)

| Round | Goal | Content |
|---|---|---|
| 1 | Anchor + learn | Thanks, acknowledge the relationship, 1-2 strongest verified claims, **1–3 distinct, feasible sheets**, approximately equal C with different mixes when testing MESOs against a single-sheet baseline; 1 question (cost breakdown / what drives the ask / earliest lead time) |
| 2 | Exploit what they picked | Move on the dimension they answered best; new claim if one remains; concession step 1 |
| 3 | Trade | Give on what is cheap for us, take on what matters (from beliefs); concession step 2 |
| 4 | Converge | Close-the-gap offer near target; signal it's near our limit without lying |
| 5 | Close | Accept best standing sheet that beats the alternative, or walk |

Concession schedule is a hypothesis. If using 50/30/15/5 percent, specify the denominator:
percentages of the initial gap sum to 100%; percentages of the remaining gap close only 71.7375%.
Use measured remaining time and supplier behavior; do not hard-code five usable rounds. Never
exceed the evaluated reservation, and distinguish a target from the alternative.

## By case type

| Type | Opening stance | Main levers | Watch out |
|---|---|---|---|
| `price_increase` | Decompose: index-justified vs. asked; challenge the residual | effective_date later, price, payment↔price trade, contract length for price protection | if asked ≤ justified (e.g. P02), don't argue indices - trade structure |
| `renewal` | Prior terms as baseline; their notice/letter vs. contract notice | contract_months, volume, price, payment, incoterm | price uncovered need and fallback risk; full coverage is not unconditional |
| `rfq` | Parallel threads; let quotes compete | rival quote claims (reveals price), MESOs to each, tooling, lead time | only one accept; keep all threads alive; don't reveal which is leading |
| `bundling` (kits) | One supplier for the kit; volume consolidation is our gift | price across the kit, contract length, logistics | routine goal: process cost; check every part covered |
| `raw_material` | Base price + surcharge clause design | index_clause (series, share, deadband, base month), base price | compare complete packages, including base-price concession and index risk |
| `capacity` | Secure supply first; commitment is our currency | volume_per_year, contract_months, lead_time_days, payment | `secure_supply`: relationship charge; don't squeeze |
| `quality` | Scorecard facts (sc/qn), 8D, cost recovery | ppm_commitment, chargeback_eur_per_complaint, price | `quality_first`: cost_per_defect dominates; red supplier may be distressed |

## By category goal

| Goal | Rates imply | Stance |
|---|---|---|
| `stabilise` | relationship charge below sustainable margin | keep the supplier's margin on **its cash value** (`arena_kit.cost.supplier_value`: price, payment timing at *its* rate, freight leg, tooling, chargebacks) at or above sustainable; win on terms that are cheap for us and valuable to it (e.g. faster payment to a cash-short supplier) |
| `secure_supply` | relationship charge; high fallback risk | cover the need, accept fair price, secure lead time/volume |
| `quality_first` | defect cost dominates | ppm + chargeback first, price second |
| `leverage` | competition; low fallback risk | push price; use rivals and data |
| `routine` | process simplicity | fast, fair close; don't burn rounds |

Supplier full-cost estimate for the relationship term: `should_cost` (own-plant rows ±5 %),
else German base × country factor (AT/CH 1.0-1.1, CZ/PL/HU 0.8-0.85, TR 0.75, CN 0.7), else
quotes/history. Run sensitivity (±10 % full cost, and the supplier's interest rate from traits:
higher for `wants_fast_payment` / `liquidity_crisis`) before choosing a target.

## By trait (see `01-research.md` R4)

| Trait | Do | Don't |
|---|---|---|
| `pricing_committee` | ask about approval authority; test price and non-price trades | assume repeated sub-2% moves bypass cumulative approval |
| `wants_fast_payment` / `liquidity_crisis` / `idle_shop_floor` | offer short payment for price (they value cash more than our r) | ask for longer payment; push price below their margin |
| `volume_focus` / `idle_capacity` / `multi_year_only` | offer volume / longer contract for price | split volume or shorten the contract |
| `open_book` | ask for the cost breakdown XLSX in round 1; argue its elements with indices | accept the headline without asking |
| `stale_index_owner` / `not_tracking_costs` | lead with verified index figures for their drivers | over-argue; one or two crisp figures |
| `hedged_inputs` | skip index claims on the hedged input until the hedge ends; consider clause after | confuse an unpersuasive claim with the checker status irrelevant |
| `price_freeze` / `fixed_price_list` | trade payment, call-off flexibility, incoterm, lead time | repeat price demands |
| `commitment_for_capacity` | binding 12-month+ commitment for lead time / allocation | ask for more volume without commitment |
| `reference_customer` / `partnership_owner` | appreciation, partnership framing, reciprocity | threats, ultimatums |
| `overdue_invoices` | acknowledge and commit to on-time payment | ask for 90 days |
| `not_strategic` | take a reasonable offer earlier; low walk-away tolerance | long haggling; it may walk |

## RFQ coordinator

- All threads progress in parallel; each answered within budget.
- Rival quote/offer claims: cite the cheapest rival's price to the others (it counts once per
  supplier and reveals it - acceptable in RFQs).
- Compare full C with standard terms and supplier estimates, not unit price.
- Close once through the coordinator after revalidation; both accept and walk-away end the case.
- Do not hold state locks across model or HTTP waits. Recheck snapshot versions before sending.

## E-mail style

- German industrial B2B tone, English language, polite, specific. ≤ 150 words.
- Structure: thanks/acknowledgement → 1-2 data sentences (figure + IDs) → the offer(s) in words
  → one question → sign-off "Hollerau Pumpenwerke, Purchasing".
- One argument per sentence; figure and ID in the same sentence.
