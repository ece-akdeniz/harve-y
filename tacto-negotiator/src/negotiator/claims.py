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
from dataclasses import asdict, dataclass, replace
from datetime import date
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
    "price_increase": ("notice", "index_change", "scorecard_otd", "scorecard_ppm", "own_quote", "po_history",
                       "rival_quote", "should_cost"),
    "rfq": ("rival_quote", "rival_offer", "scorecard_otd", "scorecard_ppm", "index_change", "own_quote",
            "po_history", "should_cost"),
    "quality": ("scorecard_ppm", "scorecard_otd", "rival_quote", "index_change", "notice", "own_quote",
                "po_history", "should_cost"),
    "renewal": ("notice", "rival_quote", "index_change", "own_quote", "po_history", "scorecard_otd",
                "scorecard_ppm", "should_cost"),
    "renewal_trade": ("scorecard_otd", "index_change", "scorecard_ppm", "notice", "own_quote", "po_history",
                      "rival_quote", "should_cost"),
}
DEFAULT_ORDER = ("index_change", "rival_quote", "rival_offer", "notice", "own_quote", "po_history",
                 "scorecard_otd", "scorecard_ppm", "should_cost")
HISTORY_ORDERS = 4  # po lines per history claim (arena: 2-8 of the same part count as one argument)
HISTORY_QUOTE_DAYS = 365  # an own quote older than this is stale, not an argument


@dataclass(frozen=True)
class Claim:
    kind: str  # index_change | rival_quote | rival_offer | scorecard_otd | scorecard_ppm | notice | should_cost
    #       | own_quote | po_history (opt-in history claims, see `history_claims`)
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
    driver_weight: float | None = None

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
    if not 1 <= int(m) <= 12:
        raise ValueError("invalid month")
    return int(y) * 12 + int(m) - 1


def _month(n: int) -> str:
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


def series_values(facts: dict) -> dict[str, dict[str, float]]:
    """{series: {month: value}} from `idx:SERIES@YYYY-MM` facts."""
    out: dict[str, dict[str, float]] = {}
    for ref, f in facts.items():
        if ref.startswith("idx:") and "@" in ref and isinstance(f, dict):
            sid, month = ref[4:].split("@", 1)
            try:
                _months(month)
                value = f.get("value")
                if (f.get("series", sid) != sid or f.get("month", month) != month or isinstance(value, bool)
                        or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
                    continue
            except ValueError:
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


def best_buyer_window(values: dict[str, float], latest_end: bool = False) -> tuple[str, str] | None:
    """The allowed window (≤ 12 months, ending within the last 12 months) with the largest fall;
    `latest_end`: only windows ending at the series' latest month (the most recent fall)."""
    if not values:
        return None
    last = _months(max(values))
    best, best_pct = None, 0.0
    for end in values:
        e = _months(end)
        if e < last - (WINDOW_MONTHS - 1) or (latest_end and e != last):
            continue
        for k in range(1, WINDOW_MONTHS + 1):
            start = _month(e - k)
            if start in values and (p := _pct(values[start], values[end])) < best_pct:
                best, best_pct = (start, end), p
    return best


def recent_buyer_window(values: dict[str, float]) -> tuple[str, str] | None:
    """Largest fall (≤ 12 months) ending at the latest published month: the current trend."""
    if not values:
        return None
    end = max(values)
    e = _months(end)
    best, best_pct = None, 0.0
    for k in range(1, WINDOW_MONTHS + 1):
        start = _month(e - k)
        if start in values and (p := _pct(values[start], values[end])) < best_pct:
            best, best_pct = (start, end), p
    return best


MIN_DRIVER_WEIGHT = 0.10  # recent-window claims only for drivers that matter to the supplier's cost
_HEDGE = re.compile(r"[^.]*\b(?:covered\b[^.]{0,40}\b(?:fixed prices|until)|hedged?)\b[^.]*", re.I)
_NAME_STOP = {"producer", "prices", "index", "monthly", "average", "derived", "fictional", "other"}


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _NAME_STOP}


