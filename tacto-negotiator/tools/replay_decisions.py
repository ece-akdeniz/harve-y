"""Offline decision replay: feed saved hosted transcripts to the agent under two policy configs.

    uv run python tools/replay_decisions.py --cases case:P01,case:P03 \\
        --config-a configs/score-push-v3.json --config-b configs/X.json [--runs DIR] [--json OUT] \\
        [--conditional-exchange auto|on|off] [--max-runs N]

For every saved run.json attempt of a chosen case, every buyer message in the transcript becomes a
decision point: the agent sees the history up to that point - with its OWN replayed moves in place
of the saved buyer messages - and `decide(case, threads)` is recorded per config (term sheets,
action, refs, body). The two configs are compared round by round; the first differing round is the
headline, later rounds are still compared but flagged as `history invalid` because the supplier
would have answered differently after a diverging move. Never contacts the arena.

Limitations (documented, pragmatic):
- Supplier replies are fixed: after the first divergence from the saved transcript the saved
  supplier messages no longer answer our replayed moves.
- Saved attachments carry no PDF text (`content_b64` is null), so quote-PDF standard terms are
  empty on replay; both configs see the same input, so A/B differences remain meaningful, but
  absolute moves can differ from the live run.
- Multi-supplier (RFQ) cases are replayed jointly by message index: at message index j every thread
  shows its first j saved messages (buyer moves substituted). When the agent addresses a supplier
  other than the saved one, the saved buyer message is kept in that thread and the round is flagged.
- `final_hold_s` timing (monotonic clock) is not reproduced; replays run instantly.
- Lab runs do not set `conditional_exchange`; `auto` turns it on when a saved buyer body mentions it.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from negotiator.agent import configured_agent  # noqa: E402

DEFAULT_RUNS = Path("/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/experiments/runs")
PRICE_FIELD = "unit_price"


# ---------------------------------------------------------------- configs and agents


def load_config(path) -> dict:
    p = Path(path)
    if not p.is_file() and (ROOT / path).is_file():
        p = ROOT / path
    cfg = json.loads(p.read_text())
    if "policy_config" not in cfg:
        cfg = {"policy_config": cfg}
    kwargs = {k: v for k, v in cfg.items() if k not in ("name", "notes", "hypothesis")}
    kwargs.setdefault("estimates", {})
    kwargs.setdefault("meso", False)
    kwargs["model_assist"] = False  # offline and deterministic
    kwargs.pop("trace_dir", None)
    return kwargs


def make_agent(kwargs: dict, conditional_exchange: bool):
    agent = configured_agent(**kwargs)
    agent.conditional_exchange = conditional_exchange
    return agent


# ---------------------------------------------------------------- transcripts


def load_cases(path: Path) -> dict[str, dict]:
    return {c["case_id"]: c for c in json.loads(path.read_text())}


def thread_messages(thread) -> list[dict]:
    if isinstance(thread, dict):
        return list(thread.get("messages") or [])
    return list(thread or [])


def iter_attempts(runs_dir: Path, cases: set[str]):
    """(run_name, run_path, attempt) for saved attempts with threads of a chosen case; one per session."""
    seen_sessions = set()
    for path in sorted(runs_dir.rglob("run.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        for attempt in data.get("attempts") or []:
            if attempt.get("case_id") not in cases or not attempt.get("threads"):
                continue
            session = attempt.get("session_id")
            if session and session in seen_sessions:
                continue  # imported copies of the same hosted session
            seen_sessions.add(session)
            name = data.get("name") or ""
            yield (path.parent.name if name.startswith("Imported") or not name else name), path, attempt


def decision_points(threads: dict[str, list[dict]]) -> list[tuple[int, str]]:
    """(message index, supplier) of every saved buyer message, ordered by index then supplier."""
    out = []
    for j in range(max((len(m) for m in threads.values()), default=0)):
        for sid in sorted(threads):
            if j < len(threads[sid]) and threads[sid][j].get("from") == "buyer":
                out.append((j, sid))
    return out


def _norm_terms(message: dict) -> list:
    return [s.get("terms") for s in (message.get("term_sheets") or [])]


def _summary(message: dict, saved: bool = False) -> dict:
    """Comparable view of a move. Saved transcripts may lack `refs`/`body` (None = unknown, not compared)."""
    refs = message.get("refs")
    return {"term_sheets": _norm_terms(message), "action": message.get("action"),
            "refs": None if saved and refs is None else list(refs or []), "body": message.get("body")}


def replay_config(case: dict, saved: dict[str, list[dict]], agent) -> list[dict]:
    """One replay pass: per decision point the agent's move given the substituted history."""
    ours: dict[str, dict[int, dict]] = {sid: {} for sid in saved}
    rounds, done = [], set()
    for n, (j, sid) in enumerate(decision_points(saved), 1):
        history = {}
        for s, msgs in saved.items():
            # Threads already addressed at this index (RFQ: earlier suppliers) show our move there too.
            cut = j + 1 if (j, s) in done else j
            history[s] = [ours[s].get(i, m) if m.get("from") == "buyer" else m for i, m in enumerate(msgs[:cut])]
        done.add((j, sid))
        try:
            move = agent.decide(case, history)
        except Exception as exc:  # keep comparing the other rounds
            rounds.append({"round": n, "index": j, "saved_supplier": sid, "supplier": None, "error": repr(exc)[:200],
                           "saved": _summary(saved[sid][j], saved=True), "move": None})
            continue
        chosen, message = move.get("supplier_id"), move.get("message") or {}
        if chosen == sid:
            ours[sid][j] = {"from": "buyer", **message}
        rounds.append({"round": n, "index": j, "saved_supplier": sid, "supplier": chosen, "error": None,
                       "saved": _summary(saved[sid][j], saved=True), "move": _summary(message),
                       "supplier_mismatch": chosen != sid})
    return rounds


