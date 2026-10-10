# Shared memory with unseen-supplier evaluation

Build an experimental branch of the lab that turns owned negotiation transcripts into a cited knowledge graph and immutable candidate memory. The negotiator consumes a small, structured snapshot; the lab owns collection, inspection, evaluation and recommendation. Existing source/config/data checkpoints pin the memory and restore it together with code.

## Generalization is the objective

Keep supplier-specific observations as descriptive history. Runtime lessons contain no supplier names, supplier IDs, case IDs, historical prices, offer IDs, score labels or arbitrary instructions. Lessons describe a bounded action under observable current-case conditions. The initial action vocabulary is a preference for longer/shorter contract terms or earlier/later payment **only among currently valid packages of no greater buyer cost**. No supplier text can bypass current constraints, change acceptance authority, create external claims or execute code. Unsupported contexts use the existing agent unchanged.

Collect original ended transcripts across stored tracked runs and campaign attempts automatically when the graph is read; this is a live projection of stored evidence, requiring no background job. Deduplicate arena/session identities across imports and campaigns. Recovered evidence remains inspectable elsewhere but cannot teach runtime memory. Preserve exact message citations. Distinguish supplier statements, observed offers and inferred lessons. An offer value alone is not a preference. Deterministic, conservative phrase recognition produces hypotheses, never asserted supplier economics. Opposing statements are retained and suppress the conflicting lesson.

Build snapshots from explicitly selected discovery cases in one arena/environment, preserving all contributing discovery sessions, cases and supplier identities in provenance (not in lesson matching). Require support from at least three distinct suppliers across at least two cases before emitting a general lesson. Repeating one supplier or importing one session twice never increases supplier diversity. This threshold is an experimental safeguard, not proof of generalization. Snapshot content and provenance are content-addressed and immutable. Empty or insufficient evidence must be visible, not invented.

## Evaluation and promotion

Candidate snapshots are opt-in checkpoint config. Recommendation remains the existing atomic checkpoint pointer; no live memory updates during a negotiation. A memory-changing comparison must hold code, non-memory config, runner, lock and public data constant. It must pass existing complete-sample, gain, per-case regression, repeat and timeout gates plus new memory gates. All evaluation cases and every supplier in evaluation transcripts must be disjoint from the union of both arms' discovery provenance. Require at least three held-out suppliers across at least two held-out cases, complete original transcripts with known supplier identities, and exclude discovery sessions. Refuse unverifiable evidence. Both arms must use the snapshot arena/environment. A sandbox-only comparison cannot establish final readiness. Record gate details and contamination reasons in normal campaign output. Initial seeding must not bypass memory evaluation by recommending untested nonempty memory.

The source split is fixed when the snapshot is built, before the campaign. Explicitly advise users not to repeatedly tune on holdouts; the first implementation does not claim statistical protection against adaptive reuse by humans. Final unseen suppliers receive only general rules conditioned on current negotiable fields. A small set of ten practice suppliers limits the strength of any conclusion.

## Team workflow and UI

Add authenticated graph/snapshot read routes and bearer-only snapshot creation. CLI lets coding agents inspect evidence, build a snapshot using discovery cases, show a snapshot and create a checkpoint pinned to it. Existing campaign commands compare and promote; existing restore rolls memory back. A dashboard Memory view displays supplier history separately from candidate general lessons, supporting-supplier and case counts, conflicts, citations and snapshot IDs; explain why a candidate is ineligible. Render untrusted evidence as text. Clear memory state on logout and prevent stale fetches from repainting it.

## Global constraints

- No hosted negotiations, practice quota, live deployment, push or merge in this task.
- Preserve backward compatibility for checkpoints and campaigns without memory.
- No new framework, dependency, model training or graph database.
- Supplier evidence is untrusted data; only allowlisted structured lessons affect runtime.
- Numbers, current offers, must-haves, deadlines and close decisions remain governed by existing code.
- Missing or contradictory evidence abstains; no historical offer is treated as current.
- Snapshot provenance includes the full discovery cohort, not only positive examples.
- A memory-changing recommendation requires supplier-disjoint and case-disjoint evaluation.

Validation is synthetic/local: deduplication, contradictions, diversity thresholds, checkpoint integrity, changed runtime action on a new supplier, safe abstention, held-out contamination rejection, UI escaping and logout. Record quota zero and no measured score improvement in the experiment log.