def hedged_series(case: dict, package, series: list[str]) -> set[str]:
    """Series whose cost the case suppliers say is fixed for now, from their own letters/quote remarks.

    A hedge sentence naming a series (ID or name word, e.g. "alloys" ~ "Alloy surcharge") hedges that
    series; one naming no known series hedges all of them (fail closed)."""
    if package is None or getattr(package, "db", None) is None:
        return set(series)
    sups = set(case.get("suppliers") or [])
    texts = []
    for ref in package.ids("doc:"):
        if (package.lookup(ref) or {}).get("supplier") in sups:
            try:
                texts.append(package.document(ref))
            except (OSError, ValueError):
                continue
    for part in case.get("parts") or []:
        texts += [r["remarks"] or "" for r in package.query(
            "SELECT supplier_id, remarks FROM quotes WHERE part_id = ?", (part,), limit=10_000)
            if r["supplier_id"] in sups]
    names = _series_names(package)
    out = set()
    for text in texts:
        for m in _HEDGE.finditer(text or ""):
            sentence = m.group(0)
            hit = {s for s in series if s in sentence
                   or _stems(names.get(s, "").split(" (")[0]) & _stems(sentence)}
            out |= hit or set(series)
    return out


def recent_index_claims(case: dict, package, facts: dict) -> list["Claim"]:
    """Public claims for material cost drivers falling at the latest month and not documented as hedged
    by the supplier (opt-in, not in the bank)."""
    parts = case.get("parts") or []
    part = parts[0] if parts else None
    refs = set(case.get("refs") or [])
    drivers = {s: w for s, w in _drivers(package, part).items() if w >= MIN_DRIVER_WEIGHT}
    hedged = hedged_series(case, package, list(drivers))
    names = _series_names(package)
    series = series_values(facts)
    out = []
    for sid in sorted(set(drivers) - hedged, key=lambda s: -drivers[s]):
        values = series.get(sid, {})
        if (w := recent_buyer_window(values)) is None:
            continue
        c = _index_claim(sid, values, w, part, drivers[sid], refs, "recent buyer window", names, cherry=True)
        c = replace(c, sentence=render(c, facts))
        if c.figure is not None and c.figure <= -BEST_WINDOW_MIN_PP:
            out.append(c)
    return out


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
        driver_weight=weight,
    )


def _reference_price(case: dict, target: str, facts: dict) -> float | None:
    own = [f["unit_price"] / (f.get("price_unit") or 1) for r, f in facts.items()
           if r.startswith("quote:") and r in set(case.get("refs") or []) | set(case.get("facts") or {})
           and f.get("supplier") == target and f.get("unit_price") is not None]
    return min(own) if own else case.get("buyer", {}).get("current_unit_price")


def _parts(row):
    value = row.get("part_ids") or row.get("parts") or row.get("part") or ""
    return set(re.findall(r"part:[\w-]+", value if isinstance(value, str) else " ".join(value)))


def _scope(ref, row, package):
    if any(key in row for key in ("part", "parts", "part_ids")):
        return _parts(row)
    if package is None:
        return set()
    if ref.startswith("doc:") and getattr(package, "db", None) is not None:
        rows = package.query("SELECT part_ids FROM documents WHERE id = ?", (ref,))
        if rows:
            return _parts(rows[0])
    if ref.startswith("ctr:"):
        try:
            text = package.document(ref)
        except (OSError, ValueError):
            return set()
        # Only the explicit Parts line defines applicability; other text is untrusted prose.
        match = re.search(r"^Parts:\s*(.+)$", text, re.MULTILINE)
        return _parts({"part_ids": match.group(1)}) if match else set()
    return set()


def _trigger_letter(case: dict, facts: dict, supplier: str, part: str) -> tuple[str, dict] | None:
    def matches(row):
        return (isinstance(row, dict) and row.get("supplier") == supplier
                and row.get("asked_pct") is not None and row.get("days") is not None
                and (not _parts(row) or part in _parts(row)))

    ref = case.get("trigger_doc")
    if ref:
        return (ref, facts[ref]) if ref.startswith("doc:") and matches(facts.get(ref)) else None
    refs = set(case.get("refs") or []) | set(case.get("facts") or {})
    letters = [(r, f) for r, f in facts.items() if r in refs and r.startswith("doc:") and matches(f)]
    return letters[0] if len(letters) == 1 else None


