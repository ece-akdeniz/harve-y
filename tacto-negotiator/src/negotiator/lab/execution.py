"""Restore immutable arms and launch workers in independently locked environments."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from .checkpoints import _data_hash, restore_checkpoint
from .worker import durable_json


def worker_env():
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("NEGOTIATOR_") and key not in ("PYTHONPATH", "VIRTUAL_ENV", "ARENA_DATA", "ARENA_RELEASE")
    }
    return env


def prepare_arms(client, campaign, project, directory, data_paths, suite):
    directory = Path(directory)
    frozen = directory / "data"
    paths = {}
    manifests = {}
    for arm in ("baseline", "candidate"):
        manifest = client.read("checkpoints", campaign[arm + "_id"])
        manifests[arm] = manifest
        for name, entry in manifest["data"].items():
            if name not in ("base", "release"):
                raise ValueError("unsupported data mapping")
            target = frozen / name
            supplied = (data_paths or {}).get(name)
            if supplied is None and not target.exists():
                raise ValueError("required data mapping missing")
            source = Path(supplied) if supplied is not None else target
            if not source.exists() or _data_hash(source) != entry["sha256"]:
                raise ValueError("required data missing or hash mismatch")
            target = frozen / name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
            if _data_hash(target) != entry["sha256"]:
                raise ValueError("frozen data mismatch")
            paths[name] = str(target.resolve())
    projects = {}
    for arm, manifest in manifests.items():
        destination = directory / arm
        if destination.exists():
            restored = destination / manifest["project_path"]
            # Never silently trust a reused worktree: verify its exact tracked content.
            from .checkpoints import _verify_checkout_bytes, _verify_tree

            _verify_tree(destination, manifest)
            _verify_checkout_bytes(destination, manifest["commit"])
            for path, sha in manifest["submodules"].items():
                _verify_checkout_bytes(destination / path, sha)
        else:
            restored = restore_checkpoint(project, manifest, destination, data_paths=paths)
        result = subprocess.run(
            ["uv", "sync", "--locked", "--offline"], cwd=restored, env=worker_env(), capture_output=True
        )
        if result.returncode:
            raise ValueError("checkpoint locked dependencies unavailable; no sessions started")
        env = worker_env()
        env["PYTHONPATH"] = str(restored / "src")
        request = dict(
            checkpoint=manifest,
            project=str(restored),
            attempt_root=str(directory / "preflight" / arm),
            data_paths=paths,
            arena_url=suite["arena_url"],
            environment=suite["environment"],
        )
        preflight = subprocess.run(
            ["uv", "run", "--locked", "--offline", "--no-sync", "python", "-m", "negotiator.lab.worker", "--preflight"],
            cwd=restored,
            env=env,
            input=json.dumps(request),
            capture_output=True,
            text=True,
        )
        if preflight.returncode:
            raise ValueError("checkpoint runtime/data preflight failed; no sessions started")
        projects[arm] = restored
    return manifests, projects, paths


def launch_worker(request, *, lock_fd=None):
    root = Path(request["attempt_root"])
    root.mkdir(parents=True, exist_ok=True)
    durable_json(root / "request.json", request)
    env = worker_env()
    env["PYTHONPATH"] = str(Path(request["project"]) / "src")

    with (root / "worker.log").open("w") as log:
        process = subprocess.Popen(
            ["uv", "run", "--locked", "--offline", "--no-sync", "python", "-m", "negotiator.lab.worker"],
            cwd=request["project"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=log,
            stderr=log,
            text=True,
            pass_fds=() if lock_fd is None else (lock_fd,),
        )
        try:
            process.communicate(json.dumps(request))
        except KeyboardInterrupt:
            # Keep the active negotiation running to its own durable finish before stopping starts.
            process.wait()
            raise
    path = root / "result.json"
    if path.is_file():
        result = json.loads(path.read_text())
        if result.get("final") is True:
            return result
    progress = root / "progress.json"
    known = json.loads(progress.read_text()) if progress.is_file() else {}

    return dict(
        attempt_id=request["attempt"]["attempt_id"],
        checkpoint_id=request["checkpoint"]["checkpoint_id"],
        session_id=known.get("session_id"),
        status="ambiguous",
        final=True,
        result={},
        threads={},
        score=None,
        timeouts=None,
        elapsed_s=None,
    )
