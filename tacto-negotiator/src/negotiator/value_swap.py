"""Value-equivalent chargeback swap (opt-in: policy.value_swap_types).

A supplier holding its price on a package with a chargeback values dropping that chargeback at
(quoted ppm / 1e6) x chargeback per unit. Priced with `arena_kit.cost.supplier_value`, using only the
supplier's own quote (standard terms and its quoted ppm), the swap keeps the supplier's value and
lowers our C when our quality cost of the lower chargeback is smaller than the price it frees.
"""

import math

from arena_kit.cost import closing_terms, complete_offer, must_haves_ok, supplier_value, total_cost

from .evaluator import eligible_sheets, nonprice


def quoted_ppm(events, standard):
    """The supplier's own quoted defect rate: its standard ppm commitment, else the ppm commitment
    of its first priced sheet (the quote). None when it never quoted one."""
    if standard.get("ppm_commitment"):
        return standard["ppm_commitment"]
    for m in events:
        if m.get("from") == "buyer":
            continue
        for sheet in m.get("term_sheets") or []:
            ppm = (sheet.get("terms") or {}).get("ppm_commitment")
            if ppm:
                return ppm
    return None


def holds(case, events, supplier=None):
    """How many consecutive supplier replies, counted back from the latest, repeat the latest
    standing package and price (0 when the latest moved)."""
    standing = []
    for i, m in enumerate(events):
        if m.get("from") != "buyer" and m.get("term_sheets"):
            sheets = eligible_sheets(case, events[: i + 1], supplier)
            standing.append(sheets[0][2] if sheets else None)
    if not standing or standing[-1] is None:
        return 0
    last, n = standing[-1], 0
    for prev in reversed(standing[:-1]):
        if (prev is None or nonprice(case, prev) != nonprice(case, last)
                or abs(prev["unit_price"] - last["unit_price"]) > 0.005):
            break
        n += 1
    return n


def value_price(case, terms, target_value, supplier):
    """Unit price (rounded up to the cent) at which `terms` are worth `target_value` to the supplier;
    supplier_value is linear in price with the other terms fixed."""
    v0 = supplier_value(case, {**terms, "unit_price": 0.0}, supplier)
    v1 = supplier_value(case, {**terms, "unit_price": 1.0}, supplier)
    if v1 - v0 <= 1e-9:
        return None
    price = (target_value - v0) / (v1 - v0)
    return math.ceil(round(price * 100, 6)) / 100


def swap(case, events, standing_terms, standard, buyer_supplier=None, last_price=None, split=1.0):
    """(terms, trace) of the cheapest-by-C package that lowers the chargeback of the standing
    sheet at the supplier's value-equivalent price, else (None, trace). The value-equivalent price
    is a ceiling; with `last_price` (our previous ask) and `split` < 1 the offer goes only that
    fraction of the way from our last price up to it. ppm is the buyer's cheapest legal option
    (the supplier's value does not price the ppm commitment)."""
    options = case.get("term_options") or {}
    field = "chargeback_eur_per_complaint"
    if field not in case.get("negotiable", []) or not options.get(field):
        return None, {"skip": "no chargeback option"}
    ppm = quoted_ppm(events, standard)
    if not ppm:
        return None, {"skip": "no quoted ppm"}
    seller = {"standard": {**standard, "ppm_commitment": ppm}, "interest_rate": 0.0, "ppm": ppm}
    base = complete_offer(case, closing_terms(case, standing_terms, standard))
    target_v = supplier_value(case, base, seller)
    base_c = total_cost(case, base, standard, buyer_supplier)
    best = None
    ppms = [base.get("ppm_commitment")]
    if "ppm_commitment" in base and options.get("ppm_commitment"):
        ppms = sorted(options["ppm_commitment"])
    for cb in options[field]:
        if cb >= (base.get(field) or 0):
            continue
        for ppm_opt in ppms:
            trial = {**base, field: cb}
            if "ppm_commitment" in base:
                trial["ppm_commitment"] = ppm_opt
            ceiling = value_price(case, trial, target_v, seller)
            if ceiling is None or ceiling <= 0:
                continue
            price = ceiling
            if last_price is not None and split < 1 and last_price < ceiling:
                price = math.ceil(round((last_price + split * (ceiling - last_price)) * 100, 6)) / 100
            trial["unit_price"] = price
            if not must_haves_ok(case, trial, standard):
                continue
            c = total_cost(case, trial, standard, buyer_supplier)
            if c < base_c - 1e-6 and (best is None or c < best[0]):
                best = (c, trial, ceiling)
    trace = {"quoted_ppm": ppm, "standing": base, "standing_c": base_c, "supplier_value": target_v}
    if best is None:
        return None, {**trace, "skip": "no cheaper value-equivalent package"}
    return best[1], {**trace, "selected": best[1], "selected_c": best[0], "ceiling": best[2]}
