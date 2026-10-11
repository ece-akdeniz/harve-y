# codex/safety-wave-prewarm — Live Final safety keys on top of codex/consolidated

Sim-only lane (2026-10-11, 03:50–04:30). Zero hosted/practice sessions; nothing talked to the arena API.
Base: `codex/consolidated` @ `7dba7c0`. Worktree `/Users/sametdegirmenci/Downloads/ysamet-safety`.

## 1. What merged

| commit | from | content |
|---|---|---|
| `d953317` | `codex/fresh-wave` @ `0a6940e` (merged up to this commit only; **not** `485b60f`) | wave time guard (agent stops extending with < 2 rounds of wall clock left), `wave_time_left` / `round_time` / `thread_time` timing trace, `budget.bounded` hard wall-clock ceiling on every model call (model_assist ≤ 3 s, inference probe ≤ 8 s), `tools/wave_rehearsal.py` (parallel 10-case wave against the kit sim), `tests/test_budget.py`, `tests/test_wave_time_guard.py` |
| `97224ef` | `codex/fresh-prewarm` @ `149afea` (builds on `0a6940e`) | `negotiator.prewarm`: package, dossiers, facts, package-tree scan and per-case evidence/estimates/traits loaded before the wave poll / before each session opens; `PolicyConfig.prewarm = True`; RLock around the shared sqlite connection; `tools/prewarm_replay.py`; `tests/test_prewarm.py` (14) |
| `0674413` | this lane | `play.play_case` (serial path of the auto runner = one-supplier final cases) now feeds `agent.time_left_fn` / `round_estimate_fn` from the same wave cap and its own slowest-round measurement. Before this only the async `CaseRunner` wired the guard, so single-supplier final cases had the watchdog cap close but no agent-side 2-round guard. + 1 test |

Fast-payment duplication check: `485b60f` (fresh-wave's `rfq_fast_payment_reanchor` port) was **not** merged;
consolidated already carries it via `e0bd7a8`/`e8b0396`. After the merge `_rfq_fast_payment` is defined once
(`agent.py`), called once, `rfq_fast_payment_reanchor` appears once in `PolicyConfig`.

### Conflicts and resolution

- `agent.py` `_reciprocal_price`: HEAD had the extended docstring (never-resend-identical-sheet note),
  0a6940e added `or self._guarded()` to the early return. Kept both (docstring + guard gate).
- `runner.py` `CaseRunner._worker`: HEAD wrapped `propose` in `try/except → fallback_propose` (Final
  robustness, `propose_fallback` trace); 0a6940e added the `wave_time_left` trace and `decide_s` timing
  around the same call. Kept the try/except and put the timing/trace around it.
- `policy.py` `PolicyConfig`: HEAD had `rfq_fast_payment_reanchor`, `alt_clause_counter`,
  `cost_breakdown_request`; 149afea added `prewarm`. Kept all four fields and appended `prewarm` to the
  boolean validation list.
- `claim_pacing` / `rfq_fast_payment_reanchor` behaviour from consolidated untouched (replay below).

### Files touched vs 7dba7c0

`src/negotiator/`: agent.py (wave guard only), budget.py (new), context.py, dossiers.py, inference.py,
ingestion.py, model_assist.py, play.py, policy.py (+`prewarm` field), prewarm.py (new), runner.py, state.py.
`tests/`: test_budget.py, test_prewarm.py, test_wave_time_guard.py (new), test_runner.py.
`tools/`: wave_rehearsal.py, prewarm_replay.py (new). No change to fixed_volume.py, cli.py, configs/.

agent.py / policy.py diff vs 7dba7c0 is exactly the 0a6940e + 149afea hunks (no new edits from this lane);
the v5 lane (codex/v5-breakthrough) touches agent.py/policy.py/fixed_volume.py — expect small textual
conflicts in `PolicyConfig` fields/validation list and in `_counter`/`_cost_target_move` where the guard
inserts its early returns.

## 2. Always-on

- **Wave time guard**: `agent.TIME_GUARD_ROUNDS = 2`, `ROUND_ESTIMATE_S = 120` are module constants, no
  policy key. `_guarded()` ⇔ `time_left < 2 × max(120 s, slowest measured round)` ⇔
  `floor(time_left / round_time) < 2`. Active whenever a wave cap is known: `--set final` → `run_waves`
  sets `deadline` from `seconds_left` → `CaseRunner._wire_agent_clock()` (multi-supplier) or
  `play.play_case` (one-supplier, serial path). Practice/sandbox pass no cap → `time_left_fn()` is None →
  guard inert, decisions unchanged. Under the guard: accept an acceptable standing sheet (through
  `close_decision`), else match the supplier's ask on our terms, else close via the evaluator (walk or
  accept). Never a schedule/reciprocal/probe/value-swap step; a counter to a final offer is never sent.
- **Prewarm**: `PolicyConfig.prewarm` defaults to **True**; `score-push-v4.json` / `v3.json` do not set it.
  `run_waves` / `play_waves` prewarm once before the first `/v1/cases?set=final` poll; `play_case`
  (async and serial) prewarms the case before `open_session`. Degrades to a log line on any failure.
- **Decision fallback** (already in consolidated, kept): `propose` exception → `fallback_propose`
  (best eligible sheet / repeat last offer / walk-away) in the async worker; `guarded_decision` on the
  serial path. Under the guard `_time_guard_move` uses `best_close` → no path raises on a stale thread.
