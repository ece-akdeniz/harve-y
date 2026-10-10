# Evidence stage implementation plan

Status: proposed work, based on a local data/code audit on 10 October 2026. Nothing in this
document marks a feature implemented or authorizes a hosted experiment. Evidence owner: you.
Decision/integration: Samet. Runtime and Evaluation owners retain their existing boundaries.

## Outcome and scope

Give Decision a current, scoped and traceable account of supplier facts and constraints; give
the outgoing message only checked claims whose figures, wording, units and audience agree.
Keep internal estimates separate from external claims and binding proposed terms.

The first release repairs existing evidence behavior. Subsequent releases add supplier signals
and cost-pressure analysis individually, only after local validation and measured comparisons.
Retain the current candidate as a reproducible comparison arm. Do not enable supplier estimates,
rival disclosure, extra case types or a model writer as a side effect of data cleanup.

Success has two separate gates:

- Correctness: no invented values, incompatible price bases, unsupported conclusions, private
  disclosures, duplicate claims or unexplained source conflicts in the agreed local case set.
- Utility: measured negotiation improvement without reliability regressions. Correctness alone
  does not demonstrate that a claim persuades a supplier.

## Audit baseline

The package contains 24 SQLite tables, 46 detailed suppliers and 60 detailed parts. CSVs are
the master extract, SQLite supports joins and facts.json supplies arena-checkable values.
Contracts and correspondence provide text; the release can add facts, CSVs and documents
without modifying the base SQLite database.

| Data | Existing consumption | Planned treatment |
|---|---|---|
| Index values/metadata and cost drivers | Index claims; weighted estimate helper | Preserve calendar windows; add explicit freshness, coverage and driver provenance |
| Scorecards | Historical OTD/PPM claims | Preserve rolling metrics; label period, date basis and whether supplier-wide |
| Contracts and correspondence | Notice claims and template traits | Match valid contract/part; date and scope supplier signals |
| Supplier master/intel/news | Dossiers and traits | Build case-aware signals with evidence and uncertainty |
| Invoices | Average payment lateness | Separate ordinary lateness, discounts and unpaid overdue exposure |
| Should-cost | Internal claim candidates and opt-in supplier estimates | Preserve basis, price unit, method and uncertainty; keep private |
| Quotes | Dormant rival claims; case alternatives | Defer disclosure until validity, comparable terms and recipient ledger pass |
| Sourcing/price conditions | Prep supplier/part pairs and latest price | Check active/valid dates and units; use for baseline context |
| Negotiation history | Stored in dossiers | Later: requested vs settled context, dated and descriptive, not a target price |
| PO/receipts/quality notifications | Indirectly represented by scorecards | Later: targeted price-history or delivery diagnosis; avoid duplicate scorecard math |
| Forecasts/forecast lines | Unused | Later: volume evidence only when needed for a specific commitment decision |
| RFQs/spend/parts/contract clauses | Little substantive analysis | Targeted qualification, concentration and clause context; no broad new analytics initially |

Observed local failures: ordinary late payments are masked by early discount payments; the
claim verifier can accept a false notice comparison or a sentence inconsistent with its
structured figure; default package discovery fails in this checkout without an explicit path.
Price-basis and citation compatibility require validation; they are not proof that all existing
case economics are wrong. Case prices use the case's specified price unit.

## Ownership and shared contracts

| Area | Evidence work | Coordination needed |
|---|---|---|
| dossiers.py, traits.py, claims.py, evidence.py | Data preparation, signals, verification, selection and decoration | Evidence owns implementation |
| agent.py, trades.py, evaluator.py, guards.py | Supply validated context and assumptions | Samet owns decision behavior, economics and outgoing guard integration |
| config.py, cli.py, runner.py, state.py, trace.py | Define preparation, status and ledger requirements | Runtime owns lifecycle, persistence, retries and concurrency |
| Reports, replay and experiment harness | Supply sources, exclusions and outcome fields | Evaluation owns comparisons and presentation |

Agree the following records before integrating changes. Extend existing dataclasses where
possible; no new framework is needed.

