"""Term-sheet economics over the case's term options, using arena_kit.cost.

All values are C in EUR from `arena_kit.cost.total_cost(case, terms, standard, supplier)`.
"""

import itertools
from dataclasses import dataclass, field

from arena_kit.cost import complete_offer, must_haves_ok, total_cost


@dataclass
class Plan:
    c_alt: float  # alternative's C (inf if none)
    c_open: float  # cheapest opening quote's C
    reservation_c: float  # walk-away: never accept above this
    target_c: float  # where we aim
    best_nonprice: dict = field(default_factory=dict)  # cheapest values for non-price fields
    concession_path: list[float] = field(default_factory=list)  # target C per round
    supplier_estimate: dict = field(default_factory=dict)  # full_cost, interest_rate, standard


def plan(case: dict, standard_terms: dict, dossier=None) -> Plan:
    """Reservation, target and concession path. In stabilise/secure_supply, include the
    relationship term with a supplier estimate (should-cost ± sensitivity)."""
    raise NotImplementedError


def meso(case: dict, anchor: dict, c_target: float, n: int = 3) -> list[dict]:
    """n complete term sheets with (nearly) equal C for us but different mixes
    (price-heavy, payment-heavy, term/volume-heavy). Uses arena_kit.cost.complete_offer."""
    raise NotImplementedError


def alternative_cost(case: dict) -> float:
    alt = case["buyer"].get("alternative") or {}
    terms = alt.get("terms") or {}
    return total_cost(case, terms) if terms.get("unit_price") else float("inf")


def best_terms(case: dict, unit_price: float, standard: dict | None = None, supplier=None) -> dict:
    """Complete term sheet at `unit_price` whose non-price fields minimise C and keep the
    must-haves. Fields without listed options keep the buyer's plan (`complete_offer`)."""
    base = complete_offer(case, {"unit_price": unit_price})
    options = case.get("term_options") or {}
    fields = [f for f in case["negotiable"] if f != "unit_price" and options.get(f)]
    best, best_c = base, float("inf")
    for combo in itertools.product(*(options[f] for f in fields)):
        terms = {**base, **dict(zip(fields, combo, strict=True))}
        if not must_haves_ok(case, terms, standard):
            continue
        c = total_cost(case, terms, standard, supplier)
        if c < best_c:
            best, best_c = terms, c
    return best


def payment_breakeven_pct(case: dict, from_days: int, to_days: int) -> float:
    """Price discount (%) that makes paying faster neutral: r · Δdays / 360 · 100."""
    r = case["buyer"]["interest_rate"]
    return r * (from_days - to_days) / 360 * 100
