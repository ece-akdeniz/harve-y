"""Exploratory buyer: the LLM writes the e-mail body and picks among code-priced, legal term sheets
and code-rendered claims; code validates every number, ID and leak and owns accept/walk.

Not the final agent. Its purpose is to find supplier moves beyond our floors and to turn them
into deterministic, behaviour-keyed rules afterwards.
"""

import json
import logging
import math
import os
import re
import time

import httpx
from arena_kit.cost import complete_offer, must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import latest, live_threads

from .guards import leaks

log = logging.getLogger("negotiator.explore")

ENDED = {"walked_away", "no_bid"}
EXTRA_LEAKS = [
    re.compile(p, re.I)
    for p in (
        r"\bfallback\b",
        r"\balternative supplier\b",
        r"\bour alternative\b",
        r"\bno alternative\b",
        r"\bsecond[- ]source quote\b",
        r"\bwalk away\b",
        r"\bc_best\b",
        r"\btarget\b",
        r"\breservation\b",
        r"\bdeadline\b",
        r"\bbefore (the )?(end of|friday|monday)\b",
        r"\bwe must (close|sign|order)\b",
        r"\bonly (option|supplier)\b",
        r"\bcannot (do )?without you\b",
        r"\bdepend(s|ent)? on you\b",
    )
]
NUM = re.compile(r"(?<![A-Za-z:@\-])\d[\d.,]*")


# ---------------------------------------------------------------- facts / claims ----------
def load_facts():
    root = os.environ.get("ARENA_DATA", "data/package")
    with open(os.path.join(root, "facts.json")) as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("facts", data)
    if isinstance(items, dict):
        items = [{"id": k, **v} for k, v in items.items() if isinstance(v, dict)]
    return {x["id"]: x for x in items}


def _pct(a, b):
    return round((b / a - 1) * 100, 1)


