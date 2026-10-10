"""Local one-decision replay; never opens arena sessions or calls a model.

Run: uv run --locked python tools/replay_decisions.py --output experiments/local-decisions.json
Each prefix is independent. Do not replay future supplier replies as if they answered a
changed proposal. Gold annotations are evaluator-only, never policy inputs.
"""

import argparse
import copy
import hashlib
import json
import socket
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from arena_kit.cost import must_haves_ok, total_cost
from arena_kit.docs import standard_terms

from negotiator.agent import PackageAgent
from negotiator.guards import leaks
from negotiator.policy import PolicyConfig
from negotiator.responses import permitted

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/replay_decisions.json"


class Trace:
    def __init__(self):
        self.events = []

    def log(self, event, **kw):
        self.events.append({"event": event, **kw})


def run_one(snapshot, case, fixes=False):
    policy = PolicyConfig(**{**snapshot["policy"], "evidence_types": ()})
    if fixes:
        policy = replace(policy, response_types=("price_increase", "quality", "raw_material"),
                         free_concessions=True, rfq_close_guard=True)
    trace = Trace()
    agent = PackageAgent(policy=policy, estimates={}, meso=False, claims=False, tracer=trace)
    sid = snapshot["supplier_id"]
    threads = copy.deepcopy(snapshot["threads"])
    agent.trades.deadlines = {s: time.time() + snapshot["seconds_left"] for s in threads}
    # Fail closed even if a future dependency accidentally attempts network access.
    with patch.object(socket.socket, "connect", side_effect=RuntimeError("offline replay forbids network")):
        move = agent.propose(copy.deepcopy(case), threads, sid)
    message = move.get("message") or {}
    terms = (message.get("term_sheets") or [{}])[0].get("terms")
    kind = "close" if move.get("close") else "hold" if move.get("hold") else "send"
    standard = standard_terms(threads[sid])
    safe = not leaks(message.get("body", ""))
    if terms:
        safe = safe and set(terms) == set(case["negotiable"]) and permitted(case, terms)
        safe = safe and must_haves_ok(case, terms, standard)
    expected = snapshot.get("expected", {"kind": kind, "terms": {}})
    matched = kind == expected["kind"] and all((terms or {}).get(k) == v for k, v in expected["terms"].items())
    if expected.get("quoted_index_clause"):
        clauses = [s["terms"].get("index_clause") for m in threads[sid] if m.get("from") != "buyer"
                   for s in m.get("term_sheets") or []]
        matched = matched and bool((terms or {}).get("index_clause")) and terms["index_clause"] in clauses
    return {"kind": kind, "terms": terms, "safe": bool(safe), "matches_annotation": matched,
            "proposal_cost": total_cost(case, terms, standard) if terms else None,
            "policy": policy.record(), "trace": trace.events, "move": move,
            "historical_fidelity": "unverified: quote defaults and timing not reconstructed"}


