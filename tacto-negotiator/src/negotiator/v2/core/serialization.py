"""Canonical JSON encoding and semantic content hashing."""

import hashlib
import json
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, TypeAdapter


def decimal_text(value: Decimal) -> str:
    """Normalize without Decimal context rounding; retain source values in models."""
    if not value.is_finite():
        raise ValueError("Decimal must be finite")
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
        # Keep JSON conversion for dates/enums/UUIDs, but normalize typed Decimals first.
        return TypeAdapter(Any).dump_python(_canonical_value(value), mode="json")
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, dict):
        return {key: _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def canonical_json(value: Any) -> bytes:
    """Encode JSON-compatible values as stable, compact UTF-8 bytes."""
    value = _canonical_value(value)
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
