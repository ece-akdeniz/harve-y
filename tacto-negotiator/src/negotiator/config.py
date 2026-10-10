"""Settings from the environment (.env is loaded if present)."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    arena_url: str
    api_key: str
    data_dir: Path
    log_dir: Path
    move_budget_s: float
    llm_provider: str
    llm_model: str
    prep_model: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass
        return cls(
            arena_url=os.environ.get("ARENA_URL", "https://arena.tacto.ai").rstrip("/"),
            api_key=os.environ.get("ARENA_API_KEY", ""),
            data_dir=Path(os.environ.get("ARENA_DATA", "data/package")),
            log_dir=Path(os.environ.get("NEGOTIATOR_LOG_DIR", "experiments/runs")),
            move_budget_s=float(os.environ.get("NEGOTIATOR_MOVE_BUDGET_S", "35")),
            llm_provider=os.environ.get("LLM_PROVIDER", "anthropic"),
            llm_model=os.environ.get("LLM_MODEL", ""),
            prep_model=os.environ.get("PREP_LLM_MODEL") or None,
        )
