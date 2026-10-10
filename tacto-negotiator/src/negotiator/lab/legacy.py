"""Import recorded practice sweeps without rewriting original failures or provenance."""

import json
from pathlib import Path

from .models import Run, utc_now
from .publish import save_snapshot
from .runner import sanitize


def import_sweep(source, store, root):
    source = Path(source)
    metadata = json.loads((source / "metadata.json").read_text())
    summary = json.loads((source / "summary.json").read_text())
    attempts = []
    for row in summary:
        case = row["case"]
        raw = json.loads((source / (case.replace(":", "-") + ".json")).read_text())
        failed = bool(row.get("error_type"))
        result = raw.get("result") or {}
        threads = raw.get("threads") or {}
        recovered = source / (case.replace(":", "-") + "-reconciled.json")
        if failed and recovered.exists():
            recovery = json.loads(recovered.read_text())
            result = {"reconciled_result": recovery["state"].get("result") or {},
                      "reconciliation_note": "Operator-assisted recovery; original execution failed."}
            threads = recovery.get("threads") or {}
        timeout_values = row.get("timeouts")
        attempts.append({"attempt_id": case + ":1", "case_id": case, "repeat": 1,
                         "status": "failed" if failed else "completed", "session_id": row.get("session"),
                         "score": None if failed else row.get("score"), "elapsed_s": row.get("elapsed_s"),
                         "timeouts": sum(timeout_values.values()) if isinstance(timeout_values, dict) else None,
                         "error": row.get("error_type"), "result": sanitize(result), "threads": sanitize(threads)})
    now = utc_now()
    run = Run.model_validate({
        "schema_version": 1, "run_id": "legacy-" + source.name, "revision": 1,
        "name": "Recorded sweep " + source.name, "author": "Ece (recorded experiment)",
        "hypothesis": "Historical development sweep; not a new controlled comparison.",
        "agent": "harve/y", "config": {"recorded_policy": metadata.get("policy"),
                                        "parallel": metadata.get("parallel")},
        "source": "tracked", "environment": "practice", "arena_url": "https://arena.tacto.ai",
        "started_at": now, "updated_at": now,
        "status": "failed" if any(a["status"] == "failed" for a in attempts) else "completed",
        "cases": [a["case_id"] for a in attempts], "repetitions": 1,
        "provenance": {"commit": metadata.get("commit")}, "quota": None, "attempts": attempts})
    # The original timestamp is encoded in the recorded directory; no invented execution time.
    from datetime import UTC, datetime

    stamp = datetime.strptime(source.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).isoformat()
    run = run.model_copy(update={"started_at": stamp})
    store.upsert(run)
    save_snapshot(run, Path(root))
    return run
