"""Which move to make this round (docs/03-playbook.md). Pure code, no LLM."""

from dataclasses import dataclass, field
from typing import Literal

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
