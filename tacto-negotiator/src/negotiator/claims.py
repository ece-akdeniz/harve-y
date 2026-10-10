"""Claim bank: arguments with exact figures, verified locally before sending.

Rules (kit api.md "What counts"): figure and ID in the same sentence; ≤ 3 checked per message;
each ID once per case (rival quotes once per supplier in RFQs - and citing reveals them);
tolerance ±0.5 pp for %, else ±0.5 % (min 0.01). Unknown ID or wrong figure = contradicted.

Outward arguments are chosen deliberately: `pick` defaults to claims that support the buyer and
disclose nothing private. Adverse claims (e.g. an index that rose) stay in the bank for internal
reasoning. `cost_pressure_estimate` is our own weighted estimate - its sentence carries no ID and
must never be presented as verified.
"""

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from negotiator import dossiers as dossiers_mod

MAX_CHECKED = 3
WINDOW_MONTHS = 12
BEST_WINDOW_MIN_PP = 1.0  # a cherry-picked window must move at least this much to be offered
OTD_TARGET = 95.0  # company.md quality agreement
OTD_WEAK = 90.0
PPM_WEAK = 1000

# public: anyone can look it up; supplier_own: the supplier's own records (scorecards are sent to it);
# reveals_rival: a rival's quote/offer; internal: our own estimates and plans.
DEFAULT_DISCLOSURE = frozenset({"public", "supplier_own"})

KIND_ORDER = {
    "price_increase": ("notice", "index_change", "scorecard_otd", "scorecard_ppm", "rival_quote", "should_cost"),
    "rfq": ("rival_quote", "rival_offer", "scorecard_otd", "scorecard_ppm", "index_change", "should_cost"),
    "quality": ("scorecard_ppm", "scorecard_otd", "rival_quote", "index_change", "notice", "should_cost"),
    "renewal": ("notice", "rival_quote", "index_change", "scorecard_otd", "scorecard_ppm", "should_cost"),
    "renewal_trade": ("scorecard_otd", "index_change", "scorecard_ppm", "notice", "rival_quote", "should_cost"),
}
DEFAULT_ORDER = ("index_change", "rival_quote", "rival_offer", "notice", "scorecard_otd", "scorecard_ppm",
                 "should_cost")


@dataclass(frozen=True)
class Claim:
    kind: str  # index_change | rival_quote | rival_offer | scorecard_otd | scorecard_ppm | notice | should_cost
    ids: tuple[str, ...]
    figure: float | None
    unit: str  # "%", "EUR", "ppm", "days", ""
    sentence: str  # one sentence with the figure next to the IDs
    supplier_id: str | None = None  # the audience; None = any supplier of the case
    part_id: str | None = None
    window: tuple[str, str] | None = None  # index months (start, end)
    supports_buyer: bool = True
    disclosure: str = "public"
    subject: str | None = None  # index series / rival supplier / scorecard supplier
    strength: float = 0.0  # ranking within a kind, larger is better
    in_case_refs: bool = False
    cherry_picked: bool = False  # index window chosen for its fall, not the latest 12 months
    note: str = ""

    @property
    def direction(self) -> str:
        return "buyer" if self.supports_buyer else "supplier"


# ---------------------------------------------------------------- facts and index helpers


def case_facts(case: dict, package=None) -> dict:
    """What the arena checks against: package facts (incl. Sunday release) overlaid by case facts."""
    base = dict(package.facts) if package is not None else {}
    return base | (case.get("facts") or {})


def _months(month: str) -> int:
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def _month(n: int) -> str:
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


def series_values(facts: dict) -> dict[str, dict[str, float]]:
    """{series: {month: value}} from `idx:SERIES@YYYY-MM` facts."""
    out: dict[str, dict[str, float]] = {}
    for ref, f in facts.items():
        if ref.startswith("idx:") and "@" in ref and isinstance(f, dict):
            sid, month = ref[4:].split("@", 1)
            value = f.get("value")
            if (type(value) not in (int, float) or not math.isfinite(value) or value <= 0
                    or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month)
                    or f.get("series", sid) != sid or f.get("month", month) != month):
                continue
            out.setdefault(sid, {})[month] = float(value)
    return out


def _idx(series: str, month: str) -> str:
    return f"idx:{series}@{month}"


