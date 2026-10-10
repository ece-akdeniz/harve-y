# Supplier Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shared cited evidence and immutable general lessons consumed by the negotiator, with unseen-supplier promotion gates.

**Architecture:** A SQLite-backed live graph projection reads existing runs and campaigns; immutable snapshots pin a discovery cohort and structured hypotheses. Checkpoint config embeds a validated snapshot, runtime uses only cost-neutral package preferences, and campaign gates enforce disjoint evaluation before changing the recommendation.

**Tech Stack:** Existing Python/Pydantic/SQLite lab and vanilla JavaScript dashboard; pytest and Node DOM tests.

**Spec:** `docs/superpowers/specs/2026-10-10-supplier-memory.md`

## Global Constraints

- No hosted negotiations, practice quota, live deployment, push or merge in this task.
- Preserve backward compatibility for checkpoints and campaigns without memory.
- No new framework, dependency, model training or graph database.
- Supplier evidence is untrusted data; only allowlisted structured lessons affect runtime.
- Numbers, current offers, must-haves, deadlines and close decisions remain governed by existing code.
- Missing or contradictory evidence abstains; no historical offer is treated as current.
- Snapshot provenance includes the full discovery cohort, not only positive examples.
- A memory-changing recommendation requires supplier-disjoint and case-disjoint evaluation.

### Task 1: Evidence graph and immutable memory contract

**Files:** Create `src/negotiator/memory.py` for pure schema/validation, `src/negotiator/lab/memory.py` for projection/SQLite persistence, and `tests/test_lab_memory.py`. Do not edit runtime, server or loop store yet.

**Interfaces:** Produce `validate_memory(snapshot: dict) -> dict`, `MemoryStore(path: Path).graph() -> dict`, `.build(*, arena_url: str, environment: str, source_cases: list[str]) -> dict`, `.get(snapshot_id: str) -> dict`, `.list() -> list[dict]`. Missing snapshots raise ValueError. Graph contains `observations`, `lessons`, `conflicts` and discovery coverage, all plain JSON. Build returns the complete validated immutable snapshot.

Snapshot exact top-level fields: `schema_version` (1), `snapshot_id` (SHA256 of canonical JSON excluding itself), `arena_url`, `environment`, `source_cases`, `source_suppliers`, `source_sessions`, `lessons`, `evidence`. All collections deterministic, unique and bounded. `source_sessions` are arena-local session ID strings. `evidence` holds citations and extracted observations. `lessons` contain `lesson_id`, `field` (contract_months/payment_days), `direction` (higher/lower), `evidence_ids`; matching never uses supplier/case identity. Any additional per-evidence schema is documented in the module and strictly validated. Citation must resolve to an original supplier message in a persisted completed ended owned session; include run/campaign/attempt/supplier/message index and arena/environment/case/session provenance.

- [ ] Write failing tests with stored Run and LoopStore fixtures for: repeated/imported sessions count once; buyer text cannot teach; recovered/incomplete missing-session outcomes excluded; opposite supplier statements retained and suppress lesson; three suppliers/two cases required; full source cohort includes non-supporting suppliers; source-case selection excludes evaluation data; deterministic hashes and tamper rejection; no arbitrary fields or raw instruction lesson.

```python
def test_snapshot_rejects_modified_content(snapshot):
    changed = dict(snapshot, source_cases=["case:other"])
    with pytest.raises(ValueError):
        validate_memory(changed)
```

- [ ] Run `UV_CACHE_DIR=/tmp/harve-y-uv-cache uv run --locked --offline pytest -q tests/test_lab_memory.py` and record the expected missing-feature failures.
- [ ] Implement pure strict bounded validation. Read stored runs and loop records without constructing LoopStore (avoid circular imports). Use a SQLite read transaction for a consistent source view. Persist snapshots in a separate immutable table with a content-ID primary key. Deduplicate using normalized arena/session; prefer original campaign and tracked records over imports. Imports never independently establish owned training provenance. Extract explicit conservative English preference statements and observed offers, separately typed; require actual supplier author identity. Never derive a preference from an offer number alone. Ignore unsupported/malformed messages. Opposing statements abstain even if one has more repetitions. Require three distinct supporting suppliers and two cases per lesson. The graph refreshes on each read and build, so newly uploaded completed runs appear automatically. Build includes only selected scope and every eligible discovery session/supplier, including negative/no-signal cases. Reject absent requested cases and empty discovery scope. Tests use synthetic data only.