- Fact: ID, raw value/unit/price_unit, supplier/part scope, observation date, validity dates,
  source layer (base/release/case/session), source path/hash and normalization method.
- Supplier signal: kind, source IDs, scope, observation/expiry dates, evidence type
  (recorded statement vs inferred hypothesis), strength/confidence, active/superseded status.
- Claim: kind, source IDs, numeric figure/unit/basis, audience/part, date/window, disclosure,
  deterministic sentence, arithmetic result, semantic result and relevance reason.
- Private analysis: drivers, known coverage, missing inputs, scenarios, uncertainty and source
  references. It cannot automatically become a checked external claim.
- Usage ledger: case/session, source ID, recipient scope where permitted, logical move ID,
  reserved/sent status and reconstruction evidence.

## Phase 0 — reproducible inputs and observable activation

Priority P0. Estimated focused effort: 30–60 minutes, excluding dependency setup.

1. Resolve the configured base/release paths once. In this checkout the available base is
   `../negotiation-arena-kit/data` when running from tacto-negotiator; do not hard-code that
   developer path into production behavior.
2. Record resolved paths, package/release hashes, data snapshot date, table counts, enabled
   evidence types and whether preparation succeeded. Never record keys.
3. Validate the required inputs for enabled claims. Optional missing data yields an explicit
   exclusion reason; incompatible core inputs fail preflight before opening sessions.
4. Keep safe runtime fallback to the original proposal, but trace that Evidence was skipped.
5. Snapshot existing selected claims on public/local cases and the current candidate config.
   Preserve baseline source/config/data linkage.

Deliverable: reproducible inventory and preflight summary. Acceptance: another machine can
identify exactly which data and Evidence features would be used before a session starts.

## Phase 1 — correct units, scope and claim meaning

Priority P0. Estimated focused effort: 2–3 hours.

1. Introduce explicit price bases. Retain recorded EUR per price_unit and optionally derive
   EUR per piece/kg/metre using the part's quantity unit. Convert both operands before comparing.
   Zero, negative or invalid price_unit is a data error, never silently treated as 1.
2. Establish the arena citation convention separately from analytical normalization. Check
   quote/cost figures against the pinned kit/API contract and any existing saved claim outcomes.
   If a non-unit case remains ambiguous, keep that claim disabled until resolved; do not alter
   official cost arithmetic based on an assumption.
3. Make deterministic rendering consume verified fields. Reject or regenerate a sentence that
   disagrees with those fields. Define templates per claim kind; a figure and ID merely being
   present is insufficient validation.
4. For notice claims, resolve the trigger letter to the receiving supplier and relevant part;
   select the applicable contract at the relevant date. Assert notice_given < notice_required
   before writing that notice is short. Ambiguous matches yield no accusation.
5. Preserve scorecard OTD as requested-date OTD and distinguish confirmed-date OTD. Label
   rolling period and supplier-wide scope; do not describe it as part-specific without evidence.
6. Recheck relevance, disclosure and the total checked-claim count for the final assembled
   message, including any existing references. Coordinate this boundary with Decision's guard.
7. Keep ledger reservation before send; ensure retries reuse payload and reservation. Verify
   reconstruction from authoritative buyer history. Defer multi-recipient scope until Phase 5.

Meaningful tests: price_unit 1/100/1000; matching and mismatched price bases; truthful vs false
notice comparisons; expired/wrong supplier/wrong part contracts; sentence/figure mismatch;
unknown source; scorecard scope; existing refs plus appended claims; resume and retry reuse.

Deliverable: corrected existing claim path. Acceptance: all known counterexamples rejected or
regenerated, original proposal terms unchanged, internal values absent from outgoing messages.

## Phase 2 — current dossiers and correct payment analysis

Priority P0 for payment/source merging, P1 for broader trait lifecycle. Effort: 2–3 hours.

1. Prepare a shared base/release package and supplier dossiers before opening sessions. Reuse
   prepared data instead of rebuilding all dossiers separately for each supplier.
2. Merge case context explicitly. Preserve base/release/case values and provenance; use case
   values for that case and log collisions. Quarantine unexplained conflicts relevant to a claim.
   Do not merge only news while ignoring case documents, costs or scorecards.
