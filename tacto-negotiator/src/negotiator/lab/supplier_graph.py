"""Human supplier intelligence: source-backed graph across owned runs and supplied releases.

The view never becomes runtime memory implicitly. Dataset partitions are preserved even
when identifiers repeat in a completely different test package. No internet collection.
"""

import json
from collections import Counter
from datetime import UTC, datetime

from .memory import MemoryStore
from .supplier_report import build_report
from .workspace import identity, messages, suppliers_for

GROUPS = {"parts": "Parts", "contracts": "Contracts", "performance": "Performance",
          "news": "News & updates", "runs": "Runs & agents", "memory": "Shared memory",
          "facts": "Other source records", "conflicts": "Conflicts"}


def packages(store):
    with store._connect() as db:
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='learning_data'").fetchone()
        if not exists:
            return []
        return [json.loads(r[0]) for r in db.execute(
            "SELECT body FROM learning_data ORDER BY ingested_at DESC, data_sha256 DESC")]


def supplier_ids(package):
    found = {r["id"] for r in package.get("entities", {}).get("suppliers", []) if isinstance(r.get("id"), str)}
    for v in package["facts"].values():
        sid = v.get("supplier") or v.get("supplier_id")
        if isinstance(sid, str):
            found.add(sid)
    for versions in package.get("manifest", {}).get("conflicts", {}).values():
        for v in versions.values():
            sid = v.get("supplier") or v.get("supplier_id")
            if isinstance(sid, str):
                found.add(sid)
    return found


def catalog(store, records_):
    data = packages(store)
    memberships = {p["data_sha256"]: supplier_ids(p) for p in data}
    names = {}
    for p in reversed(data):
        for sid in memberships[p["data_sha256"]]:
            names.setdefault(sid, sid)
        for s in p.get("entities", {}).get("suppliers", []):
            names[s["id"]] = s.get("name") or s["id"]
    historical = set()
    for r in records_:
        for sid in suppliers_for(r):
            historical.add(sid)
            if names.get(sid, sid) == sid:
                msgs = messages((r["attempt"].get("threads") or {}).get(sid, {}))
                names[sid] = next((m["from_name"] for m in msgs if m.get("from_name")), sid)
    return {"datasets": [{"id": p["data_sha256"], "label": p.get("label", "Supplied dataset"),
                          "ingested_at": p["ingested_at"], "checked_at": p.get("checked_at", p["ingested_at"]),
                          "release": p.get("release_label"), "facts": len(p["facts"]),
                          "suppliers": len(supplier_ids(p)), "news": sum(k.startswith("news:") for k in p["facts"]),
                          "conflicts": len(p.get("manifest", {}).get("conflicts", {}))} for p in data],
            "suppliers": [{"id": sid, "name": names[sid],
                           "datasets": [p["data_sha256"] for p in data if sid in memberships[p["data_sha256"]]],
                           "has_history": sid in historical} for sid in sorted(names, key=lambda s: names[s])],
            "arenas": sorted({r["run"]["arena_url"] for r in records_}), "external_news_connected": False}


def fact_state(v, today):
    for field in ("valid_from", "date"):
        value = v.get(field)
        if isinstance(value, str) and value[:10] > today:
            return "future dated"
    if isinstance(v.get("valid_to"), str) and v["valid_to"][:10] < today:
        return "expired"
    return "dated source" if v.get("date") or v.get("quarter") else "date unknown"