def _pct(a: float, b: float) -> float:
    return (b / a - 1) * 100


def _fmt_pct(x: float) -> str:
    return f"{abs(x):.1f} %"


def _verb(x: float) -> str:
    return "rose" if x > 0 else "fell" if x < 0 else "moved"


def latest_window(values: dict[str, float], months: int = WINDOW_MONTHS) -> tuple[str, str] | None:
    """(start, end): end = the series' last month, start = `months` earlier; None if missing."""
    if not values:
        return None
    end = max(values)
    start = _month(_months(end) - months)
    return (start, end) if start in values else None


def best_buyer_window(values: dict[str, float]) -> tuple[str, str] | None:
    """The allowed window (≤ 12 months, ending within the last 12 months) with the largest fall."""
    if not values:
        return None
    last = _months(max(values))
    best, best_pct = None, 0.0
    for end in values:
        e = _months(end)
        if e < last - (WINDOW_MONTHS - 1):
            continue
        for k in range(1, WINDOW_MONTHS + 1):
            start = _month(e - k)
            if start in values and (p := _pct(values[start], values[end])) < best_pct:
                best, best_pct = (start, end), p
    return best


# ---------------------------------------------------------------- bank


def _drivers(package, part: str) -> dict[str, float]:
    if package is None or package.db is None or not part:
        return {}
    rows = package.query("SELECT series_id, weight FROM cost_drivers WHERE part_id = ?", (part,))
    return {r["series_id"]: r["weight"] for r in rows}


def _series_names(package) -> dict[str, str]:
    if package is None or package.db is None:
        return {}
    return {r["id"]: r["name"] for r in package.query("SELECT id, name FROM index_series", limit=1000)}


def _index_claim(series, values, window, part, weight, refs, label, names, cherry=False) -> "Claim":
    a, b = window
    fig = round(_pct(values[a], values[b]), 1)
    ids = (_idx(series, a), _idx(series, b))
    name = names.get(series, series).split(" (")[0]
    sentence = f"The {series} index ({name}) {_verb(fig)} {_fmt_pct(fig)} between {ids[0]} and {ids[1]}."
    w = weight if weight is not None else 0.0
    return Claim(
        kind="index_change", ids=ids, figure=fig, unit="%", sentence=sentence, part_id=part, window=window,
        supports_buyer=fig < 0, disclosure="public", subject=series,
        strength=round(-fig * max(w, 0.05) if fig < 0 else fig * max(w, 0.05), 3),
        in_case_refs=all(i in refs for i in ids), cherry_picked=cherry,
        note=f"{label}; driver weight {weight}" if weight is not None else f"{label}; not a listed cost driver",
    )


def _reference_price(case: dict, target: str, facts: dict) -> float | None:
    own = [f["unit_price"] / (f.get("price_unit") or 1) for r, f in facts.items()
           if r.startswith("quote:") and r in set(case.get("refs") or []) | set(case.get("facts") or {})
           and f.get("supplier") == target and f.get("unit_price") is not None]
    return min(own) if own else case.get("buyer", {}).get("current_unit_price")


def _trigger_letter(case: dict, facts: dict, supplier: str, part: str) -> tuple[str, dict] | None:
    ref = case.get("trigger_doc")
    if ref and isinstance(facts.get(ref), dict):
        return ref, facts[ref]
    letters = [(r, f) for r, f in facts.items() if r.startswith("doc:") and isinstance(f, dict)
               and f.get("supplier") == supplier and f.get("asked_pct") is not None and f.get("days") is not None]
    letters = [x for x in letters if x[0] in (case.get("refs") or [])] or (
        letters if case.get("type") == "price_increase" else [])
    return max(letters, key=lambda x: x[1].get("date") or "") if letters else None