- **Model-call ceiling**: `budget.bounded` caps model_assist at ≤ 3 s and the inference probe at ≤ 8 s of
  wall clock regardless of httpx per-phase timeouts; fallback is the rules path / deterministic move.

## 3. Verification (all offline)

- `uv run --locked ruff check .` clean.
- `uv run --locked pytest -q`: **827 passed** (810 after the wave merge, 824 after prewarm, 827 with the
  serial-guard test; the 2 ARENA_DATA skips run when `ARENA_DATA` is exported).
- **Saved-transcript replay vs 7dba7c0** (`tools/replay_decisions.py`, config A = B =
  `configs/score-push-v4.json`, runs dir `ysamet/tacto-negotiator/experiments/runs`, all hosted practice
  cases P01–P19, run on a detached `7dba7c0` worktree and on this branch, then the per-round `rounds_a`
  JSON compared): **305 replays, 1611 decision rounds, 0 differing** (supplier choice, term sheets,
  action, refs, body byte-identical). Per case: P01 24, P02 39, P03 11, P04 16, P05 56, P07 32, P08 29,
  P10 36, P11 25, P18 37. JSON: `/tmp/replay-base-v4.json`, `/tmp/replay-safety-v4.json`.
- **Prewarm vs lazy** (`tools/prewarm_replay.py`, separate processes, P01/P05/P08/P18 × 3 runs, v4):
  12 transcripts, 74 decisions, sha256 identical.
- **Wave rehearsal, fast** (`tools/wave_rehearsal.py --config configs/score-push-v4-run.json --delay 0
  --prewarm both`): 10 hosted practice cases in parallel, all end normally (P11 walks as in v3/v4),
  first decision per case **≤ 0.66 s with prewarm** (per-case prewarm 0.39–0.51 s, package prewarm
  0.18 s), 0.5–1.3 s lazy; slowest decision 1.32 s; no cap closes.
- **Wave rehearsal, real clock, 50 s supplier delay** (`--delay 50 --guard both --prewarm on`, one real
  8-minute wave, 10 cases × guard on/off concurrently): see §4.

## 4. Rehearsal timing (real clock, --delay 50)

`tools/wave_rehearsal.py --config configs/score-push-v4-run.json --delay 50 --guard both --prewarm on`
(kit sim, 10 hosted practice cases in parallel per variant, real wall clock, 480 s cap; JSON `/tmp/wave-50.json`):

- **First decision latency (after prewarm): 0.02–0.5 s per case** (slowest 0.5 s), per-case prewarm
  0.37–0.52 s, package prewarm 0.16 s; slowest decision overall 0.5 s. Target "< 5 s" met with margin.
- **Rounds inside 8 min**: one-supplier cases 5 rounds in ~251 s (3 rounds / 151 s for P02, 4 / 201 s for
  P11), slowest round 50.1–50.6 s. P05 (three suppliers, one send slot per session) slowest round 85 s.
- **Worst case with the guard on: 270.7 s (P05)**; without it 370.8 s (P05) — both inside the cap, no
  watchdog `wave cap` close in either variant, 0 timeouts.
- **Guard fired once**, P05 round 4 with 228.6 s left (< 2 × max(120, 85) = 240 s): accepted the standing
  `offer:70210-3` → sim score **0.695**, where the unguarded run reached round 5 and 0.829 at t = 370.8 s
  (109 s before the cap; the watchdog margin there is max(90, 85 + 15) = 100 s, i.e. ~9 s to spare).
  Every other case: identical scores guard on/off (P01 .734, P02 .429, P03 .869, P04 .864, P07 .862,
  P08 .805, P10 .946, P11 walk, P18 .819).
- Fast variant (`--delay 0`, `--prewarm both`): same scores as guard-off above; first decision ≤ 0.66 s
  prewarmed vs 0.5–1.3 s lazy (lazy here already had the package cached in-process).

Trade-off for the coordinator: `ROUND_ESTIMATE_S = 120` is the brief's worst case (60 s ours + 60 s
theirs). In this sim (50 s replies) it costs P05 one round (-0.134); with hosted replies at 60 s the
unguarded P05 would have ended ~420 s in, inside the 480 s cap but past the watchdog margin (380 s), so the
guard would have been needed there anyway. Lowering the constant (e.g. 90 s) would buy P05 the fifth
round at 50 s replies at the price of less margin for a late or lost reply; not changed in this lane.

## 5. FINAL_POLICY (not repointed — coordinator decides v4 vs v5)

`src/negotiator/cli.py` line 23:

```python
FINAL_POLICY = Path(__file__).resolve().parents[2] / "configs" / "score-push-v3.json"
```

applied at line 79–80 (`if final and not args.policy_config: args.policy_config = str(FINAL_POLICY)`),
help text line 54 says "(final default: v3)". To repoint: change `"score-push-v3.json"` to
`"score-push-v4.json"` (or the v5 file) on line 23 and the help string on line 54 / comment on line 80;
or leave it and launch with `negotiator run --set final --policy-config configs/score-push-v4.json`.

## 6. Open points

- Not pushed/merged into `codex/consolidated` by this lane (coordinator merges after the v5 lane lands).
- `tools/wave_rehearsal.py` module docstring still quotes the pre-prewarm 11–27 s first-decision figure in
  its "Measured" paragraph; the 149afea commit message has the post-prewarm numbers (≤ 0.8 s).