def claim_bank(case, facts, supplier_id, rfq_offers=(), supplier_text=""):
    """Public, checkable claims for one supplier thread. Sentences are rendered by code in the
    phrasing the arena has verified before. Each claim id is used at most once per case."""
    part = (case.get("parts") or [None])[0]
    out = []
    # index windows: falling windows ending at the latest month, for the supplier's stated drivers
    series = {}
    for fid, f in facts.items():
        if fid.startswith("idx:"):
            series.setdefault(f["series"], {})[f["month"]] = f["value"]
    for s, vals in series.items():
        if s not in ("AS-14404", "PPI-C2431", "PPI-D351", "LCI-C", "CU-NOTATION", "PPI-C241"):
            continue
        if supplier_text and s not in supplier_text:
            continue  # only series the supplier itself names as cost drivers; others come back "irrelevant"
        months = sorted(vals)
        # buyer-favourable falling windows (<= 12 months, ending within the last 12 months of data),
        # non-overlapping month IDs so every claim stays citable (each idx ID counts once per case)
        cands = []
        for j in range(len(months) - 1, max(len(months) - 13, 0), -1):
            for i in range(j - 1, max(j - 13, -1), -1):
                ch = _pct(vals[months[i]], vals[months[j]])
                if ch < -1.0:
                    cands.append((0 if j >= len(months) - 4 else 1, ch, i, j))  # recent windows first
        cands.sort()
        cands = [(ch, i, j) for _, ch, i, j in cands]
        used_m, n = set(), 0
        for ch, i, j in cands:
            if i in used_m or j in used_m or n >= 1:  # one window per series: a second one comes back 'duplicate'
                continue
            used_m |= {i, j}
            n += 1
            first, lst = months[i], months[j]
            out.append(
                {
                    "id": f"idx-{s}-{first}-{lst}",
                    "ids": [f"idx:{s}@{first}", f"idx:{s}@{lst}"],
                    "kind": "index_fall",
                    "figure": ch,
                    "sentence": f"The {s} index fell {abs(ch):.1f} % between idx:{s}@{first} and idx:{s}@{lst}.",
                    "note": f"{s} fell {ch:.1f} % from {first} to {lst} (public market series).",
                }
            )
    # scorecard (latest quarter) for this supplier
    scs = sorted((fid, f) for fid, f in facts.items() if fid.startswith("sc:") and f.get("supplier") == supplier_id)
    if scs:
        fid, f = scs[-1]
        q = fid.split("@")[1]
        out.append(
            {
                "id": f"sc-{supplier_id}",
                "ids": [fid],
                "kind": "scorecard_otd",
                "figure": f["otd_pct"],
                "sentence": (
                    f"Your supplier-wide on-time delivery against requested dates on scorecard {fid} "
                    f"({q}, rolling 12 months) was {f['otd_pct']:.1f} %."
                ),
                "note": f"its OTD {f['otd_pct']} %, ppm {f.get('ppm')} (supplier's own record).",
            }
        )
    # purchase orders for this part and supplier, same price (2-3 ids, one figure)
    pos = [
        (fid, f)
        for fid, f in facts.items()
        if fid.startswith("po:") and f.get("supplier") == supplier_id and f.get("part") == part
    ]
    if pos:
        by_price = {}
        for fid, f in pos:
            by_price.setdefault(f["unit_price"], []).append(fid)
        price, ids = min((kv for kv in by_price.items() if len(kv[1]) >= 2), key=lambda kv: kv[0], default=(None, []))
        ids = sorted(ids)[-3:]
        if len(ids) >= 2:
            out.append(
                {
                    "id": f"po-{supplier_id}",
                    "ids": ids,
                    "kind": "po_history",
                    "figure": price,
                    "sentence": (
                        f"Our purchase orders {', '.join(ids[:-1])} and {ids[-1]} for {part} "
                        f"were placed with you at EUR {price:.2f} per unit."
                    ),
                "note": (
                    f"our orders for this part at EUR {price:.2f} this year "
                    "(its own delivered price; proves the running volume)."
                ),
                }
            )
    # shared forecast for the part (latest snapshot): the recorded change is what the arena checks
    fcs = sorted((fid, f) for fid, f in facts.items() if fid.startswith("fc:") and f.get("part") == part)
    if fcs:
        fid, f = fcs[-1]
        ch = f.get("change_pct")
        if ch is not None:
            out.append(
                {
                    "id": "fc-latest",
                    "ids": [fid],
                    "kind": "forecast",
                    "figure": ch,
                    "sentence": (
                        f"Our shared demand forecast {fid} for {part} shows a change of "
                        f"{'+' if ch >= 0 else ''}{ch:.1f} % against the previous snapshot."
                    ),
                    "note": (
                        f"latest shared forecast snapshot {fid}, change {ch} %; "
                        "pairs with the forecast attachment."
                    ),
                }
            )
    # rival offers in this session (RFQ)
    for oid, sup, price in rfq_offers:
        if sup != supplier_id:
            out.append(
                {
                    "id": f"rival-{oid}",
                    "ids": [oid],
                    "kind": "rival_offer",
                    "figure": price,
                    "sentence": f"Another supplier has offered {part} at EUR {price:.2f} per unit ({oid}).",
                    "note": f"rival {sup} standing offer {price:.2f} (reveals that price to this supplier).",
                }
            )
    return out


def forecast_attachment(case, supplier_id):
    """CSV of the latest shared monthly forecast for the case part, with this supplier's committed
    share (the case's fixed annual volume). Public data only (forecast_lines + sourcing quota)."""
    import base64
    import sqlite3

    part = (case.get("parts") or [None])[0]
    root = os.environ.get("ARENA_DATA", "data/package")
    db = sqlite3.connect(os.path.join(root, "world.sqlite"))
    fc = db.execute(
        "SELECT id, qty_next_12m, uom FROM forecasts WHERE part_id=? ORDER BY snapshot_month DESC LIMIT 1", (part,)
    ).fetchone()
    if not fc:
        return None, None
    lines = db.execute(
        "SELECT target_month, qty FROM forecast_lines WHERE fc_id=? ORDER BY target_month", (fc[0],)
    ).fetchall()
    quota = db.execute(
        "SELECT quota_pct FROM sourcing WHERE part_id=? AND supplier_id=?", (part, supplier_id)
    ).fetchone()
    vol = (case.get("fixed_terms") or {}).get("volume_per_year") or case["buyer"]["need_per_year"]
    share = vol / fc[1] if fc[1] else None
    rows = [
        "forecast_id,part,month,total_forecast_qty,unit,your_committed_qty",
    ]
    for month, qty in lines:
        rows.append(f"{fc[0]},{part},{month},{qty},{fc[2]},{round(qty * share) if share else ''}")
    rows.append(
        f"# total next 12 months: {fc[1]} {fc[2]}; your binding annual volume under this contract: {vol} {fc[2]}"
        + (f"; your current source-list quota: {quota[0]} %" if quota else "")
    )
    csv = "\n".join(rows) + "\n"
    att = {
        "name": f"forecast-{part.split(':')[-1]}-{fc[0].split('@')[-1]}.csv",
        "type": "csv",
        "content_b64": base64.b64encode(csv.encode()).decode(),
    }
    return att, csv


