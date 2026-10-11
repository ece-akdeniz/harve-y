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

## 5. FINAL_POLICY — repointed to v6 on `codex/release-v5`

`src/negotiator/cli.py` line 25 now reads `FINAL_POLICY = … / "configs" / "score-push-v6.json"` (v5 first, then v6 =
v5 + `cost_target_posterior` 0.10 after the 427674f merge; the guard/prewarm behaviour is identical); help text
(line 56) says "(final default: v6)", comment at the application site (line 82) likewise.
`negotiator run --set final` without `--policy-config` plays v6 (`tests/test_final_robust.py::
test_final_cli_defaults_to_auto_runner_and_v6_policy` pins the path, `policy.prewarm is True`,
`fixed_volume_types == ("raw_material",)`, `cost_target_posterior == 0.1`, `tenor_extend_types == ()`). See `experiments/RELEASE-v5.md`.

## 5a. ROUND_ESTIMATE_S calibration (codex/release-v5, 2026-10-11 04:47–05:17 CEST)

Question: keep `ROUND_ESTIMATE_S = 120` or lower it to 90? Rule agreed with the coordinator: pick 90 only if at
**all** of 50 s / 60 s / 90 s supplier reply delays there are 0 timeouts / watchdog or cap closes **and** no case
scores lower than at 120; otherwise keep 120.

