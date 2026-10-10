"""Durable serial campaign orchestration; sync never executes submitted source."""

import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

from arena_kit.client import ArenaClient

from .execution import launch_worker, prepare_arms
from .ordering import campaign_order
from .runner import assert_simulator_is_local, quota_snapshot
from .worker import durable_json

__all__ = ["campaign_order", "run_campaign", "sync_campaign"]


def campaign_dir(root, campaign_id):
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,240}", campaign_id) or campaign_id in (".", ".."):
        raise ValueError("invalid campaign identity")
    return Path(root).resolve() / campaign_id


def save_state(root, campaign_id, state):
    durable_json(campaign_dir(root, campaign_id) / "state.json", state)


def load_state(root, campaign_id):
    path = campaign_dir(root, campaign_id) / "state.json"
    return (
        json.loads(path.read_text())
        if path.exists()
        else {"campaign_id": campaign_id, "results": {}, "uploaded": [], "started": []}
    )


def outcome(body):
    fields = (
        "attempt_id",
        "checkpoint_id",
        "session_id",
        "status",
        "score",
        "timeouts",
        "result",
        "threads",
        "elapsed_s",
    )
    return {key: body[key] for key in fields if key in body}


def _sync_campaign(client, campaign_id, root):
    state = load_state(root, campaign_id)
    directory = campaign_dir(root, campaign_id)
    state["progress"] = {}
    for path in sorted((directory / "attempts").glob("*/progress.json")):
        body = json.loads(path.read_text())
        state["progress"][body["attempt_id"]] = {
            key: body.get(key) for key in ("attempt_id", "checkpoint_id", "session_id", "status")
        }
    # Recover fsynced worker files even if the orchestrator died before copying to state.
    for path in sorted((directory / "attempts").glob("*/result.json")):
        body = json.loads(path.read_text())
        if body.get("final") is True and body["attempt_id"] not in state["uploaded"]:
            state["results"][body["attempt_id"]] = body
    save_state(root, campaign_id, state)
    campaign = client.read("campaigns", campaign_id)
    for attempt in campaign["attempts"]:
        identity = attempt["attempt_id"]
        worker_request = directory / "attempts" / hashlib.sha256(identity.encode()).hexdigest() / "request.json"
        own_start = state.get("start_requests", {}).get(identity)
        owns_backend = (
            own_start and attempt.get("start", {}).get("request", {}).get("worker_id") == own_start["worker_id"]
        )
        if own_start and identity not in state["results"] and not worker_request.exists():
            # request.json is fsynced before Popen: its absence under the execution lock proves no worker launch.
            if attempt["status"] == "pending":
                state["started"] = [started for started in state.get("started", []) if started != identity]
                state["start_requests"].pop(identity, None)
            elif attempt["status"] == "started" and owns_backend:
                client.write(
                    "attempt-not-created",
                    dict(
                        attempt_id=identity,
                        checkpoint_id=attempt["checkpoint_id"],
                        worker_id=own_start["worker_id"],
                        reason="worker_preflight",
                        http_status=None,
                    ),
                )
    save_state(root, campaign_id, state)
    for attempt_id, body in state["results"].items():
        if attempt_id not in state["uploaded"]:
            if body.get("final") is not True:
                continue
            client.write("attempt-result", outcome(body))
            if body.get("not_created"):
                owner = state.get("start_requests", {}).get(attempt_id)
                if not owner:
                    raise ValueError("not-created recovery requires durable executor ownership")
                client.write("attempt-not-created", {**body["not_created"], "worker_id": owner["worker_id"]})
            state["uploaded"].append(attempt_id)
            save_state(root, campaign_id, state)
    campaign = client.read("campaigns", campaign_id)
    unresolved = [
        a["attempt_id"]
        for a in campaign["attempts"]
        if a["status"] == "started"
        or (
            "start" in a
            and not a.get("reconciliation")
            and not a.get("not_created")
            and a.get("result", {}).get("ended") is not True
        )
    ]
    unresolved.extend(
        a["attempt_id"]
        for a in campaign["attempts"]
        if a["status"] == "pending" and a["attempt_id"] in state.get("started", [])
    )
    state["blocking_attempts"] = unresolved
    if unresolved:
        state["next_action"] = (
            "Stop starts; inspect start intent, verify owned ended session and reconcile explicit attempt/session IDs"
        )
    elif any(a["status"] == "pending" for a in campaign["attempts"]):
        state["next_action"] = "campaign run --campaign-id with the same ID resumes only never-started attempts"
    else:
        state["completion"] = client.write("complete", {"campaign_id": campaign_id})
        state["next_action"] = None
    save_state(root, campaign_id, state)
    return state


def sync_campaign(client, campaign_id, root):
    import fcntl

    directory = campaign_dir(root, campaign_id)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "execution.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("campaign worker is active; sync after it finishes") from None
        return _sync_campaign(client, campaign_id, root)


