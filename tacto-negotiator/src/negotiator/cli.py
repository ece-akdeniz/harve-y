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

from .guidance import RuntimeGuidance
from .memory import MAX_MEMORY_BYTES, validate_memory
from .play import play_all, play_case, play_waves, run_config
from .runner import run_async, runtime_config
from .trace import Tracer

# Live Final default policy: the measured score-push v6 config (v5 + cost_target_posterior 0.10; v5 = v4 +
# raw_material fixed-volume ladder). Live-confirmed P02 .7351, P08 .7036, P18 .5870; byte-identical to v4
# on every other practice case.
FINAL_POLICY = Path(__file__).resolve().parents[2] / "configs" / "score-push-v6.json"


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
        sp.add_argument("--policy-config", help="versioned JSON experiment policy (final default: v6)")
        sp.add_argument("--memory-file", type=Path, help="saved immutable memory snapshot JSON (at most 64 KiB)")
        sp.add_argument(
            "--runner", choices=["serial", "async", "auto"], default=None,
            help="auto: more than one supplier -> async, one supplier -> serial (default for --set final)",
        )
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

    final = args.cmd == "run" and args.set_ == "final"
    if args.runner is None:
        args.runner = "auto" if final else "serial"
    if final and not args.policy_config:
        args.policy_config = str(FINAL_POLICY)  # the measured score-push v6 policy
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(asctime)s %(message)s", datefmt="%H:%M:%S"
    )
    run_dir = _run_dir()
    tracer = Tracer(run_dir)

    from .policy import PolicyConfig

    try:
        memory = None
        if args.memory_file:
            with args.memory_file.open("rb") as source:
                raw = source.read(MAX_MEMORY_BYTES + 1)
            if len(raw) > MAX_MEMORY_BYTES:
                raise ValueError("memory snapshot file too large")
            memory = validate_memory(json.loads(raw))
        guidance = RuntimeGuidance.load()
        policy = PolicyConfig.load(args.policy_config) if args.policy_config else None
    except (OSError, ValueError, TypeError) as exc:
        ap.error(str(exc))
    if args.model_assist:
        provider = os.environ.get("LLM_PROVIDER", "anthropic")
        key_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "LLM_API_KEY"
        if provider not in {"anthropic", "openai"} or not os.environ.get("LLM_MODEL") or not os.environ.get(key_name):
            ap.error("--model-assist requires a supported LLM_PROVIDER, LLM_MODEL and provider API key")

    client = ArenaClient()

    def new_agent():
        agent = guidance.new_agent(tracer=tracer, policy=policy, memory=memory)
        if policy is not None:
            # Parity with the measured policy scores: lab agents (PackageAgent(**config)) never
            # add the guidance's conditional-exchange wording; with it, sandbox D01/D02 drop
            # from .9192/.5239 to .9048/.5029.
            agent.conditional_exchange = False
        if args.model_assist:
            from .model_assist import ModelAssist

            agent.model_assist = ModelAssist(
                memory_path=os.environ.get("NEGOTIATOR_APPROVED_MEMORY"),
                data_sha256=os.environ.get("NEGOTIATOR_DATA_SHA256"),
            )
        return agent

    probe = new_agent()
    if args.runner in ("async", "auto"):
        cfg = {**run_config(probe, runner=args.runner), **runtime_config(getattr(args, "parallel", 1))}
    else:
        cfg = run_config(probe)
    tracer.log("run", cmd=args.cmd, arena=os.environ.get("ARENA_URL"), policy_config=args.policy_config,
               conditional_exchange=probe.conditional_exchange, **cfg)

    if args.runner in ("async", "auto"):
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