# ---------------------------------------------------------------- comparison


def _price(summary: dict | None):
    sheets = (summary or {}).get("term_sheets") or []
    return sheets[0].get(PRICE_FIELD) if sheets and isinstance(sheets[0], dict) else None


def diff_summaries(a: dict | None, b: dict | None) -> list[str]:
    """Human-readable differences between two move summaries (empty when identical)."""
    if a is None or b is None:
        return [] if a is b else ["one side errored"]
    out = []
    if a["term_sheets"] != b["term_sheets"]:
        pa, pb = _price(a), _price(b)
        if pa is not None and pb is not None and pa != pb:
            out.append(f"price {pa} vs {pb} (delta {round(pb - pa, 4):+})")
        fa = (a["term_sheets"] or [{}])[0] or {}
        fb = (b["term_sheets"] or [{}])[0] or {}
        fields = sorted(k for k in set(fa) | set(fb) if k != PRICE_FIELD and fa.get(k) != fb.get(k))
        if fields:
            out.append("terms " + ", ".join(f"{k}: {fa.get(k)} vs {fb.get(k)}" for k in fields))
        if len(a["term_sheets"]) != len(b["term_sheets"]):
            out.append(f"sheets {len(a['term_sheets'])} vs {len(b['term_sheets'])}")
        if not out:
            out.append("term sheets differ")
    if a["action"] != b["action"]:
        out.append(f"action {a['action']} vs {b['action']}")
    if a["refs"] != b["refs"] and a["refs"] is not None and b["refs"] is not None:
        out.append(f"refs {a['refs']} vs {b['refs']}")
    if a["body"] != b["body"] and (a["body"] is not None and b["body"] is not None):
        out.append("body differs")
    return out


def compare(rounds_a: list[dict], rounds_b: list[dict]) -> dict:
    first, rows = None, []
    for ra, rb in zip(rounds_a, rounds_b, strict=True):
        diffs = diff_summaries(ra["move"], rb["move"])
        if ra.get("error") or rb.get("error"):
            diffs = diffs or [f"error A={ra.get('error')} B={rb.get('error')}"]
        if diffs and first is None:
            first = ra["round"]
        vs_saved = diff_summaries(ra["move"], ra["saved"]) if ra["move"] else ["error"]
        vs_saved = [d for d in vs_saved if d != "body differs"]  # saved bodies are often missing/decorated
        rows.append({"round": ra["round"], "supplier": ra["saved_supplier"], "diff": diffs,
                     "history_invalid": first is not None and ra["round"] > first,
                     "supplier_mismatch": bool(ra.get("supplier_mismatch") or rb.get("supplier_mismatch")),
                     "a_vs_saved": vs_saved, "price_a": _price(ra["move"]), "price_b": _price(rb["move"]),
                     "price_saved": _price(ra["saved"])})
    return {"first_divergence": first, "rounds": rows,
            "first_vs_saved": next((r["round"] for r in rows if r["a_vs_saved"]), None)}


# ---------------------------------------------------------------- driver


def wants_conditional(saved: dict[str, list[dict]]) -> bool:
    return any("conditional exchange" in (m.get("body") or "").lower()
               for msgs in saved.values() for m in msgs if m.get("from") == "buyer")


