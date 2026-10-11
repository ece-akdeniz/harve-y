# Breakthrough sessions (hypothesis written BEFORE each run; result appended after)

## S1 — P08 — 70710 — "answer the volume question + carry the clause"
- Hypothesis: 70710 blocks its ladder until it gets an exact binding volume figure ("without the exact volume
  figures we requested, we cannot adjust our calculation"). Stating the binding 94,800 kg/yr (189,600 kg / 24 m) with
  PO ids as proof, and sending clause sheets (db5/db3/db0, 90 d, 24 m) at equal cost, should produce a first reply
  below 5.45i0 and a ladder that does not stall at 5.31.
- Different from every past P08 run: volume never answered with a number; clause never carried from R1 together
  with the volume answer; body never written by a model; AS-14404 claim excluded (hedged); PO-history claim new.
- Budget: 1 session (S1), repeat once if > .593.
- RESULT S1: session f4d4d86460b454dd, **0.5376** (5.36 i0 / 90 d / 36 m). First reply 5.53i0 (worse than the 5.45 a
  bare fixed-price ask gets). Volume answer acknowledged ("qualifies for a dedicated volume discount tier") but the
  ladder stayed −0.07/−0.08/−0.02 and went final at reply 4. Verified PO claim: "holds, but does not change our
  calculation". Verified PPI claim: "incorporated this movement" (−0.07, same as a normal step). Management review:
  −0.08. 36 months: −0.02. Conclusion: 70710's ladder depth is fixed; levers unlock steps, not depth. Ceiling ≈5.31.
  Do not spend more P08 sessions on content; P08 is a pacing problem (take the 5.31i0 / or ask db5 variant).

## S2 — P18 — 70740 — "volume commitment stated + spread claims + ask below its offer + committee"
- Hypothesis: 70740 ("focus on customers with volume", committee >2 %) moves one step per verified claim
  (R1 6.10→5.40, R2 →5.30 in 6cae5139). Asking BELOW its standing offer each round (we never did), stating the
  binding 23,700 kg/yr + 36-month variant, and asking it to take the package to its pricing committee should get
  it past 5.30 (its floor so far). Expect ≥5.20 db5 or db0 → score > .60.
- Differs from all 33 P18 runs: never asked below the standing offer; 36 m never offered; committee never asked;
  volume never stated; PO-history claim new; body model-written.
- RESULT S1: f4d4d86460b454dd **0.5376** (5.36 i0 / 90 d / 36 m, final at reply 4). First reply 5.53i0 (worse than
  the 5.45 a bare 5.31-fixed ask gets). Volume answer acknowledged: "Your commitment to 94,800 kg annually over a
  24-month term qualifies for a dedicated volume discount tier" — but the ladder was unchanged (−0.07, −0.08, −0.02).
  PO claim verified "does not change our calculation"; PPI claim verified "incorporated"; management review
  "we can support a further reduction to 5.38"; 36 m "in exchange for this longer commitment … 5.36". Ladder-bound.
  Lesson: 70710's first reply is 5.40–5.57 regardless of content; asking WITH the clause gets no clause compensation.

## S2 — P18 — 70740 — "volume answer + 36 m + spread claims + committee + ask below its offer"
- Hypothesis: 70740 wants volume ("focus on customers with volume" ×3) and gives one step per verified claim. A
  binding 23,700 kg/yr (truthful, fixed) over 36 months, AS-14404 fall in R1, PPI-C2431 fall in R2 with an explicit
  request to put the package to its pricing committee, PO history in R3, always asking below its standing offer with
  db5 sheets, should take it below 5.30i0 / 5.40i5.
- Different: 36 m never offered on P18; volume never answered; we always asked above its standing offer before.

## Results (12/12 sessions)

| S | case | id | score | close | what changed |
|---|---|---|---|---|---|
| 1 | P08 | f4d4d86460b454dd | 0.538 | 5.36 db0 | volume answer, db5/db3/db0 trio, PO claim |
| 2 | P18 | 7b42a1576b660c15 | 0.467 | 5.50 db5/36m | 36m volume commitment, db5 ask |
| 3 | P08 | f6e6b2de1ac9e065 | 0.483 | 5.41 db3/30d | forecast CSV + fc claim (verified); LLM gave payment away |
| 4 | P08 | (runs/S4) | 0.484 | 5.53 db5 | hold-deep test (falsified gap-fraction model) |
| 5 | P08 | 90f7a0016c5e0269 | 0.604 | 5.30 db0 | ONE no-clause sheet 4.88, +0.11/round, claim each round |
| 6 | P08 | (runs/S6) | **0.759** | 5.16 db0 | same, anchor 4.58 |
| 7 | P08 | (runs/S7) | 0.626 | 5.28 db0 | repeat of 6 (first-reply lottery 5.57 vs 5.45) |
| 8 | P18 | (runs/S8) | 0.453 | 5.40 db0/36m | P08 recipe on 70740: deep anchor punished |
| 9 | P18 | (runs/S9) | **0.587** | 5.20 db0 | credible anchor 5.20 + PO claim 5.26 + forecast, +0.02-0.05 steps |
| 10 | P18 | (runs/S10) | 0.520 | 5.30 db0 | repeat of 9 |
| 11 | P08 | (runs/S11) | 0.504 | 5.39 db0 | two-variant ask (none + db0) — worse, dropped |
| 12 | P18 | (runs/S12) | 0.587 | 5.20 db0 | anchor 5.07 + PO + fc; steps −0.30/−0.20 with a new claim each round |

Mechanics learned (both bar stockholders, 70710 and 70740):
- First reply is a package answer: ask NO clause / 90 d / 24 m → it inserts its AS-14404 clause itself at the
  db0 price (5.45–5.57 on P08; 5.40–5.70 on P18). Proposing the clause ourselves costs ≈0.12 (5.69 db5).
- After the first reply the ladder budget is fixed: ≈0.27–0.30 (70710) / 0.30–0.40 (70740) spread over 2–3
  steps, then `final_offer`. Steps need a real move from us each round and a NEW verified claim helps
  (70740 moved 0.30 and 0.20 in S12). Tiny moves (≤0.02) or an unchanged sheet trigger the final at once.
- 70710 tolerates a deep anchor (4.58 = −24 %); 70740 punishes one (4.76 → 5.70) but lands ON a credible
  anchor (5.20 → final 5.20 twice). Both ignore volume/36 m as a price lever; they just want the number.
- The forecast CSV + fc claim: verified, "we took it into account", no extra step — harmless, keeps the
  ladder alive, answers the question they ask in every reply.
- One idx claim per series per case (a second window of the same series = `duplicate`). PO claim with the
  lowest 2026 price (5.17 / 5.26) is verified but "does not change our calculation" on 70710; on 70740 it
  is the anchor's credibility.
- Giving payment days away (S3) buys 0.03–0.04 per 15 days: never worth it.
