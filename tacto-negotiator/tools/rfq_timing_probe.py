"""Send one offer to each D02 supplier concurrently, then close through one coordinator.

This measures hosted request timing; it is not a score-optimization experiment.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from arena_kit.cli import load_env
from arena_kit.cost import complete_offer, must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import RemoteTable, fetch_documents, standing
from sandbox_baseline import RecordedClient


def main():
    load_env()
    run = Path("experiments/runs") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-D02-concurrent-" + uuid4().hex[:6]
    )
    run.mkdir(parents=True)
    client = RecordedClient(run / "requests.jsonl")
    table = RemoteTable(client)
    case, threads = table.open("case:D02")
    (run / "opening.json").write_text(json.dumps({"case": case, "threads": threads}, indent=2))
    for events in threads.values():
        for message in events:
            fetch_documents(table, message)
    start = time.monotonic()
    print(f"D02 concurrent probe: {table.session_id}; logs {run}", flush=True)

    def send(supplier):
        _, terms = standing(threads[supplier])
        proposal = complete_offer(
            case,
            {
                **terms,
                "unit_price": round(terms["unit_price"] * 0.96, 2),
                "lead_time_days": 35,
                "payment_days": 60,
                "incoterm": "DAP",
            },
        )
        message = {
            "subject": case["title"],
            "body": "Thank you for your quotation. Please consider the attached complete package.",
            "term_sheets": [{"terms": proposal}],
        }
        sent = time.monotonic() - start
        try:
            reply = table.send(supplier, message)
            result = {
                "supplier": supplier,
                "request_start_s": sent,
                "request_end_s": time.monotonic() - start,
                "status": reply.get("status"),
            }
        except Exception as exc:
            result = {
                "supplier": supplier,
                "request_start_s": sent,
                "request_end_s": time.monotonic() - start,
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "status", None),
            }
        print(json.dumps(result), flush=True)
        return result

    with ThreadPoolExecutor(max_workers=len(threads)) as pool:
        timings = list(pool.map(send, threads))
    snapshot = client.session(table.session_id)
    remote_threads = {s: client.thread(table.session_id, s) for s in threads}
    (run / "after-round.json").write_text(json.dumps({"session": snapshot, "threads": remote_threads}, indent=2))
    for supplier, state in remote_threads.items():
        threads[supplier] = state["messages"]
        for msg in threads[supplier]:
            fetch_documents(table, msg)
    alternative = total_cost(case, case["buyer"]["alternative"]["terms"])
    candidates = []
    for supplier, state in remote_threads.items():
        if state.get("closed"):
            continue
        offer, terms = standing(threads[supplier])
        std = standard_terms(threads[supplier])
        if offer and must_haves_ok(case, terms, std):
            cost = total_cost(case, terms, std)
            if cost <= alternative:
                candidates.append((cost, supplier, offer))
    if snapshot.get("status") == "ended":
        outcome = snapshot.get("result")
    elif candidates:
        _, supplier, offer = min(candidates)
        outcome = table.close(supplier, {"action": {"type": "accept", "term_sheet_id": offer}})
    else:
        outcome = client.walk_away(table.session_id)
    report = {
        "session": table.session_id,
        "timings": timings,
        "threads": {
            s: {k: t.get(k) for k in ["round", "rounds", "timeouts", "closed"]} for s, t in remote_threads.items()
        },
        "outcome": outcome,
        "quota": client.me().get("practice"),
    }
    (run / "summary.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "session": table.session_id,
                "timings": timings,
                "thread_timeouts": {s: len(t.get("timeouts") or []) for s, t in remote_threads.items()},
                "score": (outcome or {}).get("score"),
                "quota": report["quota"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
