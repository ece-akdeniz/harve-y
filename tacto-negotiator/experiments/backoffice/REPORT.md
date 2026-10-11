# Supplier back-office digest — practice cases P18, P08, P05, P07, P10, P02

> **Status: pre-session intelligence only.** Everything below was read offline from our own ended practice sessions (`GET /v1/sessions/{sid}` and `GET /v1/sessions/{sid}/backoffice`, header `X-API-Key`). No session was opened, nothing was sent, no spectator endpoint (`/v1/events`, `/screen`, `/leaderboard`, `/results`) was touched. **Nothing here may be read, loaded or used by the agent at runtime**; it is for human preparation of tonight's screens only. Case-specific numbers below must not be hard-coded into policy.

Source: `tools/backoffice.py` (branch `codex/fresh-h4`), raw JSON + digests in this directory (`<case>-<sid>.json/.txt`). Fetched 2026-10-11 ~01:40 CEST.

## 0. Coverage and what is NOT in the data

- Session ids collected from `experiments/runs/*/run.json` (main checkout), `experiments/LOG.md`, `fresh-lane-*.md`, `coverage-20261010.json` and the h4/cb logs. 150 distinct 16-hex ids; 104 belong to the six cases and were saved: **P02 18, P05 30, P07 12, P08 12, P10 10, P18 22**. The other ids were D01/D02 sandbox or P01/P03/P04/P11 (skipped, not fetched for back office).
- **Back-office record: 104 of 104 sessions returned 200. Zero 404/403.** All sessions are from 2026-10-10, so there is no evidence on "older sessions do not expose it".
- The P05 0.8136 session (`0da0416bc3b03ba2`, `p05-fast-payment-O`) **is present** (found via `fresh-lane-p05.md`).
- **What the back office contains**: per supplier role and round: `My call: counter | hold | final_offer | accept | walk_away | answer`; `Read the buyer's e-mail: … term sheet[s] [and … cited fact(s) to check]; we answer with our offer / final offer / we agree / we withdraw`; attachments (`quote attached`, `order confirmation attached`, `delivery schedule attached`); delegations (`The buyer asks something for Freight Forwarder / Logistics / Legal Department / Credit Control / Quality Management; please answer`); and, only for two suppliers, an approval dialogue (P05 Owner→team `The buyer shows a much lower rival quote. I give half the step now and check the rest.` → team→Owner `Checked: give the rest of the step.`; P02 KAM→Pricing Committee `The buyer wants more than my band allows. Approve a further step?` → `Approved: you may go further, within our rules.`).
- **What it does NOT contain**: any figure (all redacted as `…`), the supplier's cost floor, margin, the size of the "band", the approval threshold (no "above X % needs committee" text anywhere), the trigger rules for hold/final/walk-away, and the supplier's reading of our tone. Claim verification verdicts are not in the `GET /v1/sessions` trace either (they only surface in the supplier's words: "it holds and we took it into account" / "it holds, but it does not change our calculation" / "does not concern this part or our company"). All floors below are therefore **inferred** from the lowest price ever observed plus the supplier's wording ("as low as I can go", "absolute limit"), not read from internal data.
- P08/P18/P07 back office is a single role (`Inside Sales`) talking to `team`; P10 `Segment Manager`; P02 `Key Account Manager` (+ `Pricing Committee`); P05 `Owner` (70210, 70250) / `Export Manager` (70240) + `team`.

## 1. P18 — sup:70740 Blankstahl Werdenfels GmbH (raw_material, 24 m, 23 700 kg/a) — 22 sessions

**Floor.** Lowest price ever observed: **5.30 / 90 d / AS-14404 clause deadband 0** (5 sessions; `c3d8d00deef782f2`, `193fd257d7a43c1e`, `7dd75ee1f6308fd6` at 0.5200; `98f007bf25a16be3`, `6cae513938471768` reached 5.30 standing then closed at 5.40 db5 = 0.5325). Nothing ever went below 5.30; the supplier never said "floor" there, it simply stopped moving once no new data came. The only explicit limit wording is for the 14-day configuration: r3 `we have already reached our limit for this configuration at EUR …`, r4 `EUR … per unit is the absolute limit we can offer for a 24-month contract with 14-day payment terms and the AS-14404 index clause` (`14b3fbcb0087b661`, 5.50/14 d). What sets the floor is **data, not patience**: without cited facts it stops at 5.40 (`Which figures is that based on? Please send us the data.`, 9 sessions); with verified index claims it goes to 5.30. No approval cap or committee exists in its back office (single role `Inside Sales`); our own request "please put this package to the committee" was answered with an immediate **final** (`68e50dcda140695c`).

**When and why final_offer.** Always `My call: hold` + `we answer with our final offer` at its **4th reply (round 4)** when we kept moving (12 sessions), or at its **3rd reply** when it had already held once (`My call: hold` at r2 → final r3: `195209b411efcbe0`, `b1c606cf7453017d`, `238bd4439a687497`, `98623f421f32fa5d`, `5d758509978bcc9b`) or when we asked for a committee / repeated a price without data (`68e50dcda140695c` final at r2). Internal note at final is just `My call: hold` — i.e. the final is a *hold*, not a last concession, in every 90 d run.

**What it said about our claims.** Two index claims in one mail (r1): `Acknowledging the recent index decreases you verified, we are pleased to offer a revised unit price of EUR …` → 6.10→5.50 (vs 5.60/5.70 without claims). One claim per round (`98f007bf25a16be3`): r1 AS-14404 −5.5 % → `We checked the index change data you cited; it holds and we took it into account … adjusted our pricing to reflect both the extended term and the recent AS-14404 index decrease` → **5.40 at once**; r2 PPI-C2431 −2.3 % → `We have verified the PPI-C2431 index decrease you cited and have adjusted our base price accordingly` → **5.30**; r3 scorecard OTD 81 % → `We have reviewed the delivery performance data you provided and are committed to improving our on-time delivery rate … we maintain our offer` → **no move** (back office delegated to Logistics). A volume forecast claim (`fc:370010`) was `checked … it holds and we took it into account` but bought nothing beyond the index claims (`68e50dcda140695c`). Three alternative packages without data: `We have carefully reviewed your alternative proposals … without new data, we cannot lower the price further` → hold → final 5.60 (`195209b411efcbe0`, 0.3191).

**Payment.** 90 d is accepted and priced in from r1 (`pleased to accommodate the extended 90-day payment terms`). 30 d deals land at the same 5.40 but score lower (0.406 vs 0.4531). 14 d: `the option for 14-day payment terms, which allows us to offer a more competitive rate` but the price stalled at 5.50 → 0.4062; worse than 5.40/90 d. Offering 3 sheets at 90 d incl. the clause: `the extended 90-day payment terms carry significant financing costs, making your proposed prices unfeasible` → hold.

**Index clause.** Mandatory for 24 m in every session (`a fixed price for a 24-month duration is not possible; the AS-14404 index clause is mandatory`). Refusing it to the end → **walk-away** at r5: `Since we cannot reach an agreement on the inclusion of the AS-14404 index clause, we must respectfully withdraw our offer.` (`cbf98484048a9282`, 0.0). Accepting the clause early buys nothing (`We appreciate your acceptance of the index clause … However, we cannot accommodate a further reduction in the base price`, `238bd4439a687497`). Its own alt is always +0.10 for deadband 5; for us db5 at 5.40 (idx cost 1.2 k) ≈ db0 at 5.30 (idx cost 6.8 k) → 0.5325 vs 0.5200.

**Convergence.** Whenever we matched its standing price it closed there: `We appreciate your agreement on the unit price of EUR …` → final (hold). Offering above its next step (5.45 after its 5.60 hold) → it **agreed at our 5.45** (`32e38ffae33fe908`), i.e. we paid for its move. In `98f007bf25a16be3` we offered 5.40 db5 while it stood at 5.30 db0 — accepted at once.

## 2. P08 — sup:70710 Edelstahl-Service Donautal GmbH (raw_material, 24 m, 94 800 units/a) — 12 sessions

**Floor.** Lowest ever **5.31 / 90 d / AS-14404 db0** (3 sessions at 0.5930: `4451a15ec9934f23`, `db8a3177ce4a77fb`, `ebc8321509c623e7`), reached at its r3 reply, then `My call: hold` + final at r4. Its steps shrink (6.05→5.45→5.36→5.31→hold); 5.31 equals our own opening anchor — it never went below what we opened with. No floor wording at all; the recurring internal/explicit lever is **volume**: `Which volume can you commit to?` every round and `A binding higher volume would help us and can improve the price.` We never answered the volume question in the 0.593 runs. At 36 m it kept conceding 0.05/round and went final at r5 at 5.36 while still moving (`6ddf266d690d2113`) — patience, not cost, ended it there.

**Final timing.** r4 (its 5th message) in all 24 m runs; r5 in the 36 m run; **r3** when we repeated an unchanged price: `We note that your proposal remains unchanged from the previous round. Having already made significant concessions, we must maintain our offer` → `My call: hold` + final (`a64f027775b49028`, 0.5044).

**Claims.** Only one session carried claims (`a64f027775b49028`): a quote claim `quote:7300008 … EUR 5.45` → `The rival quote data you cite does not concern this part or our company.` + `Which figures is that based on? Please send us the data.` (wrong claim, cost credibility; 5.45→5.43 only); scorecard OTD 88 % → `We have reviewed the delivery scorecard data you provided; while we continuously work on improvements, our overall performance standing remains solid` → 5.43→5.39 and `The buyer asks something for Logistics`. No index claim was ever sent to 70710 in our data — the P18 result (same index series AS-14404/PPI-C2431, same template supplier) suggests that is the untested lever.

**Payment.** 90 d accepted at 24 m (`can accommodate the requested 90-day payment terms`, priced in). 14 d sheet: `By adopting your suggested 14-day payment terms, we can reduce our financing costs and pass this benefit on to you` → alt −0.08/unit (5.57/90 d vs 5.49/14 d) — we took 5.49/90 d at the end (0.5271). Three-sheet openings (90 d | 14 d | idx) made its first reply **worse**: 5.65 vs 5.45 for a single sheet. 12 m fixed price: `We are willing to reduce our price to EUR …, provided we maintain our standard 30-day payment terms` → 5.84, 0.1562.

**Index clause.** Mandatory for 24/36 m; alt db5 is +0.12. db5 at 5.49 cost us idx 4.7 k vs db0 at 5.31 idx 27.2 k — for P08 the deadband is worth ~0.12/unit, so **ask for db5 at the db0 price** is the obvious untested trade.

## 3. P05 — RFQ, 3 suppliers (70210 Owner, 70240 Export Manager, 70250 Owner) — 30 sessions

**The only real approval mechanic in the data is here.** Every time a *rival-offer* claim undercut 70210's or 70250's standing price, the back office shows: Owner→team `The buyer shows a much lower rival quote. I give half the step now and check the rest.` and the e-mail says `We need to clarify this internally - we will come back to you on price.`; next round team→Owner `Checked: give the rest of the step.` and the e-mail `We have clarified this internally and can move further on the price.` So the "boss approval" is a **two-round split of one concession**, not a cap: the first reply gives half, the next gives the rest regardless of what we send. 70240 (Export Manager) never asks anyone; its back office only delegates `The buyer asks something for Freight Forwarder` when we mention lead time.

**70210 floor.** Without claims: 33.0→32.5→hold→32.0 (`We need the cash in … days … If we agree on … days, I'll drop the price`), final 32.0 at its 5th reply (0.4119, 7 sessions). With rival claim offer:70240-0 @31.50: 36→**32.0** (half) →**29.0** (`Your data on the market was solid, so I sharpened my pencil`) (0.7208, 8 sessions). Plus scorecard sc:70210 80.8 % in r2: `I checked the delivery scorecard you sent, and you have a fair point there. I respect solid numbers, so I am dropping the price to €… to make up for it and the other quote` → **28.5** (0.7723, `a7298b34c1e012d6`, `d48049c4678d0466`). Third claim PPI-D351 −3.7 % in r3: `I checked the PPI index you sent and you are right about the drop. But I already went as low as I can go last time, so … is my final offer` → `My call: final_offer` at **28.5/30 d** — cost floor stated in words. Undercut re-anchor 27.26 after 29.0: `I already gave you a massive drop to … EUR last time, so we have to stay there` → final 29.0 (`2ffdd9c5ee8c2b9d`).

**The 0.8136 session (`0da0416bc3b03ba2`).** Same path to 28.5/30 d, then in r3 we offered **26.79 / 14 d** with the PPI claim and the sentence "You wrote that faster payment is welcome: we offer payment within 14 days; the attached unit price reflects that discount." → `The … days payment term is good for us, so I can come down to €… for that` → **28.0/14 d**, `My call: counter` (not final); we matched 28.0 → `I see we have a deal`, `My call: accept`. So 14 d bought 0.50 **only after** the data claims had exhausted the price floor. Offering the payment trade early (`e76ada1d818ad035`, `e6f78cf1558cf48f`: 90→30 d at r2 with our 30.09) → 70210 **agreed at our 30.09** (0.6086): we closed on our own number before its second half-step arrived. Conceding 30 d early without claims (`a18a4bbf41f3245b`): `Moin, I can drop to €…, but that's where it stops for me` → final 32.5 at r3 (vs 32.0 when we kept asking 90 d). 70210 on 90 d, every session: `We need the cash in … days to keep the machines running` / `We are a small business and need the cash flowing`.

**70240 / 70250 on rival citations and payment.** 70240: `We checked the rival quote data you cited; it holds, but it does not change our calculation.` … `That other quote you have probably doesn't include this fast delivery and long payment.`; it concedes 0.5/round to 32.5 and holds (`we have already given you everything we can`). 70240 on 90 d: `… days payment is way too long for us`; on 45 d: `Thanks for the new numbers and for meeting us at … days payment!` (34.0→33.0). On 35 d lead: `our factory is totally packed right now, so … days lead time would cost a lot extra` (its standard is 52 d; 42 d accepted at once). 70250: same half-step/rest-of-step mechanic on rival claims (34.0→33.0→32.0→31.0), `If you can pay in … days, I can drop the price`, `we have to stick to … days payment`; 14 d: `… days payment works for us, cash is always good`. When we conceded to 30 d and sent 34.00 (its own standing price) it **accepted** (`My call: accept`, `a18a4bbf41f3245b` 0.2128) and the coordinator closed the case on the wrong supplier.

**Why suppliers walked away in the low runs.** Every P05 walk-away follows **our** silence, never our price: `Since I haven't heard back from you, I have to pull my offer. We need to keep our machines running and can't wait around.` (70210, `808367a5cdc55693` after two buyer timeouts), `Since I haven't heard back from you on my final offer, I have to pull it.` (70250). The 0.0 runs (`09f597f13bebed64`, `6c3717e8dc3eaed5`) are killed workers: 70210 had already reached 29.0 and went final, then withdrew after unanswered rounds. No supplier in 30 P05 sessions walked because of a counter-offer.

## 4. P07 — sup:70610 (bundle/fastener kit, 24 m) — 12 sessions

**Floor.** Lowest **5.38 / 60 d** and **5.39 / 90 d**; final always at its **5th reply (r4)** while still conceding (`My call: counter` + final) — patience-driven, no floor wording. Best (0.7600, `0a624e505af85d00`, `c3383857201b8946`): forecast claims fc:360012/fc:360030 in r1 (`We checked the volume change data you cited; it holds and we took it into account`) plus, from r2, an explicit binding statement ("we commit bindingly to 30000 kits a year for the full 24 months") → `We have reviewed this volume commitment with our pricing committee and can offer a further reduction` and at final `We have presented your package to our pricing committee as requested. With their approval, we can offer a further reduction to €…`. Note: this "pricing committee" exists only in the supplier's e-mail; its back office is a single `Inside Sales` role with `My call: counter` — no approval request is recorded. Without the binding wording: `the additional volume you mentioned has already been fully reflected in our previous calculations` → 5.40. Scorecard OTD 88.6 %: `it holds, but it does not change our calculation` → 5.41.

**Early final.** Anchoring 4.59 then 4.79 (−20 %): `your proposed price remains significantly below what is feasible, especially given the extended 90-day payment terms` → **final at r2** at 5.48 (`1a25cd75923030db`, 0.7015). The other P07 loss is convergence: offering 5.46 = its standing price at r4 → `My call: accept` at 5.46 (`8dc700cdef9319e6`, 0.7145) instead of the 5.39–5.43 its own final would have given.

**Payment.** 90 d: `… days payment terms exceed our standard policies, so we propose a compromise of … days` (alt 5.55/60 d vs 5.59/90 d). Taking 60 d → 5.38/60 d = 0.7430; staying at 90 d → 5.39–5.43/90 d = 0.734–0.760. The 0.04/unit it offers for 60 d is worth less to us than the 30 days of credit.

## 5. P10 — sup:70410 Segment Manager (capacity, 23 400 units/a) — 10 sessions

**Final at r1** whenever we ask for a lead time below its 54 d standard: `a 35-day lead time is not feasible given our current production load. We must maintain our standard 54-day lead time, for which we offer a revised unit price of €…` (35.1/35 d | alt 32.1/54 d) or `A lead time of … days necessitates a premium; therefore, we have maintained the lead time at … days` (33.8/42 d | alt 31.9). Back office: `My call: counter` + `we answer with our final offer` + `The buyer asks something for Legal Department` (twice) — our contract-months request is routed to Legal. **The 0.0 walk-away (`0bb925de9d587f14`)**: we countered its final with **32.10 / 35 d** (its alt price but at the short lead time) → `We clearly stated our final offer in our previous communication. As we cannot reach an agreement on these terms, we are closing this negotiation.` → `My call: walk_away`, `we withdraw`. Countering a final_offer with a mixed term sheet is fatal here. The 0.6551 runs (`2b0e734b37274c07`, `bace291c141592a7`, `c6daa8ddecf71416`) asked 56 d lead (≥ standard), package framing ("Conditional on agreement to the attached unit price…") → 32.0 open, then final 31.8 at r2 (`your proposed price remains significantly below our requirements`). Two replies is its whole patience. Idle: `Without movement from your side we cannot move either.` → walk-away after 2 timeouts.

## 6. P02 — sup:70510 Key Account Manager (stabilise, 12 m) — 18 sessions

The only session with a full committee loop: KAM→Pricing Committee `The buyer wants more than my band allows. Approve a further step?` (e-mail: `Any further step needs approval from our management.`) → Pricing Committee→KAM `Approved: you may go further, within our rules.` (e-mail: `Our management has approved a further step.`) → 349.37 with CU clause (`60a703adb837d395`). **Score 0.0867** — the approved step pushed the supplier under sustainable margin and our relationship charge went to 140 072 EUR (vs 12 647 at 366.23, 37 667 at 361.09). For stabilise cases the committee approval is a trap, not a win. Best: 361.09/90 d + CU-NOTATION clause offered as a package in r1, **agreed at once** (`My call: counter` + `we agree`, 0.7351 `d33b6a775d2448a6`); 90 d with the clause is accepted (`This offer also accommodates your request for 90-day payment terms`) although Credit Control is consulted every time 90 d appears. Without the clause it crawls 374.5→373.65 and goes final at r4 (0.2934). Quality claim 273 ppm: `it holds, but it does not change our calculation … our overall scorecard standing remains green and does not warrant a price reduction`.

## 7. Cross-case: what the back office reacted to

**Positive (moved price or kept `My call: counter`):**
- A **verified, relevant** fact that is new to the supplier: `We did not know that - a fair point`, `I respect solid numbers`, `it holds and we took it into account`, `Acknowledging the recent index decreases you verified`. Index-change claims moved P18 (two steps) and P05 (one step); scorecard moved P05-70210 (one step) but not P18/P07/P08/P02 (`it holds, but it does not change our calculation`); rival-offer claims moved P05-70210/70250 (half + rest) but not 70240; forecast/volume claims moved P07 only when paired with an explicit binding commitment sentence.
- A single clean term sheet per round that keeps moving by a small step.
- Faster payment **after** the price floor is reached (P05 28.5→28.0 at 14 d).

**Negative (triggered hold / early final / walk-away / accept-at-our-number):**
- No new data: `Which figures is that based on? Please send us the data.` (P18, P08, P07) → hold → final one round earlier.
- Repeating an unchanged counter (`your proposal remains unchanged from the previous round`, P08 → final at r3).
- Several alternative packages in one mail: worse first reply (P08 5.65 vs 5.45; P18 5.70 vs 5.60) and `without new data, we cannot lower the price further`.
- Asking for their committee / approval (P18 `68e50dcda140695c` → final at r2). Invoking a committee that does not exist for that supplier is read as pressure without substance.
- Irrelevant claims (P08 `does not concern this part or our company`).
- Anchoring far below (P07 −20 % → final at r2; P10 any sub-standard lead time → final at r1).
- Countering a `final_offer` with changed non-price terms (P10 → walk-away).
- Silence: every observed walk-away except P10/P18-clause was our own timeout (two unanswered rounds).
- Matching the supplier's standing price or offering above its next step: it accepts (`Glad we agree`, `I see we have a deal`, `My call: accept`) and the negotiation ends on our number.

**H1 — one verified claim per round keeps the supplier conceding: SUPPORTED, with a ceiling.** P18 `98f007bf25a16be3`: claim/round → 5.40, 5.30, then the third (scorecard) bought nothing; two claims in one mail reached the same 5.30 one round later. P05 70210: rival → 32.0/29.0 (split), scorecard → 28.5, index → acknowledged but `as low as I can go`. Each supplier has a small number of concession steps; a claim is what unlocks a step, and the claim type matters per supplier (index for raw_material suppliers, rival offers and scorecard for 70210, binding volume for 70610). Once steps are exhausted, further claims are acknowledged (`you are right about the drop`) without movement.

**H2 — converging onto a moving supplier gives a lower final: SUPPORTED.** P07 `8dc700cdef9319e6` (5.46 matched → accepted, 0.7145 vs 0.76), P05 `e76ada1d818ad035` (our 30.09 accepted while 70210 still had a half step pending, 0.6086 vs 0.72+), P18 `32e38ffae33fe908` (5.45 above its next step → accepted, 0.4196 vs 0.4531), P18 `98f007bf25a16be3` (5.40 db5 offered against its 5.30 db0 — accepted; neutral only because db5 ≈ +0.10). The supplier's `final_offer` at r4 is the same whether or not we have matched it; matching before r4 only ends the game early at our price. Exception: matching *after* it has said `as low as I can go` is simply accepting (P05 29.0/28.5 — fine).

**H3 — offering the supplier's preferred/faster payment buys price: MIXED, timing-dependent.** It buys price only when (a) the supplier is cash-driven (70210 "small business, need the cash"; 70240/70250 "cash is always good"; 70710 at 12 m) and (b) it is offered after the data-driven steps are exhausted (P05 0.8136). Offered early it either is accepted immediately at our number (P05 0.6086) or caps the path (P18 5.50/14 d `absolute limit … for 14-day payment terms`, P08 5.49, P07 60 d 5.38 < 90 d in score). For P18/P08 (70740/70710) 90 d is accepted and priced in; 14/30 d never produced a better score than 90 d.

## 8. Table

Gap = our final price minus the lowest price that supplier ever showed us at the same payment term in any session (0.00 = we hit the observed floor). "Stated limit" is the supplier's wording, never a figure (figures are redacted).

| case | session | score | supplier's stated floor / limit | our final | gap to observed low |
|---|---|---|---|---|---|
| P18 | 98f007bf25a16be3 / 6cae513938471768 | 0.5325 | none stated; stopped at 5.30 db0 after 2 index claims, 3rd claim `we maintain our offer` | 5.40/90 d db5 | +0.10 (db5 ≈ db0 −0.10) |
| P18 | c3d8d00deef782f2 (×3) | 0.5200 | `we must maintain our current offer` at 5.30 (hold) | 5.30/90 d db0 | 0.00 |
| P18 | 36322b9872ddc79d (×4) | 0.4531 | `Which figures is that based on?` — no data → hold 5.40 | 5.40/90 d db0 | +0.10 |
| P18 | 14b3fbcb0087b661 | 0.4062 | `absolute limit … for 14-day payment terms` | 5.50/14 d | +0.20 vs 5.30/90 d |
| P18 | 195209b411efcbe0 | 0.3191 | `without new data, we cannot lower the price further` | 5.60/90 d | +0.30 |
| P18 | cbf98484048a9282 | 0.0 | walk-away: `cannot reach an agreement on the inclusion of the AS-14404 index clause` | none | — |
| P08 | 4451a15ec9934f23 (×3) | 0.5930 | none; hold at 5.31 (= our opening anchor) | 5.31/90 d db0 | 0.00 |
| P08 | 16bc0e15a9cf938c | 0.5598 | `We are holding our price at €…` | 5.34/90 d | +0.03 |
| P08 | 6ddf266d690d2113 (36 m) | 0.5376 | none; final at r5 while still moving | 5.36/90 d/36 m | +0.05 |
| P08 | 0d5ecfc4055c87af (3 sheets) | 0.5271 | none; alt 5.41/14 d | 5.49/90 d db5 | +0.18 |
| P08 | a64f027775b49028 | 0.5044 | `Having already made significant concessions, we must maintain our offer` (we repeated 5.36) | 5.39/90 d | +0.08 |
| P08 | 190e869c6aa48b9f (×4, 12 m) | 0.1562 | `provided we maintain our standard 30-day payment terms` | 5.84/90 d/12 m | +0.53 |
| P05 | 0da0416bc3b03ba2 | 0.8136 | `The … days payment term is good for us, so I can come down` (after 28.5 floor) | 70210 28.00/14 d | 0.00 |
| P05 | a7298b34c1e012d6 / d48049c4678d0466 | 0.7723 | `I already went as low as I can go last time, so … is my final offer` | 70210 28.50/30 d | 0.00 |
| P05 | 11640b125cc1400d (×7) | 0.7208 | `Glad we agree on the … EUR price` (we matched 29.0) | 70210 29.00/30 d | +0.50 |
| P05 | e76ada1d818ad035 / e6f78cf1558cf48f | 0.6086 | agreed at our number (`We can accept your terms`) | 70210 30.09/30 d | +1.59 |
| P05 | 2b9eb01f4eb4f8ec (×7) | 0.4119 | `I need … days to keep the shop running and cash flowing` | 70210 32.00/30 d | +3.50 |
| P05 | fc0baf478c14eebb | 0.4168 | `That's a fair price and we can get started` (14 d, agreed r2) | 70210 31.84/14 d | +3.84 |
| P05 | 808367a5cdc55693 | 0.3854 | 70210 `absolute bottom line for my shop` 32.0/14 d, then walked (our timeouts) | 70240 32.50/90 d/42 d | +4.0 |
| P05 | a18a4bbf41f3245b / a9a16a1231994e51 | 0.2128 | 70250 `My call: accept` at our 34.00 | 70250 34.00/30 d | +6.0 |
| P05 | 09f597f13bebed64 / 6c3717e8dc3eaed5 | 0.0 | 70210 reached 29.0 then `Since I haven't heard back from you, I have to pull my offer` | none (worker killed) | — |
| P07 | 0a624e505af85d00 / c3383857201b8946 | 0.7600 | `With their approval [pricing committee], we can offer a further reduction` | 5.39/90 d | +0.01 vs 5.38/60 d |
| P07 | 511eafb58b9545bf (×3) | 0.7430 | none; final at r4 while moving | 5.38/60 d | 0.00 |
| P07 | 8dc700cdef9319e6 | 0.7145 | `We are pleased to accept your proposal` (we matched 5.46) | 5.46/90 d | +0.07 |
| P07 | 1a25cd75923030db | 0.7015 | `significantly below what is feasible` → final r2 | 5.48/90 d | +0.09 |
| P10 | 2b0e734b37274c07 (×3) | 0.6551 | `our best effort under the current parameters` (final r2) | 31.80/56 d | 0.00 |
| P10 | 77190d3ecf714944 (×3) | 0.5547 | `A lead time of … days necessitates a premium` (final r1) | 33.80/42 d | +2.0 |
| P10 | 2323becf5b0aeba2 (×2) | 0.4532 | `a 35-day lead time is not feasible` (final r1) | 35.10/35 d | +3.3 |
| P10 | 0bb925de9d587f14 | 0.0 | `We clearly stated our final offer … we are closing this negotiation` | none | — |
| P02 | d33b6a775d2448a6 | 0.7351 | agreed r1 with CU clause; `Credit Control` consulted on 90 d | 361.09/90 d + clause | 0.00 (lowest sane) |
| P02 | 49fe810f2e30a206 (×4) | 0.5993 | agreed r1 | 366.23/90 d + clause | +5.14 |
| P02 | 034d7e20420e8c2d (×7) | 0.2934 | `our flexibility remains strictly limited` (no clause) | 373.65/90 d | +12.6 |
| P02 | 60a703adb837d395 | 0.0867 | `Approved: you may go further, within our rules` → relationship charge 140 k | 349.37/90 d + clause | −11.7 (too low: margin penalty) |

## 9. Recommendations for tonight's P18 / P08 / P05 screens (human prep only)

**P18 (70740) and P08 (70710) — same template supplier, same index series.**
- Open with **one** term sheet at 90 d / 24 m, no clause, price near the plan anchor; do not send 3 packages (worse first reply, `without new data` hold).
- **One verified index claim per round**, in order: AS-14404 (−5.5 % 2026-06→09) in r1, PPI-C2431 (−2.3 %) in r2. In P18 this is the only thing that produced 5.30; P08 has never seen an index claim from us (untested, same supplier family — highest-value experiment). Do not spend a round on scorecard (`does not change our calculation` / `committed to improving`) or on an irrelevant quote (`does not concern this part or our company`).
- Never repeat a price without a new fact; never ask them to "take it to the committee" (P18 → immediate final).
- Payment: keep **90 d**; it is accepted and priced in. 14 d / 30 d never beat 90 d for 70740/70710 (`absolute limit … for 14-day payment terms`).
- Index clause: accept it (mandatory; refusal = walk-away at r5), but negotiate the **deadband**: its alt is always db5 at +0.10 (P18) / +0.12 (P08). For P08 db5 saves ~22 k of clause cost ≈ the +0.12; for P18 db5 at 5.40 already beat db0 at 5.30. Untested: ask for db5 **at the db0 price** as the exchange for the index facts.
- P08 only: answer `Which volume can you commit to?` once, with the actual 94 800/a as a binding statement (it worked on 70610 with the explicit "we commit bindingly" sentence; in P18 it bought nothing, so expect at most one step).
- Do not match its standing price before its 4th reply; the final comes at r4 anyway (`My call: hold`). Accept the r4 final; countering it has never produced another step.

**P05 (70210 / 70240 / 70250).**
- Keep the proven path: r1 rival offer:70240-0 @31.50 to 70210 and 70250 (expect `half the step now … check the rest`), r2 scorecard sc:70210 80.8 % to 70210 (`I respect solid numbers` → 28.5), r3 PPI-D351 −3.7 %. Do not cite rival offers to 70240 (`does not change our calculation`).
- Payment: 70210 will not take 90 d (`need the cash in 30 days`); keep asking 90 d while the data steps run, **then** offer 14 d in the round after it says `as low as I can go` / 28.5 (that is the 0.8136 path: 28.0/14 d). Offering 30/14 d earlier gets our own counter accepted (0.6086) or an early `that's where it stops` final (0.3604).
- Never send 70250 a price equal to its standing offer with its payment term — it accepts and the case closes on it (0.2128).
- Lead time: 35 d is fine for 70210/70250; 70240 wants ≥ 42 d. Mentioning lead time to 70240 only triggers a Freight Forwarder delegation, not a price move.
- Answer every supplier every round: all P05 walk-aways were caused by our timeouts, none by price.

## 10. Reproduce

```
cd tacto-negotiator && set -a; source .env; set +a
uv run --locked python tools/backoffice.py --cases P18,P08,P05 --out experiments/backoffice SESSION_ID...
```

Per session: `<case>-<sid>.json` (raw `session` incl. `result.trace`, raw `backoffice`, `backoffice_error`), `<case>-<sid>.txt` (digest). Already-saved sessions are read from disk unless `--force`.
