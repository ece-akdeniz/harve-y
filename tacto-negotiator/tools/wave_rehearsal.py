"""Live-Final wave rehearsal against the local kit simulator (offline; never the hosted arena).

Plays every hosted practice case IN PARALLEL as one 8-minute wave (`deadline` = start + 480 s on the
runner's clock) through the async `CaseRunner`, for one or more agent configs, with the wave time guard
on or off, and an optional injected supplier reply delay (the hosted supplier takes up to ~1 min).

    export ARENA_DATA=.../data/package
    uv run --locked python tools/wave_rehearsal.py --config configs/fresh-h1h2-run.json \
        --config configs/score-push-v3-run.json --delay 50 --out /tmp/wave-rehearsal.json

`--delay 0` is the raw simulator (seconds per case: shows round counts, not timing). `--delay 50`
takes ~8 real minutes per wave; every (config x guard) variant runs concurrently in the same wave so a
full rehearsal is one wall-clock wave. `--scale` compresses the clock (1 simulated s = scale real s)
for quick checks only: agent compute is not compressed, so compressed runs overstate decision time.
`--round-estimate S` overrides `negotiator.agent.ROUND_ESTIMATE_S` for the run (guard calibration; see
experiments/SAFETY.md section 5a: 120 kept, 90 loses three single-supplier cases at 90 s replies).

Measured (2026-10-11, kit sim, 10 hosted practice cases per wave, --delay 50, real clock, both configs):
worst case 280 s with the guard (P01/P04, 5 rounds, slowest round 80 s), 366 s without it (P05, three
suppliers, slowest round 85 s) where the runner's watchdog had to close at the cap; the guard fired only on
P05 (time left 202 s < 240 s) and accepted the standing sheet at round 4. First decision per case 11-27 s
before prewarm (data package, dossiers, evidence context, ten agents starting at once), <= 0.8 s with
prewarm on; later ones < 0.4 s; no timeouts.
"""

import argparse
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

from arena_kit.client import ArenaError
from arena_kit.sim import Fail, Sim

from negotiator.agent import configured_agent
from negotiator.client import UncertainOutcome
from negotiator.prewarm import prewarm_async, prewarm_case_async
from negotiator.runner import CaseRunner, Clock
from negotiator.state import Journal

ROOT = Path(__file__).resolve().parents[1]
WAVE_S = 480.0


class ScaledClock(Clock):
    def __init__(self, scale=1.0):
        self.scale, self.t0, self.m0 = scale, time.time(), time.monotonic()

    def time(self):
        return self.t0 + (time.monotonic() - self.m0) / self.scale

    async def sleep(self, s):
        await asyncio.sleep(max(0.0, s) * self.scale)


class SimArena:
    """AsyncArena's interface over the kit simulator (as tests/test_runner.SimArena): idempotent
    move ids and a supplier reply delay that, as hosted, does not count against the buyer."""

    def __init__(self, cases, facts, clock, delay_s=0.0):
        self.clock, self.delay_s = clock, delay_s
        self.sim = Sim(cases, facts, clock=clock.time)
        self.team, self.replies = "rehearsal", {}

    def _do(self, fn, *a):
        try:
            return fn(self.team, *a)
        except Fail as e:
            raise ArenaError(e.status, e.detail) from None

    async def cases(self, set_):
        return [{**c, "hosted": True} for c in self.sim.cases.values()]

    async def open_session(self, case_id, move_id):
        if move_id not in self.replies:
            self.replies[move_id] = self._do(self.sim.open, case_id)
        return self.replies[move_id]

    async def send(self, session_id, supplier_id, message, move_id):
        if move_id in self.replies:
            return self.replies[move_id]
        reply = self._do(self.sim.message, session_id, supplier_id, message)
        self.replies[move_id] = reply
        if not message.get("action") and "result" not in reply and self.delay_s:
            th = self.sim.sessions[session_id]["threads"][supplier_id]
            # The sim's 60-second rule runs on `last_at`; hosted, our 60 s start at the supplier's reply.
            # Park the thread's clock at the reply time BEFORE sleeping, otherwise with delay > 60 s any
            # session()/thread() poll during the sleep (multi-supplier cases) would count a timeout against us.
            th["last_at"] = self.clock.time() + self.delay_s
            await self.clock.sleep(self.delay_s)
            if not th["closed"]:
                th["last_at"] = self.clock.time()  # our 60 s start at the supplier's reply
        return reply

    async def session(self, session_id):
        return self._do(self.sim.state, session_id)

    async def thread(self, session_id, supplier_id):
        return self._do(self.sim.thread, session_id, supplier_id)

    async def attachment(self, session_id, attachment_id):
        return self._do(self.sim.attachment, session_id, attachment_id)[0]


