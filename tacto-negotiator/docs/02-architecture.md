# Architecture and shared contracts

Target design. Track implementation in [10](10-implementation-checklist.md).

## Data flow

```text
package + Sunday overlay -> versioned dossiers and candidate claims (before clocks)
case facts -> context -> complete candidate packages -> economic evaluation
reply -> authoritative state + interpreted hypotheses -> worker proposal
proposal -> validation -> case coordinator -> send or close
all transitions -> durable state/request journal + trace -> evaluation and replay
```

Use Python 3.12, SQLite, typed records, HTTPX and bounded concurrency. Reuse official arithmetic
and document readers. A model interprets/words moves; templates remain available.

## Ownership and interfaces

| Module | Owner | Contract |
|---|---|---|
| optimizer | Decision | Package -> cost components, feasibility, alternative comparison, supplier scenarios |
| policy, guards | Decision | State snapshot -> proposal; validate every send and close |
| client, runner, state, trace, config, cli | Runtime | Bounded execution, coordinator, durable/resumable operations |
| dossiers, traits, claims | Evidence | Versioned sources, dates, units, relevance and hypotheses |
| writer, beliefs | Evaluation with Decision | Typed interpretation, bounded writing, deterministic fallback |
| report, experiment harness, replay | Evaluation/pitch | Comparable metrics and inspectable decisions |

Function signatures are scaffolds. Update owners and tests when changing them. Closing needs
all threads and per-supplier estimates, not one thread alone.

## Shared records

- **Package:** exactly permitted negotiable fields, supplier, received offer ID if applicable,
  resolved standard/fixed terms, must-have result, cost components and estimate version.
- **Claim:** kind, IDs, typed figure/unit, supplier/part, date/window, generated sentence,
  arithmetic check, relevance hypothesis and disclosure class. Weighted index proxies stay
  internal unless the hosted checker explicitly supports the aggregate claim format.
- **Proposal:** send/consider-accept/consider-walk, packages, claims, question, reason,
  state version and expiry. The model cannot send requests or close directly.
- **Thread:** messages, latest quote standards/standing sheets/status, server rounds/timeouts,
  observed timestamps, in-flight operation and supplier hypotheses.
- **Case:** session/wave/deadline, threads, per-supplier estimates, alternative, used/reserved
  claim scopes, closing state, result and immutable run configuration.
- **Journal:** logical move ID, exact payload/endpoint, session/thread, state version,
  created/sent/acknowledged times and response or unresolved outcome. No credentials.

Claim scope is per case except eligible rival quotes/offers, tracked per recipient. Reserve
usage atomically; retrying an operation does not consume it again.

## Coordinator and concurrency

One coordinator owns **accept and walk-away** for the case. Workers propose; each thread has
at most one unresolved send. `agreed` is a closing proposal, not permission to bypass checks.
Before closing, reconcile current state, compare all eligible offers and the alternative,
account for in-flight requests and serialize the decision. Cancel unsent work; cancelling a
local HTTP task does not establish that its server move was cancelled.

Hold state locks briefly, never across model calls, attachment downloads, HTTP waits or retry
sleeps. Compute from a versioned snapshot; revalidate before transmission. Persist first.
Use one key-wide limiter for reads/writes/retries across all processes. Aim about 8 calls/s,
without bursts over the server's 10/s limit. At most 10 open sessions.

The official client anticipates per-session queuing. Test D02 before claiming async fixes
starvation. Record when clocks stop while requests wait and supplier replies generate.

## Two clocks

- **Buyer:** 60 seconds per thread. Supplier generation is excluded from its own response
  interval; queuing and other-thread effects need hosted confirmation.
- **Wave:** hard 8-minute cap; use fresh permitted case metadata `seconds_left`. Do not assume
  supplier inference pauses it or infer a fixed wall-clock schedule for all waves.
- **Engineering targets:** model p95 <=20 s, attempt <=30 s, total buyer work <=35 s. Include
  parsing, retrieval, limiter waits, retries and any interpretation call. Enforce an end-to-end
  deadline; socket timeout alone is insufficient. Disable or budget SDK retries.
- **Arena HTTP:** start with the official 180 s guidance, which grants no extra buyer/wave time.
  Initial close margin: max(90 s, slowest round +15 s), then validate queued acceptance behavior.
  All fallback closes still use our complete evaluator.

Prepare static context before opening. Fetch opening quote PDFs promptly; their defaults matter.
Do not accept without resolving required defaults or explicitly evaluating uncertainty.

## Persistence and failures

Use monotonic clocks for elapsed runtime; persist UTC timestamps and server deadline evidence.
Never restore a previous process's monotonic timestamp as a valid clock. After restart, load
journal, fetch sessions/threads and reconcile pending IDs before another POST. Do not blindly
reopen a final case. Read server rounds; counting our messages misses timeout rounds.

422 -> repair validation. 409 -> reconcile. Retryable transport/5xx/short rate limit -> reuse
same ID/payload within deadline. Quota exhaustion and ended waves are not generic retry cases.
A 409 alone does not authorize a fresh session or walk-away.

## Economics and data

Use `total_cost(case, terms, standard, supplier_estimate)` for relationship-sensitive goals.
Latest quote standards and fixed case terms take precedence over generic vendor defaults.
Do not reuse `play.closing_move` unchanged: it omits supplier estimates.

Retain base, release and case facts separately with provenance. Use case-specific values as
provisional authority for that case, logging collisions; resolve unexplained conflicts before
freeze. Sunday data is an overlay, not a changed SQLite database: load its facts, CSVs and
letters through DataPackage or an equivalent loader. Validate `price_unit` in joins and derived
costs. Do not silently change official arithmetic; confirm case-quantity normalization with
organizers and a hosted result comparison.

## Trace

Record UTC time, case/session/supplier, state version, clocks, offer IDs, complete terms,
C/components, supplier assumptions, alternative comparison, claim outcomes, guard outcomes,
model latency/fallback, request ID and a concise decision summary. Do not request private
chain-of-thought. Evaluation and the pitch viewer consume this same trace. Unknown optimal
cost components remain unknown.
