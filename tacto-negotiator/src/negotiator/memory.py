"""Pure, strict v1 memory contract; supplier prose is never a runtime instruction.

Snapshots are canonical JSON, at most 64 KiB. Evidence has exactly evidence_id,
kind, field, direction, value and citation. Statements have a direction and null
value; observed offers have a bounded integer value and null direction. Citations
have exactly run_id/campaign_id (one non-null), attempt_id, supplier, message_index,
message_sha256, arena_url, environment, case_id and session_id. IDs hash their
canonical content. Original-message resolution is the lab MemoryStore's job.
Lessons contain only the allowlisted action vocabulary and supporting evidence IDs.
"""

import hashlib
import json
import re
from urllib.parse import urlsplit

MAX_MEMORY_BYTES = 65536
MAX_EVIDENCE = 512
MAX_COHORT = 1000
FIELDS = {"contract_months": 36, "payment_days": 120}
ENVIRONMENTS = {"simulator", "sandbox", "practice"}
SNAPSHOT_FIELDS = {
    "schema_version",
    "snapshot_id",
    "arena_url",
    "environment",
    "source_cases",
    "source_suppliers",
    "source_sessions",
    "lessons",
    "evidence",
}
CITATION_FIELDS = {
    "run_id",
    "campaign_id",
    "attempt_id",
    "supplier",
    "message_index",
    "message_sha256",
    "arena_url",
    "environment",
    "case_id",
    "session_id",
}


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_id(value) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def identifier(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,239}", value) is not None