def build_bank(case: dict, package=None) -> list[Claim]:
    """Candidate claims for a case (arena case dict: case_id, type, parts, suppliers, refs, facts...).

    Index changes for the part's cost drivers (and indices the case cites) over the latest 12-month
    window, plus a buyer-favourable window when the latest one supports the supplier; rival quotes
    (case refs / alternative) per receiving supplier; scorecard OTD and ppm; letter notice vs.
    contract notice; should-cost (internal). Every claim passes `verify` against the case facts."""
    facts = case_facts(case, package)
    refs = set(case.get("refs") or []) | set(case.get("facts") or {})
    parts = case.get("parts") or []
    suppliers = case.get("suppliers") or []
    part = parts[0] if parts else None
    names = _series_names(package)
    series = series_values(facts)
    bank: list[Claim] = []

    cost_owner = {}
    if package is not None and package.db is not None and part:
        cost_owner = {r["id"]: r["supplier_id"] for r in package.query(
            "SELECT id, supplier_id FROM should_cost WHERE part_id = ?", (part,))}

    drivers = _drivers(package, part)
    cited = {r[4:].split("@")[0] for r in refs if r.startswith("idx:")}
    for sid in sorted(set(drivers) | cited):
        values = series.get(sid, {})
        w = latest_window(values)
        if not w:
            continue
        c = _index_claim(sid, values, w, part, drivers.get(sid), refs, "latest 12 months", names)
        bank.append(c)
        if not c.supports_buyer and (bw := best_buyer_window(values)):
            alt = _index_claim(sid, values, bw, part, drivers.get(sid), refs, "best buyer window", names, cherry=True)
            if alt.figure is not None and alt.figure <= -BEST_WINDOW_MIN_PP:
                bank.append(alt)

    quotes = {r for r in refs if r.startswith("quote:")}
    alt = (case.get("buyer") or {}).get("alternative") or {}
    if str(alt.get("ref") or "").startswith("quote:"):
        quotes.add(alt["ref"])
    for q in sorted(quotes):
        f = facts.get(q)
        if not isinstance(f, dict) or f.get("unit_price") is None:
            continue
        price = f["unit_price"] / (f.get("price_unit") or 1)
        for target in suppliers:
            if target == f.get("supplier"):
                continue
            ref_price = _reference_price(case, target, facts)
            bank.append(Claim(
                kind="rival_quote", ids=(q,), figure=round(price, 2), unit="EUR",
                sentence=f"We hold a quote {q} for {f.get('part')} at EUR {price:.2f} per unit.",
                supplier_id=target, part_id=f.get("part"), supports_buyer=ref_price is None or price < ref_price,
                disclosure="reveals_rival", subject=f.get("supplier"),
                strength=round((ref_price - price) / ref_price * 100, 2) if ref_price else 0.0,
                in_case_refs=q in refs, note=f"rival {f.get('supplier')} quoted {f.get('date')}"))

    for target in suppliers:
        rows = [(r, f) for r, f in facts.items() if r.startswith("sc:") and isinstance(f, dict)
                and f.get("supplier") == target]
        in_refs = [x for x in rows if x[0] in refs]
        if not (rows := in_refs or rows):
            continue
        ref, f = max(rows, key=lambda x: x[1].get("quarter") or "")
        if f.get("otd_pct") is not None:
            otd = round(float(f["otd_pct"]), 1)
            bank.append(Claim(
                kind="scorecard_otd", ids=(ref,), figure=otd, unit="%",
                sentence=f"Your on-time delivery on scorecard {ref} was {otd:.1f} %.",
                supplier_id=target, part_id=part, supports_buyer=otd < OTD_WEAK, disclosure="supplier_own",
                subject=target, strength=round(OTD_TARGET - otd, 1), in_case_refs=ref in refs))
        if f.get("ppm") is not None:
            ppm = int(f["ppm"])
            earlier = facts.get(f"sc:{target.split(':', 1)[-1]}@{_shift_quarter(f.get('quarter'), -4)}") or {}
            rising = earlier.get("ppm") is not None and ppm > 1.2 * earlier["ppm"]
            bank.append(Claim(
                kind="scorecard_ppm", ids=(ref,), figure=float(ppm), unit="ppm",
                sentence=f"Your supplier-caused defect rate on scorecard {ref} was {ppm} ppm.",
                supplier_id=target, part_id=part, supports_buyer=ppm >= PPM_WEAK or rising,
                disclosure="supplier_own", subject=target, strength=float(ppm), in_case_refs=ref in refs,
                note="rising vs. a year earlier" if rising else ""))

        letter = _trigger_letter(case, facts, target, part)
        contract = next(((r, c) for r, c in facts.items() if r.startswith("ctr:") and "#" not in r
                         and isinstance(c, dict) and c.get("supplier") == target and c.get("days")), None)
        if letter and contract and all(
            isinstance(x, int | float) and not isinstance(x, bool)
            for x in (letter[1].get("days"), contract[1].get("days"))
        ):
            (dref, d), (cref, c) = letter, contract
            given, needed = d["days"], c["days"]
            bank.append(Claim(
                kind="notice", ids=(dref, cref), figure=float(given), unit="days",
                sentence=f"Your letter {dref} gives only {given} days' notice, short of the notice period "
                         f"in contract {cref}.",
                supplier_id=target, part_id=part, supports_buyer=given < needed, disclosure="supplier_own",
                subject=target, strength=float(needed - given), in_case_refs=dref in refs or cref in refs))

        for ref, f in facts.items():
            if not (ref.startswith("cost:") and isinstance(f, dict) and f.get("part") == part):
                continue
            owner = cost_owner.get(ref) or (f"sup:{ref.split('-', 1)[1]}" if "-" in ref[5:] else None)
            if owner and owner != target:
                continue
            cost = round(f["unit_cost"] / (f.get("price_unit") or 1), 2)
            cur = (case.get("buyer") or {}).get("current_unit_price")
            bank.append(Claim(
                kind="should_cost", ids=(ref,), figure=cost, unit="EUR",
                sentence=f"Our should-cost estimate {ref} for {part} is EUR {cost:.2f} per unit.",
                supplier_id=target, part_id=part, supports_buyer=bool(cur and cost < cur), disclosure="internal",
                subject=target, in_case_refs=ref in refs,
                note=f"+-{f.get('confidence_pct')} %, no margin; reveals our estimate"))

    return [c for c in bank if verify(c, facts)]


