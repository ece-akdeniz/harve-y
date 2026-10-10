"""Frozen-source subset runner for final paired regression.

Run via `uv run --locked python ABSOLUTE_SCRIPT` from the selected source checkout.
Imports come from that checkout's installed package, not the evaluation tool's checkout.
One AsyncArena owns the limiter for all concurrent cases.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from arena_kit.cli import load_env

from negotiator.agent import PackageAgent
from negotiator.client import AsyncArena
from negotiator.play import run_config
from negotiator.runner import run_set, runtime_config
from negotiator.state import Journal
from negotiator.trace import Tracer


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", nargs="+", required=True)
    ap.add_argument("--parallel", type=int, default=10)
    ap.add_argument("--set", dest="set_", choices=["practice", "sandbox"], default="practice")
    ap.add_argument("--runner", choices=["async"], default="async")
    ap.add_argument("--policy-config")
    args = ap.parse_args()
    load_env()
    if len(set(args.cases)) != len(args.cases):
        ap.error("duplicate cases")
    policy = None
    if args.policy_config:
        from negotiator.policy import PolicyConfig

        policy = PolicyConfig.load(args.policy_config)
    path = Path(os.environ["NEGOTIATOR_LOG_DIR"])
    tracer = Tracer(path)
    journal = Journal(path / "journal.jsonl")

    def new_agent():
        kw = {"tracer": tracer}
        if policy is not None:
            kw["policy"] = policy
        return PackageAgent(**kw)

    tracer.log(
        "run",
        cmd="selected_cases",
        cases=args.cases,
        **run_config(new_agent(), runner="async"),
        **runtime_config(args.parallel),
    )

    async def run():
        arena = AsyncArena()
        try:
            return await run_set(
                arena, args.set_, new_agent, journal, parallel=args.parallel, case_ids=args.cases, tracer=tracer
            )
        finally:
            await arena.aclose()

    results = asyncio.run(run())
    ok = set(results) == set(args.cases)
    for cid, result in results.items():
        full = result if isinstance(result, dict) else None
        tracer.log("result", case=cid, result=full or repr(result), full=full)
        print(json.dumps({"case": cid, "result": full or type(result).__name__}), flush=True)
        ok = (
            ok and isinstance(result, dict) and result.get("score") is not None and isinstance(result.get("deal"), bool)
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
