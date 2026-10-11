# Harvey supplier workspace

Open `/workspace` on the existing lab host and sign in with the same team password.
The experiment lab links to it in its sidebar. This is a human-facing, read-only view;
it does not start sessions, call a model, send supplier messages or promote policy.

## Included

- Overview with simulated cost reduction, supplier/session counts, marked-running
  sessions, historical failures and overdue uploads, and recent activity.
- Searchable supplier directory, separated by environment and arena identity.
- Supplier pages with selectable historical negotiations, polling conversations,
  first/latest supplier sheets versus final selected terms, complete outcome cost,
  recorded must-have status, version-scoped memory, recorded configuration and
  source-backed feedback suggestions. Missing records are explicitly labeled.
- The UI checks uploads every five seconds while visible. It does not establish a
  direct streaming connection to the Arena. Current tracked runners primarily attach
  conversations after attempt completion; per-message streaming requires runner telemetry. Source timestamps and overdue uploads
  remain visible; loss of the lab connection retains the last view and shows an error.
- Authentication is the existing read cookie or bearer token. All supplier content
  is rendered as text. Logout clears rendered supplier evidence; late requests
  cannot repopulate it. Existing CSP applies to the new static assets.

## Metric definitions

Savings are `c_open - c_deal`, using the latest recorded session for each arena/case
in the selected environment. Eligibility requires an original completed and ended
session, a deal, satisfied must-haves, a selected supplier, finite recorded costs,
and positive opening cost. Cost increases remain negative. The coverage count and
baseline description accompany the metric. A newer failure does not cause fallback
to an older success. This is a latest-case snapshot, not a sum over experiments or
realized business savings. In RFQs, opening cost can represent another supplier.

Canonical arena/session records deduplicate campaigns, tracked runs and imported
history in that priority order. A case score or cost is attributed only to the
selected supplier. Conversation participation alone never earns the case outcome.

## Evidence boundaries and remaining work

Supplier memory shows observations for the selected case, arena, environment and
known data version. It is a human history view, potentially including observations
from later sessions. Matching supplied facts retain their original dates, validity
and sources. Neither implies that the runtime consumed those records. Unknown data
versions do not match one another. Up to 100 facts and 100 observations are shown
with total counts; the full existing lab memory view remains available.

The approach tab shows saved configuration, not a claim about the currently deployed
agent. Next steps are descriptive saved feedback or explicit review guidance, not
an invented agent plan. Editing policies, pausing agents, approved-lesson management,
per-decision retrieval traces and detailed requirement thresholds need additional
runtime/API contracts and are not controls in this release. Campaigns only upload
available outcome evidence; this interface cannot invent in-progress conversations.

## Verification

Run the repository's full pytest suite and Ruff before publishing. The deployment
workflow checks server, workspace, supplier-graph and learning tests. New regressions
cover eligibility/negative savings, repeated-case accounting, latest failures,
authentication, immutable originals, losing suppliers, memory isolation and campaign
versus import deduplication. Browser verification covers login, search, all supplier tabs,
negotiation switching, retained disclosures on refresh, mobile overflow and logout.

## Shared supplier knowledge (2026-10-11)

The orange/neutral workspace adds **Shared knowledge** navigation and a **Knowledge
graph** supplier tab. The global view also includes suppliers found only in supplied
master data, before they have any saved negotiations. A grouped interactive graph
opens records, graph relationships and original source citations. It joins parts,
contracts, performance, supplied news/documents, runs/contributing agent configurations,
shared observations and unresolved conflicts. Search and progressive lists keep large
groups usable. Source evidence is rendered as text, never interpreted as instructions.

The default scope is the most recently first-ingested supplied dataset. Agent evidence
joins only on its exact recorded data fingerprint and selected environment/arena.
An explicit run-history scope shows all source versions in distinct partitions;
unknown versions are partitioned by original source run/campaign. Repeated IDs across
releases do not establish the same supplier identity. Repeated offer observations
combine with support/session counts and up to 20 citations; different offers are not
inferred preferences. Explicit opposing statements are visible as conflicts. Raw
conversation interpretation remains the existing conservative memory extractor.
This is a shared human evidence view: approved runtime memory/policy does not change.

