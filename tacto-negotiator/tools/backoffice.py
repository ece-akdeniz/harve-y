"""Post-session supplier back-office digest (READ only; opens nothing, sends nothing).

    uv run --locked python tools/backoffice.py SESSION_ID... [--out experiments/backoffice/]
    uv run --locked python tools/backoffice.py --cases P05,P18 SESSION_ID...   # keep only these cases
    uv run --locked python tools/backoffice.py --force SESSION_ID             # refetch saved sessions

For each of OUR OWN past sessions this fetches `GET /v1/sessions/{sid}` (state, result, trace) and
`GET /v1/sessions/{sid}/backoffice` (the supplier's roles talking internally after the case ended:
who asked whom, approvals, documents attached), saves both raw under
`<out>/<case>-<sid>.json`, writes a readable digest next to it (`.txt`) and prints that digest:
per supplier thread, round by round, our offer -> the supplier's offer and status -> its stated
reasons -> the back-office entries (from -> to, kind, figure/limit if any, verbatim text).

404/403 on the back office (older sessions, or a case not yet ended) is recorded in the JSON as
`backoffice_error` and the digest still shows the trace. Calls are spaced by `--sleep` (0.5 s).
Spectator endpoints are never touched (`negotiator.client.assert_allowed`). This is offline,
pre-session intelligence for humans; nothing here is read by the agent at runtime.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from negotiator.client import assert_allowed  # noqa: E402

HOSTED = "https://arena.tacto.ai"
TERM_KEYS = ("unit_price", "payment_days", "lead_time_days", "contract_months", "volume_per_year",
             "index_clause", "incoterm", "tooling_eur", "ppm_commitment", "chargeback_eur_per_complaint",
             "effective_date")
FIGURE_RE = re.compile(r"(?:EUR|€)\s?\d[\d.,]*|\d[\d.,]*\s?(?:%|EUR|€|days?|d\b|months?|ppm)", re.I)
APPROVAL_WORDS = ("approv", "sign-off", "sign off", "clarify internally", "check internally", "ask ",
                  "need to ask", "escalat", "committee", "boss", "management", "can we", "may we", "ok to")
DECISION_WORDS = ("my call", "decision", "approved", "declined", "rejected", "go ahead", "agreed", "no.",
                  "yes.", "granted", "refuse")


def load_env() -> None:
    """ARENA_URL / ARENA_API_KEY from the environment, else from `.env` next to the repo root."""
    try:
        from arena_kit.cli import load_env as kit_load_env

        kit_load_env(str(ROOT / ".env"))
        return
    except Exception:  # noqa: BLE001 - the kit is optional; fall back to a tiny parser
        pass
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Fetcher:
    """Plain httpx GETs with the key header, polite spacing and a spectator-endpoint guard."""

    def __init__(self, base_url: str, api_key: str, sleep_s: float):
        self.http = httpx.Client(base_url=base_url.rstrip("/"), headers={"X-API-Key": api_key}, timeout=60.0)
        self.sleep_s, self._last = sleep_s, 0.0

    def get(self, path: str) -> tuple[int, object]:
        assert_allowed(path)
        wait = self._last + self.sleep_s - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            try:
                r = self.http.get(path)
            except httpx.TransportError as e:
                if attempt == 2:
                    return 0, {"detail": repr(e)}
                time.sleep(1.0 * 2**attempt)
                continue
            self._last = time.monotonic()
            if r.status_code == 429 or r.status_code >= 500:
                retry = r.headers.get("Retry-After", "")
                time.sleep(float(retry) if retry.isdigit() else 1.0 * 2**attempt)
                continue
            break
        try:
            body = r.json()
        except ValueError:
            body = {"detail": r.text}
        return r.status_code, body

    def close(self) -> None:
        self.http.close()


def short_case(case_id: str | None) -> str:
    return (case_id or "unknown").removeprefix("case:")


def fmt_terms(terms: dict | None) -> str:
    if not terms:
        return "-"
    parts = []
    for k in TERM_KEYS:
        if k not in terms:
            continue
        v = terms[k]
        if k == "unit_price":
            parts.append(f"EUR {v}")
        elif k == "payment_days":
            parts.append(f"{v}d pay")
        elif k == "lead_time_days":
            parts.append(f"{v}d lead")
        elif k == "contract_months":
            parts.append(f"{v}m")
        elif k == "index_clause":
            clause = f"{v.get('series')} db{v.get('deadband_pct')}" if isinstance(v, dict) else "none"
            parts.append(f"clause {clause}")
        elif k == "volume_per_year":
            parts.append(f"vol {v}")
        else:
            parts.append(f"{k}={v}")
    return " / ".join(parts)


def classify(text: str) -> str:
    low = text.lower()
    if "attached" in low:
        return "attachment"
    if low.startswith("my call") or any(w in low for w in DECISION_WORDS):
        return "decision"
    if any(w in low for w in APPROVAL_WORDS) or "?" in text:
        return "approval request"
    if low.startswith("read the buyer"):
        return "reading"
    return "reason"


def figures(text: str) -> str:
    found = [m.group(0).strip() for m in FIGURE_RE.finditer(text)]
    return ", ".join(dict.fromkeys(found)) if found else ""


def entries_by_supplier(backoffice) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    items = backoffice if isinstance(backoffice, list) else (backoffice or {}).get("entries", [])
    for e in items:
        if not isinstance(e, dict):
            continue
        out.setdefault(e.get("supplier_id") or "?", []).append(e)
    return out


def moves_by_supplier(session: dict) -> dict[str, list[dict]]:
    """Trace moves grouped per supplier thread; buyer moves are attached to the thread they went to."""
    result = session.get("result") or {}
    trace = result.get("trace") or session.get("trace") or []
    threads = list((session.get("threads") or {}).keys())
    out: dict[str, list[dict]] = {t: [] for t in threads}
    for t in trace:
        actor = t.get("actor") or "?"
        move = t.get("move") or {}
        sup = actor
        if actor == "buyer":
            sup = move.get("supplier_id") or move.get("to") or (threads[0] if len(threads) == 1 else None)
            if sup is None:  # several threads: fall back to the offer id's supplier
                oid = move.get("offer_id") or move.get("term_sheet_id") or ""
                m = re.match(r"offer:(\d+)", str(oid))
                sup = f"sup:{m.group(1)}" if m else "buyer(unassigned)"
        out.setdefault(sup, []).append(t)
    return out


def claim_line(move: dict) -> str:
    claims = list(move.get("claims") or []) + list((move.get("interpreted") or {}).get("claims") or [])
    bits = []
    for c in claims:
        res = c.get("result") or c.get("status") or c.get("verdict")
        asserted = c.get("asserted")
        bits.append(f"{c.get('type')}{'[' + str(res) + ']' if res else ''} {','.join(c.get('refs') or [])}"
                    + (f" {json.dumps(asserted)}" if asserted else ""))
    return "; ".join(bits)


def buyer_head(move: dict) -> str:
    kind = move.get("type") or "message"
    sheets = move.get("term_sheets") or []
    if sheets:
        terms = " | ".join(fmt_terms((s or {}).get("terms")) for s in sheets)
    elif move.get("terms"):
        terms = fmt_terms(move.get("terms"))
    else:
        terms = "(no term sheet)"
    head = f"    BUYER {kind}: {terms}"
    if move.get("offer_id") or move.get("accept"):
        head += f" accept={move.get('offer_id') or move.get('accept')}"
    if move.get("refs"):
        head += f" refs={','.join(move['refs'])}"
    return head


def squash(text: str, limit: int = 600) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def digest(record: dict) -> str:
    s = record["session"]
    res = s.get("result") or {}
    lines = []
    lines.append(f"=== {short_case(s.get('case_id'))} session {s.get('session_id')} set={s.get('set')} "
                 f"status={s.get('status')} end={s.get('end_reason')} rounds={s.get('rounds')}")
    if res:
        lines.append(f"    result: deal={res.get('deal')} score={res.get('score')} with {res.get('supplier_id')} "
                     f"{fmt_terms(res.get('terms'))} | c_open={res.get('c_open')} c_deal={res.get('c_deal')} "
                     f"c_best={res.get('c_best')} must_haves_ok={res.get('must_haves_ok')}")
    err = record.get("backoffice_error")
    if err:
        lines.append(f"    back office: NOT AVAILABLE ({err.get('status')}: {str(err.get('detail'))[:120]})")
    bo = entries_by_supplier(record.get("backoffice"))
    moves = moves_by_supplier(s)
    suppliers = list(dict.fromkeys([*moves.keys(), *bo.keys()]))
    for sup in suppliers:
        if sup == "buyer(unassigned)":
            continue
        name = next((e.get("supplier") for e in bo.get(sup, []) if e.get("supplier")), "")
        thread = (s.get("threads") or {}).get(sup) or {}
        lines.append(f"--- {sup} {name} thread status={thread.get('status')} closed={thread.get('closed')}")
        rounds = sorted({t.get("round", 0) for t in moves.get(sup, [])} | {e.get("round", 0) for e in bo.get(sup, [])})
        for r in rounds:
            lines.append(f"  round {r}")
            for t in [m for m in moves.get(sup, []) if m.get("round", 0) == r]:
                move = t.get("move") or {}
                if t.get("actor") == "buyer":
                    lines.append(buyer_head(move))
                    cl = claim_line(move)
                    if cl:
                        lines.append(f"      claims: {cl}")
                    if move.get("body"):
                        lines.append(f"      said: {squash(move['body'])}")
                    continue
                status = move.get("status")
                head = f"    SUPPLIER: {fmt_terms(move.get('terms'))}" + (f" [{status}]" if status else "")
                if move.get("alternatives"):
                    head += " +alt " + " | ".join(fmt_terms(a.get("terms") if isinstance(a, dict) else a)
                                                    for a in move["alternatives"])
                lines.append(head)
                cl = claim_line(move)
                if cl:
                    lines.append(f"      claims: {cl}")
                for reason in t.get("reasons") or []:
                    lines.append(f"      reason: {reason}")
            for e in [x for x in bo.get(sup, []) if x.get("round", 0) == r]:
                text = e.get("text") or ""
                fig = figures(text)
                lines.append(f"    BACKOFFICE {e.get('from')} -> {e.get('to')} ({classify(text)}"
                             f"{'; figures: ' + fig if fig else ''}): {text}")
        if sup in moves and sup not in bo and not err:
            lines.append("    (no back-office entries for this thread)")
    unassigned = moves.get("buyer(unassigned)")
    if unassigned:
        lines.append(f"--- {len(unassigned)} buyer moves could not be assigned to a thread")
    return "\n".join(lines)


def fetch_one(f: Fetcher, sid: str, keep_cases: set[str] | None) -> dict | None:
    status, session = f.get(f"/v1/sessions/{sid}")
    if status != 200:
        print(f"[{sid}] session GET failed: {status} {str(session)[:160]}", file=sys.stderr)
        return None
    case = short_case(session.get("case_id"))
    if keep_cases and case not in keep_cases:
        print(f"[{sid}] {case}: skipped (not in --cases)")
        return None
    record = {
        "session_id": sid,
        "case_id": session.get("case_id"),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "session": session,
        "backoffice": None,
        "backoffice_error": None,
    }
    status, bo = f.get(f"/v1/sessions/{sid}/backoffice")
    if status == 200:
        record["backoffice"] = bo
    else:
        record["backoffice_error"] = {"status": status, "detail": bo.get("detail") if isinstance(bo, dict) else bo}
    return record


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sessions", nargs="+", help="session ids (ours)")
    ap.add_argument("--out", default="experiments/backoffice", help="directory for <case>-<sid>.json/.txt")
    ap.add_argument("--cases", default="", help="comma list of case ids to keep (e.g. P05,P18); others skipped")
    ap.add_argument("--sleep", type=float, default=0.5, help="seconds between calls")
    ap.add_argument("--force", action="store_true", help="refetch sessions already saved under --out")
    ap.add_argument("--quiet", action="store_true", help="do not print the digests, only a summary")
    args = ap.parse_args(argv)

    load_env()
    url = os.environ.get("ARENA_URL") or HOSTED
    key = os.environ.get("ARENA_API_KEY")
    if not key:
        print("ARENA_API_KEY is not set (export it or put it in .env)", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    keep = {c.strip().removeprefix("case:") for c in args.cases.split(",") if c.strip()} or None

    sessions = list(dict.fromkeys(s.strip() for s in args.sessions if s.strip()))
    saved = {p.name.split("-", 1)[1].removesuffix(".json"): p for p in out.glob("*-*.json")}
    f = Fetcher(url, key, args.sleep)
    counts = {"saved": 0, "backoffice": 0, "no_backoffice": 0, "skipped": 0, "failed": 0, "cached": 0}
    try:
        for sid in sessions:
            if not args.force and sid in saved:
                record = json.loads(saved[sid].read_text())
                counts["cached"] += 1
            else:
                record = fetch_one(f, sid, keep)
                if record is None:
                    counts["skipped" if keep else "failed"] += 1
                    continue
                stem = f"{short_case(record['case_id'])}-{sid}"
                (out / f"{stem}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
                counts["saved"] += 1
            counts["backoffice" if record.get("backoffice") is not None else "no_backoffice"] += 1
            text = digest(record)
            (out / f"{short_case(record['case_id'])}-{sid}.txt").write_text(text)
            if not args.quiet:
                print(text)
                print()
    finally:
        f.close()
    print(f"done: {counts} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