def scan_saved(cases, runs_root):
    """Guard-check every open single-thread prefix in all 24 runs; no future replies.

RFQ cross-thread coordination is covered by curated timestamp-aligned snapshots, not
inferred from independent final thread histories. Exact repeats are deduplicated.
    """
    paths = []
    for batch in ("staged-a-20261010", "staged-b-20261010", "staged-refinement-20261010",
                  "staged-broader-20261010"):
        batch_paths = sorted((runs_root / batch).glob("*/server-evidence.json"))
        if not batch_paths:
            raise ValueError(f"No saved evidence found for {batch}")
        paths.extend(batch_paths)
    seen, rows, prefixes = set(), [], 0
    for path in paths:
        traces = list(path.parent.glob("*/trace.jsonl"))
        if len(traces) != 1:
            raise ValueError(f"Expected one trace for {path.parent.name}")
        run = json.loads(traces[0].read_text().splitlines()[0])
        policy = (run.get("policy") or {}).get("config", {"version": 1})
        for cid, data in json.loads(path.read_text()).items():
            for sid, thread in data["threads"].items():
                for i, message in enumerate(thread["messages"]):
                    if message.get("from") == "buyer" or message.get("status") != "open":
                        continue
                    prefixes += 1
                    prefix = [{k: v for k, v in m.items()
                               if k in ("from", "status", "term_sheets", "body", "refs", "message_id", "attachments")}
                              for m in thread["messages"][:i + 1]]
                    s = {"case_id": cid, "supplier_id": sid, "policy": policy,
                         "threads": {sid: prefix}, "seconds_left": 60,
                         "quote_defaults_verified": False}
                    digest = hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest()
                    if digest in seen:
                        continue
                    seen.add(digest)
                    before, after = run_one(s, cases[cid]), run_one(s, cases[cid], True)
                    cost_guard = (before["proposal_cost"] is None or after["proposal_cost"] is None
                                  or after["proposal_cost"] <= before["proposal_cost"] + 0.01)
                    rows.append({"case": cid, "session": data["state"]["session_id"], "supplier": sid,
                                 "prefix_end": i, "prefix_sha256": digest, "safe": after["safe"],
                                 "proposal_cost_not_increased": cost_guard,
                                 "changed": before["move"] != after["move"],
                                 "before": before, "after": after})
    return {"runs": len(paths), "prefixes": prefixes, "unique_prefixes": len(rows),
            "failures": sum(not r["safe"] or not r["proposal_cost_not_increased"] for r in rows),
            "interpretation": ("Synthetic prefix guard checks; quote defaults unavailable. "
                               "Not faithful historical replays, rollouts or RFQ timelines."),
            "historical_fidelity_verified": False,
            "rows": rows}


def evaluate(all_saved=False, runs_root=ROOT / "experiments/runs"):
    cases = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
    snapshots = json.loads(FIXTURE.read_text())["snapshots"]
    rows = []
    for snapshot in snapshots:
        before = run_one(snapshot, cases[snapshot["case_id"]])
        after = run_one(snapshot, cases[snapshot["case_id"]], True)
        before_c, after_c = before["proposal_cost"], after["proposal_cost"]
        cost_guard = before_c is None or after_c is None or after_c <= before_c + 0.01
        rows.append({"id": snapshot["id"], "source": snapshot["source"], "before": before, "after": after,
                     "proposal_cost_not_increased": cost_guard})
    report = {"interpretation": ("Synthetic one-step development regressions with incomplete quote defaults; "
                                 "no predicted arena scores or supplier responses."),
            "historical_fidelity_verified": False,
            "arena_sessions_started": 0, "model_calls": 0,
            "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted((ROOT / "src/negotiator").glob("*.py"))},
            "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), "rows": rows,
            "before_matches": sum(r["before"]["matches_annotation"] for r in rows),
            "after_matches": sum(r["after"]["matches_annotation"] for r in rows),
            "checks_pass": all(r["after"]["safe"] and r["after"]["matches_annotation"]
                               and r["proposal_cost_not_increased"] for r in rows)}
    if all_saved:
        report["saved_scan"] = scan_saved(cases, runs_root)
        report["checks_pass"] = report["checks_pass"] and report["saved_scan"]["failures"] == 0
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--all-saved", action="store_true", help="Also guard-check all 24 local saved runs")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "experiments/runs")
    args = parser.parse_args()
    report = evaluate(args.all_saved, args.runs_root)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    for row in report["rows"]:
        print(row["id"], "before:", row["before"]["matches_annotation"],
              "after:", row["after"]["matches_annotation"], "safe:", row["after"]["safe"],
              "cost guard:", row["proposal_cost_not_increased"])
    print("No arena sessions or model calls. These checks do not predict negotiation scores.")
    if "saved_scan" in report:
        print({k: v for k, v in report["saved_scan"].items() if k != "rows"})
    return 0 if report["checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