class Trace:
    def __init__(self):
        self.rows = []

    def log(self, event, **fields):
        self.rows.append({"event": event, **fields})


def load_config(path):
    raw = json.loads(Path(path).read_text())
    if "policy_config" not in raw:  # a bare policy: wrap as the *-run.json files do
        raw = {"policy_config": raw, "estimates": {}, "meso": False}
    return raw


def hosted_cases():
    cases = json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
    return {c["case_id"]: c for c in cases if c.get("hosted")}


def facts():
    try:
        from negotiator.dossiers import load_package

        return dict(load_package().facts)
    except (FileNotFoundError, OSError, ValueError):
        return {}


async def play_wave(label, cfg, cases, known, *, delay_s, guard, clock, journal_dir, prewarm=True):
    trace = Trace()
    # As hosted: the listing carries `hosted`, the opened session's case does not (context cache key).
    arena = SimArena({k: {f: v for f, v in c.items() if f != "hosted"} for k, c in cases.items()}, known, clock,
                     delay_s)
    t0 = clock.time()
    cap = t0 + WAVE_S

    def make_agent():
        policy = dict(cfg["policy_config"])
        # Package advice (an LLM call) is serial-runner only; the async wave runner rejects it, and the
        # rehearsal is offline. Dropped here; everything else in the policy is live.
        policy.pop("package_advice_types", None)
        policy["prewarm"] = bool(prewarm)
        agent = configured_agent(policy, tracer=trace, estimates=cfg.get("estimates", {}),
                                 meso=cfg.get("meso", False))
        if not guard:
            agent.time_guard_rounds = 0
        return agent

    if prewarm:  # as `runner.run_waves`: once, before the wave's cases are polled/started
        await prewarm_async(make_agent, tracer=trace)
    wave_t0 = clock.time()

    async def one(case_id):
        agent = make_agent()
        if prewarm:  # as `runner.play_case`: per case, in a thread, before the session opens
            await prewarm_case_async(agent, cases[case_id], tracer=trace)
        variant = f"{label}-g{int(guard)}-p{int(prewarm)}-{case_id[5:]}"
        runner = CaseRunner(arena, case_id, agent, Journal(Path(journal_dir) / f"{variant}.jsonl"),
                            case=cases[case_id], deadline=lambda: cap, clock=clock, tracer=trace)
        try:
            return await runner.run()
        except (ArenaError, UncertainOutcome, Exception) as exc:  # one broken case must not stop the wave
            return {"error": f"{type(exc).__name__}: {exc}", "session_id": runner.st.session_id if runner.st else None}

    results = dict(zip(cases, await asyncio.gather(*(one(c) for c in cases)), strict=True))
    warm = [r for r in trace.rows if r["event"] == "prewarm"]
    rows = []
    for case_id, result in results.items():
        sid = result.get("session_id")
        sess = arena.sim.sessions.get(sid) if sid else None
        threads = [r for r in trace.rows if r["event"] == "thread_time" and r.get("case") == case_id]
        guards = [r for r in trace.rows if r["event"] == "decision" and r.get("kind") == "time_guard"
                  and r.get("case") == case_id]
        closes = [r for r in trace.rows if r["event"] == "close" and r.get("case") == case_id]
        rounds = [r for r in trace.rows if r["event"] == "round_time" and r.get("case") == case_id]
        end = next((r for r in trace.rows if r["event"] == "case_end" and r.get("case") == case_id), {})
        warm_case = next((r for r in trace.rows if r["event"] == "prewarm_case" and r.get("case") == case_id), None)
        firsts = [r["decide_s"] for r in rounds if r.get("round") == 1]
        rows.append({
            "config": label, "guard": guard, "delay_s": delay_s, "prewarm": prewarm, "case": case_id,
            "type": cases[case_id]["type"],
            "deal": result.get("deal"), "score": result.get("score"), "error": result.get("error"),
            "end_reason": sess["end_reason"] if sess else None, "how": end.get("how"),
            "close_reasons": [c.get("reason") for c in closes],
            "guard_fired": bool(guards), "guard_actions": [g.get("action") for g in guards],
            "guard_time_left": [g.get("time_left") for g in guards],
            "threads": {t["supplier"]: {"total_s": t["total_s"], "rounds": t["rounds"],
                                        "slowest_round_s": t["slowest_round_s"],
                                        "slowest_decide_s": t["slowest_decide_s"], "end": t["end"],
                                        "decide_s": [r["decide_s"] for r in rounds if r["supplier"] == t["supplier"]],
                                        "reply_s": [r["reply_s"] for r in rounds if r["supplier"] == t["supplier"]]}
                        for t in threads},
            "first_decide_s": max(firsts) if firsts else None,
            "prewarm_case_s": warm_case.get("seconds") if warm_case else None,
            "prewarm_s": warm[0].get("seconds") if warm else None,
            "wave_start_offset_s": round(wave_t0 - t0, 2),
            "case_s": round(max([t["total_s"] or 0 for t in threads] or [0]), 1),
            "timeouts": result.get("thread_timeouts"),
        })
    return rows