def graph(store, records_, *, supplier, dataset="latest", environment="practice", arena=None):
    data = packages(store)
    if dataset == "latest":
        dataset = data[0]["data_sha256"] if data else "history"
    package = next((p for p in data if p["data_sha256"] == dataset), None)
    if dataset != "history" and package is None:
        raise ValueError("dataset not found")
    known = any(supplier in supplier_ids(p) for p in data)
    historical = [r for r in records_ if supplier in suppliers_for(r)]
    if not known and not historical:
        raise ValueError("supplier not found")
    historical = [r for r in historical if r["run"]["environment"] == environment
                  and (arena is None or r["run"]["arena_url"] == arena)]
    matched = [r for r in historical if dataset == "history"
               or (r["run"].get("provenance") or {}).get("data_sha256") == dataset]
    nodes, edges = {}, []
    today = datetime.now(UTC).date().isoformat()

    def node(kind, key, label, group, values=None, evidence=None, status=None):
        nid = identity(kind, key)
        nodes[nid] = {"id": nid, "kind": kind, "label": str(label), "group": group,
                      "values": values or {}, "evidence": evidence or [], "status": status}
        return nid

    def edge(source, relation, target):
        edges.append({"source": source, "relation": relation, "target": target})

    master = next((s for s in (package or {}).get("entities", {}).get("suppliers", [])
                   if s["id"] == supplier), {})
    root = node("supplier", (dataset, supplier), master.get("name", supplier), None,
                {"supplier_id": supplier, "dataset": dataset, **master},
                [{"source_id": f"sqlite-table:suppliers:{supplier}", "dataset": dataset}] if master else [])
    fact_counts = Counter()
    if package:
        version = package["data_sha256"]
        part_ids = set()
        for ref, v in sorted(package["facts"].items()):
            if v.get("supplier") != supplier and v.get("supplier_id") != supplier:
                continue
            kind = ref.split(":")[0]
            group = {"news": "news", "doc": "news", "ctr": "contracts", "sc": "performance",
                     "qn": "performance"}.get(kind, "facts")
            part = v.get("part") or v.get("part_id")
            if isinstance(part, str):
                part_ids.add(part)
            title = v.get("headline") or v.get("title") or ref
            nid = node("source_fact", (version, ref), title, group, v,
                       [{"source_id": ref, "dataset": version, "source_layer": package["sources"].get(ref),
                         "ingested_at": package["ingested_at"], "observed_at": v.get("date") or v.get("quarter")}],
                       fact_state(v, today))
            edge(root, "has_source_record", nid)
            fact_counts[kind] += 1
        parts = {p["id"]: p for p in package.get("entities", {}).get("parts", [])}
        for part in sorted(part_ids):
            nid = node("part", (version, part), parts.get(part, {}).get("description", part), "parts",
                       {"part_id": part, **parts.get(part, {})},
                       [{"source_id": f"sqlite-table:parts:{part}", "dataset": version}] if part in parts
                       else [{"source_id": ref, "dataset": version} for ref, v in package["facts"].items()
                             if part in (v.get("part"), v.get("part_id"))
                             and supplier in (v.get("supplier"), v.get("supplier_id"))][:20])
            edge(root, "quoted_or_supplied_part", nid)
            for fact in list(nodes.values()):
                if fact["kind"] == "source_fact" and part in (fact["values"].get("part"),
                                                               fact["values"].get("part_id")):
                    edge(fact["id"], "describes_part", nid)
        for ref, versions in package.get("manifest", {}).get("conflicts", {}).items():
            if any(supplier in (v.get("supplier"), v.get("supplier_id")) for v in versions.values()):
                nid = node("conflict", (version, ref), ref, "conflicts", versions,
                           [{"source_id": ref, "dataset": version}], "unresolved · excluded from facts")
                edge(root, "has_conflicting_source", nid)
        for intel in package.get("entities", {}).get("supplier_intel", []):
            if intel.get("supplier_id") == supplier:
                nid = node("supplier_profile", (version, supplier), "Supplier profile", "facts", intel,
                           [{"source_id": f"sqlite-table:supplier_intel:{supplier}", "dataset": version}],
                           "supplied profile · check fiscal year")
                edge(root, "has_profile", nid)
    session_lookup, run_nodes, contributors = {}, {}, set()
    for r in matched:
        run, a = r["run"], r["attempt"]
        version = (run.get("provenance") or {}).get("data_sha256")
        source_id = run["run_id"] or run.get("campaign_id")
        partition = version or f"unknown:{run['source']}:{source_id}"
        scope = (run["arena_url"], environment, partition, supplier)
        scoped_supplier = node("supplier_scope", scope, f"Dataset {partition[:12]}", None,
                               {"dataset": partition, "arena": run["arena_url"], "environment": environment})
        edge(root, "history_partition", scoped_supplier)
        ref = {"run_id": run["run_id"], "campaign_id": run.get("campaign_id"), "session_id": a.get("session_id"),
               "attempt_id": a["attempt_id"], "case_id": a["case_id"], "dataset": partition,
               "arena": run["arena_url"], "environment": environment, "recorded_at": run["updated_at"]}
        contributor = (run["agent"], run.get("author", "Unknown author"),
                       (run.get("provenance") or {}).get("commit"), identity(run.get("config", {})))
        contributors.add(contributor)
        agent_id = node("agent", (scope, contributor), run["agent"], "runs",
                        {"agent": run["agent"], "author": contributor[1], "commit": contributor[2],
                         "configuration_fingerprint": contributor[3]}, [ref], "recorded contributor")
        rid = node("run", (scope, run["source"], source_id), run["name"], "runs",
                   {"source": run["source"], "status": run["status"], "agent": run["agent"],
                    "author": contributor[1], "dataset": partition}, [ref], "historical evidence")
        run_nodes[r["id"]] = rid
        edge(rid, "contributed_by", agent_id)
        edge(scoped_supplier, "observed_in", rid)
        session_lookup[(run["arena_url"], a.get("session_id"))] = (r, rid, ref)
        nid = node("negotiation", (scope, r["id"]), a["case_id"], "runs",
                   {"status": a["status"], "messages": len(messages((a.get("threads") or {}).get(supplier, {}))),
                    "selected": (a.get("result") or {}).get("supplier_id") == supplier}, [ref])
        edge(rid, "has_negotiation", nid)
    observations = MemoryStore(store.path).graph()["observations"]
    memory_nodes = {}
    for o in observations:
        c = o["citation"]
        found = session_lookup.get((c["arena_url"], c["session_id"]))
        if c["supplier"] != supplier or c["environment"] != environment or not found:
            continue
        r, rid, ref = found
        value = o.get("direction") or o.get("value")
        memory_key = (ref["arena"], ref["dataset"], o["kind"], o["field"], value)
        evidence = {**ref, "message_index": c["message_index"], "excerpt": o.get("excerpt"),
                    "evidence_id": o["evidence_id"]}
        if memory_key not in memory_nodes:
            nid = node("observation", memory_key, f"{o['field'].replace('_', ' ')} · {value}", "memory",
                       {"kind": o["kind"], "field": o["field"], "value": value, "dataset": ref["dataset"],
                        "support_count": 0, "session_count": 0}, [],
                       "supplier statement" if o["kind"] == "supplier_statement"
                       else "observed offer · not a preference")
            memory_nodes[memory_key] = (nid, set())
        nid, sessions = memory_nodes[memory_key]
        item = nodes[nid]
        item["values"]["support_count"] += 1
        sessions.add(c["session_id"])
        item["values"]["session_count"] = len(sessions)
        if len(item["evidence"]) < 20:
            item["evidence"].append(evidence)
        edge(nid, "supported_by", rid)
    # Opposing explicit statements are conflicts; different offer values are not.
    for key, (nid, _) in memory_nodes.items():
        arena_id, version, kind, field, value = key
        opposite = (arena_id, version, kind, field, "lower" if value == "higher" else "higher")
        if kind == "supplier_statement" and value == "higher" and opposite in memory_nodes:
            other = memory_nodes[opposite][0]
            conflict = node("memory_conflict", (arena_id, version, field), f"Conflicting statements: {field}",
                            "conflicts", {"field": field, "dataset": version},
                            nodes[nid]["evidence"] + nodes[other]["evidence"], "unresolved · no inferred preference")
            edge(conflict, "contradictory_evidence", nid)
            edge(conflict, "contradictory_evidence", other)
    unique_edges = {identity(e["source"], e["relation"], e["target"]): e for e in edges}
    group_counts = Counter(n["group"] for n in nodes.values() if n["group"])
    dates = sorted(v.get("date") for v in (package or {}).get("facts", {}).values()
                   if supplier in (v.get("supplier"), v.get("supplier_id")) and isinstance(v.get("date"), str))
    return {"supplier": supplier, "name": master.get("name", supplier), "dataset": dataset,
            "environment": environment, "arena": arena, "root": root, "nodes": list(nodes.values()),
            "edges": list(unique_edges.values()), "groups": [
                {"id": key, "label": title, "count": group_counts[key]} for key, title in GROUPS.items()],
            "coverage": {"sessions": len(matched), "all_historical_sessions": len(historical),
                         "contributors": len(contributors), "shared_observations": len(memory_nodes),
                         "source_facts": sum(fact_counts.values()), "latest_source_date": dates[-1] if dates else None},
            "freshness": {"ingested_at": (package or {}).get("ingested_at"),
                          "checked_at": (package or {}).get("checked_at", (package or {}).get("ingested_at")),
                          "release": (package or {}).get("release_label"), "as_of": datetime.now(UTC).isoformat(),
                          "external_news_connected": False},
            "report": build_report(matched, supplier, list(nodes.values())),
            "boundary": "Shared human evidence view, not an automatic runtime policy. Dataset and unknown-source "
            "partitions stay separate. Repeated supplier IDs across datasets do not establish the same legal identity. "
            "Ingestion time is not the age of the source; dated, expired, future and conflicting records "
            "remain labeled."}
