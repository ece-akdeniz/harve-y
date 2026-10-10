# Shared Experiment Dashboard Implementation Plan

**Goal:** Let four laptop runners automatically publish reproducible experiments to one authenticated dashboard.

**Architecture:** A separate lab command layer uses the existing arena agent interface. A small local
HTTP service persists versioned snapshots in SQLite; browser UI and uploader share one port.

**Tech stack:** Python 3.12, standard-library HTTP/SQLite, existing HTTPX/Pydantic/dotenv, vanilla HTML/CSS/JS.

**Spec:** `docs/superpowers/specs/2026-10-10-experiment-dashboard-design.md`

## Global constraints

- Keep existing negotiation behavior and final runner unchanged.
- Never consume hosted practice quota during tests; use fake/local transport.
- No new frameworks. No secrets, source patches or credentials in uploaded run metadata.
- New browser/API operations require authentication; no spectator endpoints in agents.
- Preserve failed/missing attempts and distinguish imported history from tracked experiments.

## Task 1: Data contract, store and authenticated server

Files: `src/negotiator/lab/{models,store,server}.py`, `tests/test_lab_server.py`.

- [x] Write tests for authentication, invalid payloads, duplicate and stale revisions, persisted
  results, immutable manifest fields, missing-score summaries and case-aligned comparisons.
- [x] Run tests and confirm failures before implementation.
- [x] Implement a bounded validated Run snapshot; SQLite store with atomic revision checks;
  read-only browser cookie and bearer upload authentication, login/logout, static assets.
- [x] Run targeted tests and review server/store behavior.

## Task 2: Local runner, durable publishing, history import and commands

Files: `src/negotiator/lab/{__init__,cli,runner,publish,history}.py`,
`src/negotiator/cli.py`, `tests/test_lab_runner.py`.

- [x] Write tests for offline persistence/retry, provenance capture, budget/case validation,
  interrupted/failed attempts, read-only import and session deduplication.
- [x] Run tests and confirm failures before implementation.
- [x] Add init/serve/run/sync/import commands, built-in package/naive agents and local module:factory
  extension. Use explicit cases/repeats and max sessions, serial execution, background upload.
- [x] Persist metadata before sessions open, update on session creation and attempt completion,
  retain local failure evidence and print useful exit codes without secret/error-body leaks.
- [x] Exercise run/import against a fake arena and sync against the real local dashboard server.

## Task 3: Shared dashboard UI

Files: `src/negotiator/lab/static/{index.html,app.css,app.js}`.

- [x] Implement login, filters, live status, run detail and case comparison against the frozen API contract.
- [x] Render untrusted values as text, validate replay URLs, keep auth tokens out of browser storage.
- [x] Verify empty/error states, seeded synthetic experiments, failed attempts and narrow viewport.

## Task 4: Documentation, integration and review

Files: `docs/12-experiment-dashboard.md`, README, `.env.example`, `.gitignore`, experiment log.

- [x] Document one-host/four-laptop setup, secret distribution, VS Code forwarding, history import,
  local buffering, recovery, comparisons, quota coordination and current final-runner limitations.
- [x] Run `uv run --locked pytest -q` and `uv run --locked ruff check .`.
- [x] Request an independent code review and resolve actionable findings.
- [x] Start a clean local dashboard and give the user the exact VS Code forwarding step.

## Execution notes

Work is on `codex/experiment-dashboard` in the user's existing clean checkout. User approved the
design and implementation in chat. Keep changes reviewable here; no push or merge is requested.
Baseline: 15 tests passed using the locked dependency revision. No hosted sessions opened.

Final verification: 71 tests passed; Ruff, JavaScript syntax and whitespace checks passed.
Independent review findings were fixed and the scoped re-review found no remaining actionable issues.
The real authenticated server is on loopback port 8000 with secure cookies and zero records.
Earlier browser checks covered login, list/detail/comparison and mobile layouts using synthetic data.
The final browser reopening timed out; direct HTTP authentication and clean-state checks passed.
Public port forwarding and teammate setup remain user steps documented in the guide.
