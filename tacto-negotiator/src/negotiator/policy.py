"""Versioned, explicit experiment settings. Omitted config preserves legacy behavior."""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

TYPES = {"price_increase", "renewal", "rfq", "bundling", "raw_material", "capacity", "quality"}


@dataclass(frozen=True)
class PolicyConfig:
    version: int = 1
    package_types: tuple[str, ...] = ()
    evidence_types: tuple[str, ...] = ()
    final_offer_risk: str = "legacy"
    preference: str = "default"
    chargeback_steps: int = 1
    preferences: dict[str, str] = field(default_factory=dict)
    cost_neutral_lead_time: bool = False
    package_advice_types: tuple[str, ...] = ()
    clause_variant_types: tuple[str, ...] = ()
    recent_index_window_types: tuple[str, ...] = ()
    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    @classmethod
    def from_dict(cls, data):
        d = dict(data) if isinstance(data, dict) else data
        if not isinstance(d, dict) or set(d) - set(cls.__dataclass_fields__):
            raise ValueError("unknown policy fields")
        if type(d.get("version")) is not int or d["version"] != 1:
            raise ValueError("policy version must be 1")
        for k in ("package_types", "evidence_types", "package_advice_types", "clause_variant_types",
                  "recent_index_window_types"):
            v = d.get(k, [])
            if not isinstance(v, list) or any(not isinstance(x, str) or x not in TYPES for x in v):
                raise ValueError(f"invalid {k}")
            d[k] = tuple(sorted(set(v)))
        if type(d.get("cost_neutral_lead_time", False)) is not bool:
            raise ValueError("cost_neutral_lead_time must be boolean")
        if d.get("final_offer_risk", "legacy") not in ("legacy", "opening_proxy"):
            raise ValueError("invalid final_offer_risk")
        if d.get("preference", "default") not in ("default", "standard_payment", "longer_tenor", "lower_chargeback"):
            raise ValueError("invalid preference")
        steps = d.get("chargeback_steps", 1)
        if type(steps) is not int or not 1 <= steps <= 3:
            raise ValueError("chargeback_steps must be 1, 2 or 3")
        preferences = d.get("preferences", {})
        allowed = {"default", "standard_payment", "longer_tenor", "lower_chargeback"}
        if not isinstance(preferences, dict) or any(
            k not in TYPES or not isinstance(v, str) or v not in allowed for k, v in preferences.items()
        ):
            raise ValueError("invalid case-type preferences")
        return cls(**d)

    def record(self):
        d = asdict(self)
        return {"config": d, "sha256": hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()}


MoveKind = Literal["probe", "trade", "converge", "hold", "accept", "walk_away"]


@dataclass
class Move:
    kind: MoveKind
    supplier_id: str
    sheets: list[dict] = field(default_factory=list)  # complete term sheets
    claims: list = field(default_factory=list)  # claims.Claim
    question: str | None = None  # e.g. "cost_breakdown", "lead_time", "variants"
    accept_sheet_id: str | None = None
    reason: str = ""  # for the trace and the pitch


def next_move(case: dict, thread_state, plan, belief, dossier, time_left_s: float) -> Move:
    raise NotImplementedError
