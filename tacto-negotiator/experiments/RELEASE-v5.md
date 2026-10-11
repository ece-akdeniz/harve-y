# codex/release-v5 — Live Final release (safety-wave-prewarm + v5 fixed-volume ladder + v6 posterior 0.10)

> **Current state: section 8 (v6).** `FINAL_POLICY` = `configs/score-push-v6.json`. Sections 1–7 are the v5
> release as shipped at 2e4e3ef; the v6 follow-up supersedes their commands.

Worktree `/Users/sametdegirmenci/Downloads/ysamet-release`, branch `codex/release-v5`. Built 2026-10-11
04:25–05:30 CEST (v5) and 05:30–06:05 CEST (v6), sim-only (no hosted or practice session was opened; no
`negotiator lab run`). `main` is fast-forwarded to this branch (sections 7 and 8).

## 1. What this release is

| commit | content |
|---|---|
| `09e7fe4` | `origin/main` before this release (Live Final robustness fixes) |
| `7dba7c0` | `codex/consolidated`: main + `configs/score-push-v4.json` (`claim_pacing`, `rfq_fast_payment_reanchor`) |
| `f31b4dd` | `codex/safety-wave-prewarm` (on 7dba7c0): wave time guard (`TIME_GUARD_ROUNDS = 2`, `ROUND_ESTIMATE_S = 120`, always on when a wave cap is known), prewarm (`PolicyConfig.prewarm = True`), serial-path guard wiring, `tools/wave_rehearsal.py`, `experiments/SAFETY.md` |
| `9c1ee52` | `codex/v5-breakthrough` (on 7dba7c0): `fixed_volume` module, `fixed_volume_types` / `anchor_by_type` / `rounds_by_type`, `configs/score-push-v5.json` (+ `-run.json`), live-confirmed P08 .7036 / P18 .5870, `experiments/V5.md` |
| `16c13c7` | **merge** of 9c1ee52 into f31b4dd (this branch) |
| `77b42a4` | `FINAL_POLICY` → `configs/score-push-v5.json`; help text / comment; test pins v5 + prewarm; runbooks and `CONSOLIDATED.md` §5 ten-case command on v5 |
| `1f79b44` | guard calibration (`ROUND_ESTIMATE_S` stays 120), `wave_rehearsal.py --round-estimate`, sim 60-s-rule fix in the rehearsal arena, `SAFETY.md` §5/§5a, guard tests at clock scale 0.01 |

Policy that the Live Final plays: `configs/score-push-v5.json` = v4 + `"fixed_volume_types": ["raw_material"]`,
`"anchor_by_type": {"raw_material": 0.19}`, `"rounds_by_type": {"raw_material": 10}`. `prewarm` is not set
in the file and defaults to **True**; the time guard has no policy key (always on under a cap).

## 2. Merge and conflicts

`git merge --no-ff 9c1ee52` onto f31b4dd: **no textual conflicts** — the expected ones did not materialise
because the two branches touched disjoint regions:

- `PolicyConfig` field list: the safety branch added `prewarm` (end of the class), v5 added
  `fixed_volume_types` next to `bundle_commitment_types` and extended the list validator tuple. Both kept.
- `agent.py` guard early-returns vs the v5 ladder: the guard's early returns sit **before** the ladder code
  in `decide_thread` (`guarded = self._guarded()` → `_time_guard_move` at the price-schedule entry, before
  `floor`/`ladder` are computed) and in `_counter` / the finals branch of `_propose`; v5's ladder block only
  replaces the `price = …` schedule line and `_fixed_volume` only decorates an *offer* message (it returns
  the move untouched when `message.action` is set, i.e. on accept/walk). So when `_guarded()` is true a
  `raw_material` thread closes (accept) or matches the ask on our terms instead of stepping the ladder —
  verified in the rehearsal: every P08/P18 guard event is `accept` (SAFETY.md §5a).
- `_enrich_evidence` returns early for `fixed_volume_types` (ladder owns claims) — independent of the guard.

Tests after the merge: 835 passed, 2 skipped (837 with `ARENA_DATA`), ruff clean.

## 3. FINAL_POLICY and runbooks

