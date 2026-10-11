"""Byte-identity check for `negotiator.prewarm`: replay saved transcripts with and without pre-warming.

    uv run --locked python tools/prewarm_replay.py --cases case:P05,case:P18,case:P01 \\
        --config configs/score-push-v3-run.json [--runs DIR] [--max-runs N] [--json OUT]

Every saved lab/hosted attempt of the chosen cases (`run.json` under --runs, as tools/replay_decisions.py
reads them) is replayed twice, each in a FRESH interpreter so that module caches cannot leak between
the two: `lazy` (no prewarm call at all: the data package, dossiers and evidence context load on the
first `decide`, as before) and `prewarm` (`prewarm()` once, then `prewarm_case(agent, case)` before the
first decision, as the runners do). Each buyer message of a transcript is a decision point; the agent
sees the saved history with its own replayed moves substituted and `decide(case, threads)` is recorded
in full (supplier, action, term sheets, body, refs). The two runs' canonical JSON must be byte-identical.
Never contacts the arena.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_RUNS = Path("/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/experiments/runs")


def load_config(path) -> dict:
    cfg = json.loads(Path(path).read_text())
    if "policy_config" not in cfg:
        cfg = {"policy_config": cfg}
    kwargs = {k: v for k, v in cfg.items() if k not in ("name", "notes", "hypothesis", "trace_dir")}
    kwargs.setdefault("estimates", {})
    kwargs.setdefault("meso", False)
    kwargs["model_assist"] = False
    kwargs["policy_config"] = dict(kwargs["policy_config"])
    kwargs["policy_config"].pop("package_advice_types", None)  # LLM; offline replay
    return kwargs


def iter_attempts(runs_dir: Path, cases: set[str], max_runs=None):
    seen_sessions, per_case = set(), {}
    for path in sorted(runs_dir.rglob("run.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        for attempt in data.get("attempts") or []:
            cid = attempt.get("case_id")
            if cid not in cases or not attempt.get("threads"):
                continue
            session = attempt.get("session_id")
            if session and session in seen_sessions:
                continue
            if max_runs is not None and per_case.get(cid, 0) >= max_runs:
                continue
            seen_sessions.add(session)
            per_case[cid] = per_case.get(cid, 0) + 1
            yield str(path.relative_to(runs_dir)), attempt


def decision_points(threads):
    out = []
    for j in range(max((len(m) for m in threads.values()), default=0)):
        for sid in sorted(threads):
            if j < len(threads[sid]) and threads[sid][j].get("from") == "buyer":
                out.append((j, sid))
    return out


def replay(case: dict, saved: dict[str, list[dict]], agent) -> list[dict]:
    ours: dict[str, dict[int, dict]] = {sid: {} for sid in saved}
    rounds, done = [], set()
    for n, (j, sid) in enumerate(decision_points(saved), 1):
        history = {}
        for s, msgs in saved.items():
            cut = j + 1 if (j, s) in done else j
            history[s] = [ours[s].get(i, m) if m.get("from") == "buyer" else m for i, m in enumerate(msgs[:cut])]
        done.add((j, sid))
        try:
            move = agent.decide(case, history)
        except Exception as exc:
            rounds.append({"round": n, "index": j, "saved_supplier": sid, "error": repr(exc)[:300]})
            continue
        chosen, message = move.get("supplier_id"), move.get("message") or {}
        if chosen == sid:
            ours[sid][j] = {"from": "buyer", **message}
        rounds.append({"round": n, "index": j, "saved_supplier": sid, "supplier": chosen, "message": message})
    return rounds


def run_mode(mode: str, config: str, case_ids: list[str], runs_dir: Path, cases_file: Path, max_runs) -> list[dict]:
    """One replay pass in this interpreter (`mode`: lazy | prewarm)."""
    from negotiator.agent import configured_agent

    cases = {c["case_id"]: c for c in json.loads(cases_file.read_text())}
    kwargs = load_config(config)
    out = []
    if mode == "prewarm":
        from negotiator.prewarm import prewarm

        prewarm(cases=[cases[c] for c in case_ids if c in cases])
    for run, attempt in iter_attempts(runs_dir, set(case_ids), max_runs):
        case = cases[attempt["case_id"]]
        saved = {sid: list(t.get("messages") or []) if isinstance(t, dict) else list(t or [])
                 for sid, t in attempt["threads"].items()}
        agent = configured_agent(**kwargs)
        agent.conditional_exchange = any("conditional exchange" in (m.get("body") or "").lower()
                                         for msgs in saved.values() for m in msgs if m.get("from") == "buyer")
        if mode == "prewarm":
            from negotiator.prewarm import prewarm_case

            prewarm_case(agent, {**case, "hosted": True, "wave": 1, "seconds_left": 480, "open": True})
        out.append({"case_id": case["case_id"], "run": run, "attempt_id": attempt.get("attempt_id"),
                    "rounds": replay(case, saved, agent)})
    return out


def canonical(results) -> bytes:
    return json.dumps(results, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cases", required=True, help="comma-separated case IDs")
    ap.add_argument("--config", required=True, help="policy or *-run.json config")
    ap.add_argument("--runs", default=str(DEFAULT_RUNS))
    ap.add_argument("--cases-file", default=str(ROOT / "tests/fixtures/practice_cases.json"))
    ap.add_argument("--max-runs", type=int, default=3, help="saved attempts per case (default 3)")
    ap.add_argument("--json", help="write both modes' decisions here")
    ap.add_argument("--mode", choices=("lazy", "prewarm"), help="(internal) one pass; print canonical JSON")
    args = ap.parse_args(argv)
    case_ids = [c.strip() for c in args.cases.split(",") if c.strip()]
    if args.mode:
        results = run_mode(args.mode, args.config, case_ids, Path(args.runs), Path(args.cases_file), args.max_runs)
        sys.stdout.buffer.write(canonical(results))
        return 0
    outputs = {}
    for mode in ("lazy", "prewarm"):
        cmd = [sys.executable, __file__, "--mode", mode, "--cases", args.cases, "--config", args.config,
               "--runs", args.runs, "--cases-file", args.cases_file, "--max-runs", str(args.max_runs)]
        proc = subprocess.run(cmd, capture_output=True, check=False, cwd=ROOT)
        if proc.returncode != 0:
            print(proc.stderr.decode(errors="replace"))
            return 1
        outputs[mode] = proc.stdout
    lazy, warm = outputs["lazy"], outputs["prewarm"]
    results = json.loads(lazy)
    n_rounds = sum(len(r["rounds"]) for r in results)
    errors = sum(1 for r in results for x in r["rounds"] if x.get("error"))
    print(f"replayed {len(results)} saved transcripts, {n_rounds} decisions ({errors} errored), cases "
          f"{sorted({r['case_id'] for r in results})}")
    print(f"lazy    sha256 {hashlib.sha256(lazy).hexdigest()}  ({len(lazy)} bytes)")
    print(f"prewarm sha256 {hashlib.sha256(warm).hexdigest()}  ({len(warm)} bytes)")
    identical = lazy == warm
    print("IDENTICAL" if identical else "DIFFERENT")
    if not identical:
        a, b = json.loads(lazy), json.loads(warm)
        for ra, rb in zip(a, b, strict=False):
            for xa, xb in zip(ra["rounds"], rb["rounds"], strict=False):
                if xa != xb:
                    print(f"first difference: {ra['case_id']} {ra['run']} round {xa['round']}")
                    print(" lazy   ", json.dumps(xa, sort_keys=True)[:400])
                    print(" prewarm", json.dumps(xb, sort_keys=True)[:400])
                    break
            else:
                continue
            break
    if args.json:
        Path(args.json).write_text(json.dumps({"lazy": json.loads(lazy), "prewarm": json.loads(warm),
                                               "identical": identical}, indent=1))
        print(f"written: {args.json}")
    return 0 if identical else 2


if __name__ == "__main__":
    sys.exit(main())