def replay_threads(case: dict, saved: dict[str, list[dict]], cfg_a: dict, cfg_b: dict,
                   conditional_exchange="auto") -> dict:
    ce = wants_conditional(saved) if conditional_exchange == "auto" else conditional_exchange == "on"
    rounds_a = replay_config(case, saved, make_agent(cfg_a, ce))
    rounds_b = replay_config(case, saved, make_agent(cfg_b, ce))
    result = compare(rounds_a, rounds_b)
    result.update(case_id=case["case_id"], conditional_exchange=ce, rounds_a=rounds_a, rounds_b=rounds_b)
    return result


def replay_runs(runs_dir: Path, case_ids: list[str], cfg_a: dict, cfg_b: dict, cases: dict[str, dict],
                conditional_exchange="auto", max_runs=None) -> list[dict]:
    results, seen = [], {}
    for name, path, attempt in iter_attempts(runs_dir, set(case_ids)):
        cid = attempt["case_id"]
        if cid not in cases:
            continue
        if max_runs is not None and seen.get(cid, 0) >= max_runs:
            continue
        seen[cid] = seen.get(cid, 0) + 1
        saved = {sid: thread_messages(t) for sid, t in attempt["threads"].items()}
        try:
            result = replay_threads(cases[cid], saved, cfg_a, cfg_b, conditional_exchange)
        except Exception as exc:
            result = {"case_id": cid, "first_divergence": None, "rounds": [], "error": repr(exc)[:300]}
        result.update(run=name, run_path=str(path), attempt_id=attempt.get("attempt_id"), score=attempt.get("score"))
        results.append(result)
    return results


def _what(result: dict) -> str:
    if result.get("error"):
        return f"replay error: {result['error']}"
    first = result["first_divergence"]
    if first is None:
        return "identical"
    row = next(r for r in result["rounds"] if r["round"] == first)
    later = sum(1 for r in result["rounds"] if r["diff"] and r["round"] > first)
    extra = f" (+{later} later rounds differ, history invalid)" if later else ""
    return "; ".join(row["diff"]) + extra


def print_table(results: list[dict], cfg_a: str, cfg_b: str) -> None:
    print(f"A = {cfg_a}\nB = {cfg_b}")
    header = f"{'case':<9} {'run':<36} {'score':>6} {'rounds':>6} {'A!=saved':>8} {'first A!=B':>10}  what differed"
    print(header)
    print("-" * len(header))
    for r in results:
        first = r.get("first_divergence")
        div = "identical" if first is None and not r.get("error") else f"round {first}" if first else "error"
        score = f"{r['score']:.3f}" if isinstance(r.get("score"), (int, float)) else "-"
        vs = r.get("first_vs_saved")
        vs = "-" if vs is None else f"r{vs}"
        print(f"{r['case_id']:<9} {str(r['run'])[:36]:<36} {score:>6} {len(r.get('rounds') or []):>6} {vs:>8} "
              f"{div:>10}  {_what(r)}")
    ident = sum(1 for r in results if r.get("first_divergence") is None and not r.get("error"))
    print(f"\n{len(results)} replays, {ident} identical, {len(results) - ident} diverging/errored")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", default=str(DEFAULT_RUNS), help="directory scanned recursively for run.json")
    ap.add_argument("--cases", required=True, help="comma-separated case IDs, e.g. case:P01,case:P03")
    ap.add_argument("--config-a", required=True)
    ap.add_argument("--config-b", required=True)
    ap.add_argument("--cases-file", default=str(ROOT / "tests/fixtures/practice_cases.json"))
    ap.add_argument("--conditional-exchange", choices=("auto", "on", "off"), default="auto")
    ap.add_argument("--max-runs", type=int, help="at most N saved runs per case")
    ap.add_argument("--json", help="write per-round details here")
    args = ap.parse_args(argv)
    case_ids = [c.strip() for c in args.cases.split(",") if c.strip()]
    cases = load_cases(Path(args.cases_file))
    missing = [c for c in case_ids if c not in cases]
    if missing:
        print(f"unknown cases (not in {args.cases_file}): {', '.join(missing)}")
    cfg_a, cfg_b = load_config(args.config_a), load_config(args.config_b)
    results = replay_runs(Path(args.runs), case_ids, cfg_a, cfg_b, cases, args.conditional_exchange, args.max_runs)
    print_table(results, args.config_a, args.config_b)
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1, default=str))
        print(f"details written to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
