# codex/consolidated — Sunday ten-case candidate (score-push-v4)

Worktree `/Users/sametdegirmenci/Downloads/ysamet-consolidated`, branch `codex/consolidated`, base
`origin/main 09e7fe4` (= merge of `codex/final-robust` d6df8ca: `--runner auto`, resilient final
polling, decision fallback, lab-parity CLI). Built 2026-10-11 02:10–02:40 CEST. Not pushed. Hosted
practice budget untouched by this branch (0 practice sessions; 1 free sandbox run, 2 sessions).

## 1. Commits included

| merge commit | branch @ tip | content |
|---|---|---|
| `1a5c0e4` | `codex/fresh-pacing` @ `3bf3959` | H1 `claim_pacing`, H2 `reciprocal_schedule`, H3 `supplier_payment_trade` (all opt-in), P08 fixes (own_quote only from case refs/alternative; supplier step on the standing sheet; never resend an identical sheet while open), `tools/release_check.py`, `tools/replay_decisions.py`, fresh-h2/h1h2/h3/h3h1 configs |
| `2cd31ad` | `codex/fresh-p05-fp` @ `ad811a6` | `rfq_fast_payment_reanchor` (port of archive fd195f3 `_rfq_fast_payment`), `configs/p05-fast-payment.json`, fixture `tests/fixtures/p05_fast_payment_run.json`, `experiments/fresh-lane-p05.md` |
| `4b19359` | `codex/fresh-p18-db5` @ `f93dec1` | `alt_clause_counter` (opt-in, off), `configs/p18-alt-counter.json`, `experiments/fresh-lane-p18.md`, trace `fresh-p18-altdb5-s1` |
| `b5e672a` | `codex/fresh-costbreakdown` @ `883712c` | `cost_breakdown_request` (opt-in, off), `cost_breakdown.py`, fresh-h1h2-cb configs |
| `035aad5` | `codex/fresh-h4` @ `182b08f` | `tools/backoffice.py` (release_check/replay_decisions were already in via fresh-pacing 0322340) |
| `640faf9` | untracked logs from the `../ysamet-fresh` worktree | `experiments/fresh-lane-p08.md`, `experiments/fresh-backoffice-summary.md`, `experiments/backoffice/REPORT.md` (no traces/runs) |
| `e0bd7a8` | this branch | `claim_pacing` gating (section 3), `configs/score-push-v4.json`, `configs/score-push-v4-run.json`, tests |

All merges `--no-ff`; every source branch is an ancestor of HEAD, so the lane history is preserved.
`uv.lock` unchanged (sha `a0ec7fe14679…`). Runtime data `ARENA_DATA` = main checkout `data/package`
(sha `dfcb322f…`), symlinked as `tacto-negotiator/data` (ignored).

**Not merged (by instruction):** `codex/fresh-wave` (`485b60f`: wave time guard 0a6940e + a duplicate
cherry-pick of the P05 port). See section 8.

## 2. Conflict log