```python
payload = {"schema_version": 1, "arena_url": arena, "environment": environment,
           "source_cases": sorted(cases), "source_suppliers": sorted(suppliers),
           "source_sessions": sorted(sessions), "lessons": lessons, "evidence": evidence}
snapshot = {**payload, "snapshot_id": hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
).hexdigest()}
```

- [ ] Run focused tests and ruff, self-review, commit task files and report exact command/output and schema choices.

### Task 2: Negotiator consumption, checkpoint pinning and held-out gates

**Files:** Modify `src/negotiator/agent.py`, `lab/checkpoints.py`, `lab/policy.py`, `lab/loop_store.py`, `lab/worker.py`, `lab/execution.py`, `lab/campaign.py` as needed; create `src/negotiator/memory_policy.py`, `tests/test_memory_policy.py`, `tests/test_lab_memory_promotion.py`; extend existing checkpoint tests.

**Interfaces:** Consume Task 1 `validate_memory`, snapshot schema, `MemoryStore.get`. PackageAgent gains optional `memory=None`; checkpoint resolved config permits an optional validated `memory` object without adding a key to legacy configs. Produce pure runtime helper in memory_policy.py selecting a valid current nonprice package and trace metadata; define the exact helper signature there and call it only at initial package selection. Add promotion gate entries to `evaluate_campaign`; existing result shape is unchanged. Expose memory store via LoopStore operations for Task 3: reads `memory` (graph), `memory-snapshots` (list or key); write `memory-snapshot` body exactly `{arena_url, environment, source_cases}`. Delegate before LoopStore's existing transaction to avoid nested writer locks. Only registered immutable snapshots can be uploaded in memory checkpoint config.

- [ ] Write failing behavioral tests: a general longer-contract lesson learned on three distinct suppliers changes initial package for a fourth unseen supplier when valid and cost-neutral; costlier/invalid/unsupported packages and empty snapshots leave existing behavior unchanged; raw text does not become outbound claims; both runner types accept config; tampered snapshots rejected; no-memory checkpoints preserve their exact shape; restore retains snapshot. Promotion tests cover identity-overlap rejection even when every numeric score gate passes, missing transcript rejection, matching selected supplier but hidden overlap in another thread, discovery case/session overlap, differing code/config, and truly disjoint three-supplier/two-case original outcomes passing. Seed cannot recommend nonempty untested memory. All-memory gates apply when either arm has a nonempty memory and its content changes.

```python
evaluation = evaluate_campaign(suite, baseline, candidate, contaminated_attempts)
assert not evaluation["eligible"]
assert "memory_holdout" in evaluation["evidence_gaps"]
```

- [ ] Run focused tests to capture expected failures.
- [ ] Implement optional memory config validation and content pinning. Preserve legacy checkpoint IDs/config representation. Validate memory schema before agent execution. Worker verifies snapshot arena/environment against campaign request, with preflight carrying those fields; final agent has no lab API or spectator access. Keep scope origin checks in the worker, not supplier identity matching in policy. Runtime enumerates current packages, filters must-haves and buyer cost at the reference price, uses only hints supported by current negotiable options, and abstains on invalid data. Never bypass existing _offer or closing checks. Log snapshot/lesson/evidence IDs when a lesson affects a package. Avoid applying preferences repeatedly to override later supplier events.
- [ ] Extend evaluation with memory comparability and `memory_holdout` gates. For memory-changing experiments compare commit/lock/runner/data/non-memory config exactly. Check both discovery cohorts. All planned attempt transcripts must be present, original, ended and contain known supplier messages; inspect all thread suppliers rather than selected winners alone. Require evaluation cases and sessions disjoint from discovery, same origin/environment, at least two cases and three distinct suppliers, no source-supplier overlap, and exact corresponding supplier cohorts across comparison arms for each case/repeat. Do not weaken existing score gates. Store registration enforces content equality to known snapshots; initial recommendation seeding forbids nonempty memory, while recommendation restore remains authorized only for historical checkpoints.

