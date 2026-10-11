"""Source-agnostic, versioned supplier briefs for negotiation model context.

The compiler runs before negotiation. Model text is advice only: every quote and
source ID is checked against the immutable package, and no brief can create terms.
"""

import csv
import json
import os

from .advice import AdviceCompletion, digest
from .package_advisor import bounded_call, complete
from .skill_docs import load_skill, skill_prompt

CONTRACT = "supplier-brief-v1"
KINDS = ("constraint", "preference", "refusal", "condition", "risk", "capability",
         "question", "context", "other")
MAX_SOURCE_TEXT = 1800
MAX_SOURCES = 16
MAX_PROMPT_BYTES = 18000
MAX_BRIEF_BYTES = 16000
TEXT_FIELDS = ("body", "text", "content", "note", "remarks", "comment", "description",
               "narrative", "headline", "title")


def system_prompt(expected_hash):
    return skill_prompt("brief", "supplier-brief", expected_hash)


def response_schema(_context):
    source = {"type": "string"}
    observation = {"type": "object", "additionalProperties": False,
                   "properties": {"source_id": source, "quote": source,
                                  "kind": {"type": "string", "enum": list(KINDS)},
                                  "interpretation": source},
                   "required": ["source_id", "quote", "kind", "interpretation"]}
    tactic = {"type": "object", "additionalProperties": False,
              "properties": {"approach": source, "source_ids": {"type": "array", "items": source}},
              "required": ["approach", "source_ids"]}
    conflict = {"type": "object", "additionalProperties": False,
                "properties": {"older_source_id": source, "newer_source_id": source,
                               "explanation": source},
                "required": ["older_source_id", "newer_source_id", "explanation"]}
    return {"type": "object", "additionalProperties": False,
            "properties": {"observations": {"type": "array", "items": observation},
                           "tactics": {"type": "array", "items": tactic},
                           "conflicts": {"type": "array", "items": conflict}},
            "required": ["observations", "tactics", "conflicts"]}


def _text(value):
    return value if isinstance(value, str) else ""


def _first_text(fact):
    return next((_text(fact.get(key)) for key in TEXT_FIELDS if _text(fact.get(key))), "")


def _csv_rows(package, name):
    out = {}
    for root in (package.root, package.release):
        path = root / "data" / f"{name}.csv" if root else None
        if path and path.is_file():
            with path.open(encoding="utf-8", newline="") as stream:
                out.update((row["id"], row) for row in csv.DictReader(stream) if row.get("id"))
    return out


def _record(ref, fact, text, supplier_id, source_type, *, part_id=None):
    body = _text(text).strip()
    if not body:
        return None
    return {"source_id": ref, "source_type": source_type,
            "supplier_id": supplier_id, "part_id": part_id,
            "date": _text(fact.get("date")), "speaker": _text(fact.get("speaker")),
            "text": body[:MAX_SOURCE_TEXT], "truncated": len(body) > MAX_SOURCE_TEXT}


