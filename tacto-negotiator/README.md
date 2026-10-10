# tacto-negotiator

Buyer agent for the Tacto Negotiation Arena, EHL Grand Finale, 10–11 October 2026.

**Status: integrated deterministic agent with serial and async runners.** `prep`, `play`, `run`
and `report` execute. Shared closing checks, journalled recovery, a claim bank and opt-in
claim delivery are implemented. Hosted P01: mechanical baseline 80.0/100; claims-only candidate
92.8/100 in two observed runs. A hosted D02 interruption/restart completed the same session
without timeouts. These are development measurements, not final-readiness certification.
See [the hacking guide](docs/README.md) and [experiment results](experiments/LOG.md).

## Shared experiment dashboard

Run agents on each teammate's laptop and publish experiments to a password-protected dashboard
hosted on one laptop through VS Code port forwarding. Includes code/configuration provenance,
per-case comparisons, local buffering and read-only arena-history import.

```bash
uv run --locked negotiator lab init
uv run --locked negotiator lab serve --secure-cookies
uv run --locked negotiator lab run --help
```

See [the host and teammate setup guide](docs/12-experiment-dashboard.md). The lab is development
tooling; it does not replace or complete the final negotiation runtime.

## Objective

Maximize normalized case scores reliably, then demonstrate procurement judgment with an
evidence-linked replay. Code evaluates complete packages and renders approved offers and claims.
Model interpretation/writing remains an optional, unimplemented extension. One coordinator closes each case. Overall jury criteria remain
unconfirmed; a high track score supports, but does not guarantee, an overall title.

## Setup

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). Run from the `tacto-negotiator` directory:

```bash
uv sync --locked
```

Copy `.env.example` to `.env` only if `.env` does not already exist. Fill in the team arena key
and chosen model credentials locally. Never log or commit credentials. The official arena CLI
loads `.env`; standalone research scripts read shell environment variables.

```bash
uv run --locked arena --help
uv run --locked negotiator --help
uv run --locked pytest -q
uv run --locked ruff check .
```

With the arena key configured, these use the **official starter**, not our custom agent:

```bash
uv run --locked arena me
uv run --locked arena data --out data
export ARENA_DATA="$PWD/data/package"
uv run --locked arena cases --set sandbox
uv run --locked arena play case:D01 --agent naive --data "$ARENA_DATA" -v
uv run --locked arena play case:D02 --agent naive --data "$ARENA_DATA" -v
```

Check that the data path contains `world.sqlite` and `facts.json`; use the actual unpacked path
if different. D01/D02 are sandbox cases. Hosted team keys come from
[the application page](https://arena.tacto.ai/apply), not `arena register`.
Record the D02 baseline; the starter's serial RFQ loop may time out.

## Local research tools

```bash
export ARENA_DATA="$PWD/data/package"
uv run --locked python tools/build_dossiers.py
uv run --locked python tools/index_justified.py
uv run --locked python tools/lever_sensitivity.py
```

These do not start hosted sessions. Dossiers go to `experiments/dossiers.json`. They are
prototypes: the dossier tool reads the base SQLite, not the Sunday overlay; “justified” in the
index output means a partial cost proxy; the sensitivity tool chooses an illustrative baseline.
See [research limitations](docs/01-research.md).

## Custom commands

```bash
uv run --locked negotiator prep
uv run --locked negotiator play case:D01 --runner serial -v
uv run --locked negotiator play case:D02 --runner async -v
uv run --locked negotiator run --set practice --parallel 10
uv run --locked negotiator run --set final --parallel 10
uv run --locked negotiator report experiments/runs/REPLACE_WITH_RUN_ID
```

Do not use these for final operations until the [implementation gates](docs/10-implementation-checklist.md)
and [runbook](docs/06-final-runbook.md) pass on the final machine.

Claims are **off by default**. Enable only for a planned experiment; currently they apply to
single-supplier price-increase cases. Supplier estimates and payment MESOs also remain opt-in.
For a quota-budgeted P01 claims comparison:

```bash
caffeinate -i uv run --locked python tools/compare.py --mode practice --practice --budget 4 \
  --cases P01 -n 2 --baseline WORKTREE --candidate WORKTREE \
  --baseline-env NEGOTIATOR_CLAIMS=0 NEGOTIATOR_ESTIMATES=0 NEGOTIATOR_MESO=0 \
  --candidate-env NEGOTIATOR_CLAIMS=1 NEGOTIATOR_ESTIMATES=0 NEGOTIATOR_MESO=0
```

For a free hosted interruption/restart rehearsal, keep the lid open and run
`caffeinate -i uv run --locked python tools/resume_probe.py`. This intentionally interrupts its
own D02 child process, then resumes the persisted journal. Never use that script on the final.

Use `NEGOTIATOR_JOURNAL=/absolute/path/to/journal.jsonl` with `--runner async` to resume an
existing run; a new journal opens a new practice session. Keep experiment journals separate.

## Configuration

| Variable | Use |
|---|---|
| `ARENA_URL`, `ARENA_API_KEY` | Hosted base URL and team key, shared by the team |
| `ARENA_DATA` | Base package root; export explicitly for research scripts |
| `ARENA_RELEASE` | Optional Sunday overlay path, supported by kit DataPackage |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_EFFORT` | Model selection; measure score and tail latency |
| `LLM_BASE_URL`, `LLM_API_KEY`, `ANTHROPIC_API_KEY` | Provider-specific configuration |
| `PREP_LLM_MODEL` | Planned optional offline model |
| `NEGOTIATOR_MOVE_BUDGET_S` | Proposed buyer-work target, default 35 seconds; not HTTP timeout |
| `NEGOTIATOR_CLAIMS` | `1` enables checked claims; default off |
| `NEGOTIATOR_ESTIMATES` | `1` enables dossier cost estimates; default off pending calibration |
| `NEGOTIATOR_MESO` | `1` enables payment variants; default off after D02 regression |
| `NEGOTIATOR_JOURNAL` | Explicit persistent journal for async resume |
| `NEGOTIATOR_LOG_DIR` | Trace location, default `experiments/runs` |

The current Settings class reads only part of the planned configuration; wiring it is a build
task. Local settings never override the arena's per-thread or per-wave limits.


## Shared session history

The parent repository tracks Entire settings and Codex/Cursor hooks. Install Entire locally,
then run `entire enable` from the parent repository to install local Git hooks. Run
`entire status` to verify capture and sync; hooks skip harmlessly when the CLI is absent.
Checkpoint trailers link code commits to agent sessions. `entire checkpoint list` and
`entire checkpoint explain <checkpoint-id>` retrieve context for teammates. Secrets belong
only in ignored `.env` files; review checkpoint redaction before pushing session history.

### Staged policy experiments

The default policy remains the measured baseline behavior. Opt in explicitly:

```sh
uv run --locked negotiator play case:P04 --runner async --policy-config configs/packages.json
uv run --locked negotiator play case:P11 --runner async --policy-config configs/packages-evidence.json
```

These commands consume one hosted practice session each. Use the budgeted manifest runner
in [the staged experiment contract](docs/13-staged-experiments.md) for comparisons and stop
checks. Keep estimates and generic MESOs disabled during this cycle. Never use leaderboard
scores, historical Cbest or diagnostic target prices as runtime inputs.
