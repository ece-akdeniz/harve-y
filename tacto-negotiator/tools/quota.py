"""Practice quota ledger: `arena me` used/left plus the practice sessions our local runs opened.

    uv run --locked python tools/quota.py                 # ledger + quota
    uv run --locked python tools/quota.py --planned 12    # warn if left <= 46 reserve + 12
    uv run --locked python tools/quota.py --offline       # local runs only, no arena call

Reads /v1/me and /v1/sessions?set=practice (read-only; opens nothing). Local sessions come from
experiments/runs/**/trace.jsonl runs against the hosted arena with practice cases (case:P..),
plus tools/sandbox_baseline.py dumps. Exit code 1 when the reserve would be touched.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from negotiator.report import load_hosted, load_trace, session_ids  # noqa: E402

RESERVE = 46
HOSTED = "https://arena.tacto.ai"


def is_local(url) -> bool:
    return any(h in (url or "") for h in ("127.0.0.1", "localhost", "0.0.0.0"))


def set_of(case_id: str) -> str:
    """Hosted case prefixes: P practice, D sandbox, F/W final; S is the local simulator."""
    tag = case_id.removeprefix("case:")[:1]
    return {"P": "practice", "D": "sandbox", "S": "sim"}.get(tag, "other")


def local_ledger(runs_dir: Path) -> list[dict]:
    rows = []
    for tr in sorted(runs_dir.rglob("trace.jsonl")):
        events = load_trace(tr)
        arena = next((e.get("arena") for e in events if e.get("event") == "run"), None)
        if is_local(arena):
            continue
        cases = list(dict.fromkeys(e["case"] for e in events if e.get("case")))
        results = {e["case"]: e.get("result") for e in events if e.get("event") == "result"}
        sids = session_ids(tr)
        t0 = next((e["t"] for e in events if isinstance(e.get("t"), int | float)), tr.stat().st_mtime)
        for i, case in enumerate(cases):
            res = results.get(case)
            rows.append({
                "when": datetime.fromtimestamp(t0).strftime("%m-%d %H:%M"),
                "set": set_of(case),
                "case": case,
                "session": sids[i] if len(sids) == len(cases) else (sids[0] if len(sids) == 1 else "?"),
                "score": res.get("score") if isinstance(res, dict) else None,
                "status": "error" if isinstance(res, str) else ("done" if res else "no result"),
                "source": str(tr.relative_to(ROOT) if tr.is_relative_to(ROOT) else tr),
            })
    seen = {r["session"] for r in rows}
    for d in sorted({p.parent for p in runs_dir.rglob("*.json")}):
        for case, h in load_hosted(d).items():
            if h.get("session") in seen or (d / "trace.jsonl").exists():
                continue
            res = (h["state"].get("result") or {})
            rows.append({
                "when": datetime.fromtimestamp((d / h["_src"]).stat().st_mtime).strftime("%m-%d %H:%M"),
                "set": h["state"].get("set") or set_of(case),
                "case": case,
                "session": h.get("session"),
                "score": res.get("score"),
                "status": h["state"].get("status") or "?",
                "source": str((d / h["_src"]).relative_to(ROOT)),
            })
    return rows


def table(rows, cols) -> str:
    def cell(v):
        return f"{100 * v:.1f}" if isinstance(v, float) else ("-" if v is None else str(v))

    widths = {c: max(len(c), *(len(cell(r.get(c))) for r in rows)) for c in cols}
    lines = ["  ".join(c.ljust(widths[c]) for c in cols)]
    lines += ["  ".join(cell(r.get(c)).ljust(widths[c]) for c in cols) for r in rows]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--planned", type=int, default=0, help="practice sessions you are about to open")
    ap.add_argument("--offline", action="store_true", help="skip the arena calls")
    ap.add_argument("--all", action="store_true", help="also list sandbox/other hosted sessions")
    ap.add_argument("--runs", default=str(ROOT / "experiments/runs"))
    args = ap.parse_args(argv)

    rows = local_ledger(Path(args.runs))
    shown = rows if args.all else [r for r in rows if r["set"] == "practice"]
    print(f"Local hosted sessions ({'all sets' if args.all else 'practice'}) from {args.runs}:")
    print(table(shown, ["when", "set", "case", "session", "score", "status", "source"]) if shown else "  none")
    print(f"local practice sessions: {sum(r['set'] == 'practice' for r in rows)}"
          f" (sandbox {sum(r['set'] == 'sandbox' for r in rows)}, not counted)")

    if args.offline:
        return 0
    from arena_kit.cli import load_env
    from arena_kit.client import ArenaClient, ArenaError

    os.chdir(ROOT)
    load_env()
    url = os.environ.get("ARENA_URL") or HOSTED
    if is_local(url):
        url = HOSTED
    client = ArenaClient(base_url=url)
    try:
        me = client.me()
    except ArenaError as e:
        print(f"arena me failed: {e}", file=sys.stderr)
        return 2
    p = me.get("practice") or {}
    print(f"\narena me ({url}): team {me.get('team_name')} status {me.get('status')}")
    print(f"practice used {p.get('used')} / limit {p.get('limit')}, left {p.get('left')},"
          f" resets_at {p.get('resets_at')}")
    try:
        server = client.sessions("practice")
        server = server.get("sessions", server) if isinstance(server, dict) else server
        print(f"server practice sessions listed: {len(server)}")
        known = {r["session"] for r in rows}
        missing = [s for s in server if isinstance(s, dict) and s.get("session_id") not in known]
        if missing:
            print(f"  not in local traces ({len(missing)}):")
            for s in missing:
                print("  ", json.dumps({k: s.get(k) for k in ("session_id", "case_id", "status", "score")}))
    except ArenaError as e:
        print(f"(sessions list unavailable: {e})")
    left = p.get("left")
    if left is None:
        return 0
    floor = RESERVE + args.planned
    if left <= floor:
        print(f"WARNING: practice left {left} <= reserve {RESERVE} + planned {args.planned} = {floor}."
              " Do not open these sessions without a team decision.")
        return 1
    print(f"ok: after {args.planned} planned, {left - args.planned} left (reserve {RESERVE}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
