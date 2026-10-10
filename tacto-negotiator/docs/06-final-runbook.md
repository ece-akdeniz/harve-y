# Final runbook

Sunday 11 October 2026, Europe/Berlin. These are target operations. The custom play/run CLI
executes, including async recovery. Full final-machine and wave rehearsal remain unfinished.

## Before Sunday

- [ ] Implementation gates in 10 pass; record exact tested revision, lockfile and config.
- [ ] Hosted D02 clock/queue behavior and acceptance near the cap measured.
- [x] Hosted D02 interruption/restart used the same session and ended with zero timeouts.
  Final-wave recovery permission and full-load rehearsal remain separate gates.
- [ ] Confirm organizer answers on jury criteria, units and permitted crash recovery.
- [ ] Designate one final operator; everyone else observes.

## 08:00 — Sunday overlay

```bash
uv run --locked arena data --out data
```

- [ ] Verify actual base and release paths; Sunday release is expected in data/release-sunday.
- [ ] Check release facts plus CSVs/letters/memo are loaded; base SQLite alone is insufficient.
- [ ] Rebuild versioned dossiers/claims using the implemented prep path. Record hashes/new IDs.
- [ ] Confirm runtime case facts are supported; resolve collisions with provenance.
- [ ] Run targeted regressions. Practice stays on base-package cases, so separately test overlay loading.

## 09:00 — Preflight

- [ ] Exact final machine/network, installed dependencies, model endpoint and configuration.
- [ ] One practice case through the same execution path, with a practice set selected.
- [ ] End-to-end latency measured under intended concurrency, including model retries/limiter waits.
- [ ] Quota, inference balance/rate limits and persistent log space checked.
- [ ] Final-mode waiting behavior checked without forbidden endpoints or premature session opens.

## 10:30–11:30 — Freeze candidate

- [ ] Stop new features at 10:30; fixes need relevant regression evidence.
- [ ] Tests/lint pass; working tree clean; commit and lockfile recorded. Do not auto-upgrade dependencies.
- [ ] Scan tracked files/history with a redacting secret scanner; do not print possible keys with grep.
- [ ] Submit repo access, commit hash, description and slides by 12:00; verify jury can open repo.
- [ ] Power connected, lid open, idle sleep prevented, stable network, logs persist. Ensure only one runner uses the key.
- [ ] Create log directory and launch the **implemented and rehearsed** final command before 12:00.

```bash
# run from tacto-negotiator/
mkdir -p experiments/runs
NEGOTIATOR_JOURNAL="$PWD/experiments/runs/final-journal.jsonl" \
caffeinate -dimsu uv run --locked negotiator run --set final --runner auto \
  --policy-config configs/score-push-v3.json --parallel 10 > experiments/runs/final.log 2>&1
```

This is the one final launch command (the same one LAB_PLAYBOOK gives). `--runner auto` routes
each case by supplier count: more than one supplier -> async runner (package advice disabled for
that case), one supplier -> serial runner; both share one key-wide pace. `--set final` already
defaults to `--runner auto` and `configs/score-push-v3.json`; the flags are spelled out so the
trace and the command agree. The case-list poll backs off and keeps polling on any HTTP (non-403)
or network error, and a crashed decision step falls back (accept the best eligible sheet that
beats the alternative, else repeat our last offer, else walk away; never counter a final offer).
Rehearse with the same flags on the free sandbox (`--set sandbox`) before launch.
This custom launch loads `src/negotiator/AGENTS.md` from the installed package.
Check the initial `run` trace for `runtime_guidance.sha256` and `settings`; both
serial and async custom runners use this same guidance. The starter command
`arena run --agent llm` runs another agent and does not consume this file.
Experimental policies still require an explicit rehearsed `--policy-config`.
Reuse the same journal only for an organizer-permitted restart of that final run. In another terminal:

```bash
tail -f experiments/runs/final.log
```

Verify the process is alive, polling permitted case metadata and waiting for wave 1—not merely
that the shell command started. Dispatch alone does not establish final readiness.

A hosted run on Saturday expired during 403 seconds of clamshell sleep. `caffeinate` prevents
idle sleep, not normal lid-close sleep: keep the lid open or use a verified always-on host.

## Live Final

- No code/model/config/data-policy edits, manual offers or strategic intervention.
- Agent reads permitted case/session/thread metadata only; never events, screen, leaderboard,
  results or their aliases/subpaths. Human spectator viewing must not enter agent context.
- Read actual seconds_left and running-wave state; do not assume continuous 8-minute waves.
- If the process dies, follow the organizer-confirmed recovery policy: same revision/config,
  reconcile existing sessions and pending IDs, no duplicate session or move. Do not improvise
  recovery or change strategy. Escalate organizer-side failures to the desk.

## After final closes

Fetch released replays/backoffice, select an honest measured example, and load it into the
existing viewer. Slides were frozen at 12:00: confirm whether live result display is allowed;
do not assume you may edit slides afterward. Keep a pre-freeze practice replay as backup.
