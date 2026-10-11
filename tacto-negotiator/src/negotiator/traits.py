"""Deterministic supplier traits from note templates, news topics and intel.

Templates found in data package v1 (docs/01-research.md R4). Patterns are matched on the note
text with the supplier name removed. Re-check after the Sunday release for new templates.
"""

import re

NOTE_TRAITS: dict[str, re.Pattern] = {
    "pricing_committee": re.compile(r"price changes above \d+ % need the approval of their pricing committee"),
    "wants_fast_payment": re.compile(r"pay our invoices within \d+ days\? In return we would grant a cash discount"),
    "volume_focus": re.compile(r"reviewing small accounts and will focus on customers with volume"),
    "open_book": re.compile(r"offered to walk us through their calculation"),
    "idle_capacity": re.compile(r"could take additional parts at short notice; the second shift has been on hold"),
    "reference_customer": re.compile(r"important reference customer"),
    "overdue_invoices": re.compile(r"invoices are overdue again"),
    "partnership_owner": re.compile(r"kept supplying at the old price .* expects partnership"),
    "liquidity_crisis": re.compile(r"bank is watching every month"),
    "stale_index_owner": re.compile(r"own spreadsheet, last updated"),
    "not_tracking_costs": re.compile(r"had not followed his material and energy prices"),
    "hedged_inputs": re.compile(r"(bought their .* forward until|covered at fixed prices until)"),
    "price_freeze": re.compile(r"frozen all price reductions"),
    "fixed_price_list": re.compile(r"price list applies to all customers without exception"),
    "commitment_for_capacity": re.compile(r"additional volumes only against a binding \d+-month commitment"),
    "multi_year_only": re.compile(r"standard items are not discounted; only multi-year volume agreements"),
    "not_strategic": re.compile(r"'not strategic'"),
    "idle_shop_floor": re.compile(r"half the shop floor was idle"),
    "range_reorg": re.compile(r"reorganising our range around our key accounts"),
}

NEWS_TRAITS = {
    "credit_downgrade", "credit_watch", "restructuring", "succession", "short_time_work",
    "free_capacity", "full_order_book", "allocation", "chip_shortage", "energy_contract",
    "refocus", "big_order", "new_plant", "new_owner", "approvals",
}

# Suppliers for whom money now is worth more than usual (supplier_value interest_rate).
# `offers_skonto`: the master data (suppliers row) states a cash discount for early payment.
CASH_SHORT = {"liquidity_crisis", "wants_fast_payment", "overdue_invoices", "credit_worsening",
              "credit_downgrade", "credit_watch", "restructuring", "short_time_work", "offers_skonto"}

CREDIT_WORSENING_POINTS = 20  # credit index: higher is worse
LATE_PAYER_DAYS = 10  # we pay this supplier's invoices late on average


def _note_text(note: dict, name: str) -> str:
    text = note.get("text") or ""
    return text.replace(name, "") if name else text


def classify(dossier) -> set[str]:
    """Traits from notes (NOTE_TRAITS), news topics (NEWS_TRAITS) and intel thresholds
    (e.g. credit index worsened > 20 points → `credit_worsening`)."""
    out = {t for t, p in NOTE_TRAITS.items() for n in dossier.notes if p.search(_note_text(n, dossier.name))}
    out |= {n.get("topic") for n in dossier.news if n.get("topic") in NEWS_TRAITS}
    now, before = dossier.intel.get("credit_index"), dossier.intel.get("credit_index_12m_ago")
    if now is not None and before is not None and now - before > CREDIT_WORSENING_POINTS:
        out.add("credit_worsening")
    if (dossier.payment_lateness_days or 0) > LATE_PAYER_DAYS:
        out.add("paid_late_by_us")
    if skonto_pct(dossier) > 0:
        out.add("offers_skonto")
    return out


def skonto_pct(dossier) -> float:
    """The cash discount (%) the supplier's master row states, 0 when none or not a number."""
    pct = (getattr(dossier, "master", None) or {}).get("skonto_pct")
    return float(pct) if isinstance(pct, int | float) and not isinstance(pct, bool) else 0.0


def evidence(dossier, trait: str) -> list[str]:
    """Document/news IDs that support a trait - for the trace and the pitch."""
    if trait in NOTE_TRAITS:
        return [n["id"] for n in dossier.notes if NOTE_TRAITS[trait].search(_note_text(n, dossier.name))]
    if trait in NEWS_TRAITS:
        return [n["id"] for n in dossier.news if n.get("topic") == trait]
    if trait == "offers_skonto":
        return []  # master data, not a citable document
    return []