def collect_sources(package, supplier_id, *, case=None, memory=None):
    """Collect dated text from any authorized package source and scoped case facts.

    New source formats can participate by supplying a citable fact ID and text-like
    field. Structured negotiation history and approved memory are marked separately.
    """
    if not isinstance(supplier_id, str) or not supplier_id.startswith("sup:"):
        raise ValueError("invalid supplier scope")
    rows = {}
    documents = _csv_rows(package, "documents")
    news = _csv_rows(package, "news")
    for ref in [*package.ids("doc:"), *package.ids("news:")]:
        fact = package.lookup(ref)
        if not isinstance(fact, dict):
            continue
        owner = fact.get("supplier") or fact.get("supplier_id")
        if owner not in (supplier_id, None, ""):
            continue
        if owner in (None, "") and not ref.startswith(("news:", "doc:")):
            continue
        if ref.startswith("doc:"):
            try:
                body = package.document(ref)
            except (FileNotFoundError, ValueError):
                body = documents.get(ref, {}).get("body") or documents.get(ref, {}).get("text")
            kind = "document" if owner == supplier_id else "market_document"
        elif ref.startswith("news:"):
            body = news.get(ref, {}).get("body") or fact.get("body") or fact.get("headline")
            kind = "news" if owner == supplier_id else "market_news"
        else:
            continue
        row = _record(ref, fact, body, owner or None, kind, part_id=fact.get("part"))
        if row:
            rows[ref] = row
    for ref, fact in package.facts.items():
        if (not isinstance(ref, str) or ref.startswith(("doc:", "news:"))
                or not isinstance(fact, dict)
                or (fact.get("supplier") or fact.get("supplier_id")) != supplier_id):
            continue
        row = _record(ref, fact, _first_text(fact), supplier_id, "package_fact",
                      part_id=fact.get("part") or fact.get("part_id"))
        if row:
            rows[ref] = row
    if package.db is not None:
        history = package.query("SELECT * FROM negotiation_history WHERE supplier_id = ? ORDER BY date",
                                (supplier_id,), limit=1000)
        for item in history:
            # A saved historical row is an observation, never a fresh supplier promise.
            detail = _text(item.get("note")).strip()
            if not detail:
                detail = (f"Historical {item.get('type') or 'negotiation'}: asked "
                          f"{item.get('asked_pct')}%, settled {item.get('settled_pct')}%.")
            ref = _text(item.get("id")) or "history:" + digest(item)[:20]
            row = _record(ref, item, detail, supplier_id, "negotiation_history",
                          part_id=item.get("part_id"))
            if row:
                rows[ref] = row
    for ref, fact in (case or {}).get("facts", {}).items():
        if not isinstance(ref, str) or not isinstance(fact, dict):
            continue
        owner = fact.get("supplier") or fact.get("supplier_id")
        if owner not in (supplier_id, None, ""):
            continue
        body = _first_text(fact)
        row = _record(ref, fact, body, owner or None, "case_fact", part_id=fact.get("part"))
        if row:
            rows[ref] = row
    if memory is not None:
        from .memory import validate_memory

        checked = validate_memory(memory)
        for item in checked["evidence"]:
            citation = item["citation"]
            if citation["supplier"] != supplier_id:
                continue
            detail = (f"Approved historical {item['kind']}: {item['field']} "
                      f"{item['direction'] if item['direction'] is not None else item['value']}; "
                      f"case {citation['case_id']}, message {citation['message_index']}.")
            ref = "memory:" + item["evidence_id"]
            rows[ref] = _record(ref, {}, detail, supplier_id, "approved_memory")
    return sorted(rows.values(), key=lambda r: (r["date"], r["source_id"]), reverse=True)


def selected_sources(sources):
    """Bound input while preserving recent supplier evidence before market context."""
    owned = [s for s in sources if s["supplier_id"]]
    market = [s for s in sources if not s["supplier_id"]]
    selected = (owned[:MAX_SOURCES - min(3, len(market))] + market[:3])[:MAX_SOURCES]
    while selected and len(json.dumps(selected, ensure_ascii=False).encode()) > MAX_PROMPT_BYTES:
        selected.pop()
    return selected


def extractive_brief(package, supplier_id, *, case=None, memory=None):
    sources = selected_sources(collect_sources(package, supplier_id, case=case, memory=memory))
    return {"schema_version": 1, "contract": CONTRACT, "supplier_id": supplier_id,
            "data_sha256": package.manifest["sha256"], "source_digest": digest(sources),
            "status": "extractive", "sources": sources, "observations": [],
            "tactics": [], "conflicts": []}


