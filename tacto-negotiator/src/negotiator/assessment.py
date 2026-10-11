"""Source-linked supplier assessment; derived state never grants execution authority.

The owned thread is the factual ledger. Model observations are admitted one by one,
keyed to a history digest, and can be rebuilt after restart. A citation proves only
where an interpretation came from, not that the interpretation is correct.
"""

import hashlib
import json
import re
from pathlib import Path

SCHEMA = "supplier-assessment-v1"
PROMPT = "capacity-advice-v2"
KINDS = {"objection", "refusal", "conditional_trade", "question", "stated_terms",
         "preference", "concession", "contradiction"}
CONDITION = re.compile(r"\b(if|only if|only with|only when|unless|provided that|subject to|against|"
                       r"wenn|nur wenn|falls|sofern|vorausgesetzt)\b", re.I)
REFUSAL = re.compile(r"\b(no|not|cannot|can't|won't|refus\w*|reject\w*|unable|"
                     r"nicht|kein\w*|ablehn\w*)\b", re.I)
QUESTION = re.compile(r"\?\s*$|\b(which|what|when|who|how|welch\w*|wie|wann)\b", re.I)
FIELD_CUES = {
    "contract_months": re.compile(
        r"\b(?:contracts?|commitments?|term|laufzeit|vertragsdauer|vertragslaufzeit)\b", re.I),
    "lead_time_days": re.compile(r"\b(?:deliver\w*|delivery|lead[ -]?times?|schedule|liefer\w*|vorlaufzeit)\b", re.I),
    "payment_days": re.compile(r"\b(?:pay\w*|payment|invoice|cash|zahl\w*|rechnung\w*)\b", re.I),
    "volume_per_year": re.compile(r"\b(?:volume|quantity|units?|pieces?|pcs|menge|stückzahl)\b", re.I),
    "unit_price": re.compile(r"\b(?:price|cost|eur|preis|kosten)\b|€", re.I),
}
NEGATION = re.compile(r"\b(?:no|not|cannot|can't|won't|without|kein\w*|nicht|unmöglich)\b", re.I)
CORRECTION = re.compile(r"\b(?:now|no longer|instead|revised|corrected|jetzt|nun|doch|stattdessen)\b", re.I)
OBJECTION = re.compile(r"\b(?:need|require|cannot|can't|refus\w*|reject\w*|unable|prefer|help|"
                       r"limited|constrain\w*|necessitat\w*|tight|longer|shorter|not|"
                       r"brauchen|benötig\w*|nötig|knapp|begrenzt)\b", re.I)
OFFER_CUE = re.compile(r"\b(?:offer|alternatively|alternative|alternativ|wahlweise|"
                       r"angebot|anbieten|bieten)\b", re.I)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def sources(case, events, supplier_id, notes=()):
    """Public supplier messages and supplier-scoped dated documents only."""
    part = (case.get("parts") or [None])[0] if len(case.get("parts") or []) == 1 else None
    out = {}
    for index, event in enumerate(events):
        if event.get("from") == "buyer" or not isinstance(event.get("body"), str):
            continue
        body = event["body"]
        source_id = event.get("message_id") or event.get("id") or f"message:{index}:{digest(body)[:12]}"
        out[(index, None)] = {"source_id": str(source_id), "message_index": index,
                              "public_note_id": None, "source_role": "supplier", "body": body,
                              "supplier_id": supplier_id, "part_id": part,
                              "date": event.get("date") or event.get("created_at")}
    for note in notes:
        if (not isinstance(note, dict) or not isinstance(note.get("id"), str)
                or not isinstance(note.get("text"), str)
                or note.get("supplier_id", supplier_id) != supplier_id
                or note.get("supplier", supplier_id) != supplier_id
                or note.get("part", part) not in (None, part)):
            continue
        out[(-1, note["id"])] = {"source_id": note["id"], "message_index": -1,
                                 "public_note_id": note["id"], "source_role": "public_document",
                                 "body": note["text"], "supplier_id": supplier_id,
                                 "part_id": part, "date": note.get("date")}
    return out


