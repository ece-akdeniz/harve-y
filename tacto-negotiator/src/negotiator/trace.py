"""JSONL trace of every decision (format in docs/02-architecture.md)."""

import json
import time
from pathlib import Path


class Tracer:
    def __init__(self, run_dir: Path):
        self.path = Path(run_dir) / "trace.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **fields) -> None:
        line = json.dumps({"t": time.time(), "event": event, **fields}, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
