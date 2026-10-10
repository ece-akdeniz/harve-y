"""Per-supplier dossiers from the data package (and the Sunday release).

A dossier is everything the data says about one supplier, with citable IDs kept:
master data, intel (credit index now vs. 12 m ago, equity, owner type), news (topic-tagged),
notes/letters/e-mails, scorecards, our payment lateness, negotiation history (asked vs. settled),
contracts and clauses, quotes, price conditions, should-cost for its parts.

Loading goes through `arena_kit.data.DataPackage`, so the Sunday release (ARENA_RELEASE or a
`release-sunday` folder in/next to the package) adds its news and letters without code changes.
"""

import os
import weakref
from dataclasses import dataclass, field
from pathlib import Path

from arena_kit.cost import RELATIONSHIP_GOALS
from arena_kit.data import DataPackage

from negotiator import traits as traits_mod

from .ingestion import VersionedPackage

DATA_CANDIDATES = ("data/package", "/tmp/nak/data")
SKIP_SUBJECTS = {"Holiday shutdown", "ISO 9001 certificate", "Packaging",
                 "Trade fair invitation"}

# company.md: full cost relative to the German base for German-base should-cost rows.
COUNTRY_FACTOR = {"DE": 1.0, "AT": 1.05, "CH": 1.05, "CZ": 0.825, "PL": 0.825, "HU": 0.825, "TR": 0.75, "CN": 0.7}
BASE_RATE = 0.08  # company cost of capital; a healthy supplier's usual rate (assumption)
CASH_SHORT_RATE = 0.15
CRISIS_RATE = 0.20
ASSUMED_MARGIN = 0.06  # only without any should-cost row
_BUILT: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # package -> build(package)


def load_package(data_dir=None, release=None) -> DataPackage:
    """The data package plus the Sunday release overlay (`release` or ARENA_RELEASE)."""
    explicit = data_dir or os.environ.get("ARENA_DATA")
    for c in ([explicit] if explicit else DATA_CANDIDATES):
        if c and (Path(c).expanduser() / "facts.json").is_file():
            return VersionedPackage(c, release=release or os.environ.get("ARENA_RELEASE"))
    raise FileNotFoundError("data package not found: pass data_dir, set ARENA_DATA or run `uv run arena data`")


@dataclass
class Dossier:
    supplier_id: str
    name: str
    country: str
    category: str
    master: dict = field(default_factory=dict)  # suppliers row: payment_days, incoterm, lead time, contract
    intel: dict = field(default_factory=dict)
    news: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)  # {id, date, kind, subject, text}
    scorecard: dict = field(default_factory=dict)
    payment_lateness_days: float | None = None
    history: list[dict] = field(default_factory=list)
    should_cost: dict = field(default_factory=dict)  # part_id -> row
    traits: set[str] = field(default_factory=set)


def _note(package: DataPackage, ref: str, fact: dict) -> dict | None:
    if fact.get("title") in SKIP_SUBJECTS:
        return None
    try:
        text = package.document(ref)
    except (FileNotFoundError, ValueError):
        text = ""
    if text.lstrip().startswith("#"):
        text = text.split("\n", 3)[-1].strip()
    return {"id": ref, "date": fact.get("date"), "kind": fact.get("type"), "subject": fact.get("title"), "text": text}


