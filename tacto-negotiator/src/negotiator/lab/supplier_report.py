"""Deterministic, cited supplier brief. No provider calls or runtime policy changes.

Narrative uses recorded outcomes/terms and verbatim topic excerpts. Mentions are not
interpreted as preferences, and separate datasets never contribute to one analysis.
"""

import re
from collections import defaultdict

from negotiator.memory import supplier_author_matches

from .workspace import identity, messages, numeric, savings

TERMS = {
    "unit_price": ("unit price", " per recorded price unit"),
    "payment_days": ("payment", " days"), "contract_months": ("contract", " months"),
    "lead_time_days": ("lead time", " days"), "ppm_commitment": ("quality commitment", " ppm"),
    "volume_commitment_pct": ("volume commitment", "%"),
}
TOPICS = {
    "price": ("Price & costs", r"\b(price|cost|copper|material|index|preis|kosten)\b"),
    "payment": ("Payment terms", r"\b(payment|cash flow|zahlungsziel|net \d+|\d+.day payment)\b"),
    "commitment": ("Volume & commitment", r"\b(volume|commitment|forecast|contract|commit|binding)\b"),
    "delivery": ("Delivery & capacity", r"\b(delivery|lead time|capacity|allocation|lieferzeit)\b"),
    "quality": ("Quality & assurance", r"\b(quality|ppm|warranty|certification|inspection)\b"),
}


def scope(run):
    version = (run.get("provenance") or {}).get("data_sha256")
    return (run["arena_url"], version or f"unknown:{run['source']}:{run['run_id'] or run.get('campaign_id')}")


def reference(r, supplier, index=None):
    run, a = r["run"], r["attempt"]
    return {"negotiation_id": r["id"], "supplier_key": identity(run["arena_url"], run["environment"], supplier),
            "session_id": a.get("session_id"), "run_id": run["run_id"], "campaign_id": run.get("campaign_id"),
            "case_id": a["case_id"], "message_index": index, "dataset": scope(run)[1],
            "arena": run["arena_url"], "environment": run["environment"]}


def outcome(r, supplier):
    a = r["attempt"]
    result = a.get("result") or {}
    if a["status"] != "completed":
        return {"label": a["status"].replace("_", " ").capitalize(), "kind": a["status"]}
    if result.get("ended") is not True:
        return {"label": "Completion not confirmed", "kind": "unknown"}
    if result.get("deal") is True and result.get("supplier_id") == supplier:
        if result.get("must_haves_ok") is True:
            return {"label": "Valid deal", "kind": "valid"}
        if result.get("must_haves_ok") is False:
            return {"label": "Requirements failed", "kind": "invalid"}
        return {"label": "Deal · requirements unrecorded", "kind": "unverified"}
    if result.get("deal") is True and result.get("supplier_id"):
        return {"label": "Another supplier selected", "kind": "other"}
    if result.get("deal") is False:
        return {"label": "No deal", "kind": "no_deal"}
    return {"label": "Outcome not recorded", "kind": "unknown"}


def term_text(terms):
    text = [f"{label} {terms[k]:g}{unit}" for k, (label, unit) in TERMS.items()
            if numeric(terms.get(k))]
    if "index_clause" in terms:
        clause = terms["index_clause"]
        text.append("no index clause" if clause is None else "an index clause")
    return "; ".join(text[:5]) or "no comparable structured terms recorded"


def excerpts(body):
    # Do not rewrite supplier claims, strip negation or turn quoted instructions into policy.
    if not isinstance(body, str):
        return []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", body[:20000])
    return [s.strip()[:480] + ("…" if len(s.strip()) > 480 else "") for s in sentences
            if len(s.strip()) > 20]


def sheets(message):
    values = message.get("term_sheets")
    return [s for s in values if isinstance(s, dict) and isinstance(s.get("terms"), dict)] \
        if isinstance(values, list) else []


