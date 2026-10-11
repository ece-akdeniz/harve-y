"""Give the supplier the volume it keeps asking for: the case's fixed annual volume as a binding
commitment, our latest shared forecast as a CSV attachment and the forecast's own `fc:` ID as a
checkable claim. Behaviour-triggered: only cases with a fixed `volume_per_year` and a shared forecast
for the part. Found in the breakthrough sessions (P08 S3-S7, P18 S9-S12): the bar stockholders ask
"Which volume can you commit to?" in every reply and never got a number; with the number, the file
and the ID the claim comes back `verified` ("we took it into account") and the ladder keeps moving.
"""
import base64
import re

from . import claims as claims_mod

_WHICH_VOLUME = re.compile(r"(which volume|volume forecast|volume figures|exact volume)", re.I)


def plan(case, package, supplier) -> dict | None:
    """Facts for the volume answer, or None when the case has no fixed volume / shared forecast."""
    parts = case.get("parts") or []
    volume = (case.get("fixed_terms") or {}).get("volume_per_year")
    if len(parts) != 1 or not volume:
        return None
    part = parts[0]
    facts = claims_mod.case_facts(case, package)
    rows = [(r, f) for r, f in facts.items() if r.startswith("fc:") and isinstance(f, dict)
            and f.get("part") == part and isinstance(f.get("volume_per_year"), int | float)]
    if not rows:
        return None
    fref, f = max(rows, key=lambda x: x[0])
    try:
        lines = package.query("SELECT target_month, qty FROM forecast_lines WHERE fc_id = ? ORDER BY target_month",
                              (fref,))
        quota = package.query("SELECT quota_pct FROM sourcing WHERE part_id = ? AND supplier_id = ?",
                              (part, supplier))
    except Exception:  # noqa: BLE001 - the DB is optional; the statement and the claim still work
        lines, quota = [], []
    lines = [(r["target_month"], r["qty"]) for r in lines]
    q = quota[0]["quota_pct"] if quota else None
    return {"part": part, "volume": int(volume), "fc": fref, "change_pct": f.get("change_pct"),
            "total": f["volume_per_year"], "unit": "kg" if "kg" in (case.get("briefing") or "") else "units",
            "lines": lines, "quota": q}


def attachment(p: dict) -> dict | None:
    """CSV of the shared monthly forecast with this supplier's committed share (public data only)."""
    if not p["lines"]:
        return None
    share = p["volume"] / p["total"] if p["total"] else None
    rows = ["forecast_id,part,month,total_forecast_qty,your_committed_qty"]
    for month, qty in p["lines"]:
        rows.append(f"{p['fc']},{p['part']},{month},{qty},{round(qty * share) if share else ''}")
    rows.append(f"# total next 12 months: {p['total']}; your binding annual volume under this contract: {p['volume']}"
                + (f"; your current source-list quota: {p['quota']} %" if p["quota"] is not None else ""))
    csv = "\n".join(rows) + "\n"
    return {"name": f"forecast-{p['part'].split(':')[-1]}-{p['fc'].split('@')[-1]}.csv", "type": "csv",
            "content_b64": base64.b64encode(csv.encode()).decode()}


def first_paragraph(p: dict, terms) -> tuple[str, list[str]]:
    """Binding volume over the offered term, the attached forecast, the fc claim (one checkable sentence)."""
    months = int(terms.get("contract_months") or 12)
    total = p["volume"] * months // 12
    text = (f"On volume: our annual requirement for {p['part']} is fixed at {p['volume']} {p['unit']}; with this "
            f"package we commit to it bindingly for the full {months} months, {total} {p['unit']} in total. "
            f"The attached file lists our latest shared monthly forecast with your committed quantity per month; "
            f"please price this committed volume.")
    ids = []
    if p["change_pct"] is not None:
        ch = p["change_pct"]
        text += (f" Our shared demand forecast {p['fc']} for {p['part']} shows a change of "
                 f"{'+' if ch >= 0 else ''}{ch:.1f} % against the previous snapshot.")
        ids.append(p["fc"])
    return text, ids


def reminder(p: dict, terms) -> str:
    months = int(terms.get("contract_months") or 12)
    return (f"To answer your volume question again: the binding quantity is {p['volume']} {p['unit']} a year for "
            f"the full {months} months; we are not proposing a higher annual quantity.")


def asked_for_volume(events) -> bool:
    return any(e.get("from") != "buyer" and _WHICH_VOLUME.search(e.get("body") or "") for e in events)
