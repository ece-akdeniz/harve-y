"""Baseline vs candidate on the same cases, N repeats each, fixed and recorded configs.

An arm is a git ref (or WORKTREE = the current files) plus env overrides and extra CLI args.
Each run is `uv run --locked negotiator play <case> [args]` (or `run --set ...`) in the
foreground with its own NEGOTIATOR_LOG_DIR; scores come from negotiator.report.summarise.

    # local arena-sim (started on --sim-url if not up), working tree vs HEAD
    uv run --locked python tools/compare.py --cases S01 S02 S03 --repeats 2
    # sandbox D01/D02 (hosted, no practice quota), explicit arms and pass-through args
    uv run --locked python tools/compare.py --mode sandbox --cases D01 D02 --baseline 42c7659 \\
        --candidate WORKTREE --candidate-env NEGOTIATOR_MOVE_BUDGET_S=20 -- --runner async
    # hosted practice: only with --practice and a session cap; keeps the 46-session reserve
    uv run --locked python tools/compare.py --mode practice --practice --budget 8 --cases P01 P02

Arm order is interleaved per case and repeat (seeded). Output: experiments/runs/compare/<stamp>/
(summary.json, per-run stdout/stderr and traces) and a markdown section appended to experiments/LOG.md.
"""

import argparse
import hashlib
import json
import os
import shlex
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from negotiator.report import summarise  # noqa: E402

RESERVE = 46
HOSTED = "https://arena.tacto.ai"
WORKTREE = "WORKTREE"