```python
left = {k: v for k, v in baseline["config"].items() if k != "memory"}
right = {k: v for k, v in candidate["config"].items() if k != "memory"}
comparable = left == right and baseline["commit"] == candidate["commit"]
```

- [ ] Run focused tests plus full Python suite once, ruff, self-review, commit and report.

### Task 3: Agent CLI, dashboard and documented branch trial

**Files:** Modify `lab/loop_cli.py`, `lab/cli.py`, `lab/server.py` only as needed for routes, `lab/static/index.html`, `app.js`, `app.css`; create `lab/static/memory.js`, `tests/test_lab_memory_ui.cjs`, `tests/test_lab_memory_cli.py`; extend server auth tests; update `LAB_PLAYBOOK.md`, `docs/13-agent-experiment-loop.md`, `experiments/LOG.md`.

**Interfaces:** Consume LoopStore reads/writes defined in Task 2 and complete snapshots from Task 1. CLI `lab memory graph`, `lab memory snapshots`, `lab memory show SNAPSHOT_ID`, `lab memory build --arena-url URL --environment sandbox|practice|simulator --source-case CASE` (repeatable). Checkpoint create adds `--memory SNAPSHOT_ID` and retrieves immutable snapshot into its config; refuse ambiguous conflicting config memory. Use existing --format JSON/markdown pattern. Dashboard uses authenticated `/api/loop/memory` and `/api/loop/memory-snapshots` routes and existing read-only session; no browser mutations required.

- [ ] Write failing CLI/server/DOM tests: graph auth required, cookie may read but not build; bearer build; CLI correct request and checkpoint pin; UI separate supplier history/general lessons, diversity and conflict labels, source citation drilldown, insufficient evidence empty state, escaped hostile text, logout and delayed response clearing. Reuse existing test fixture helpers and Node DOM dependencies.
- [ ] Run those tests to record RED.
- [ ] Implement CLI/parser wiring and a Memory navigation view. Render concise lesson cards with support counts, conflicts/abstentions and candidate status; supplier observation cards with source scope and citations; snapshot list with immutable IDs and discovery cohorts. No score claim without evaluation. Link run/campaign evidence where existing UI supports it and otherwise show a precise readable citation. Fetch only while authenticated, clear all data on logout and reject stale completion. No new library.

```javascript
const generation = state.memoryGeneration;
const graph = await api('/api/loop/memory');
if (generation !== state.memoryGeneration || !state.authenticated) return;
```

- [ ] Document usable discovery/holdout workflow: reserve cases/suppliers before training, inspect graph, build candidate, pin baseline without memory and candidate with memory to SAME feature-capable source/config/data, explicitly budget separate held-out evaluation, inspect gates, restore checkpoint for rollback. Explain that D01/D02 cannot support generalization alone, identity-free lessons abstain safely and repeated human holdout tuning remains a limitation. Do not promise new suppliers are statistically covered. Add experiment log with hypothesis, branch, config/action bounds, synthetic cases, quota 0, tests, no measured hosted score gain, decision keep experimental.
- [ ] Run focused checks then full Python suite/ruff and all lab Node tests. Use `ARENA_DATA=/home/brscn/Desktop/harve-y/negotiation-arena-kit/data UV_CACHE_DIR=/tmp/harve-y-uv-cache uv run --locked --offline pytest -q`; use escalation only if sockets require it. Node DOM module is `/tmp/lab-report-validation/node_modules/linkedom` when available. Self-review and commit. Report test evidence and remaining limitations without publishing/deploying.
