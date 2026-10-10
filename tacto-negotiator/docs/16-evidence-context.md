# Shared Evidence context

Implemented on `feat/evidence-context` for the existing single-supplier price-increase message
path. Explicit policy configurations retain their existing eligible case types. No new claims,
rival disclosure, cost-pressure integration, pricing, package or closing policies are enabled.

## Interface and responsibilities

`negotiator.context.build_context(case, package) -> EvidenceContext` takes an arena case and an
already loaded `DataPackage`. It reuses `case_facts`, `build_bank`, dossier preparation and trait
classification. It does not send messages, select claims, reserve IDs or modify inputs.
`package=None` is available for local case-only inspection; normal runtime uses the existing
loader and falls back to its original offer if the package cannot be loaded.

The record contains case/supplier/part IDs, schema and content versions, resolved package/release
paths, input file hashes, merged-fact and case hashes, scoped raw facts, source IDs/layers/paths,
field units and price units, existing verified claim candidates, supplier signal source IDs and
observation dates, explicit gaps and failed claim checks. It is an internal record: candidates
include adverse claims, private should-cost estimates and dormant rival candidates. Outgoing
messages receive only selected, reverified claim sentences and their IDs.

| Owner | Responsibility |
|---|---|
| Evidence | Build facts/candidates/signals, record sources, units, exclusions and failed checks |
| Decision / Samet | `PackageAgent.propose` obtains the context and passes it to `EvidencePolicy`; prices, terms and closes retain their current owners |
| Runtime | Load/cache a package, preserve exact send payloads and journals, reconcile retry/resume history |
| Evaluation | Join `evidence.context_version` to `evidence_context.context_version` and its stored sources; assess correctness and utility separately |

`EvidencePolicy.context_for(case)` caches by case and loaded fact contents. It never reserves
claims. `enrich(..., context=context)` retains the existing `pick` ordering/disclosure rules,
reverification, pre-send reservations and reconstruction from authoritative buyer-history refs.
Verification now takes optional `package` and `case` inputs to resolve notice applicability;
callers verifying notice claims must supply those inputs or explicit part scope in the facts.
Existing message refs are included in used IDs, and each consumes one claim slot conservatively.
The appended sentences are checked through the same canonical renderer used by generation.
Package files and the SQLite connection are treated as immutable during a run: reload the package
and create a fresh policy after replacing base/release inputs. Changed case/fact contents rebuild
the context without resetting usage. Do not modify returned snapshots.

`to_dict()`, `to_json()` and explicit `export(path)` provide readable inspection artifacts.
The SHA-256 content version includes resolved paths as well as contents, so exports on different
machines may have different versions. `evidence_context` traces contain the internal snapshot;
`evidence` traces contain the chosen existing claims and the same version. Keep these artifacts
internal, as with decision traces; do not attach them to supplier messages.

## Known boundaries

The follow-up verification/relevance batch strengthens the existing claim path. Each supported
kind has a canonical sentence; verification checks its figures, units, source IDs and disclosure.
Notice claims require a matching supplier and part, known contract validity at the notice and
effective dates, and strictly shorter notice. Document part scope comes from fact fields or the
existing documents table; contract scope comes from fact fields or its explicit `Parts:` line.
Missing/ambiguous applicability yields no accusation. A scorecard is no longer required to build
notice claims. Scorecards explicitly describe supplier-wide, rolling 12-month metrics and
requested-date OTD. These checks follow arena facts, not a complete interpretation of contract
prose. Passing local checks does not establish persuasion. The existing dossier overlay merges
case news only; broader document merging, expiry, payment analysis and inferred-trait citation
coverage remain gaps. Signals are classifier hypotheses with unchecked freshness, and do not
change policy. Absent index units or snapshot dates are reported as unknown rather than invented.
Optional signal preparation failures preserve valid claims; claim-preparation failures leave an
empty bank and an explicit gap. Missing referenced facts and rejected candidates are inspectable.

## Local P01 example

Run from `tacto-negotiator` using Python 3.12 and the pinned lockfile:

```bash
export ARENA_DATA="$(realpath ../negotiation-arena-kit/data)"
uv run --locked python tools/evidence_context.py --data "$ARENA_DATA" --out /tmp/p01-evidence-context.json
uv run --locked pytest -q
uv run --locked ruff check .
```

The fixture is `tests/fixtures/practice_cases.json`; it needs no API credentials or session.
The base snapshot selects notice **51 days** against **90 required**, electricity index
**−3.7%** (2025-08 to 2026-08), and supplier scorecard OTD **85.2%** (`sc:70110@2026Q3`).
The bank also preserves LCI-C **+2.7%**, PPI-C241 **+6.5%**, and scorecard **712 ppm**;
these are not selected in the initial default message. Independent expected-value tests and an
exact comparison with the current bank/pick confirm the context preserves selection.
The follow-up local audit of all 19 saved cases preserves default selected kinds/IDs/figures;
P02 and P17 lose invalid, previously unselected notice candidates that were not actually short.

## Hosted-run handoff checklist

This is the proposed team checklist, ready for Runtime/Evaluation agreement; no team sign-off or
hosted validation is claimed. The user-authorized implementation excludes hosted runs.

- [ ] Evidence/Decision/Runtime/Evaluation review this interface, private-artifact handling and known gaps.
- [ ] Freeze source revision, policy config, base/release hashes and context export; rerun required local checks.
- [ ] Runtime checks current authorization, quota, deadlines and freeze rules; retains the paused practice comparison.
- [ ] Under a separate hosted-run instruction, choose the case set and session allocation before starting.
- [ ] Use separately authorized D01/D02 checks for transport/recovery; confirm journal retries reuse exact payloads.
- [ ] Evaluation links each selected claim through context version to its IDs, figures, units and sources.
- [ ] Compare complete term sheets and closing outcomes with the frozen baseline; verify private values never appear in messages.
- [ ] Verify resumed buyer refs prevent repeats, and missing inputs preserve offers with visible exclusions.
- [ ] Record actual arena claim outcomes, latency, invalid actions, timeouts, unresolved sends and quota usage.
- [ ] Stop new starts on contradicted claims or runtime failures; finish open sessions safely and record the decision.

## Claim relevance follow-up

For existing index candidates, `index_relevance` prioritizes series named in the latest supplier
message, then the trigger document/case index references, then recorded part cost drivers.
Only known series IDs are matched; untrusted prose cannot authorize a claim or change disclosure.
This ranking operates within existing claim-kind order and still excludes adverse/cherry-picked
claims by default. A decline in a listed but unmentioned driver remains eligible as a secondary
argument. No weighted cost claim or policy change is introduced.

The `evidence_selection` trace records index relevance reasons, remaining checked-claim slots and
selected kinds/IDs, including empty selections. Existing `evidence` and `evidence_context`
records retain their context-version link. Relevance is a bounded heuristic, not a measured
supplier persuasion model. Local checks establish a preparation/message contract, not measured
hosted benefit or promotion.