Source cards show original dates and ingestion/check timestamps separately. Expired,
future-dated and undated records remain visible and labeled. **External news/company
feeds are a concept only**, with a dashed, expandable source-flow illustration. They
are not connected and do not fetch, schedule or fabricate news for synthetic suppliers.
There is no automatic background external ingestion.

Register each new supplied base/release on the lab host with:

```sh
negotiator lab learn ingest --db /var/lib/y-agent-lab/dashboard.sqlite3 \
  --data /path/to/new-supplied-data --release /path/to/optional-release \
  --label 'Test release name'
```

Omit `--release` when none is supplied. The loader's resolved overlay (including its
existing automatic discovery) participates in the fingerprint. Supplier/part master
records and company profiles are included when available; facts-only packages remain
supported. Reingesting an unchanged package enriches old projections and updates its
checked time but preserves its first ingestion order. No upload control is added to
the read-only browser. Refresh the workspace after registering a new dataset to reload
the selector/catalog. The graph checks evidence at most every 30 seconds; conversation
checks remain every five seconds.

Tests in `test_supplier_graph.py` cover aggregation across cases/contributors, new
suppliers without runs, reused IDs in unrelated new datasets, unknown-version/arena/
environment isolation, dated/conflicting records, discovered-release fingerprints,
recheck ordering and authenticated routes. They run in the deployment workflow with
existing workspace/server/learning regressions. Browser checks cover groups, citations,
history scope, source concept, tab switching, desktop/mobile and clearing on logout.

## Supplier brief and conversation reader (2026-10-11)

Shared knowledge now opens with a short relationship brief: saved history, attributable
results, remembered facts, a suggested approach and one prominent next step. Conversation
recaps compare the opening and latest structured offers with the saved outcome. The
brief combines matching saved runs and contributing agents within one dataset/arena
partition. Supplied-only suppliers receive a clear empty-history state.

These are deterministic, source-linked summaries, not model-generated interpretations
of the whole discussion. Topic excerpts preserve the original wording and negation;
mentions do not establish preferences. Historical offer ranges are labeled as observations.
Suggested approaches and next steps are untested human review guidance. Latest recorded
configuration does not establish the active or best policy. Savings use only the latest
case record, without multiplying repeated experiments or falling back after failure.

Conversations have a searchable session list, outcome filters, a short recap, message
search, role/offer filters and expandable full text. Structured terms highlight changes
against the same speaker's previous offer. Source links open the original message.
Unknown timestamps and missing fields are not invented. The same reader is used on
supplier pages; logout clears its evidence and invalidates late responses.

The orange/neutral design remains, with larger readable text, plain-language orientation
and a short default view. Extra ideas, quotes, methodology and saved configuration are
collapsed. Graphs and source ingestion stay in separate tabs. We applied the official
[Impeccable](https://github.com/pbakaus/impeccable) simplification and clear-copy guidance
to the existing frontend; no Impeccable CLI, hooks or UI dependency was installed.

Six report regressions cover citations, outcome attribution, latest-case accounting,
version/environment isolation, preserved negation and malformed optional fields. Browser
checks cover the new report, partition selection, search, evidence navigation, retained
graph/source concept, supplier-page integration, logout and mobile overflow.

## Short default view (2026-10-11)

The default summary now shows two outcome numbers, one suggested next step and two
remembered points. The full relationship report, citations, original recaps, settings
and methodology remain available behind disclosures. Repeated supplier headings and
technical IDs were removed from the main reading path; data boundaries are still
available under Data settings / Data sources. Case-specific memory retains its case.

Chat history uses compact case/outcome rows, a two-change recap and shorter message
previews. Full messages and offer details are expandable, and evidence links still open
the exact message. Overview and supplier cards use fewer rows and shorter labels.
Environment controls are tucked away, onboarding help is removed at the user’s request,
and content uses larger body text.
No API, reporting arithmetic, evidence scope or runtime negotiation behavior changed.
