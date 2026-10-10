"""Human-only supplier workspace projected from saved evidence; never sends agent moves."""

import hashlib
import json
import math
from datetime import UTC, datetime

from .memory import MemoryStore
from .models import utc_now


def identity(*parts):
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:24]


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def messages(thread):
    value = thread if isinstance(thread, list) else thread.get("messages", [])
    return [m for m in value if isinstance(m, dict)] if isinstance(value, list) else []


def records(store, loop):
    """Deduplicate canonical sessions, preferring owned campaign/tracked evidence to imports."""
    suites = {s["suite_id"]: s for s in loop.read("suites")["suites"]}
    checkpoints = {c["checkpoint_id"]: c for c in loop.read("checkpoints")["checkpoints"]}
    sources = []
    for c in loop.read("campaigns")["campaigns"]:
        suite = suites.get(c["suite_id"])
        if not suite:
            continue
        for a in c["attempts"]:
            outcome = a.get("outcome") or {}
            cp = checkpoints.get(a["checkpoint_id"], {})
            started = a.get("start", {}).get("started_at", c["created_at"])
            run = dict(run_id=None, campaign_id=c["campaign_id"], name=c["campaign_id"], author=c["author"],
                       source="campaign", environment=suite["environment"], arena_url=suite["arena_url"],
                       started_at=datetime.fromtimestamp(started, UTC).isoformat(),
                       updated_at=datetime.fromtimestamp(a.get("finished_at") or started, UTC).isoformat(),
                       status=c["status"], agent=cp.get("agent", "Recorded checkpoint"), config=cp.get("config", {}),
                       provenance={"commit": cp.get("commit"), "data_sha256": suite.get("data", {}).get("sha256")})
            sources.append((run, {**outcome, "attempt_id": a["attempt_id"], "case_id": a["case_id"],
                                  "status": "running" if a["status"] == "started" else a["status"],
                                  "reconciliation": a.get("reconciliation")}))
    for run in sorted(store.all(), key=lambda r: r.source == "imported"):
        sources.extend((run.model_dump(exclude={"attempts"}), a.model_dump()) for a in run.attempts)
    unique = {}
    for run, a in sources:
        if a["status"] == "pending":
            continue
        session = a.get("session_id")
        key = (run["arena_url"].rstrip("/"), session) if session else (run["run_id"], a["attempt_id"])
        if key in unique:
            continue
        unique[key] = {"run": run, "attempt": a, "id": identity(*key)}
    return list(unique.values())


def savings(record):
    a = record["attempt"]
    r = a.get("result") or {}
    if (a["status"] != "completed" or r.get("ended") is not True or r.get("deal") is not True
            or r.get("must_haves_ok") is not True or not r.get("supplier_id")
            or not numeric(r.get("c_open")) or not numeric(r.get("c_deal")) or r["c_open"] <= 0):
        return None
    return {"opening_eur": r["c_open"], "outcome_eur": r["c_deal"],
            "change_eur": round(r["c_open"] - r["c_deal"], 2), "basis": "Recorded case opening full cost"}


def summary(record, supplier):
    run, a = record["run"], record["attempt"]
    result = a.get("result") or {}
    thread = (a.get("threads") or {}).get(supplier, {})
    msgs = messages(thread)
    selected = result.get("supplier_id") == supplier
    return dict(id=record["id"], case_id=a["case_id"], session_id=a.get("session_id"),
                run_id=run["run_id"], campaign_id=run.get("campaign_id"), name=run["name"],
                source=run["source"], environment=run["environment"], arena_url=run["arena_url"],
                started_at=run["started_at"], updated_at=run["updated_at"], status=a["status"],
                selected=selected, deal=result.get("deal") if selected else None,
                must_haves_ok=result.get("must_haves_ok") if selected else None,
                score=a.get("score") if selected else None, savings=savings(record) if selected else None,
                message_count=len(msgs), timeouts=a.get("timeouts"),
                stale=a["status"] == "running" and
                (datetime.now(UTC) - datetime.fromisoformat(run["updated_at"])).total_seconds() > 120)


def suppliers_for(record):
    a = record["attempt"]
    threads = a.get("threads") or {}
    ids = {sid for sid, thread in threads.items() if isinstance(thread, (dict, list))}
    selected = (a.get("result") or {}).get("supplier_id")
    if isinstance(selected, str):
        ids.add(selected)
    return sorted(ids)


