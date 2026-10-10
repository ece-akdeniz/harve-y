"""Explicit, environment-independent V2 configuration resolution."""

import json
from collections.abc import Mapping
from typing import Any

from .core.models import EffectiveConfig
from .core.serialization import semantic_hash

DEFAULT_SUPPORTED_STRATEGY_IDS = ("baseline-v1", "grounded-exchange-v1")


def resolve_config(
    raw: Mapping[str, Any],
    *,
    supported_strategy_ids: tuple[str, ...] = DEFAULT_SUPPORTED_STRATEGY_IDS,
) -> EffectiveConfig:
    """Validate a declared config block and derive its canonical content hash."""
    if not isinstance(raw, Mapping):
        raise ValueError("config must be a mapping")
    if any(not isinstance(key, str) for key in raw):
        raise ValueError("config keys must be strings")
    if not isinstance(supported_strategy_ids, tuple) or any(
        not isinstance(strategy_id, str) or not strategy_id for strategy_id in supported_strategy_ids
    ):
        raise ValueError("supported_strategy_ids must be a tuple of nonempty strings")

    values = dict(raw)
    supplied_hash = values.pop("config_hash", None)
    if "config_hash" in raw and not isinstance(supplied_hash, str):
        raise ValueError("config_hash must be a SHA-256 digest")
    values["config_hash"] = "0" * 64
    try:
        encoded = json.dumps(values, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        candidate = EffectiveConfig.model_validate_json(encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid V2 configuration") from exc

    if candidate.strategy_id not in supported_strategy_ids:
        raise ValueError(f"unsupported strategy_id: {candidate.strategy_id}")
    config_hash = semantic_hash(candidate.model_dump(mode="json", exclude={"config_hash"}))
    if supplied_hash is not None and supplied_hash != config_hash:
        raise ValueError("config_hash_mismatch")
    result = candidate.model_copy(update={"config_hash": config_hash})
    result._verified_hash = config_hash
    result._verified_strategy_ids = supported_strategy_ids
    return result


def require_verified_config(config: EffectiveConfig) -> EffectiveConfig:
    """Executable construction gate; parsing alone never grants execution trust."""
    if not isinstance(config, EffectiveConfig) or config._verified_hash is None:
        raise ValueError("configuration is not registry verified")
    # Revalidate even model_copy/model_construct inputs before using them.
    checked = resolve_config(config.model_dump(mode="json"),
                             supported_strategy_ids=config._verified_strategy_ids)
    if checked.config_hash != config._verified_hash:
        raise ValueError("verified configuration was changed")
    return config