def arena_snapshot(suite):
    assert_simulator_is_local(suite["environment"], suite["arena_url"])
    client = ArenaClient(base_url=suite["arena_url"], retries=0, rate=1)
    try:
        from arena_kit.play import hosted

        set_ = "practice" if suite["environment"] == "simulator" else suite["environment"]
        allowed = {case["case_id"] for case in hosted(client.cases(set_))}
        if not set(suite["cases"]) <= allowed:
            raise ValueError("requested cases unavailable in declared environment")
        sessions = {}
        for set_ in ("practice", "sandbox"):
            for session in client.sessions(set_):
                sessions[session["session_id"]] = session
        opened = 0
        for identity, session in sessions.items():
            if session.get("status") == "ended" or session.get("ended") is True:
                continue
            if session.get("status") == "open" or session.get("ended") is False:
                opened += 1
                continue
            state = client.session(identity)
            if state.get("ended") is True or state.get("status") == "ended":
                continue
            opened += 1
        if opened >= 10:
            raise ValueError("arena open-session limit reached")
        quota = quota_snapshot(client)
        if suite["environment"] == "practice" and quota is None:
            raise ValueError("authoritative practice quota unavailable")
        return {"remaining": quota.left, "observed_at": time.time(), "open_sessions": opened} if quota else None
    finally:
        client.http.close()


def run_campaign(client, campaign_id, project, root, *, data_paths=None):
    directory = campaign_dir(root, campaign_id)
    directory.mkdir(parents=True, exist_ok=True)
    # One laptop process per local campaign. Server key leases serialize all laptops.
    import fcntl

    with (directory / "execution.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("campaign already running locally") from None
        state = _sync_campaign(client, campaign_id, root)
        if state.get("blocking_attempts") or state.get("completion"):
            return state
        campaign = client.read("campaigns", campaign_id)
        suite = client.read("suites", campaign["suite_id"])
        arena_snapshot(suite)  # Origin and case/environment verification before restored source execution.
        manifests, projects, paths = prepare_arms(client, campaign, project, directory, data_paths, suite)
        key = os.environ.get("ARENA_API_KEY")
        if not key:
            raise ValueError("ARENA_API_KEY required before campaign execution")
        key_id = hashlib.sha256((suite["arena_url"] + "\0" + key).encode()).hexdigest()
        state.setdefault("started", [])
        state.setdefault("start_requests", {})
        for attempt in campaign["attempts"]:
            if attempt["status"] != "pending" or attempt["attempt_id"] in state["started"]:
                continue
            quota = arena_snapshot(suite)
            start = dict(attempt_id=attempt["attempt_id"], worker_id=uuid.uuid4().hex, key_id=key_id, quota=quota)
            state["start_requests"][attempt["attempt_id"]] = start
            # Persist intent before the start request. A lost ACK must block, never execute speculatively.
            state["started"].append(attempt["attempt_id"])
            save_state(root, campaign_id, state)
            try:
                acknowledged = client.write("attempt-start", start)
                if acknowledged.get("start", {}).get("request", {}).get("worker_id") != start["worker_id"]:
                    raise ValueError("attempt start belongs to another executor")
                request = dict(
                    checkpoint=manifests[attempt["arm"]],
                    project=str(projects[attempt["arm"]]),
                    attempt=attempt,
                    attempt_root=str(
                        directory / "attempts" / hashlib.sha256(attempt["attempt_id"].encode()).hexdigest()
                    ),
                    arena_url=suite["arena_url"],
                    environment=suite["environment"],
                    data_paths=paths,
                    worker_id=start["worker_id"],
                )
                result = launch_worker(request, lock_fd=lock.fileno())
                result["final"] = True
                state["results"][attempt["attempt_id"]] = result
                save_state(root, campaign_id, state)
                state = _sync_campaign(client, campaign_id, root)
                if state.get("blocking_attempts") or result.get("status") != "completed":
                    break
            except BaseException:
                state["next_action"] = (
                    "Stop new starts; sync durable results and explicitly reconcile any started attempt"
                )
                save_state(root, campaign_id, state)
                raise
        return _sync_campaign(client, campaign_id, root)


def reconcile_attempt(client, campaign_id, attempt_id, session_id):
    campaign = client.read("campaigns", campaign_id)
    attempt = next((a for a in campaign["attempts"] if a["attempt_id"] == attempt_id), None)
    if attempt is None or "start" not in attempt:
        raise ValueError("attempt was not started in this campaign")
    suite = client.read("suites", campaign["suite_id"])
    arena = ArenaClient(base_url=suite["arena_url"], retries=0, rate=1)
    try:
        owned = {s["session_id"] for set_ in ("practice", "sandbox") for s in arena.sessions(set_)}
        if session_id not in owned:
            raise ValueError("session is not owned")
        result = arena.session(session_id)
        case = result.get("case_id", result.get("case", {}).get("case_id"))
        if result.get("ended") is not True or case != attempt["case_id"]:
            raise ValueError("session must be ended and match planned case")
        threads = {sid: arena.thread(session_id, sid) for sid in result.get("threads", {})}
        from .runner import sanitize

        body = dict(
            attempt_id=attempt_id,
            checkpoint_id=attempt["checkpoint_id"],
            session_id=session_id,
            result=sanitize(result),
            threads=sanitize(threads),
            score=result.get("score"),
            timeouts=None,
        )
        return client.write("attempt-reconcile", body)
    finally:
        arena.http.close()
