"""Term-sheet economics over the case's term options, using arena_kit.cost.

All values are C in EUR from `arena_kit.cost.total_cost(case, terms, standard, supplier)`.
"""

import itertools
import math
from dataclasses import dataclass, field

from arena_kit.cost import complete_offer, must_haves_ok, total_cost

from .economics import InfeasiblePackage

MAX_PACKAGE_COMBINATIONS = 4096


def option_combinations(options, fields):
    if math.prod(len(options[field]) for field in fields) > MAX_PACKAGE_COMBINATIONS:
        raise InfeasiblePackage("option space exceeds bounded search; retain checked standing offers")
    return itertools.product(*(options[field] for field in fields))


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
    for combo in option_combinations(options, fields):
        terms = {**base, **dict(zip(fields, combo, strict=True))}
        if not must_haves_ok(case, terms, standard):
            continue
        c = total_cost(case, terms, standard, supplier)
        # When chargebacks eliminate residual quality cost, do not demand a
        # stricter PPM promise for no modeled buyer benefit.
        tie = (-(terms.get("ppm_commitment") or 0), terms.get("chargeback_eur_per_complaint") or 0)
        best_tie = (-(best.get("ppm_commitment") or 0), best.get("chargeback_eur_per_complaint") or 0)
        if c < best_c or (c == best_c and tie < best_tie):
            best, best_c = terms, c
    return best


def trade_packages(case, primary, standard=None):
    """Up to three distinct, valid packages at no greater modeled cost.

    Prices are proposed indifference prices, not predictions of acceptance.
    Relationship-sensitive goals need supplier-specific valuation; do not apply
    this linear price search to those cases.
    """
    packages = [primary]
    if case["buyer"].get("category_goal") in {"secure_supply", "stabilise"}:
        return packages
    target = total_cost(case, primary, standard)
    options = case.get("term_options") or {}
    variants = []
    for term_field in ("chargeback_eur_per_complaint", "payment_days", "index_clause", "contract_months"):
        if term_field not in case["negotiable"]:
            continue
        values = options.get(term_field) or []
        if term_field == "chargeback_eur_per_complaint":
            values = [v for v in reversed(values) if 0 < v < primary.get(term_field, 0)]
        elif term_field == "payment_days":
            values = [v for v in values if v < primary.get(term_field, 0)]
        elif term_field == "index_clause":
            values = [v for v in reversed(values) if v is not None]
        else:
            values = [v for v in values if v >= 12 * case["buyer"]["horizon_years"]]
        variants.extend({**primary, term_field: v} for v in values[:1] if v != primary.get(term_field))
    for variant in variants:
        low, high = 0.01, primary["unit_price"]
        if total_cost(case, {**variant, "unit_price": low}, standard) > target:
            continue
        for _ in range(40):
            mid = (low + high) / 2
            if total_cost(case, {**variant, "unit_price": mid}, standard) <= target:
                low = mid
            else:
                high = mid
        variant["unit_price"] = int(low * 100) / 100
        if (variant["unit_price"] > 0 and must_haves_ok(case, variant, standard)
                and total_cost(case, variant, standard) <= target + 0.01 and variant not in packages):
            packages.append(variant)
        if len(packages) == 3:
            break
    return packages


def payment_breakeven_pct(case: dict, from_days: int, to_days: int) -> float:
    """Price discount (%) that makes paying faster neutral: r · Δdays / 360 · 100."""
    r = case["buyer"]["interest_rate"]
    return r * (from_days - to_days) / 360 * 100