def directory(records_, environment):
    scoped = [r for r in records_ if r["run"]["environment"] == environment]
    suppliers, latest_cases = {}, {}
    for r in sorted(scoped, key=lambda r: (r["run"]["started_at"], r["id"]), reverse=True):
        run = r["run"]
        latest_cases.setdefault((run["arena_url"], r["attempt"]["case_id"]), r)
        for sid in suppliers_for(r):
            key = identity(run["arena_url"], environment, sid)
            msgs = messages((r["attempt"].get("threads") or {}).get(sid, {}))
            name = next((m["from_name"] for m in msgs if m.get("from") != "buyer" and m.get("from_name")), sid)
            supplier = suppliers.setdefault(key, dict(key=key, supplier_id=sid, name=name,
                arena_url=run["arena_url"], environment=environment, negotiations=[]))
            supplier["negotiations"].append(summary(r, sid))
    latest = list(latest_cases.values())
    covered = [savings(r) for r in latest if savings(r) is not None]
    opening = sum(v["opening_eur"] for v in covered)
    change = sum(v["change_eur"] for v in covered)
    return {"environment": environment, "generated_at": utc_now(), "suppliers": list(suppliers.values()),
            "summary": {"suppliers": len(suppliers), "sessions": len(scoped), "cases": len(latest),
                        "running": sum(r["attempt"]["status"] == "running" for r in scoped),
                        "savings_eur": round(change, 2) if covered else None,
                        "savings_pct": change / opening * 100 if opening else None,
                        "savings_covered": len(covered), "savings_cases": len(latest)},
            "savings_basis": "Latest recorded session per arena and case in the selected environment. "
            "Only completed, valid deals with opening and outcome full costs. Negative changes remain included. "
            "Simulation results, not realized business savings. Case opening baseline may be another RFQ supplier."}


def detail(store, records_, key, negotiation=None):
    matches = []
    supplier = None
    for record in records_:
        run = record["run"]
        for sid in suppliers_for(record):
            if identity(run["arena_url"], run["environment"], sid) == key:
                matches.append(record)
                supplier = sid
    if not matches:
        return None
    matches.sort(key=lambda r: (r["run"]["started_at"], r["id"]), reverse=True)
    record = next((r for r in matches if r["id"] == negotiation), None) if negotiation else matches[0]
    if record is None:
        return None
    run, a = record["run"], record["attempt"]
    result = a.get("result") or {}
    thread = (a.get("threads") or {}).get(supplier, {})
    msgs = messages(thread)
    data_hash = (run.get("provenance") or {}).get("data_sha256")
    scoped_sessions = {r["attempt"].get("session_id") for r in matches
                       if r["attempt"]["case_id"] == a["case_id"] and data_hash
                       and (r["run"].get("provenance") or {}).get("data_sha256") == data_hash}
    observations = [o for o in MemoryStore(store.path).graph()["observations"]
                    if o["citation"]["supplier"] == supplier
                    and o["citation"]["arena_url"] == run["arena_url"]
                    and o["citation"]["environment"] == run["environment"]
                    and o["citation"]["case_id"] == a["case_id"]
                    and o["citation"]["session_id"] in scoped_sessions]
    facts, findings = [], []
    with store._connect() as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if data_hash and "learning_data" in tables:
            row = db.execute("SELECT body FROM learning_data WHERE data_sha256=?", (data_hash,)).fetchone()
            if row:
                package = json.loads(row[0])
                for ref, value in sorted(package["facts"].items()):
                    if value.get("supplier") == supplier or value.get("supplier_id") == supplier:
                        facts.append({"source_id": ref, "layer": package["sources"].get(ref), "values": value})
        if run["run_id"] and "feedback" in tables:
            from ..ingestion import fingerprint

            original = store.get(run["run_id"])
            row = db.execute("SELECT body FROM feedback WHERE source_sha256=?", (fingerprint(original),)).fetchone()
            if row:
                findings = [f for f in json.loads(row[0])["findings"] if any(
                    e.get("attempt_id") == a["attempt_id"] and e.get("supplier") in (None, supplier)
                    for e in f["evidence"])]
    return {"supplier_id": supplier, "key": key, "negotiation": summary(record, supplier),
            "negotiations": [summary(r, supplier) for r in matches],
            "messages": msgs, "thread_status": thread.get("status") if isinstance(thread, dict) else None,
            "evidence_truncated": bool((a.get("threads") or {}).get("evidence_truncated")),
            "result": result if result.get("supplier_id") == supplier else {},
            "recovery": a.get("reconciliation"), "error": a.get("error"),
            "policy": {"agent": run["agent"], "config": run["config"], "provenance": run.get("provenance"),
                       "source": run["source"]},
            "memory": {"observations": observations[:100], "observation_count": len(observations),
                       "facts": facts[:100], "fact_count": len(facts), "data_sha256": data_hash},
            "findings": findings}
