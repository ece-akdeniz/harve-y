# Shared experiment dashboard

Approved direction: four teammates run agents on their own laptops. One laptop hosts a shared
dashboard and upload API behind VS Code port forwarding. This is development tooling; it does
not replace the negotiation runtime or make the agent ready for the final.

## Scope and architecture

One Python service serves static HTML/CSS/JavaScript and a JSON API, backed by SQLite. Use the
standard library and existing dependencies; no frontend build step or new application framework.
The new `negotiator lab` commands are separate from existing play/run and final operations.

Each local experiment records its hypothesis, owner, agent factory, JSON configuration, exact
commit, dirty status, dependency lock hash, data fingerprint, case set, repetitions and baseline.
Clean commits are required by default. An explicit dirty override records a patch hash and saves
the patch locally, labels the run unreproducible from Git alone, and never uploads source code.
Environment secrets are excluded. Agents implement the existing `decide(case, threads)` contract.

An experiment owns independent attempts, one per case and repeat. Persist the complete snapshot
locally before publishing. Monotonically increasing revisions make retries idempotent and prevent
late uploads from undoing finished results. Network publishing runs outside the negotiation loop;
an unavailable dashboard cannot fail the negotiation. `lab sync` republishes saved snapshots.

Host initialization generates a dashboard password and a separate upload token in an ignored,
owner-readable file. Browser login uses an HttpOnly, SameSite cookie; writes need the upload token.
The server binds loopback by default. Public VS Code forwarding requires application authentication;
credentials never appear in URLs, logs, HTML or run metadata. Forward only the application port.

## UI

The dashboard has a password login, an experiment table with author/status/search filters,
summary cards, a baseline/candidate comparison and run details. Details include configuration,
provenance, attempt status, normalized scores, cost components, errors and a link to Tacto's replay.
Use automatic polling, visible connection errors, accessible forms and responsive layout.
No placeholder scores in the normal dashboard; an empty state explains how to submit the first run.

Comparison uses the intersection of case IDs and displays repeat counts and per-case deltas.
Missing/failed attempts remain visible, and incomplete runs never get an unqualified aggregate.
Different arena/data environments are flagged. Simulator, sandbox and practice are distinct.

## History import

A host-side CLI command uses the existing arena client to GET practice/sandbox session history,
session results and replay URLs. Import is read-only and does not open sessions. Preserve unknown
code/configuration as unknown. Deduplicate by arena URL and session ID, including sessions already
linked to tracked experiments. Do not read spectator endpoints or import live final information.
Arena credentials stay server-side. Imported history and locally instrumented experiments are labeled.

## Limits

No automatic global quota enforcement in this version. Show authoritative quota snapshots and
require a per-run session ceiling; document that all laptops share the team limit. Run cases serially
per laptop initially at a conservative request rate. No speculative hosted test runs. No remote
execution, agent editing, general plugin framework, model integration or new negotiation strategy.

## Verification

Use temporary SQLite databases, a fake HTTP arena and actual local HTTP requests to exercise
authorization, stale/duplicate snapshots, validation, missing outcomes, comparisons, offline sync,
imports and the CLI. Run the existing pytest/Ruff checks. Verify login, empty state, live results,
comparison and mobile layout in the browser with clearly synthetic local fixtures, then start a
clean dashboard for the user. No credentials or synthetic runs enter Git.