def _notice_reason(claim, facts, package=None, require_short=True):
    if len(claim.ids) != 2 or not claim.ids[0].startswith("doc:") or not claim.ids[1].startswith("ctr:"):
        return "needs letter and contract ids"
    doc, ctr = [facts[i] for i in claim.ids]
    if not claim.supplier_id or any(r.get("supplier") != claim.supplier_id for r in (doc, ctr)):
        return "other supplier"
    if not claim.part_id:
        return "notice part unknown"
    if any(claim.part_id not in _scope(ref, row, package) for ref, row in zip(claim.ids, (doc, ctr), strict=True)):
        return "notice part outside or missing scope"
    if not all(_number(r.get("days")) and r["days"] >= 0 for r in (doc, ctr)):
        return "invalid notice days"
    if require_short and doc["days"] >= ctr["days"]:
        return "notice is not short"
    try:
        observed = date.fromisoformat(doc["date"])
        start, end = date.fromisoformat(ctr["valid_from"]), date.fromisoformat(ctr["valid_to"])
        effective = date.fromisoformat(doc.get("effective_date") or doc["date"])
    except (KeyError, TypeError, ValueError):
        return "notice validity dates unknown"
    if not start <= observed <= effective <= end:
        return "contract not valid at notice/effective date"
    return None


def build_bank(case: dict, package=None, verify_claims=True) -> list[Claim]:
    """Candidate claims for a case (arena case dict: case_id, type, parts, suppliers, refs, facts...).

    Index changes for the part's cost drivers (and indices the case cites) over the latest 12-month
    window, plus a buyer-favourable window when the latest one supports the supplier; rival quotes
    (case refs / alternative) per receiving supplier; scorecard OTD and ppm; letter notice vs.
    contract notice; should-cost (internal). By default every claim passes `verify` against
    the case facts. `verify_claims=False` exposes raw candidates for context check diagnostics."""
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
        if not c.supports_buyer:
            for label, bw in (("best buyer window", best_buyer_window(values)),
                              ("recent buyer window", best_buyer_window(values, latest_end=True))):
                if not bw or any(x.window == bw and x.subject == sid for x in bank):
                    continue
                alt = _index_claim(sid, values, bw, part, drivers.get(sid), refs, label, names, cherry=True)
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
        rows = in_refs or rows
        ref, f = max(rows, key=lambda x: x[1].get("quarter") or "") if rows else (None, {})
        if f.get("otd_pct") is not None:
            otd = round(float(f["otd_pct"]), 1)
            bank.append(Claim(
                kind="scorecard_otd", ids=(ref,), figure=otd, unit="%",
                sentence=f"Your on-time delivery on scorecard {ref} was {otd:.1f} %.",
                supplier_id=target, part_id=None, supports_buyer=otd < OTD_WEAK, disclosure="supplier_own",
                subject=target, strength=round(OTD_TARGET - otd, 1), in_case_refs=ref in refs))
        if f.get("ppm") is not None:
            ppm = int(f["ppm"])
            earlier = facts.get(f"sc:{target.split(':', 1)[-1]}@{_shift_quarter(f.get('quarter'), -4)}") or {}
            rising = earlier.get("ppm") is not None and ppm > 1.2 * earlier["ppm"]
            bank.append(Claim(
                kind="scorecard_ppm", ids=(ref,), figure=float(ppm), unit="ppm",
                sentence=f"Your supplier-caused defect rate on scorecard {ref} was {ppm} ppm.",
                supplier_id=target, part_id=None, supports_buyer=ppm >= PPM_WEAK or rising,
                disclosure="supplier_own", subject=target, strength=float(ppm), in_case_refs=ref in refs,
                note="rising vs. a year earlier" if rising else ""))

        letter = _trigger_letter(case, facts, target, part)
        if letter:
            dref, d = letter
            notices = []
            for cref, ctr in facts.items():
                if not (cref.startswith("ctr:") and "#" not in cref and isinstance(ctr, dict)
                        and ctr.get("supplier") == target):
                    continue
                candidate = Claim("notice", (dref, cref), d.get("days"), "days", "",
                                  supplier_id=target, part_id=part, disclosure="supplier_own", subject=target)
                if _notice_reason(candidate, facts, package, require_short=False) is None:
                    notices.append(replace(candidate, supports_buyer=d["days"] < ctr["days"],
                                           strength=float(ctr["days"] - d["days"]),
                                           in_case_refs=dref in refs or cref in refs))
            # Multiple applicable contracts need resolution, never an arbitrary first match.
            if len(notices) == 1:
                bank.append(notices[0])

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

    bank = [replace(c, sentence=render(c, facts)) for c in bank]
    return [c for c in bank if verify(c, facts, package, case)] if verify_claims else bank


