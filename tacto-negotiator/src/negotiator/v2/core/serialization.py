"""Canonical JSON encoding and semantic content hashing."""

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    """Encode JSON-compatible values as stable, compact UTF-8 bytes."""
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("value is not valid canonical JSON") from exc
    return encoded.encode("utf-8")


def semantic_hash(value: Any) -> str:
    """Return the SHA-256 hex digest of canonical JSON bytes."""
    return hashlib.sha256(canonical_json(value)).hexdigest()