def _shift_quarter(quarter: str | None, n: int) -> str:
    if not quarter or "Q" not in quarter:
        return ""
    y, q = quarter.split("Q")
    k = int(y) * 4 + int(q) - 1 + n
    return f"{k // 4}Q{k % 4 + 1}"


def offer_claim(offer_id: str, unit_price: float, rival_supplier: str, target_supplier: str, part: str) -> Claim:
    """A rival's live offer in an RFQ session (cited once per receiving supplier; reveals it)."""
    return Claim(kind="rival_offer", ids=(offer_id,), figure=round(unit_price, 2), unit="EUR",
                 sentence=f"Another supplier has offered {part} at EUR {unit_price:.2f} per unit ({offer_id}).",
                 supplier_id=target_supplier, part_id=part, disclosure="reveals_rival", subject=rival_supplier)


# ---------------------------------------------------------------- verify


def _close(claimed: float, actual: float, unit: str) -> bool:
    if unit == "%":
        return abs(claimed - actual) <= 0.5
    return abs(claimed - actual) <= max(abs(actual) * 0.005, 0.01)


def check(claim: Claim, facts: dict) -> str | None:
    """None if the claim recomputes from `facts` within tolerance, else the reason."""
    rows = [facts.get(i) for i in claim.ids]
    if any(not isinstance(r, dict) for r in rows):
        return "unknown id"
    if claim.figure is None:
        return "no figure"
    if not all(i in claim.sentence for i in claim.ids):
        return "id missing from sentence"
    k = claim.kind
    if k == "index_change":
        if len(rows) != 2:
            return "needs two index ids"
        sids = {i[4:].split("@")[0] for i in claim.ids}
        months = [r.get("month") or i.split("@")[1] for i, r in zip(claim.ids, rows, strict=True)]
        if len(sids) != 1:
            return "different series"
        (a, ra), (b, rb) = sorted(zip(months, rows, strict=True), key=lambda x: x[0])
        span = _months(b) - _months(a)
        if not 0 < span <= WINDOW_MONTHS:
            return "window longer than 12 months"
        last = max(series_values(facts).get(sids.pop(), {b: 0}))
        if _months(b) < _months(last) - (WINDOW_MONTHS - 1):
            return "window ends too early"
        actual = _pct(ra["value"], rb["value"])
    elif k in ("rival_quote", "rival_offer"):
        r = rows[0]
        if claim.part_id and r.get("part") and r["part"] != claim.part_id:
            return "other part"
        if claim.supplier_id and r.get("supplier") == claim.supplier_id:
            return "own quote"
        actual = r["unit_price"] / (r.get("price_unit") or 1)
    elif k in ("scorecard_otd", "scorecard_ppm"):
        if claim.supplier_id and any(r.get("supplier") != claim.supplier_id for r in rows):
            return "other supplier"
        key = "otd_pct" if k == "scorecard_otd" else "ppm"
        actual = sum(r[key] for r in rows) / len(rows)
    elif k == "notice":
        doc, ctr = rows
        if doc.get("supplier") != ctr.get("supplier"):
            return "other supplier"
        actual = doc["days"]
    elif k == "should_cost":
        actual = rows[0]["unit_cost"] / (rows[0].get("price_unit") or 1)
    else:
        return f"unknown kind {k}"
    return None if _close(claim.figure, actual, claim.unit) else f"figure {claim.figure} vs {actual:.4g}"


