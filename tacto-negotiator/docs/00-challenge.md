# 00 - The challenge (facts only)

Source: kit `brief/brief.md`, `brief/api.md`, `brief/submission.md`; audited revision
`1b5516bb95ef28e37f69aa446dc62168864bca53`. These are the published contract and event schedule,
not evidence of our implementation. Resolve updates with organizers and record them in 08.
All event times are Europe/Berlin, 10–11 October 2026. Company data is dated 30 September.
Company defaults below are background; actual case parameters govern cost calculations.

## Story

We are purchasing at **Hollerau Pumpenwerke GmbH** (fictional Bavarian pump maker, €252 M revenue,
910 staff, ~45 suppliers, ~€35 M purchasing spend FY2026). Today is **30 Sep 2026**. Company policy:
60 days net standard, 8 %/yr cost of capital, DAP Hollerau preferred, €150 flat fee per
supplier-caused complaint, OTD target 95 %.

## A case

- Trigger (letter, expiring contract, RFQ, escalation, kit memo) + case file + 1-3 supplier bots.
- Case types: `price_increase`, `renewal`, `rfq`, `bundling`, `raw_material`, `capacity`, `quality`.
- Category goals: `stabilise` (castings, electrical), `secure_supply` (seals, capacity squeezes),
  `quality_first` (quality escalations), `leverage` (machined, sheet metal, raw material),
  `routine` (C-parts, kits). The goal sets the case's rates.
- Each supplier has roles: rep/owner who writes, a boss for bigger moves, and engineering,
  quality, logistics, finance or legal who answer their topics and attach documents.

## Messages

| Field | Buyer limit |
|---|---|
| `subject` | ≤ 300 chars |
| `body` | plain text ≤ 8,000 chars |
| `term_sheets` | 0-3 packages, each with **every** negotiable field |
| `refs` | ≤ 20 data IDs (IDs in the body count too) |
| `attachments` | ≤ 5 (md/csv/json/pdf/xlsx); md, csv, json are read |
| `action` | `accept {term_sheet_id}` or `walk_away` |

Supplier reply: `status` (`open`, `final_offer`, `agreed`, `walked_away`, `no_bid`), its standing
term sheet, `signals` (`reply_delay_days`, `validity_days`), `missing_fields` (close on its
**standard terms** from the quote PDF), `claim_results`.

Documents (rendered from supplier state, byte-stable): quote PDF (offered, standard, fixed terms,
validity), cost breakdown XLSX (ask; open suppliers send it), 8D report PDF, delivery schedule
XLSX, order confirmation PDF.

## Claims (data you cite)

- Cite by ID with your figure **in the same sentence**. At most **3 checked per message**. One
  argument per sentence. Each ID counts **once per case** (`duplicate` otherwise), except a rival's
  quote/offer in an RFQ, which counts once per supplier - and **reveals it** to that supplier.
- Results: `verified`, `contradicted` (unknown ID or wrong figure - **costs trust**), `irrelevant`
  (true but not about this supplier/part, or index window too long/old), `duplicate`.
- Tolerance: ±0.5 pp for %, else ±0.5 % (min 0.01).

| You cite | Checked against | Your figure |
|---|---|---|
| 2 × `idx`, same series, ≤ 12 months apart, ending within the last 12 months of data | `(later/earlier − 1)×100` | % |
| a `quote` of this case, or another supplier's `offer` in this session | its price, same part | EUR |
| `sc` rows (quality also `qn`) | mean OTD, or mean ppm if about quality | % / ppm |
| 2-8 × `po`, same part | order prices | - |
| `fc` / `cost` / `news` | recorded change / estimate / that it's about this supplier | % / EUR / - |
| letter `doc` with notice + contract `ctr` | notice given vs. contract notice | days |

Verified ≠ convincing. Supplier hard limits: cost floor, boss approval for bigger moves, no
concession without a move from us. Tone, questions, threats, urgency, manipulation are understood
and have consequences.

## Score

```
score = clip((C_open − C_deal) / (C_open − C_best), 0, 1)
```

