"""Answer the supplier's "which volume can you commit to?" with public volume facts.

Opt-in (`PolicyConfig.volume_answer_types`). The figures come from code only: the case's fixed
`volume_per_year` over the offered `contract_months` (never more than the need), the latest shared
forecast `fc:` for the part (its `volume_per_year` and recorded `change_pct`, the checked figure)
and the current sourcing quota. The forecast ID is cited once, in the first offer; later offers
repeat the binding figures without an ID. No price, term or closing decision is changed.
"""

from . import claims as claims_mod

MAX_CHECKED = 3


def latest_forecast(facts, part):
    """(id, fact) of the latest forecast for `part` with a volume and a change, or None."""
    code = part.split(":", 1)[-1]
    rows = [(r, f) for r, f in facts.items() if r.startswith(f"fc:{code}@") and isinstance(f, dict)
            and f.get("part") == part and isinstance(f.get("volume_per_year"), int | float)
            and f["volume_per_year"] > 0 and isinstance(f.get("change_pct"), int | float)]
    return max(rows, key=lambda x: x[0]) if rows else None


def _quota(package, part, supplier):
    try:
        rows = package.query(
            "SELECT supplier_id, quota_pct FROM sourcing WHERE part_id = ? AND status = 'active'", (part,))
    except Exception:  # noqa: BLE001 - a missing table only drops the quota sentence
        return None
    for r in rows:
        if r["supplier_id"] == supplier and r["quota_pct"] is not None:
            return float(r["quota_pct"])
    return None


def plan(case, package, supplier) -> dict | None:
    parts = case.get("parts") or []
    volume = (case.get("fixed_terms") or {}).get("volume_per_year")
    need = (case.get("buyer") or {}).get("need_per_year")
    if len(parts) != 1 or not volume or not need:
        return None
    facts = claims_mod.case_facts(case, package)
    return {"part": parts[0], "volume": int(min(volume, need)), "forecast": latest_forecast(facts, parts[0]),
            "quota": _quota(package, parts[0], supplier)}


def checked_claims(refs) -> int:
    """Rough count of checked arguments already in a message: index pairs count once."""
    refs = list(refs or [])
    idx = sum(1 for r in refs if r.startswith("idx:"))
    other = sum(1 for r in refs if r.split(":", 1)[0] in ("quote", "offer", "sc", "qn", "fc", "cost", "news"))
    return (idx + 1) // 2 + other


def paragraph(p: dict, months: int, first: bool, room: bool, unit: str = "kg",
              threshold: float | None = None) -> tuple[str, list[str]]:
    total = p["volume"] * months // 12
    text = (f"On your question about volume: with this package we commit bindingly to {p['volume']} {unit} a year "
            f"for the full {months} months, {total} {unit} in total.")
    ids = []
    if p["forecast"]:
        fref, f = p["forecast"]
        figure = f"{f['change_pct']:+.1f} %"
        if first and room:
            text += (f" It is based on our forecast {fref}: {int(f['volume_per_year'])} {unit} for {p['part']} over "
                     f"the next 12 months, a change of {figure}.")
            ids.append(fref)
        else:
            text += f" It is based on our shared forecast of {int(f['volume_per_year'])} {unit} for the next 12 months."
        if p["quota"]:
            text += f" Your current share of that need is {p['quota']:g} %."
    text += " Please price this committed volume."
    if threshold is not None:
        text += (f" As changes above {threshold:g} % need your pricing committee, please put this package "
                 "to the committee so your answer carries its approval.")
    return text, ids
