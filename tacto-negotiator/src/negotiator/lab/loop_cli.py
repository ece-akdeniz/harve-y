"""Versioned JSON coding-agent interface for checkpoints, campaigns and recommendations."""

import argparse
import getpass
import json
import os
import uuid
from pathlib import Path

from arena_kit.cli import load_env

from .campaign import arena_snapshot, campaign_dir, reconcile_attempt, run_campaign, sync_campaign
from .checkpoints import _save, create_checkpoint, load_checkpoint, publish_checkpoint, restore_checkpoint
from .loop_client import LoopClient, LoopError
from .policy import default_suite, evaluate_campaign


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid command arguments")


def _shared(parser):
    parser.add_argument("--url", default=os.environ.get("LAB_URL"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--root", type=Path, default=Path("experiments/loop"))
    parser.add_argument("--author", default=os.environ.get("LAB_AUTHOR") or getpass.getuser())
    parser.add_argument("--format", choices=("json", "markdown"), default="json")


def add_loop_commands(subparsers):
    loop = subparsers.add_parser("loop", help="immutable checkpoints and executable local campaigns")
    configure(loop)
    return loop


def configure(parser=None, *, groups=None):
    if groups is None:
        groups = parser.add_subparsers(dest="loop_group", required=True)
    for group, commands in {
        "checkpoint": ("create", "publish", "show"),
        "suite": ("list", "show", "create"),
        "family": ("create", "show"),
        "recommended": ("seed", "show", "history", "restore"),
        "campaign": ("run", "status", "compare", "sync", "reconcile"),
        "evidence": ("show",),
        "findings": ("add", "list"),
        "memory": ("graph", "snapshots", "show", "build"),
        "learning": ("proposals", "prepare", "register", "review"),
    }.items():
        parent = groups.add_parser(group)
        parent.set_defaults(loop_group=group)
        sub = parent.add_subparsers(dest="loop_action", required=True)
        for action in commands:
            leaf = sub.add_parser(action)
            _shared(leaf)
            if action in ("show", "publish", "status", "compare", "sync"):
                leaf.add_argument("identity")
            if group == "checkpoint" and action == "create":
                leaf.add_argument("--config", default="{}")
                leaf.add_argument("--memory", help="immutable registered memory snapshot ID")
                leaf.add_argument("--runner", choices=("serial", "async"), default="serial")
                leaf.add_argument("--description", required=True)
                leaf.add_argument("--parent")
                leaf.add_argument("--data", default="{}", help="public data fingerprint manifest JSON or @file")
            if group == "memory" and action == "build":
                leaf.add_argument("--arena-url", required=True)
                leaf.add_argument("--environment", choices=("sandbox", "practice", "simulator"), required=True)
                leaf.add_argument("--source-case", action="append", required=True)
            if group == "learning" and action in {"register", "review"}:
                leaf.add_argument("--body", required=True, help="public JSON request or @file")
            if group == "learning" and action == "prepare":
                leaf.add_argument("--proposal", required=True)
                leaf.add_argument("--suite", required=True)
            if action in ("create", "seed", "restore", "add") and group != "checkpoint":
                leaf.add_argument("--body", help="public JSON object or @file")
            if group == "family" and action == "create":
                leaf.add_argument("--family-id")
                leaf.add_argument("--max-sessions", type=int)
                leaf.add_argument("--practice-allowance", type=int, default=0)
                leaf.add_argument("--reserve", type=int, default=0)
            if group == "recommended":
                if action in ("seed", "restore"):
                    leaf.add_argument("--suite", default="d01-d02-sandbox-serial-v1")
                    leaf.add_argument("--checkpoint")
                    leaf.add_argument("--request-id")
                if action == "history":
                    leaf.add_argument("--suite")
            if group == "campaign" and action == "run":
                leaf.add_argument("--campaign-id")
                leaf.add_argument("--family")
                leaf.add_argument("--candidate")
                leaf.add_argument("--suite", default="d01-d02-sandbox-serial-v1")
                leaf.add_argument("--max-sessions", type=int)
                leaf.add_argument("--practice-allowance", type=int)
                leaf.add_argument("--reserve", type=int)
                leaf.add_argument("--seed", type=int, default=0)
                leaf.add_argument("--hypothesis")
                leaf.add_argument("--data-paths", default="{}")
            if group == "evidence":
                leaf.add_argument("--supplier")
                leaf.add_argument("--message", type=int)
                leaf.add_argument("--campaign")
                leaf.add_argument("--case")
            if group == "findings" and action == "list":
                leaf.add_argument("--campaign")
            if group == "campaign" and action == "reconcile":
                leaf.add_argument("identity")
                leaf.add_argument("--attempt", required=True)
                leaf.add_argument("--session", required=True)
    restore = groups.add_parser("restore")
    restore.set_defaults(loop_group="restore")
    _shared(restore)
    restore.add_argument("identity")
    restore.add_argument("--destination", type=Path, required=True)
    restore.add_argument("--data-paths", default="{}")


def public_json(value):
    if value is None:
        raise ValueError("JSON object required")
    body = json.loads(Path(value[1:]).read_text() if value.startswith("@") else value)
    if not isinstance(body, dict):
        raise ValueError("JSON object required")
    from .models import check_json

    check_json(body)
    return body


def _checkpoint(client, identity, root):
    try:
        return load_checkpoint(identity, root / "checkpoints")
    except FileNotFoundError:
        return client.read("checkpoints", identity)


def dispatch(args):
    group, action = args.loop_group, getattr(args, "loop_action", None)
    if group == "checkpoint" and action == "create":
        config = public_json(args.config)
        if args.memory:
            from negotiator.memory import validate_memory

            client = LoopClient(args.url, os.environ.get("LAB_UPLOAD_TOKEN"))
            try:
                memory = validate_memory(client.read("memory-snapshots", args.memory))
                if memory["snapshot_id"] != args.memory:
                    raise ValueError("memory snapshot identity mismatch")
                if "memory" in config and config["memory"] != memory:
                    raise ValueError("conflicting checkpoint memory")
                config["memory"] = memory
            finally:
                if hasattr(client, "close"):
                    client.close()
        return create_checkpoint(
            args.repo,
            config=config,
            runner=args.runner,
            author=args.author,
            description=args.description,
            parent_id=args.parent,
            data=public_json(args.data),
            root=args.root / "checkpoints",
        )
    if (group == "checkpoint" and action == "show") or group == "restore":
        try:
            checkpoint = load_checkpoint(args.identity, args.root / "checkpoints")
        except FileNotFoundError:
            pass
        else:
            if group == "checkpoint":
                return checkpoint
            restored = restore_checkpoint(
                args.repo, checkpoint, args.destination, data_paths=public_json(args.data_paths)
            )
            return {"checkpoint_id": args.identity, "destination": str(restored)}
    client = LoopClient(args.url, os.environ.get("LAB_UPLOAD_TOKEN"))
    try:
        if group == "checkpoint":
            body = _checkpoint(client, args.identity, args.root)
            if action == "publish":
                body = publish_checkpoint(args.repo, body)
                _save(body, args.root / "checkpoints")
                return client.write("checkpoint", body)
            return body
        if group == "memory":
            if action == "build":
                return client.write("memory-snapshot", {
                    "arena_url": args.arena_url, "environment": args.environment,
                    "source_cases": args.source_case,
                })
            resource = "memory" if action == "graph" else "memory-snapshots"
            return client.read(resource, getattr(args, "identity", None))
        if group == "learning":
            if action == "proposals":
                return client.read("learning-proposals")
            if action == "prepare":
                from .checkpoints import _git

                proposal = client.read("learning-proposals", args.proposal)
                if proposal["status"] != "draft":
                    raise ValueError("learning proposal is not a draft")
                recommended = client.read("recommended", args.suite)
                baseline = client.read("checkpoints", recommended["checkpoint_id"])
                if _git(args.repo, "status", "--porcelain"):
                    raise ValueError("config candidate source checkout must be clean")
                if baseline.get("source_tree") != _git(args.repo, "rev-parse", "HEAD^{tree}"):
                    raise ValueError("restore the recommended source tree before preparing a config candidate")
                config = {**baseline["config"], **proposal["config_patch"]}
                if config == baseline["config"]:
                    raise ValueError("bounded proposal does not change the recommended configuration")
                return create_checkpoint(
                    args.repo, config=config, runner=baseline["runner"], author=args.author,
                    description=proposal["hypothesis"], parent_id=baseline["checkpoint_id"],
                    data=baseline["data"], root=args.root / "checkpoints",
                )
            return client.write("learning-" + action, public_json(args.body))
        if group == "suite":
            if action == "create":
                return client.write("suite", public_json(args.body) if args.body else default_suite())
            return client.read("suites", getattr(args, "identity", None))
        if group == "family":
            if action == "show":
                return client.read("families", args.identity)
            body = (
                public_json(args.body)
                if args.body
                else dict(
                    family_id=args.family_id,
                    max_sessions=args.max_sessions,
                    practice_allowance=args.practice_allowance,
                    reserve=args.reserve,
                )
            )
            return client.write("family", body)
        if group == "recommended":
            if action == "show":
                return client.read("recommended", args.identity)
            if action == "history":
                body = client.read("history")
                return {
                    "history": [event for event in body["history"] if not args.suite or event["suite_id"] == args.suite]
                }
            body = (
                public_json(args.body)
                if args.body
                else dict(suite_id=args.suite, checkpoint_id=args.checkpoint, author=args.author)
            )
            if action == "seed":
                if args.request_id:
                    body["request_id"] = args.request_id
                return client.write("seed", body)
            body.setdefault("request_id", args.request_id or uuid.uuid4().hex)
            if "generation" not in body:
                prior = next(
                    (
                        event
                        for event in client.read("history").get("history", [])
                        if event["event_id"] == body["request_id"]
                    ),
                    None,
                )
                original = prior.get("request", {}) if prior else {}
                if (
                    prior
                    and prior["action"] == "restore"
                    and all(body.get(key) == original.get(key) for key in ("suite_id", "checkpoint_id", "author"))
                ):
                    body["generation"] = original["generation"]
                else:
                    body["generation"] = client.read("recommended", body["suite_id"])["generation"]
            return client.write("restore", body)
        if group == "restore":
            checkpoint = _checkpoint(client, args.identity, args.root)
            restored = restore_checkpoint(
                args.repo, checkpoint, args.destination, data_paths=public_json(args.data_paths)
            )
            return {"checkpoint_id": args.identity, "destination": str(restored)}
        if group == "campaign":
            if action == "run":
                identity = args.campaign_id
                if identity and (
                    (campaign_dir(args.root, identity) / "state.json").exists()
                    or (not args.family and not args.candidate and not args.hypothesis)
                ):
                    return run_campaign(client, identity, args.repo, args.root, data_paths=public_json(args.data_paths))
                if not args.family or not args.candidate or not args.hypothesis or args.max_sessions is None:
                    raise ValueError("new campaign requires family, candidate, hypothesis and max-sessions")
                suite = client.read("suites", args.suite)
                if args.max_sessions < suite["max_sessions"]:
                    raise ValueError("explicit campaign ceiling is below suite sessions")
                observed_quota = arena_snapshot(suite)
                family = next(
                    (
                        entry
                        for entry in client.read("families").get("families", [])
                        if entry["family_id"] == args.family
                    ),
                    None,
                )
                if family is None:
                    client.write(
                        "family",
                        dict(
                            family_id=args.family,
                            max_sessions=args.max_sessions,
                            practice_allowance=args.practice_allowance or 0,
                            reserve=args.reserve or 0,
                        ),
                    )
                elif any(
                    value is not None and value != family[key]
                    for key, value in (("practice_allowance", args.practice_allowance), ("reserve", args.reserve))
                ):
                    raise ValueError("campaign flags conflict with immutable family protections")
                current = client.read("recommended", args.suite)
                body = dict(
                    campaign_id=identity or uuid.uuid4().hex,
                    family_id=args.family,
                    suite_id=args.suite,
                    baseline_id=current["checkpoint_id"],
                    candidate_id=args.candidate,
                    generation=current["generation"],
                    seed=args.seed,
                    author=args.author,
                    hypothesis=args.hypothesis,
                    quota=observed_quota,
                )
                campaign = client.write("campaign", body)
                return run_campaign(
                    client, campaign["campaign_id"], args.repo, args.root, data_paths=public_json(args.data_paths)
                )
            if action == "sync":
                return sync_campaign(client, args.identity, args.root)
            if action == "reconcile":
                return reconcile_attempt(client, args.identity, args.attempt, args.session)
            body = client.read("campaigns", args.identity)
            if action == "status":
                blockers = [
                    attempt["attempt_id"]
                    for attempt in body["attempts"]
                    if attempt["status"] == "started"
                    or (
                        "start" in attempt
                        and not attempt.get("reconciliation")
                        and not attempt.get("not_created")
                        and attempt.get("result", {}).get("ended") is not True
                    )
                ]
                body["blocking_attempts"] = blockers
                body["next_action"] = (
                    "Verify owned ended session and campaign reconcile explicit attempt/session IDs"
                    if blockers
                    else "Sync saved results or resume only never-started pending cells"
                    if any(a["status"] == "pending" for a in body["attempts"])
                    else None
                )
                return body
            suite = client.read("suites", body["suite_id"])
            return evaluate_campaign(
                suite,
                client.read("checkpoints", body["baseline_id"]),
                client.read("checkpoints", body["candidate_id"]),
                body["attempts"],
            )
        if group == "evidence":
            body = client.read("evidence", args.identity)
            if args.campaign and body["campaign_id"] != args.campaign:
                raise ValueError("evidence campaign mismatch")
            attempt = body["attempt"]
            if args.case and attempt["case_id"] != args.case:
                raise ValueError("evidence case mismatch")
            if args.message is not None and not args.supplier:
                raise ValueError("message selection requires supplier")
            if args.supplier:
                if args.supplier not in attempt.get("threads", {}):
                    raise ValueError("supplier evidence unavailable")
                thread = attempt["threads"][args.supplier]
                if args.message is not None:
                    messages = thread if isinstance(thread, list) else thread.get("messages", thread.get("events", []))
                    if args.message < 0 or args.message >= len(messages):
                        raise ValueError("message evidence unavailable")
                    if isinstance(thread, list):
                        thread = [messages[args.message]]
                    else:
                        key = "messages" if "messages" in thread else "events"
                        thread = {**thread, key: [messages[args.message]]}
                attempt["threads"] = {args.supplier: thread}
                body["selection"] = {"supplier": args.supplier, "message_index": args.message}
            return body
        if group == "findings":
            if action == "add":
                return client.write("finding", public_json(args.body))
            body = client.read("findings")
            if args.campaign:
                body["findings"] = [finding for finding in body["findings"] if finding["campaign_id"] == args.campaign]
            return body
        raise ValueError("unknown command")
    finally:
        if hasattr(client, "close"):
            client.close()


def handle_loop(args):
    try:
        body = dispatch(args)
        incomplete = (
            args.loop_group == "campaign" and args.loop_action in ("run", "sync") and not body.get("completion")
        )
        output = {"schema_version": 1, **body}
        if incomplete:
            output["execution_status"] = "blocked" if body.get("blocking_attempts") else "incomplete"

        if args.format == "markdown":
            from .reports import markdown_report

            print(markdown_report(output), end="")
        else:
            print(json.dumps(output, allow_nan=False))
        return 1 if incomplete else 0
    except LoopError as error:
        code, message, exit_code = error.code, str(error), 1
    except KeyboardInterrupt:
        code, message, exit_code = "interrupted", "Interrupted; inspect local state and sync before resuming", 130
    except ValueError as error:
        code, message, exit_code = "invalid_input", "Invalid input or unavailable local checkpoint dependencies", 2
        safe_messages = (
            "checkpoint locked dependencies unavailable",
            "checkpoint runtime/data preflight failed",
            "required data mapping missing",
            "required data missing or hash mismatch",
            "campaign worker is active",
            "campaign already running locally",
            "arena open-session limit reached",
            "authoritative practice quota unavailable",
            "ARENA_API_KEY required before campaign execution",
            "campaign flags conflict with immutable family protections",
            "explicit campaign ceiling is below suite sessions",
        )
        if type(error) is ValueError and str(error).startswith(safe_messages):
            message = str(error)
    except Exception:
        code, message, exit_code = "operation_failed", "Operation failed; inspect saved local campaign state", 1
    print(json.dumps({"schema_version": 1, "error": {"code": code, "message": message}}))
    return exit_code


def main(argv=None):
    load_env()
    parser = Parser(prog="negotiator lab loop")
    configure(parser)
    try:
        return handle_loop(parser.parse_args(argv))
    except ValueError:
        print(
            json.dumps(
                {"schema_version": 1, "error": {"code": "invalid_input", "message": "Invalid command arguments"}}
            )
        )
        return 2