def public_rival_quotes(case: dict, package=None) -> list[tuple[Claim, dict]]:
    """Documented quotes for the case part from suppliers outside the case, still valid on the case
    trigger date, as (claim, buyer terms of the quote). Cost comparison is the caller's job: a
    rival quote supports the buyer only if its complete cost beats the supplier's standing sheet.
    Fails closed (empty) without a package, a dated trigger document or a quote validity."""
    if package is None or getattr(package, "db", None) is None:
        return []
    facts = case_facts(case, package)
    parts, suppliers = set(case.get("parts") or []), set(case.get("suppliers") or [])
    trigger = facts.get(case.get("trigger_doc") or "") or {}
    try:
        as_of = date.fromisoformat(trigger["date"])
    except (KeyError, TypeError, ValueError):
        return []
    out = []
    for part in sorted(parts):
        rows = package.query("SELECT id, validity_days FROM quotes WHERE part_id = ?", (part,), limit=10_000)
        for row in rows:
            q, f = row["id"], facts.get(row["id"])
            if not isinstance(f, dict) or f.get("supplier") in suppliers or f.get("unit_price") is None:
                continue
            try:
                quoted = date.fromisoformat(f["date"])
                valid = int(row["validity_days"])
            except (KeyError, TypeError, ValueError):
                continue
            if not quoted <= as_of or (as_of - quoted).days > valid:
                continue
            price = f["unit_price"] / (f.get("price_unit") or 1)
            for target in sorted(suppliers):
                claim = Claim(kind="rival_quote", ids=(q,), figure=round(price, 2), unit="EUR", sentence="",
                              supplier_id=target, part_id=part, disclosure="reveals_rival",
                              subject=f.get("supplier"), note=f"public rival {f.get('supplier')} quoted {f['date']}")
                claim = replace(claim, sentence=render(claim, facts))
                if verify(claim, facts, package, case):
                    terms = {"unit_price": round(price, 4), "payment_days": f.get("payment_days"),
                             "lead_time_days": f.get("lead_time_days"), "incoterm": f.get("incoterm"),
                             "index_clause": None}
                    out.append((claim, {k: v for k, v in terms.items() if k == "index_clause" or v is not None}))
    return out


def _unit_price(fact: dict) -> float | None:
    if not isinstance(fact, dict) or not _number(fact.get("unit_price")) or fact["unit_price"] < 0:
        return None
    unit = fact.get("price_unit", 1)
    if unit is None:
        unit = 1
    if not _number(unit) or unit <= 0 or fact.get("currency", "EUR") != "EUR":
        return None
    return fact["unit_price"] / unit