def verify(claim: Claim, facts: dict) -> bool:
    """Recompute the claim's figure from `facts` (package + release + case facts) within tolerance."""
    try:
        return check(claim, facts) is None
    except (TypeError, ValueError, KeyError, ZeroDivisionError, OverflowError):
        return False


# ---------------------------------------------------------------- pick


def claim_keys(claim: Claim) -> set[str]:
    """Keys a claim uses up: its IDs; a rival quote/offer only for the receiving supplier."""
    if claim.disclosure == "reveals_rival" and claim.supplier_id:
        return {f"{i}>{claim.supplier_id}" for i in claim.ids}
    return set(claim.ids)


def pick(bank: list[Claim], used_ids: set[str], max_claims: int = MAX_CHECKED, *,
         supplier_id: str | None = None, case_type: str | None = None, allow_adverse: bool = False,
         disclosures: frozenset[str] | set[str] = DEFAULT_DISCLOSURE,
         skip_kinds: frozenset[str] | set[str] = frozenset(), allow_cherry_pick: bool = False) -> list[Claim]:
    """At most `max_claims` (never more than 3) unused claims for `supplier_id`.

    Defaults: only claims that support the buyer, latest index windows only, disclosing nothing private (pass
    `disclosures | {"reveals_rival"}` to cite a rival quote deliberately). Order by case type,
    then case refs, then strength. Callers add `claim_keys(c)` of sent claims to `used_ids`."""
    order = KIND_ORDER.get(case_type or "", DEFAULT_ORDER)
    rank = {k: i for i, k in enumerate(order)}
    cands = [c for c in bank
             if (allow_adverse or c.supports_buyer) and c.disclosure in disclosures and c.kind not in skip_kinds
             and (allow_cherry_pick or not c.cherry_picked)
             and (supplier_id is None or c.supplier_id in (None, supplier_id))]
    cands.sort(key=lambda c: (not c.supports_buyer, rank.get(c.kind, len(rank)), not c.in_case_refs, -c.strength))
    out, taken, subjects = [], set(used_ids), set()
    for c in cands:
        if len(out) >= min(max_claims, MAX_CHECKED):
            break
        keys = claim_keys(c)
        raw = set(c.ids)
        if keys & taken or (c.disclosure != "reveals_rival" and raw & taken) or (c.kind, c.subject) in subjects:
            continue
        out.append(c)
        taken |= keys | raw
        subjects.add((c.kind, c.subject))
    return out


# ---------------------------------------------------------------- weighted estimate (never verified)

_SERIES_RE = re.compile(r"\b([A-Z]{2,6}(?:-[A-Z0-9]+)+)\b")
_PCT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


def parse_stated_drivers(text: str) -> list[dict]:
    """Drivers a supplier states, e.g. "LCI-C rose 2.7 % ... and is 30 % of our cost; PPI-C241 rose
    6.5 % and is 24 %" → [{series, pct, weight}]. First % after the series = change, second = share."""
    out = []
    for clause in re.split(r"[;\n]|(?<=[.!?])\s", text):
        m = _SERIES_RE.search(clause)
        if not m:
            continue
        nums = [float(x.replace(",", ".")) for x in _PCT_RE.findall(clause[m.end():])]
        if not nums:
            continue
        neg = re.search(r"\b(fell|dropped|decreased|declined)\b", clause[m.end():]) is not None
        out.append({"series": m.group(1), "pct": -nums[0] if neg else nums[0],
                    "weight": nums[1] / 100 if len(nums) > 1 else None})
    return out


