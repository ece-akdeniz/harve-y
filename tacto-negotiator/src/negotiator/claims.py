"""Claim bank: arguments with exact figures, verified locally before sending.

Rules (kit api.md "What counts"): figure and ID in the same sentence; ≤ 3 checked per message;
each ID once per case (rival quotes once per supplier in RFQs - and citing reveals them);
tolerance ±0.5 pp for %, else ±0.5 % (min 0.01). Unknown ID or wrong figure = contradicted.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Claim:
    kind: str  # index_change | rival_quote | scorecard | po_trend | forecast | should_cost | news | notice
    ids: tuple[str, ...]
    figure: float | None
    unit: str  # "%", "EUR", "ppm", "days", ""
    sentence: str  # one sentence with the figure next to the IDs
    supplier_id: str | None = None
    part_id: str | None = None
    direction: str = "buyer"  # does it help the buyer's position


def build_bank(package) -> list[Claim]:
    """Pre-compute candidate claims: index windows per cost driver (12-month and best window),
    weighted decomposition per part, scorecard means, PO price trends, should-cost, notice periods."""
    raise NotImplementedError


def verify(claim: Claim, facts: dict) -> bool:
    """Recompute the claim's figure from `facts` (package + release + case facts) within tolerance."""
    raise NotImplementedError


def pick(case: dict, supplier_id: str, traits: set[str], used: set[str], k: int = 2) -> list[Claim]:
    """Best ≤ k unused claims for this supplier: helpful direction, relevant to its cost drivers,
    skipping hedged inputs; never more than 3 checked claims per message."""
    raise NotImplementedError
