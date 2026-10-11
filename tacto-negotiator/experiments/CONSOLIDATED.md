# codex/consolidated — Sunday ten-case candidate (score-push-v4)

Worktree `/Users/sametdegirmenci/Downloads/ysamet-consolidated`, branch `codex/consolidated`, base
`origin/main 09e7fe4` (= merge of `codex/final-robust` d6df8ca: `--runner auto`, resilient final
polling, decision fallback, lab-parity CLI). Built 2026-10-11 02:10–02:40 CEST (lanes 1–5), wave +
prewarm lanes added 03:50–04:40 CEST (section 8). Pushed to `origin/codex/consolidated`. Hosted
practice budget untouched by this branch (0 practice sessions; 2 free sandbox runs, 4 sessions).

## 1. Commits included

| merge commit | branch @ tip | content |
|---|---|---|
| `9ff8bff` (cherry-pick of `0a6940e`) | `codex/fresh-wave` | wave time guard (`time_left_fn`/`round_estimate_fn`, stop extending with < 2 rounds left), `budget.bounded` 8 s LLM ceiling, `round_time`/`thread_time`/`wave_time_left` trace rows, `tools/wave_rehearsal.py`, 29 tests |
| `8cd88cb` (cherry-pick of `1a7325e`) | `codex/fresh-wave` | `compressed_schedule` + explicit `time_guard` policy keys, guard leader-match + `rfq_yield`, `propose()` back to 3 positional params (section 8.3), fake-clock tests, saved-run on/off replay test |
| `861ce5b` (cherry-pick of `149afea`) | `codex/fresh-prewarm` | `prewarm.py` (package, dossiers, facts, per-case context/estimates/traits before the poll), sqlite `RLock` in context/dossiers/ingestion caches, hooks in `runner.run_waves`/`play_case` and `play.play_waves`/`play_case`, `prewarm: bool = True`, `tools/prewarm_replay.py`, 14 tests |
| `00a4113` | this branch | `compressed_schedule` dataclass default **False** (section 8.2), `score-push-v4(.json/-run.json)` explicit flag block |
| — | `codex/fresh-wave` `485b60f` | **skipped** by instruction: duplicate cherry-pick of the P05 port already in as `2cd31ad` |
| `1a5c0e4` | `codex/fresh-pacing` @ `3bf3959` | H1 `claim_pacing`, H2 `reciprocal_schedule`, H3 `supplier_payment_trade` (all opt-in), P08 fixes (own_quote only from case refs/alternative; supplier step on the standing sheet; never resend an identical sheet while open), `tools/release_check.py`, `tools/replay_decisions.py`, fresh-h2/h1h2/h3/h3h1 configs |
| `2cd31ad` | `codex/fresh-p05-fp` @ `ad811a6` | `rfq_fast_payment_reanchor` (port of archive fd195f3 `_rfq_fast_payment`), `configs/p05-fast-payment.json`, fixture `tests/fixtures/p05_fast_payment_run.json`, `experiments/fresh-lane-p05.md` |
| `4b19359` | `codex/fresh-p18-db5` @ `f93dec1` | `alt_clause_counter` (opt-in, off), `configs/p18-alt-counter.json`, `experiments/fresh-lane-p18.md`, trace `fresh-p18-altdb5-s1` |
| `b5e672a` | `codex/fresh-costbreakdown` @ `883712c` | `cost_breakdown_request` (opt-in, off), `cost_breakdown.py`, fresh-h1h2-cb configs |
| `035aad5` | `codex/fresh-h4` @ `182b08f` | `tools/backoffice.py` (release_check/replay_decisions were already in via fresh-pacing 0322340) |
| `640faf9` | untracked logs from the `../ysamet-fresh` worktree | `experiments/fresh-lane-p08.md`, `experiments/fresh-backoffice-summary.md`, `experiments/backoffice/REPORT.md` (no traces/runs) |
| `e0bd7a8` | this branch | `claim_pacing` gating (section 3), `configs/score-push-v4.json`, `configs/score-push-v4-run.json`, tests |

All merges `--no-ff` (lanes 1–5; every source branch is an ancestor of HEAD) and three cherry-picks
(wave/prewarm, section 8; `485b60f` left out, so `codex/fresh-wave` itself is not an ancestor).
`uv.lock` unchanged (sha `a0ec7fe14679…`). Runtime data `ARENA_DATA` = main checkout `data/package`
(sha `dfcb322f…`), symlinked as `tacto-negotiator/data` (ignored).

## 2. Conflict log

