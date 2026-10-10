"""Host setup, experiment execution, recovery sync and read-only history import."""

import argparse
import getpass
import json
import os
import secrets
import sys
from pathlib import Path

from arena_kit.cli import load_env
from arena_kit.client import ArenaClient
from dotenv import dotenv_values

from .history import import_history
from .publish import Publisher, sync
from .runner import agent_factory, capture_provenance, plan_run, run_experiment
from .server import DashboardServer
from .store import Store


def _publisher() -> Publisher | None:
    url, token = os.environ.get("LAB_URL"), os.environ.get("LAB_UPLOAD_TOKEN")
    if bool(url) != bool(token):
        raise ValueError("set both LAB_URL and LAB_UPLOAD_TOKEN, or neither for local buffering")
    return Publisher(url, token) if url and token else None


def _author(value):
    return value or os.environ.get("LAB_AUTHOR") or getpass.getuser()


def _init(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(f"LAB_PASSWORD={secrets.token_urlsafe(24)}\nLAB_UPLOAD_TOKEN={secrets.token_urlsafe(32)}\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(path)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def parser():
    ap = argparse.ArgumentParser(prog="negotiator lab", description="Shared experiment dashboard tooling")
    sub = ap.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="generate host secrets without printing values")
    init.add_argument("--secrets-file", type=Path, default=Path(".lab-secrets.env"))
    serve = sub.add_parser("serve", help="serve the authenticated dashboard")
    serve.add_argument("--host", default=os.environ.get("LAB_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=os.environ.get("PORT", os.environ.get("LAB_PORT", "8000")))
    serve.add_argument("--db", type=Path, default=os.environ.get("LAB_DB", "experiments/dashboard.sqlite3"))
    serve.add_argument("--secrets-file", type=Path, default=os.environ.get("LAB_SECRETS_FILE", ".lab-secrets.env"))
    serve.add_argument("--secure-cookies", action=argparse.BooleanOptionalAction, default=None,
                       help="require HTTPS for browser authentication cookies")
    run = sub.add_parser("run", help="run an explicit serial case plan")
    run.add_argument("--name", required=True)
    run.add_argument("--hypothesis", required=True)
    run.add_argument("--author")
    run.add_argument("--agent", default="package")
    run.add_argument("--config", default="{}", help="JSON object passed as factory keyword arguments")
    run.add_argument("--cases", nargs="+", required=True)
    run.add_argument("--repetitions", type=int, required=True)
    run.add_argument("--max-sessions", type=int, required=True)
    run.add_argument("--environment", choices=["simulator", "sandbox", "practice"], required=True)
    run.add_argument(
        "--release",
        type=Path,
        default=Path(os.environ["ARENA_RELEASE"]) if os.environ.get("ARENA_RELEASE") else None,
        help="overlay directory included in the combined data fingerprint",
    )
    run.add_argument("--baseline", dest="baseline_id")
    run.add_argument("--allow-dirty", action="store_true")
    run.add_argument("--root", type=Path, default=Path("experiments/runs"))
    run.add_argument("--repo", type=Path, default=Path.cwd())
    run.add_argument("--data", type=Path, default=Path(os.environ.get("ARENA_DATA", "data/package")))
    recover = sub.add_parser("sync", help="retry saved snapshot uploads")
    recover.add_argument("--root", type=Path, default=Path("experiments/runs"))
    history = sub.add_parser("import", help="read only owned practice/sandbox session history")
    history.add_argument("--environment", choices=["practice", "sandbox"], required=True)
    history.add_argument("--root", type=Path, default=Path("experiments/runs"))
    history.add_argument("--author")
    feedback = sub.add_parser("feedback", help="audit saved runs without changing scores or policies")
    feedback.add_argument("--db", type=Path, default=Path("experiments/dashboard.sqlite3"))
    feedback.add_argument("--out", type=Path, default=Path("experiments/feedback.json"))
    feedback.add_argument("--data", type=Path, help="public package for recomputing historical offer validity")
    graph = sub.add_parser("graph-export", help="export a versioned evaluation graph for the shared lab")
    graph.add_argument("--db", type=Path, default=Path("experiments/dashboard.sqlite3"))
    graph.add_argument("--out", type=Path, default=Path("experiments/knowledge-graph.json"))
    graph.add_argument("--data", type=Path, help="optional current public data package for a separate graph layer")
    history.add_argument(
        "--db",
        type=Path,
        default=Path("experiments/dashboard.sqlite3"),
        help="consult existing host runs and save imports directly when this DB exists",
    )
    from .loop_cli import add_loop_commands, configure

    add_loop_commands(sub)
    configure(groups=sub)
    return ap


def parse_args(argv):
    args = parser().parse_args(argv)
    if args.command == "serve" and args.secure_cookies is None:
        args.secure_cookies = _env_flag("LAB_SECURE_COOKIES")
    return args


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "loop":
        from .loop_cli import main as loop_main

        return loop_main(argv[1:])
    if argv and argv[0] in (
        "checkpoint",
        "suite",
        "family",
        "recommended",
        "campaign",
        "evidence",
        "findings",
        "memory",
        "restore",
    ):
        from .loop_cli import main as loop_main

        return loop_main(argv)
    load_env()
    args = parse_args(argv)
    try:
        if args.command == "graph-export":
            from .feedback import review_store
            from .knowledge import export_graph

            if not args.db.is_file():
                raise ValueError("graph database does not exist")
            store = Store(args.db)
            package = None
            if args.data:
                from negotiator.dossiers import load_package

                package = load_package(args.data)
            try:
                graph = export_graph(store.all(), review_store(store)["reports"], package=package)
            finally:
                if package and package.db:
                    package.db.close()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(graph, indent=2, allow_nan=False))
            print(json.dumps({"nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
                              "graph": str(args.out), "live_lessons_enabled": False}))
            return 0
        if args.command == "feedback":
            from .feedback import review_store
            from .runner import fingerprint_data

            if not args.db.is_file():
                raise ValueError("feedback database does not exist")
            package = None
            if args.data:
                from negotiator.dossiers import load_package

                package = load_package(args.data)
            try:
                data_hash = fingerprint_data(package.root) if package else None
                if package and package.release:
                    import hashlib

                    overlay_hash = fingerprint_data(package.release)
                    data_hash = hashlib.sha256(f"base:{data_hash}\nrelease:{overlay_hash}".encode()).hexdigest()
                result = review_store(Store(args.db), package.cases if package else None, data_hash, package)
            finally:
                if package and package.db:
                    package.db.close()
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2))
            print(json.dumps({"runs": result["runs"], "report": str(args.out), "policy_changed": False}))
            return 0
        if args.command == "init":
            _init(args.secrets_file)
            return 0
        if args.command == "serve":
            if os.name == "posix" and args.secrets_file.is_file() and args.secrets_file.stat().st_mode & 0o077:
                raise ValueError("host secret file must have mode 0600")
            values = dotenv_values(args.secrets_file)
            password = os.environ.get("LAB_PASSWORD") or values.get("LAB_PASSWORD")
            token = os.environ.get("LAB_UPLOAD_TOKEN") or values.get("LAB_UPLOAD_TOKEN")
            with DashboardServer(
                (args.host, args.port),
                Store(args.db),
                password=password,
                upload_token=token,
                secure_cookie=args.secure_cookies,
            ) as server:
                print(f"Dashboard: http://{args.host}:{server.server_port}", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
            return 0
        if args.command == "sync":
            url, token = os.environ.get("LAB_URL"), os.environ.get("LAB_UPLOAD_TOKEN")
            if not url or not token:
                raise ValueError("sync requires LAB_URL and LAB_UPLOAD_TOKEN")
            report = sync(args.root, url, token)
            print(json.dumps(report))
            return 0 if report["failed"] == 0 else 1
        arena_url = os.environ.get("ARENA_URL", "https://arena.tacto.ai")
        if args.command == "run":
            config = json.loads(args.config)
            if not isinstance(config, dict):
                raise ValueError("agent config must be a JSON object")
            provenance, patch = capture_provenance(
                args.repo, data_dir=args.data, release_dir=args.release, allow_dirty=args.allow_dirty
            )
            run = plan_run(
                name=args.name,
                author=_author(args.author),
                hypothesis=args.hypothesis,
                agent=args.agent,
                config=config,
                cases=args.cases,
                repetitions=args.repetitions,
                max_sessions=args.max_sessions,
                environment=args.environment,
                arena_url=arena_url,
                provenance=provenance,
                baseline_id=args.baseline_id,
            )
            factory = agent_factory(args.agent, config)
            publisher = _publisher()
            from .transport import JournaledArena

            client = JournaledArena(args.root / run.run_id / "serial.jsonl", base_url=arena_url, rate=2)
            try:
                final = run_experiment(run, args.root, client, factory, publisher=publisher, patch=patch)
            finally:
                client.http.close()
            print(f"{final.status}: {args.root / final.run_id / 'run.json'}")
            if final.quota:
                print(f"practice sessions left: {final.quota.left}/{final.quota.limit}")
            return 0 if final.status == "completed" else 130 if final.status == "interrupted" else 1
        client = ArenaClient(base_url=arena_url, rate=1)
        try:
            report = import_history(
                client,
                args.root,
                environment=args.environment,
                arena_url=arena_url,
                author=_author(args.author),
                store=Store(args.db) if args.db.is_file() else None,
                publisher=_publisher(),
            )
        finally:
            client.http.close()
        print(json.dumps(report))
        return 0 if report["failed"] == 0 else 1
    except FileExistsError:
        print("lab: secret file already exists", file=sys.stderr)
    except ValueError as error:
        # Only our validation messages are printed; Pydantic and JSON errors echo input values.
        message = (
            str(error) if type(error) is ValueError and error.__class__.__module__ == "builtins" else "invalid input"
        )
        allowed = (
            "working tree is dirty",
            "set both LAB_URL",
            "sync requires",
            "host secret file",
            "agent config must",
            "case/repetition plan",
            "configuration contains",
            "agent must",
            "dashboard password",
            "simulator",
        )
        print("lab: " + (message if message.startswith(allowed) else "invalid input"), file=sys.stderr)
    except KeyboardInterrupt:
        return 130
    except Exception:
        print("lab: operation failed; check configuration and saved local snapshots", file=sys.stderr)
    return 2
