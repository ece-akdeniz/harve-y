"""Tracked serial and async experiments using the existing negotiation runners."""

import asyncio
import difflib
import hashlib
import importlib
import ipaddress
import json
import math
import os
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from arena_kit.client import ArenaError
from arena_kit.play import RemoteTable, hosted

from negotiator.play import play_case as play

from .models import MAX_ATTEMPTS, SECRET_KEYS, Quota, Run, check_json, safe_url, utc_now
from .publish import Publisher, save_snapshot


def _git(repo: Path, *args) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return result.stdout.decode("utf-8", errors="replace")


def _private_path(path: str) -> bool:
    parts = Path(path).parts
    return any(
        part.startswith(".env")
        or part == ".lab-secrets.env"
        or part in {".aws", ".codex", ".agents"}
        or SECRET_KEYS.search(part)
        for part in parts
    )


def fingerprint_data(directory: Path) -> str | None:
    if not directory.is_dir():
        return None
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("data fingerprint cannot include symbolic links")
        if path.is_file():
            relative = path.relative_to(directory).as_posix().encode()
            digest.update(len(relative).to_bytes(8, "big") + relative)
            content = path.read_bytes()
            digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


def capture_provenance(
    repo: Path, *, data_dir: Path, release_dir: Path | None = None, allow_dirty=False
) -> tuple[dict, str | None]:
    project = Path(repo).resolve()
    repo = Path(_git(repo, "rev-parse", "--show-toplevel").strip())
    commit = _git(repo, "rev-parse", "HEAD").strip()
    dirty = bool(_git(repo, "status", "--porcelain"))
    if dirty and not allow_dirty:
        raise ValueError("working tree is dirty; commit changes or pass --allow-dirty")
    patch = None
    if dirty:
        # Only nonprivate paths enter the local patch; its contents never enter snapshots.
        tracked = _git(repo, "diff", "HEAD", "--name-only", "-z").split("\0")
        tracked = [p for p in tracked if p and not _private_path(p)]
        patch = _git(repo, "diff", "HEAD", "--binary", "--", *tracked) if tracked else ""
        untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
        for name in untracked:
            path = repo / name
            if name and not _private_path(name) and path.is_file() and not path.is_symlink():
                content = path.read_text(errors="replace")
                patch += "".join(
                    difflib.unified_diff(
                        [], content.splitlines(keepends=True), fromfile="/dev/null", tofile="b/" + name
                    )
                )
        # Do not record environment credentials even if someone put them in a source diff.
        for secret in _secret_values():
            patch = patch.replace(secret, "[redacted]")
    lock_root = project
    while not (lock_root / "uv.lock").is_file() and lock_root != repo:
        lock_root = lock_root.parent
    lock = lock_root / "uv.lock"
    base_hash = fingerprint_data(data_dir)
    overlay_hash = fingerprint_data(release_dir) if release_dir else None
    if release_dir is not None and overlay_hash is None:
        raise ValueError("configured data overlay directory is unavailable")
    data_hash = (
        hashlib.sha256(f"base:{base_hash}\nrelease:{overlay_hash}".encode()).hexdigest()
        if base_hash is not None and overlay_hash is not None
        else base_hash
    )
    return (
        {
            "commit": commit,
            "dirty": dirty,
            "patch_sha256": hashlib.sha256(patch.encode()).hexdigest() if patch is not None else None,
            "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.is_file() else None,
            "data_sha256": data_hash,
        },
        patch,
    )


def _secret_values():
    return [value for key, value in os.environ.items() if SECRET_KEYS.search(key) and len(value) >= 8]


def sanitize(value, *, budget=120000):
    """Remove credential fields, redact known credentials, and cap supplier evidence size."""
    secrets = _secret_values()

    def visit(node, depth=0):
        if depth > 10:
            return "[truncated]"
        if isinstance(node, dict):
            return {
                str(k)[:256]: visit(v, depth + 1)
                for k, v in list(node.items())[:1000]
                if not SECRET_KEYS.search(str(k))
            }
        if isinstance(node, list):
            return [visit(v, depth + 1) for v in node[:1000]]
        if isinstance(node, str):
            for secret in secrets:
                node = node.replace(secret, "[redacted]")
            return node[:65536]
        if node is None or isinstance(node, (int, float, bool)):
            return node if not isinstance(node, (int, float)) or math.isfinite(node) else None
        return "[unsupported value]"

    result = visit(value)
    if len(json.dumps(result, allow_nan=False).encode()) > budget:
        return {"evidence_truncated": True, "note": "Evidence exceeded the snapshot budget; outcome metrics retained."}
    return result