def _asked_pct(case: dict, facts: dict, part: str | None) -> float | None:
    for s in case.get("suppliers") or [None]:
        if (letter := _trigger_letter(case, facts, s, part)) and letter[1].get("asked_pct") is not None:
            return letter[1]["asked_pct"]
    return None


def cost_pressure_estimate(case: dict, part: str | None = None, package=None, stated=None) -> dict:
    """Our estimate: Σ weight × 12-month change for the cost drivers (or the drivers the supplier
    stated: list of {series, weight, pct} or its message text), with the cost-base share they cover.
    Returns {pp, coverage, asked_pct, residual_pp, drivers, sentence, verified: False}. The sentence
    has no IDs on purpose: it is our arithmetic, not a checked claim."""
    part = part or (case.get("parts") or [None])[0]
    facts = case_facts(case, package)
    series = series_values(facts)
    if isinstance(stated, str):
        stated = parse_stated_drivers(stated)
    drivers = _drivers(package, part)
    rows = []
    for d in stated or [{"series": s, "weight": w, "pct": None} for s, w in drivers.items()]:
        sid, w, pct = d["series"], d.get("weight"), d.get("pct")
        w = drivers.get(sid) if w is None else w
        window = latest_window(series.get(sid, {}))
        if pct is None and window:
            v = series[sid]
            pct = _pct(v[window[0]], v[window[1]])
        if w is None or pct is None:
            continue
        rows.append({"series": sid, "weight": w, "pct": round(pct, 2), "pp": round(w * pct, 2),
                     "window": window, "listed_weight": drivers.get(sid)})
    pp = round(sum(r["pp"] for r in rows), 2)
    coverage = round(sum(r["weight"] for r in rows), 2)
    asked = _asked_pct(case, facts, part)
    names = ", ".join(r["series"] for r in rows)
    whose = "the drivers you cite" if stated else "the listed cost drivers"
    sentence = (f"By our estimate, {whose} ({names}) contribute about {pp:.2f} percentage points to cost "
                f"movement, covering {coverage * 100:.0f} % of the cost base")
    sentence += f"; what accounts for the remainder of the requested {asked:g} %?" if asked is not None else "."
    return {"pp": pp, "coverage": coverage, "asked_pct": asked,
            "residual_pp": round(asked - pp, 2) if asked is not None else None,
            "drivers": rows, "sentence": sentence, "verified": False}


# ---------------------------------------------------------------- prep (Sunday 08:00 rebuild)


def prep(data_dir=None, out_path="experiments/prep.json", release=None) -> dict:
    """Rebuild dossiers and per-(supplier, part) claim banks from the package plus the Sunday
    release overlay (`release` or ARENA_RELEASE). Intended for `negotiator prep`; writes JSON."""
    package = dossiers_mod.load_package(data_dir, release)
    ds = dossiers_mod.build(package)
    pairs = package.query(
        "SELECT s.part_id, s.supplier_id, (SELECT price FROM price_conditions p WHERE p.part_id = s.part_id "
        "AND p.supplier_id = s.supplier_id ORDER BY valid_from DESC LIMIT 1) price FROM sourcing s "
        "WHERE s.status = 'active' ORDER BY s.supplier_id, s.part_id", limit=100_000)
    banks = {}
    for p in pairs:
        if p["supplier_id"] not in ds:
            continue
        case = {"type": "price_increase", "parts": [p["part_id"]], "suppliers": [p["supplier_id"]],
                "buyer": {"current_unit_price": p["price"]}}
        banks[f"{p['supplier_id']}|{p['part_id']}"] = [asdict(c) for c in build_bank(case, package)]
    out = {
        "data_manifest": package.manifest,
        "release": str(package.release) if package.release else None,
        "facts": len(package.facts),
        "dossiers": {sid: {"name": d.name, "category": d.category, "traits": sorted(d.traits),
                           "news": [n["id"] for n in d.news], "notes": [n["id"] for n in d.notes]}
                     for sid, d in ds.items()},
        "banks": banks,
    }
    dest = Path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"release": out["release"], "facts": out["facts"], "dossiers": len(ds), "banks": len(banks),
            "claims": sum(len(b) for b in banks.values()), "out": str(dest)}
