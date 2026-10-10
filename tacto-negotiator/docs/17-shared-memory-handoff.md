# Shared supplier memory: integration handoff

## Ownership

Barış owns the knowledge graph and shared memory service in y/agent lab. Uğur owns the final
data ingestion implementation. Samet owns the interface and Decision policy. This branch keeps
the small ingestion adapter for comparison and replacement, and adds the graph exchange contract
and feedback reader. It does not deploy a graph database or change the team's shared service.

## Implemented exchange

```sh
uv run --locked negotiator lab graph-export --db experiments/dashboard.sqlite3 \
  --out experiments/knowledge-graph.json
uv run --locked negotiator lab feedback --data "$ARENA_DATA"
```

These commands use saved records and make no Arena requests. The JSON output is ignored by Git.
`lab/knowledge.py` supplies `export_graph`, `MemoryReader`, and the reference `SnapshotMemory`.
The authenticated feedback read API uses the same reader. No additional interface work is needed
to consume its `memory_context` field; Samet can decide how to display that evidence.

The version-1 graph contains run, attempt, case, supplier, message, offer and feedback-observation
nodes, connected by typed edges. IDs are deterministic hashes. Regeneration is idempotent for an
unchanged snapshot and independent of input ordering. Source hashes identify changed snapshots.
Messages retain attribution, original text, claims and offer data; they are not verified facts.
Feedback findings retain supporting run/attempt/message references and proposed disposition.
Original failed attempts and their separately reconciled outcomes remain separate data fields.

Supplier and case identities include Arena origin, environment and data fingerprint. Unknown
fingerprints include the run ID, deliberately preventing automatic joins across unknown releases.
Entity names alone are not identity keys. Observations retain run, attempt, case, session, supplier,
message index, recorded time, source commit when available, and source snapshot hash. Historical
import timestamps are recording times, not proof of the underlying commercial event date.

## Read contract for agents

`MemoryReader.supplier_history(run, supplier, purpose="feedback", limit=20)` returns bounded prior
attempt nodes for the exact data/environment scope. It excludes the current run and records newer
than the run's start time. Feedback cites earlier failed attempts as a reason to compare causes;
it does not infer that the supplier caused the failure or that any tactic caused a score gain.

All exported nodes currently have `scope="evaluation_only"`. The reference reader returns no raw
history for `purpose="live"`. Barış's service should implement the same contract and add a separate
approved lesson projection before wiring live agents to it. That projection needs evidence IDs,
applicability conditions, data scope, valid-from/expiry, confidence, conflicts, approval identity and
the paired experiment that supports adoption. A graph edge or repeated observation is not approval.
The live runtime must never obtain historical scores, private supplier state or spectator data via
the graph. Public supplier facts and current owned-session observations are distinct access classes.

For future verified facts, parts, people, authority changes and lessons, extend the schema with
typed nodes rather than interpreting arbitrary message text as fact. In particular, the saved
run schema does not contain reliable historical part IDs or current personnel identities; this
export does not invent those links. Preserve contradictory observations and their sources.

## Uğur's ingestion boundary

Keep `dossiers.load_package(data_dir, release)` as the entry point or supply an adapter with
`facts`, `cases`, `lookup`, `ids`, `query`, `root`, `release`, `manifest` and `conflicts`. Existing
callers consume public facts, dossier data and case-local overlays; they do not need a graph DB.
The current `VersionedPackage` remains available as a reference implementation. Preserve missing
table diagnostics, explicit source versions, unresolved conflicts and fresh supplier fallback.
`context_manifest` records the case hash as well as the input data hash.

Two hashes currently have different formats: the ingestion manifest hashes per-file hashes; lab
provenance uses `lab.runner.fingerprint_data` and its explicit release combination. Do not compare
them directly. Preserve the existing lab hash when replacing ingestion, or migrate the schema and
stored manifests explicitly. Historical arithmetic checks run only against a matching lab data
fingerprint and remain qualified because session-local overrides may be unavailable.

## Barış's next integration steps

1. Import the snapshot using node/edge IDs as upsert keys, with authenticated team access.
2. Back `MemoryReader` with graph queries and preserve data/time/access filters.
3. Accept provenance-bearing public facts from Uğur and link parts only from explicit source IDs.
4. Add proposed lessons and an explicit reviewed promotion path tied to lab campaign evidence.
5. Expose that bounded approved projection to agents; retain full history for evaluation/feedback.

This is a local handoff, not a shared-host deployment. The existing local database contains 100
run records / 113 attempts. Initial export: 4,356 nodes and 6,268 edges. Server-only history has
unknown source/configuration; its supplier identities remain isolated until a reliable version
mapping is supplied. No historical result is silently promoted into the live negotiator.
