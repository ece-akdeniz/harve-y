"""Run summaries for experiments (metrics in docs/04-experiments.md).

Sources, in order of authority: the run's trace.jsonl (our decisions and the result we saw),
hosted session dumps next to it (`hosted-<session>.json` from tools/replay_viewer.py, or the
`case-*.json` files of tools/sandbox_baseline.py: arena state with cost breakdown and threads),
and the sibling `<run>.log` for session ids. Every figure keeps a pointer to where it came from.

    uv run --locked python -m negotiator.report experiments/runs/practice_P01 [--json]
"""

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

SESSION_RE = re.compile(r"\bsession ([0-9a-f]{16})\b")
GUARD_KEYS = ("guard", "guards", "blocked", "guard_outcome")


def find_traces(run_dir) -> list[Path]:
    p = Path(run_dir)
    if p.is_file():
        return [p]
    if (p / "trace.jsonl").is_file():
        return [p / "trace.jsonl"]
    return sorted(p.rglob("trace.jsonl"))


def load_trace(path) -> list[dict]:
    """Events of one trace.jsonl, each with `_src` = "<file>#L<n>". Bad lines are skipped."""
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ev["_src"] = f"{Path(path).name}#L{n}"
        out.append(ev)
    return out


def load_hosted(run_dir) -> dict[str, dict]:
    """case_id -> {"session", "state", "threads", "_src"} from hosted dumps in or above run_dir."""
    p = Path(run_dir)
    base = p.parent if p.is_file() else p
    out = {}
    for f in sorted(base.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(d, dict) or "state" not in d:
            continue
        state = d.get("state") or {}
        case = state.get("case_id") or d.get("case")
        if case:
            out[case] = {
                "session": d.get("session") or state.get("session_id"),
                "state": state,
                "threads": d.get("threads") or {},
                "_src": f.name,
            }
    return out


def session_ids(trace_path) -> list[str]:
    """Session ids from trace events, else from the sibling log (`runs/x/<ts>/trace.jsonl` -> `runs/x.log`)."""
    ids = []
    trace_path = Path(trace_path)
    for ev in load_trace(trace_path):
        for k in ("session", "session_id"):
            if isinstance(ev.get(k), str) and ev[k] not in ids:
                ids.append(ev[k])
    if ids:
        return ids
    run = trace_path.parent
    for log in (run.parent.with_suffix(".log"), run / "run.log", run.with_suffix(".log")):
        if log.is_file():
            for m in SESSION_RE.finditer(log.read_text(encoding="utf-8", errors="replace")):
                if m.group(1) not in ids:
                    ids.append(m.group(1))
            if ids:
                break
    return ids


def _num(x):
    return x if isinstance(x, int | float) and not isinstance(x, bool) else None


def _decision(ev) -> dict:
    keep = ("kind", "supplier", "terms", "c", "c_alt", "reason", "sheet", "claims", "refs", "fallback", "latency_s")
    d = {k: ev[k] for k in keep if k in ev}
    for k in GUARD_KEYS:
        if k in ev:
            d["guard"] = ev[k]
    d["t"], d["src"] = ev.get("t"), ev["_src"]
    return d


def _case_summary(case_id, events, hosted) -> dict:
    decisions = [_decision(e) for e in events if e.get("event") == "decision"]
    results = [e for e in events if e.get("event") == "result"]
    guards = [
        {"src": e["_src"], **{k: v for k, v in e.items() if k not in ("t", "event", "case", "_src")}}
        for e in events
        if e.get("event") == "guard"
    ]
    guards += [
        {"src": d["src"], "kind": d["kind"], "supplier": d.get("supplier"), "outcome": d["guard"]}
        for d in decisions
        if "guard" in d
    ]
    claims = [
        {"src": d["src"], "supplier": d.get("supplier"), "claims": d.get("claims") or d.get("refs")}
        for d in decisions
        if d.get("claims") or d.get("refs")
    ]
    claims += [
        {"src": e["_src"], "supplier": e.get("supplier"), "claims": e.get("claims")}
        for e in events
        if e.get("event") == "evidence"
    ]
    offers = Counter(d.get("supplier") for d in decisions if d.get("kind") == "offer")
    s = {
        "case": case_id,
        "score": None,
        "deal": None,
        "supplier": None,
        "terms": None,
        "c_open": None,
        "c_deal": None,
        "c_best": None,
        "c_alt": next((d["c_alt"] for d in reversed(decisions) if _num(d.get("c_alt")) is not None), None),
        "gap": None,
        "components": None,
        "components_src": None,
        "must_haves_ok": None,
        "rounds": max(offers.values(), default=0),
        "offers_per_supplier": dict(offers),
        "decision_counts": dict(Counter(d.get("kind") for d in decisions)),
        "decisions": decisions,
        "guards": guards,
        "claims_used": claims,
        "fallbacks": sum(1 for d in decisions if d.get("fallback")),
        "error": None,
        "timeouts": None,
        "session": next(
            (
                e.get("session") or e.get("session_id")
                for e in events
                if isinstance(e.get("session") or e.get("session_id"), str)
            ),
            None,
        ),
        "replay_url": None,
        "result_src": None,
        "duration_s": None,
    }
    times = [e["t"] for e in events if _num(e.get("t")) is not None]
    if len(times) > 1:
        s["duration_s"] = round(max(times) - min(times), 1)
    if results:
        r = results[-1]
        s["result_src"] = r["_src"]
        row = r.get("full") if isinstance(r.get("full"), dict) else r.get("result")
        if isinstance(row, dict):
            for k in ("score", "deal", "terms", "c_open", "c_deal", "c_best", "must_haves_ok"):
                if k in row:
                    s[k] = row[k]
            s["supplier"] = row.get("supplier_id")
            if isinstance(row.get("thread_timeouts"), dict) and row["thread_timeouts"]:
                s["timeouts"] = sum(row["thread_timeouts"].values())
            if row.get("score") is None or not isinstance(row.get("deal"), bool):
                s["error"] = "incomplete result"
            if isinstance(row.get("cost_breakdown"), dict):
                s["components"], s["components_src"] = row["cost_breakdown"], r["_src"]
        else:
            s["error"] = str(row)
    h = hosted.get(case_id)
    if h:
        st = h["state"]
        res = st.get("result") or {}
        s["session"], s["replay_url"] = h.get("session") or s["session"], st.get("replay_url")
        if isinstance(st.get("rounds"), int):
            s["rounds"] = st["rounds"]
        for k in ("score", "deal", "terms", "c_open", "c_deal", "c_best", "c_alt", "must_haves_ok"):
            if s.get(k) is None and res.get(k) is not None:
                s[k] = res[k]
        if s["supplier"] is None:
            s["supplier"] = res.get("supplier_id")
        if s["components"] is None and isinstance(res.get("cost_breakdown"), dict):
            s["components"], s["components_src"] = res["cost_breakdown"], h["_src"]
        if h["threads"] and all("timeouts" in t for t in h["threads"].values()):
            s["timeouts"] = sum(len(t.get("timeouts") or []) for t in h["threads"].values())
    if not results and not h:
        s["error"] = "missing result"
    if s["error"] and "timeout" in s["error"].lower():
        s["timeouts"] = max(s["timeouts"] or 0, 1)
    if _num(s["c_deal"]) is not None and _num(s["c_best"]) is not None:
        s["gap"] = round(s["c_deal"] - s["c_best"], 2)
    return s


def summarise(run_dir) -> dict:
    """Per case: score, deal terms, C (open/deal/best/alt, components when the arena gave them),
    rounds, decisions, guard outcomes, claims used. Aggregate: mean/min score, worst case,
    deals, must-have breaks, failures, timeouts, fallbacks."""
    run_dir = Path(run_dir)
    traces = find_traces(run_dir)
    by_case: dict[str, tuple[str, list]] = {}  # key (case, or case#n for repeats) -> (case, events)
    runs, sessions = [], []
    for tr in traces:
        events = load_trace(tr)
        runs += [{k: v for k, v in e.items() if k != "event"} for e in events if e.get("event") == "run"]
        sessions += [x for x in session_ids(tr) if x not in sessions]
        for case in dict.fromkeys(e["case"] for e in events if e.get("case")):
            key, n = case, 2
            while key in by_case:
                key, n = f"{case}#{n}", n + 1
            by_case[key] = (case, [e for e in events if e.get("case") == case])
    hosted = {}
    for d in {run_dir} | {t.parent for t in traces}:
        hosted.update(load_hosted(d))
    cases = {key: _case_summary(case, events, hosted) for key, (case, events) in by_case.items()}
    for case_id in hosted:
        if case_id not in cases:
            cases[case_id] = _case_summary(case_id, [], hosted)
    single = [c for c in cases.values() if c["session"] is None]
    if len(sessions) == 1 and len(single) == 1:
        single[0]["session"] = sessions[0]
    for c in cases.values():
        if c["session"] and not c["replay_url"]:
            c["replay_url"] = f"/replay/{c['session']}"
    scored = {k: c["score"] for k, c in cases.items() if _num(c["score"]) is not None}
    worst = min(scored, key=scored.get) if scored else None
    agg = {
        "n_cases": len(cases),
        "n_scored": len(scored),
        "mean": statistics.mean(scored.values()) if scored else None,
        "min": scored[worst] if worst else None,
        "worst_case": worst,
        "deals": sum(1 for c in cases.values() if c["deal"] is True),
        "no_deals": sum(1 for c in cases.values() if c["deal"] is False),
        "must_have_breaks": sum(1 for c in cases.values() if c["must_haves_ok"] is False),
        "failures": sorted(k for k, c in cases.items() if c["error"]),
        "timeouts": sum(c["timeouts"] or 0 for c in cases.values()),
        "timeouts_unknown_cases": sum(c["timeouts"] is None for c in cases.values()),
        "decisions": sum(len(c["decisions"]) for c in cases.values()),
        "fallbacks": sum(c["fallbacks"] for c in cases.values()),
    }
    return {
        "run_dir": str(run_dir),
        "traces": [str(t) for t in traces],
        "runs": runs,
        "sessions": sessions,
        "cases": cases,
        "aggregate": agg,
    }


def fmt(x, digits=2) -> str:
    if x is None:
        return "-"
    if isinstance(x, float):
        if math.isinf(x):
            return "∞"
        return f"{x:,.{digits}f}"
    return str(x)


def _pct(x) -> str:
    return "-" if _num(x) is None else f"{100 * x:.1f}"


def _terms(t) -> str:
    if not isinstance(t, dict):
        return "-"
    return ", ".join(f"{k}={v}" for k, v in t.items() if v not in (None, 0.0) or k == "unit_price")


def to_markdown(summary: dict) -> str:
    a = summary["aggregate"]
    lines = [
        f"### Run `{summary['run_dir']}`",
        "",
        f"- Cases {a['n_scored']}/{a['n_cases']} scored; mean {_pct(a['mean'])}, min {_pct(a['min'])}"
        f" ({a['worst_case'] or '-'}); deals {a['deals']}, no deal {a['no_deals']}",
        f"- Must-have breaks {a['must_have_breaks']}, failures {len(a['failures'])}"
        f"{' ' + str(a['failures']) if a['failures'] else ''}, timeouts {a['timeouts']},"
        f" unknown timeout cases {a['timeouts_unknown_cases']}, fallbacks {a['fallbacks']}, decisions {a['decisions']}",
        "",
        "| Case | Score | Deal | Supplier | C deal | C best | Gap | C alt | Rounds | Decisions | Guards |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---|---:|",
    ]
    for key, c in summary["cases"].items():
        dec = " ".join(f"{k}:{v}" for k, v in sorted(c["decision_counts"].items()))
        lines.append(
            f"| {key} | {_pct(c['score'])} | {fmt(c['deal'])} | {c['supplier'] or '-'} | {fmt(c['c_deal'])} |"
            f" {fmt(c['c_best'])} | {fmt(c['gap'])} | {fmt(c['c_alt'])} | {c['rounds']} | {dec or '-'} |"
            f" {len(c['guards'])} |"
        )
    for key, c in summary["cases"].items():
        lines += ["", f"**{key}** terms: {_terms(c['terms'])}" + (f" (error: {c['error']})" if c["error"] else "")]
        if c["components"]:
            parts = ", ".join(f"{k} {fmt(v, 0)}" for k, v in c["components"].items() if v)
            lines.append(f"C components ({c['components_src']}): {parts}")
        if c["session"]:
            lines.append(f"session {c['session']}, replay {c['replay_url']}")
        for g in c["guards"]:
            lines.append(f"- guard {g.get('src')}: {json.dumps({k: v for k, v in g.items() if k != 'src'})}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="negotiator report")
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true", help="print the full summary as JSON")
    args = ap.parse_args(argv)
    if not Path(args.run_dir).exists():
        print(f"no such run: {args.run_dir}", file=sys.stderr)
        return 2
    s = summarise(args.run_dir)
    print(json.dumps(s, indent=2, default=str) if args.json else to_markdown(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