def normalize_arena(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("invalid arena origin")
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        raise ValueError("invalid arena origin")
    host = url.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    port = url.port
    suffix = "" if port is None or port == {"http": 80, "https": 443}[url.scheme] else f":{port}"
    return f"{url.scheme}://{host}{suffix}"


def supplier_author_matches(sender, supplier_id) -> bool:
    """Match the actual arena author: exact supplier ID or sales@<ID suffix>.

    Arena messages use sales@70110 for sup:70110. Generic sales/supplier labels,
    missing authors, buyer text and another supplier's address are insufficient.
    """
    return (
        identifier(supplier_id)
        and isinstance(sender, str)
        and sender != "buyer"
        and sender
        in {
            supplier_id,
            "sales@" + supplier_id.split(":", 1)[-1],
        }
    )


def _exact(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("unexpected memory fields")


def _collection(value, *, maximum, key=lambda item: item, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError("invalid memory collection size")
    keys = [key(item) for item in value]
    if keys != sorted(set(keys)):
        raise ValueError("memory collections must be sorted and unique")


def _digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise ValueError("invalid content ID")


def derive_lessons(evidence: list[dict]) -> list[dict]:
    """Abstain for conflicts or less than three suppliers across two cases."""
    lessons = []
    for field in sorted(FIELDS):
        statements = [e for e in evidence if e["kind"] == "supplier_statement" and e["field"] == field]
        directions = {e["direction"] for e in statements}
        if len(directions) != 1:
            continue
        if len({e["citation"]["supplier"] for e in statements}) < 3:
            continue
        if len({e["citation"]["case_id"] for e in statements}) < 2:
            continue
        direction = next(iter(directions))
        lessons.append(
            {
                "lesson_id": f"preference:{field}:{direction}",
                "field": field,
                "direction": direction,
                "evidence_ids": sorted(e["evidence_id"] for e in statements),
            }
        )
    return sorted(lessons, key=lambda lesson: lesson["lesson_id"])


def validate_memory(snapshot: dict) -> dict:
    """Validate hashes, exact JSON schema, cohorts, support and contradiction abstention.

    Returns a detached JSON object. Does not consult a lab, execute source text,
    normalize content after hashing or permit arbitrary additional instructions.
    """
    try:
        return _validate_memory(snapshot)
    except (TypeError, KeyError, OverflowError, RecursionError) as error:
        raise ValueError("invalid memory snapshot") from error


def _validate_memory(snapshot):
    _exact(snapshot, SNAPSHOT_FIELDS)
    encoded = canonical_json(snapshot)
    if len(encoded.encode()) > MAX_MEMORY_BYTES:
        raise ValueError("memory snapshot too large")
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1:
        raise ValueError("invalid memory schema version")
    _digest(snapshot["snapshot_id"])
    if snapshot["snapshot_id"] != content_id({k: v for k, v in snapshot.items() if k != "snapshot_id"}):
        raise ValueError("memory content ID mismatch")
    if normalize_arena(snapshot["arena_url"]) != snapshot["arena_url"]:
        raise ValueError("memory arena must be normalized")
    if snapshot["environment"] not in ENVIRONMENTS:
        raise ValueError("invalid memory environment")
    for name in ("source_cases", "source_suppliers", "source_sessions"):
        _collection(snapshot[name], maximum=MAX_COHORT, minimum=0 if name == "source_suppliers" else 1)
        if any(not identifier(item) for item in snapshot[name]):
            raise ValueError("invalid memory provenance identity")
    _collection(snapshot["evidence"], maximum=MAX_EVIDENCE, key=lambda e: e["evidence_id"])
    for evidence in snapshot["evidence"]:
        _exact(evidence, {"evidence_id", "kind", "field", "direction", "value", "citation"})
        _digest(evidence["evidence_id"])
        if evidence["evidence_id"] != content_id({k: v for k, v in evidence.items() if k != "evidence_id"}):
            raise ValueError("evidence content ID mismatch")
        if evidence["field"] not in FIELDS:
            raise ValueError("unsupported memory field")
        if evidence["kind"] == "supplier_statement":
            if evidence["direction"] not in {"higher", "lower"} or evidence["value"] is not None:
                raise ValueError("invalid supplier statement")
        elif evidence["kind"] == "observed_offer":
            value = evidence["value"]
            if (
                evidence["direction"] is not None
                or type(value) is not int
                or not 0 <= value <= FIELDS[evidence["field"]]
            ):
                raise ValueError("invalid observed offer")
        else:
            raise ValueError("unsupported memory evidence")
        citation = evidence["citation"]
        _exact(citation, CITATION_FIELDS)
        if (citation["run_id"] is None) == (citation["campaign_id"] is None):
            raise ValueError("citation requires exactly one source record")
        for name in ("run_id", "campaign_id", "attempt_id", "supplier", "case_id", "session_id"):
            if citation[name] is not None and not identifier(citation[name]):
                raise ValueError("invalid citation identity")
            if name not in {"run_id", "campaign_id"} and citation[name] is None:
                raise ValueError("missing citation identity")
        if type(citation["message_index"]) is not int or not 0 <= citation["message_index"] < 5000:
            raise ValueError("invalid message index")
        _digest(citation["message_sha256"])
        if citation["arena_url"] != snapshot["arena_url"] or citation["environment"] != snapshot["environment"]:
            raise ValueError("citation differs from discovery scope")
        for key, cohort in (
            ("case_id", "source_cases"),
            ("supplier", "source_suppliers"),
            ("session_id", "source_sessions"),
        ):
            if citation[key] not in snapshot[cohort]:
                raise ValueError("citation absent from discovery cohort")
    _collection(snapshot["lessons"], maximum=4, key=lambda lesson: lesson["lesson_id"])
    eligible = {lesson["lesson_id"]: lesson for lesson in derive_lessons(snapshot["evidence"])}
    for lesson in snapshot["lessons"]:
        _exact(lesson, {"lesson_id", "field", "direction", "evidence_ids"})
        _collection(lesson["evidence_ids"], maximum=MAX_EVIDENCE, minimum=3)
        if lesson != eligible.get(lesson["lesson_id"]):
            raise ValueError("lesson lacks diverse consistent supplier evidence")
    return json.loads(encoded)