Setup: `tools/wave_rehearsal.py --config configs/score-push-v5-run.json --delay {50,60,90} --guard {on,off}
--round-estimate {120,90} --prewarm on` — kit sim, the 10 hosted practice cases in parallel per wave, real wall
clock, 480 s cap, `TIME_GUARD_ROUNDS = 2`. New `--round-estimate` flag overrides the agent constant for the
run (default: the constant). Waves for the three delays ran as concurrent processes (30 cases at once; first
decision per case still ≤ 0.53 s, slowest decision ≤ 1 s). The 60 s / 90 s waves were repeated after fixing
the rehearsal's `SimArena.send` so the sim's 60-second rule is parked at the reply time *before* the
injected sleep (with delay > 60 s a poll during the sleep could otherwise count a timeout against us); the
repeat reproduced the first run case for case (only P05's guarded score moved, .226 → .376, timing jitter).
"UNRESOLVED" = the runner's `IncompleteSession("close unresolved")`: the only open thread still had a reply
in flight when the cap-margin close ran, so nothing could be closed — hosted that is a `wave_cap` no-deal
(alternative's score). It is counted as a watchdog/cap event. JSON: `/tmp/calib-release/*.json`.

Per case (score unguarded / guard with RE=120 / guard with RE=90; wall seconds = thread total):

| delay | case | type | score unguarded | score RE=120 | score RE=90 | wall s off / 120 / 90 | end off / 120 / 90 | guard action 120 / 90 | sim timeouts off/120/90 |
|---|---|---|---|---|---|---|---|---|---|
| 50 | P01 | price_increase | 0.7339 | 0.7339 | 0.7339 | 250.9 / 250.9 / 250.8 | accepted / accepted / accepted | no / no | 0/0/0 |
| 50 | P02 | price_increase | 0.4290 | 0.4290 | 0.4290 | 150.7 / 150.8 / 150.8 | accepted / accepted / accepted | no / no | 0/0/0 |
| 50 | P03 | renewal | 0.8694 | 0.8694 | 0.8694 | 250.9 / 250.4 / 251.0 | accepted / accepted / accepted | no / no | 0/0/0 |
| 50 | P04 | renewal | 0.8644 | 0.8644 | 0.8644 | 250.9 / 250.9 / 250.6 | accepted / accepted / accepted | no / no | 0/0/0 |
| 50 | P05 | rfq | 0.8291 | 0.6953 | 0.5541 | 370.3 / 270.4 / 320.5 | accepted / accepted / accepted | accept / accept | 0/0/0 |
| 50 | P07 | bundling | 0.8618 | 0.8618 | 0.8618 | 250.9 / 251.0 / 251.0 | accepted / accepted / accepted | no / no | 0/0/0 |
| 50 | P08 | raw_material | 1.0000 | 0.4948 | 1.0000 | 300.9 / 250.3 / 300.2 | accepted / accepted / accepted | accept / no | 0/0/0 |
| 50 | P10 | capacity | 0.9462 | 0.9462 | 0.9462 | 250.2 / 250.3 / 251.0 | accepted / accepted / accepted | no / no | 0/0/0 |
| 50 | P11 | quality | 0.0000 | 0.0000 | 0.0000 | 200.9 / 200.9 / 200.9 | walked_away / walked_away / walked_away | no / no | 0/0/0 |
| 50 | P18 | raw_material | 1.0000 | 0.4911 | 1.0000 | 300.2 / 250.5 / 300.5 | accepted / accepted / accepted | accept / no | 0/0/0 |

| delay | guard | mean score (None=0) | unresolved/cap | worst wall s (case) | margin to 480 s cap | slowest round s | watchdog margin s = max(90, slowest+15) | cases scoring below RE=120 |
|---|---|---|---|---|---|---|---|---|
| 50 | off | 0.7534 | 0  | 370.3 (P05) | 110 | 85.0 | 100 | — |
| 50 | 120 | 0.6386 | 0  | 270.4 (P05) | 210 | 85.0 | 100 | — |
| 50 | 90 | 0.7259 | 0  | 320.5 (P05) | 160 | 85.0 | 100 | P05 |

| delay | case | type | score unguarded | score RE=120 | score RE=90 | wall s off / 120 / 90 | end off / 120 / 90 | guard action 120 / 90 | sim timeouts off/120/90 |
|---|---|---|---|---|---|---|---|---|---|
| 60 | P01 | price_increase | 0.7339 | 0.6944 | 0.7339 | 300.8 / 240.8 / 300.8 | accepted / accepted / accepted | accept / no | 0/0/0 |
| 60 | P02 | price_increase | 0.4290 | 0.4290 | 0.4290 | 180.7 / 180.8 / 180.7 | accepted / accepted / accepted | no / no | 0/0/0 |
| 60 | P03 | renewal | 0.8694 | 0.2125 | 0.8694 | 300.7 / 240.5 / 300.4 | accepted / accepted / accepted | accept / no | 0/0/0 |
| 60 | P04 | renewal | 0.8644 | 0.3447 | 0.8644 | 300.3 / 240.8 / 300.3 | accepted / accepted / accepted | accept / no | 0/0/0 |
| 60 | P05 | rfq | – | 0.3759 | 0.6953 | 0 / 260.3 / 320.4 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |
| 60 | P07 | bundling | 0.8618 | 0.8618 | 0.8618 | 300.4 / 300.4 / 300.9 | accepted / accepted / accepted | match / no | 0/0/0 |
| 60 | P08 | raw_material | 1.0000 | 0.3959 | 0.4948 | 360.3 / 240.2 / 300.3 | accepted / accepted / accepted | accept / accept | 0/0/0 |
| 60 | P10 | capacity | 0.9462 | 0.9462 | 0.9462 | 300.3 / 300.3 / 300.3 | accepted / accepted / accepted | match / no | 0/0/0 |
| 60 | P11 | quality | 0.0000 | 0.7968 | 0.0000 | 240.2 / 300.6 / 240.5 | walked_away / accepted / walked_away | match / no | 0/0/0 |
| 60 | P18 | raw_material | 1.0000 | 0.3990 | 0.4911 | 360.2 / 240.4 / 300.2 | accepted / accepted / accepted | accept / accept | 0/0/0 |
| 90 | P01 | price_increase | – | 0.5208 | 0.6944 | 0 / 270.6 / 360.8 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |
| 90 | P02 | price_increase | 0.4290 | 0.4290 | 0.4290 | 271.0 / 270.9 / 270.8 | accepted / accepted / accepted | no / no | 0/0/0 |
| 90 | P03 | renewal | – | 0.1594 | 0.2125 | 0 / 270.9 / 360.4 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |
| 90 | P04 | renewal | – | 0.2585 | 0.3447 | 0 / 271.0 / 360.2 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |
| 90 | P05 | rfq | – | 0.1977 | 0.1977 | 0 / 270.0 / 270.0 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |
| 90 | P07 | bundling | – | 0.8465 | – | 0 / 270.2 / 0 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / walked_away / UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) | close / match | ?/0/? |
| 90 | P08 | raw_material | – | 0.2969 | 0.3959 | 0 / 270.9 / 360.3 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |
| 90 | P10 | capacity | – | 0.8915 | – | 0 / 361.0 / 0 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) | match / match | ?/0/? |
| 90 | P11 | quality | 0.0000 | 0.5976 | – | 360.4 / 360.3 / 0 | walked_away / accepted / UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) | match / match | 0/0/? |
| 90 | P18 | raw_material | – | 0.2992 | 0.3990 | 0 / 270.9 / 360.4 | UNRESOLVED (close blocked by in-flight reply; hosted = wave_cap no-deal) / accepted / accepted | accept / accept | ?/0/0 |