- `src/negotiator/cli.py:24` `FINAL_POLICY = … / "configs" / "score-push-v5.json"`; `:55` help "(final
  default: v5)"; `:81` comment. `tests/test_final_robust.py::test_final_cli_defaults_to_auto_runner_and_v5_policy`
  asserts the resolved path, `policy.prewarm is True`, `fixed_volume_types == ("raw_material",)`.
- `docs/06-final-runbook.md`, `LAB_PLAYBOOK.md`: final command spells out `--policy-config configs/score-push-v5.json`.
- `experiments/CONSOLIDATED.md` §5: ten-case command on v5 (v4 form kept as history); §7 blockers struck.
- `experiments/V5.md` open items struck; `experiments/SAFETY.md` §5 rewritten, §5a added, §6 updated.
- No `--dry-run` exists. Offline check (stubbed `run_async` / `ArenaClient`, no network):
  `negotiator run --set final` resolves `runner=auto`, `policy_config=…/configs/score-push-v5.json`,
  agent `policy.prewarm=True`, `time_guard_rounds=2`, `ROUND_ESTIMATE_S=120.0`; the trace's `run` row records
  the same. `runner.run_waves` calls `prewarm_async` before the first poll and `play_case` /
  `prewarm_case_async` per case (unchanged from f31b4dd).

## 4. Guard calibration — `ROUND_ESTIMATE_S` stays 120

Full table in `experiments/SAFETY.md` §5a (per case score guarded/unguarded, wall time, end reason, guard
action, for 50/60/90 s replies × RE 120/90). Summary (kit sim, 10 hosted practice cases in parallel, real
clock, 480 s cap; "unresolved" = runner `IncompleteSession`, the only open thread had a reply in flight at
the cap-margin close → hosted `wave_cap` no-deal):

| delay | guard | mean score | unresolved / cap closes | worst wall s | margin to 480 s | cases below RE=120 |
|---|---|---|---|---|---|---|
| 50 | off | .7534 | 0 | 370 (P05) | 110 | — |
| 50 | **RE=120** | .6386 | **0** | 270 (P05) | 210 | — |
| 50 | RE=90 | .7259 | 0 | 320 (P05) | 160 | P05 (.554 < .695) |
| 60 | off | .6705 | 1 (P05) | 360 | 120 | P05, P11 |
| 60 | **RE=120** | .5456 | **0** | 301 (P11) | 179 | — |
| 60 | RE=90 | .6386 | 0 | 320 (P05) | 160 | P11 (walk < .797) |
| 90 | off | .0429 | 8 | 360 | 120 | 9 cases |
| 90 | **RE=120** | .4497 | **0** | 361 (P10) | 119 | — |
| 90 | RE=90 | .2673 | **3 (P07, P10, P11)** | 361 (P01) | 119 | P07, P10, P11 |

