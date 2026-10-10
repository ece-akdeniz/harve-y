"""negotiator play <case> | run --set practice|sandbox|final | prep | report <run_dir>"""

import argparse
import json
import logging
import os
import statistics
import sys
import time
from pathlib import Path

from arena_kit.cli import load_env, summary
from arena_kit.client import ArenaClient, ArenaError
from arena_kit.play import RemoteTable, hosted

from .agent import PackageAgent
from .play import play_all, play_case, play_waves, run_config
from .runner import run_async, runtime_config
from .trace import Tracer


def _run_dir() -> Path:
    root = Path(os.environ.get("NEGOTIATOR_LOG_DIR", "experiments/runs"))
    return root / time.strftime("%Y%m%d-%H%M%S")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "lab":
        from .lab.cli import main as lab_main

        return lab_main(argv[1:])
    if argv and argv[0] == "loop":
        from .lab.loop_cli import main as loop_main

        return loop_main(argv[1:])
    load_env()
    ap = argparse.ArgumentParser(prog="negotiator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep", help="build dossiers and the claim bank from the data package")
    p = sub.add_parser("play", help="play one case")
    p.add_argument("case_id")
    p.add_argument("-v", "--verbose", action="store_true")
    r = sub.add_parser("run", help="play a set; --set final runs the Live Final waves")
    r.add_argument("--set", dest="set_", choices=["practice", "sandbox", "final"], required=True)
    r.add_argument("--parallel", type=int, default=8)
    r.add_argument("--waves", type=int, default=5)
    r.add_argument("-v", "--verbose", action="store_true")
    for sp in (p, r):
        sp.add_argument("--policy-config", help="versioned JSON experiment policy")
        sp.add_argument("--runner", choices=["serial", "async"], default="serial")
        sp.add_argument("--model-assist", action="store_true", help="bounded supplier-email model interpretation")
    rep = sub.add_parser("report", help="summarise a run directory")
    rep.add_argument("run_dir")
    rep.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "report":
        from .report import main as report_main

        return report_main([args.run_dir, *(["--json"] if args.json else [])])
    if args.cmd == "prep":
        from .claims import prep

        print(json.dumps(prep()))
        return 0

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(asctime)s %(message)s", datefmt="%H:%M:%S"
    )
    run_dir = _run_dir()
    tracer = Tracer(run_dir)
    client = ArenaClient()

    from .policy import PolicyConfig

    try:
        policy = PolicyConfig.load(args.policy_config) if args.policy_config else None
    except (OSError, ValueError, TypeError) as exc:
        ap.error(str(exc))

    def new_agent():
        return PackageAgent(tracer=tracer, policy=policy, model_assist=args.model_assist)

    if args.runner == "async":
        cfg = {**run_config(new_agent(), runner="async"), **runtime_config(getattr(args, "parallel", 1))}
    else:
        cfg = run_config(new_agent())
    tracer.log("run", cmd=args.cmd, arena=os.environ.get("ARENA_URL"), **cfg)

    if args.runner == "async":
        out = run_async(args, new_agent, tracer, run_dir)
    elif args.cmd == "play":
        table = RemoteTable(client)
        try:
            out = {args.case_id: play_case(table, args.case_id, new_agent())}
        except ArenaError as e:
            raise SystemExit(str(e)) from None
    elif args.set_ == "final":
        out = play_waves(client, new_agent, args.waves, min(args.parallel, 10))
    else:
        ids = [c["case_id"] for c in hosted(client.cases(args.set_))]
        out = play_all(lambda: RemoteTable(client), ids, new_agent, min(args.parallel, 10))

    scores = {}
    for case_id, result in out.items():
        row = repr(result) if isinstance(result, Exception) else summary(result)
        full = None if isinstance(result, Exception) else result  # keeps cost_breakdown
        tracer.log("result", case=case_id, result=row, full=full)
        print(case_id, json.dumps(row))
        if isinstance(result, dict) and result.get("score") is not None:
            scores[case_id] = result["score"]
    if scores:
        print(f"mean score: {100 * statistics.mean(scores.values()):.1f} over {len(scores)}/{len(out)} cases")
    print(f"trace: {tracer.path}")
    if client.practice_remaining is not None:
        print(f"practice sessions left: {client.practice_remaining}")
    return (
        0
        if out
        and all(
            isinstance(r, dict)
            and r.get("score") is not None
            and isinstance(r.get("deal"), bool)
            and r.get("ended", True) is True
            for r in out.values()
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
