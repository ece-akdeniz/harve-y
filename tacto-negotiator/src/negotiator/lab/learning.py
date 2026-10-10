"""Lab-owned, retryable learning projections. Originals and recommendations stay immutable."""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from ..dossiers import load_package
from ..ingestion import fingerprint
from .feedback import FeedbackAgent
from .knowledge import SnapshotMemory, export_graph
from .memory import MemoryStore
from .models import utc_now
from .runner import fingerprint_data
from .store import Store

TERMINAL = {"completed", "failed", "interrupted"}
PERMITTED_CHANGES = {
    "shorter_final_hold": {"final_hold_s": 20.0},
    "stronger_opening_anchor": {"anchor": 0.16},
}


class LearningStore:
    def __init__(self, path):
        self.path = Path(path)
        self.store = Store(path)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS learning_data (
                    data_sha256 TEXT PRIMARY KEY, body TEXT NOT NULL, ingested_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS learning_status (
                    run_id TEXT PRIMARY KEY, source_sha256 TEXT, state TEXT NOT NULL,
                    error_code TEXT, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS learning_proposals (
                    proposal_id TEXT PRIMARY KEY, body TEXT NOT NULL);
            """)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def ingest(self, base, release=None):
        """Register supplied arena data on the lab host; never fetch external news."""
        base = Path(base)
        release = Path(release) if release else None
        package = load_package(base, release)
        try:
            base_hash = fingerprint_data(base)
            release_hash = fingerprint_data(release) if release else None
            if not base_hash or (release and not release_hash):
                raise ValueError("required data directory is unavailable")
            data_hash = (hashlib.sha256(f"base:{base_hash}\nrelease:{release_hash}".encode()).hexdigest()
                         if release else base_hash)
            body = {"schema_version": 1, "data_sha256": data_hash,
                    "package_sha256": package.manifest["sha256"],
                    "manifest": package.manifest, "facts": package.facts,
                    "sources": package.sources, "ingested_at": utc_now()}
            encoded = json.dumps(body, sort_keys=True, allow_nan=False)
            if len(encoded.encode()) > 32 * 1024 * 1024:
                raise ValueError("data projection exceeds lab limit")
            with self._connect() as db:
                row = db.execute("SELECT body FROM learning_data WHERE data_sha256=?", (data_hash,)).fetchone()
                if row and json.loads(row[0])["package_sha256"] != body["package_sha256"]:
                    raise ValueError("data fingerprint collision")
                if not row:
                    db.execute("INSERT INTO learning_data VALUES(?,?,?)", (data_hash, encoded, body["ingested_at"]))
            refreshed, failures = 0, 0
            for run in self.store.all():
                if (run.status not in TERMINAL or run.provenance is None
                        or run.provenance.data_sha256 != data_hash):
                    continue
                try:
                    self.review(run.run_id)
                    refreshed += 1
                except Exception:
                    failures += 1
            return {"data_sha256": data_hash, "package_sha256": body["package_sha256"],
                    "facts": len(package.facts), "conflicts": len(package.conflicts),
                    "warnings": list(package.warnings), "feedback_refreshed": refreshed,
                    "feedback_failed": failures}
        finally:
            if package.db:
                package.db.close()

    def _package(self, data_sha256):
        with self._connect() as db:
            row = db.execute("SELECT body FROM learning_data WHERE data_sha256=?", (data_sha256,)).fetchone()
        if not row:
            return None
        body = json.loads(row[0])
        return SimpleNamespace(manifest={"sha256": body["package_sha256"],
                                         "conflicts": body["manifest"].get("conflicts", {})},
                               facts=body["facts"], sources=body["sources"])

    def graph(self, data_sha256=None):
        if data_sha256 is None:
            with self._connect() as db:
                row = db.execute(
                    "SELECT data_sha256 FROM learning_data ORDER BY ingested_at DESC, data_sha256 DESC LIMIT 1"
                ).fetchone()
            data_sha256 = row[0] if row else None
        return export_graph(self.store.all(), package=self._package(data_sha256))

    def status(self, run_id):
        with self._connect() as db:
            row = db.execute("SELECT source_sha256,state,error_code,updated_at FROM learning_status WHERE run_id=?",
                             (run_id,)).fetchone()
        return {"run_id": run_id, "source_sha256": row[0], "state": row[1],
                "error_code": row[2], "updated_at": row[3]} if row else {"run_id": run_id, "state": "pending"}

    def report(self, run_id):
        with self._connect() as db:
            try:
                row = db.execute("SELECT body FROM feedback WHERE run_id=? ORDER BY rowid DESC LIMIT 1",
                                 (run_id,)).fetchone()
            except sqlite3.OperationalError:
                row = None
        report = json.loads(row[0]) if row else None
        run = self.store.get(run_id)
        return report if run and report and report["source_sha256"] == fingerprint(run) else None

    def _set_status(self, run_id, source_hash, state, error=None):
        with self._connect() as db:
            db.execute("INSERT INTO learning_status VALUES(?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET "
                       "source_sha256=excluded.source_sha256,state=excluded.state,"
                       "error_code=excluded.error_code,updated_at=excluded.updated_at",
                       (run_id, source_hash, state, error, utc_now()))

    def review(self, run_id):
        run = self.store.get(run_id)
        if not run or run["status"] not in TERMINAL:
            raise ValueError("terminal run required")
        source_hash = fingerprint(run)
        try:
            package = self._package((run.get("provenance") or {}).get("data_sha256"))
            runs = self.store.all()
            graph = export_graph(runs, package=package)
            report = FeedbackAgent().review(run, memory=SnapshotMemory(graph),
                                            data_sha256=(run.get("provenance") or {}).get("data_sha256"),
                                            public_graph=graph)
            owned = {item.run_id: item.model_dump() for item in runs}
            episodic = MemoryStore(self.path).graph()
            scoped = []
            scopes = {(supplier, attempt["case_id"]) for attempt in run["attempts"]
                      for supplier in attempt.get("threads", {})}
            for observation in episodic["observations"]:
                citation = observation["citation"]
                prior = owned.get(citation.get("run_id"))
                if (not prior or prior["run_id"] == run_id
                        or (citation["supplier"], citation["case_id"]) not in scopes
                        or citation["arena_url"] != run["arena_url"]
                        or citation["environment"] != run["environment"]
                        or (prior.get("provenance") or {}).get("data_sha256") !=
                        (run.get("provenance") or {}).get("data_sha256")
                        or prior["updated_at"] > run["started_at"]):
                    continue
                scoped.append({"evidence_id": observation["evidence_id"],
                               "kind": observation["kind"], "field": observation["field"],
                               "citation": citation})
                if len(scoped) == 20:
                    break
            report["episodic_context"] = scoped
            selected_ids = {item["evidence_id"] for item in scoped}
            report["episodic_conflicts"] = [conflict for conflict in episodic["conflicts"]
                                            if conflict["arena_url"] == run["arena_url"] and
                                            conflict["environment"] == run["environment"] and
                                            selected_ids.intersection(conflict.get("evidence_ids", []))][:10]
            report["missing_evidence"] = (
                [] if package else ["matching_public_data_unavailable"]
            )
            report["proposed_experiments"] = self._proposals(run, report)
            with self._connect() as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS feedback (source_sha256 TEXT PRIMARY KEY, run_id TEXT, body TEXT)"
                )
                db.execute("INSERT OR REPLACE INTO feedback VALUES(?,?,?)",
                           (report["source_sha256"], run_id, json.dumps(report, allow_nan=False)))
                for proposal in report["proposed_experiments"]:
                    db.execute("INSERT OR IGNORE INTO learning_proposals VALUES(?,?)",
                               (proposal["proposal_id"], json.dumps(proposal, sort_keys=True, allow_nan=False)))
            self._set_status(run_id, source_hash, "ready")
            return report
        except Exception as error:
            self._set_status(run_id, source_hash, "failed", type(error).__name__)
            raise

    @staticmethod
    def _proposals(run, report):
        """Only a named, deterministic config change can become a draft."""
        if run.get("source") != "tracked" or run.get("agent") != "package":
            return []
        proposals = []
        evidence = [ref for finding in report["findings"] if finding.get("code") == "thread_timeout"
                    for ref in finding["evidence"]]
        if evidence and run.get("config", {}).get("final_hold_s", 40.0) > 20:
            proposals.append({"kind": "shorter_final_hold", "evidence": evidence,
                              "hypothesis": "A shorter final hold reduces thread timeouts without losing score."})
        # This is deliberately a testable hypothesis, not an attribution of poor scores.
        # Require repeated, completed, valid deals across distinct cases before proposing it.
        weak = []
        for attempt in run["attempts"]:
            result = attempt.get("result") or {}
            breakdown = result.get("cost_breakdown") or {}
            price = breakdown.get("price")
            total = result.get("c_deal")
            if (attempt["status"] == "completed" and type(attempt.get("score")) in (int, float)
                    and attempt["score"] < 0.5 and attempt.get("timeouts") == 0
                    and result.get("deal") is True and result.get("must_haves_ok") is True
                    and type(price) in (int, float) and type(total) in (int, float)
                    and total > 0 and price / total >= 0.75):
                weak.append(attempt)
        anchor = run.get("config", {}).get("anchor", 0.12)
        if (len({attempt["case_id"] for attempt in weak}) >= 2
                and type(anchor) in (int, float) and 0 <= anchor <= 0.12):
            proposals.append({"kind": "stronger_opening_anchor",
                              "evidence": [{"run_id": run["run_id"], "attempt_id": a["attempt_id"],
                                            "case_id": a["case_id"]} for a in weak],
                              "hypothesis": "A stronger opening anchor improves price-dominated, low-scoring "
                                            "deals without increasing no-deals or case regressions."})
        for proposal in proposals:
            proposal.update(schema_version=1, run_id=run["run_id"],
                            source_sha256=report["source_sha256"],
                            config_patch=PERMITTED_CHANGES[proposal["kind"]], status="draft")
            proposal["proposal_id"] = fingerprint(proposal)
        return proposals

    def proposals(self):
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute(
                "SELECT body FROM learning_proposals ORDER BY proposal_id"
            )]

    def context(self, *, supplier, case_id, arena_url, environment, data_sha256, before,
                purpose="feedback", limit=20):
        """Bounded source references; raw history and scores are never returned to live play."""
        from ..memory import identifier, normalize_arena

        if (not identifier(supplier) or not identifier(case_id)
                or normalize_arena(arena_url) != arena_url
                or environment not in {"practice", "sandbox", "simulator"}
                or not isinstance(data_sha256, str) or len(data_sha256) != 64
                or purpose not in {"feedback", "live"}
                or type(limit) is not int or not 1 <= limit <= 20):
            raise ValueError("invalid learning context scope")
        cutoff = datetime.fromisoformat(before.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            raise ValueError("learning context requires timezone")
        package = self._package(data_sha256)
        facts = []
        if package:
            for ref, value in sorted(package.facts.items()):
                if value.get("supplier") != supplier and value.get("supplier_id") != supplier:
                    continue
                observed = value.get("date")
                if observed and isinstance(observed, str) and observed[:10] > cutoff.date().isoformat():
                    continue
                if value.get("valid_from") and value["valid_from"][:10] > cutoff.date().isoformat():
                    continue
                if value.get("valid_to") and value["valid_to"][:10] < cutoff.date().isoformat():
                    continue
                facts.append({"source_id": ref, "source_layer": package.sources.get(ref, "unknown"),
                              "kind": ref.split(":", 1)[0], "observed_at": observed})
                if len(facts) == limit:
                    break
        observations = []
        if purpose == "feedback":
            runs = {run.run_id: run.model_dump() for run in self.store.all()}
            for item in MemoryStore(self.path).graph()["observations"]:
                citation = item["citation"]
                source = runs.get(citation.get("run_id"))
                if (not source or citation["supplier"] != supplier or citation["case_id"] != case_id
                        or citation["arena_url"] != arena_url or citation["environment"] != environment
                        or (source.get("provenance") or {}).get("data_sha256") != data_sha256
                        or datetime.fromisoformat(source["updated_at"]) >= cutoff):
                    continue
                observations.append({"evidence_id": item["evidence_id"], "kind": item["kind"],
                                     "field": item["field"], "citation": citation})
                if len(observations) == limit:
                    break
        return {"supplier": supplier, "case_id": case_id, "data_sha256": data_sha256,
                "purpose": purpose, "public_facts": facts, "episodic_observations": observations,
                "approved_lessons": []}
