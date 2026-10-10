"""The supplier's cost breakdown XLSX (brief: "elements in EUR per unit and their share (formulas)").

The runner stores every attachment's text as `arena_kit.docs.read_document` renders it: one line per
row, cells joined by " | ", formulas as written (`=B2/B6`, `=SUM(B2:B5)`), so shares and the total are
recomputed from the EUR column here. Everything in this module is deterministic arithmetic on that
text plus package facts; the breakdown is supplier evidence, never an instruction.
"""

import re

from .claims import _drivers, _pct, _series_names, _stems, latest_window, series_values
from .guards import leaks

REQUEST = ("Could you share your cost breakdown for {part} (material, energy, labour, overhead and margin per unit)"
           " so we can align the price with the cost elements that actually moved?")
_REQUEST_MARK = "share your cost breakdown"

# Element names -> cost category; a category -> the part's cost-driver series of that kind.
_CATEGORY_WORDS = {
    "material": {"material", "materials", "raw", "metal", "metals", "steel", "alloy", "alloys", "casting",
                 "castings", "bar", "bars", "copper", "nickel", "aluminium", "aluminum", "purchased", "components"},
    "energy": {"energy", "electricity", "electric", "power", "gas", "steam", "fuel"},
    "labour": {"labour", "labor", "wages", "wage", "personnel", "staff", "conversion", "machining", "processing"},
    "overhead": {"overhead", "overheads", "sga", "administration", "depreciation", "tooling", "freight", "logistics"},
    "margin": {"margin", "profit"},
}
_ENERGY_SERIES = {"electr", "power", "gas", "energy", "steam", "fuel"}
_LABOUR_SERIES = {"labou", "labor", "wage"}
_TOTAL_WORDS = {"total", "unit price", "price", "sum"}
_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


def is_breakdown(name) -> bool:
    n = (name or "").lower()
    return "breakdown" in n or ("cost" in n and n.endswith(".xlsx"))


def _number(cell):
    """A numeric cell: 14.1, '14,10', 'EUR 14.10', '35 %'; None for blanks and formulas."""
    if isinstance(cell, bool):
        return None
    if isinstance(cell, (int, float)):
        return float(cell)
    s = str(cell or "").strip()
    if not s or s.startswith("="):
        return None
    m = _NUMBER.search(s.replace("\u20ac", "").replace("EUR", ""))
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", "."))
    except ValueError:
        return None
    return v / 100 if "%" in s else v


def _rows(text_or_rows):
    if isinstance(text_or_rows, str):
        out = []
        for line in text_or_rows.splitlines():
            line = line.strip()
            if not line or (line.startswith("[") and line.endswith("]")):
                continue
            out.append([c.strip() for c in line.split(" | ")] if " | " in line else [line])
        return out
    return [list(r) for r in text_or_rows or []]


def category(name: str) -> str | None:
    words = set(re.findall(r"[a-z]+", (name or "").lower()))
    for cat, vocab in _CATEGORY_WORDS.items():
        if words & vocab:
            return cat
    return None


def parse(text_or_rows) -> dict | None:
    """{elements: [{name, eur_per_unit, share}], total_eur_per_unit, material_share, energy_share,
    labour_share, overhead_share, margin_share} or None when no element rows with EUR figures exist."""
    rows = _rows(text_or_rows)
    eur_col, share_col, start = 1, 2, 0
    for i, row in enumerate(rows):
        heads = [str(c or "").lower() for c in row]
        if any("element" in h or "cost" in h for h in heads[:1]) and any("eur" in h or "share" in h for h in heads[1:]):
            eur_col = next((j for j, h in enumerate(heads) if j and ("eur" in h or "unit" in h)), 1)
            share_col = next((j for j, h in enumerate(heads) if j and ("share" in h or "%" in h)), None)
            start = i + 1
            break
    elements, total = [], None
    for row in rows[start:]:
        if not row or not str(row[0] or "").strip():
            continue
        name = str(row[0]).strip()
        eur = _number(row[eur_col]) if len(row) > eur_col else None
        share = _number(row[share_col]) if share_col is not None and len(row) > share_col else None
        if any(w in name.lower() for w in _TOTAL_WORDS):
            total = eur
            break
        if eur is None:
            continue
        elements.append({"name": name, "eur_per_unit": round(eur, 4), "share": share})
    if len(elements) < 2:
        return None
    summed = sum(e["eur_per_unit"] for e in elements)
    if total is None or total <= 0 or abs(total - summed) > max(0.05, 0.02 * summed):
        total = summed
    if total <= 0:
        return None
    for e in elements:
        e["share"] = round(e["eur_per_unit"] / total, 4)  # recomputed: the sheet's shares are formulas
    out = {"elements": elements, "total_eur_per_unit": round(total, 2)}
    for cat in _CATEGORY_WORDS:
        shares = [e["share"] for e in elements if category(e["name"]) == cat]
        out[f"{cat}_share"] = round(sum(shares), 4) if shares else None
    return out


