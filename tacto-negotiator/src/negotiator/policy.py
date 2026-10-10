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
    cost_target_types: tuple[str, ...] = ()
    cost_target_index_clause: bool = False
    clause_variant_types: tuple[str, ...] = ()
    rfq_nonleading_hold: bool = False
    rfq_final_guard: bool = False
    # Case types whose opening and later packages keep the supplier's standard (quote PDF)
    # payment days when that is a listed option; price is still scheduled by buyer C.
    standard_payment_types: tuple[str, ...] = ()
    rfq_supplier_lead_time: bool = False
    rfq_rival_offer: bool = False
    rfq_supplier_payment: bool = False
    rfq_rival_offer_history: bool = False
    rfq_undercut_reanchor: bool = False
    rfq_data_claims: bool = False
    rfq_data_claims_stack: bool = False
    # Case types whose evidence uses only public index windows ending at the latest month.
    recent_index_window_types: tuple[str, ...] = ()
    rival_quote_types: tuple[str, ...] = ()
    index_window_types: tuple[str, ...] = ()
    cost_target_posterior: float = 0.0  # s_max of the in-session supplier-cost posterior; 0 = off
    # Case types whose opening takes the longest contract term among options of equal buyer C
    # (e.g. a commitment beyond the cost horizon) and keeps it against equal-cost shortening.
    longer_tenor_types: tuple[str, ...] = ()
    # Per case type opening anchor (fraction below the supplier's price); others use the agent's.
    anchor_by_type: dict[str, float] = field(default_factory=dict)
    # Case types whose offers state, from public facts, the volume a kit moves to the supplier
    # (kit memo quantities x need, current sourcing quota, forecast IDs, capacity note).
    bundle_volume_types: tuple[str, ...] = ()
    # Subset of bundle_volume_types whose later offers answer the supplier's volume question with the
    # case's fixed volume over the offered term and, if it has a pricing committee, the approval path.
    bundle_commitment_types: tuple[str, ...] = ()
    # Per case type number of buyer rounds over which the price schedule reaches the
    # supplier's price (faster convergence before a supplier's final offer); others use the agent's.
    rounds_by_type: dict[str, int] = field(default_factory=dict)
    # Case types where, once the supplier holds its standing price, we offer once to drop the
    # chargeback at the price that leaves the supplier's value unchanged (arena_kit supplier_value
    # with the ppm from the supplier's own quote) - only if it lowers our C.
    value_swap_types: tuple[str, ...] = ()
    # Consecutive unchanged standing replies (same package and price) that trigger the swap.
    value_swap_holds: int = 1
    # Fraction of the way from our last price to the value-equivalent ceiling the swap offers
    # (1.0 = the ceiling itself); later rounds concede toward it on the swapped package.
    value_swap_split: float = 1.0
    # Case types whose offers, once a supplier with a pricing committee (its own dossier note) holds
    # its standing price, ask it to put the proposal to that committee when our ask is beyond its band.
    committee_escalation_types: tuple[str, ...] = ()

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
        for k in (
            "package_types",
            "evidence_types",
            "package_advice_types",
            "cost_target_types",
            "clause_variant_types",
            "standard_payment_types",
            "recent_index_window_types",
            "rival_quote_types",
            "index_window_types",
            "longer_tenor_types",
            "bundle_volume_types",
            "bundle_commitment_types",
            "value_swap_types",
            "committee_escalation_types",
        ):
            v = d.get(k, [])
            if not isinstance(v, list) or any(not isinstance(x, str) or x not in TYPES for x in v):
                raise ValueError(f"invalid {k}")
            d[k] = tuple(sorted(set(v)))
        for k in ("cost_neutral_lead_time", "cost_target_index_clause", "rfq_nonleading_hold", "rfq_final_guard",
                  "rfq_supplier_lead_time", "rfq_rival_offer", "rfq_supplier_payment", "rfq_rival_offer_history",
                  "rfq_undercut_reanchor", "rfq_data_claims", "rfq_data_claims_stack"):
            if type(d.get(k, False)) is not bool:
                raise ValueError(f"{k} must be boolean")
        post = d.get("cost_target_posterior", 0.0)
        if isinstance(post, bool) or not isinstance(post, (int, float)) or not 0 <= post <= 1:
            raise ValueError("cost_target_posterior must be a number in [0, 1]")
        d["cost_target_posterior"] = float(post)
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
        anchors = d.get("anchor_by_type", {})
        if not isinstance(anchors, dict) or any(
            k not in TYPES or type(v) not in (int, float) or not 0 <= v <= 0.4 for k, v in anchors.items()
        ):
            raise ValueError("invalid anchor_by_type")
        d["anchor_by_type"] = {k: float(v) for k, v in anchors.items()}
        rounds = d.get("rounds_by_type", {})
        if not isinstance(rounds, dict) or any(
            k not in TYPES or type(v) is not int or not 1 <= v <= 12 for k, v in rounds.items()
        ):
            raise ValueError("invalid rounds_by_type")
        d["rounds_by_type"] = dict(rounds)
        holds = d.get("value_swap_holds", 1)
        if type(holds) is not int or not 1 <= holds <= 3:
            raise ValueError("value_swap_holds must be 1, 2 or 3")
        split = d.get("value_swap_split", 1.0)
        if isinstance(split, bool) or not isinstance(split, (int, float)) or not 0 < split <= 1:
            raise ValueError("value_swap_split must be a number in (0, 1]")
        d["value_swap_split"] = float(split)
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
