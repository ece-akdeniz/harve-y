# Agent experiment loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Coding agents can checkpoint, compare, explain and restore negotiators, with automatic lab recommendation updates.

**Architecture:** Local Git worktrees execute immutable candidates. The existing authenticated HTTP/SQLite lab stores immutable suite definitions, campaign attempts, findings, reservations and an atomic recommendation history. Small modules keep Git, numerical policy, persistence, execution, transport and presentation separate.

**Tech Stack:** Python 3.12, existing Pydantic/httpx/SQLite, Git CLI, vanilla JavaScript. No new runtime dependencies.

**Spec:** docs/superpowers/specs/2026-10-10-agent-experiment-loop-design.md (approved by user).

## Global Constraints

- Four laptops execute locally; the dashboard does not execute submitted code.
- Promotion updates only the lab recommendation, never Git main.
- Checkpoints preserve the working branch/index/files and omit secrets, ignored output and machine configuration.
- Published, restorable checkpoints are required for recommendation; restore uses a new worktree.
- Initial suite: D01/D02 sandbox, serial, three repeats per case per arm, twelve sessions.
- Policy: all planned outcomes valid, candidate must-have compliance, complete timeout evidence with no increase, >=1 point overall gain, no case mean regression >2 points, wins >=two thirds of repetition blocks.
- Atomic generation comparison prevents stale campaigns from promoting. Completion and start IDs are idempotent.
- Practice needs explicit allowance and reserve; no hosted sessions or remote pushes as incidental validation.
- No spectator inputs, credentials in output, new frameworks, or automatic supplier-instruction execution.
- Existing uncommitted lab work is preserved. Work in the current codex/experiment-dashboard branch as requested earlier; no main integration.

### Task 1: Exact shared checkpoints

**Files:** Create src/negotiator/lab/checkpoints.py, tests/test_lab_checkpoints.py.

**Interfaces:**
- `create_checkpoint(project: Path, *, config: dict, agent: str = 'package', runner: str = 'serial', author: str, description: str, parent_id: str | None = None, data: dict | None = None, root: Path | None = None) -> dict`.
- `load_checkpoint(checkpoint_id: str, root: Path) -> dict`; local manifests are atomic JSON.
- `publish_checkpoint(project: Path, checkpoint: dict, *, remote: str = 'origin') -> dict`; immutable ref refs/heads/lab/checkpoints/<id>; return published manifest.
- `restore_checkpoint(project: Path, checkpoint: dict, destination: Path, *, branch: str | None = None, data_paths: dict | None = None) -> Path`; fetch exact ref when absent, verify SHA, submodules/lock/data before execution; restore must not overwrite existing directory.
- `validate_checkpoint(body: dict) -> dict`; strict bounded public schema for server registration; no network on host.
- Manifest fields: schema_version=1, checkpoint_id, commit, project_path (relative to Git root), author, description, parent_id, created_at, agent, config (resolved), runner, lock_sha256, submodules (path->SHA), data (name->{sha256,source} or {} for explicitly unused), harness_version, remote (credential-free URL or null), ref, published (bool).

- [x] Write tests first for binary/untracked/deleted roundtrip, unchanged active index and branch, tracked secret exclusion, dirty submodule rejection, invalid config/remote rejection, hash mismatch, second clone restore, duplicate publication and immutable ref rejection.
```python
def test_roundtrip_preserves_current_checkout(tmp_path):
    # Real temp repository fixture: staged a.py differs from working a.py, binary added, source deleted.
    before = git(repo, 'status', '--porcelain=v1')
    checkpoint = create_checkpoint(repo, config={}, author='test', description='candidate')
    restored = restore_checkpoint(repo, checkpoint, tmp_path / 'restored')
    assert (restored / 'binary.bin').read_bytes() == b'\x00\xff'
    assert not (restored / 'deleted.py').exists()
    assert git(repo, 'status', '--porcelain=v1') == before
```
- [x] Run focused pytest and record expected missing-module failure.
- [x] Implement temporary-index snapshot with safe path selection, secret value rejection (never redaction changing runnable code), commit-tree/update-ref, immutable publishing, isolated restore and data verification. Resolve PackageAgent option defaults and env feature switches into public config; reject unresolved inputs. Reject dirty submodules rather than automatically publishing third-party changes. Reject unsafe links; no inherited hooks on restore/publish commands. Do not publish to real origin in tests.
- [x] Run focused tests and Ruff; self-review; record changed files and RED/GREEN evidence for review. Keep changes uncommitted because the lab baseline is still uncommitted; task diff is captured independently.