def validate_answer(answer, sources):
    if isinstance(answer, AdviceCompletion):
        answer = answer.response
    if not isinstance(answer, dict) or set(answer) != {"observations", "tactics", "conflicts"}:
        raise ValueError("invalid brief response")
    observations, tactics, conflicts = (answer[k] for k in ("observations", "tactics", "conflicts"))
    if (not all(isinstance(x, list) for x in (observations, tactics, conflicts))
            or len(observations) > 12 or len(tactics) > 5 or len(conflicts) > 6):
        raise ValueError("brief collection bound")
    by_id = {s["source_id"]: s for s in sources}
    if len(json.dumps(answer, ensure_ascii=False).encode()) > MAX_BRIEF_BYTES:
        raise ValueError("brief response too large")
    valid_observations = [item for item in observations if (
        isinstance(item, dict) and set(item) == {"source_id", "quote", "kind", "interpretation"}
        and isinstance(item["source_id"], str) and item["source_id"] in by_id
        and item["kind"] in KINDS
        and isinstance(item["quote"], str) and 8 <= len(item["quote"]) <= 500
        and item["quote"] in by_id[item["source_id"]]["text"]
        and isinstance(item["interpretation"], str)
        and 3 <= len(item["interpretation"]) <= 240)]
    observed_ids = {item["source_id"] for item in valid_observations}
    valid_tactics = [item for item in tactics if (
        isinstance(item, dict) and set(item) == {"approach", "source_ids"}
        and isinstance(item["approach"], str) and 5 <= len(item["approach"]) <= 240
        and isinstance(item["source_ids"], list) and 1 <= len(item["source_ids"]) <= 4
        and all(isinstance(ref, str) and ref in observed_ids for ref in item["source_ids"]))]
    valid_conflicts = [item for item in conflicts if (
        isinstance(item, dict) and set(item) == {"older_source_id", "newer_source_id", "explanation"}
        and isinstance(item["older_source_id"], str) and isinstance(item["newer_source_id"], str)
        and item["older_source_id"] in by_id and item["newer_source_id"] in by_id
        and item["older_source_id"] != item["newer_source_id"]
        and by_id[item["older_source_id"]]["date"] <= by_id[item["newer_source_id"]]["date"]
        and isinstance(item["explanation"], str) and 5 <= len(item["explanation"]) <= 240)]
    return {"observations": valid_observations, "tactics": valid_tactics,
            "conflicts": valid_conflicts}


def compile_brief(package, supplier_id, *, complete_fn=complete, timeout_s=45.0):
    brief = extractive_brief(package, supplier_id)
    skill = load_skill("brief", "supplier-brief")
    context = {"response_contract": CONTRACT, "skill_sha256": skill.sha256,
               "supplier_id": supplier_id,
               "data_sha256": brief["data_sha256"], "sources": brief["sources"]}
    answer = bounded_call(complete_fn, context, timeout_s)
    validated = validate_answer(answer, brief["sources"])
    if not validated["observations"]:
        raise ValueError("no cited observations admitted")
    raw = answer.response if isinstance(answer, AdviceCompletion) else answer
    usage = answer.usage if isinstance(answer, AdviceCompletion) else {}
    return {**brief, "status": "model", **validated,
            "model": os.environ.get("LLM_MODEL"),
            "skill_sha256": skill.sha256,
            "provider_usage": {k: usage[k] for k in ("prompt_tokens", "completion_tokens")
                               if type(usage.get(k)) is int and usage[k] >= 0},
            "rejected_items": {k: len(raw[k]) - len(validated[k])
                               for k in ("observations", "tactics", "conflicts")}}


def brief_path(package, supplier_id):
    return (package.root.parent / "briefs" / package.manifest["sha256"]
            / (supplier_id.replace(":", "-") + ".json"))