def session_brief(r, supplier):
    run, a = r["run"], r["attempt"]
    msgs = messages((a.get("threads") or {}).get(supplier, {}))
    offers = [(i, sheet["terms"]) for i, m in enumerate(msgs)
              if supplier_author_matches(m.get("from"), supplier)
              for sheet in sheets(m)]
    buyer = [(i, sheet["terms"]) for i, m in enumerate(msgs) if m.get("from") == "buyer"
             for sheet in sheets(m)]
    beats = []
    for label, entry in (("Supplier opened with", offers[0] if offers else None),
                         ("Buyer last proposed", buyer[-1] if buyer else None),
                         ("Supplier last offered", offers[-1] if len(offers) > 1 else None)):
        if entry:
            i, terms = entry
            beats.append({"text": f"{label} {term_text(terms)}.", "evidence": [reference(r, supplier, i)]})
    changes = []
    if offers:
        first, last = offers[0], offers[-1]
        for key, (label, unit) in TERMS.items():
            before, after = first[1].get(key), last[1].get(key)
            if numeric(before) and numeric(after) and before != after:
                changes.append({"field": key, "label": label, "before": before, "after": after,
                                "text": f"{label.capitalize()}: {before:g} → {after:g}{unit}",
                                "evidence": [reference(r, supplier, first[0]), reference(r, supplier, last[0])]})
    end = outcome(r, supplier)
    beats.append({"text": f"Recorded outcome: {end['label'].lower()}.", "evidence": [reference(r, supplier)]})
    return {"id": r["id"], "reference": reference(r, supplier), "case_id": a["case_id"],
            "date": run["started_at"], "updated_at": run["updated_at"], "agent": run["agent"],
            "author": run.get("author"), "run_name": run["name"], "dataset": scope(run)[1],
            "arena": run["arena_url"], "outcome": end, "messages": len(msgs), "summary": beats,
            "changes": changes, "savings": savings(r) if end["kind"] == "valid" else None,
            "truncated": bool((a.get("threads") or {}).get("evidence_truncated"))}