def table(rows):
    head = ("config", "guard", "prewarm", "delay", "case", "type", "deal", "score", "end_reason", "case_s", "rounds",
            "slowest_round_s", "first_decide_s", "prewarm_case_s", "guard_fired", "guard_actions")
    out = [" | ".join(head)]
    for r in rows:
        rounds = "/".join(str(t["rounds"]) for t in r["threads"].values())
        slow = max([t["slowest_round_s"] for t in r["threads"].values()] or [0])
        out.append(" | ".join(str(x) for x in (
            r["config"], "on" if r["guard"] else "off", "on" if r["prewarm"] else "off", r["delay_s"], r["case"],
            r["type"], r["deal"],
            None if r["score"] is None else round(r["score"], 3), r["end_reason"] or r["error"], r["case_s"],
            rounds, slow, r["first_decide_s"], r["prewarm_case_s"], r["guard_fired"], ",".join(r["guard_actions"]))))
    return "\n".join(out)


async def main_async(args):
    cases, known = hosted_cases(), facts()
    if args.case:
        cases = {c: cases[c] for c in args.case}
    journal_dir = tempfile.mkdtemp(prefix="wave-rehearsal-")
    rows = []
    for path in args.config:
        cfg, label = load_config(path), Path(path).stem
        for guard in {"on": [True], "off": [False], "both": [True, False]}[args.guard]:
            for prewarm in {"on": [True], "off": [False], "both": [True, False]}[args.prewarm]:
                # One wave at a time: a wave's cases run in parallel (as hosted), variants do not share CPU.
                rows += await play_wave(label, cfg, cases, known, delay_s=args.delay, guard=guard,
                                        clock=ScaledClock(args.scale), journal_dir=journal_dir, prewarm=prewarm)
                print(f"wave done: {label} guard={'on' if guard else 'off'} prewarm={'on' if prewarm else 'off'}",
                      file=sys.stderr, flush=True)
    print(table(rows))
    slowest_decide = max(t["slowest_decide_s"] for r in rows for t in r["threads"].values())
    print(f"\nagent decision time: slowest {slowest_decide} s")
    first = max((r["first_decide_s"] or 0) for r in rows)
    warm = [r["prewarm_s"] for r in rows if r["prewarm_s"] is not None]
    print(f"first decision per case: slowest {first} s; package prewarm {warm[0] if warm else None} s")
    worst = max(rows, key=lambda r: r["case_s"] or 0)
    print(f"\nworst-case thread/case duration: {worst['case_s']} s ({worst['config']} guard="
          f"{'on' if worst['guard'] else 'off'} {worst['case']}); wave cap {WAVE_S:.0f} s")
    capped = [(r["config"], r["guard"], r["case"]) for r in rows
              if r["end_reason"] == "wave_cap" or "wave cap" in (r["close_reasons"] or [])]
    print(f"cap closes (runner watchdog 'wave cap' or arena wave_cap): {capped}")
    if args.out:
        from negotiator import agent as agent_mod

        Path(args.out).write_text(json.dumps({"wave_s": WAVE_S, "delay_s": args.delay, "scale": args.scale,
                                              "round_estimate_s": agent_mod.ROUND_ESTIMATE_S,
                                              "time_guard_rounds": agent_mod.TIME_GUARD_ROUNDS,
                                              "rows": rows}, indent=1, default=str))
        print(f"written: {args.out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", action="append", required=True, help="*-run.json ({policy_config, estimates, meso})")
    ap.add_argument("--delay", type=float, default=0.0, help="injected supplier reply delay, seconds")
    ap.add_argument("--scale", type=float, default=1.0, help="clock compression (1 = real wall clock)")
    ap.add_argument("--guard", choices=["on", "off", "both"], default="on", help="agent wave time guard")
    ap.add_argument("--prewarm", choices=["on", "off", "both"], default="on",
                    help="pre-warm the package/dossiers before the wave and each case before it opens")
    ap.add_argument("--case", action="append", help="restrict to these case ids")
    ap.add_argument("--round-estimate", type=float, default=None,
                    help="override agent.ROUND_ESTIMATE_S (guard calibration; default: the agent's constant)")
    ap.add_argument("--out", help="JSON output path")
    args = ap.parse_args(argv)
    if args.round_estimate is not None:
        from negotiator import agent as agent_mod

        agent_mod.ROUND_ESTIMATE_S = float(args.round_estimate)
        print(f"ROUND_ESTIMATE_S={agent_mod.ROUND_ESTIMATE_S}", file=sys.stderr)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