def agent_factory(name: str, config: dict):
    check_json(config)
    if name == "package":
        from negotiator.agent import PackageAgent

        factory = PackageAgent
    elif name == "naive":
        from arena_kit.agents import NaiveAgent

        factory = NaiveAgent
    else:
        module, sep, attribute = name.partition(":")
        if not sep or not module or not attribute.isidentifier():
            raise ValueError("agent must be package, naive or module:factory")
        factory = getattr(importlib.import_module(module), attribute)
    if not callable(factory):
        raise ValueError("agent factory is not callable")

    def create():
        agent = factory(**config)
        if not callable(getattr(agent, "decide", None)):
            raise ValueError("agent must implement decide(case, threads)")
        return agent

    # Validate before opening sessions and reuse that first object, avoiding construction side effects.
    first = [create()]

    def next_agent():
        return first.pop() if first else create()

    return next_agent


def assert_simulator_is_local(environment: str, arena_url: str) -> None:
    if environment != "simulator":
        return
    host = urlsplit(safe_url(arena_url)).hostname
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host == "localhost"
    if not local:
        raise ValueError("simulator runs require a loopback ARENA_URL (localhost, 127.0.0.1 or ::1)")


RUNNERS = ("serial", "async", "auto")
# `auto` routes each attempt by hosted case type: multi-supplier RFQ cases need the async
# runner (concurrent supplier windows, measured P05 `rfq_nonleading_hold`); every other case
# keeps the serial runner, where the serial-only levers (package advice, expected-C target) live.
ASYNC_CASE_TYPES = frozenset({"rfq"})


def attempt_runner(run, case_type):
    runner = run.config.get("_lab_runner", "serial")
    if runner == "auto":
        return "async" if case_type in ASYNC_CASE_TYPES else "serial"
    return runner


def plan_run(
    *,
    name,
    author,
    hypothesis,
    agent,
    config,
    cases,
    repetitions,
    max_sessions,
    environment,
    arena_url,
    provenance,
    baseline_id=None,
    runner="serial",
) -> Run:
    if (
        type(repetitions) is not int
        or type(max_sessions) is not int
        or not cases
        or len(set(cases)) != len(cases)
        or repetitions < 1
        or max_sessions < 1
        or max_sessions > MAX_ATTEMPTS
        or len(cases) * repetitions > max_sessions
    ):
        raise ValueError("case/repetition plan exceeds the explicit session ceiling")
    if runner not in RUNNERS:
        raise ValueError("unsupported runner")
    if runner == "async" and len(cases) * repetitions != 1:
        raise ValueError("async standalone runs require exactly one attempt")
    assert_simulator_is_local(environment, arena_url)
    check_json(config)
    if any(secret in json.dumps(config) for secret in _secret_values()):
        raise ValueError("configuration contains private credentials")
    public_manifest = {
        "name": name,
        "author": author,
        "hypothesis": hypothesis,
        "agent": agent,
        "arena_url": arena_url,
        "baseline_id": baseline_id,
    }
    if any(secret in json.dumps(public_manifest) for secret in _secret_values()):
        raise ValueError("manifest contains private credentials")
    model_environment = {
        key: os.environ[key] for key in ("LLM_PROVIDER", "LLM_MODEL", "LLM_EFFORT") if os.environ.get(key)
    }
    if any(k in config for k in ("_lab_environment", "_lab_runner")):
        raise ValueError("configuration uses a reserved metadata field")
    recorded_config = {**config, "_lab_runner": runner,
                       **({"_lab_environment": model_environment} if model_environment else {})}
    check_json(recorded_config)
    if any(secret in json.dumps(recorded_config) for secret in _secret_values()):
        raise ValueError("configuration contains private credentials")
    now = utc_now()
    return Run.model_validate(
        {
            "schema_version": 1,
            "run_id": str(uuid.uuid4()),
            "revision": 1,
            "name": name,
            "author": author,
            "hypothesis": hypothesis,
            "agent": agent,
            "config": recorded_config,
            "source": "tracked",
            "environment": environment,
            "arena_url": safe_url(arena_url),
            "baseline_id": baseline_id,
            "started_at": now,
            "updated_at": now,
            "status": "running",
            "cases": cases,
            "repetitions": repetitions,
            "provenance": provenance,
            "quota": None,
            "attempts": [
                {
                    "attempt_id": f"{case}:{repeat}",
                    "case_id": case,
                    "repeat": repeat,
                    "status": "pending",
                    "session_id": None,
                    "replay_url": None,
                    "score": None,
                    "rounds": None,
                    "elapsed_s": None,
                    "timeouts": None,
                    "error": None,
                    "result": {},
                    "threads": {},
                }
                for case in cases
                for repeat in range(1, repetitions + 1)
            ],
        }
    )