| merge | file | conflict | resolution |
|---|---|---|---|
| fresh-pacing | — | none (fresh-pacing touches `agent/claims/evidence/policy/traits/dossiers`; main's final-robust touches `runner/play/cli/lab`) | — |
| fresh-p05-fp | — | none | — |
| fresh-p18-db5 (`f93dec1`) | `src/negotiator/agent.py` ×2 | both sides added adjacent `__init__` state (`fast_payment_traded` vs `alt_clause_countered`) and adjacent methods (`_rfq_fast_payment` vs `_alt_clause_*`) | kept both, HEAD side first; no logic changed |
| fresh-p18-db5 | `src/negotiator/policy.py` ×2 | both sides appended a new dataclass field and a new name in the bool-validator tuple | kept both fields (`rfq_fast_payment_reanchor`, `alt_clause_counter`); validator tuple lists both |
| fresh-costbreakdown | `src/negotiator/policy.py` ×2 | same shape: `cost_breakdown_request` field + validator name vs the two above | kept all three; validator tuple now `…, "rfq_fast_payment_reanchor", "alt_clause_counter", "cost_breakdown_request"` |
| fresh-h4 | — | none | — |
| wave `0a6940e` → `9ff8bff` | `src/negotiator/runner.py` `_worker` | main's final-robust `try: propose … except: fallback_propose` block vs the wave's `wave_time_left` trace row + `d0`/`decide_s` timing around the same `propose` call | **main's launch/polling/fallback logic kept**; the wave hooks wrap it additively (trace row before, `decide_s`/`slowest_decide_s` after the try/except). `_time_left`, `_wire_agent_clock`, `round_time`, `_trace_thread_times`, `opened_at` auto-merged |
| wave `0a6940e` | `src/negotiator/agent.py` `_reciprocal_price` | fresh-pacing's longer docstring (never resend an identical sheet) vs the wave's `or self._guarded()` early return | both: HEAD docstring, wave condition |
| wave `1a7325e` → `8cd88cb` | `src/negotiator/agent.py` `_reciprocal_price` | same hunk again: wave adds `ml`/`comp` params and `or comp is not None` | both (HEAD docstring + wave's sentence, `… or self._guarded() or comp is not None`) |
| wave `1a7325e` | `src/negotiator/policy.py` | `alt_clause_counter`/`cost_breakdown_request` fields vs `time_guard`/`compressed_schedule` fields at the same spot | all four kept; `compressed_schedule` default set to False here (section 8.2); the validator's second tuple (`d.get(k, True)`) covers `time_guard`, `compressed_schedule` |
| wave `1a7325e` | `configs/score-push-v4.json` (add/add) | wave's v4 = v3 + `time_guard`/`compressed_schedule` vs ours = v3 + `claim_pacing`/`rfq_fast_payment_reanchor` | ours, then the explicit nine-flag block of item C (`00a4113`) |
| wave `1a7325e` | `experiments/LOG.md` | two 2026-10-11 entries appended at the same place | both kept (main's supplier-brief entry first, then the wave compression entry) |
| wave `1a7325e` | `tools/replay_decisions.py` (add/add) | — | auto-resolved: byte-identical to the copy already merged via fresh-pacing |
| prewarm `149afea` → `861ce5b` | `src/negotiator/policy.py` ×2 | `prewarm: bool = True` next to the `time_guard` block; validator tuple | field kept; `prewarm` added to the default-True validator tuple (`time_guard`, `compressed_schedule`, `prewarm`) |
| prewarm `149afea` | `tools/wave_rehearsal.py` ×7 | the lane's prewarm hooks/columns (`--prewarm`, `first_decide_s`, `prewarm_case_s`) were written against `0a6940e`, ours carries `1a7325e`'s `--compression`/`comp_ratio` | hand-merged: both options and both column sets; `--compression` default **off** (= v4), `--prewarm` default on |

Main's launch/polling/fallback logic is intact: `git diff 09e7fe4 HEAD -- src/negotiator/cli.py` is
empty; `runner.py` +87/−2 (the −2 are the two `CaseState(...)` constructions gaining `opened_at`), all
additive wave timing hooks + the one-line prewarm call before the `run_waves` poll loop and in
`play_case`; `play.py` +6 (the two prewarm calls). The auto-merged hunks in `agent.py` (cost-breakdown
hook after `_fast_payment_note`, alt-clause hook in `decide_thread`, wave guard in `decide_thread`/
`_propose`) were reviewed; focused and full suites pass.

## 3. Policy: `configs/score-push-v4.json`

v3 baseline = `configs/score-push-v3.json` (= `FINAL_POLICY` in `cli.py`, the ten-case v2-confirm
run 6b162c54 config + P01 fast payment + P11 value swap; `configs/candidate.json` is the older
pre-score-push policy and is **not** the baseline). v4 = v3 + `claim_pacing: true` +
`rfq_fast_payment_reanchor: true` + an explicit flag block: `reciprocal_schedule`, `alt_clause_counter`,
`supplier_payment_trade`, `cost_breakdown_request: false`; `time_guard: true`, `compressed_schedule:
false`, `prewarm: true`. Policy sha256 `eab4d7882cbc…` (sort_keys JSON; file sha `2365fcfe58b5…`).
Runner wrapper `configs/score-push-v4-run.json` = `{"policy_config": …, "estimates": {}, "meso": false}`
(the lane logs' `lab run --config` form). Both load via `PolicyConfig.from_dict` and `configured_agent`;
`test_policy_keys_default_on_and_validate` pins the block (v4 minus the nine flags == v3).

`FINAL_POLICY` in `src/negotiator/cli.py` still points at `score-push-v3.json` (main's launch code
left untouched): `negotiator run --set final` without `--policy-config` would play **v3** (with
`time_guard`/`prewarm` on and `compressed_schedule` off by dataclass default). The ten-case and final
commands below pass the v4 config explicitly.

### Flag table

| flag | v4 | evidence |
|---|---|---|
| `rfq_fast_payment_reanchor` | **on** | P05 **0.8136 ×2**: archive `p05-fast-payment-O` (session `0da0416bc3b03ba2`) and repeat run `a1c2e3ea` `fresh-p05-fp-s1` (`1cde0b704685b2bd`, commit e8b0396) vs v3 0.7723; off = byte-identical to v3 (replay) |
| `claim_pacing` (gated, see below) | **on** | P18 **0.5325 ×2** (`129ce820` `6cae513938471768`, `e7045989` `98f007bf25a16be3`, config fresh-h1h2) vs v3 0.4531/0.5200; P18 alt-counter tie `a2becc8e` 0.5325 reproduces the same r1–r3; P08 `f5852936` 0.5930 = v3 tie (with the ungated deep bank; gated v4 sends P08 exactly v3's messages, also 0.5930) |
| `time_guard` | **on** (default on) | wave lane kit sim, 10 cases, 55 s replies, 480 s cap (LOG.md 2026-10-11 wave compression): guard on = guard off on P01–P04/P07/P08/P10/P18, P05 no deal at the cap → **0.829**, P11 walked → 0.797; 0 cap closes. Inert without a cap (practice): `time_left_fn` is None → replay byte-identical (section 3 audit, `test_compressed_schedule_replay`). No hosted evidence (0 hosted sessions on the lane) |
| `compressed_schedule` | **off** (default flipped to off, `00a4113`) | same sim: the literal rescale turns every case into a round-2 match — P01 .734→.429, P02 .695→.174, P03 .869→.478, P04 .864→.356, P05 .829→.316, P08 .805→.222, P10 .946→.782, P18 .819→.230 — while leader-match + `rfq_yield` alone carry P05. The lane kept the dataclass default on "as specified"; the evidence says off. Code kept, opt-in per config |
| `prewarm` | **on** (default on) | decision-neutral by construction (same loaders, called earlier; `tools/prewarm_replay.py`, 14 tests incl. `test_run_waves_prewarms_before_the_first_poll`). Lane measurement: first decision per case 11–27 s → < 1 s with ten cases starting at once. Rehearsal here: first decision ≤ 0.10 s, package prewarm 0.15 s (section 8.4) |
| `reciprocal_schedule` | off | P18 `fresh-p18-h2-s1` 0.4531 = v3 (no-op: our schedule step already ≤ theirs; measures the wrong sheet) |
| `supplier_payment_trade` (H3) | off | P05 **0.6086 ×2** (`7d01d937`, `d098b465`) vs 0.7723 — regression |
| `alt_clause_counter` | off | P18 `a2becc8e` 0.5325 tie (n=1, supplier answered 5.30 db5 with final 5.40 db5); lane says do not merge yet |
| `cost_breakdown_request` | off | no hosted evidence; code merged for later lanes |

Not flag-gated (wave lane, "pure safety", active whenever a wave cap is known): `rounds_available`
caps `moves_left` (`ml = min(moves_left, rounds_available)`), no final-offer counter with < 2 rounds
available, RFQ rivals hold (`rfq_yield`) while `rounds_available <= 2` and the leader is open. See the
open risk in section 9.

### claim_pacing replay audit and gating decision

Audit 1 — `tools/replay_decisions.py`, A = v3, B = v4 **with the original pacing** (one claim per
message from round 1 + deeper bank), all 111 saved transcripts of P01/P03/P04/P11/P05/P18 across the
main checkout, the lane worktrees and `ysamet-run-archive`:

| case | runs | v3 round 1 claims | v4 (original) round 1 | moved / added | total claims v3 → v4 | verdict |
|---|---|---|---|---|---|---|
| P01 (.9602/.9702 runs) | 19 | notice `doc:…-P01`+`ctr:4600070110`, `idx:PPI-D351` (2 ids), `sc:70110@2026Q3` | notice only | idx → r2, sc → r3, **+ po_history ×4 at r4** | 3 → 4 | **loses two round-1 claims of the winning message** |
| P03 (.8998) | 6 | none | `sc:70530@2026Q3` | **+ sc r1, + po ×4 r2** (deep bank) | 0 → 2 | adds unvalidated claims to the winning path |
| P04 (.8604) | 12 | none | `sc:70620@2026Q3` | **+ sc r1, + po ×4 r2** | 0 → 2 | same |
| P11 (.8771) | 18 | `sc:70140@2026Q3`, `idx:PPI-D351` | sc only | idx → r2, **+ po ×4 r3** | 2 → 3 | **loses the round-1 index claim of the .8771 message** |
| P18 (.5325) | 21 | `idx:AS-14404`, `idx:PPI-C2431` | `idx:AS-14404` | PPI → r2, + sc r3 (deep) | 2 → 3 | the measured 0.5325 mechanism |
| P05 (.8136) | 35 | rival offers / scorecards, 1 slot | identical | — | = | pacing inert on RFQ; only r7/r10 14 d differ (fast payment) |

Decision rule triggered (P01 and P11 lose round-1 claims; P03/P04 gain claims v3 never sent). Two
candidate gates were examined:

- **(a) "round 1 = v3 bundle, pacing from round 2"** (the literal rule). Round 1 is protected, but the
  deeper bank then adds `po_history` claims from round 2 on P01/P03/P04/P11 (not byte-identical), and
  P18 sends both index claims in round 1 — exactly the v3 message the supplier answers with 5.50
  (0.4531/0.5200 paths), so the +0.08 P18 gain is lost. Under (a) `claim_pacing` would be a no-op on
  every validated case and a regression vs the measured P18 run.
- **(b) "one claim per *kind* per message; deeper bank only after a deferral"** — implemented as the
  behaviour of `claim_pacing` (`evidence.py` `EvidencePolicy.pace` / `paced_before`, commit `e0bd7a8`).
  A bundle of different kinds (P01 notice+index+scorecard, P11 scorecard+index) travels in one
  message exactly as in v3; a second claim of a kind the message already carries (P18's second index
  decrease) waits for the next message; the deeper bank (one claim per message, never should-cost or
  cherry-picked windows) opens only in a thread where two claims of one kind have already been sent,
  so threads v3 never paced stay byte-identical. This is the observed P18 mechanism (each supplier
  acknowledgement names one index decrease) and the only variant that protects P01/P03/P04/P11 while
  keeping P18's 0.5325 path. It is **not** a case-type gate.

Honest caveat: (b) is a post-hoc restriction fitted to the six replayed cases (n=2 hosted evidence for
P18 only, no hosted evidence for "index+scorecard in one message" vs split). The stricter original
rule is not kept as a sub-option; the diff is one function and can be restored from `3bf3959`.
Tests: `tests/test_fresh_pacing.py` (`test_pacing_keeps_mixed_kind_bundles_together_and_defers_only_same_kind`,
`test_pacing_first_message_of_p01_and_p11_equals_v3`, P08 unchanged-without-deferral), 9 passed.

Audit 2 — same tool, A = v3, B = v4 **with (b)**, 130 transcripts (P08 added), JSON `/tmp/replay-v3-v4b.json`:

| case | replays | A == B (all rounds, sheets+action+refs+body) | first A ≠ B | what differs |
|---|---|---|---|---|
| P01 | 19 | **19/19 identical** | — | — |
| P03 | 6 | **6/6 identical** | — | — |
| P04 | 12 | **12/12 identical** | — | — |
| P08 | 19 | **19/19 identical** | — | — |
| P11 | 18 | **18/18 identical** | — | — |
| P05 | 35 | 25 identical | r7 (sup:70210, 10 runs that reach the undercut re-anchor) | payment 90 → **14 d** at 26.79, r10 **28.00/14 d**; 70240/70250 rounds unchanged |
| P18 | 21 | 0 identical (by design) | r1 | refs `AS-14404 + PPI-C2431` → `AS-14404` only; r2 `PPI-C2431`; r3 `sc:70740@2026Q3` (deep bank) |
| P02 / P07 / P10 | 42 | **42/42 identical** | — | — (v4 flags never fire) |

- P18 `fresh-p18-h1h2-s1` (0.5325): B reproduces the saved transcript in all 5 rounds — r1 5.37 +
  `idx:AS-14404@2026-06/09`, r2 5.39 + `idx:PPI-C2431@2026-06/08`, r3 5.40 no clause + `sc:70740@2026Q3`,
  r4 5.40 **db5** (take alternative), r5 accept `offer:70740-4`. Same for `fresh-p18-h1h2-s2` and
  `fresh-p18-altdb5-s1` r1–r3.
- P05 `fresh-p05-fp-s1` and archive `p05-fast-payment-O` (0.8136): B = saved at r7 (26.79 / **14 d** /
  35 d + PPI-D351) and r10 (**28.00 / 14 d**). (r2/r11 on sup:70240 are flagged `supplier_mismatch` for
  A and B alike — a limitation of the tool's `decide`-based replay, not of the policy: `decide` picks
  the first non-holding thread, which at those two points is 70250; `propose(case, threads, "sup:70240")`
  on the same snapshots reproduces both saved moves, see section 8.3.)
- **Flag-off baseline check:** A = v3 replayed on a pure `09e7fe4` worktree (`../ysamet-pure-main`, only
  the replay tool copied in) vs A = v3 on this branch: **130/130 replays, 848 decision rounds
  byte-identical** (supplier choice, sheets, action, refs, body). The merge did not alter v3.
  Re-run after the wave + prewarm cherry-picks (HEAD `00a4113`): still **130/130 / 848 identical**, and
  B = v4 after the cherry-picks vs B = v4 at `7dba7c0`: **172/172 replays, 1000 decision points
  identical** (the wave/prewarm code is inert without a cap, as the lane claimed).

## 4. Verification (HEAD `00a4113`)

- `uv sync --locked` ok (lock unchanged); `uv run ruff check src tests tools` clean.
- `uv run --locked pytest -q` (ARENA_DATA set): **838 passed** in 74 s (800 before the two lanes).
  The five named fake-clock tests are present and pass:
  `test_compressed_schedule_closes_before_cap_minus_20s`,
  `test_final_offer_is_never_countered_when_the_counter_cannot_be_reaped` (test_compressed_schedule),
  `test_guard_accepts_acceptable_standing_sheet_before_the_cap` (test_wave_time_guard),
  `test_agent_time_guard_closes_before_the_watchdog` (test_runner),
  `test_run_waves_prewarms_before_the_first_poll` (test_prewarm).
- Test adjustments for the flipped default: `test_policy_keys_default_on_and_validate` asserts
  `compressed_schedule is False` by default and pins the v4 flag block; the compression unit tests build
  their agents through `_comp()` (policy-less agent with `compressed_schedule = True`) and the replay
  on/off test sets `on.compressed_schedule = True` explicitly. `PackageAgent.__init__` now derives
  `compressed_schedule = bool(policy and policy.compressed_schedule)` (a policy-less agent no longer
  compresses silently; `time_guard` keeps its default-on derivation).
- Sandbox (free), `lab run --runner auto`, config `score-push-v4-run.json`:

| run | commit | case | session | score | required | rounds | wall s | timeouts | error |
|---|---|---|---|---|---|---|---|---|---|
| `e3d7a4b8` `consolidated-sandbox-s1` | `e0bd7a8` | D01 | `d096e71ee72d9fe5` | **0.9192** | 0.9192 | 7 | 5.6 | 0 | None |
| | | D02 | `c7125f443e453e71` | **0.5239** | 0.5239 | 9 | 8.7 | 0 | None |
| `625209f1` `consolidated-sandbox-s2` | `00a4113` (clean) | D01 | `96ce1589c8c5aa87` | **0.9192** (0.919230949) | 0.9192 | 7 | 5.1 | 0 | None |
| | | D02 | `20cd758db651b204` | **0.5239** (0.523861298) | 0.5239 | 9 | 8.6 | 0 | None |

All attempts `completed`, runs `completed`, practice quota untouched (255 left after other lanes'
use; sandbox is free).

## 5. Ten-case run command (NOT run)

Same launch pattern as the lane runs (`fresh-p05-fp-s1`, `fresh-p18-h1h2-s1`) and the v2 ten-case
confirmation (`score-push-final-confirm`): tracked `lab run`, `configured_agent`, `--runner auto`
(rfq → async, single-supplier → serial), inline JSON config, one repetition, max 10 sessions.

```bash
cd /Users/sametdegirmenci/Downloads/ysamet-consolidated/tacto-negotiator
export ARENA_DATA=/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/data/package
mkdir -p experiments/runs
caffeinate -dimsu uv run --locked negotiator lab run \
  --name score-push-v4-confirm \
  --hypothesis "codex/consolidated + score-push-v4 (claim_pacing per-kind, rfq_fast_payment_reanchor): ten-case practice mean >= .7619 projected, P05 .8136, P18 .5325, others = v3" \
  --author samet \
  --agent negotiator.agent:configured_agent --runner auto \
  --config "$(cat configs/score-push-v4-run.json)" \
  --cases case:P01 case:P02 case:P03 case:P04 case:P05 case:P07 case:P08 case:P10 case:P11 case:P18 \
  --repetitions 1 --max-sessions 10 --environment practice \
  2>&1 | tee experiments/runs/score-push-v4-confirm.log
```

Run it in the foreground of a long-blocking call (LOG.md 1026: detached `lab run` lost its coordinator).
Working tree must be clean (no `--allow-dirty`), otherwise provenance records a patch. To record the
decision trace add `"trace_dir": "experiments/traces/score-push-v4-confirm"` to the inline config.
Expected from the replay: P01/P02/P03/P04/P07/P08/P10/P11 reproduce v3 (.9602/.5993+/.8998/.8604/
.7600/.5930/.6551/.7902 or their v3 values), P05 .8136, P18 .5325. Practice has no wave cap, so
`time_guard`/`rounds_available`/`rfq_yield` are inert there (`time_left_fn` returns None); `prewarm`
runs once before the first poll (decision-neutral).

For the Live Final the runbook command needs the v4 config spelled out
(`--policy-config configs/score-push-v4.json`), since `--set final` defaults to v3.

## 6. Wave + prewarm lanes (added 03:50–04:40 CEST)

### 6.1 What came in

`codex/fresh-wave` `0a6940e` + `1a7325e` (cherry-picked as `9ff8bff`, `8cd88cb`; `485b60f` skipped),
`codex/fresh-prewarm` `149afea` (as `861ce5b`). Section 2 has the conflict log. The guard/compression
code is additive in `agent.py` (`time_guard`, `_guarded`, `rounds_available`, `compression`,
`_time_guard_move`, `rfq_yield`), the runner wires the clock at `_open` and emits `wave_time_left`/
`round_time`/`thread_time`; `budget.bounded` caps one LLM call at 8 s. All of it keys on
`time_left_fn`, which only the capped (final) runner sets.

### 6.2 `compressed_schedule` default → False (item C)

Wave lane's own kit-sim table (LOG.md "wave compression", 10 cases, 55 s replies, 480 s cap): guard on +
compression off equals guard off on every case except P05 (no deal at the cap → 0.829) and P11 (walked →
0.797); compression on turns every case into a round-2 match (P01 .734→.429, P08 .805→.222, P05 .829→.316,
P18 .819→.230, …). The lane kept the dataclass default on "as specified"; this branch flips it to off
(`policy.py`, `00a4113`), keeps the code, and v4 records `compressed_schedule: false` explicitly.
`PackageAgent.__init__` derives `compressed_schedule = bool(policy and policy.compressed_schedule)` so a
policy-less agent does not compress either. Tests adjusted as listed in section 4.

### 6.3 Wave rehearsal (`tools/wave_rehearsal.py`, kit sim, 10 cases in one 480 s wave, guard on, compression off, prewarm on, v4)

Run A — `--delay 52` (replies 52 s; rounds 52.2 s single-supplier, 87 s on P05 where the three sends share the slot):

| case | type | deal | score | end | case s | rounds | slowest round s | first decision s | prewarm case s | guard fired |
|---|---|---|---|---|---|---|---|---|---|---|
| P01 | price_increase | yes | 0.734 | accepted | 260.6 | 5 | 52.2 | 0.08 | 0.50 | no |
| P02 | price_increase | yes | 0.695 | accepted | 208.6 | 4 | 52.2 | 0.08 | 0.49 | no |
| P03 | renewal | yes | 0.869 | accepted | 260.7 | 5 | 52.2 | 0.03 | 0.37 | no |
| P04 | renewal | yes | 0.864 | accepted | 260.7 | 5 | 52.2 | 0.06 | 0.40 | no |
| P05 | rfq | yes | **0.020** | accepted (sup:70240 `offer:70240-1`) | 230.6 | 5/1/1 | 87.0 | 0.05 | 0.47 | no (`rfq_yield` from round 2) |
| P07 | bundling | yes | 0.862 | accepted | 260.7 | 5 | 52.2 | 0.10 | 0.42 | no |
| P08 | raw_material | yes | 0.805 | accepted | 260.7 | 5 | 52.2 | 0.05 | 0.38 | no |
| P10 | capacity | yes | 0.946 | accepted | 260.7 | 5 | 52.2 | 0.06 | 0.40 | no |
| P11 | quality | **no** | 0.000 | walked_away (gap closed at its final) | 208.7 | 4 | 52.2 | 0.09 | 0.43 | no |
| P18 | raw_material | yes | 0.819 | accepted | 260.8 | 5 | 52.2 | 0.09 | 0.37 | no |

Slowest agent decision 0.19 s, slowest first decision **0.10 s**, package prewarm 0.15 s, worst case
260.8 s of 480, 0 cap closes, 0 timeouts. At 52 s replies every 5-round schedule finishes by 260 s, so
the guard window (last 240 s) is never reached and the table equals the lane's "guard off" column — P11
walks at its final exactly as there. P05 is the exception, see below.

Run B — `--delay 75` (the lane's measured 73–90 s round regime; rounds 75.2 s, P05 110 s):

| case | deal | score | end | case s | rounds | guard fired / action |
|---|---|---|---|---|---|---|
| P01 | yes | 0.734 | accepted | 375.6 | 5 | match |
| P02 | yes | 0.695 | accepted | 300.6 | 4 | accept |
| P03 | yes | 0.869 | accepted | 375.5 | 5 | match |
| P04 | yes | 0.864 | accepted | 375.5 | 5 | match |
| P05 | yes | **0.020** | accepted (sup:70240 `offer:70240-1`) | 265.7 | 4/1/1 | hold ×6, **accept** |
| P07 | yes | 0.862 | accepted | 375.7 | 5 | match |
| P08 | yes | 0.805 | accepted | 375.6 | 5 | match |
| P10 | yes | 0.946 | accepted | 375.7 | 5 | match |
| P11 | yes | **0.797** | accepted | 375.7 | 5 | match |
| P18 | yes | 0.819 | accepted | 375.7 | 5 | match |

First decisions ≤ 0.18 s, slowest decision 0.21 s, worst case 375.7 s, 0 cap closes. Nine of ten cases
reproduce the lane's "guard on, compression off" column to the third decimal (incl. P11 0.797 via the
leader match). **P05 does not reproduce the lane's 0.829 (expected ≥ .78) in either regime** — both runs
end at 0.020 with the runner accepting rival 70240's opening-round sheet (39.94). Trace (run B):
rivals 70240/70250 hold from round 2 (`rfq_yield`, `rounds_available` ≤ 2 once the shared-slot round
measures 110 s), the leader 70210 walks the schedule alone (35.23 → 36.03 → 36.51 → 36.67), the guard
fires at 239.6 s left and holds the rivals six times (`pending: false`, "leader may still match"), then
at 233.6 s left `_guard_round_fits` turns false and the rival's guard decision returns `close` naming
`offer:70210-4` (c 312 534) as the sheet to accept — but the runner's `_close` excludes threads with a
message in flight after its 20 s `CLOSE_WAIT_S`, the leader's round-4 POST is still inside the 75 s
injected delay, and `close_decision` accepts the best *remaining* sheet, 70240's. Root cause of the
`pending: false` and of the 0.02 is a **rehearsal-tool artifact**: `arena_kit.sim.Sim.message` appends
the supplier's reply synchronously and `SimArena.send` only *sleeps* the delay afterwards, so the rivals'
hold loops (`_refresh_all` once their 60 s window passed) already see the leader's next reply while the
leader's worker is still "in flight" — the leader thread never looks like it awaits a reply, and the
close happens with the leader excluded. On the hosted arena the reply is not visible before the POST
returns, so the guard's "leader awaits a reply" hold applies; but the sim cannot be used as evidence for
P05 under the guard until `SimArena.send` withholds the reply for the delay (and run A's "supplier
agreed" close at 0.02 is the same artifact on the leader's round-5 "their price, our terms" message). The
lane's 0.829 was presumably a timing in which the leader matched before any rival refreshed. Open risk
in section 8.

### 6.4 Item E — the `propose()` arity fix

`7dba7c0` had `PackageAgent.propose(self, case, threads, supplier_id, *, defer_evidence=False)` (four
parameters), so `runner.propose`'s `_arity(fn) == 3` test failed and the async runner used the fallback:
`agent.decide(case, full snapshot)`; if `decide` picked another thread, `agent.decide(case, {sid: thread})`
on a **single-thread snapshot**. `1a7325e` restores the three-parameter `propose` (the keyword moved to
`_propose_for`), so every async worker now calls `agent.propose(case, full snapshot, sid)`. The hosted
P05 0.8136 runs (`fresh-p05-fp-s1`, archive `p05-fast-payment-O`, both `--runner async`) ran under the
OLD path. Quantified three ways:

1. **Saved transcripts, decision by decision** (`/tmp/arity_replay.py`: the saved history up to each of
   our messages, substituted with our replayed moves, both paths side by side; v4 config). The replay
   tool itself uses `decide` only, i.e. neither path exactly — hence its `supplier_mismatch` rows.

   | transcript | OLD path (decide full → decide single) reproduces | NEW path (`propose`, full snapshot) reproduces |
   |---|---|---|
   | P05 `fresh-p05-fp-s1` (0.8136, 13 decision points) | 12/13 — r2 via the single-thread view (27.72 ✓), **r11 (sup:70240 30.59/45 d) comes back without the saved `offer:70210-3` rival ref** (single view cannot cite the leader) | **13/13** sheets, refs and bodies incl. r2 27.72/90 d, r7 26.79/14 d, r10 28.00/14 d, r11 30.59/45 d + `offer:70210-3`, r13 accept |
   | P05 archive `p05-fast-payment-O` (0.8136, 12 points) | 11/12 (same r11) | **12/12** |
   | P18 `fresh-p18-h1h2-s1` (0.5325, single supplier) | 5/5 | 5/5 (single supplier: `--runner auto` plays it serially through `decide`; the fix is irrelevant) |

   Reading: the hosted 0.8136 transcripts are reproduced *exactly* by the new path; the old path's
   index-aligned emulation misses the r11 ref, i.e. the hosted run at r11 happened to see the full
   view (which thread `decide` ranks first depends on what the concurrent snapshot contained at that
   instant). The old path was the order-sensitive one.
2. **Kit sim, `--runner async` (wave_rehearsal, delay 0, guard off, compression off), HEAD vs HEAD with
   only the arity reverted** (`def propose(self, case, threads, supplier_id, *, defer_evidence=False)`):
   P05 0.8291 / P18 0.8189 both ways; per-thread sends and decision rows identical for all three P05
   threads and P18 (0 differing rows).
3. **Offline replay** (section 3, decide-based): unchanged by construction.

**Verdict:** the ten-case run is **not** at risk of diverging from the hosted P05/P18 evidence because of
the fix; the measured risk runs the other way (the old single-thread fallback drops rival refs). Keep it.
One-line revert if the coordinator wants the old behaviour anyway (`src/negotiator/agent.py` ~L1128):

```python
    def propose(self, case, threads, supplier_id, *, defer_evidence=False):  # 4 params -> runner falls back to decide
```

(no test asserts the signature itself; the wave tests that drive the async runner through `propose`
— guard leader-match, `rfq_yield` — would then run through the `decide` fallback and must be re-checked).

## 7. Open merges pending

- None. `codex/fresh-wave` `485b60f` is intentionally not an ancestor (duplicate P05 port).
- ACKS handoff: this report. Pushed as `origin/codex/consolidated`.

## 8. Open risks

1. **`FINAL_POLICY` (cli.py) still = v3.** Pass `--config "$(cat configs/score-push-v4-run.json)"` (lab) or
   `--policy-config configs/score-push-v4.json` (`negotiator run`) explicitly, or repoint it. With v3 the
   wave guard and prewarm are still on (dataclass defaults) and compression off.
2. **Guard/`rounds_available` safeties have no hosted evidence** (0 hosted sessions on the wave lane; the
   kit sim concedes 2 % a round whatever we send). `rfq_yield` and the `moves_left` cap are not
   flag-gated: with a 480 s cap and ~60 s replies the P05 rivals will hold from round 2 on (their first
   round measured 87–110 s with the shared send slot) and the leader plays alone — a different game from
   the hosted 0.8136 path (13 decision points across three threads, which would not fit in 480 s anyway).
   In practice (no cap) none of this is active; the ten-case run is unaffected.
3. **Rehearsal tool artifact (6.3):** `SimArena` exposes the supplier reply before the injected delay
   elapses; combined with the runner's `_close` excluding in-flight threads after `CLOSE_WAIT_S` (20 s)
   the rehearsal accepts a rival's opening sheet on P05 (0.02). Fix `SimArena.send` (withhold the reply
   until the delay has passed) before using the rehearsal as P05 evidence. The hosted equivalent — a
   guard-initiated close while the leader's POST is in flight longer than 20 s — is worth a look: the
   agent holds while `threads[leader][-1]` is ours, so it needs a refreshed leader thread without our
   message to misfire, which the hosted thread view should not produce.
4. **The sim's P11 0.797 (guard "match")** is a toy-sim win; the hosted P11 value is v3's 0.7902 path, which the
   replay shows unchanged.
5. **`claim_pacing` gating (3b)** is fitted to the replayed cases (n=2 hosted P18); stated in section 3.
6. **Flake:** `test_final_robust.py::test_async_worker_crash_still_ends_the_session[0]` failed once in an
   earlier focused run (not in any full run); LOG.md notes this async-simulator timing flake.