def build(package) -> dict[str, Dossier]:
    """All detailed suppliers (`suppliers.detail = 'full'`), keyed by `sup:` id."""
    q = package.query
    by_sup_news: dict[str, list] = {}
    by_sup_docs: dict[str, list] = {}
    for ref in package.ids("news:"):
        f = package.lookup(ref) or {}
        by_sup_news.setdefault(f.get("supplier") or f.get("supplier_id"), []).append(
            {"id": ref, "date": f.get("date"), "topic": f.get("topic"), "headline": f.get("headline")})
    for ref in package.ids("doc:"):
        f = package.lookup(ref) or {}
        by_sup_docs.setdefault(f.get("supplier") or f.get("supplier_id"), []).append((ref, f))
    out = {}
    for s in q("SELECT * FROM suppliers WHERE detail = 'full' ORDER BY id", limit=10_000):
        sid = s["id"]
        intel = (q("SELECT * FROM supplier_intel WHERE supplier_id = ?", (sid,)) or [{}])[0]
        sc = (q("SELECT * FROM scorecards WHERE supplier_id = ? ORDER BY quarter DESC LIMIT 1", (sid,)) or [{}])[0]
        late = q("SELECT round(AVG(julianday(paid_date) - julianday(due_date)), 1) d FROM invoices "
                 "WHERE supplier_id = ? AND paid_date IS NOT NULL", (sid,))
        late = late[0].get("d") if late else None
        hist = q("SELECT date, part_id, type, asked_pct, settled_pct, note FROM negotiation_history "
                 "WHERE supplier_id = ? ORDER BY date", (sid,), limit=10_000)
        notes = [n for ref, f in sorted(by_sup_docs.get(sid, []), key=lambda x: x[1].get("date") or "")
                 if (n := _note(package, ref, f))]
        sc_rows = q("SELECT * FROM should_cost WHERE supplier_id = ?", (sid,), limit=10_000)
        d = Dossier(sid, s["name"], s["country"], s["category"], master=s, intel=intel,
                    news=sorted(by_sup_news.get(sid, []), key=lambda n: n["date"] or ""), notes=notes,
                    scorecard=sc, payment_lateness_days=late, history=hist,
                    should_cost={r["part_id"]: r for r in sc_rows})
        d.traits = traits_mod.classify(d)
        out[sid] = d
    return out


def for_case(dossiers: dict[str, Dossier], case: dict) -> dict[str, Dossier]:
    """Dossiers for the case's suppliers; hidden cases may add facts via `case['facts']`."""
    out = {}
    for sid in case.get("suppliers", []):
        d = dossiers.get(sid) or Dossier(sid, sid, "", "")
        extra = [{"id": k, "date": v.get("date"), "topic": v.get("topic"), "headline": v.get("headline")}
                 for k, v in (case.get("facts") or {}).items()
                 if k.startswith("news:") and v.get("supplier") == sid and k not in {n["id"] for n in d.news}]
        notes = [{"id": k, "date": v.get("date"), "kind": v.get("type"),
                  "subject": v.get("title"), "text": v.get("body") or v.get("text") or ""}
                 for k, v in (case.get("facts") or {}).items()
                 if k.startswith("doc:") and v.get("supplier") == sid]
        d = Dossier(**{**d.__dict__, "news": d.news + extra, "notes": d.notes + notes})
        d.traits = traits_mod.classify(d)
        out[sid] = d
    return out


def _cost_row(package, case: dict, part: str, supplier_id: str) -> tuple[dict | None, str]:
    """Supplier-specific should-cost first (case facts, then package), else the German base row."""
    rows = []
    if package is not None and package.db is not None:
        rows += package.query("SELECT * FROM should_cost WHERE part_id = ?", (part,))
    known = {r["id"] for r in rows}
    for ref, f in (case.get("facts") or {}).items():
        if ref.startswith("cost:") and f.get("part") == part and ref not in known:
            owner = f.get("supplier") or (f"sup:{ref.split('-', 1)[1]}" if "-" in ref[5:] else None)
            rows.append({"id": ref, "part_id": part, "supplier_id": owner, **f})
    suffix = supplier_id.split(":", 1)[-1]
    for r in rows:
        if r.get("supplier_id") == supplier_id or r["id"].endswith(f"-{suffix}"):
            return r, "supplier_plant"
    for r in rows:
        if r.get("supplier_id") in (None, "") and r.get("cost_base", "DE") == "DE" and "-" not in r["id"]:
            return r, "german_base"
    return None, "none"