def _condition_spans(quote):
    """Preserve the full conditional statement; ambiguous splits remain unresolved."""
    match = CONDITION.search(quote)
    if match is None:
        return None
    before, after = quote[:match.start()].strip(), quote[match.end():].strip()
    if not after or (not before and match.start() != 0):
        return {"antecedent": None, "consequence": None, "status": "unresolved"}
    if match.group().lower() == "against":
        return {"antecedent": after, "consequence": before, "status": "explicit"}
    if match.start() == 0:
        separator = re.search(r"[,;:]", after)
        if separator is None:
            return {"antecedent": None, "consequence": None, "status": "unresolved"}
        antecedent, consequence = after[:separator.start()].strip(), after[separator.end():].strip()
    else:
        antecedent, consequence = after, before
    return {"antecedent": antecedent or None, "consequence": consequence or None,
            "status": "explicit" if antecedent and consequence else "unresolved"}


def _field_span(quote, field):
    """Locate a field's own clause; a shared unit such as 'days' is never evidence."""
    cue = FIELD_CUES.get(field)
    if cue is None:
        return None
    for clause in re.finditer(r".+?(?:[.!?;](?!\d)|$)", quote, re.S):
        match = cue.search(clause.group())
        if match:
            return {"start": clause.start(), "end": clause.end(),
                    "quote": clause.group().strip(), "cue": match.group()}
    return None


