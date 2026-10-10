"""Transactional loop metadata; laptops execute code and report owned evidence."""

import json
import sqlite3
import time
from pathlib import Path

from ..ingestion import fingerprint
from .checkpoints import validate_checkpoint
from .evidence import validate_references
from .loop_models import (
    Campaign,
    Complete,
    Family,
    Finding,
    NotCreated,
    Outcome,
    Recommendation,
    Reconciliation,
    Start,
    Suite,
)
from .memory import MemoryStore
from .ordering import campaign_order
from .policy import evaluate_campaign
from .store import Conflict, Store


class LoopStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS loop_records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS loop_sessions (
                    arena TEXT NOT NULL, session_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                    PRIMARY KEY(arena,session_id));
                CREATE TABLE IF NOT EXISTS loop_leases (
                    key_id TEXT PRIMARY KEY, attempt_id TEXT, last_start REAL NOT NULL);
            """)

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _get(db, kind, key):
        row = db.execute("SELECT body FROM loop_records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if not row:
            raise ValueError("record not found")
        return json.loads(row[0])

    @staticmethod
    def _all(db, kind):
        records = [
            json.loads(r[0]) for r in db.execute("SELECT body FROM loop_records WHERE kind=? ORDER BY id", (kind,))
        ]
        if kind == "history":
            records.sort(key=lambda event: (event["recommendation"]["updated_at"], event["event_id"]))
        return records

    @staticmethod
    def _put(db, kind, key, body, immutable=False):
        encoded = json.dumps(body, sort_keys=True, allow_nan=False)
        row = db.execute("SELECT body FROM loop_records WHERE kind=? AND id=?", (kind, key)).fetchone()
        if immutable and row and json.loads(row[0]) != body:
            raise Conflict("immutable record conflict")
        db.execute(
            "INSERT INTO loop_records VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
            (kind, key, encoded),
        )
        return body

    def _checkpoint(self, db, suite, key):
        checkpoint = self._get(db, "checkpoints", key)
        if (
            not checkpoint["published"]
            or checkpoint["runner"] != suite["runner"]
            or checkpoint["data"] != suite["data"]
        ):
            raise ValueError("checkpoint unavailable or execution inputs differ")
        return checkpoint

    def _practice(self, db, suite, family, quota, *, starting=False):
        if suite["environment"] != "practice":
            return
        if not family["practice_allowance"] or quota is None or not 0 <= time.time() - quota["observed_at"] <= 60:
            raise ValueError("practice allowance and fresh quota required")
        campaigns = self._all(db, "campaigns")
        active = sum(
            sum(a["status"] == "pending" for a in c["attempts"])
            for c in campaigns
            if self._get(db, "suites", c["suite_id"])["arena_url"] == suite["arena_url"]
            and self._get(db, "suites", c["suite_id"])["environment"] == "practice"
        )
        required = 0 if starting else suite["max_sessions"]
        reserve = max([family["reserve"]] + [f["reserve"] for f in self._all(db, "families")])
        if quota["remaining"] - quota["open_sessions"] - active - required < reserve:
            raise ValueError("protected practice reserve")
        if not starting and family["practice_reserved"] + required > family["practice_allowance"]:
            raise ValueError("practice allowance exhausted")

    def write(self, operation: str, body: dict) -> dict:
        # MemoryStore owns its own connection/transaction; do not nest its writer.
        if operation == 'memory-snapshot':
            if not isinstance(body, dict) or set(body) != {'arena_url', 'environment', 'source_cases'}:
                raise ValueError('invalid memory snapshot request')
            return MemoryStore(self.path).build(**body)
        if operation in {"learning-register", "learning-review"}:
            return self._learning_decision(operation, body)
        models = {
            "suite": Suite,
            "family": Family,
            "campaign": Campaign,
            "seed": Recommendation,
            "restore": Recommendation,
            "attempt-start": Start,
            "attempt-result": Outcome,
            "attempt-reconcile": Reconciliation,
            "attempt-not-created": NotCreated,
            "complete": Complete,
            "finding": Finding,
        }
        if operation == "checkpoint":
            body = validate_checkpoint(body)
            if 'memory' in body['config']:
                snapshot = body['config']['memory']
                if MemoryStore(self.path).get(snapshot['snapshot_id']) != snapshot:
                    raise ValueError('checkpoint memory differs from registered snapshot')
        elif operation in models:
            body = models[operation].model_validate(body).model_dump()
        else:
            raise ValueError("unknown operation")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if operation in ("checkpoint", "suite", "family"):
                kind = {"checkpoint": "checkpoints", "suite": "suites", "family": "families"}[operation]
                key = body[operation + "_id"]
                if operation == "family":
                    body.update(reserved_sessions=0, practice_reserved=0)
                    existing = db.execute("SELECT body FROM loop_records WHERE kind=? AND id=?", (kind, key)).fetchone()
                    if existing:
                        old = json.loads(existing[0])
                        body.update(
                            reserved_sessions=old["reserved_sessions"], practice_reserved=old["practice_reserved"]
                        )
                return self._put(db, kind, key, body, immutable=True)
            if operation in ("seed", "restore"):
                suite = self._get(db, "suites", body["suite_id"])
                checkpoint = self._checkpoint(db, suite, body['checkpoint_id'])
                if operation == 'seed' and checkpoint['config'].get('memory', {}).get('lessons'):
                    raise ValueError('nonempty memory requires held-out evaluation before recommendation')
                if operation == "restore" and not body["request_id"]:
                    raise ValueError("restore request ID required")
                if operation == "restore" and not any(
                    h["suite_id"] == body["suite_id"] and h["checkpoint_id"] == body["checkpoint_id"]
                    for h in self._all(db, "history")
                ):
                    raise ValueError("restore target was never recommended")
                event_id = body["request_id"] or "seed:" + body["suite_id"]
                previous_event = db.execute(
                    "SELECT body FROM loop_records WHERE kind=? AND id=?", ("history", event_id)
                ).fetchone()
                if previous_event:
                    event = json.loads(previous_event[0])
                    if event.get("request") != body:
                        raise Conflict("recommendation request conflict")
                    return event["recommendation"]
                old = db.execute(
                    "SELECT body FROM loop_records WHERE kind=? AND id=?", ("recommended", body["suite_id"])
                ).fetchone()
                old = json.loads(old[0]) if old else None
                if (
                    operation == "seed"
                    and old
                    or operation == "restore"
                    and (not old or body["generation"] != old["generation"])
                ):
                    raise Conflict("recommendation generation conflict")
                return self._recommend(db, suite, body["checkpoint_id"], old, event_id, operation, request=body)
            if operation == "campaign":
                previous = db.execute(
                    "SELECT body FROM loop_records WHERE kind=? AND id=?", ("campaigns", body["campaign_id"])
                ).fetchone()
                if previous:
                    previous = json.loads(previous[0])
                    if previous["request"] != body:
                        raise Conflict("campaign ID conflict")
                    return previous
                suite = self._get(db, "suites", body["suite_id"])
                family = self._get(db, "families", body["family_id"])
                rec = self._get(db, "recommended", body["suite_id"])
                if rec["generation"] != body["generation"] or rec["checkpoint_id"] != body["baseline_id"]:
                    raise Conflict("baseline superseded")
                for key in ("baseline_id", "candidate_id"):
                    self._checkpoint(db, suite, body[key])
                if family["reserved_sessions"] + suite["max_sessions"] > family["max_sessions"]:
                    raise ValueError("family budget exhausted")
                self._practice(db, suite, family, body["quota"])
                attempts = []
                for cell in campaign_order(suite["cases"], suite["repetitions"], body["seed"]):
                    arm, case, repeat = cell["arm"], cell["case_id"], cell["repeat"]
                    case_index = suite["cases"].index(case)
                    attempts.append(
                        dict(
                            attempt_id=f"{body['campaign_id']}:{case_index}:{repeat}:{arm}",
                            **cell,
                            checkpoint_id=body[arm + "_id"],
                            status="pending",
                        )
                    )
                family["reserved_sessions"] += suite["max_sessions"]
                if suite["environment"] == "practice":
                    family["practice_reserved"] += suite["max_sessions"]
                self._put(db, "families", family["family_id"], family)
                campaign = {
                    **body,
                    "request": body,
                    "attempts": attempts,
                    "status": "running",
                    "created_at": time.time(),
                }
                return self._put(db, "campaigns", body["campaign_id"], campaign)
            if operation == "attempt-not-created":
                campaign, attempt = self._attempt(db, body["attempt_id"])
                if "start" not in attempt or attempt["checkpoint_id"] != body["checkpoint_id"]:
                    raise ValueError("not-created attempt mismatch")
                if attempt["start"]["request"]["worker_id"] != body["worker_id"]:
                    raise Conflict("not-created evidence executor mismatch")
                if attempt.get("session_id") or attempt.get("reconciliation"):
                    raise Conflict("known session cannot be declared not created")
                if "not_created" in attempt:
                    if attempt["not_created"] != body:
                        raise Conflict("immutable not-created evidence conflict")
                    return attempt
                if attempt["status"] not in ("started", "failed"):
                    raise Conflict("not-created evidence requires started or failed attempt")
                attempt.update(status="failed", not_created=body)
                db.execute("UPDATE loop_leases SET attempt_id=NULL WHERE attempt_id=?", (body["attempt_id"],))
                self._put(db, "campaigns", campaign["campaign_id"], campaign)
                return attempt
            if operation in ("attempt-start", "attempt-result", "attempt-reconcile"):
                campaign, attempt = self._attempt(db, body["attempt_id"])
                suite = self._get(db, "suites", campaign["suite_id"])
                if campaign["status"] != "running" and operation == "attempt-start":
                    raise Conflict("campaign already completed")
                if operation == "attempt-reconcile":
                    if "start" not in attempt or attempt["checkpoint_id"] != body["checkpoint_id"]:
                        raise ValueError("reconciliation attempt mismatch")
                    if attempt.get("session_id") not in (None, body["session_id"]):
                        raise Conflict("reconciliation session mismatch")
                    if "reconciliation" in attempt:
                        if attempt["reconciliation"] != body:
                            raise Conflict("immutable reconciliation conflict")
                        return attempt
                    row = db.execute(
                        "SELECT attempt_id FROM loop_sessions WHERE arena=? AND session_id=?",
                        (suite["arena_url"], body["session_id"]),
                    ).fetchone()
                    if row and row[0] != body["attempt_id"]:
                        raise Conflict("session already belongs to another attempt")
                    db.execute(
                        "INSERT OR IGNORE INTO loop_sessions VALUES(?,?,?)",
                        (suite["arena_url"], body["session_id"], body["attempt_id"]),
                    )
                    # Add recovered evidence, retaining the original execution status and score.
                    if attempt["status"] == "started":
                        attempt["status"] = "ambiguous"
                    attempt["reconciliation"] = body
                    db.execute("UPDATE loop_leases SET attempt_id=NULL WHERE attempt_id=?", (body["attempt_id"],))
                    self._put(db, "campaigns", campaign["campaign_id"], campaign)
                    return attempt
                if operation == "attempt-start":
                    if "start" in attempt:
                        if attempt["start"]["request"] != body:
                            raise Conflict("attempt start conflict")
                        return attempt
                    if attempt["status"] != "pending":
                        raise Conflict("attempt is terminal")
                    family = self._get(db, "families", campaign["family_id"])
                    self._practice(db, suite, family, body["quota"], starting=True)
                    lease = db.execute(
                        "SELECT attempt_id,last_start FROM loop_leases WHERE key_id=?", (body["key_id"],)
                    ).fetchone()
                    now = time.time()
                    if lease and lease[0] is not None:
                        raise Conflict("hosted start already owned")
                    # Sandbox has no quota pacing requirement; practice uses a key-wide interval.
                    if lease and suite["environment"] == "practice" and now - lease[1] < 1:
                        raise Conflict("hosted start pacing")
                    db.execute(
                        "INSERT INTO loop_leases VALUES(?,?,?) ON CONFLICT(key_id) DO UPDATE SET "
                        "attempt_id=excluded.attempt_id,last_start=excluded.last_start",
                        (body["key_id"], body["attempt_id"], now),
                    )
                    attempt.update(status="started", start={"request": body, "started_at": now})
                else:
                    if attempt["checkpoint_id"] != body["checkpoint_id"]:
                        raise ValueError("attempt checkpoint mismatch")
                    if "outcome" in attempt:
                        if attempt["outcome"] != body:
                            raise Conflict("terminal outcome conflict")
                        return attempt
                    if "start" not in attempt:
                        raise ValueError("attempt not started")
                    if attempt["status"] != "started":
                        raise Conflict("original execution outcome is already terminal")
                    if "reconciliation" in attempt and body["session_id"] != attempt["reconciliation"]["session_id"]:
                        raise Conflict("known session identity conflict")
                    if body["status"] in ("completed", "recovered") and not body["session_id"]:
                        raise ValueError("known outcome requires session ID")
                    if body["session_id"]:
                        row = db.execute(
                            "SELECT attempt_id FROM loop_sessions WHERE arena=? AND session_id=?",
                            (suite["arena_url"], body["session_id"]),
                        ).fetchone()
                        if row and row[0] != body["attempt_id"]:
                            raise Conflict("session already belongs to another attempt")
                        db.execute(
                            "INSERT OR IGNORE INTO loop_sessions VALUES(?,?,?)",
                            (suite["arena_url"], body["session_id"], body["attempt_id"]),
                        )
                    attempt.update(body, outcome=body)
                    if body["session_id"] and body["result"].get("ended") is True:
                        db.execute("UPDATE loop_leases SET attempt_id=NULL WHERE attempt_id=?", (body["attempt_id"],))
                self._put(db, "campaigns", campaign["campaign_id"], campaign)
                return attempt
            if operation == "complete":
                campaign = self._get(db, "campaigns", body["campaign_id"])
                if "completion" in campaign:
                    self._mark_rejected_proposal(db, campaign, campaign["completion"]["status"])
                    return campaign["completion"]
                if any(a["status"] in ("pending", "started") for a in campaign["attempts"]):
                    raise Conflict("campaign has unfinished planned attempts")
                suite = self._get(db, "suites", campaign["suite_id"])
                evaluation = evaluate_campaign(
                    suite,
                    self._get(db, "checkpoints", campaign["baseline_id"]),
                    self._get(db, "checkpoints", campaign["candidate_id"]),
                    campaign["attempts"],
                )
                old = self._get(db, "recommended", suite["suite_id"])
                if old["generation"] != campaign["generation"] or old["checkpoint_id"] != campaign["baseline_id"]:
                    status = "baseline_superseded"
                elif evaluation["eligible"]:
                    proposal = db.execute(
                        "SELECT proposal_id,body FROM learning_proposals WHERE "
                        "json_extract(body,'$.checkpoint_id')=?",
                        (campaign["candidate_id"],),
                    ).fetchone() if self._has_table(db, "learning_proposals") else None
                    if proposal:
                        draft = json.loads(proposal[1])
                        status = "awaiting_review" if draft.get("status") == "registered" else "proposal_unavailable"
                        if status == "awaiting_review":
                            draft.update(status=status, campaign_id=campaign["campaign_id"])
                            db.execute("UPDATE learning_proposals SET body=? WHERE proposal_id=?",
                                       (json.dumps(draft, sort_keys=True), proposal[0]))
                    else:
                        status = "promoted"
                        self._recommend(
                            db, suite, campaign["candidate_id"], old,
                            "promotion:" + campaign["campaign_id"], "promotion",
                            campaign_id=campaign["campaign_id"], evaluation=evaluation,
                        )
                else:
                    status = (
                        "insufficient_evidence"
                        if any(
                            g in evaluation["evidence_gaps"]
                            for g in ("complete_sample", "must_haves", "timeout_evidence")
                        )
                        else "rejected"
                    )
                self._mark_rejected_proposal(db, campaign, status)
                completion = dict(campaign_id=campaign["campaign_id"], status=status, evaluation=evaluation)
                campaign.update(status=status, completion=completion)
                self._put(db, "campaigns", campaign["campaign_id"], campaign)
                return completion
            if operation == "finding":
                campaign = self._get(db, "campaigns", body["campaign_id"])
                if campaign["candidate_id"] != body["candidate_id"]:
                    raise ValueError("finding candidate mismatch")
                validate_references(body["evidence"], campaign["attempts"])
                return self._put(db, "findings", body["finding_id"], body, immutable=True)
        raise ValueError("unknown operation")

    def _mark_rejected_proposal(self, db, campaign, status):
        if status not in {"rejected", "insufficient_evidence", "baseline_superseded"} or not self._has_table(
            db, "learning_proposals"
        ):
            return
        row = db.execute(
            "SELECT proposal_id,body FROM learning_proposals WHERE json_extract(body,'$.checkpoint_id')=?",
            (campaign["candidate_id"],),
        ).fetchone()
        if not row:
            return
        proposal = json.loads(row[1])
        if proposal.get("status") == "registered":
            proposal.update(status="evaluated_rejected", campaign_id=campaign["campaign_id"],
                            evaluation_status=status)
            db.execute("UPDATE learning_proposals SET body=? WHERE proposal_id=?",
                       (json.dumps(proposal, sort_keys=True), row[0]))

    @staticmethod
    def _has_table(db, name):
        return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    def _proposal_current(self, proposal):
        if proposal.get("run_id") and proposal.get("source_sha256"):
            source = Store(self.path).get(proposal["run_id"])
            if not source or fingerprint(source) != proposal["source_sha256"]:
                raise Conflict("learning proposal source changed")

    def _learning_decision(self, operation, body):
        if not isinstance(body, dict):
            raise ValueError("invalid learning request")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not self._has_table(db, "learning_proposals"):
                raise ValueError("learning proposal not found")
            if operation == "learning-register":
                if set(body) != {"proposal_id", "checkpoint_id"}:
                    raise ValueError("invalid learning registration")
                row = db.execute("SELECT body FROM learning_proposals WHERE proposal_id=?",
                                 (body["proposal_id"],)).fetchone()
                if not row:
                    raise ValueError("learning proposal not found")
                proposal = json.loads(row[0])
                if proposal.get("checkpoint_id") == body["checkpoint_id"]:
                    return proposal
                if proposal["status"] != "draft":
                    raise Conflict("learning proposal already registered")
                self._proposal_current(proposal)
                checkpoint = self._get(db, "checkpoints", body["checkpoint_id"])
                if not checkpoint["published"] or not checkpoint["parent_id"]:
                    raise ValueError("published child checkpoint required")
                baseline = self._get(db, "checkpoints", checkpoint["parent_id"])
                expected = {**baseline["config"], **proposal["config_patch"]}
                if checkpoint["config"] != expected:
                    raise ValueError("checkpoint differs from bounded proposal")
                proposal.update(checkpoint_id=body["checkpoint_id"], status="registered")
                db.execute("UPDATE learning_proposals SET body=? WHERE proposal_id=?",
                           (json.dumps(proposal, sort_keys=True), body["proposal_id"]))
                return proposal
            if set(body) != {"proposal_id", "campaign_id", "author", "approve"} or (
                not isinstance(body["author"], str) or not body["author"] or type(body["approve"]) is not bool
            ):
                raise ValueError("invalid learning review")
            row = db.execute("SELECT body FROM learning_proposals WHERE proposal_id=?",
                             (body["proposal_id"],)).fetchone()
            if not row:
                raise ValueError("learning proposal not found")
            proposal = json.loads(row[0])
            self._proposal_current(proposal)
            if proposal.get("review") == body:
                return proposal
            if proposal.get("status") != "awaiting_review" or proposal.get("campaign_id") != body["campaign_id"]:
                raise Conflict("proposal is not awaiting this review")
            campaign = self._get(db, "campaigns", body["campaign_id"])
            if body["author"] == campaign["author"]:
                raise ValueError("teammate review requires a different author")
            if (campaign["candidate_id"] != proposal["checkpoint_id"]
                    or not campaign["completion"]["evaluation"]["eligible"]):
                raise ValueError("campaign is not an eligible comparison")
            suite = self._get(db, "suites", campaign["suite_id"])
            rec = self._get(db, "recommended", suite["suite_id"])
            if rec["generation"] != campaign["generation"] or rec["checkpoint_id"] != campaign["baseline_id"]:
                raise Conflict("baseline was superseded before review")
            if body["approve"]:
                self._recommend(db, suite, campaign["candidate_id"], rec,
                                "reviewed-promotion:" + body["campaign_id"], "reviewed_promotion",
                                campaign_id=body["campaign_id"], author=body["author"],
                                evaluation=campaign["completion"]["evaluation"])
            proposal.update(status="approved" if body["approve"] else "rejected", review=body)
            db.execute("UPDATE learning_proposals SET body=? WHERE proposal_id=?",
                       (json.dumps(proposal, sort_keys=True), body["proposal_id"]))
            return proposal

    def _attempt(self, db, key):
        for campaign in self._all(db, "campaigns"):
            for attempt in campaign["attempts"]:
                if attempt["attempt_id"] == key:
                    return campaign, attempt
        raise ValueError("attempt not found")

    def _recommend(self, db, suite, checkpoint_id, old, event_id, action, **metadata):
        rec = dict(
            suite_id=suite["suite_id"],
            checkpoint_id=checkpoint_id,
            generation=old["generation"] + 1 if old else 1,
            updated_at=time.time(),
            event_id=event_id,
        )
        event = dict(
            event_id=event_id,
            action=action,
            previous_id=old["checkpoint_id"] if old else None,
            checkpoint_id=checkpoint_id,
            suite_id=suite["suite_id"],
            recommendation=rec,
            **metadata,
        )
        self._put(db, "history", event_id, event, immutable=True)
        self._put(db, "recommended", suite["suite_id"], rec)
        return rec

    def read(self, resource: str, key: str | None = None) -> dict:
        if resource == "learning-proposals":
            with self._connect() as db:
                if not self._has_table(db, "learning_proposals"):
                    return {"learning-proposals": []}
                if key is not None:
                    row = db.execute("SELECT body FROM learning_proposals WHERE proposal_id=?", (key,)).fetchone()
                    if not row:
                        raise ValueError("learning proposal not found")
                    return json.loads(row[0])
                return {"learning-proposals": [json.loads(row[0]) for row in db.execute(
                    "SELECT body FROM learning_proposals ORDER BY proposal_id"
                )]}
        if resource == 'memory':
            if key is not None:
                raise ValueError('memory graph does not take a key')
            return MemoryStore(self.path).graph()
        if resource == 'memory-snapshots':
            memory = MemoryStore(self.path)
            return memory.get(key) if key is not None else {resource: memory.list()}
        if resource not in (
            "checkpoints",
            "suites",
            "families",
            "campaigns",
            "recommended",
            "history",
            "findings",
            "evidence",
            "overview",
        ):
            raise ValueError("unknown resource")
        with self._connect() as db:
            if resource == "evidence":
                if key is None:
                    raise ValueError("evidence requires attempt ID")
                campaign, attempt = self._attempt(db, key)
                return dict(campaign_id=campaign["campaign_id"], attempt=attempt)
            if resource == "overview":
                campaigns = self._all(db, "campaigns")
                return dict(
                    suites=self._all(db, "suites"),
                    recommended=self._all(db, "recommended"),
                    families=self._all(db, "families"),
                    history=self._all(db, "history"),
                    campaigns=[
                        {
                            **{k: v for k, v in c.items() if k not in ("attempts", "request", "quota")},
                            "attempt_counts": {
                                "total": len(c["attempts"]),
                                "completed": sum(a["status"] == "completed" for a in c["attempts"]),
                                "failed": sum(a["status"] in {"failed", "interrupted", "recovered"}
                                              for a in c["attempts"]),
                            },
                        } for c in campaigns
                    ],
                    findings=self._all(db, "findings"),
                )
            if key is not None:
                return self._get(db, resource, key)
            return {resource: self._all(db, resource)}