| merge | file | conflict | resolution |
|---|---|---|---|
| fresh-pacing | — | none (fresh-pacing touches `agent/claims/evidence/policy/traits/dossiers`; main's final-robust touches `runner/play/cli/lab`) | — |
| fresh-p05-fp | — | none | — |
| fresh-p18-db5 (`f93dec1`) | `src/negotiator/agent.py` ×2 | both sides added adjacent `__init__` state (`fast_payment_traded` vs `alt_clause_countered`) and adjacent methods (`_rfq_fast_payment` vs `_alt_clause_*`) | kept both, HEAD side first; no logic changed |
| fresh-p18-db5 | `src/negotiator/policy.py` ×2 | both sides appended a new dataclass field and a new name in the bool-validator tuple | kept both fields (`rfq_fast_payment_reanchor`, `alt_clause_counter`); validator tuple lists both |
| fresh-costbreakdown | `src/negotiator/policy.py` ×2 | same shape: `cost_breakdown_request` field + validator name vs the two above | kept all three; validator tuple now `…, "rfq_fast_payment_reanchor", "alt_clause_counter", "cost_breakdown_request"` |
| fresh-h4 | — | none | — |

The conflicts anticipated in `runner.py _worker`, `play.py play_case`, `cli.py new_agent` did **not**
occur: none of the five merged branches modifies those files, so main's launch/polling/fallback logic
is untouched (verified: `git diff 09e7fe4 HEAD -- src/negotiator/runner.py src/negotiator/play.py
src/negotiator/cli.py` is empty). The auto-merged hunks in `agent.py` (cost-breakdown hook after
`_fast_payment_note`, alt-clause hook in `decide_thread`) were reviewed; focused and full suites pass.

## 3. Policy: `configs/score-push-v4.json`

v3 baseline = `configs/score-push-v3.json` (= `FINAL_POLICY` in `cli.py`, the ten-case v2-confirm
run 6b162c54 config + P01 fast payment + P11 value swap; `configs/candidate.json` is the older
pre-score-push policy and is **not** the baseline). v4 = v3 + `claim_pacing: true` +
`rfq_fast_payment_reanchor: true`; `reciprocal_schedule`, `alt_clause_counter`,
`supplier_payment_trade`, `cost_breakdown_request` absent (= false). Policy sha256 `417ac597f66a…`.
Runner wrapper `configs/score-push-v4-run.json` = `{"policy_config": …, "estimates": {}, "meso": false}`
(the lane logs' `lab run --config` form). Both load via `PolicyConfig.from_dict` and `configured_agent`.

`FINAL_POLICY` in `src/negotiator/cli.py` still points at `score-push-v3.json` (main's launch code
left untouched): `negotiator run --set final` without `--policy-config` would play **v3**. The
ten-case and final commands below pass the v4 config explicitly.

### Flag table

| flag | v4 | evidence |
|---|---|---|
| `rfq_fast_payment_reanchor` | **on** | P05 **0.8136 ×2**: archive `p05-fast-payment-O` (session `0da0416bc3b03ba2`) and repeat run `a1c2e3ea` `fresh-p05-fp-s1` (`1cde0b704685b2bd`, commit e8b0396) vs v3 0.7723; off = byte-identical to v3 (replay) |
| `claim_pacing` (gated, see below) | **on** | P18 **0.5325 ×2** (`129ce820` `6cae513938471768`, `e7045989` `98f007bf25a16be3`, config fresh-h1h2) vs v3 0.4531/0.5200; P18 alt-counter tie `a2becc8e` 0.5325 reproduces the same r1–r3; P08 `f5852936` 0.5930 = v3 tie (with the ungated deep bank; gated v4 sends P08 exactly v3's messages, also 0.5930) |
| `reciprocal_schedule` | off | P18 `fresh-p18-h2-s1` 0.4531 = v3 (no-op: our schedule step already ≤ theirs; measures the wrong sheet) |
| `supplier_payment_trade` (H3) | off | P05 **0.6086 ×2** (`7d01d937`, `d098b465`) vs 0.7723 — regression |
| `alt_clause_counter` | off | P18 `a2becc8e` 0.5325 tie (n=1, supplier answered 5.30 db5 with final 5.40 db5); lane says do not merge yet |
| `cost_breakdown_request` | off | no hosted evidence; code merged for later lanes |

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
  35 d + PPI-D351) and r10 (**28.00 / 14 d**). (r2/r11 on sup:70240 differ from saved for A and B alike —
  known replay limitation: saved attachments carry no PDF text.)
- **Flag-off baseline check:** A = v3 replayed on a pure `09e7fe4` worktree (`../ysamet-pure-main`, only
  the replay tool copied in) vs A = v3 on this branch: **130/130 replays, 848 decision rounds
  byte-identical** (supplier choice, sheets, action, refs, body). The merge did not alter v3.

## 4. Verification

- `uv sync --locked` ok (lock unchanged); `uv run ruff check src tests tools` clean.
- `uv run --locked pytest -q` (ARENA_DATA set): **800 passed** in 136 s. One earlier focused-run
  failure of `test_final_robust.py::test_async_worker_crash_still_ends_the_session[0]` did not
  reproduce (passes alone and in the full run; LOG.md already notes this async-simulator timing flake).
- Sandbox (free), `lab run --runner auto`, config `score-push-v4-run.json`, commit `e0bd7a8` clean,
  run `e3d7a4b8-6773-4bf3-ae9a-fbba0080e9ea` `consolidated-sandbox-s1`:

| case | session | score | required | rounds | wall s | timeouts | error |
|---|---|---|---|---|---|---|---|
| D01 | `d096e71ee72d9fe5` | **0.9192** (0.919230949) | 0.9192 | 7 | 5.6 | 0 | None |
| D02 | `c7125f443e453e71` | **0.5239** (0.523861298) | 0.5239 | 9 | 8.7 | 0 | None |

Both attempts `completed`, run `completed`, practice quota untouched (298 left, sandbox is free).

## 5. Ten-case run command (NOT run)

> **Superseded on `codex/release-v5`** (`experiments/RELEASE-v5.md`): the ten-case confirmation and the
> Live Final now use `configs/score-push-v5.json` (= v4 + raw_material fixed-volume ladder), and
> `FINAL_POLICY` in `cli.py` points at v5, so `negotiator run --set final` needs no `--policy-config`.
> The v4 command below is kept for the record; the live command is the v5 one that follows it.

Same launch pattern as the lane runs (`fresh-p05-fp-s1`, `fresh-p18-h1h2-s1`) and the v2 ten-case
confirmation (`score-push-final-confirm`): tracked `lab run`, `configured_agent`, `--runner auto`
(rfq → async, single-supplier → serial), inline JSON config, one repetition, max 10 sessions.

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

Historical v4 form (`codex/consolidated`, `7dba7c0`): same command with `ysamet-consolidated`,
`--name score-push-v4-confirm`, `--config "$(cat configs/score-push-v4-run.json)"` and the v4 hypothesis
("ten-case practice mean >= .7619 projected, P05 .8136, P18 .5325, others = v3").

Run it in the foreground of a long-blocking call (LOG.md 1026: detached `lab run` lost its coordinator).
Working tree must be clean (no `--allow-dirty`), otherwise provenance records a patch. To record the
decision trace add `"trace_dir": "experiments/traces/score-push-v5-confirm"` to the inline config.
Expected from the replay: P01/P02/P03/P04/P07/P10/P11 reproduce v4 (= v3 except P05 .8136 / P18), P05
.8136, P08 .7036 (v5, live n=2), P18 .5870 (v5, live n=2).

For the Live Final `--set final` now defaults to v5 (`FINAL_POLICY`); spelling the config out
(`--policy-config configs/score-push-v5.json`) is harmless and recommended for the log.

## 6. Open merges pending

- `codex/fresh-wave` (`485b60f`): wave time guard (`0a6940e`: stop extending with <2 rounds left,
  round/thread timing trace, LLM timeout audit, `tools/wave_rehearsal.py`) **plus** `485b60f`, a
  re-application of the P05 port already merged here as `e8b0396`. Dry-run `git merge --no-commit
  codex/fresh-wave` on `e0bd7a8` conflicts in `agent.py`, `policy.py` (the duplicate port lands next to
  `alt_clause_counter`/`cost_breakdown_request` additions) and `runner.py` (wave guard vs main's
  final-robust runner). Cleanest path for the follow-up: rebase the wave lane's `0a6940e` alone onto
  `codex/consolidated` (drop `485b60f`), then resolve the single `runner.py` conflict keeping main's
  launch/polling/fallback and the wave guard's timing hooks additive. Nothing on this branch touches
  `runner.py`, so the conflict is wave-vs-main, not wave-vs-consolidated.
- `codex/fresh-p18-db5` is merged at `f93dec1` (flag off); any later lane commit merges cleanly on top.
- ACKS handoff and `git push` deferred until the wave guard is in.

## 7. Blockers / decisions for the 08:30 run

1. ~~`FINAL_POLICY` (cli.py) still = v3~~ — repointed to `score-push-v5.json` on `codex/release-v5`.
2. ~~The wave guard is not in~~ — in since `codex/safety-wave-prewarm` (`f31b4dd`), always-on with a cap.
3. All ten practice cases replayed (172 transcripts): only P05 (14 d re-anchor) and P18 (paced index
   claims) change vs v3; P01/P02/P03/P04/P07/P08/P10/P11 are byte-identical.