3. Recalculate invoice metrics as distinct measures: ordinary-invoice days late and late share,
   cash-discount timing, and unpaid overdue count/amount as of the context date. Use the actual
   applicable due date; exclude invoices not yet due. Keep amount-weighted measures separate.
4. Preserve vendor aliases. Resolve the known old/new record sup:71999 -> sup:70210 for joined
   analysis without rewriting original citable IDs or double-counting transactions.
5. Replace permanent trait accumulation with dated evidence. Explicit expiry/hedge dates take
   precedence; otherwise mark freshness uncertain using documented signal-specific rules.
   Keep contradictory statements visible and prefer applicable, current direct evidence.
6. Make case overlays update supplier signals before TradePolicy consumes them. Never cache a
   case-specific inference globally under supplier ID alone.

Meaningful tests: sup:70210 all-invoice -8.4 days vs ordinary +11.3 days; the other three affected
suppliers; unpaid/not-yet-due invoices; aliases; conflicting/expired signals; case-only document
and news signals; release CSV/document loading; missing document text stays unknown.

Deliverable: case-aware dossiers and sourced signals. Acceptance: identical inputs give
identical output; each active signal explains its source and applicability; no hidden case leaks.

## Phase 3 — supply useful signals to Decision

Priority P1. Estimated Evidence effort: 1–2 hours plus Decision integration and experiments.

Start with signals that explain a concrete supplier constraint:

| Signal | Evidence output | Decision hypothesis to test |
|---|---|---|
| Pricing committee | Stated approval threshold, date and source | Avoid assuming the contact can approve every price move; ask about approval path |
| Fast payment / our overdue invoices | Stated preference and payment metrics, separately | Price a conditional payment trade or address our payment behavior |
| Multi-year/volume focus | Stated tenor/volume constraint and source | Propose permitted commitments whose complete buyer cost is acceptable |
| Hedged inputs | Input, coverage and expiry when recorded | Treat spot-index movements as a weak short-term cost proxy |
| Idle capacity/full order book | Current dated capacity signal | Test volume or delivery trade only where applicable |

These are hypotheses about willingness, not hard economic floors or guaranteed concessions.
Do not equate wanting faster payment with a measured 15% financing rate. Keep assumed rates
explicit and separate from observed statements. Supplier estimates stay opt-in; any activation
needs Decision to resolve quote defaults and test uncertainty scenarios consistently at closing.

Deliverable: bounded signal interface and one chosen policy experiment. Acceptance: Decision can
explain which signal caused a change; other policies and closing checks retain their contracts.

## Phase 4 — complete internal cost-pressure reasoning

Priority P1. Estimated effort: 1–2 hours plus validation.

1. Build a driver table per relevant part: weight, source, start/end month, change, contribution,
   missing-data reason and whether the supplier stated or the category team estimated it.
2. Report weighted movement as percentage points of the modeled cost base, with known coverage
   and uncovered share. Different series may end at different dates; expose the mismatch.
3. Do not silently add overlapping drivers, accept weights exceeding 100%, count duplicates or
   treat missing components as zero. Separate supplier-stated figures from verified index figures.
4. Keep partial contributions separate from a requested selling-price increase. Margin, unknown
   costs and timing prevent the partial proxy from establishing a justified final price.
5. Compare scenarios for hedges, lags and uncertain driver weights only where supported. Keep
   unsupported scenarios explicitly hypothetical.
6. Select external individual index claims for relevance to the supplier's explanation. Weighted
   aggregates stay internal unless an explicitly supported external claim format is established.

Acceptance: P01's stated-driver calculation remains 2.37 pp at 54% coverage, labeled partial;
missing drivers cannot produce a falsely complete estimate; no internal target price is emitted.

## Phase 5 — deliberate competition and optional additional evidence

Priority P2; defer if the previous gates or time budget are not met.

For rival quotes: establish same part/unit/currency, eligibility as case reference or alternative,
validity at the context date, approved sourcing and comparable complete terms. Historical low
prices with unknown validity are context, not live competing offers. For session offers, derive
facts from permitted authoritative thread state and revalidate validity immediately before send.