# ---------------------------------------------------------------- term-sheet menu ---------
def _combos(case):
    opts = case.get("term_options") or {}
    fields = [f for f in case["negotiable"] if f != "unit_price"]
    combos = [{}]
    for f in fields:
        values = opts.get(f) or [None]
        combos = [{**c, f: v} for c in combos for v in values]
    return combos


def price_for(case, terms, target_c, std, lo=0.01, hi=10000.0):
    for _ in range(60):
        mid = (lo + hi) / 2
        c = total_cost(case, {**terms, "unit_price": mid}, std)
        if c > target_c:
            hi = mid
        else:
            lo = mid
    return math.floor(lo * 100) / 100


def describe(case, terms):
    bits = []
    for k, v in terms.items():
        if k == "unit_price":
            continue
        if k == "index_clause":
            bits.append("no index clause" if not v else f"index {v['series']} deadband {v['deadband_pct']}%")
        else:
            bits.append(f"{k}={v}")
    return ", ".join(bits)


def menu(case, std, c_levels):
    """[{id, terms(no price), label, prices: {level: price}}] for every legal non-price package."""
    out = []
    for i, combo in enumerate(_combos(case)):
        full = complete_offer(case, {**combo, "unit_price": 1.0})
        if not must_haves_ok(case, full, std):
            continue
        base = {k: v for k, v in full.items() if k != "unit_price"}
        prices = {lvl: price_for(case, base, c, std) for lvl, c in c_levels.items()}
        out.append({"id": f"S{i}", "terms": base, "label": describe(case, full), "prices": prices})
    return out


