"""Read-only owned-session history, retryable imports and separate crash recovery evidence."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .models import Run, safe_url, timestamp, utc_now
from .publish import Publisher, load_snapshots, save_reconciliation, save_snapshot
from .reconcile import known_score, preserve_recovered, recovered_result
from .runner import collect_session, quota_snapshot, safe_error, sanitize
from .store import Store

OPEN = {"open", "running", "active", "pending"}
ENDED = {"ended", "completed", "closed"}


def _session_records(root: Path, store: Store | None):
    runs = [run for _, run in load_snapshots(root)]
    if store:
        runs += store.all()
    records = {}
    for run in runs:
        for index, attempt in enumerate(run.attempts):
            if not attempt.session_id:
                continue
            key = (run.arena_url, attempt.session_id)
            old = records.get(key)
            if old:
                previous, old_index = old
                if previous.source == "tracked" and run.source == "imported":
                    continue
                if previous.run_id == run.run_id:
                    if previous.revision > run.revision:
                        continue
                    body = run.model_dump()
                    preserve_recovered(previous.attempts[old_index].model_dump(), body["attempts"][index])
                    run = Run.model_validate(body)
            records[key] = (run, index)
    return records


def _remember_run(records, run: Run):
    for index, attempt in enumerate(run.attempts):
        if attempt.session_id:
            records[(run.arena_url, attempt.session_id)] = (run, index)


def known_sessions(root: Path, *, store: Store | None = None) -> set[tuple[str, str]]:
    return set(_session_records(root, store))


def _created(value, fallback):
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value, tz=UTC).isoformat()
        timestamp(value)
        return value
    except (ValueError, TypeError, OverflowError, OSError):
        return fallback


def _new_import(row, state, *, environment, arena_url, author, quota, read_error):
    session_id = row["session_id"]
    case_id = state.get("case_id", row.get("case_id"))
    now = utc_now()
    ended = state.get("status") in ENDED
    result = state.get("result") or {}
    digest = hashlib.sha256(f"{arena_url}\0{session_id}".encode()).hexdigest()[:32]
    return Run.model_validate(
        {
            "schema_version": 1,
            "run_id": "import-" + digest,
            "revision": 1,
            "name": f"Imported {case_id}",
            "author": author,
            "hypothesis": "",
            "agent": "unknown",
            "config": {},
            "source": "imported",
            "environment": environment,
            "arena_url": arena_url,
            "baseline_id": None,
            "started_at": _created(row.get("created_at"), now),
            "updated_at": now,
            "status": "completed" if ended else "failed",
            "cases": [case_id],
            "repetitions": 1,
            "provenance": None,
            "quota": quota.model_dump() if quota else None,
            "attempts": [
                {
                    "attempt_id": f"{case_id}:1",
                    "case_id": case_id,
                    "repeat": 1,
                    "status": "completed" if ended else "failed",
                    "session_id": session_id,
                    "replay_url": None,
                    "score": result.get("score") if ended else None,
                    "rounds": None,
                    "elapsed_s": None,
                    "timeouts": None,
                    "error": None if ended else read_error or "imported session has no completed outcome",
                    "result": sanitize(result),
                    "threads": {},
                }
            ],
        }
    )


def import_history(
    client,
    root: Path,
    *,
    environment: str,
    arena_url: str,
    author: str,
    store: Store | None = None,
    publisher: Publisher | None = None,
) -> dict:
    if environment not in {"practice", "sandbox"}:
        raise ValueError("history import only supports practice and sandbox")
    arena_url = safe_url(arena_url)
    records = _session_records(root, store)
    report = {"imported": 0, "skipped": 0, "failed": 0}
    try:
        quota = quota_snapshot(client)
        rows = client.sessions(environment)
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("invalid arena history")
        for row in rows:
            if not isinstance(row, dict):
                report["failed"] += 1
                continue
            session_id = row.get("session_id")
            if (
                not isinstance(session_id, str)
                or not session_id
                or len(session_id) > 160
                or any(
                    c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-" for c in session_id
                )
            ):
                report["failed"] += 1
                continue
            if row.get("status") in OPEN or row.get("set", environment) != environment:
                report["skipped"] += 1
                continue
            existing = records.get((arena_url, session_id))
            if existing:
                prior, index = existing
                attempt = prior.attempts[index]
                if (attempt.status == "completed" and known_score(attempt.score)) or recovered_result(
                    attempt.model_dump()
                ):
                    report["skipped"] += 1
                    continue
            try:
                read_error = None
                try:
                    state = client.session(session_id)
                except Exception as error:
                    state = {"case_id": row.get("case_id"), "status": "unavailable"}
                    read_error = safe_error(error)
                if state.get("status") in OPEN or state.get("set", environment) != environment:
                    report["skipped"] += 1
                    continue
                result = state.get("result") or {}
                if existing:
                    if (
                        read_error
                        or state.get("status") not in ENDED
                        or not known_score(result.get("score"))
                        or state.get("case_id", attempt.case_id) != attempt.case_id
                    ):
                        report["failed"] += 1
                        continue
                    if prior.source == "tracked":
                        outcome = sanitize(result, budget=min(300000, 800000 // len(prior.attempts)))
                        # Preserve the scalar outcome even when large source evidence is explicitly truncated.
                        outcome["score"] = result["score"]
                        if "deal" in result:
                            outcome["deal"] = result["deal"]
                        enriched = save_reconciliation(prior, session_id, outcome, root)
                        if store:
                            store.reconcile(prior.run_id, session_id, outcome)
                        if publisher:
                            publisher.submit(enriched)
                        _remember_run(records, enriched)
                        report["imported"] += 1
                        continue
                    # Only mutable outcome fields change. Original author/plan/provenance/timestamps
                    # remain intact, and the original failed-read error stays visible after recovery.
                    body = prior.model_dump()
                    body["revision"] += 1
                    body["updated_at"] = utc_now()
                    body["quota"] = quota.model_dump() if quota else body["quota"]
                    body["attempts"][index].update(status="completed", score=result["score"], result=sanitize(result))
                    body["status"] = (
                        "completed" if all(a["status"] == "completed" for a in body["attempts"]) else "failed"
                    )
                    run = Run.model_validate(body)
                else:
                    run = _new_import(
                        row,
                        state,
                        environment=environment,
                        arena_url=arena_url,
                        author=author,
                        quota=quota,
                        read_error=read_error,
                    )
                    index = 0
                if read_error is None:
                    collect_session(client, run.attempts[index], arena_url, budget=300000)
                save_snapshot(run, root)
                if store:
                    store.upsert(run)
                if publisher:
                    publisher.submit(run)
                _remember_run(records, run)
                report["failed" if read_error else "imported"] += 1
            except Exception:
                # Neither exception messages nor upstream error bodies enter output or snapshots.
                report["failed"] += 1
    finally:
        if publisher:
            publisher.close()
    return report