def history_claims(case: dict, package=None) -> list[Claim]:
    """Opt-in deeper bank (`claim_pacing`): what the case supplier itself quoted and what we ordered.

    `po_history`: the supplier's most recent `po:` lines for the case part (2-8 count as one argument)
    priced at or below our current price. `own_quote`: the supplier's latest own quote for the part,
    not older than HISTORY_QUOTE_DAYS at the trigger date, at or below our current price - and only
    when the quote id is in the case refs or is the buyer's alternative. api.md counts a quote only when
    it is "of this case (in its refs or your alternative)"; hosted run 9a4fbb93 (P08) cited the
    supplier's own quote:7300008 outside the refs, the arena rated it `irrelevant` and the supplier
    read it as a rival quote. `po` carries no such qualifier, so order lines stay unrestricted. Both
    disclose nothing the supplier does not have (its own quote, our orders with it). Callers compare
    the figure with the supplier's standing ask before citing; verification is `verify`."""
    facts = case_facts(case, package)
    parts = case.get("parts") or []
    part = parts[0] if parts else None
    current = (case.get("buyer") or {}).get("current_unit_price")
    if not part or not _number(current):
        return []
    trigger = facts.get(case.get("trigger_doc") or "") or {}
    refs = set(case.get("refs") or [])
    alt_ref = ((case.get("buyer") or {}).get("alternative") or {}).get("ref")
    case_quotes = refs | ({alt_ref} if isinstance(alt_ref, str) and alt_ref.startswith("quote:") else set())
    try:
        as_of = date.fromisoformat(trigger["date"])
    except (KeyError, TypeError, ValueError):
        as_of = None
    out = []
    for target in case.get("suppliers") or []:
        orders = []
        for ref, f in facts.items():
            if not (ref.startswith("po:") and isinstance(f, dict) and f.get("supplier") == target
                    and f.get("part") == part):
                continue
            price = _unit_price(f)
            if price is None or price > current + 1e-9:
                continue
            orders.append((f.get("date") or "", ref, price))
        orders.sort(reverse=True)
        recent = orders[:HISTORY_ORDERS]
        if len(recent) >= 2:
            ids = tuple(sorted(r for _, r, _ in recent))
            claim = Claim(kind="po_history", ids=ids, figure=round(max(p for *_, p in recent), 2), unit="EUR",
                          sentence="", supplier_id=target, part_id=part, disclosure="supplier_own", subject=target,
                          strength=round((current - max(p for *_, p in recent)) / current * 100, 2),
                          note=f"{len(recent)} most recent orders, {recent[-1][0]} to {recent[0][0]}")
            out.append(replace(claim, sentence=render(claim, facts)))
        quotes = []
        for ref, f in facts.items():
            if not (ref.startswith("quote:") and ref in case_quotes and isinstance(f, dict)
                    and f.get("supplier") == target and f.get("part") == part):
                continue
            price = _unit_price(f)
            try:
                quoted = date.fromisoformat(f["date"])
            except (KeyError, TypeError, ValueError):
                continue
            if price is None or price > current + 1e-9:
                continue
            if as_of is not None and not 0 <= (as_of - quoted).days <= HISTORY_QUOTE_DAYS:
                continue
            quotes.append((f["date"], ref, price))
        if quotes:
            quoted, ref, price = max(quotes)
            claim = Claim(kind="own_quote", ids=(ref,), figure=round(price, 2), unit="EUR", sentence="",
                          supplier_id=target, part_id=part, disclosure="supplier_own", subject=target,
                          strength=round((current - price) / current * 100, 2), in_case_refs=ref in refs,
                          note=f"own quote of {quoted}" + ("" if ref in refs else "; buyer alternative"))
            out.append(replace(claim, sentence=render(claim, facts)))
    return [c for c in out if verify(c, facts, package, case)]


def _shift_quarter(quarter: str | None, n: int) -> str:
    if not quarter or "Q" not in quarter:
        return ""
    y, q = quarter.split("Q")
    k = int(y) * 4 + int(q) - 1 + n
    return f"{k // 4}Q{k % 4 + 1}"


def offer_claim(offer_id: str, unit_price: float, rival_supplier: str, target_supplier: str, part: str) -> Claim:
    """A rival's live offer in an RFQ session (cited once per receiving supplier; reveals it)."""
    claim = Claim(kind="rival_offer", ids=(offer_id,), figure=round(unit_price, 2), unit="EUR",
                 sentence=f"Another supplier has offered {part} at EUR {unit_price:.2f} per unit ({offer_id}).",
                 supplier_id=target_supplier, part_id=part, disclosure="reveals_rival", subject=rival_supplier)
    return replace(claim, sentence=render(claim, {}))


# ---------------------------------------------------------------- verify


def _close(claimed: float, actual: float, unit: str) -> bool:
    if unit == "%":
        return abs(claimed - actual) <= 0.5
    return abs(claimed - actual) <= max(abs(actual) * 0.005, 0.01)


