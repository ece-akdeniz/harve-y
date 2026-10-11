# harve/y

An AI buyer agent for the Tacto Negotiation Arena. It uses supplier and case evidence to prepare complete offers, checks decisions in code, and uses bounded model assistance when eligible.

## Setup

Use Python 3.12 and `uv`. From the repository root:

```bash
cd tacto-negotiator
uv sync --locked
```

Configure these environment variables in an untracked `.env` file or in the shell. Do not commit credentials.

- `ARENA_URL` — Arena endpoint; defaults to the live Arena.
- `ARENA_API_KEY` — team key for Arena access.
- `LLM_PROVIDER` — provider matching the model endpoint.
- `LLM_BASE_URL` — HTTPS OpenAI-compatible endpoint.
- `LLM_MODEL` — model name.
- `LLM_API_KEY` — model API credential.

## Run

Check local setup without contacting Arena:

```bash
bash tools/final_launch.sh --check
```

Start the five-wave final agent:

```bash
bash tools/final_launch.sh --run
```

The launcher uses the rehearsed V6 policy, records a persistent journal, and writes logs to `experiments/runs/final.log`. Keep the machine awake and connected until the run finishes.