- `C_open`: cheapest opening quote that keeps the must-haves.
- `C_best`: cheaper of our alternative and the best package any supplier would accept with every
  valid lever. Fixed per case.
- No deal → alternative's score (0 if none). Broken must-have → 0.
- Final: wave score = mean case score × 100; total = sum of 5 waves (max 500).
  Ties: more deals, then fewer rounds.

Cost C (see `arena_kit.cost`, `api.md#cost-and-score`):

```
spend + uncovered·(1+fallback_risk) + spend·r·(d_ref − payment_days)/360 + committed·freight[incoterm]
+ late_cost·max(0, lead − need_lead) + committed·ppm/1e6·(cost_per_defect − min(chargeback, cost_per_defect))
+ tooling + index clause effect + index risk + relationship (stabilise/secure_supply only)
```

Relationship: `relationship_eur_per_point · soft(sustainable_margin − supplier_margin) · years`,
`soft(g)=0 (g≤0), g²/10 (0<g≤5), g−2.5 (g>5)`. Supplier margin uses its full cost and the deal's
cash value **to it** (payment timing at its own rate - higher for cash-short suppliers).

## Limits

- **60 s per message per thread**, from the supplier's reply. Late = timeout: last offer
  repeated, patience drops. 3 in a row, or one after the last round, ends the thread.
- Supplier reply takes up to ~1 min (excluded from its buyer-response interval). HTTP timeout ≥180 s.
  Queued requests and effects on other RFQ threads need hosted confirmation; do not assume
  this exclusion extends the hard wave cap.
- Round limit per thread: default 10 messages.
- Per key: 10 calls/s, 10 open sessions. Body ≤ 64 KB.
- `X-Move-Id` on every POST; same id = idempotent retry.
- `422` invalid (no round used), `409` ended/late/round limit, `429` rate/quota.
- Practice: 10 hosted cases, **200 sessions per rolling 24 h**, best score per case counts on the
  practice board (practice does not rank the final). Sandbox `case:D01` (price increase),
  `case:D02` (RFQ, 2 suppliers): free, no board.

## Live Final

- 5 themed waves, **8 min hard cap each** (host may extend; read `seconds_left`).
- Cases appear at wave start for all teams; each team gets its own order. One session per case.
- At the cap every open session ends with no deal (alternative's score).
- Up to **a third** of hidden cases combine supplier types and case types never seen in practice.
  Hidden case files may carry their own `facts`; some cite the Sunday release.
- **Agent must not read** `/v1/events`, `/v1/events/stream`, `/screen`, `/v1/screen`,
  `/leaderboard`, `/v1/leaderboard`, `/results`, `/v1/results`.

## Schedule

| When | What |
|---|---|
| Sat 12:00-13:00 | Deep dive (ground floor). **Challenge selection closes 13:00** |
| Sat afternoon | Office hours at the Tacto table |
| Sat night | Tacto stops answering (time TBD - see open questions) |
| Sun 08:00 | Sunday release: news, letters, memo (`GET /v1/data`, 06:00 UTC) |
| Sun 09:00 | Pre-flight: one practice case through the final setup |
| Sun 11:30 | Checklist (see runbook) |
| Sun 12:00 | Code + slides freeze, Live Final (5 × 8 min) |
| Sun 13:00-14:30 | Top 10 pitch: 5 min + 2 min Q&A |
| Sun 14:30 | Track winners + 2 finalists to the Grand Final |
| Sun 15:30 | Grand Final pitches (AudiMax) |
| Sun 16:30 | Awards |

Prize: €1,500 for 1st, medals for the top 3. Places 1-3 weighting (Live Final vs. jury) is a
placeholder in the brief - ask. EHL Grand Final: best 2 of the 5 EHL finalist teams in this track
go on; finalists outside the top 10 are ranked by Live Final score alone.

## Submission (ehl.gg, by Sun 12:00)

1. Public-to-jury repo: agent + README (setup, env var names, command). Commit hash in the
   description. tum.ai runs a code agent over every submission.
2. Short description: how the agent prepares, what it reads, how it decides offers, when it
   closes or walks away.
3. Pitch slides.
No `.env`, no keys in the repo. Top 10 are checked for pushes after the freeze.