def _number(value):
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def render(claim: Claim, facts: dict) -> str:
    """Single approved sentence per kind, using structured fields rather than arbitrary prose."""
    ref = claim.ids[0]
    figure = claim.figure
    if claim.kind == "index_change":
        series = ref[4:].split("@")[0]
        return f"The {series} index {_verb(figure)} {_fmt_pct(figure)} between {ref} and {claim.ids[1]}."
    if claim.kind in ("scorecard_otd", "scorecard_ppm"):
        quarter = facts.get(ref, {}).get("quarter") or (ref.split("@", 1)[1] if "@" in ref else None)
        period = f" ({quarter}, rolling 12 months)" if quarter else ""
        metric = ("on-time delivery against requested dates" if claim.kind == "scorecard_otd"
                  else "supplier-caused defect rate")
        value = f"{figure:.1f} %" if claim.kind == "scorecard_otd" else f"{figure:g} ppm"
        return f"Your supplier-wide {metric} on scorecard {ref}{period} was {value}."
    if claim.kind == "notice":
        needed = facts[claim.ids[1]]["days"]
        return (f"Your letter {ref} gives {figure:g} days' notice, short of the {needed:g}-day "
                f"requirement in contract {claim.ids[1]}.")
    if claim.kind == "rival_quote":
        return f"We hold a quote {ref} for {claim.part_id} at EUR {figure:.2f} per unit."
    if claim.kind == "rival_offer":
        return f"Another supplier has offered {claim.part_id} at EUR {figure:.2f} per unit ({ref})."
    if claim.kind == "should_cost":
        return f"Our should-cost estimate {ref} for {claim.part_id} is EUR {figure:.2f} per unit."
    if claim.kind == "own_quote":
        return f"Your own quote {ref} for {claim.part_id} offered EUR {figure:.2f} per unit."
    if claim.kind == "po_history":
        prices = [p for i in claim.ids if (p := _unit_price(facts.get(i))) is not None]
        lo, hi = (min(prices), max(prices)) if prices else (figure, figure)
        ids = ", ".join(claim.ids)
        if abs(hi - lo) < 0.005:
            return f"Our orders {ids} for {claim.part_id} were placed at EUR {hi:.2f} per unit."
        return f"Our orders {ids} for {claim.part_id} were placed between EUR {lo:.2f} and EUR {hi:.2f} per unit."
    raise ValueError("unknown claim kind")