Decision rule (90 only if 0 timeouts/cap closes at all three delays and no case below 120): **90 fails at
90 s replies** (three single-supplier cases unresolved: the guard fires one round later, the last "match"
offer's reply lands inside the watchdog margin) and scores below 120 on P05@50 and P11@60 → **120 kept**,
no code change. Watchdog margin = max(90, slowest round + 15) = 100 / 110 / 140 s at 50 / 60 / 90 s replies;
with RE=120 the worst guarded case ends ≥ 119 s before the cap at every delay.

Known cost (sim only): with suppliers that never close early, the guard at 50–60 s replies accepts the
standing sheet 1–2 rounds early on P05/P08/P18 (and P01/P03/P04 at 60 s). The hosted v5 practice sessions
closed P08/P18 in 5 rounds / 84–87 s (≈ 15 s replies), far from the guard.

## 5. Verification

- `uv run --locked pytest -q`: **835 passed, 2 skipped** (837 passed with `ARENA_DATA` exported).
  `tests/test_wave_time_guard.py` was flaky on f31b4dd too (2 of 5 runs; clock scale 0.004 turns a 0.3 s
  decision into 75 simulated s and the watchdog races the in-flight reply) — now scale 0.01, 9/9 green incl.
  3 concurrent runs; +8 s suite time.
- `uv run --locked ruff check .`: clean.
- `tools/replay_decisions.py`, all 10 hosted practice cases, every saved `run.json` under
  `ysamet/tacto-negotiator/experiments/runs`, `--conditional-exchange off`, config A = B, JSON compared
  byte-for-byte across worktrees (`cmp`):
  - **v5 on release (16c13c7 and 1f79b44) vs v5 on 9c1ee52: identical** — 305 replays, 1611 rounds,
    sha256 `03cd9b2f…6145` both. `/tmp/replay-v5-base.json`, `/tmp/replay-v5-release.json`,
    `/tmp/replay-v5-release-head.json`.
  - **v4 on release vs v4 on 7dba7c0: identical** — 305 replays, 1611 rounds, sha256 `db2e3e08…8ed7` both.
    `/tmp/replay-v4-base.json`, `/tmp/replay-v4-release.json`.
  - Per case: P01 24, P02 39, P03 11, P04 16, P05 56, P07 32, P08 29, P10 36, P11 25, P18 37.
- Final-launch resolution (offline, section 3): v5 + prewarm + guard.

## 6. Commands

Live Final (from `tacto-negotiator/` of the checkout that is at `main` = this branch; `--set final` already
defaults to `--runner auto` and v5, flags spelled out so trace and command agree):

```bash
cd /Users/sametdegirmenci/Downloads/ysamet-release/tacto-negotiator   # or any checkout at main (1f79b44)
export ARENA_DATA=/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/data/package
mkdir -p experiments/runs
NEGOTIATOR_JOURNAL="$PWD/experiments/runs/final-journal.jsonl" \
caffeinate -dimsu uv run --locked negotiator run --set final --runner auto \
  --policy-config configs/score-push-v5.json --parallel 10 > experiments/runs/final.log 2>&1
```

Ten-case practice confirmation of v5 (tracked `lab run`, clean tree, one repetition, 10 sessions; **not run**
by this worker):

```bash
cd /Users/sametdegirmenci/Downloads/ysamet-release/tacto-negotiator
export ARENA_DATA=/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/data/package
mkdir -p experiments/runs
caffeinate -dimsu uv run --locked negotiator lab run \
  --name score-push-v5-confirm \
  --hypothesis "codex/release-v5 + score-push-v5 (v4 + raw_material fixed-volume ladder, wave guard, prewarm): ten-case practice mean >= .7726 projected, P08 .7036, P18 .5870, others = v4" \
  --author samet \
  --agent negotiator.agent:configured_agent --runner auto \
  --config "$(cat configs/score-push-v5-run.json)" \
  --cases case:P01 case:P02 case:P03 case:P04 case:P05 case:P07 case:P08 case:P10 case:P11 case:P18 \
  --repetitions 1 --max-sessions 10 --environment practice \
  2>&1 | tee experiments/runs/score-push-v5-confirm.log
```

Expected: P01/P02/P03/P04/P07/P10/P11 = v4 values, P05 .8136, P08 .7036, P18 .5870 (projected mean .7726).

## 7. Refs

- `origin/main` 09e7fe4 → fast-forwarded to `codex/release-v5` (`git merge-base --is-ancestor origin/main HEAD`
  confirmed before `git push origin codex/release-v5:main`); `codex/release-v5` pushed.
- Local `main` ref: see `ysamet-coord/ACKS-release.md` for whether `git branch -f main` was applied (only if
  no worktree had `main` checked out).
- Untouched: `/Users/sametdegirmenci/Downloads/ysamet-v5` (other worker still committing past 9c1ee52 —
  anything after 9c1ee52 is **not** in this release), `ysamet-safety`, `ysamet-pure-main`.
- Temporary detached worktrees `/tmp/ysamet-rel-v5base` (9c1ee52) and `/tmp/ysamet-rel-v4base` (7dba7c0)
  were used for the cross-tree replay and removed afterwards.

## 8. v6 follow-up — merge of `codex/v5-breakthrough` @ 427674f (2026-10-11 05:30–06:05 CEST)

The P02/P10 lane finished after the v5 release. Delta 9c1ee52 → 427674f: `configs/score-push-v6.json` /
`-run.json` (= v5 + `"cost_target_posterior": 0.10`; live P02 .7351 vs .7115), opt-in `tenor_extend_types` +
`PackageAgent._extend_tenor` (OFF in v6; only `configs/p10-tenor-extend.json`), explorer tooling fixes
(`tools/explore_run.py`, `tools/list_attempts.py`, `Explorer.acceptable()`), strategies/traces, `V5.md` lanes 2–3.

| commit | content |
|---|---|
| `28fd4cf` | **merge** of 427674f into 2e4e3ef; `_extend_tenor` gated on `not self._guarded()`; `tests/test_tenor_extend.py::test_no_tenor_extension_under_the_wave_guard` |
| (this) | `FINAL_POLICY` → `configs/score-push-v6.json`; help/comment; `test_final_robust` pins v6 (+ posterior 0.1, `tenor_extend_types == ()`); runbook, LAB_PLAYBOOK, CONSOLIDATED §5, SAFETY §5, this file |

Conflicts: one, `experiments/V5.md` (the v5 release had struck the "open items" paragraph that the lane rewrote
below its lanes 2–3) — kept the release wording, appended lanes 2–3. `agent.py` / `policy.py` auto-merged.
Guard vs `_extend_tenor`: the extension runs inside `_nonprice`, which `decide_thread` evaluates **before** the
`guarded → _time_guard_move` early return, and its result `n` is what the guard's "its ask, our terms" match
would carry — so an extension would have ridden on the guard's offer. Added `and not self._guarded()` to the
call site: under the guard the non-price package is left as the supplier has seen it (test: unguarded thread
extends 24 → 36 m and logs `tenor_extend`; the same thread with 100 s left logs `time_guard`, no
`tenor_extend`, no 36 m sheet). No effect on v6 (`tenor_extend_types` empty).

v6 config check: `prewarm` not set → `PolicyConfig.prewarm` default **True** applies (offline launch check below
reports `prewarm True`, `prewarm()` not disabled); `fixed_volume_types == ["raw_material"]`, `anchor_by_type` /
`rounds_by_type` as v5; `cost_target_posterior 0.1`; `tenor_extend_types` absent → `()`.

Verification:
- `uv run --locked pytest -q`: **842 passed** (ARENA_DATA exported; 840 + 2 skips without). `ruff check .` clean.
- Replay (305 transcripts, 1611 rounds, all 10 hosted practice cases, `--conditional-exchange off`, A = B):
  **v6 on release ≡ v6 on 427674f** — byte-identical, sha256 `954e8289…8008`
  (`/tmp/replay-v6-base.json`, `/tmp/replay-v6-release.json`);
  **v5 on release ≡ v5 on 2e4e3ef** — byte-identical, sha256 `03cd9b2f…6145` (same hash as the v5 release
  check; `/tmp/replay-v5-2e4e3ef.json`, `/tmp/replay-v5-release2.json`).
- Offline stubbed `negotiator run --set final`: `runner=auto`, `policy_config=…/configs/score-push-v6.json`,
  `policy.prewarm=True`, `fixed_volume_types=('raw_material',)`, `cost_target_posterior=0.1`,
  `tenor_extend_types=()`, `time_guard_rounds=2`, `ROUND_ESTIMATE_S=120.0`.
- Guard calibration (section 4) is unchanged by v6: the posterior only moves P02's opening price; the
  rehearsal's timing/round structure is the same.

### Final launch command (v6)

```bash
cd /Users/sametdegirmenci/Downloads/ysamet-release/tacto-negotiator   # or any checkout at main
export ARENA_DATA=/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/data/package
mkdir -p experiments/runs
NEGOTIATOR_JOURNAL="$PWD/experiments/runs/final-journal.jsonl" \
caffeinate -dimsu uv run --locked negotiator run --set final --runner auto \
  --policy-config configs/score-push-v6.json --parallel 10 > experiments/runs/final.log 2>&1
```

### Ten-case practice confirmation (v6; not run by this worker)

```bash
cd /Users/sametdegirmenci/Downloads/ysamet-release/tacto-negotiator
export ARENA_DATA=/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/data/package
mkdir -p experiments/runs
caffeinate -dimsu uv run --locked negotiator lab run \
  --name score-push-v6-confirm \
  --hypothesis "codex/release-v5 + score-push-v6 (v4 + raw_material fixed-volume ladder + posterior 0.10, wave guard, prewarm): ten-case practice mean >= .7862 projected, P02 .7351, P08 .7036, P18 .5870, others = v4" \
  --author samet \
  --agent negotiator.agent:configured_agent --runner auto \
  --config "$(cat configs/score-push-v6-run.json)" \
  --cases case:P01 case:P02 case:P03 case:P04 case:P05 case:P07 case:P08 case:P10 case:P11 case:P18 \
  --repetitions 1 --max-sessions 10 --environment practice \
  2>&1 | tee experiments/runs/score-push-v6-confirm.log
```

Expected: P01/P03/P04/P07/P10/P11 = v4 values, P02 .7351, P05 .8136, P08 .7036, P18 .5870 (projected mean .7862).

## 9. Generalisation hardening — AUDIT #1–#4 (2026-10-11 05:55–06:20 CEST)

Source: `ysamet-coord/AUDIT-generalization.md` (sim-only audit of v6 on unseen-style fixtures; harness
`/tmp/audit-gen/sim_unseen.py`, before/after runs `/tmp/audit-gen/hardening-{before,after}.log` via
`sim_hardening.py`, holding supplier, 6 rounds, no guard). All four fixes fail closed and touch only
`price_unit != 1` parts, raw_material cases without a reconcilable plan, and listings without `type`.

| # | fix | before (bfa23e6) | after (842f46d) |
|---|---|---|---|
| 1 | `claims._unit_price` → None unless `price_unit` is 1 (used by `fixed_volume.ladder`, `history_claims`, `render`, `_check` → "invalid price basis"). No PO / own-quote claim on per-100 / per-1000 lines. | P16 r1: "Our orders po:4500014324-20, … for part:370020 were placed at **EUR 0.84 per unit**" next to a 94.44 (per 100 kg) ask | P16 r1: reminder only, `refs=None`; P08 PO claim unchanged (EUR 5.17 per unit, `price_unit 1`) |
| 2 | `fixed_volume.need` parses the briefing `Need: N[ x M] UNIT a year`; `plan` requires N == `fixed_terms.volume_per_year`, uses N×M in `unit`, and returns None when the line is missing, disagrees, or N×M exceeds the shared forecast. | P16 r0: "fixed at **5510 kg** … 11020 kg in total", CSV `your_committed_qty` = 1 % of each month (quota 100 %) | P16 r0: "fixed at **551000 kg** … 1102000 kg in total", CSV committed = forecast; P08/P18 text and CSV unchanged (94800 / 23700 kg, total 118500). Fixture H (volume 5500 vs Need 5510): no paragraph, no CSV, no fc ref |
| 3 | `_enrich_evidence` short-circuits only when `_fixed_volume_plan(case, sid)` is not None (plan cached per (case, supplier) on the agent; `_fixed_volume` uses the same cache). | P18 minus `volume_per_year`: `refs=None` all 6 rounds | same fixture: r0 AS-14404 −5.5 %, r1 PPI-C2431 −2.3 %, r2 four `po:` lines at EUR 5.84, r3 scorecard sc:70740@2026Q3 (the v4 path). P08 minus volume (70710) still sends nothing — its hedge statements empty the preferred bank, as under v4. |
| 4 | `_typed(case)` in `decide` / `propose`: a listing without `type` gets `type: None` (copy; caller's dict untouched); every type gate is membership/equality → inert. | fixture E: `KeyError: 'type'` on the first decide (runner → fallback every round) | fixture E: default schedule (anchor 0.12, 5 rounds: 5.23 → 5.37 → … → 5.94), no crash |

- `uv run --locked pytest -q`: **852 passed** (ARENA_DATA exported; `tests/test_generalization_hardening.py`
  adds 10). `ruff check .` clean.
- Replay, all 10 hosted practice cases, 305 transcripts / 1611 rounds, v6 A = B, `--conditional-exchange off`:
  **842f46d ≡ bfa23e6 byte-identical**, sha256 `954e8289…8008` — the same hash as v6 on 427674f
  (`/tmp/replay-v6-bfa23e6.json`, `/tmp/replay-v6-hardened.json`).
- Not applied (per the audit's recommendation): #5 final counter, #6 quality value-swap re-send, #7–#9.
- Launch and ten-case commands: unchanged from section 8 (v6).
