# Experiments and quota

## Budget and data split

Practice allowance is 200 sessions per rolling 24 hours per team, less prior use. Saturday
13:00→Sunday12:00 is only 23 hours: those sessions do not expire before freeze. Read /v1/me
and record consumption before each batch. Sandbox D01/D02 does not use practice quota;
local arena-sim checks protocol, not hosted persuasion.

Select a representative development set and a frozen holdout before tuning. Example: six
hosted cases for development, four for validation, balanced by type/goal where possible.
Do not mine holdout replays to tune policy; once you do, label them development cases.
Hidden evaluation remains necessary because ten public cases cannot establish generalization.

| Allocation | Maximum sessions |
|---|---:|
| B0: naive and kit LLM baselines, all ten cases | 20 |
| B1: safe custom baseline, two runs on six development cases | 12 |
| A1–A4: four chosen comparisons, both arms twice on six cases | 96 |
| H1: baseline versus selected candidate, twice on four holdouts | 16 |
| R1: full rehearsal on all ten | 10 |
| Protected reserve: regressions, refresh, preflight | 46 |
| Total ceiling, assuming zero prior use | 200 |

This is a ceiling, not a target. Subtract prior consumption; reduce ablations before touching
reserve. Never rerun a batch merely to improve the displayed best score.

## Experiment order

1. **S0 sandbox timing:** timestamp reply receipt, decision, request transmission and response;
   compare serial and concurrent D02 schedules. Record rounds/timeouts, queuing and in-flight behavior.
2. **B0/B1 baselines:** establish complete cost breakdowns and failure rates. Safe runner first.
3. **A1 multiple offers:** one package versus two or three equivalent-cost feasible packages.
4. **A2 evidence:** guarded baseline versus typed relevant claims and supplier hypotheses.
5. **A3 economics:** improved supplier-estimate sensitivity versus baseline estimates; keep
   fundamental validation enabled in both arms.
6. **A4 choose one:** adaptive closing, cost-breakdown request, or model comparison—based on
   observed failures, not the number of features available.
7. **H1 holdout**, then **R1 rehearsal** with simultaneous cases and the intended wave cap.

Randomize/interleave arm order. Fix data version, model/config and case set. Several repeats
are directional evidence, not statistical certainty. Preserve an untouched baseline.

## Metrics and promotion

Record run IDs, commit/config/data hashes, quota before/after, per-case score, mean/minimum,
must-have failures, timeouts, claim outcomes, completion latency, model p50/p95 and fallbacks.
Compare normalized case scores, not absolute savings or deal rate alone. Final aggregation is
mean case score per wave, summed across waves.

Report realized C components and aggregate c_deal−c_best separately. An optimal component
breakdown cannot be inferred from scalar c_best. Use paired package/intervention deltas for
component diagnostics, clearly labeled as our analysis.

Promote only when measured scores improve without new correctness/reliability failures. Inspect
per-case losses; retain baseline if the apparent gain is noisy or latency regresses. Template
fallbacks and zero observed failures are measurements, not guarantees.

## Required failure checks (local/fake transport unless explicitly scheduled)

- Stale or invalid offer on agreed; better eligible offer on another thread.
- Simultaneous accept/walk proposals; no duplicate close or POST after unresolved outcome.
- Model timeout, slow attachment, 429, 5xx and disconnect; original move ID reused.
- Restart with pending request; authoritative rounds include timeout rounds.
- Imminent wave cap; queued close; no assumption HTTP cancellation cancels server work.
- Sunday overlay, unknown supplier, missing index month and non-unit price_unit.

## Tooling (run from the project root)

| Step | Command | Notes |
|---|---|---|
| Quota before/after a batch | `uv run --locked python tools/quota.py --planned N` | `/v1/me` used/left plus local practice ledger; exit 1 when left <= 46 + N |
| Baseline vs candidate | `uv run --locked python tools/compare.py --cases S01 S02 S03 -n 2` | default sim on :8030 (auto-started), HEAD vs working tree |
| Sandbox comparison | `... compare.py --mode sandbox --cases D01 D02 --baseline <ref> --candidate WORKTREE` | hosted, no practice quota |
| Practice comparison | `... compare.py --mode practice --practice --budget 8 --cases P01 P02 -n 1` | refuses above budget or into the reserve |
| Run summary | `uv run --locked negotiator report <run_dir> [--json]` | per case score, terms, C, gap, rounds, decisions, guards |
| Replay page | `uv run --locked python tools/replay_viewer.py <run_dir> [--fetch]` | static `replay.html`; `--fetch` stores `hosted-<sid>.json` (read-only GETs) |

`compare.py` records commit, dirty-diff hash, env overrides and args per arm, data and lock
hashes, and interleaves arm order (seeded). Per-arm env: `--baseline-env K=V`, extra args:
`--candidate-args "..."`, both arms: after `--` (e.g. `-- --runner async`). Each run uses its
own `NEGOTIATOR_LOG_DIR` under `experiments/runs/compare/<stamp>/`; a commit arm runs in a
temporary git worktree with `data/` linked in. The markdown summary is appended to LOG.md
(`--no-log` to skip); fill in the decision line by hand.

Viewer sources: our decisions and result come from `trace.jsonl` (cited as `trace.jsonl#L<n>`),
supplier messages and the arena cost breakdown from hosted session dumps (cited by message id
or file). Arena "reasons" are spectator data: analysis and pitch only, never agent input.
To show C components for every run, decisions/results should log `cost_breakdown`/`components`
and a `session` event with the session id; the report picks them up when present.

Save all runs in experiments/runs and summarize in experiments/LOG.md. Replay mining is for
practice development runs; never feed spectator pages into the final agent. R1 is rehearsal;
use unique names for additional experiments.