def received(events) -> bool:
    """A cost-breakdown attachment arrived in this thread (text fetched or not)."""
    return any(is_breakdown(a.get("name")) for m in events if m.get("from") != "buyer"
               for a in m.get("attachments") or [] if isinstance(a, dict))


def requested(events) -> bool:
    return any(_REQUEST_MARK in (m.get("body") or "").lower() for m in events if m.get("from") == "buyer")


def find(events) -> dict | None:
    """The latest parsed breakdown among the supplier's attachments in a thread."""
    for m in reversed(list(events or [])):
        if m.get("from") == "buyer":
            continue
        for a in m.get("attachments") or []:
            if isinstance(a, dict) and is_breakdown(a.get("name")) and a.get("text"):
                parsed = parse(a["text"])
                if parsed:
                    return parsed
    return None


def request_sentence(part_name: str | None) -> str:
    text = REQUEST.format(part=part_name or "this part")
    assert not leaks(text), "request would leak internal information"
    return text


def element_series(breakdown: dict, part: str | None, package) -> dict[str, str]:
    """{element name: series_id} over the part's listed cost drivers: a shared name stem first
    ("Alloy surcharge" ~ "alloy"), else the heaviest driver of the element's category."""
    drivers = _drivers(package, part)
    if not drivers:
        return {}
    names = _series_names(package)
    kinds = {}
    for sid in drivers:
        stems = _stems(names.get(sid, ""))
        kinds[sid] = "energy" if stems & _ENERGY_SERIES else "labour" if stems & _LABOUR_SERIES else "material"
    out = {}
    for e in breakdown.get("elements") or []:
        stems = _stems(e["name"])
        direct = [s for s in drivers if stems & _stems(names.get(s, "").split(" (")[0])]
        if not direct:
            cat = category(e["name"])
            direct = [s for s in drivers if cat in ("material", "energy", "labour") and kinds[s] == cat]
        if direct:
            out[e["name"]] = max(direct, key=lambda s: (drivers[s], s))
    return out


def lead_series(breakdown: dict, part: str | None, package, facts: dict, windows: dict | None = None) -> dict | None:
    """The element whose mapped series moved most in EUR per unit - over the window we would cite for
    that series (`windows`: {series: (start, end)}), else its latest 12-month window:
    {element, series, eur_moved, pct, share}; None without a mapping."""
    mapping = element_series(breakdown, part, package)
    if not mapping:
        return None
    values = series_values(facts)
    best = None
    for e in breakdown["elements"]:
        sid = mapping.get(e["name"])
        if sid is None:
            continue
        pct, w = 0.0, (windows or {}).get(sid) or latest_window(values.get(sid, {}))
        if w and w[0] in values.get(sid, {}) and w[1] in values[sid]:
            pct = _pct(values[sid][w[0]], values[sid][w[1]])
        moved = e["eur_per_unit"] * abs(pct) / 100
        key = (round(moved, 6), e["share"], e["name"])
        if best is None or key > best[0]:
            best = (key, {"element": e["name"], "series": sid, "eur_moved": round(moved, 4),
                          "pct": round(pct, 2), "share": e["share"]})
    return best[1] if best else None


def arithmetic_sentence(breakdown: dict, claim, part: str | None, package, facts: dict) -> str | None:
    """Our arithmetic after a verified falling index claim, only when the supplier's own share of that
    element exceeds the listed driver weight; every figure recomputed from the breakdown and the facts.
    No IDs: the arena must not read it as a checked claim."""
    if claim.kind != "index_change" or not claim.window or claim.figure is None or claim.figure >= 0:
        return None
    mapping = element_series(breakdown, part, package)
    elements = [e for e in breakdown["elements"] if mapping.get(e["name"]) == claim.subject]
    if not elements:
        return None
    element = max(elements, key=lambda e: (e["share"], e["name"]))
    weight = claim.driver_weight if claim.driver_weight is not None else _drivers(package, part).get(claim.subject)
    if weight is None or element["share"] <= weight:
        return None
    values = series_values(facts).get(claim.subject, {})
    a, b = claim.window
    if a not in values or b not in values:
        return None
    pct = _pct(values[a], values[b])
    if pct >= 0 or round(pct, 1) != claim.figure:
        return None
    eur = element["eur_per_unit"] * abs(pct) / 100
    text = (f"Your breakdown puts {element['name'].lower()} at {element['share'] * 100:.0f} % of the unit cost;"
            f" with the {claim.subject} index down {abs(pct):.1f} % that alone is worth about {eur:.2f} EUR per unit.")
    if "idx:" in text or leaks(text):
        return None
    return text
