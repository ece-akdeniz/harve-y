"""Run one exploratory practice session: python tools/explore_run.py case:P08 strategy.txt [--max-rounds 5]

Writes experiments/breakthrough/runs/<name>-<sid>.json (events, result, trace, backoffice) and a
readable .txt transcript. Reads ARENA_URL/ARENA_API_KEY/LLM_* from the environment (.env)."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from arena_kit.client import ArenaClient  # noqa: E402
from arena_kit.play import RemoteTable, fetch_documents, live_threads  # noqa: E402

from negotiator.explore import Explorer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("explore_run")
PRACTICE_FLOOR = 100


def preflight(client, set_):
    if set_ != "practice":
        return
    practice = client.me().get("practice") or {}
    left = practice.get("left")
    if not isinstance(left, int):
        raise SystemExit("authoritative practice quota unavailable; refusing to open a session")
    if left <= PRACTICE_FLOOR:
        raise SystemExit(f"practice quota has {left} sessions left; floor is {PRACTICE_FLOOR}")

    open_sessions = []
    for session_set in ("practice", "sandbox"):
        rows = client.sessions(session_set)
        rows = rows.get("sessions", rows) if isinstance(rows, dict) else rows
        for row in rows:
            if row.get("status") == "ended" or row.get("ended") is True:
                continue
            if row.get("status") == "open" or row.get("ended") is False:
                open_sessions.append(row.get("session_id", "unknown"))
                continue
            state = client.session(row["session_id"])
            if state.get("status") != "ended" and state.get("ended") is not True:
                open_sessions.append(row["session_id"])
    if open_sessions:
        raise SystemExit(f"open arena session(s) exist: {', '.join(open_sessions)}")
    log.info("preflight ok: practice left=%s, open sessions=0", left)


def render(sess, bo):
    res = sess.get("result") or {}
    out = [
        f"SESSION {sess['session_id']} case={sess['case_id']} end={sess.get('end_reason')} rounds={sess.get('rounds')}",
        f"score={res.get('score')} c_open={res.get('c_open')} c_deal={res.get('c_deal')} c_alt={res.get('c_alt')} "
        f"supplier={res.get('supplier_id')}",
        f"terms={json.dumps(res.get('terms'))}",
        f"breakdown={json.dumps(res.get('cost_breakdown'))}",
        "",
    ]
    for t in res.get("trace", []):
        mv = t.get("move", {})
        out.append(f"--- round {t.get('round')} actor={t.get('actor')} status={mv.get('status')}")
        if mv.get("body"):
            out.append(mv["body"])
        if mv.get("text"):
            out.append(mv["text"])
        for x in mv.get("term_sheets") or []:
            out.append(f"  TS: {json.dumps(x.get('terms'))}")
        if mv.get("terms") and t.get("actor") != "buyer":
            out.append(f"  SUPPLIER OFFER {mv.get('offer_id')}: {json.dumps(mv.get('terms'))}")
            for a in mv.get("alternatives") or []:
                out.append(f"  ALT {a.get('offer_id')}: {json.dumps(a.get('terms'))}")
        if mv.get("refs"):
            out.append(f"  REFS: {mv['refs']}")
        if mv.get("claim_results"):
            out.append(f"  CLAIMS: {mv['claim_results']}")
        if mv.get("action"):
            out.append(f"  ACTION: {mv['action']}")
        if t.get("reasons"):
            out.append(f"  REASONS: {json.dumps(t['reasons'], ensure_ascii=False)}")
        out.append("")
    out.append("=== BACKOFFICE ===")
    for b in bo if isinstance(bo, list) else [bo]:
        if isinstance(b, dict):
            out.append(f"r{b.get('round')} {b.get('from')}->{b.get('to')}: {b.get('text')}")
        else:
            out.append(str(b))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    ap.add_argument("strategy_file")
    ap.add_argument("--name", default="explore")
    ap.add_argument("--max-rounds", type=int, default=5)
    ap.add_argument("--set", default="practice")
    args = ap.parse_args()
    strategy = Path(args.strategy_file).read_text()
    out_dir = Path("experiments/breakthrough/runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = ArenaClient()
    preflight(client, args.set)
    table = RemoteTable(client)
    case, threads = table.open(args.case_id)
    sid = table.session_id
    log.info("session %s", sid)
    agent = Explorer(
        strategy=strategy, max_rounds=args.max_rounds, log_path=str(out_dir / f"{args.name}-{sid}.events.jsonl")
    )
    for ev in threads.values():
        for m in ev:
            fetch_documents(table, m)
    result = None
    while live_threads(threads):
        t0 = time.monotonic()
        decision = agent.decide(case, threads)
        took = time.monotonic() - t0
        s, msg = decision["supplier_id"], decision["message"]
        log.info(
            "decide %.1fs -> %s %s", took, s, msg.get("action") or [t["terms"] for t in msg.get("term_sheets", [])]
        )
        if msg.get("action"):
            result = table.close(s, msg)
            break
        reply = table.send(s, msg)
        if "result" in reply:
            result = reply["result"]
            break
        threads[s] += [{**msg, "from": "buyer"}, fetch_documents(table, reply)]
        log.info("%s %s %s", s, reply.get("status"), [t["terms"] for t in reply.get("term_sheets") or []])
    if result is None:
        result = table.result()
    log.info("RESULT score=%s deal=%s", result.get("score"), result.get("deal"))
    time.sleep(1.0)
    sess = client.session(sid)
    try:
        bo = client._call("GET", f"/sessions/{sid}/backoffice")
    except Exception as e:  # noqa: BLE001
        bo = {"error": str(e)}
    (out_dir / f"{args.name}-{sid}.json").write_text(
        json.dumps(
            {"session": sess, "backoffice": bo, "result": result, "strategy": strategy, "events": agent.events},
            indent=1,
            default=str,
        )
    )
    (out_dir / f"{args.name}-{sid}.txt").write_text(render(sess, bo))
    print(
        json.dumps(
            {
                "session_id": sid,
                "score": result.get("score"),
                "c_deal": result.get("c_deal"),
                "terms": result.get("terms"),
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
