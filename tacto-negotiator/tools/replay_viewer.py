"""Static, offline replay of a run: one HTML file per run directory, built from trace.jsonl.

Per case and supplier thread: supplier messages (status, every term sheet, claim results) when
hosted session data is available, our decisions (kind, terms, C vs alternative, reason, claims,
guard), then the result and C components. Every figure carries its source (trace line, hosted
message id, arena result). No network unless --fetch/--session is given.

    uv run --locked python tools/replay_viewer.py experiments/runs/practice_P01
    uv run --locked python tools/replay_viewer.py experiments/runs/practice_P01 --fetch   # read-only arena GETs
    uv run --locked python tools/replay_viewer.py RUN --session <sid> --out /tmp/replay.html

--fetch stores `hosted-<sid>.json` next to the trace (state + threads; no practice quota used).
Arena "reasons" are spectator data: use for analysis and the pitch, never as agent input.
"""

import argparse
import html
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from negotiator.report import fmt, load_hosted, summarise  # noqa: E402

DEFAULT_ARENA = "https://arena.tacto.ai"

CSS = """
body{font:14px/1.45 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:0;background:#f6f6f3;color:#1d1d1b}
header{background:#1d1d1b;color:#fff;padding:14px 24px}header h1{margin:0;font-size:18px}
header .meta{color:#bbb;font-size:12px}main{max-width:1100px;margin:0 auto;padding:16px 24px}
nav a{margin-right:12px}section.case{background:#fff;border:1px solid #ddd;border-radius:6px;margin:18px 0;
padding:14px 18px}h2{margin:4px 0 8px;font-size:17px}h3{margin:16px 0 6px;font-size:15px;border-bottom:1px solid #eee}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:8px 0}.kpi{background:#f0f0ea;border-radius:4px;padding:6px 10px}
.kpi b{display:block;font-size:16px}.row{display:flex;margin:8px 0}.row.buyer{justify-content:flex-end}
.msg{width:72%;border:1px solid #ddd;border-radius:6px;padding:8px 10px;background:#fbfbf8}
.buyer .msg{background:#eef4ff;border-color:#c9d8f5}.msg .hd{font-size:12px;color:#555;margin-bottom:4px}
.tag{display:inline-block;border-radius:3px;padding:0 6px;font-size:11px;font-weight:600;background:#ddd;
margin-right:4px}
.open{background:#e8eef9}.final_offer{background:#fde6c8}.agreed,.accept{background:#cdeccf}.walk_away,.walked{background:#f6c9c9}
.offer{background:#d7e3fb}.guard{background:#efe0fb}table{border-collapse:collapse;margin:4px 0}
td,th{border:1px solid #e3e3e3;padding:2px 6px;font-size:12px;text-align:left}td.n{text-align:right}
.src{font-size:10px;color:#888;font-family:ui-monospace,Menlo,monospace}.reason{font-style:italic}
details{margin-top:4px}pre{white-space:pre-wrap;font-size:12px;margin:4px 0}.spect{color:#7a5b00}
.bad{color:#a01818}.good{color:#176b1d}
"""


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def src(s) -> str:
    return f'<span class="src">[{esc(s)}]</span>' if s else ""


def terms_table(terms) -> str:
    if not isinstance(terms, dict) or not terms:
        return ""
    cells = "".join(f"<tr><th>{esc(k)}</th><td>{esc(json.dumps(v) if isinstance(v, dict) else v)}</td></tr>"
                    for k, v in terms.items())
    return f"<table>{cells}</table>"


def sheets_html(sheets, alternatives=()) -> str:
    out = []
    for s in list(sheets or []) + list(alternatives or []):
        sid = s.get("term_sheet_id") or s.get("offer_id")
        out.append(f'<div><span class="tag">{esc(sid or "sheet")}</span>{terms_table(s.get("terms"))}</div>')
    return "".join(out)


def money(x) -> str:
    return fmt(x) if x is not None else "-"


def decision_html(d) -> str:
    kind = d.get("kind", "?")
    c, alt = d.get("c"), d.get("c_alt")
    vs = ""
    if isinstance(c, int | float) and isinstance(alt, int | float) and not math.isinf(alt):
        margin = alt - c
        vs = f' <span class="{"good" if margin > 0 else "bad"}">({money(margin)} below alternative)</span>'
    parts = [
        f'<div class="hd"><span class="tag {esc(kind)}">our {esc(kind)}</span> to {esc(d.get("supplier"))}'
        f' {src(d.get("src"))}</div>',
        terms_table(d.get("terms")),
        f"<div>C {money(c)} vs C alternative {money(alt)}{vs}</div>" if c is not None or alt is not None else "",
        f'<div>sheet {esc(d["sheet"])}</div>' if d.get("sheet") else "",
        f'<div class="reason">reason: {esc(d.get("reason"))}</div>' if d.get("reason") else "",
    ]
    if d.get("claims") or d.get("refs"):
        parts.append(f"<div>claims used: {esc(json.dumps(d.get('claims') or d.get('refs'), ensure_ascii=False))}</div>")
    if "guard" in d:
        guard = esc(json.dumps(d["guard"], ensure_ascii=False))
        parts.append(f'<div><span class="tag guard">guard</span>{guard}</div>')
    if d.get("fallback"):
        parts.append(f"<div class='bad'>fallback: {esc(d['fallback'])}</div>")
    return "".join(parts)


