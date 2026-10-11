# harve/y

An AI buyer agent for the Tacto Negotiation Arena. The agent uses supplier and case evidence to prepare a complete offer, applies code checks before sending, and uses bounded model assistance when eligible.

## Setup

Use Python 3.12 and `uv`. From this directory:

```bash
uv sync --locked
```

Set the following variables in an untracked `.env` file or in the shell environment. Do not put credentials in the repository.

- `ARENA_URL` — Arena endpoint; defaults to the live Arena.
- `ARENA_API_KEY` — team key for Arena access.
- `LLM_PROVIDER` — must match the configured OpenAI-compatible endpoint.
- `LLM_BASE_URL` — HTTPS model API endpoint.
- `LLM_MODEL` — model name.
- `LLM_API_KEY` — model API credential.

## Run the final agent

On a clean `main` checkout with the Sunday release data present, check setup without contacting Arena:

```bash
bash tools/final_launch.sh --check
```

Start the five-wave final runner:

```bash
bash tools/final_launch.sh --run
```

The launcher uses the rehearsed V6 policy, records a persistent journal and writes logs to `experiments/runs/final.log`. Keep the machine awake and connected until all waves finish.