| delay | guard | mean score (None=0) | unresolved/cap | worst wall s (case) | margin to 480 s cap | slowest round s | watchdog margin s = max(90, slowest+15) | cases scoring below RE=120 |
|---|---|---|---|---|---|---|---|---|
| 60 | off | 0.6705 | 1 ['P05'] | 360.3 (P08) | 120 | 60.5 | 90 | P05,P11 |
| 60 | 120 | 0.5456 | 0  | 300.6 (P11) | 179 | 95.0 | 110 | — |
| 60 | 90 | 0.6386 | 0  | 320.4 (P05) | 160 | 95.0 | 110 | P11 |
| 90 | off | 0.0429 | 8 ['P01', 'P03', 'P04', 'P05', 'P07', 'P08', 'P10', 'P18'] | 360.4 (P11) | 120 | 90.5 | 106 | P01,P03,P04,P05,P07,P08,P10,P11,P18 |
| 90 | 120 | 0.4497 | 0  | 361.0 (P10) | 119 | 125.0 | 140 | — |
| 90 | 90 | 0.2673 | 3 ['P07', 'P10', 'P11'] | 360.8 (P01) | 119 | 125.0 | 140 | P07,P10,P11 |

Decision: **keep `ROUND_ESTIMATE_S = 120`** (no code change).

- 90 fails the rule at **90 s replies**: P07, P10 and P11 end UNRESOLVED (the guard fires one round later than
  with 120 — at t≈361 s with ~119 s left the agent still sends a "match" offer whose reply would land at
  ~451 s, inside the watchdog margin max(90, 125+15) = 140 s) → hosted these are `wave_cap` no-deals; with 120
  the same three cases close at 270–361 s (P07 .8465, P10 .8915, P11 .5976). 90 also scores lower than 120
  on P05 at 50 s (.554 vs .695) and P11 at 60 s (walk vs .797).
- 120: **0 unresolved / 0 cap closes at every delay**, worst wall 361 s (P10 at 90 s replies) = 119 s before
  the cap; 300.9 s / 270.4 s worst at 60 s / 50 s. Unguarded: 1 unresolved at 60 s (P05, three suppliers),
  8 of 10 at 90 s.
- Cost of 120 in this sim (suppliers that never close early): at 50 s replies the guard accepts the standing
  sheet on P05/P08/P18 one or more rounds early (P08/P18 sim 1.0 → .49 — the 10-step raw_material ladder is
  still climbing at round 5); at 60 s also P01/P03/P04 (.73/.87/.86 → .69/.21/.34). Hosted v5 practice runs
  closed P08/P18 in 5 rounds and 84–87 s (supplier replies ≈ 15 s), where the guard never fires; the brief's
  worst case (60 s theirs + 60 s ours) is exactly where 120 keeps every case inside the cap.
- 90 would only pay off if Live Final replies sit at 50–60 s *and* the arena never slows beyond that; a single
  90 s reply then turns three single-supplier cases into no-deals. Not worth it.

## 6. Open points

- ~~Not pushed/merged~~ — merged with `codex/v5-breakthrough` 9c1ee52 on `codex/release-v5` (`experiments/RELEASE-v5.md`).
- `tools/wave_rehearsal.py` module docstring still quotes the pre-prewarm 11–27 s first-decision figure in
  its "Measured" paragraph; the 149afea commit message has the post-prewarm numbers (≤ 0.8 s).