def supplier_html(m, reasons=None) -> str:
    status = m.get("status") or ("action" if m.get("action") else "")
    parts = [
        f'<div class="hd"><span class="tag {esc(status)}">{esc(status or "message")}</span>'
        f'{esc(m.get("from_name") or m.get("from"))} {src(m.get("message_id") or "hosted thread")}</div>',
        sheets_html(m.get("term_sheets")),
    ]
    if m.get("claim_results"):
        parts.append(f"<div>claim results: {esc(json.dumps(m['claim_results'], ensure_ascii=False))}</div>")
    if m.get("refs"):
        parts.append(f"<div>refs: {esc(json.dumps(m['refs'], ensure_ascii=False))}</div>")
    if m.get("missing_fields"):
        parts.append(f"<div>missing fields: {esc(', '.join(m['missing_fields']))}</div>")
    if m.get("signals"):
        parts.append(f"<div class='src'>signals {esc(json.dumps(m['signals']))}</div>")
    if reasons:
        items = "".join(f"<li>{esc(r)}</li>" for r in reasons)
        parts.append(
            f'<details class="spect"><summary>arena reasons (spectator data)</summary><ul>{items}</ul></details>'
        )
    if m.get("body"):
        parts.append(f"<details><summary>message text</summary><pre>{esc(m['body'])}</pre></details>")
    return "".join(parts)


def buyer_msg_html(m) -> str:
    action = (m.get("action") or {}).get("type") if isinstance(m.get("action"), dict) else None
    parts = [f'<div class="hd"><span class="tag">sent</span>{esc(action or "message")} (hosted thread)</div>']
    if m.get("refs"):
        parts.append(f"<div>claims/refs sent: {esc(json.dumps(m['refs'], ensure_ascii=False))}</div>")
    if m.get("body"):
        parts.append(f"<details><summary>our text</summary><pre>{esc(m['body'])}</pre></details>")
    return "".join(parts)


def row(side, inner) -> str:
    return f'<div class="row {side}"><div class="msg">{inner}</div></div>'


def thread_html(supplier, decisions, thread, reasons) -> str:
    """Interleave hosted messages with our decisions: the k-th buyer message pairs with the k-th decision."""
    out, pending = [], list(decisions)
    sup_i = 0
    for m in (thread or {}).get("messages", []):
        if m.get("from") == "buyer":
            inner = decision_html(pending.pop(0)) if pending else ""
            out.append(row("buyer", inner + buyer_msg_html(m)))
        else:
            out.append(row("supplier", supplier_html(m, reasons[sup_i] if sup_i < len(reasons) else None)))
            sup_i += 1
    out += [row("buyer", decision_html(d)) for d in pending]
    if thread and thread.get("timeouts"):
        out.append(f"<div class='bad'>timeouts: {esc(json.dumps(thread['timeouts']))}</div>")
    return f"<h3>Thread {esc(supplier)}</h3>" + "".join(out)


def case_html(key, c, hosted, arena) -> str:
    state = (hosted or {}).get("state") or {}
    threads = (hosted or {}).get("threads") or {}
    reasons = {}
    for step in (state.get("result") or {}).get("trace") or []:
        if step.get("actor") != "buyer":
            reasons.setdefault(step["actor"], []).append(step.get("reasons") or [])
    suppliers = list(dict.fromkeys([d.get("supplier") for d in c["decisions"]] + list(threads)))
    replay = f"{arena}{c['replay_url']}" if c.get("replay_url") else None
    score = "-" if c["score"] is None else f"{100 * c['score']:.1f}"
    kpis = [
        ("score", score, c.get("result_src")),
        ("deal", fmt(c["deal"]), None),
        ("supplier", c["supplier"] or "-", None),
        ("C open", money(c["c_open"]), None),
        ("C deal", money(c["c_deal"]), None),
        ("C best", money(c["c_best"]), None),
        ("C deal − C best", money(c["gap"]), None),
        ("C alternative", money(c["c_alt"]), None),
        ("rounds", c["rounds"], None),
        ("timeouts", c["timeouts"], None),
    ]
    kp = "".join(f'<div class="kpi">{esc(k)}<b>{esc(v)}</b>{src(s)}</div>' for k, v, s in kpis)
    parts = [
        f'<section class="case" id="{esc(key)}"><h2>{esc(key)}</h2>',
        f"<div>session {esc(c['session'] or 'unknown')}"
        + (f' · <a href="{esc(replay)}">hosted replay</a>' if replay else "")
        + (f" · hosted data {src(hosted['_src'])}" if hosted else " · trace only (no hosted messages)")
        + "</div>",
        f'<div class="kpis">{kp}</div>',
    ]
    if c["error"]:
        parts.append(f"<div class='bad'>error: {esc(c['error'])}</div>")
    for s in suppliers:
        if s is None:
            continue
        ds = [d for d in c["decisions"] if d.get("supplier") == s]
        parts.append(thread_html(s, ds, threads.get(s), reasons.get(s, [])))
    parts.append(f"<h3>Result {src(c.get('result_src'))}</h3>")
    if c["terms"]:
        parts.append(f"<div>deal terms</div>{terms_table(c['terms'])}")
    if c["components"]:
        total = sum(v for v in c["components"].values() if isinstance(v, int | float)) or 1
        rows = "".join(
            f'<tr><th>{esc(k)}</th><td class="n">{money(v)}</td><td class="n">{100 * v / total:.1f}%</td></tr>'
            for k, v in c["components"].items() if v
        )
        parts.append(f"<div>C components {src(c['components_src'])}</div><table>{rows}</table>")
    if c["guards"]:
        items = "".join(f"<li>{esc(json.dumps(g, ensure_ascii=False))}</li>" for g in c["guards"])
        parts.append(f"<div>guard outcomes</div><ul>{items}</ul>")
    parts.append("</section>")
    return "".join(parts)


