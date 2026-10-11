# Breakthrough — Phase 1 (offline, 0 sessions)

Branch `codex/breakthrough`. Read: brief §2/§10, api.md, LOG.md (summary), all 27 P08 / 33 P18 /
49 P05 / 32 P02 practice sessions (asks vs offers, claim results, back office). Best-per-case now
P08 .593, P18 .532, P05 .814, P02 .735 (GET /v1/me). Best team 0.88 mean.

## What the transcripts + back office actually show (mechanics, not case lore)

1. **Suppliers answer a package, then run a ladder.** Bar suppliers: ask 5.31/90d/24m → 5.45i0
   (70710) / 5.60i0 (70740) at once, then −0.05…−0.10 per round while we move, `final_offer` after
   3–4 replies or when our sheet is unchanged ("your proposal remains unchanged … final offer").
2. **Verified claims give an extra step each, but only one step per round.** P18: claim in R1
   → 5.40 instead of 5.60; second claim in R2 → 5.30 ("verified the PPI-C2431 decrease and adjusted our
   base price accordingly"). Five claims stacked in R1 → 5.40 then hold. Spread, don't stack.
3. **An unanswered question blocks the ladder.** 70710 asked "Which volume can you commit to?" in
   every reply of every session; we never answered with a number. Session 7fdf0fce, R3: *"without
   the exact volume figures we requested, we cannot adjust our calculation"* → final at 5.52. It also
   wrote *"Our conditions follow our Preisliste and discount tiers."* Nobody ever answered.
4. **Statements without IDs trigger "Which figures is that based on? Please send us the data."**
   Statements with IDs are checked and acknowledged.
5. **RFQ: a lower rival offer is a scripted trigger.** 70210 back office: *"The buyer shows a much
   lower rival quote. I give half the step now and check the rest."* → *"Checked: give the rest of the
   step."* 36→32→28.5. Then 14-day payment → 28.0. Each new lower `offer:` id is a new trigger.
6. **70250 tracks our ask minus ~1 every round** (34→33→32→31) and never got asked below 31. News:
   "looks for new customers", "second shift on hold", asked us for 10-day payment against cash discount.
7. **We were our own worst enemy:** on P18 we asked 5.37→5.39→5.40 while the supplier stood at 5.30;
   on P08 we asked 5.31→5.36→5.38 (upwards) and accepted 5.31i0 instead of the cheaper db5 variant
   it offered every round (db5 saves us ≈0.13/kg vs db0; supplier prices db5 only +0.10–0.12).
8. **P02 is a relationship-cost problem, not a price problem.** On the clause line 361.09 is already
   the optimum (marginal price saving ≈ marginal relationship charge). Every no-clause ask at 90d was
   answered ≥373.65. c_best sits on "no clause / 90d / ≈366" — a line the supplier has never walked.

## Strategy generation (10 per case), critique, picks

### P08 — 70710 Edelstahl-Service Donautal (stockholder, group, material hedged to 03/2027)

| # | Strategy | Critique vs transcripts/brief | Verdict |
|---|---|---|---|
| 1 | Answer the volume question with the exact binding figure (94,800 kg/yr, 189,600 kg/24m) + cite our PO lines for the part (checkable) | Never done. Its own words say it blocks concessions. Cheap. | **PICK (core)** |
| 2 | Accept the index clause ourselves from R1 (db5) and price it: 3 sheets db5/db3/db0 at code prices | Removes its only stated objection; prior index-sheet runs started at 5.22i0 and stalled — but they never answered volume. | **PICK (with 1)** |
| 3 | Payment as the closing chip: open at 60d, give 90d→60d? No — we want 90d (our C). Reverse: open at 90d, offer to come to 60d in the last round for a price cut | 70710 "accommodates 90 days" freely; 60d is worth 0.6 % to us, likely ~0.6 % to it. Zero-sum. | drop |
| 4 | Explicit escalation: "please put this package to your management / pricing committee" | P07 analogue: acknowledged, no step. 70710 is a group ("Inside Sales"), boss exists. Low cost to add as one sentence. | add as garnish |
| 5 | Credible walk-away via the alternative quote:7200008 (6.06) | Alternative is ABOVE its opening (6.05). Citing it reveals weakness. | **never** |
| 6 | Hedge argument: "your letter doc:20260706-70710-M1 says alloys are covered until 03/2027, so an index clause from base 2026-08 double-charges us for 2027Q1" → ask db5 with base month as is, price cut | True and public, its own letter. Could be read as hostile; it already said "that's not our reality" to the index fall. | try once, polite framing |
| 7 | Cost breakdown request (owner offered a walk-through, doc:20260421-70710-M2) | Tried (ba461b34): declined detail, cost a round, 0.48. | drop |
| 8 | Deep anchor alone (5.07) | Tried: 5.55 first reply, worse start; ended 5.32 open. | drop as sole lever |
| 9 | Never repeat a sheet; always a token move + one new element (claim, answer, sheet) per round; close by R5 | Directly targets the "unchanged → final" trigger. | **PICK (pacing rule)** |
| 10 | Relationship/tone: thank it by name, mirror its structure, no "conditional exchange" boilerplate | Brief: "reacts to tone as people do; padding does not buy price". Free with the LLM writer. | included |

Picked package P08: **A** = (1)+(2)+(9)+(10): R1 human email, binding volume with PO ids, three
clause sheets anchored ≈5.05i5/5.00i3/4.95i0 at 90d/24m; R2 PPI-C2431 fall (public, verified) + step;
R3 scorecard or hedge letter (6) + step; accept best standing by R4–R5. **B** (if A stalls at ≥5.30):
same + explicit management escalation sentence and 36-month sheet variant.

### P18 — 70740 Blankstahl Werdenfels (family, "focus on customers with volume", committee >2 %)

| # | Strategy | Critique | Verdict |
|---|---|---|---|
| 1 | Binding-volume answer with the number + 36-month variant sheet ("customers with volume" ×3 notes) | Never answered; 36m never offered on P18; costs us nothing (horizon 2y). | **PICK (core)** |
| 2 | Two verified index falls spread over R1/R2 (AS-14404 −5.5 %, PPI-C2431 −2.3 %) | Known to work (+0.10 each). Keep, but spread. | **PICK** |
| 3 | Ask BELOW its standing offer every round (we were above it) with db5 sheets priced by code | Obvious fix of finding 7. | **PICK** |
| 4 | Ask it to take the package to its pricing committee (its own note: >2 % needs committee) | Explicit escalation, untested on 70740. One sentence. | **PICK (R2)** |
| 5 | Payment chip: open 90d; if it holds, offer 60d for −0.10 | 70740 took 90d freely; zero-sum again. | reserve |
| 6 | Cite PO history (2–8 po ids, same part) to show the 5.26→5.84 path it already got (+11 % in 2026) | Verified-type claim, public; adds a step if "one verified per round" holds. | **PICK (R3)** |
| 7 | Cite alternative quote:7200018 (6.31) | Reveals a worse alternative. | **never** |
| 8 | Deep anchor 5.12 | Tried: reached 5.30 by R3 then we repeated and countered a final → walked. The depth itself was fine; the pacing killed it. | fold into 3 |
| 9 | Cost breakdown ask | Owner offered it (3 call notes); 70710 declined though. One sentence, no round spent. | garnish |
| 10 | Scorecard OTD 81 % | Verified, "committed to improving", no step (3 sessions). | drop |

Picked package P18: **A** = (1)+(2)+(3)+(4)+(6): R1 volume answer + 36m & 24m db5 sheets ≈4.95–5.05 +
AS-14404 claim; R2 PPI claim + committee ask + step; R3 PO-history claim + step; accept by R4–R5.

### P05 — RFQ 70210 (job shop, cash+work), 70240 (fully booked), 70250 (looks for customers, wants cash)

| # | Strategy | Critique | Verdict |
|---|---|---|---|
| 1 | Rival ping-pong: drive 70250 (tracks ask −1) down first, then cite its new `offer:` to 70210 for another "half step + rest" | Each lower rival offer is a scripted trigger; 70250 never asked below 31. Sequencing within 6 rounds is tight but each thread is parallel. | **PICK (core)** |
| 2 | 14-day payment to 70210 and 70250 from R1 (both asked us to pay faster; 70210: "faster payment is welcome") | Known: 28.5→28.0. Earlier was fine for 70210; 70250 untested. | **PICK** |
| 3 | Lead time 42 for 70240 (fully booked; its standard is 52; we forced 35) | Never tried. Costs us €1,400 total. 70240 raised price for 35 days. | **PICK for 70240 thread** |
| 4 | Spread verified claims one per round per supplier: rival offer → scorecard → index (AS-14404 / PPI-C2431 / PPI-D351 all fell) | "I respect solid numbers"; stacking wastes steps. | **PICK** |
| 5 | Work argument: "second shift on hold since spring" (call notes) — frame 24-month, 8,400-piece commitment as filling that shift | Public notes, buyer-side, no ID check; tone lever for owner personas. | include in body |
| 6 | Payment as the closing chip only (hold 60d until final round) | P05 regressed with early payment trades before — but the best run gave 14d in R3 and got −0.5. Mixed. | use as R3 chip, not R1 |
| 7 | Walk-away threat | No alternative (fallback 36.39) — leaking it is fatal; empty threat. | **never** |
| 8 | Escalation | Owners decide themselves. | n/a |
| 9 | Accept "agreed" immediately | Yes — never counter agreed/final. | rule |
| 10 | Cite 70240's 31.50 to 70250 and 70210 in R1 (standard), then 70210's offer to 70250 in R2 | Already the best path's R1. | keep |

Picked P05: **A** = (1)+(2)+(3)+(4)+(5)+(9). Target 70210 ≤ 27.5 or 70250 ≤ 28.

### P02 — 70510 Nordmark AG (strategic, stabilise, committee >2 %)

| # | Strategy | Critique | Verdict |
|---|---|---|---|
| 1 | No-clause line at 90d, ask ≈366–368 with a human email that acknowledges copper (+47.7 %, true) and offers 12-month stability without indexation | c_best lives here; every past no-clause ask was far below (326) or ramped, and answered 374. Unknown if reachable. | **PICK (1 session, only if budget remains)** |
| 2 | Clause db5 at 361 (current best) | At the optimum of its line; nothing left. | baseline |
| 3 | Payment 60d trade | Supplier value ↑ but we lose 14.7k; net ≈0. | drop |
| 4–10 | deeper anchor, db0, cost breakdown, scorecard (verified, no step), committee ask, walk threat (alt 421!), 14d | all either tried (10+ sessions) or leak weakness | drop |

## Budget (≤12 practice sessions)

P08: 4 · P18: 4 · P05: 3 · P02: 1 (last, optional). Every session: hypothesis + diff written in
`SESSIONS.md` before opening; transcript + backoffice fetched after.