def _check(claim, facts, package=None, case=None):
    rows = [facts.get(i) for i in claim.ids]
    if not rows or any(not isinstance(r, dict) for r in rows):
        return "unknown id"
    if not _number(claim.figure):
        return "invalid figure"
    if not all(i in claim.sentence for i in claim.ids):
        return "id missing from sentence"
    k = claim.kind
    units = {"index_change": "%", "scorecard_otd": "%", "scorecard_ppm": "ppm", "notice": "days",
             "rival_quote": "EUR", "rival_offer": "EUR", "should_cost": "EUR", "own_quote": "EUR",
             "po_history": "EUR"}
    if k not in units:
        return f"unknown kind {k}"
    if claim.unit != units[k]:
        return "wrong unit"
    disclosures = {"index_change": "public", "scorecard_otd": "supplier_own", "scorecard_ppm": "supplier_own",
                   "notice": "supplier_own", "should_cost": "internal",
                   "rival_quote": "reveals_rival", "rival_offer": "reveals_rival",
                   "own_quote": "supplier_own", "po_history": "supplier_own"}
    if claim.disclosure != disclosures[k]:
        return "wrong disclosure"
    if case is not None and claim.part_id is not None and claim.part_id not in case.get("parts", []):
        return "other case part"
    if k in ("own_quote", "po_history"):
        if not claim.supplier_id or not claim.part_id:
            return "history claim needs supplier and part"
        if case is not None and claim.supplier_id not in case.get("suppliers", []):
            return "other supplier"
        prefix = "quote:" if k == "own_quote" else "po:"
        if k == "own_quote" and len(rows) != 1:
            return "needs one quote id"
        if k == "po_history" and not 2 <= len(rows) <= 8:
            return "needs two to eight order lines"
        if any(not i.startswith(prefix) for i in claim.ids) or len(set(claim.ids)) != len(claim.ids):
            return "wrong or repeated id type"
        if any(r.get("supplier") != claim.supplier_id or r.get("part") != claim.part_id for r in rows):
            return "other supplier or part"
        prices = [_unit_price(r) for r in rows]
        if any(p is None for p in prices):
            return "invalid price basis"
        actual = max(prices)
    elif k == "index_change":
        if len(rows) != 2 or any(not re.fullmatch(r"idx:[^@]+@\d{4}-\d{2}", i) for i in claim.ids):
            return "needs two index ids"
        sids = {i[4:].split("@")[0] for i in claim.ids}
        months = [i.split("@")[1] for i in claim.ids]
        if len(sids) != 1 or any(r.get("series", i[4:].split("@")[0]) != i[4:].split("@")[0]
                                 or r.get("month", m) != m
                                 for i, m, r in zip(claim.ids, months, rows, strict=True)):
            return "different series or month"
        a, b = months
        span = _months(b) - _months(a)
        if not 0 < span <= WINDOW_MONTHS:
            return "window longer than 12 months"
        if claim.window is not None and claim.window != (a, b):
            return "window mismatch"
        series = next(iter(sids))
        if claim.subject not in (None, series):
            return "index subject mismatch"
        last = max(series_values(facts).get(series, {b: 0}))
        if _months(b) < _months(last) - (WINDOW_MONTHS - 1):
            return "window ends too early"
        if len({r["unit"] for r in rows if r.get("unit")}) > 1:
            return "incompatible index units"
        if not all(_number(r.get("value")) and r["value"] > 0 for r in rows):
            return "invalid index value"
        actual = _pct(rows[0]["value"], rows[1]["value"])
        if _verb(claim.figure) != _verb(round(actual, 1)) or claim.supports_buyer != (claim.figure < 0):
            return "index direction mismatch"
    elif k in ("rival_quote", "rival_offer", "should_cost"):
        if len(rows) != 1:
            return "needs one price id"
        r = rows[0]
        if claim.part_id and r.get("part") != claim.part_id:
            return "other part"
        if k != "should_cost" and claim.supplier_id and r.get("supplier") == claim.supplier_id:
            return "own quote"
        if r.get("currency", "EUR") != "EUR":
            return "non-EUR price source"
        unit = r.get("price_unit", 1)
        value = r.get("unit_cost" if k == "should_cost" else "unit_price")
        if not _number(unit) or unit <= 0 or not _number(value) or value < 0:
            return "invalid price basis"
        actual = value / unit
    elif k in ("scorecard_otd", "scorecard_ppm"):
        if len(rows) != 1 or not claim.ids[0].startswith("sc:"):
            return "needs one scorecard id"
        if not claim.supplier_id or rows[0].get("supplier") != claim.supplier_id:
            return "other supplier"
        if claim.part_id is not None or _parts(rows[0]):
            return "scorecard is supplier-wide"
        if rows[0].get("window_months", 12) != 12:
            return "scorecard period is not rolling 12 months"
        quarter = rows[0].get("quarter")
        if quarter is not None and (not re.fullmatch(r"\d{4}Q[1-4]", quarter)
                                    or ("@" in claim.ids[0] and claim.ids[0].split("@", 1)[1] != quarter)):
            return "scorecard period mismatch"
        key = "otd_pct" if k == "scorecard_otd" else "ppm"
        actual = rows[0].get(key)
        if not _number(actual) or actual < 0 or (k == "scorecard_otd" and actual > 100):
            return "invalid scorecard value"
    else:
        reason = _notice_reason(claim, facts, package)
        if reason:
            return reason
        if case is not None:
            if claim.supplier_id not in case.get("suppliers", []) or claim.part_id not in case.get("parts", []):
                return "notice outside case"
            letter = _trigger_letter(case, facts, claim.supplier_id, claim.part_id)
            if letter is None or letter[0] != claim.ids[0]:
                return "notice is not case trigger"
        actual = rows[0]["days"]
    if not _close(claim.figure, actual, claim.unit):
        return f"figure {claim.figure} vs {actual:.4g}"
    if claim.sentence != render(claim, facts):
        return "sentence differs from verified fields"
    return None


def check(claim: Claim, facts: dict, package=None, case=None) -> str | None:
    """Check arithmetic, units, scope and the deterministic sentence; malformed facts fail closed."""
    try:
        return _check(claim, facts, package, case)
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError, OverflowError):
        return "malformed claim or source"


def verify(claim: Claim, facts: dict, package=None, case=None) -> bool:
    return check(claim, facts, package, case) is None


# ---------------------------------------------------------------- pick


