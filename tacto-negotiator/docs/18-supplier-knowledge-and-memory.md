# Supplier knowledge and memory integration

Status: local candidate on `codex/combined-latest-updates`, 10 October 2026. No hosted score
improvement or live-policy promotion has been measured.

## Two records with different lifecycles

**Current public knowledge** comes from the versioned data package. `lab graph-export --data PATH`
projects facts as `current_public_data` nodes with source IDs, base/release layer, data hash,
and supplier/part links when those identities are present. A new release creates new fact
identities; it does not edit old conversation evidence. This is the adapter boundary for
Uğur's future ingestion pipeline. News, company updates and revised performance data should
enter through the same typed, dated, source-linked boundary. No live news collector exists yet.

**Episodic memory** records original owned sessions, messages, offers and outcomes. Barış's
`lab.memory.MemoryStore` projects cited supplier observations, records contradictions and
builds immutable discovery snapshots. Its optional live policy uses only a narrow, validated
preference vocabulary; raw supplier prose, scores and current facts do not become instructions.
The older evaluation graph remains available for feedback and imported runs.

## Feedback and live use

The lab now computes and persists descriptive feedback when a terminal run upload is accepted.
It reads earlier same-version supplier attempts from the evaluation graph. When explicitly
given a matching public package, `lab feedback --data PATH` additionally reports supplier
fact IDs in a separate `current_data_context`; mismatched data never revalidates historical
offers. Feedback does not approve a lesson, change a checkpoint, or send a negotiation move.
Barış's immutable discovery snapshots and the feedback reports are still separate inputs;
there is no automatic feedback-to-memory promotion.

## Next interfaces

1. Normalize supplier and part identities across data releases while retaining aliases,
   ownership and effective dates. Do not equate matching names with matching legal entities.
2. Add typed relations for supplier-to-part, contract, performance, contact and alternative,
   each with source, observation time, validity interval, confidence and contradiction state.
3. Extend supplier-specific episodic summaries beyond exact payment/tenor phrases. Model
   extraction may propose observations with citations; deterministic checks decide which
   observations become facts or eligible lessons.
4. Give each agent a bounded retrieval view scoped to its case, supplier, environment and
   allowed data version. Keep private evaluation outcomes out of outward arguments.
5. Require reviewed lessons and supplier/case-disjoint held-out comparisons before a memory
   preference becomes a default negotiating policy.

The graph is a provenance index, not a second price engine. Complete-cost calculations,
offer validity and accept/walk decisions stay in deterministic code.