def quota_snapshot(client) -> Quota | None:
    try:
        body = client.me()
        practice = body.get("practice", {})
        used = practice.get("used", body.get("practice_sessions_used"))
        left = practice.get("left", body.get("practice_sessions_left"))
        limit = practice.get("limit", body.get("practice_sessions_limit"))
        if limit is None and type(used) is int and type(left) is int:
            limit = used + left
        return Quota.model_validate({"used": used, "left": left, "limit": limit, "checked_at": utc_now()})
    except Exception:
        return None


def replay_url(value, arena_url):
    if not isinstance(value, str) or not value:
        return None
    try:
        full = safe_url(urljoin(arena_url + "/", value))
        arena, target = urlsplit(arena_url), urlsplit(full)
        return full if (target.scheme, target.netloc) == (arena.scheme, arena.netloc) else None
    except ValueError:
        return None


def safe_error(error: Exception | BaseException) -> str:
    if isinstance(error, ArenaError):
        return f"arena request failed (HTTP {error.status}); inspect the arena session before retrying"
    if isinstance(error, KeyboardInterrupt):
        return "run interrupted; inspect the arena session before starting another attempt"
    return f"attempt failed ({type(error).__name__}); inspect the arena session before retrying"


class RecordingTable(RemoteTable):
    def __init__(self, client, attempt, changed):
        super().__init__(client)
        self.attempt, self.changed = attempt, changed
        self.rounds = 0
        self.seen_threads = {}

    def open(self, case_id):
        case, threads = super().open(case_id)
        self.attempt.session_id = self.session_id
        self.changed()  # durably record identity before documents or the first decision
        self.seen_threads = threads
        return case, threads

    def send(self, supplier_id, message):
        self.rounds += 1
        return super().send(supplier_id, message)

    def close(self, supplier_id, message):
        self.rounds += 1
        return super().close(supplier_id, message)


def collect_session(client, attempt, arena_url, *, budget):
    """Only owned session/thread reads, after negotiation; never spectator routes."""
    if not attempt.session_id:
        return
    try:
        state = client.session(attempt.session_id)
        attempt.replay_url = replay_url(state.get("replay_url"), arena_url)
        if type(state.get("rounds")) is int:
            attempt.rounds = max(0, state["rounds"])
        threads, timeouts = {}, 0
        for supplier in list(state.get("threads", {}))[:100]:
            thread = client.thread(attempt.session_id, supplier)
            threads[supplier] = thread
            timeout_values = thread.get("timeouts", [])
            timeouts += len(timeout_values) if isinstance(timeout_values, list) else max(0, int(timeout_values or 0))
        attempt.threads = sanitize(threads, budget=budget)
        attempt.timeouts = timeouts
    except Exception:
        # Failure to read ancillary evidence never invents a negotiation score or overwrites the outcome.
        if not attempt.error:
            attempt.error = "session detail unavailable; outcome retained"


def play_async_attempt(run, attempt, root, agent, changed):
    """One journalled session; failures retain its identity and never start a replacement."""
    from negotiator.client import AsyncArena
    from negotiator.runner import CaseRunner
    from negotiator.state import Journal

    class RecordingJournal(Journal):
        def session(self, case_id, session_id, case=None):
            record = super().session(case_id, session_id, case)
            attempt.session_id = session_id
            changed()  # before documents or the first buyer move
            return record

    journal = RecordingJournal(root / run.run_id / f"async-{attempt.repeat}-{attempt.case_id.replace(':', '-')}.jsonl")
    # Reinvoking run_experiment is not an implicit resume/new-session mechanism.
    if journal.records:
        attempt.session_id = journal.session_for(attempt.case_id)
        changed()
        raise ValueError("async attempt already journalled; reconcile the existing session")

    async def execute():
        arena = AsyncArena(base_url=run.arena_url, retries=0, calls_per_s=2)
        try:
            runner = CaseRunner(arena, attempt.case_id, agent, journal, tracer=getattr(agent, "tracer", None))
            return await runner.run()
        finally:
            attempt.session_id = journal.session_for(attempt.case_id)
            changed()
            await arena.aclose()

    return asyncio.run(execute())