def git(*args, cwd=ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.is_file() else None


def case_id(c: str) -> str:
    return c if c.startswith("case:") else f"case:{c}"


def parse_env(pairs) -> dict:
    out = {}
    for p in pairs or []:
        k, sep, v = p.partition("=")
        if not sep:
            raise SystemExit(f"bad env override {p!r}: use KEY=VALUE")
        out[k] = v
    return out


class Arm:
    def __init__(self, name, ref, env, args):
        self.name, self.ref, self.env, self.args = name, ref, env, args
        self.dir, self.worktree = ROOT, None

    def prepare(self, data_dir: Path):
        """Resolve the ref; for a commit, check it out in a temporary worktree with data linked in."""
        head = git("rev-parse", "HEAD")
        if self.ref == WORKTREE:
            self.commit = head
            diff = subprocess.run(["git", "diff", "HEAD", "--", "."], cwd=ROOT, capture_output=True).stdout
            untracked = git("ls-files", "--others", "--exclude-standard", "--", ".").splitlines()
            self.dirty = bool(diff or untracked)
            h = hashlib.sha256(diff)
            for rel in untracked:
                h.update(rel.encode() + b"\0" + (ROOT / rel).read_bytes())
            self.diff_hash = h.hexdigest()[:12] if self.dirty else None
            self.untracked = untracked
            return
        self.commit, self.dirty, self.diff_hash, self.untracked = git("rev-parse", self.ref), False, None, []
        prefix = git("rev-parse", "--show-prefix")
        self.worktree = Path(tempfile.mkdtemp(prefix=f"tacto-cmp-{self.commit[:8]}-"))
        git("worktree", "add", "--detach", str(self.worktree), self.commit)
        self.dir = self.worktree / prefix
        for rel in ("data", "experiments/dossiers.json"):
            src, dst = ROOT / rel, self.dir / rel
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.symlink_to(src)

    def cleanup(self):
        if self.worktree:
            subprocess.run(["git", "worktree", "remove", "--force", str(self.worktree)], cwd=ROOT, capture_output=True)

    def record(self) -> dict:
        return {
            "ref": self.ref,
            "commit": self.commit,
            "dirty": self.dirty,
            "diff_hash": self.diff_hash,
            "untracked": self.untracked,
            "env": self.env,
            "args": self.args,
        }


def sim_up(url) -> bool:
    u = urlparse(url)
    try:
        with socket.create_connection((u.hostname, u.port or 80), timeout=1):
            return True
    except OSError:
        return False


def start_sim(url, data_dir: Path, out_dir: Path):
    port = str(urlparse(url).port or 8030)
    log = (out_dir / "sim.log").open("w")
    proc = subprocess.Popen(
        ["uv", "run", "--locked", "arena-sim", "serve", "--data", str(data_dir), "--port", port],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    for _ in range(60):
        if sim_up(url):
            return proc
        time.sleep(0.5)
    stop(proc)
    raise SystemExit(f"arena-sim did not start on {url}; see {out_dir / 'sim.log'}")


def stop(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait(timeout=10)


def sim_key(url) -> str:
    from arena_kit.client import ArenaClient

    reply = ArenaClient(base_url=url, api_key="none").register(f"yagent-ev-{uuid.uuid4().hex[:6]}", "sim")
    return reply["api_key"]


def practice_left(env) -> dict:
    from arena_kit.client import ArenaClient

    return ArenaClient(base_url=env["ARENA_URL"], api_key=env.get("ARENA_API_KEY")).me().get("practice") or {}


def run_one(arm: Arm, argv, env, run_dir: Path, timeout) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    full_env = {**env, **arm.env, "NEGOTIATOR_LOG_DIR": str(run_dir)}
    cmd = ["uv", "run", "--locked", "negotiator", *argv, *arm.args]
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=arm.dir, env=full_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        out, err = proc.communicate()
    (run_dir / "stdout.txt").write_text(out or "")
    (run_dir / "stderr.txt").write_text(err or "")
    summary = summarise(run_dir) if list(run_dir.rglob("trace.jsonl")) else {"cases": {}, "aggregate": {}}
    return {
        "cmd": shlex.join(cmd),
        "cwd": str(arm.dir),
        "run_dir": str(run_dir.relative_to(ROOT)) if run_dir.is_relative_to(ROOT) else str(run_dir),
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "elapsed_s": round(time.monotonic() - started, 1),
        "cases": {k: {f: c.get(f) for f in ("score", "deal", "error", "timeouts", "session", "must_haves_ok")}
                  for k, c in summary["cases"].items()},
        "stderr_tail": (err or "")[-400:],
    }


def aggregate(runs, arms, cases) -> dict:
    out = {}
    for arm in arms:
        mine = [r for r in runs if r["arm"] == arm]
        per_case, failures, timeouts = {}, [], 0
        for c in cases:
            scores = []
            for r in mine:
                if r["case"] not in (c, "*"):
                    continue
                row = r["cases"].get(c)
                if row and isinstance(row.get("score"), int | float):
                    scores.append(row["score"])
                else:
                    failures.append({"case": c, "repeat": r["repeat"], "run_dir": r["run_dir"],
                                     "why": (row or {}).get("error") or f"rc={r['returncode']} no score"})
                timeouts += (row or {}).get("timeouts") or 0
            per_case[c] = scores
        timeouts += sum(1 for r in mine if r["timed_out"])
        means = {c: statistics.mean(s) for c, s in per_case.items() if s}
        allv = [v for s in per_case.values() for v in s]
        worst = min(means, key=means.get) if means else None
        out[arm] = {
            "scores": per_case,
            "case_means": means,
            "mean": statistics.mean(allv) if allv else None,
            "mean_of_case_means": statistics.mean(means.values()) if means else None,
            "worst_case": worst,
            "worst_case_mean": means.get(worst),
            "min_run": min(allv) if allv else None,
            "failures": failures,
            "timeouts": timeouts,
            "runs": len(mine),
        }
    return out


def pct(x) -> str:
    return "-" if x is None else f"{100 * x:.1f}"


def markdown(meta, agg) -> str:
    b, c = agg["baseline"], agg["candidate"]
    kind = {"sim": "MEASURED LOCAL SIM", "sandbox": "MEASURED HOSTED SANDBOX", "practice": "MEASURED HOSTED PRACTICE"}
    lines = [
        f"## {meta['started'][:16].replace('T', ' ')} - compare {meta['name']} ({kind[meta['mode']]})",
        "",
    ]
    for arm in ("baseline", "candidate"):
        a = meta["arms"][arm]
        lines.append(
            f"- {arm.title()}: `{a['ref']}` @ {a['commit'][:8]}"
            + (f" dirty diff {a['diff_hash']}" if a["dirty"] else "")
            + (f", env {a['env']}" if a["env"] else "")
            + (f", args `{' '.join(a['args'])}`" if a["args"] else "")
        )
    lines += [
        f"- Cases × repeats: {', '.join(meta['cases'])} × {meta['repeats']} (`{meta['cmd']}`), arm order interleaved,"
        f" seed {meta['seed']}; arena {meta['arena']}; data {meta['data_hash']}, uv.lock {meta['lock_hash']}",
        "",
        "| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |",
        "|---|---|---:|---|---:|---:|",
    ]
    for case in meta["cases"]:
        bs, cs = b["scores"].get(case, []), c["scores"].get(case, [])
        bm, cm = b["case_means"].get(case), c["case_means"].get(case)
        delta = f"{100 * (cm - bm):+.1f}" if bm is not None and cm is not None else "-"
        lines.append(f"| {case} | {' '.join(pct(x) for x in bs) or '-'} | {pct(bm)} |"
                     f" {' '.join(pct(x) for x in cs) or '-'} | {pct(cm)} | {delta} |")
    for arm, a in (("Baseline", b), ("Candidate", c)):
        lines.append(f"- {arm}: mean {pct(a['mean'])} over {sum(len(s) for s in a['scores'].values())} scored runs,"
                     f" worst case {a['worst_case'] or '-'} {pct(a['worst_case_mean'])}, min run {pct(a['min_run'])},"
                     f" failures {len(a['failures'])}, timeouts {a['timeouts']}")
    if meta.get("quota"):
        lines.append(f"- Practice quota before/after: {meta['quota']}")
    lines += [f"- Raw: `{meta['out_dir']}/summary.json`", "- Decision: (fill in)", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", nargs="+", required=True, help="e.g. S01 S02 or case:D01")
    ap.add_argument("--repeats", "-n", type=int, default=2)
    ap.add_argument("--mode", choices=["sim", "sandbox", "practice"], default="sim")
    ap.add_argument("--practice", action="store_true", help="required for --mode practice")
    ap.add_argument("--budget", type=int, help="max practice sessions this comparison may open")
    ap.add_argument("--baseline", default="HEAD", help="git ref or WORKTREE (default HEAD)")
    ap.add_argument("--candidate", default=WORKTREE, help="git ref or WORKTREE (default: current files)")
    ap.add_argument("--baseline-env", nargs="*", default=[], metavar="K=V")
    ap.add_argument("--candidate-env", nargs="*", default=[], metavar="K=V")
    ap.add_argument("--baseline-args", default="", help="extra negotiator args for the baseline only")
    ap.add_argument("--candidate-args", default="", help="extra negotiator args for the candidate only")
    ap.add_argument("--cmd", choices=["play", "run"], default="play", help="play per case, or run the whole set")
    ap.add_argument("--timeout", type=float, default=900, help="seconds per subprocess")
    ap.add_argument("--sim-url", default="http://127.0.0.1:8030")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--name", default="", help="label for the LOG.md section")
    ap.add_argument("--no-log", action="store_true", help="do not append to experiments/LOG.md")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    ap.add_argument("extra", nargs=argparse.REMAINDER, help="after --: args passed to both arms")
    args = ap.parse_args(argv)
    extra = args.extra[1:] if args.extra[:1] == ["--"] else args.extra
    cases = [case_id(c) for c in args.cases]

    if args.mode == "practice" and not (args.practice and args.budget):
        ap.error("--mode practice needs --practice and --budget N")
    if args.practice and args.mode != "practice":
        ap.error("--practice only with --mode practice")

    from arena_kit.cli import load_env

    os.chdir(ROOT)
    load_env()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "experiments/runs/compare" / f"{stamp}-{args.mode}{'-' + args.name if args.name else ''}"
    data_dir = next(
        (p.resolve() for p in (Path(os.environ.get("ARENA_DATA", "")), ROOT / "data/package")
         if str(p) and (p / "world.sqlite").is_file()),
        ROOT / "data/package",
    )
    env = {**os.environ, "ARENA_DATA": str(data_dir)}
    set_ = {"sim": "practice", "sandbox": "sandbox", "practice": "practice"}[args.mode]
    per_repeat = 2 * (len(cases) if args.cmd == "play" else 0)

    sim_proc, quota = None, {}
    if args.mode == "sim":
        env["ARENA_URL"] = args.sim_url
    else:
        env["ARENA_URL"] = os.environ.get("ARENA_URL") or HOSTED
        if "127.0.0.1" in env["ARENA_URL"] or "localhost" in env["ARENA_URL"]:
            env["ARENA_URL"] = HOSTED
    if args.cmd == "run" and args.mode == "practice":
        from arena_kit.client import ArenaClient
        from arena_kit.play import hosted

        n_set = len(hosted(ArenaClient(base_url=env["ARENA_URL"]).cases(set_)))
        per_repeat = 2 * n_set
    planned = per_repeat * args.repeats
    print(f"plan: {len(cases)} cases × {args.repeats} repeats × 2 arms, mode {args.mode}, arena {env['ARENA_URL']}")
    if args.mode == "practice":
        before = practice_left(env)
        quota["before"] = before
        left = before.get("left")
        print(f"practice: {planned} sessions planned, budget {args.budget}, left {left}, reserve {RESERVE}")
        if planned > args.budget:
            raise SystemExit(f"refusing: {planned} sessions planned > --budget {args.budget}")
        if left is None or left - planned < RESERVE:
            raise SystemExit(f"refusing: would leave {None if left is None else left - planned} < reserve {RESERVE}")
    if args.dry_run:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    arms = {
        "baseline": Arm("baseline", args.baseline, parse_env(args.baseline_env), shlex.split(args.baseline_args)),
        "candidate": Arm("candidate", args.candidate, parse_env(args.candidate_env), shlex.split(args.candidate_args)),
    }
    for a in arms.values():
        a.args = a.args + extra
    runs = []
    try:
        for a in arms.values():
            a.prepare(data_dir)
        if args.mode == "sim":
            if not sim_up(args.sim_url):
                sim_proc = start_sim(args.sim_url, data_dir, out_dir)
            env["ARENA_API_KEY"] = sim_key(args.sim_url)
        from negotiator.lab.ordering import campaign_order
        cells = campaign_order(cases if args.cmd == "play" else ["*"], args.repeats, args.seed, tuple(arms))
        jobs = [(cell["repeat"], cell["case_id"], cell["arm"]) for cell in cells]
        for i, (rep, case, name) in enumerate(jobs, 1):
            argv_ = ["play", case] if case != "*" else ["run", "--set", set_]
            tag = case.replace("case:", "") if case != "*" else set_
            rd = out_dir / name / f"{tag}-r{rep}"
            r = run_one(arms[name], argv_, env, rd, args.timeout)
            r.update(arm=name, case=case, repeat=rep)
            runs.append(r)
            scores = {k: v.get("score") for k, v in r["cases"].items()}
            print(f"[{i}/{len(jobs)}] {name:9} {tag} r{rep}: rc={r['returncode']}"
                  f"{' TIMEOUT' if r['timed_out'] else ''} {r['elapsed_s']}s scores={scores}", flush=True)
    finally:
        for a in arms.values():
            a.cleanup()
        if sim_proc:
            stop(sim_proc)

    if args.mode == "practice":
        quota["after"] = practice_left(env)
    agg = aggregate(runs, list(arms), cases)
    meta = {
        "name": args.name or f"{args.baseline}-vs-{args.candidate}",
        "started": datetime.strptime(stamp, "%Y%m%d-%H%M%S").isoformat(),
        "mode": args.mode,
        "arena": env["ARENA_URL"],
        "cmd": " ".join(["negotiator", args.cmd, *(["<case>"] if args.cmd == "play" else ["--set", set_])]),
        "cases": cases,
        "repeats": args.repeats,
        "seed": args.seed,
        "timeout_s": args.timeout,
        "data_hash": sha256(data_dir / "world.sqlite"),
        "lock_hash": sha256(ROOT / "uv.lock"),
        "python": sys.version.split()[0],
        "arms": {k: a.record() for k, a in arms.items()},
        "quota": quota,
        "out_dir": str(out_dir.relative_to(ROOT)),
    }
    (out_dir / "summary.json").write_text(json.dumps({"meta": meta, "aggregate": agg, "runs": runs}, indent=2))
    md = markdown(meta, agg)
    (out_dir / "summary.md").write_text(md)
    print("\n" + md)
    if not args.no_log:
        with (ROOT / "experiments/LOG.md").open("a", encoding="utf-8") as f:
            f.write("\n" + md)
        print("appended to experiments/LOG.md")
    return 0 if not any(a["failures"] for a in agg.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
