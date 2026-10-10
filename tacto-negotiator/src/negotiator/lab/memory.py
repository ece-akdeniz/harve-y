"""Live projection of original owned transcripts, with immutable memory snapshots.

Reads stored runs and loop records in one SQLite read transaction, without importing
or constructing LoopStore or invoking its promotion hooks. Original imports come
from the owned-session API and require supplier transcripts. Canonical arena/session
identities deduplicate originals; campaigns precede tracked runs, then imports.
Every eligible selected discovery session
and its full known supplier cohort remain in snapshot provenance, even without a
signal. Graph excerpts are untrusted display text; snapshots contain no excerpts.
"""

import json
import re
import sqlite3
from pathlib import Path

from negotiator.memory import (
    ENVIRONMENTS,
    FIELDS,
    MAX_COHORT,
    MAX_EVIDENCE,
    canonical_json,
    content_id,
    derive_lessons,
    identifier,
    normalize_arena,
    supplier_author_matches,
    validate_memory,
)

from .loop_models import Outcome, Start, Suite
from .models import Run

# Full sentences only: negation, quoted assertions and embedded instructions do
# not turn into a preference. The small vocabulary intentionally misses paraphrases.
PHRASES = {
    ("contract_months", "higher"): {
        "we prefer longer contracts",
        "we prefer longer contract terms",
        "we prefer longer commitments",
    },
    ("contract_months", "lower"): {
        "we prefer shorter contracts",
        "we prefer shorter contract terms",
        "we prefer shorter commitments",
    },
    ("payment_days", "lower"): {
        "we prefer faster payment",
        "we prefer earlier payment",
        "we prefer shorter payment terms",
        "faster payment helps our cash flow",
    },
    ("payment_days", "higher"): {
        "we prefer later payment",
        "we prefer longer payment terms",
    },
}


def _statements(body):
    if not isinstance(body, str) or len(body) > 8000:
        return []
    # Use an explicit conservative allowlist for whole messages, not substring
    # matching inside a supplier's instruction, quotation or hypothetical.
    sentences = [" ".join(s.strip().lower().split()) for s in re.split(r"[.!?\n]+", body) if s.strip()]
    allowed = set().union(*PHRASES.values())
    if not sentences or any(sentence not in allowed for sentence in sentences):
        return []
    return sorted(key for key, phrases in PHRASES.items() if any(sentence in phrases for sentence in sentences))


def _original(attempt):
    result = attempt.get("result")
    return (
        attempt.get("status") == "completed"
        and identifier(attempt.get("session_id"))
        and isinstance(result, dict)
        and result.get("ended") is True
    )


def _suppliers(threads):
    return sorted(
        supplier for supplier, thread in threads.items() if identifier(supplier) and isinstance(thread, (dict, list))
    )


def _complete_supplier_threads(threads):
    suppliers = _suppliers(threads)
    if not suppliers or len(suppliers) != len(threads):
        return False
    for supplier in suppliers:
        thread = threads[supplier]
        if isinstance(thread, dict) and thread.get("supplier_id", supplier) != supplier:
            return False
        messages = thread.get("messages", []) if isinstance(thread, dict) else thread
        if not isinstance(messages, list) or not any(
            isinstance(message, dict) and supplier_author_matches(message.get("from"), supplier) for message in messages
        ):
            return False
    return True


def _observations(session, threads):
    observations = {}
    for supplier in _suppliers(threads):
        thread = threads[supplier]
        if isinstance(thread, dict) and thread.get("supplier_id", supplier) != supplier:
            continue
        messages = thread.get("messages", []) if isinstance(thread, dict) else thread
        if not isinstance(messages, list):
            continue
        for index, message in enumerate(messages[:5000]):
            if not isinstance(message, dict) or not supplier_author_matches(message.get("from"), supplier):
                continue
            citation = {k: v for k, v in session.items() if k != "suppliers"}
            citation.update(supplier=supplier, message_index=index, message_sha256=content_id(message))
            extracted = [
                ("supplier_statement", field, direction, None) for field, direction in _statements(message.get("body"))
            ]
            sheets = message.get("term_sheets", [])
            if isinstance(sheets, list):
                for sheet in sheets[:3]:
                    terms = sheet.get("terms") if isinstance(sheet, dict) else None
                    if not isinstance(terms, dict):
                        continue
                    for field, maximum in FIELDS.items():
                        value = terms.get(field)
                        if type(value) is int and 0 <= value <= maximum:
                            extracted.append(("observed_offer", field, None, value))
            for kind, field, direction, value in extracted:
                evidence = dict(kind=kind, field=field, direction=direction, value=value, citation=citation)
                evidence = {"evidence_id": content_id(evidence), **evidence}
                body = message.get("body")
                observations[evidence["evidence_id"]] = {
                    **evidence,
                    "excerpt": body[:512] if isinstance(body, str) else "",
                }
    return sorted(observations.values(), key=lambda evidence: evidence["evidence_id"])


class MemoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memory_snapshots (snapshot_id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _sources(db):
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        sources = []
        if "loop_records" in tables:
            suites = {}
            for key, encoded in db.execute("SELECT id,body FROM loop_records WHERE kind='suites' ORDER BY id"):
                try:
                    suites[key] = Suite.model_validate(json.loads(encoded)).model_dump()
                except (ValueError, TypeError):
                    continue
            for (encoded,) in db.execute("SELECT body FROM loop_records WHERE kind='campaigns' ORDER BY id"):
                try:
                    campaign = json.loads(encoded)
                    suite = suites.get(campaign.get("suite_id"))
                except (ValueError, TypeError, AttributeError):
                    continue
                if suite is None or not identifier(campaign.get("campaign_id")):
                    continue
                for attempt in campaign.get("attempts", []):
                    if not isinstance(attempt, dict) or not identifier(attempt.get("attempt_id")):
                        continue
                    outcome = attempt.get("outcome", {})
                    reconciliation = attempt.get("reconciliation", {})
                    if not isinstance(outcome, dict) or not isinstance(reconciliation, dict):
                        continue
                    session_id = (
                        attempt.get("session_id") or outcome.get("session_id") or reconciliation.get("session_id")
                    )
                    if not identifier(session_id) or attempt.get("case_id") not in suite["cases"]:
                        continue
                    threads = None
                    try:
                        start = Start.model_validate(attempt["start"]["request"]).model_dump()
                        original = Outcome.model_validate(outcome).model_dump()
                        if (
                            start["attempt_id"] == attempt["attempt_id"]
                            and original["attempt_id"] == attempt["attempt_id"]
                            and original["checkpoint_id"] == attempt.get("checkpoint_id")
                            and original["session_id"] == session_id
                            and _original(original)
                        ):
                            threads = original["threads"]
                    except (ValueError, TypeError, KeyError):
                        pass
                    session = dict(
                        arena_url=suite["arena_url"],
                        environment=suite["environment"],
                        case_id=attempt["case_id"],
                        session_id=session_id,
                        run_id=None,
                        campaign_id=campaign["campaign_id"],
                        attempt_id=attempt["attempt_id"],
                        suppliers=_suppliers(threads) if threads is not None else [],
                    )
                    # Ineligible original ownership still suppresses an imported
                    # copy of recovered evidence, including arena-origin aliases.
                    sources.append((0, session, threads))
        if "runs" in tables:
            for (encoded,) in db.execute("SELECT body FROM runs ORDER BY run_id"):
                try:
                    run = Run.model_validate(json.loads(encoded)).model_dump()
                    arena = normalize_arena(run["arena_url"])
                except (ValueError, TypeError):
                    continue
                for attempt in run["attempts"]:
                    if not identifier(attempt["session_id"]):
                        continue
                    eligible = _original(attempt)
                    if run["source"] == "imported":
                        eligible = eligible and _complete_supplier_threads(attempt["threads"])
                    threads = attempt["threads"] if eligible else None
                    session = dict(
                        arena_url=arena,
                        environment=run["environment"],
                        case_id=attempt["case_id"],
                        session_id=attempt["session_id"],
                        run_id=run["run_id"],
                        campaign_id=None,
                        attempt_id=attempt["attempt_id"],
                        suppliers=_suppliers(attempt["threads"]),
                    )
                    priority = 1 if run["source"] == "tracked" else (2 if eligible else 3)
                    sources.append((priority, session, threads))
        return sources

    @classmethod
    def _projection(cls, db):
        originals = {}
        ordered = sorted(cls._sources(db), key=lambda item: (item[0], canonical_json(item[1])))
        for _priority, session, threads in ordered:
            key = (session["arena_url"], session["session_id"])
            originals.setdefault(key, (session, threads))
        eligible = [(s, t) for s, t in originals.values() if t is not None]
        if len(eligible) > 10000:
            raise ValueError("memory graph exceeds discovery session bound")
        sessions = sorted((s for s, _ in eligible), key=canonical_json)
        observations = sorted(
            (e for s, t in eligible for e in _observations(s, t)), key=lambda evidence: evidence["evidence_id"]
        )
        if len(observations) > 50000:
            raise ValueError("memory graph exceeds observation bound")
        return sessions, observations

    def graph(self) -> dict:
        with self._connect() as db:
            db.execute("BEGIN")
            sessions, observations = self._projection(db)
        lessons, conflicts = [], []
        for arena, environment in sorted({(s["arena_url"], s["environment"]) for s in sessions}):
            scope = [
                e
                for e in observations
                if (e["citation"]["arena_url"], e["citation"]["environment"]) == (arena, environment)
            ]
            scope_metadata = dict(arena_url=arena, environment=environment)
            for lesson in derive_lessons(scope):
                support = [e for e in scope if e["evidence_id"] in lesson["evidence_ids"]]
                lessons.append(
                    {
                        **lesson,
                        **scope_metadata,
                        "supporting_suppliers": sorted({e["citation"]["supplier"] for e in support}),
                        "supporting_cases": sorted({e["citation"]["case_id"] for e in support}),
                    }
                )
            for field in sorted(FIELDS):
                statements = [e for e in scope if e["kind"] == "supplier_statement" and e["field"] == field]
                if len({e["direction"] for e in statements}) > 1:
                    conflicts.append(
                        {**scope_metadata, "field": field, "evidence_ids": sorted(e["evidence_id"] for e in statements)}
                    )
        return {
            "observations": observations,
            "lessons": lessons,
            "conflicts": conflicts,
            "coverage": {
                "sessions": sessions,
                "session_count": len(sessions),
                "supplier_count": len({supplier for s in sessions for supplier in s["suppliers"]}),
                "case_count": len({s["case_id"] for s in sessions}),
            },
        }

    def build(self, *, arena_url: str, environment: str, source_cases: list[str]) -> dict:
        arena = normalize_arena(arena_url)
        if (
            environment not in ENVIRONMENTS
            or not isinstance(source_cases, list)
            or not 1 <= len(source_cases) <= MAX_COHORT
            or any(not identifier(c) for c in source_cases)
            or len(set(source_cases)) != len(source_cases)
        ):
            raise ValueError("explicit nonempty discovery scope required")
        cases = sorted(source_cases)
        with self._connect() as db:
            db.execute("BEGIN")
            sessions, observations = self._projection(db)
            selected = [
                s
                for s in sessions
                if s["arena_url"] == arena and s["environment"] == environment and s["case_id"] in cases
            ]
            if {s["case_id"] for s in selected} != set(cases):
                raise ValueError("requested discovery cases lack original owned ended sessions")
            evidence = [
                {k: v for k, v in e.items() if k != "excerpt"}
                for e in observations
                if e["citation"]["arena_url"] == arena
                and e["citation"]["environment"] == environment
                and e["citation"]["case_id"] in cases
            ]
            if len(evidence) > MAX_EVIDENCE:
                raise ValueError("discovery evidence exceeds snapshot bound; select a smaller scope")
            payload = dict(
                schema_version=1,
                arena_url=arena,
                environment=environment,
                source_cases=cases,
                source_suppliers=sorted({supplier for s in selected for supplier in s["suppliers"]}),
                source_sessions=sorted({s["session_id"] for s in selected}),
                lessons=derive_lessons(evidence),
                evidence=evidence,
            )
            snapshot = validate_memory({"snapshot_id": content_id(payload), **payload})
            db.execute(
                "INSERT OR IGNORE INTO memory_snapshots VALUES (?,?)",
                (snapshot["snapshot_id"], canonical_json(snapshot)),
            )
            row = db.execute(
                "SELECT body FROM memory_snapshots WHERE snapshot_id=?", (snapshot["snapshot_id"],)
            ).fetchone()
            if validate_memory(json.loads(row[0])) != snapshot:
                raise ValueError("immutable memory snapshot conflict")
        return snapshot

    @staticmethod
    def _stored_snapshot(snapshot_id: str, encoded: str) -> dict:
        snapshot = validate_memory(json.loads(encoded))
        if snapshot["snapshot_id"] != snapshot_id:
            raise ValueError("stored snapshot identity mismatch")
        return snapshot

    def get(self, snapshot_id: str) -> dict:
        with self._connect() as db:
            row = db.execute(
                "SELECT snapshot_id,body FROM memory_snapshots WHERE snapshot_id=?", (snapshot_id,)
            ).fetchone()
        if row is None:
            raise ValueError("memory snapshot not found")
        return self._stored_snapshot(*row)

    def list(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT snapshot_id,body FROM memory_snapshots ORDER BY snapshot_id").fetchall()
        return [self._stored_snapshot(*row) for row in rows]