def _observation(quote, field, source_start):
    span = _field_span(quote, field)
    if span is None:
        return None
    clause = quote[span["start"]:span["end"]]
    cue = FIELD_CUES[field].search(clause)
    numbers = list(re.finditer(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", clause))
    def gap(number):
        if number.end() <= cue.start():
            return cue.start() - number.end()
        if number.start() >= cue.end():
            return number.start() - cue.end()
        return 0

    nearest = min(numbers, key=gap) if numbers else None
    value = float(nearest.group().replace(",", ".")) if nearest else None
    if value is not None and value.is_integer():
        value = int(value)
    unit = ("days" if re.search(r"\b(?:days?|tage?n?)\b", clause, re.I) else
            "months" if re.search(r"\b(?:months?|monate?n?)\b", clause, re.I) else
            "years" if re.search(r"\b(?:years?|jahre?n?)\b", clause, re.I) else
            "eur" if re.search(r"\bEUR\b|€", clause, re.I) else None)
    direction = ("increase" if re.search(r"\b(?:longer|more|higher|increase|länger|mehr|höher)\b", clause, re.I)
                 else "decrease" if re.search(r"\b(?:shorter|less|lower|reduce|kürzer|weniger|niedriger)\b",
                                              clause, re.I) else None)
    return {"field": field, "requested_direction": direction, "value": value, "unit": unit,
            "polarity": "negative" if NEGATION.search(clause) else "positive",
            "source_span": {"start": source_start + span["start"],
                            "end": source_start + span["end"]},
            "explicit": True}


def condition_supported(observation, candidate):
    """Only a verifiable antecedent can authorize a conditional change."""
    condition = observation.get("condition")
    if not condition:
        return True
    if condition.get("status") != "explicit":
        return False
    antecedent = condition["antecedent"]
    if "unless" in observation["span"]["quote"].lower():
        return False
    mentioned = [f for f in candidate if _field_span(antecedent, f)]
    if not mentioned:
        return False
    for field in mentioned:
        value = candidate.get(field)
        if type(value) not in (int, float):
            return False
        if field == "contract_months" and re.search(r"\byears?|jahre?\b", antecedent, re.I):
            value /= 12
        observed = _observation(antecedent, field, 0)
        if observed["value"] is None or abs(observed["value"] - value) >= 1e-6:
            return False
    return True


def stated_terms_support(quote, fields, candidate):
    """A quoted supplier alternative may support a buyer counter on its stated fields.

    Delivery can be rounded up to the next legal buyer option. The quote never
    authorizes a price, acceptance or a field it does not itself specify.
    """
    if not OFFER_CUE.search(quote) or not fields:
        return False
    for field in fields:
        observed = _observation(quote, field, 0)
        value = candidate.get(field)
        if observed is None or observed["value"] is None or type(value) not in (int, float):
            return False
        stated = observed["value"]
        if field == "contract_months" and observed["unit"] == "years":
            stated *= 12
        if field == "lead_time_days":
            if value < stated:
                return False
        elif abs(value - stated) >= 1e-6:
            return False
    return True


def _supersedes(newer, older):
    if (newer is older or not set(newer["fields"]) & set(older["fields"])
            or not (newer["source"]["message_index"] > older["source"]["message_index"]
                    or (older["source"]["source_role"] == "public_document"
                        and newer["source"]["source_role"] == "supplier"))):
        return False
    if newer["kind"] == "refusal":
        return True
    return (older["kind"] == "refusal" and newer["kind"] in {"concession", "stated_terms"}
            and CORRECTION.search(newer["span"]["quote"]) is not None)


def admit(raw, case, events, supplier_id, notes=(), *, session_id=None, prompt_version=PROMPT):
    """Return admitted events and per-item rejection codes, without all-or-nothing parsing."""
    catalog = sources(case, events, supplier_id, notes)
    history_hash = digest(events)
    if not isinstance(raw, list):
        return [], [{"index": -1, "reason": "observations_not_array"}]
    admitted, rejected = [], []
    allowed_fields = set(case.get("negotiable") or [])
    for position, item in enumerate(raw[:12]):
        reason = None
        if not isinstance(item, dict):
            reason = "observation_not_object"
        else:
            index, note_id = item.get("message_index"), item.get("public_note_id")
            source = catalog.get((index, note_id)) if type(index) is int else None
            quote, kind, fields = item.get("quote"), item.get("kind"), item.get("addressed_fields")
            if (source is None or kind not in KINDS or not isinstance(quote, str)
                    or not 8 <= len(quote) <= 2000 or quote not in source["body"]):
                reason = "invalid_source_or_quote"
            elif (not isinstance(fields, list) or any(f not in allowed_fields for f in fields)
                  or len(fields) != len(set(fields))):
                reason = "invalid_fields"
            elif kind == "refusal" and not REFUSAL.search(quote):
                reason = "refusal_without_cue"
            elif kind == "question" and not QUESTION.search(quote):
                reason = "question_without_cue"
            elif kind == "objection" and not OBJECTION.search(quote):
                reason = "objection_without_constraint"
            elif kind == "conditional_trade" and not CONDITION.search(quote):
                reason = "condition_without_cue"
            elif kind != "conditional_trade" and CONDITION.search(quote) and kind not in {"refusal", "contradiction"}:
                reason = "condition_mislabeled"
            elif any(_field_span(quote, field) is None for field in fields):
                reason = "field_without_cue"
        if reason:
            rejected.append({"index": position, "reason": reason})
            continue
        span = source["body"].index(quote)
        condition = _condition_spans(quote) if kind == "conditional_trade" else None
        interpretation = "explicit" if kind in {"refusal", "question", "stated_terms", "conditional_trade",
                                                 "concession"} else "inference"
        event = {"schema": SCHEMA, "prompt_version": prompt_version,
                 "session_id": session_id, "case_id": case.get("case_id"), "supplier_id": supplier_id,
                 "history_hash": history_hash, "latest_supplier_index": max(
                     (i for i, e in enumerate(events) if e.get("from") != "buyer"), default=-1),
                 "source": {k: v for k, v in source.items() if k != "body"},
                 "span": {"start": span, "end": span + len(quote), "quote": quote},
                 "kind": kind, "interpretation": interpretation, "fields": list(fields),
                 "field_spans": {field: _field_span(quote, field) for field in fields},
                 "observations": [_observation(quote, field, span) for field in fields],
                 "polarity": "negative" if NEGATION.search(quote) else "positive",
                 "condition": condition, "lifecycle": "active", "lifecycle_reason": None,
                 "prior_source_id": None,
                 "uncertainty": (["conditional consequence unresolved"] if condition and
                                 condition["status"] != "explicit" else [])}
        event["event_id"] = "sha256:" + digest(event)
        admitted.append(event)
    # Current explicit refusals supersede older scoped preferences/trades. Retain both records.
    for event in admitted:
        for newer in admitted:
            if _supersedes(newer, event):
                event["lifecycle"] = "superseded"
                event["lifecycle_reason"] = "newer explicit update on the same field"
                event["prior_source_id"] = newer["source"]["source_id"]
    return admitted, rejected


def refused_candidate(events, reference, candidate):
    """A current explicit scoped refusal vetoes the matching non-price trade.

    This deliberately recognizes only bounded numeric or comparative refusals. Other
    prose remains uncertainty and is never interpreted as a reason to concede.
    """
    state = {}
    for event in events:
        if event.get("from") == "buyer":
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", event.get("body") or ""):
            negative = bool(REFUSAL.search(sentence))
            positive = bool(re.search(r"\b(agree|accept|works|possible|can offer)\b", sentence, re.I))
            if not (negative or positive):
                continue
            for field, cue in FIELD_CUES.items():
                value = candidate.get(field)
                if (not cue.search(sentence) or value == reference.get(field)
                        or type(value) not in (int, float)):
                    continue
                numeric = re.search(rf"(?<!\d){re.escape(str(value))}(?!\d)", sentence)
                before = reference.get(field)
                comparative = (field == "contract_months" and type(before) in (int, float) and value > before
                               and re.search(r"\blonger\b", sentence, re.I))
                if numeric or comparative:
                    state[field] = "refused" if negative else "accepted"
    return any(value == "refused" for value in state.values())


def resolved_historical_constraint(body, fields):
    """A current explicit resolution stops a historical note justifying a new trade."""
    if not re.search(r"\b(no longer|resolved|now stable|can meet)\b", body, re.I):
        return False
    return any((field in FIELD_CUES and FIELD_CUES[field].search(body))
               or (field in {"lead_time_days", "volume_per_year", "contract_months"}
                   and re.search(r"\bcapacity\b", body, re.I)) for field in fields)


class AssessmentStore:
    """Append-only derived observations; stale/session-mismatched records are never replayed."""

    def __init__(self, path):
        self.path = Path(path)

    def append(self, events):
        if not events:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        import os

        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        self.path.chmod(0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def reconstruct(self, case, events, supplier_id, *, session_id, notes=()):
        if not self.path.is_file() or not session_id:
            return []
        allowed = sources(case, events, supplier_id, notes)
        result = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                source = item["source"]
                span = item["span"]
                actual = allowed.get((source["message_index"], source["public_note_id"]))
                if (item["schema"] == SCHEMA and item["session_id"] == session_id
                        and item["supplier_id"] == supplier_id and item["case_id"] == case.get("case_id")
                        and item["kind"] in KINDS
                        and isinstance(item["fields"], list)
                        and all(isinstance(f, str) and f in case.get("negotiable", [])
                                for f in item["fields"])
                        and all(_field_span(span["quote"], f) is not None for f in item["fields"])
                        and source["source_role"] in ("supplier", "public_document")
                        and isinstance(item["condition"], (dict, type(None)))
                        and item["lifecycle"] in ("active", "superseded")
                        and actual is not None
                        and actual["source_id"] == source["source_id"]
                        and actual["body"][span["start"]:span["end"]] == span["quote"]):
                    result.append(item)
            except (KeyError, ValueError, TypeError, IndexError):
                continue
        # Carry source-valid facts forward as history grows, while retaining conflicts.
        # Admission decisions still use the current snapshot and never replay a prior choice.
        for index, item in enumerate(result):
            newer_refusal = None
            for newer in result:
                if _supersedes(newer, item):
                    newer_refusal = newer
            if newer_refusal:
                result[index] = {**item, "lifecycle": "superseded",
                                 "lifecycle_reason": "newer explicit update on the same field",
                                 "prior_source_id": newer_refusal["source"]["source_id"]}
        return result

    def reservations(self, session_id):
        """Unknown attempts remain charged after a restart; corrupt rows grant no retry."""
        if not self.path.is_file() or not session_id:
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                if (item.get("record") == "reservation" and item.get("session_id") == session_id
                        and isinstance(item.get("update_hash"), str)
                        and type(item.get("seconds")) in (int, float)
                        and 0 < item["seconds"] <= 8):
                    out.append(item)
            except (ValueError, TypeError):
                continue
        return out
