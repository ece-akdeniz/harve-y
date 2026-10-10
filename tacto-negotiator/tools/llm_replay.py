"""Offline replay of a saved lab run with two policy configs: where do the model features change
our decisions, and what does the model actually extract/choose/write?

    uv run --locked python tools/llm_replay.py RUN_JSON --base configs/score-push-v3.json \\
        --cand configs/fresh-llm.json [--cases P07 P10] [--fetch] [--mode traits|all]

Per case and buyer turn the recorded thread prefix is fed to one agent per config (state carried
across turns, like a live session) and the two proposals are compared. The recorded buyer message,
not the agent's, is appended afterwards, so both agents always see the same history. Attachments
are not stored in run.json: with --fetch the quote PDFs of these owned sessions are read once from
the arena (GET attachments, no spectator endpoints, no sessions opened) and cached next to the run.
Model calls are real (LLM_* from .env); traits, picks, answers and latency are printed per turn.
Multi-supplier (rfq) cases are replayed per thread with the other threads at their final state.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from arena_kit.docs import read_document  # noqa: E402

from negotiator.agent import PackageAgent  # noqa: E402
from negotiator.policy import PolicyConfig  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/practice_cases.json"


class Recorder:
    def __init__(self):
        self.records = []

    def log(self, event, **fields):
        self.records.append({"event": event, **fields})

    def drain(self, kinds):
        out = [r for r in self.records if r.get("kind") in kinds]
        self.records = []
        return out


def load_cases():
    return {c["case_id"]: c for c in json.loads(FIXTURE.read_text())}


def attachments(run_path, attempts, fetch):
    cache = run_path.parent / "attachments.json"
    texts = json.loads(cache.read_text()) if cache.is_file() else {}
    if fetch:
        from arena_kit.client import ArenaClient

        client = ArenaClient()
        for a in attempts:
            for t in (a.get("threads") or {}).values():
                for m in t.get("messages", []):
                    for att in m.get("attachments") or []:
                        aid = att.get("attachment_id")
                        if aid and aid not in texts and att.get("name", "").startswith("quote"):
                            texts[aid] = read_document(att["name"], client.attachment(a["session_id"], aid))
        cache.write_text(json.dumps(texts, indent=1))
    return texts


def thread_messages(thread, texts):
    out = []
    for m in thread.get("messages", []):
        m = dict(m)
        atts = []
        for att in m.get("attachments") or []:
            att = dict(att)
            if att.get("attachment_id") in texts:
                att["text"] = texts[att["attachment_id"]]
            atts.append(att)
        m["attachments"] = atts
        if m.get("from") == "buyer":
            m = {k: v for k, v in m.items() if k != "message_id"}
        out.append(m)
    return out


def agent_for(config_path, tracer):
    policy = PolicyConfig.load(config_path)
    return PackageAgent(policy=policy, tracer=tracer, estimates={}, meso=False)


def summarize(move):
    msg = move.get("message") or {}
    if msg.get("action"):
        return {"action": msg["action"]}
    return {"terms": [s.get("terms") for s in msg.get("term_sheets") or []],
            "body": msg.get("body", ""), "refs": msg.get("refs")}


def replay_case(case, threads_full, base_cfg, cand_cfg, mode):
    sids = list(threads_full)
    rec_a, rec_b = Recorder(), Recorder()
    agent_a, agent_b = agent_for(base_cfg, rec_a), agent_for(cand_cfg, rec_b)
    diffs = []
    for sid in sids:
        full = threads_full[sid]
        others = {s: threads_full[s] for s in sids if s != sid}
        prefix = []
        turn = 0
        for m in full:
            if m.get("from") != "buyer":
                prefix.append(m)
                continue
            turn += 1
            if not any(x.get("from") != "buyer" for x in prefix):
                prefix.append(m)
                continue
            threads = {**others, sid: list(prefix)}
            out = {}
            for name, agent, rec in (("base", agent_a, rec_a), ("cand", agent_b, rec_b)):
                started = time.monotonic()
                try:
                    move = agent.decide(case, {k: list(v) for k, v in threads.items()})
                    out[name] = summarize(move)
                except Exception as exc:  # replay harness limitation, not a runtime path
                    out[name] = {"error": f"{type(exc).__name__}: {exc}"}
                out[name]["elapsed_s"] = round(time.monotonic() - started, 2)
                out[name]["model"] = rec.drain({"model_traits", "model_fallback", "model_choice", "model_answer",
                                                "fast_payment", "bundle_volume", "package_trade"})
            recorded = summarize({**m, "message": m})
            same_terms = out["base"].get("terms") == out["cand"].get("terms")
            same_body = out["base"].get("body") == out["cand"].get("body")
            diffs.append({"supplier": sid, "turn": turn, "recorded_terms": recorded.get("terms"),
                          "base": out["base"], "cand": out["cand"], "same_terms": same_terms, "same_body": same_body})
            prefix.append(m)
    return diffs, agent_b


def print_case(cid, diffs, agent_b, mode):
    print(f"\n=== {cid}")
    for d in diffs:
        flag = "" if d["same_terms"] else "  <-- TERMS DIFFER"
        bflag = "" if d["same_body"] else "  (body differs)"
        print(f"- {d['supplier']} turn {d['turn']}: recorded {d['recorded_terms']}")
        print(f"    base {d['base'].get('terms') or d['base'].get('action') or d['base'].get('error')}"
              f"  [{d['base']['elapsed_s']}s]")
        print(f"    cand {d['cand'].get('terms') or d['cand'].get('action') or d['cand'].get('error')}"
              f"  [{d['cand']['elapsed_s']}s]{flag}{bflag}")
        for r in d["cand"]["model"]:
            kind = r.get("kind")
            if kind == "model_traits":
                for item in r.get("items", []):
                    print(f"      trait {item['trait']} <- {item['source']}: \"{item['quote'][:120]}\"")
                print(f"      model traits {r.get('traits')} ({r.get('elapsed_s')}s)")
            elif kind == "model_choice":
                print(f"      choice: {r.get('selected')} reason={r.get('reason')!r} "
                      f"candidates={[c.get('id') for c in r.get('candidates', [])]} ({r.get('elapsed_s')}s)")
            elif kind == "model_answer":
                print(f"      answer[{r.get('status')}]: {r.get('text')!r} ({r.get('elapsed_s')}s) "
                      f"q={r.get('questions')}")
            elif kind == "model_fallback":
                print(f"      fallback: {r}")
        if not d["same_body"] and mode == "all":
            print("      cand body:", (d["cand"].get("body") or "").replace("\n", " // ")[:700])
    if agent_b.llm:
        m = agent_b.llm.metrics()
        print(f"  llm calls {m['calls']} fallbacks {m['fallbacks']} max {m['max_latency_s']}s by_kind {m['by_kind']}")


def trait_report(case, sids, agent_b):
    """Regex vs model traits per supplier, and which active levers each model-only trait touches."""
    policy = agent_b.policy
    t = case["type"]
    levers = []
    if t in policy.fast_payment_types:
        levers.append(("wants_fast_payment", "fast_payment_types: shortest legal payment term"))
    if t in policy.bundle_volume_types:
        levers.append(("idle_capacity", "bundle_volume: cites the capacity note"))
    if t in policy.package_types:
        levers.append(("multi_year_only", "TradePolicy.initial: tenor >= horizon"))
        levers.append(("wants_fast_payment", "TradePolicy.switch: explores payment_days"))
    for sid in sids:
        regex, _ = agent_b._public_traits(sid)
        model = agent_b.trait_reader.traits(sid) if agent_b.trait_reader else set()
        only = model - regex
        print(f"  {sid}: regex {sorted(regex)} | model-only {sorted(only)}")
        for trait, what in levers:
            if trait in only:
                ev = agent_b.trait_reader.evidence(sid, trait)
                print(f"    !! model-only {trait} touches an active lever ({what}); sources {ev}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json", type=Path)
    ap.add_argument("--base", default="configs/score-push-v3.json")
    ap.add_argument("--cand", default="configs/fresh-llm.json")
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--fetch", action="store_true", help="read quote attachments of these owned sessions once")
    ap.add_argument("--mode", choices=["traits", "all"], default="all")
    args = ap.parse_args()
    if not os.environ.get("ARENA_DATA"):
        raise SystemExit("ARENA_DATA must point at the data package")
    run = json.loads(args.run_json.read_text())
    attempts = [a for a in run["attempts"] if a.get("threads")]
    if args.cases:
        want = {c if c.startswith("case:") else f"case:{c}" for c in args.cases}
        attempts = [a for a in attempts if a["case_id"] in want]
    texts = attachments(args.run_json, attempts, args.fetch)
    cases = load_cases()
    for a in attempts:
        case = cases.get(a["case_id"])
        if case is None:
            print(f"skip {a['case_id']}: no case fixture")
            continue
        threads = {sid: thread_messages(t, texts) for sid, t in a["threads"].items()}
        missing = sum(1 for ms in threads.values() for m in ms for att in m.get("attachments") or []
                      if "text" not in att)
        diffs, agent_b = replay_case(case, threads, args.base, args.cand, args.mode)
        print_case(a["case_id"], diffs, agent_b, args.mode)
        if missing:
            print(f"  note: {missing} attachments without text (run with --fetch for quote standard terms)")
        trait_report(case, list(threads), agent_b)


if __name__ == "__main__":
    main()
