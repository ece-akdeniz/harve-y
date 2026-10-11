#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ "${1:-}" != "--check" && "${1:-}" != "--run" || $# -ne 1 ]]; then
  echo "usage: tools/final_launch.sh --check|--run" >&2
  exit 2
fi

if [[ "$(git branch --show-current)" != "main" || -n "$(git status --porcelain)" ]]; then
  echo "Use a clean main worktree for the final." >&2
  exit 1
fi

if [[ ! -x .venv/bin/negotiator || ! -d data/release-sunday || ! -f configs/score-push-v6-all-cases.json ]]; then
  echo "Install locked dependencies and verify the Sunday data and V6 policy." >&2
  exit 1
fi

.venv/bin/python - <<'PY'
import os
import sys

from dotenv import load_dotenv

load_dotenv(".env")
required = ("ARENA_URL", "ARENA_API_KEY", "LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")
missing = [name for name in required if not os.environ.get(name)]
if missing:
    print("Missing configuration: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
if os.environ["ARENA_URL"].rstrip("/") != "https://arena.tacto.ai":
    print("ARENA_URL must point to the live Arena, not the local simulator.", file=sys.stderr)
    sys.exit(1)
if os.environ["LLM_PROVIDER"] != "openai" or not os.environ["LLM_BASE_URL"].startswith("https://"):
    print("The rehearsed V6 policy requires a configured HTTPS OpenAI-compatible endpoint.", file=sys.stderr)
    sys.exit(1)
PY

if [[ "${1}" == "--check" ]]; then
  echo "Final launch prerequisites are present; no Arena request was made."
  exit 0
fi

mkdir -p experiments/runs
export NEGOTIATOR_JOURNAL="$project_dir/experiments/runs/final-journal.jsonl"
command=("$project_dir/.venv/bin/negotiator" run --set final --waves 5 --runner auto
  --policy-config configs/score-push-v6-all-cases.json --parallel 10)

if [[ "$(uname -s)" == "Linux" ]]; then
  exec systemd-inhibit --what=idle:sleep --mode=block "${command[@]}" \
    >> experiments/runs/final.log 2>&1
elif [[ "$(uname -s)" == "Darwin" ]]; then
  exec caffeinate -dimsu "${command[@]}" >> experiments/runs/final.log 2>&1
else
  echo "No verified sleep inhibitor for this operating system." >&2
  exit 1
fi