# ---------------------------------------------------------------- LLM ---------------------
def llm(messages, timeout=45.0, max_tokens=1800):
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = os.environ["LLM_API_KEY"]
    model = os.environ.get("EXPLORE_LLM_MODEL") or os.environ.get("LLM_MODEL")
    body = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    t0 = time.monotonic()
    with httpx.Client(timeout=timeout) as c:
        r = c.post(base + "/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
    log.info("llm %.1fs", time.monotonic() - t0)
    return json.loads(text)


SYSTEM = """You are the purchasing lead of Hollerau Pumpenwerke GmbH writing ONE e-mail to a supplier in a
negotiation. You write like an experienced, courteous, direct industrial buyer - a person, not a template.

Hard rules (code checks them; a violation is rejected):
- Never mention or hint at: budgets, target prices, internal cost figures, deadlines, urgency, our
  alternative/fallback/second source, that we lack options, or any threat to walk away.
- Every number you write must come from the whitelist given (chosen term sheets, fixed case terms,
  figures the supplier itself wrote, claim figures). Do not invent percentages, volumes or prices.
- Do not paraphrase claim figures; claims you select are appended verbatim by code after your text.
  You may refer to them ("see the figures below").
- Promises exist only as term sheets. Describe the term sheets you chose in words that match them.
- Answer every question the supplier asked, precisely, with the whitelisted number if it asked for one.
- Address what the supplier said last (its conditions, objections, what it welcomed). One or two new
  elements per round; never send the same proposal twice.
- Plain text, 500-1500 characters, no markdown, sign as "Hollerau Pumpenwerke GmbH, Purchasing".
Return JSON only:
{"subject": str, "body": str, "sheets": [{"id": "S..", "level": "L.."}] (1-3 items),
 "claims": [claim ids, 0-2], "attachments": ["forecast"] or [], "action": null | "accept", "rationale": str}
"""


def _nums(text):
    out = set()
    for m in NUM.finditer(text or ""):
        tok = m.group(0).rstrip(".,")
        tok = tok.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", tok) else tok.replace(",", ".")
        try:
            out.add(round(float(tok), 3))
        except ValueError:
            pass
    return out


def _strip_ids(text):
    return re.sub(r"\b[a-z]{2,6}:[A-Za-z0-9#@\-\.]+", " ", text or "")


class Explorer:
    version = "Explorer-v0.1"

    def __init__(self, strategy="", max_rounds=5, depth_levels=None, tracer=None, log_path=None):
        self.strategy = strategy
        self.max_rounds = max_rounds
        self.levels = depth_levels or {
            "L0": 0.995,
            "L1": 0.98,
            "L2": 0.965,
            "L3": 0.95,
            "L4": 0.93,
            "L5": 0.91,
            "L6": 0.89,
            "L7": 0.87,
            "L8": 0.85,
            "L9": 0.83,
            "L10": 0.81,
            "L11": 0.785,
            "L12": 0.76,
        }
        self.facts = load_facts()
        self.used_claims = set()
        self.last_sent = {}  # sid -> list of sheet terms we sent last
        self.last_ask_c = {}  # sid -> C of our cheapest-for-us sheet last round
        self.parked = set()  # sids with a final offer we will not touch
        self.sent_forecast = {}  # sid -> forecast attachment already sent
        self.log_path = log_path
        self.events = []

    # -- helpers --------------------------------------------------------------------------
    def _log(self, kind, **f):
        rec = {"t": time.time(), "kind": kind, **f}
        self.events.append(rec)
        if self.log_path:
            with open(self.log_path, "a") as fh:
                fh.write(json.dumps(rec, default=str) + "\n")

    @staticmethod
    def c_alt(case):
        alt = (case["buyer"].get("alternative") or {}).get("terms") or {}
        return total_cost(case, alt) if alt.get("unit_price") else math.inf

    @staticmethod
    def standing(case, events):
        msg = latest(events)
        std = standard_terms(events)
        sheets = msg.get("term_sheets") or []
        eligible = []
        for sheet in sheets:
            terms = sheet.get("terms") or {}
            if sheet.get("term_sheet_id") and terms.get("unit_price") is not None:
                eligible.append((total_cost(case, terms, std), sheet, terms))
        if not eligible:
            return None, {}, math.inf, std
        cost, sheet, terms = min(eligible, key=lambda item: item[0])
        return sheet["term_sheet_id"], terms, cost, std

    @staticmethod
    def acceptable(case, events):
        """(sheet_id, terms, C, std) of the supplier's FIRST sheet - the only one the arena lets us
        accept ("offer:...-a" alternatives answer HTTP 422 "not a standing offer"; L3-S2 on P18 lost
        its accept that way). `standing` keeps pricing our levels off the cheapest sheet."""
        msg = latest(events)
        std = standard_terms(events)
        sheets = msg.get("term_sheets") or []
        for sheet in sheets[:1]:
            terms = sheet.get("terms") or {}
            if sheet.get("term_sheet_id") and terms.get("unit_price") is not None:
                return sheet["term_sheet_id"], terms, total_cost(case, terms, std), std
        return None, {}, math.inf, std

    def _ours(self, events):
        return sum(1 for m in events if m.get("from") == "buyer")

    def rfq_offers(self, case, threads):
        out = []
        for sid, ev in threads.items():
            msg = latest(ev)
            for s in msg.get("term_sheets") or []:
                p = (s.get("terms") or {}).get("unit_price")
                if p is not None and s.get("term_sheet_id") and msg.get("status") not in ENDED:
                    out.append((s["term_sheet_id"], sid, p))
        return out

    # -- closing (code only) -----------------------------------------------------------------
    def _accept(self, case, sid, sheet_id, c, why):
        self._log("accept", supplier=sid, sheet=sheet_id, c=c, why=why)
        return {
            "supplier_id": sid,
            "message": {
                "subject": case["title"],
                "body": "We accept your offer. Thank you.",
                "action": {"type": "accept", "term_sheet_id": sheet_id},
            },
        }

    def best_standing(self, case, threads):
        best = None
        for sid, ev in threads.items():
            msg = latest(ev)
            if msg.get("status") in ENDED:
                continue
            sheet_id, terms, c, std = self.acceptable(case, ev)
            if sheet_id and must_haves_ok(case, terms, std) and (best is None or c < best[0]):
                best = (c, sid, sheet_id, terms)
        return best

    def decide(self, case, threads):
        live = [s for s in live_threads(threads) if latest(threads[s]).get("status") not in ENDED]
        c_alt = self.c_alt(case)
        # 1. agreed anywhere -> accept it if it beats the alternative
        for sid in live:
            msg = latest(threads[sid])
            if msg.get("status") == "agreed":
                sheet_id, terms, c, std = self.acceptable(case, threads[sid])
                if sheet_id and c <= c_alt and must_haves_ok(case, terms, std):
                    return self._accept(case, sid, sheet_id, c, "agreed")
        # 2. park finals; decide whether anything is still worth talking to
        for sid in live:
            if latest(threads[sid]).get("status") == "final_offer":
                self.parked.add(sid)
        talk = [s for s in live if s not in self.parked and self._ours(threads[s]) < self.max_rounds]
        if not talk:
            best = self.best_standing(case, threads)
            if best and best[0] <= c_alt:
                return self._accept(case, best[1], best[2], best[0], "no thread left to talk to")
            self._log("walk", c_alt=c_alt, best=best)
            return {
                "supplier_id": live[0] if live else next(iter(threads)),
                "message": {
                    "subject": case["title"],
                    "body": "We will not place the order on these terms.",
                    "action": {"type": "walk_away"},
                },
            }
        # 3. talk to the thread with the fewest of our messages (round-robin)
        sid = min(talk, key=lambda s: (self._ours(threads[s]), s))
        return self.compose(case, threads, sid)

    # -- composing (LLM picks, code prices and validates) --------------------------------------
    def _context(self, case, threads, sid):
        ev = threads[sid]
        sheet_id, s_terms, c_stand, std = self.standing(case, ev)
        ours = self._ours(ev)
        levels = {k: c_stand * v for k, v in self.levels.items()} if math.isfinite(c_stand) else {}
        if not levels:
            opening = case["buyer"]["current_unit_price"] * 1.1
            c0 = total_cost(case, complete_offer(case, {"unit_price": opening}), std)
            levels = {k: c0 * v for k, v in self.levels.items()}
        men = menu(case, std, levels)
        sup_text = " ".join((m.get("body") or "") for m in threads[sid] if m.get("from") != "buyer")
        bank = [
            c
            for c in claim_bank(case, self.facts, sid, self.rfq_offers(case, threads), sup_text)
            if not (set(c["ids"]) & self.used_claims)
        ]
        transcript = []
        for m in ev:
            who = "BUYER (us)" if m.get("from") == "buyer" else f"SUPPLIER ({m.get('from')})"
            sheets = [s.get("terms") for s in m.get("term_sheets") or []]
            transcript.append(
                {
                    "from": who,
                    "status": m.get("status"),
                    "text": (m.get("body") or "")[:3000],
                    "term_sheets": sheets,
                    "claim_results": m.get("claim_results") or None,
                }
            )
        others = {}
        for osid, oev in threads.items():
            if osid != sid:
                oid, oterms, oc, _ = self.standing(case, oev)
                others[osid] = {
                    "status": latest(oev).get("status"),
                    "standing": oterms,
                    "relative_cost_vs_this_supplier": None
                    if not math.isfinite(oc) or not math.isfinite(c_stand)
                    else round(oc / c_stand - 1, 4),
                }
        b = case["buyer"]
        public_case = {
            "title": case["title"],
            "briefing": case["briefing"],
            "type": case["type"],
            "parts": case["parts"],
            "need_per_year": b["need_per_year"],
            "horizon_years": b["horizon_years"],
            "current_unit_price": b["current_unit_price"],
            "fixed_terms": case.get("fixed_terms"),
            "negotiable": case["negotiable"],
            "term_options": case.get("term_options"),
            "must_haves": b.get("must_haves"),
            "category_goal": b.get("category_goal"),
            "reference_payment_days": b.get("reference_payment_days"),
        }
        return (
            {
                "case": public_case,
                "supplier_id": sid,
                "our_messages_so_far": ours,
                "max_our_messages": self.max_rounds,
                "strategy_notes": self.strategy,
                "transcript": transcript,
                "supplier_standing_offer": {"id": sheet_id, "terms": s_terms},
                "other_threads": others or None,
                "term_sheet_menu": {
                    "how": (
                        "Pick 1-3 packages by id and a level each. Prices are computed by code so that the package "
                        "costs us the given fraction of the supplier's standing offer (L0=0.5% better for us ... "
                        "L8=15% better). Pick deeper levels early, move toward L0 as rounds pass. Equal levels on "
                        "different packages cost us the same, so the supplier shows which mix it values."
                    ),
                    "packages": [{"id": m["id"], "label": m["label"], "prices": m["prices"]} for m in men],
                },
                "claims": [
                    {"id": c["id"], "kind": c["kind"], "note": c["note"], "sentence_preview": c["sentence"]}
                    for c in bank
                ],
                "attachments_available": {
                    "forecast": "CSV of our latest shared monthly demand forecast for the part with "
                    "this supplier's committed quantity per month (send it when the supplier asks "
                    "for volume figures or a forecast; pairs with claim fc-latest)"
                },
                "whitelist_numbers_hint": "chosen sheet values, fixed terms, the supplier's own figures, claim figures",
            },
            men,
            bank,
            c_stand,
            std,
        )

    def _whitelist(self, case, threads, sid, sheets, claims):
        wl = {2026.0, 2027.0, 2028.0, 12.0, 24.0, 36.0}
        b = case["buyer"]
        for v in (
            b["need_per_year"],
            b["horizon_years"],
            b.get("need_lead_time_days"),
            b.get("reference_payment_days"),
        ):
            if isinstance(v, (int, float)):
                wl.add(round(float(v), 3))
        for _key, v in (case.get("fixed_terms") or {}).items():
            if isinstance(v, (int, float)):
                wl.add(round(float(v), 3))
        for t in sheets:
            for _key, v in t.items():
                if isinstance(v, (int, float)):
                    wl.add(round(float(v), 3))
                elif isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, (int, float)):
                            wl.add(round(float(vv), 3))
            months = t.get("contract_months") or (case.get("fixed_terms") or {}).get("contract_months") or 12
            vol = (
                t.get("volume_per_year") or (case.get("fixed_terms") or {}).get("volume_per_year") or b["need_per_year"]
            )
            wl.add(round(float(vol * months / 12), 3))
            wl.add(round(float(vol * max(1, months // 12)), 3))
        for c in claims:
            wl.add(round(abs(float(c["figure"])), 3))
            wl.add(round(float(c["figure"]), 3))
        for m in threads[sid]:
            if m.get("from") != "buyer":
                wl |= _nums(_strip_ids(m.get("body") or ""))
        att, csv = forecast_attachment(case, sid)
        if csv:
            wl |= _nums(csv)
        return wl

    def _validate(self, case, threads, sid, out, men, bank, c_stand):
        errors = []
        body = out.get("body") or ""
        if not (300 <= len(body) <= 2500):
            errors.append(f"body length {len(body)} outside 300-2500")
        bad = leaks(body) + [p.pattern for p in EXTRA_LEAKS if p.search(body)]
        if bad:
            errors.append(f"leak patterns: {bad}")
        by_id = {m["id"]: m for m in men}
        picks = out.get("sheets") or []
        if not 1 <= len(picks) <= 3:
            errors.append("need 1-3 sheets")
        sheets, cs = [], []
        for p in picks:
            m = by_id.get(p.get("id"))
            if not m or p.get("level") not in m["prices"]:
                errors.append(f"unknown sheet/level {p}")
                continue
            t = {**m["terms"], "unit_price": m["prices"][p["level"]]}
            sheets.append(complete_offer(case, t))
            cs.append(total_cost(case, t, standard_terms(threads[sid])))
        accepting = out.get("action") == "accept"
        if sheets and self.last_sent.get(sid) == sheets and not accepting:
            errors.append("identical to our last proposal; change level or package")
        if cs and min(cs) >= c_stand - 0.01 and not accepting:
            errors.append("our sheet is not better for us than the supplier's standing offer")
        if not accepting:
            for t in sheets:
                for pt in self.last_sent.get(sid) or []:
                    same = all(pt.get(k) == t.get(k) for k in pt if k != "unit_price")
                    if same and t["unit_price"] < pt["unit_price"] - 1e-9:
                        errors.append("our ask moved backwards (lower price than last round on the same package)")
        bank_by = {c["id"]: c for c in bank}
        claims = []
        for cid in out.get("claims") or []:
            if cid not in bank_by:
                errors.append(f"unknown claim {cid}")
            else:
                claims.append(bank_by[cid])
        if len(claims) > 2:
            errors.append("at most 2 claims per message")
        wl = self._whitelist(case, threads, sid, sheets, claims)
        stray = []
        for n in _nums(_strip_ids(body)):
            if n in wl or any(abs(n - w) <= 0.011 for w in wl) or (float(n).is_integer() and 0 <= n <= 36):
                continue
            stray.append(n)
        if stray:
            errors.append(f"numbers not in whitelist: {sorted(stray)}")
        return errors, sheets, cs, claims

    def compose(self, case, threads, sid):
        ctx, men, bank, c_stand, std = self._context(case, threads, sid)
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(ctx, ensure_ascii=False, default=str)},
        ]
        out, sheets, cs, claims = None, [], [], []
        for attempt in range(3):
            try:
                out = llm(messages)
            except Exception as e:  # noqa: BLE001
                self._log("llm_error", supplier=sid, error=str(e))
                continue
            errors, sheets, cs, claims = self._validate(case, threads, sid, out, men, bank, c_stand)
            self._log("llm_draft", supplier=sid, attempt=attempt, out=out, errors=errors)
            if not errors:
                break
            messages += [
                {"role": "assistant", "content": json.dumps(out)},
                {
                    "role": "user",
                    "content": "Rejected by validator: " + "; ".join(errors) + ". Return corrected JSON only.",
                },
            ]
            out = None
        if out is None:
            out, sheets, cs, claims = self._fallback(case, threads, sid, men, bank, c_stand)
        if out.get("action") == "accept":
            sheet_id, s_terms, c, std = self.acceptable(case, threads[sid])
            if sheet_id and c <= self.c_alt(case) and must_haves_ok(case, s_terms, std):
                return self._accept(case, sid, sheet_id, c, "llm recommends; code checked vs alternative")
        body = out["body"].rstrip()
        if claims:
            body += "\n\n" + "\n".join(c["sentence"] for c in claims)
        refs = sorted({i for c in claims for i in c["ids"]})
        for c in claims:
            self.used_claims |= set(c["ids"])
        self.last_sent[sid] = sheets
        self.last_ask_c[sid] = min(cs) if cs else None
        self._log(
            "send",
            supplier=sid,
            sheets=sheets,
            c=cs,
            c_stand=c_stand,
            claims=[c["id"] for c in claims],
            rationale=out.get("rationale"),
        )
        msg = {
            "subject": out.get("subject") or case["title"],
            "body": body,
            "term_sheets": [{"terms": t} for t in sheets],
        }
        if refs:
            msg["refs"] = refs
        if "forecast" in (out.get("attachments") or []) and not self.sent_forecast.get(sid):
            att, csv = forecast_attachment(case, sid)
            if att:
                msg["attachments"] = [att]
                self.sent_forecast[sid] = True
                self._log("attachment", supplier=sid, name=att["name"], csv=csv)
        return {"supplier_id": sid, "message": msg}

    def _fallback(self, case, threads, sid, men, bank, c_stand):
        """Deterministic fallback when the model fails three times: the standing package one level
        better for us, no claims, a plain body."""
        _, s_terms, _, _ = self.standing(case, threads[sid])
        match = next((m for m in men if all(m["terms"].get(k) == s_terms.get(k) for k in m["terms"])), men[0])
        level = "L1" if self._ours(threads[sid]) == 0 else "L0"
        t = complete_offer(case, {**match["terms"], "unit_price": match["prices"][level]})
        body = (
            f"Thank you for your offer and for the points you raised. We confirm our binding annual volume under "
            f"the attached term sheet and move towards you: unit price EUR {t['unit_price']:.2f}, "
            f"{describe(case, t)}. Please consider the figure below and let us know your best price on this "
            f"package.\n\nKind regards,\nHollerau Pumpenwerke GmbH, Purchasing"
        )
        claims = [c for c in bank if not (set(c["ids"]) & self.used_claims)][:1]
        return (
            {"subject": case["title"], "body": body, "rationale": "fallback"},
            [t],
            [total_cost(case, t, standard_terms(threads[sid]))],
            claims,
        )