def build_report(records, supplier, nodes):
    ordered = sorted(records, key=lambda r: (r["run"]["started_at"], r["id"]), reverse=True)
    history = [session_brief(r, supplier) for r in ordered]
    partitions = defaultdict(list)
    for r, h in zip(ordered, history, strict=True):
        partitions[scope(r["run"])].append((r, h))
    reports = []
    for (arena, version), entries in partitions.items():
        rows = [h for _, h in entries]
        latest = rows[0]
        valid = sum(h["outcome"]["kind"] == "valid" for h in rows)
        cases = sorted({h["case_id"] for h in rows})
        latest_cases = {}
        for h in rows:
            latest_cases.setdefault(h["case_id"], h)
        eligible = [h for h in latest_cases.values() if h["savings"]]
        reduction = sum(h["savings"]["change_eur"] for h in eligible) if eligible else None
        topics = {}
        for key, (label, pattern) in TOPICS.items():
            evidence, sessions = [], set()
            for r, h in entries:
                msgs = messages((r["attempt"].get("threads") or {}).get(supplier, {}))
                for i, m in reversed(list(enumerate(msgs))):
                    if not supplier_author_matches(m.get("from"), supplier):
                        continue
                    quotes = [q for q in excerpts(m.get("body")) if re.search(pattern, q, re.I)]
                    quotes.sort(key=lambda q: not bool(re.search(
                        r"\b(cannot|need|require|welcome|accept|if|provided|but|prefer)\b", q, re.I)))
                    quote = quotes[0] if quotes else None
                    if quote:
                        sessions.add(h["id"])
                        if len(evidence) < 3:
                            evidence.append({**reference(r, supplier, i), "quote": quote})
                        break
            if sessions:
                topics[key] = {"title": label, "count": len(sessions),
                               "text": f"Mentioned by the supplier in {len(sessions)} of {len(rows)} conversations.",
                               "evidence": evidence}
        memory, approach, next_steps = [], [], []
        scoped_nodes = [n for n in nodes if n["values"].get("dataset") == version and any(
            e.get("arena") == arena for e in n["evidence"])]
        conflicts = [n for n in scoped_nodes if n["kind"] == "memory_conflict"]
        for n in [n for n in scoped_nodes if n["kind"] == "observation"
                  and n["values"].get("kind") == "supplier_statement"][:3]:
            v = n["values"]
            memory.append({"title": "Explicit supplier statement", "text":
                           f"The supplier stated a preference for {v['value']} {v['field'].replace('_', ' ')} "
                           f"in {v['session_count']} saved sessions. Reconfirm applicability before using it.",
                           "node_id": n["id"], "evidence": []})
        for case in cases[:4]:
            case_entries = [(r, h) for r, h in entries if h["case_id"] == case]
            values = defaultdict(set)
            for r, _ in case_entries:
                for m in messages((r["attempt"].get("threads") or {}).get(supplier, {})):
                    if supplier_author_matches(m.get("from"), supplier):
                        for sheet in sheets(m):
                            for k, value in (sheet.get("terms") or {}).items():
                                if k in TERMS and numeric(value):
                                    values[k].add(value)
            text = []
            for field in ("payment_days", "contract_months", "lead_time_days", "unit_price"):
                if field in values:
                    low, high = min(values[field]), max(values[field])
                    label, unit = TERMS[field]
                    text.append(f"{label} {low:g}{'–' + format(high, 'g') if high != low else ''}{unit}")
            if text:
                memory.append({"title": f"Observed offers · {case}",
                               "text": "; ".join(text[:3]) + ". Historical offers; reconfirm current terms.",
                               "evidence": [h["reference"] for _, h in case_entries[:3]]})
        if conflicts:
            approach.append({"title": "Reconfirm conflicting signals", "status": "Review needed",
                             "text": "Opposing supplier statements exist. Ask for current requirements before "
                             "building a concession around an assumed preference.", "node_id": conflicts[0]["id"],
                             "evidence": []})
        if "payment" in topics:
            approach.append({"title": "Keep payment inside the package", "status": "Suggested approach",
                             "text": "Ask what price change they would offer for different payment terms. "
                             "Compare the total cost of the permitted package.",
                             "evidence": topics["payment"]["evidence"][:1]})
        if "commitment" in topics or "delivery" in topics:
            t = topics.get("commitment", topics.get("delivery"))
            approach.append({"title": "Confirm the commitment before trading", "status": "Suggested approach",
                             "text": "Clarify volume, duration and delivery obligations before offering a commitment. "
                             "Stay within the current case requirements.", "evidence": t["evidence"][:1]})
        if "price" in topics:
            approach.append({"title": "Check the stated cost drivers", "status": "Suggested approach",
                             "text": "Check the supplier's cost claims against the latest supplied sources "
                             "before using them in a counteroffer.", "evidence": topics["price"]["evidence"][:1]})
        if not approach:
            approach.append({"title": "Establish the current requirements", "status": "Suggested approach",
                             "text": "Ask which terms matter now, then validate a complete package. The saved record "
                             "does not support a supplier-specific tactic yet.", "evidence": [latest["reference"]]})
        risky = next((h for h in rows if h["outcome"]["kind"] in {"failed", "interrupted", "invalid"}), None)
        if risky:
            next_steps.append({"title": "Resolve the recorded exception", "status": "Review first",
                               "text": f"Inspect {risky['case_id']} ({risky['outcome']['label'].lower()}) and its "
                               "original result before repeating that setup.", "evidence": [risky["reference"]]})
        moving = next((h for h in rows if h["changes"]), None)
        if moving:
            change = moving["changes"][0]
            next_steps.append({"title": f"Test the tradeoff in {moving['case_id']}", "status": "Untested suggestion",
                               "text": f"Observed change: {change['text'].lower()}. "
                               "Test one permitted term at a time and compare the total cost.",
                               "evidence": change["evidence"]})
        next_steps.append({"title": "Refresh the starting position", "status": "Before the next negotiation",
                           "text": "Confirm offer validity and check the newest supplied update. Reuse only evidence "
                           "that matches the current supplier, case and data version.",
                           "evidence": [latest["reference"]]})
        run = entries[0][0]["run"]
        policy = {"agent": run["agent"], "author": run.get("author"), "config": run.get("config", {}),
                  "commit": (run.get("provenance") or {}).get("commit"), "evidence": [latest["reference"]],
                  "text": "Latest saved configuration in this evidence partition. It is not proof of an active "
                  "deployment or the best-performing policy."}
        reports.append({"id": identity(arena, version), "arena": arena, "dataset": version,
                        "title": "Supplier relationship brief", "summary":
                        f"{len(rows)} saved negotiations across {len(cases)} "
                        f"{'case' if len(cases) == 1 else 'cases'}. "
                        f"{valid} confirmed deals with this supplier. "
                        f"Latest interaction ({latest['case_id']}): {latest['outcome']['label'].lower()}.",
                        "period": {"first": rows[-1]["date"], "last": latest["date"]},
                        "stats": {"sessions": len(rows), "valid_deals": valid,
                                  "other_selected": sum(h["outcome"]["kind"] == "other" for h in rows),
                                  "messages": sum(h["messages"] for h in rows), "cases": len(cases),
                                  "latest_case_reduction_eur": reduction, "cost_coverage": len(eligible)},
                        "latest": latest, "topics": list(topics.values()), "memory": memory[:6],
                        "approach": approach[:3], "next_steps": next_steps[:3], "policy": policy,
                        "limitations": ["Rule-based brief from saved outcomes, structured offers and quoted messages; "
                                        "it does not interpret the whole conversation or infer intent.",
                                        "Repeated experiments are not independent proof of a tactic's effectiveness. "
                                        "Suggestions require review; they do not change runtime policy."]})
    return {"partitions": reports, "history": history,
            "method": "Extractive, source-linked summary; no model or external calls.",
            "boundary": "Choose one dataset/arena partition for analysis. Supplier IDs reused in other datasets "
            "and unknown-source runs are kept separate."}