### Task 2: Suites, campaigns, reservations and recommendation state

**Files:** Create src/negotiator/lab/loop_models.py, policy.py, loop_store.py, evidence.py; tests/test_lab_loop_store.py, test_lab_policy.py. Modify server.py only for `/api/loop` routes.

**Interfaces:**
- `LoopStore(path: Path)` shares DB with `Store`; use separate loop_* tables and BEGIN IMMEDIATE mutations.
- `LoopStore.read(resource: str, key: str | None = None) -> dict`; resources checkpoints/suites/families/campaigns/recommended/history/findings/evidence/overview.
- `LoopStore.write(operation: str, body: dict) -> dict`; operations checkpoint, suite, family, seed, campaign, attempt-start, attempt-result, complete, restore, finding. All writes require bearer; reads accept existing read cookie.
- `default_suite(arena_url='https://arena.tacto.ai', environment='sandbox') -> dict`; suite_id stable versioned string, cases, repetitions, runner, arena_url/environment, data, max_sessions, policy.
- `evaluate_campaign(suite: dict, baseline: dict, candidate: dict, attempts: list[dict]) -> dict` returns eligible, gates [{id,passed,detail}], cases, repeats, metrics (scores in 0–100), evidence_gaps.
- Campaign captures family_id, suite_id, baseline_id, candidate_id, generation, seed, author and hypothesis. Server creates exact plan of attempt_id/arm/case/repeat; no client policy overrides after reservation.
- Attempt-result carries attempt_id, status, score (0–1), timeouts, result, threads, elapsed_s, session_id, checkpoint_id. Reject changed terminal outcome, duplicate session reuse and attempt mismatch.
- Family has explicit max_sessions and optional practice_allowance/reserve. Reservation budget never implicitly refunds started/ambiguous sessions. Shared hosted start lease serializes key use across laptops and records pacing; finish/reconciliation releases only a known session. Fresh quota required for practice, check remaining net of reservations and protected reserve. No automatic lease expiry refund.

- [x] First tests: valid improving sample promotes once; missing/failing/recovered/unknown timeout or must-have evidence cannot promote; no per-case regression over limit; unequal suite/checkpoint data/runner rejected; stale generation does not replace newer recommendation; restore appends history; two concurrent clients cannot overspend family/practice budget or own hosted start simultaneously; unauthorized HTTP mutations fail.
```python
def test_stale_baseline_cannot_promote(loop, improving_campaigns):
    first, second = improving_campaigns
    assert loop.write('complete', {'campaign_id': first})['status'] == 'promoted'
    assert loop.write('complete', {'campaign_id': second})['status'] == 'baseline_superseded'
    assert len(loop.read('history')['history']) == 2  # explicit seed plus promotion
```
- [x] Run RED tests.
- [x] Implement strict Pydantic definitions, immutable registration, deterministic policy with full samples, atomic recommendation/history/idempotency and budget/lease coordination. Calculate facts from uploaded outcomes, never findings text. Findings validate evidence references down to message indices against recorded attempts; represent observation/hypothesis/change/next_test/confidence/disposition separately. Expose overview metadata without dumping thread bodies.
- [x] Add authenticated transport handlers: GET /api/loop/<resource>[/<id>], POST /api/loop/<operation>. Use bounded existing _body and generic safe errors; no server Git or external arena actions. Exercise real local HTTP auth.
- [x] Run focused tests/Ruff and record RED/GREEN/report for review.

### Task 3: Executable campaigns and coding-agent CLI

**Files:** Create src/negotiator/lab/loop_client.py, campaign.py, loop_cli.py, worker.py; tests/test_lab_campaign.py, test_lab_loop_cli.py. Modify cli.py dispatch, runner.py runtime adapter, tools/compare.py to consume common ordering helper.

