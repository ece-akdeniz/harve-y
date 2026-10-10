"""Locate the data package for the research tools: ARENA_DATA, data/package, or a kit clone."""

import os
import sqlite3
from pathlib import Path

CANDIDATES = [
    os.environ.get("ARENA_DATA", ""),
    "data/package",
    "/tmp/nak/data",
]


def package_dir() -> Path:
    for c in CANDIDATES:
        if c and (Path(c) / "world.sqlite").is_file():
            return Path(c)
    raise SystemExit("data package not found: run `uv run arena data` or set ARENA_DATA")


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{package_dir() / 'world.sqlite'}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db