Integrate recipient-scoped usage with Runtime: reserve atomically, persist the exact payload,
reconcile uncertain sends, and reconstruct per-recipient usage on restart. A two-bidder fixture
must show one allowed disclosure to each recipient, no disclosure to the quote owner, and no
repeat to the same recipient. Current single-supplier eligibility must be changed deliberately.

Only then propose one bounded RFQ experiment. Keep rival disclosure disabled until this gate.

Additional data requires a concrete question: forecasts for a volume commitment, PO histories
for a like-for-like price argument, clauses for an index mechanism. Preserve stale-condition,
partial-receipt, posting-calendar and forecast-snapshot caveats. Avoid reimplementing scorecards
or creating broad spend dashboards during the first release.

## Validation and experiment sequence

1. Run relevant local tests during each phase. Before integration/push run the repository-required
   `uv run --locked pytest -q` and `uv run --locked ruff check .`. Missing dependencies/data must
   be reported; skipped dataset tests do not count as validated behavior.
2. Validate claim banks against all available public/local case metadata. Report exclusions and
   coverage by kind/supplier/part; a bank passing its own verifier is not independent evidence.
   Add independent expected-value and semantic fixtures, and compare saved arena outcomes.
3. Rehearse preparation, resume and safe fallback using local/fake transport. Use D01/D02 for
   a separately scheduled hosted contract check; they test runtime, not practice persuasion.
4. Freeze source, config and data before any paired comparison. Change one feature group,
   interleave arms and keep package policy fixed for an Evidence-only comparison.
5. Suggested practice probes, subject to a new explicit batch instruction: P01/P02 for existing
   price evidence and P11 for quality. Select cases that exercise the changed path; do not spend
   sessions on an unchanged path merely to increase repeat counts.
6. Record scores, actual claim results, duplicates/irrelevance, source hashes, fallback reasons,
   latency, completed deals, invalid actions, timeouts and unresolved requests. Cached identical
   responses establish reproducibility, not statistical significance.
7. Promote only with no new correctness/runtime failures, improved measured score and acceptable
   per-case behavior. Stop new starts on contradicted claims or unresolved runtime failures;
   finish already-open sessions safely. Remove the responsible feature before another batch.

Practice quota remains preserved. Document 13 records that the final 20-session comparison is
paused pending a new user instruction. This plan does not release it or add to the 52-session
cycle ceiling. Recheck quota before any authorized batch and retain the 46-session reserve.
Reuse/substitute within an agreed allocation rather than inventing an extra experiment budget.

## Release checklist and cut line

- [ ] Explicit data/release paths and hashes; enabled Evidence status visible before sessions.
- [ ] Price bases, scope, semantic rendering and final-message limits validated.
- [ ] Correct payment metrics and case/release merging; active signals have dates and sources.
- [ ] Evidence cannot modify binding terms or disclose private estimates.
- [ ] Used/reserved IDs survive resume; retry payloads remain identical.
- [ ] Relevant local checks plus full required suite/lint pass against the pinned dependencies.
- [ ] Behavior changes have experiment entries, with measured or pending status stated honestly.
- [ ] Sunday overlay rebuild passes targeted regressions and records excluded/changed claims.
- [ ] Runtime/Evaluation receive the prepared context, status fields and replay provenance.

Minimal first release: Phases 0–1, payment correction and case-aware merging from Phase 2.
Then add one Phase 3 signal experiment. Cut rival disclosure, new claim families and model
wording first. Do not cut unit/scope checks, preparation observability or resume safety.

Estimated total focused engineering effort through Phase 4: approximately 8–13 hours, shared
integration and hosted validation additional. This is an effort estimate, not a promise to finish
before freeze. Team feature freeze is Sunday 11 October 2026 at 10:30; no pushes or manual moves
after the 12:00 Europe/Zurich final freeze. If less time remains, use the minimal release.

First work item: make preparation reproducible, then add independent regression fixtures for
the payment reversal, false notice comparison, sentence/figure mismatch and non-unit price
comparisons before changing the corresponding implementation.