def run_experiment(
    run: Run, root: Path, client, create_agent, *, publisher: Publisher | None = None, patch: str | None = None
) -> Run:
    if run.status != "running" or any(a.status != "pending" for a in run.attempts):
        raise ValueError("run already attempted; reconcile or sync its existing records")

    def persist():
        run.revision += 1
        run.updated_at = utc_now()
        save_snapshot(run, root)
        if publisher:
            publisher.submit(run)

    def session_created():
        left = getattr(client, "practice_remaining", None)
        if run.quota and type(left) is int and 0 <= left <= run.quota.limit and left != run.quota.left:
            run.quota = Quota(used=run.quota.limit - left, left=left, limit=run.quota.limit, checked_at=utc_now())
        persist()

    save_snapshot(run, root, patch=patch)  # before any arena networking
    if publisher:
        publisher.submit(run)
    budget = min(300000, 800000 // len(run.attempts))
    try:
        assert_simulator_is_local(run.environment, run.arena_url)
        set_ = "practice" if run.environment == "simulator" else run.environment
        hosted_cases = hosted(client.cases(set_))
        allowed = {c["case_id"] for c in hosted_cases}
        case_types = {c["case_id"]: c.get("type") for c in hosted_cases}
        if not set(run.cases) <= allowed:
            raise ValueError("requested case is not hosted in this environment")
        run.quota = quota_snapshot(client)
        if run.environment == "practice" and run.quota and run.quota.left < len(run.attempts):
            raise ValueError("authoritative practice quota is below the planned session count")
        persist()
        for attempt in run.attempts:
            attempt.status = "running"
            persist()
            table = RecordingTable(client, attempt, session_created)
            started = time.monotonic()
            agent = None
            mode = "serial"
            try:
                agent = create_agent()
                mode = attempt_runner(run, case_types.get(attempt.case_id))
                if mode == "async":
                    policy = getattr(agent, "policy", None)
                    if (getattr(agent, "package_advisor", None) is not None and policy is not None
                            and case_types.get(attempt.case_id) not in policy.package_advice_types):
                        agent.package_advisor = None  # inert for this case type; async rejects it
                if mode == "async":
                    result = play_async_attempt(run, attempt, root, agent, persist)
                else:
                    result = play(table, attempt.case_id, agent)
                score = result.get("score")
                if score is not None and (
                    isinstance(score, bool)
                    or not isinstance(score, (int, float))
                    or not math.isfinite(score)
                    or not 0 <= score <= 1
                ):
                    raise ValueError("invalid arena score")
                attempt.result = sanitize(result, budget=budget)
                attempt.score = float(score) if score is not None else None
                attempt.status = "completed"
            except KeyboardInterrupt as error:
                attempt.status, attempt.error = "failed", safe_error(error)
                run.status = "interrupted"
                raise
            except Exception as error:
                attempt.status, attempt.error = "failed", safe_error(error)
                if isinstance(error, ArenaError) and error.status == 429:
                    run.status = "failed"
                    break
            finally:
                metrics = getattr(agent, "experiment_metrics", None)
                if callable(metrics):
                    try:
                        attempt.result["agent_metrics"] = sanitize(metrics(), budget=10000)
                    except Exception:
                        attempt.result["agent_metrics"] = {"unavailable": True}
                attempt.elapsed_s = min(604800.0, time.monotonic() - started)
                if mode == "serial":
                    attempt.rounds = table.rounds
                    attempt.threads = sanitize(table.seen_threads, budget=budget)
                # Persist the outcome immediately before ancillary read calls.
                persist()
            collect_session(client, attempt, run.arena_url, budget=budget)
            persist()
        if run.status == "running":
            run.status = "completed" if all(a.status == "completed" for a in run.attempts) else "failed"
    except KeyboardInterrupt:
        run.status = "interrupted"
    except Exception as error:
        run.status = "failed"
        for attempt in run.attempts:
            if attempt.status == "pending":
                attempt.status, attempt.error = "failed", safe_error(error)
    finally:
        run.quota = quota_snapshot(client) or run.quota
        persist()
        if publisher:
            publisher.close()
    return run
