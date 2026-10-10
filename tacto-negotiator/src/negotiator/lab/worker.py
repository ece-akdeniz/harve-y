"""Single-attempt checkpoint worker. Public request on stdin, credentials in env only."""

import asyncio
import contextlib
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from .checkpoints import _data_hash
from .runner import RecordingTable, collect_session, sanitize


def durable_json(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as stream:
        json.dump(body, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def prepare_environment(manifest, data_paths, root):
    for key in list(os.environ):
        if key.startswith("NEGOTIATOR_") or key in ("ARENA_DATA", "ARENA_RELEASE", "PYTHONPATH"):
            os.environ.pop(key, None)
    data = manifest["data"]
    if set(data) - {"base", "release"} or ("release" in data and "base" not in data):
        raise ValueError("unsupported data mapping")
    for name, entry in data.items():
        if name not in data_paths or _data_hash(Path(data_paths[name])) != entry["sha256"]:
            raise ValueError("required data missing or changed")
        os.environ["ARENA_DATA" if name == "base" else "ARENA_RELEASE"] = str(data_paths[name])
    empty = Path(root) / "empty-data"
    empty.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ARENA_DATA", str(empty))
    os.environ.setdefault("ARENA_RELEASE", str(empty))
    config = manifest["config"]
    if config.get("estimates") is None:
        os.environ["NEGOTIATOR_ESTIMATES"] = "1"
    if config.get("claims"):
        os.environ["NEGOTIATOR_CLAIMS"] = "1"
    if (config.get("estimates") is None or config.get("claims")) and "base" not in data:
        raise ValueError("enabled dossier features require base data")


def validate_runtime(request):
    manifest = request["checkpoint"]
    project = Path(request["project"]).resolve()
    if Path(__file__).resolve().parents[2] != project / "src":
        raise ValueError("worker source does not match checkpoint project")
    if hashlib.sha256((project / "uv.lock").read_bytes()).hexdigest() != manifest["lock_sha256"]:
        raise ValueError("checkpoint lock mismatch")
    prepare_environment(manifest, request.get("data_paths", {}), request["attempt_root"])
    if manifest["config"].get("estimates") is None or manifest["config"].get("claims"):
        from negotiator.dossiers import load_package

        load_package(os.environ["ARENA_DATA"], os.environ["ARENA_RELEASE"])
    return manifest


def execute(request):
    from negotiator.agent import PackageAgent
    from negotiator.play import play_case

    manifest = validate_runtime(request)
    root = Path(request["attempt_root"])
    attempt = request["attempt"]
    body = dict(
        attempt_id=attempt["attempt_id"],
        checkpoint_id=manifest["checkpoint_id"],
        session_id=None,
        status="ambiguous",
        score=None,
        timeouts=None,
        result={},
        threads={},
        elapsed_s=None,
    )
    path = root / "progress.json"
    durable_json(path, body)
    from .transport import JournaledArena

    client = JournaledArena(root / "serial.jsonl", base_url=request["arena_url"], rate=2)
    record = SimpleNamespace(session_id=None, replay_url=None, rounds=None, threads={}, timeouts=None, error=None)
    started = time.monotonic()

    def changed():
        body["session_id"] = record.session_id
        durable_json(path, body)

    try:
        agent = PackageAgent(**manifest["config"])
        if manifest["runner"] == "serial":
            result = play_case(RecordingTable(client, record, changed), attempt["case_id"], agent)
        else:
            from negotiator.client import AsyncArena
            from negotiator.runner import play_case as async_play
            from negotiator.state import Journal

            journal = Journal(root / "journal.jsonl")

            async def run():
                arena = AsyncArena(base_url=request["arena_url"], retries=0, calls_per_s=2)
                try:
                    return await async_play(arena, attempt["case_id"], agent, journal)
                finally:
                    record.session_id = journal.session_for(attempt["case_id"])
                    changed()
                    await arena.aclose()

            result = asyncio.run(run())
        body.update(
            session_id=record.session_id, status="completed", score=result.get("score"), result=sanitize(result)
        )
    except BaseException:
        # No retry of an uncertain open. Preserve durable identity and any already journaled session.
        body["status"] = "ambiguous"
    finally:
        body["elapsed_s"] = time.monotonic() - started
        durable_json(path, body)
        if record.session_id:
            try:
                state = client.session(record.session_id)
                body["result"] = sanitize({**body["result"], **state})
                if state.get("ended") is True and body["status"] != "completed":
                    body["status"] = "failed"
            except Exception:
                pass
            collect_session(client, record, request["arena_url"], budget=300000)
            body.update(threads=record.threads, timeouts=record.timeouts)
        client.http.close()
        if body["session_id"] is None and body["status"] == "ambiguous":
            journals = []
            for journal_path in (root / "serial.jsonl", root / "journal.jsonl"):
                if journal_path.exists():
                    journals.extend(json.loads(line) for line in journal_path.read_text().splitlines() if line)
            opens = [
                r
                for r in journals
                if r.get("rec") == "intent" and (r.get("path") == "/sessions" or r.get("kind") == "open")
            ]
            proof = None
            if not opens:
                proof = dict(reason="worker_preflight", http_status=None)
            elif len(opens) == 1:
                rejection = next(
                    (
                        r
                        for r in journals
                        if r.get("move_id") == opens[0]["move_id"]
                        and r.get("http") in (400, 401, 403, 404, 422, 429)
                        and r.get("rec") == "failed"
                    ),
                    None,
                )
                if rejection:
                    proof = dict(reason="arena_rejected", http_status=rejection["http"])
            if proof:
                body["status"] = "failed"
                body["not_created"] = dict(attempt_id=body["attempt_id"], checkpoint_id=body["checkpoint_id"], **proof)
        body["runtime"] = {
            "harness": manifest["harness_version"],
            "python": sys.version.split()[0],
            "runner": manifest["runner"],
            "lock_sha256": manifest["lock_sha256"],
        }
        body["final"] = True
        durable_json(root / "result.json", body)
    return body


def main():
    request = json.load(sys.stdin)
    if "--preflight" in sys.argv:
        try:
            manifest = validate_runtime(request)
            from negotiator.agent import PackageAgent

            PackageAgent(**manifest["config"])
        except Exception:
            print(json.dumps({"schema_version": 1, "error": "checkpoint runtime preflight failed"}))
            return 2
        print(json.dumps({"schema_version": 1, "preflight": True}))
        return 0
    # Runtime stdout belongs to the local diagnostic log, never the result protocol.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            result = execute(request)
    except Exception:
        root = Path(request["attempt_root"])
        result = dict(
            attempt_id=request["attempt"]["attempt_id"],
            checkpoint_id=request["checkpoint"]["checkpoint_id"],
            status="ambiguous",
            session_id=None,
            result={},
            threads={},
            score=None,
            timeouts=None,
        )
        known = root / "progress.json"
        if known.exists():
            try:
                result.update(json.loads(known.read_text()))
            except (ValueError, OSError):
                pass
        records = []
        unreadable = False
        for path in (root / "serial.jsonl", root / "journal.jsonl"):
            if path.exists():
                try:
                    records.extend(json.loads(line) for line in path.read_text().splitlines() if line)
                except (ValueError, OSError):
                    unreadable = True
        opened = any(
            r.get("rec") == "intent" and (r.get("path") == "/sessions" or r.get("kind") == "open") for r in records
        )
        if not unreadable and not opened and not result.get("session_id"):
            result["status"] = "failed"
            result["not_created"] = dict(
                attempt_id=result["attempt_id"],
                checkpoint_id=result["checkpoint_id"],
                reason="worker_preflight",
                http_status=None,
            )
        result["final"] = True
        durable_json(root / "result.json", result)
    print(json.dumps({"schema_version": 1, **result}))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