def save_brief(package, brief):
    path = brief_path(package, brief["supplier_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(brief, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode()) > 80000:
        raise ValueError("brief file too large")
    staged = path.with_suffix(".tmp")
    staged.write_text(raw, encoding="utf-8")
    staged.replace(path)
    return path


def load_brief(package, supplier_id):
    """Revalidate persisted model output against the current package before use."""
    path = brief_path(package, supplier_id)
    if not path.is_file() or path.stat().st_size > 80000:
        return extractive_brief(package, supplier_id)
    fresh = extractive_brief(package, supplier_id)
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fresh
    if (not isinstance(saved, dict) or saved.get("schema_version") != 1
            or saved.get("contract") != CONTRACT or saved.get("supplier_id") != supplier_id
            or saved.get("data_sha256") != fresh["data_sha256"]
            or saved.get("source_digest") != fresh["source_digest"]
            or saved.get("sources") != fresh["sources"]
            or saved.get("status") not in ("extractive", "model")):
        return fresh
    try:
        checked = validate_answer({k: saved[k] for k in ("observations", "tactics", "conflicts")},
                                  fresh["sources"])
    except (KeyError, TypeError, ValueError):
        return fresh
    if any(checked[k] != saved[k] for k in ("observations", "tactics", "conflicts")):
        return fresh
    return {**fresh, "status": saved["status"], **checked,
            "model": saved.get("model"), "provider_usage": saved.get("provider_usage", {}),
            "rejected_items": saved.get("rejected_items", {}),
            **({"skill_sha256": saved["skill_sha256"]} if isinstance(saved.get("skill_sha256"), str) else {})}


def runtime_view(package, supplier_id, *, case=None, memory=None, max_sources=4,
                 issue_text=""):
    """Small supplier-scoped brief, plus current case evidence not known at prep time."""
    brief = load_brief(package, supplier_id)
    current = collect_sources(package, supplier_id, case=case, memory=memory)
    parts = set((case or {}).get("parts") or [])

    def applies(source):
        return not parts or not source["part_id"] or source["part_id"] in parts

    fresh_case = [s for s in current if s["source_type"] in ("case_fact", "approved_memory")
                  and applies(s) and s["source_id"] not in {r["source_id"] for r in brief["sources"]}]
    excerpt_limit = min(max_sources, 2) if brief["status"] == "model" and not issue_text else max_sources
    owned = [s for s in brief["sources"] if s["supplier_id"] and applies(s)]
    market = [s for s in brief["sources"] if not s["supplier_id"] and applies(s)]
    if issue_text:
        from .assessment import FIELD_CUES

        relevant = {field for field, cue in FIELD_CUES.items() if cue.search(issue_text)}
        words = {word for word in issue_text.lower().split() if len(word) >= 5}

        def relevance(source):
            body = source["text"].lower()
            issue_hits = sum(bool(FIELD_CUES[field].search(body)) for field in relevant)
            word_hits = sum(word.strip(".,;:?!") in body for word in words)
            authority = source["source_type"] not in ("negotiation_history", "approved_memory")
            return (issue_hits, word_hits, authority, source["date"])

        owned = sorted(owned, key=relevance, reverse=True)
        fresh_case = sorted(fresh_case, key=relevance, reverse=True)
    fresh = fresh_case[:1]
    market_slot = market[:1] if not issue_text or not owned else []
    retained = fresh + owned[:max(0, excerpt_limit - len(fresh) - len(market_slot))] + market_slot
    if issue_text and brief["conflicts"]:
        by_source = {s["source_id"]: s for s in owned}
        for conflict in brief["conflicts"]:
            pair = (conflict["older_source_id"], conflict["newer_source_id"])
            present = {s["source_id"] for s in retained}
            if len(set(pair) & present) != 1:
                continue
            missing = next((by_source[ref] for ref in pair if ref not in present and ref in by_source), None)
            if missing is None:
                continue
            if len(retained) < excerpt_limit:
                retained.append(missing)
            elif retained and retained[-1]["source_id"] not in pair:
                retained[-1] = missing
    excerpts = [{"source_id": s["source_id"], "source_type": s["source_type"],
                 "date": s["date"], "text": s["text"][:900],
                 "truncated": s["truncated"] or len(s["text"]) > 900}
                for s in retained]
    by_id = {s["source_id"]: s for s in brief["sources"]}
    observations = [{**o, "date": by_id[o["source_id"]]["date"],
                     "source_type": by_id[o["source_id"]]["source_type"]}
                    for o in brief["observations"] if applies(by_id[o["source_id"]])][:8]
    allowed = {o["source_id"] for o in observations} | {s["source_id"] for s in retained}
    tactics = [t for t in brief["tactics"] if all(ref in allowed for ref in t["source_ids"])][:3]
    conflicts = [c for c in brief["conflicts"] if c["older_source_id"] in allowed
                 and c["newer_source_id"] in allowed][:3]
    return {"status": brief["status"], "supplier_id": supplier_id,
            "data_sha256": brief["data_sha256"], "source_digest": brief["source_digest"],
            "compiler_skill_sha256": brief.get("skill_sha256"),
            "excerpts": excerpts, "observations": observations, "tactics": tactics,
            "conflicts": conflicts}
