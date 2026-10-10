"""Publish recorded practice sessions to the shared lab, with local retry files."""

import argparse
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from arena_kit.cli import load_env

SECRET_KEY = re.compile(r"(^|_)(api_key|password|token|secret|authorization|credentials)(_|$)", re.I)


def sanitize(value, secrets, depth=0):
    if depth > 10:
        return "[truncated]"
    if isinstance(value, dict):
        return {str(key)[:256]: sanitize(child, secrets, depth + 1)
                for key, child in list(value.items())[:1000] if not SECRET_KEY.search(str(key))}
    if isinstance(value, list):
        return [sanitize(child, secrets, depth + 1) for child in value[:1000]]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, "[redacted]")
        return value[:65536]
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    return "[unsupported value]"


def snapshot(record, metadata, *, author, arena_url, quota=None, revision=1):
    case, session = record["case"], record["session"]
    result, state, threads = record.get("result", {}), record.get("state", {}), record.get("threads", {})
    secrets = [value for key, value in os.environ.items() if SECRET_KEY.search(key) and len(value) >= 8]
    cleaned_threads = sanitize(threads, secrets)
    if len(json.dumps(cleaned_threads).encode()) > 120000:
        cleaned_threads = {"evidence_truncated": True}
    stamp = datetime.now(UTC).isoformat()
    started = metadata.get("started_at") or datetime.strptime(
        metadata["run_dir_timestamp"], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()
    timeouts = sum(len(t.get("timeouts", [])) if isinstance(t.get("timeouts", []), list)
                   else int(t.get("timeouts") or 0) for t in threads.values()) if threads else None
    score = result.get("score")
    status = "completed" if isinstance(score, (int, float)) and math.isfinite(score) else "failed"
    run_id = f"ece-{case.split(':')[-1].lower()}-{session}"
    attempt = {"attempt_id": f"{run_id}-1", "case_id": case, "repeat": 1,
               "status": status, "session_id": session,
               "replay_url": urljoin(arena_url.rstrip("/") + "/", state["replay_url"])
               if state.get("replay_url") else None,
               "score": float(score) if status == "completed" else None,
               "rounds": state.get("rounds") if type(state.get("rounds")) is int else None,
               "elapsed_s": float(record.get("elapsed_s", 0)), "timeouts": timeouts,
               "error": None if status == "completed" else "Arena outcome unavailable",
               "result": sanitize(result, secrets), "threads": cleaned_threads}
    return {"schema_version": 1, "run_id": run_id, "revision": revision,
            "name": f"{case} practice sweep", "author": author,
            "hypothesis": "Recorded practice sweep of the current agent branch",
            "agent": metadata.get("agent", "y/agent"),
            "config": {"policy": metadata.get("policy", "practice-sweep"), "evidence": True},
            "source": "tracked", "environment": "practice", "arena_url": arena_url,
            "baseline_id": None, "started_at": started, "updated_at": stamp,
            "status": status, "cases": [case], "repetitions": 1,
            "provenance": {"commit": metadata.get("commit"), "dirty": False,
                           "patch_sha256": None, "lock_sha256": None, "data_sha256": None},
            "quota": quota, "attempts": [attempt]}


def publish(record_path, *, strict=False):
    """Save a retryable snapshot, then upload it when lab credentials are configured."""
    root = Path(record_path).parent
    record = json.loads(Path(record_path).read_text())
    if not record.get("session") or not record.get("case"):
        return False
    metadata = json.loads((root / "metadata.json").read_text())
    metadata["run_dir_timestamp"] = root.name.split("-practice-")[0]
    url, token = os.environ.get("LAB_URL", ""), os.environ.get("LAB_UPLOAD_TOKEN", "")
    if bool(url) != bool(token):
        raise ValueError("Set both LAB_URL and LAB_UPLOAD_TOKEN to enable publishing")
    quota_path = root / "quota-after.json"
    quota = None
    raw, checked_at = record.get("quota") or {}, record.get("quota_checked_at")
    if quota_path.exists():
        raw = json.loads(quota_path.read_text())
        checked_at = datetime.fromtimestamp(quota_path.stat().st_mtime, UTC).isoformat()
    if all(type(raw.get(key)) is int for key in ("used", "left", "limit")):
        quota = {key: raw[key] for key in ("used", "left", "limit")}
        quota["checked_at"] = checked_at
    body = snapshot(record, metadata, author=os.environ.get("LAB_AUTHOR", "Ece"),
                    arena_url=os.environ.get("ARENA_URL", "https://arena.tacto.ai"),
                    quota=quota, revision=2 if quota else 1)
    path = Path(record_path).with_suffix(".lab.json")
    path.write_text(json.dumps(body, ensure_ascii=False, allow_nan=False))
    path.chmod(0o600)
    if not url:
        return False
    try:
        response = httpx.put(f"{url.rstrip('/')}/api/runs/{body['run_id']}", json=body,
                             headers={"Authorization": f"Bearer {token}"}, timeout=15)
        response.raise_for_status()
        accepted = response.json().get("ok") is True
    except (httpx.HTTPError, ValueError) as exc:
        if strict:
            raise RuntimeError(f"Lab upload failed for {body['run_id']}: {type(exc).__name__}") from exc
        return False
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="saved practice sweep directory to sync")
    args = parser.parse_args()
    load_env()
    for path in sorted(args.run_dir.glob("case-*.json")):
        print(path.stem, "uploaded" if publish(path, strict=True) else "not configured", flush=True)


if __name__ == "__main__":
    main()