def supplier_estimate(case: dict, supplier_id: str, package=None, dossiers=None, force: bool = False) -> dict | None:
    """Our estimate of a supplier for `arena_kit.cost.supplier_value` / `relationship_cost`
    (`supplier=`): standard terms, interest_rate, usual_rate, ppm, full_cost - plus `notes` and
    `full_cost_range` for sensitivity. None outside relationship goals unless `force`.
    `standard` is the master-data default; override it with the quote PDF's standard terms."""
    if not force and case.get("buyer", {}).get("category_goal") not in RELATIONSHIP_GOALS:
        return None
    package = package or load_package()
    d = (dossiers or {}).get(supplier_id) or build_one(package, supplier_id)
    part = (case.get("parts") or [None])[0]
    notes = []
    master = d.master if d else {}
    standard = {k: v for k, v in {
        "payment_days": master.get("payment_days"),
        "incoterm": master.get("incoterm"),
        "lead_time_days": master.get("standard_lead_time_days"),
    }.items() if v is not None}
    standard.setdefault("payment_days", case.get("buyer", {}).get("reference_payment_days", 60))
    standard.setdefault("incoterm", "FCA")

    tr = d.traits if d else set()
    cash_short = sorted(tr & traits_mod.CASH_SHORT)
    rate = CRISIS_RATE if "liquidity_crisis" in tr else CASH_SHORT_RATE if cash_short else BASE_RATE
    if cash_short:
        notes.append(f"interest_rate {rate:.2f} from traits {', '.join(cash_short)} (assumed, not observed)")

    row, basis = _cost_row(package, case, part, supplier_id) if part else (None, "none")
    current = case.get("buyer", {}).get("current_unit_price")
    if row:
        unit_cost = row["unit_cost"]
        conf = (row.get("confidence_pct") or 10) / 100
        if basis == "german_base":
            factor = COUNTRY_FACTOR.get(d.country if d else "DE", 1.0)
            unit_cost *= factor
            conf += 0.05
            notes.append(f"German-base should-cost {row['id']} x country factor {factor} (+5 pp uncertainty)")
        else:
            notes.append(f"supplier-plant should-cost {row['id']} (+-{conf * 100:.0f} %)")
        full_cost = round(unit_cost, 2)
        if (row.get("price_unit") or 1) != 1:
            notes.append(f"should-cost per {row['price_unit']} units: check the case price unit")
    elif current:
        full_cost, conf = round(current * (1 - ASSUMED_MARGIN), 2), 0.10
        notes.append(f"no should-cost row: assumed {ASSUMED_MARGIN:.0%} margin on current price (weak)")
    else:
        return None
    lo, hi = round(full_cost * (1 - conf), 2), round(full_cost * (1 + conf), 2)
    if current:
        m = (current - full_cost) / current * 100
        notes.append(f"margin at current price {current}: {m:+.1f} % (range {(current - hi) / current * 100:+.1f}"
                     f" to {(current - lo) / current * 100:+.1f} %)")
    out = {"standard": standard, "interest_rate": rate, "usual_rate": BASE_RATE, "full_cost": full_cost,
           "full_cost_range": (lo, hi), "cost_basis": basis, "cost_ref": row["id"] if row else None,
           "traits": sorted(tr), "notes": notes}
    if d and d.scorecard.get("ppm") is not None:
        out["ppm"] = d.scorecard["ppm"]
    return out


def build_one(package, supplier_id: str) -> Dossier | None:
    """One dossier (also for suppliers without `detail = 'full'`)."""
    full = _BUILT.get(package)
    if full is None:
        full = _BUILT[package] = build(package)
    if supplier_id in full:
        return full[supplier_id]
    rows = package.query("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)) if package.db else []
    if not rows:
        d = Dossier(supplier_id, supplier_id, "", "")
        d.news = [{"id": ref, **(package.lookup(ref) or {})} for ref in package.ids("news:")
                  if (package.lookup(ref) or {}).get("supplier") == supplier_id]
        d.notes = [n for ref in package.ids("doc:")
                   if (f := package.lookup(ref) or {}).get("supplier") == supplier_id
                   if (n := _note(package, ref, f))]
        d.traits = traits_mod.classify(d)
        return d
    s = rows[0]
    return Dossier(supplier_id, s["name"], s["country"], s["category"], master=s)