def claim_keys(claim: Claim) -> set[str]:
    """Keys a claim uses up: its IDs; a rival quote/offer only for the receiving supplier."""
    if claim.disclosure == "reveals_rival" and claim.supplier_id:
        return {f"{i}>{claim.supplier_id}" for i in claim.ids}
    return set(claim.ids)


def pick(bank: list[Claim], used_ids: set[str], max_claims: int = MAX_CHECKED, *,
         supplier_id: str | None = None, case_type: str | None = None, allow_adverse: bool = False,
         disclosures: frozenset[str] | set[str] = DEFAULT_DISCLOSURE,
         skip_kinds: frozenset[str] | set[str] = frozenset(), allow_cherry_pick: bool = False,
         index_priorities: dict[str, int] | None = None) -> list[Claim]:
    """At most `max_claims` (never more than 3) unused claims for `supplier_id`.

    Defaults: only claims that support the buyer, latest index windows only, disclosing nothing private (pass
    `disclosures | {"reveals_rival"}` to cite a rival quote deliberately). Order by case type,
    then optional index relevance, case refs and strength. Callers add `claim_keys(c)` of sent claims to `used_ids`."""
    order = KIND_ORDER.get(case_type or "", DEFAULT_ORDER)
    rank = {k: i for i, k in enumerate(order)}
    cands = [c for c in bank
             if (allow_adverse or c.supports_buyer) and c.disclosure in disclosures and c.kind not in skip_kinds
             and (allow_cherry_pick or not c.cherry_picked)
             and (supplier_id is None or c.supplier_id in (None, supplier_id))]
    cands.sort(key=lambda c: (not c.supports_buyer, rank.get(c.kind, len(rank)),
                              (index_priorities or {}).get(c.subject, 0) if c.kind == "index_change" else 0,
                              not c.in_case_refs, -c.strength))
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


def index_relevance(bank, case, package=None, events=(), breakdown=None):
    """Rank only known series mentions; supplier prose cannot authorize claims or disclosure.
    `breakdown` (opt-in, `cost_breakdown.find`): the series of the supplier's biggest moved cost element
    ranks ahead of every other explanation - its own figures, not its prose, set the order."""
    series = {c.subject for c in bank if c.kind == "index_change" and c.subject}
    cited = {r[4:].split("@")[0] for r in case.get("refs", []) if r.startswith("idx:")}
    latest = next((e for e in reversed(events) if e.get("from") != "buyer" and e.get("body")), {})
    text = latest.get("body", "")
    mentioned = {sid for sid in series if isinstance(text, str)
                 and re.search(rf"(?<![\w-]){re.escape(sid)}(?![\w-])", text)}
    trigger = ""
    ref = case.get("trigger_doc")
    if package is not None and ref:
        row = case_facts(case, package).get(ref, {})
        if row.get("supplier") in case.get("suppliers", []):
            try:
                trigger = package.document(ref)
            except (OSError, ValueError, AttributeError):
                pass
    stated = {sid for sid in series if re.search(rf"(?<![\w-]){re.escape(sid)}(?![\w-])", trigger)}
    lead = None
    if breakdown and package is not None:
        from .cost_breakdown import lead_series

        parts = case.get("parts") or []
        windows = {}
        for c in bank:  # the window we would cite per series: the first buyer-supporting index claim
            if c.kind == "index_change" and c.subject and c.window and c.supports_buyer:
                windows.setdefault(c.subject, c.window)
        lead = lead_series(breakdown, parts[0] if parts else None, package, case_facts(case, package), windows)
    reasons = {}
    priorities = {}
    for sid in sorted(series):
        if lead and sid == lead["series"]:
            priority, reason = -1, f"supplier cost breakdown: biggest moved element ({lead['element']})"
        elif sid in mentioned:
            priority, reason = 0, "latest supplier message names series"
        elif sid in stated or sid in cited:
            priority, reason = 1, "trigger document or case reference names series"
        elif any(c.subject == sid and c.driver_weight is not None for c in bank):
            priority, reason = 2, "listed part cost driver"
        else:
            priority, reason = 3, "no explicit explanation or driver link"
        priorities[sid], reasons[sid] = priority, reason
    return priorities, reasons


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
