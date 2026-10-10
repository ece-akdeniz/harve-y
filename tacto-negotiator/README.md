# tacto-negotiator

Buyer agent for the Tacto Negotiation Arena, EHL Grand Finale, 10–11 October 2026.

**Status: PackageAgent v0 runs through the official kit.** `play` and `run` dispatch
negotiations; `prep` and `report` remain placeholders. The custom async runtime, persistent
recovery and full closing guards remain unfinished. Start with [the hacking guide](docs/README.md)
and [hosted experiment results](experiments/LOG.md).

## Objective

Maximize normalized case scores reliably, then demonstrate procurement judgment with an
evidence-linked replay. Code evaluates complete packages; a bounded model interprets replies
and explains approved moves. One coordinator closes each case. Overall jury criteria remain
unconfirmed; a high track score supports, but does not guarantee, an overall title.

## Setup

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). Run from the repository root:

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

## Custom commands — partial implementation

```bash
uv run --locked negotiator prep
uv run --locked negotiator play case:D01 -v
uv run --locked negotiator run --set practice --parallel 10
uv run --locked negotiator run --set final --parallel 10
uv run --locked negotiator report experiments/runs/REPLACE_WITH_RUN_ID
```

Do not use these for final operations until the [implementation gates](docs/10-implementation-checklist.md)
and [runbook](docs/06-final-runbook.md) pass on the final machine.

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
| `NEGOTIATOR_LOG_DIR` | Trace location, default `experiments/runs` |

The current Settings class reads only part of the planned configuration; wiring it is a build
task. Local settings never override the arena's per-thread or per-wave limits.