def render(run_dir, arena=DEFAULT_ARENA) -> str:
    s = summarise(run_dir)
    hosted = {}
    for d in {Path(run_dir)} | {Path(t).parent for t in s["traces"]}:
        hosted.update(load_hosted(d))
    a = s["aggregate"]
    run = s["runs"][0] if s["runs"] else {}
    mean = "-" if a["mean"] is None else f"{100 * a['mean']:.1f}"
    nav = " ".join(f'<a href="#{esc(k)}">{esc(k)}</a>' for k in s["cases"])
    body = "".join(case_html(k, c, hosted.get(k.split("#")[0]), arena) for k, c in s["cases"].items())
    traces = ", ".join(esc(t) for t in s["traces"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Replay {esc(s['run_dir'])}</title>
<style>{CSS}</style></head><body><header><h1>Replay · {esc(s['run_dir'])}</h1>
<div class="meta">agent {esc(run.get('agent'))} · cmd {esc(run.get('cmd'))} · arena {esc(run.get('arena'))} ·
mean {mean} over {a['n_scored']}/{a['n_cases']} · min {'-' if a['min'] is None else f"{100 * a['min']:.1f}"}
({esc(a['worst_case'])}) · failures {len(a['failures'])} · timeouts {a['timeouts']}</div>
<div class="meta">sources: {traces}</div></header><main><nav>{nav}</nav>{body}
<p class="src">Built offline from the trace (our decisions, result) and hosted session dumps (supplier
messages, arena cost breakdown). Arena reasons are spectator data.</p></main></body></html>
"""


def fetch(run_dir, sid) -> Path:
    from arena_kit.cli import load_env
    from arena_kit.client import ArenaClient

    load_env()
    os.environ.setdefault("ARENA_URL", DEFAULT_ARENA)
    client = ArenaClient()
    state = client.session(sid)
    threads = {s: client.thread(sid, s) for s in state.get("threads", {})}
    traces = sorted(Path(run_dir).rglob("trace.jsonl")) if Path(run_dir).is_dir() else [Path(run_dir)]
    target = (traces[0].parent if traces else Path(run_dir)) / f"hosted-{sid}.json"
    target.write_text(json.dumps({"session": sid, "state": state, "threads": threads}, indent=2, ensure_ascii=False))
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dirs", nargs="+", help="run directories (or trace.jsonl files)")
    ap.add_argument("--session", help="hosted session id to fetch for a single run")
    ap.add_argument("--fetch", action="store_true", help="fetch hosted data for detected sessions (read-only)")
    ap.add_argument("--out", help="output HTML (single run only); default <trace dir>/replay.html")
    ap.add_argument("--arena", default=os.environ.get("ARENA_URL") or DEFAULT_ARENA)
    args = ap.parse_args(argv)
    if args.out and len(args.run_dirs) > 1:
        ap.error("--out needs a single run")
    for rd in args.run_dirs:
        if not Path(rd).exists():
            print(f"skip {rd}: not found", file=sys.stderr)
            continue
        sids = [args.session] if args.session else (summarise(rd)["sessions"] if args.fetch else [])
        for sid in sids:
            have = list(Path(rd).rglob(f"hosted-{sid}.json")) if Path(rd).is_dir() else []
            if not have:
                print(f"fetched {fetch(rd, sid)}")
        traces = sorted(Path(rd).rglob("trace.jsonl")) if Path(rd).is_dir() else [Path(rd)]
        out = Path(args.out) if args.out else (traces[0].parent if len(traces) == 1 else Path(rd)) / "replay.html"
        out.write_text(render(rd, args.arena.rstrip("/")), encoding="utf-8")
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
