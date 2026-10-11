# PD1 lifecycle batch implementation evidence

Date: 11 October 2026 (Europe/Zurich). Scope: PD1.1 and timeout/fallback/pre-POST portions of PD1.2. This is local implementation evidence only; it does not authorize hosted inference, Arena execution, Lab publication, D02, P10, push or promotion.

## Implemented

- `DecisionModelLedger` owns interpreter/proposer/selector stage caps, total call/token/time admission and synchronous revocation on timeout, uncertain transport failure or cancellation. Existing 8/4-second stage ceilings are centralized in the ledger and clipped by the original decision deadline, computation allowance and fallback/submission reserves. Unknown timeout usage retains the full reservation.
- The model gateway requests per-stage budgets from the ledger. Model unavailability no longer blocks an independently validated fallback action. A local end-to-end official-Sim regression times out interpretation, validates the deterministic fallback and records one submitted buyer move.
- The synchronous Lab callback runs its async decision in a daemon worker so `asyncio.run()` cleanup cannot hold the caller past its original compute/deadline window. A run-wide model-call gate lets a whole-decision timeout stop later calls, including while a worker is cleaning up. The agent revokes execution and requires recovery; no late result is applied to agent state.
- Offline decision stages now record elapsed time. Historical stage serialization omits the new field when it was absent, preserving old trace hash projections.
- Journaled Arena POSTs pace first, refresh owned session/thread state, run the final exact-payload validator, persist the exact operation, and issue one request. A rejected pre-POST check creates neither an intent nor a POST. Uncertain writes remain journal-owned and are never retried automatically.

## Evidence

Local checks, no provider/Arena/Lab network calls:

```text
pytest tests/v2/integration/test_grounded_model.py tests/v2/integration/test_adaptive_proposal.py tests/v2/integration/test_hosted_sandbox.py tests/v2/acceptance/test_model_budget.py tests/v2/integration/test_lab_integration.py
74 passed, 2 xfailed

pytest tests/test_lab_runner.py  [localhost socket binding allowed]
32 passed

scoped Ruff check
All checks passed

git diff --check
clean
```

The two acceptance xfails require the absent `negotiator.v2.adapters.recorded` module; they do not exercise these Lab bridge fixes. An initial sandboxed Lab-runner attempt failed because the environment denied localhost socket binding. The same local-only suite passed when run with socket permission.

Focused regressions cover timeout reservation and later-call rejection; stage cap/deadline clipping; complete synchronous return ahead of cancellation-resistant cleanup; timeout fallback through independent validation and one simulator submission; fresh post-pacing validation; exact journal/header/body linkage; and zero POST/intent after stale dispatch rejection.

## Fingerprint and limits

Selected implementation and regression files as present at review have aggregate SHA-256 `19f6668bb1bba9cd2899f4c3288e9ad748999f86b71b58872559b42d642a8073`. It hashes the ordered per-file `sha256sum` output for the files touched by this batch, including the already dirty workspace contents. Workspace HEAD is `a88bf86820214be9fdf4e0d4e679675d946e0607`, but the repository had extensive pre-existing tracked and untracked V2 work; HEAD alone does not reproduce this fingerprint.

PD1.3 durable terminal/publication recovery, real-model latency measurement, hosted validation, commercial-effects work and run-level strategy persistence remain deferred. The background worker is bounded from the caller's perspective; cancellation-resistant provider cleanup can continue in its daemon thread and may still incur provider charges. No hosted validity or negotiation-quality claim is made.
