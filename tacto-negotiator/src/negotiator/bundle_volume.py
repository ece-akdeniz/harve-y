"""Bundling: tell the kit supplier, from public facts, how much volume the kit moves to it.

Opt-in (`PolicyConfig.bundle_volume_types`). Everything is computed here from the data package:
kit quantities from the case's trigger memo, the supplier's current quota per part from
`sourcing`, the forecast IDs (`fc:`) whose `volume_per_year` figure is quoted next to them, and
the supplier's own capacity note when its dossier carries the `idle_capacity` trait. No price,
term or closing decision is changed; the text only adds cited facts (at most three IDs, once).
"""

import re

from . import claims as claims_mod
from . import traits as traits_mod

MAX_IDS = 3
_KIT_LINE = re.compile(r"(\d+)\s*x\s+[^\n]*?\((part:[\w-]+)\)")


def kit_quantities(text: str, parts) -> dict[str, int]:
    """{part: pieces per kit} from memo lines like "19 x Hex bolt ... (part:360010)"."""
    out = {}
    for qty, part in _KIT_LINE.findall(text or ""):
        if part in parts:
            out[part] = out.get(part, 0) + int(qty)
    return out


def _quota(package, part, supplier) -> float:
    rows = package.query(
        "SELECT supplier_id, quota_pct FROM sourcing WHERE part_id = ? AND status = 'active'", (part,))
    for r in rows:
        if r["supplier_id"] == supplier and r["quota_pct"] is not None:
            return float(r["quota_pct"]) / 100
    return 0.0


def _latest_forecast(facts, part):
    rows = [(r, f) for r, f in facts.items() if r.startswith(f"fc:{part.split(':', 1)[1]}@")
            and isinstance(f, dict) and f.get("part") == part
            and isinstance(f.get("volume_per_year"), int | float) and f["volume_per_year"] > 0]
    return max(rows, key=lambda x: x[0]) if rows else None


def plan(case, package, supplier, dossier=None) -> dict | None:
    """Facts for the volume argument, or None when the case has no kit memo with quantities."""
    ref, parts = case.get("trigger_doc"), case.get("parts") or []
    need = (case.get("buyer") or {}).get("need_per_year")
    if not ref or not parts or not need:
        return None
    try:
        quantities = kit_quantities(package.document(ref), parts)
    except (OSError, ValueError, AttributeError):
        return None
    if set(quantities) != set(parts):
        return None  # every part must be covered, or the arithmetic would mislead
    facts = claims_mod.case_facts(case, package)
    lines = []
    for part in parts:
        pieces = quantities[part] * need
        share = _quota(package, part, supplier)
        lines.append({"part": part, "pieces": pieces, "share": share, "new": round(pieces * (1 - share)),
                      "forecast": _latest_forecast(facts, part)})
    new = sum(x["new"] for x in lines)
    if new <= 0:
        return None
    capacity = []
    if dossier is not None and "idle_capacity" in (dossier.traits or set()):
        ids = [i for i in traits_mod.evidence(dossier, "idle_capacity") if i in facts]
        capacity = sorted(ids)[-1:]  # the latest note
    return {"lines": lines, "new": new, "total": sum(x["pieces"] for x in lines), "capacity": capacity}


def first_paragraph(p: dict) -> tuple[str, list[str]]:
    """Text and cited IDs for the first offer: totals, the forecasts of the parts that move most."""
    ranked = sorted((x for x in p["lines"] if x["new"] > 0 and x["forecast"]), key=lambda x: -x["new"])
    ids = list(p["capacity"])
    sentences = [
        f"The kit puts the whole annual volume of all {len(p['lines'])} parts with one supplier: "
        f"{p['total']} pieces a year, of which {p['new']} pieces a year are delivered by other suppliers today."
    ]
    for x in ranked[: MAX_IDS - len(ids)]:
        fref, f = x["forecast"]
        sentences.append(f"Our forecast {fref} for {x['part']} is {int(f['volume_per_year'])} pieces a year.")
        ids.append(fref)
    if p["capacity"]:
        sentences.append(f"As you told us ({p['capacity'][0]}), you can take additional parts at short notice "
                         "and your second shift is on hold; this volume fills it.")
    sentences.append("Please reflect the full kit volume in your price.")
    return " ".join(sentences), ids


def reminder(p: dict) -> str:
    return (f"Our proposal moves {p['new']} pieces a year that other suppliers deliver today to you; "
            "please price that volume.")


_COMMITTEE = re.compile(r"price changes above (\d+(?:\.\d+)?) % need the approval of their pricing committee")


def committee_threshold(dossier) -> float | None:
    """The approval threshold (%) from the supplier's own note, when its dossier has the trait."""
    if dossier is None or "pricing_committee" not in (dossier.traits or set()):
        return None
    for n in dossier.notes:
        m = _COMMITTEE.search(traits_mod._note_text(n, dossier.name))
        if m:
            return float(m.group(1))
    return None


def commitment(p: dict, case, terms, threshold=None) -> str:
    """Answer 'which volume can you commit to?' with the case's fixed volume over the offered term
    (never more than the need), plus the approval path when the supplier has a pricing committee."""
    volume = (case.get("fixed_terms") or {}).get("volume_per_year") or terms.get("volume_per_year")
    months = terms.get("contract_months")
    if not volume or not months:
        return reminder(p)
    kits = int(volume) * int(months) // 12
    text = (f"On your question about volume: with this package we commit bindingly to {int(volume)} kits a year "
            f"for the full {int(months)} months, {kits} kits in total, all {p['total']} pieces a year from one "
            f"supplier, {p['new']} of them moved from other suppliers. That is our full need; please price it.")
    if threshold is not None:
        text += (f" As changes above {threshold:g} % need your pricing committee, please put this package "
                 "to the committee so your answer carries its approval.")
    return text