**Interfaces:**
- `LoopClient(url, token).read(resource, key=None)` and `.write(operation, body)` implement task 2 interface, no secret error output. Can use LoopStore directly for local tests; remote required for hosted campaigns.
- `campaign_order(cases, repetitions, seed)` shared deterministic interleaving, used by tools/compare.py and lab campaign.
- `run_campaign(client, campaign_id, project, root, *, data_paths=None) -> dict`; restore both checkpoints to campaign subdirectories, verify pinned lock and dependencies before starting, execute each planned attempt through worker subprocess from its checkpoint, durable local results and idempotent uploads. Stop new starts on host failure; preserve/finish active session; never retry uncertain session creation. Fully uploaded campaign calls complete automatically.
- Worker stdin/manifest public config, env secrets only, serial uses negotiator.play.play_case, async uses negotiator.runner.play_case with journal; each result carries durable session identity, closing result and owned threads. No spectator calls. Lab ordinary run default switches to custom serial runtime too.
- CLI dispatch `handle_loop(args)`, registering through `add_loop_commands(subparsers)` in current parser. JSON `{schema_version:1,...}` default; --format markdown for reports; errors `{schema_version:1,error:{code,message}}` plus nonzero exit.
- Commands checkpoint create/publish/show; suite list/show/create (default suite); family create/show; recommended seed/show/history/restore; campaign run/status/compare/sync; evidence show; findings add/list; restore CHECKPOINT --destination PATH. Public JSON config/files accepted. --url/token defaults env (token not argv option), --repo/root/author shared. `campaign run` requires family/candidate and uses current suite recommendation as baseline; explicit --max-sessions family allowance. Checkpoint publication also registers manifest with lab.

- [x] RED tests for CLI structured errors, checkpoint workflow against local fake Git remote, shared command transport, deterministic complete ordering, custom runner invocation, subprocess checkpoint isolation, interrupted upload recovery and no second create after ambiguous failure.
```python
def test_order_contains_each_cell_once():
    cells = campaign_order(['D01', 'D02'], 3, 7)
    assert len(cells) == 12
    assert len({(c['arm'], c['case_id'], c['repeat']) for c in cells}) == 12
```
- [x] Implement adapters using existing custom runtime and owned evidence collection. Clear incidental strategy/data env before running checkpoint config; secret values only via environment. A required data path must match recorded fingerprint. Run locked uv in each project, use checkpoint source not installed mutable project. Async journal stays per attempt. Record runtime/harness versions. Avoid executing optional custom agent during checkpoint validation on host.
- [x] Implement durable campaign state file and sync without replaying negotiation starts. Mark uncertain attempts and retain lease until explicit owned-history reconciliation, expose blocking status and clear next action.
- [x] Run focused tests/Ruff; document command semantics and exit codes in report.

### Task 4: Recommendation dashboard and actionable evidence

**Files:** Modify static/index.html, app.js, app.css; tests/test_lab_ui.cjs. Create docs/13-agent-experiment-loop.md; link docs/README.md and docs/12-experiment-dashboard.md.

**Interfaces:** consume GET /api/loop/overview and detail resources; existing cookie grants reads only. Overview includes recommendations, campaign summaries, families/budgets and latest findings/history.

- [x] RED JS tests for summarizing promotion gates, evidence gaps, per-case score deltas, stale baseline labels and restore command output; verify malicious text stays text.
```js
test('superseded campaign explains required next comparison', () => {
  const view = campaignView({status:'baseline_superseded', evaluation:{gates:[]}});
  assert.match(view.message, /new recommendation/i);
});
```
- [x] Add readable recommendation cards, campaign/family list, expandable gate and repeat tables with score spread, checkpoint/config differences, finding cards and append-only history timeline. Show clear empty state with next CLI command. Keep existing experiment UI. Restore buttons copy CLI command; do not grant write capability to read cookies. Poll safely with existing dialog/scroll rules.
- [x] Write workflow guide from exact CLI help: four-laptop setup, published checkpoint/explicit baseline, bounded comparisons, JSON/Markdown evidence to coding agents, findings, safe local restore and recommendation restore, concurrency/offline recovery and practice policy. Distinguish sandbox improvement from generalization; no claim hosted policy validated.
- [x] Run JS tests, node syntax check and DOM smoke render; report missing visual verification if browser unavailable.

### Task 5: Full local rehearsal and final review

**Files:** Tests may add tests/test_lab_loop_integration.py; update experiments/LOG.md, approved spec status and this checklist.

- [x] Run a local simulator end-to-end comparison using temporary Git remote/SQLite, two checkpoint worktrees, case repeats and real CLI; no hosted quota. If simulator data unavailable, use kit fixtures for a deterministic local HTTP arena with real worker runners and stateful sessions; explicitly label fidelity in log.
- [x] Verify restore on a second clone, policy rejection/promotion, same-generation race and recommendation rollback roundtrip. Run uv locked pytest and Ruff, Node tests, git diff --check. Record environment-only restrictions separately.
- [x] Obtain independent whole-change review with spec and quality verdicts, resolve important findings and recheck affected tests.
- [x] Restart existing lab host to load API changes, verify authenticated overview without printing secrets. Keep live data/old runs untouched. Summarize implemented flow, verification, remaining external prerequisites. No real checkpoint publication or hosted campaign automatically launched.
