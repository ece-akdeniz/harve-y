"""Portable evidence graph for the lab. Storage/service ownership belongs to Barış.

All exported records are evaluation-only. A supplier's claim is an attributed message,
not a verified fact. Unknown data versions deliberately cannot join across runs.
"""

from typing import Literal, Protocol

from ..ingestion import fingerprint
from .models import timestamp


class MemoryReader(Protocol):
    def supplier_history(self, run: dict, supplier: str, *, purpose: Literal["feedback", "live"],
                         limit: int = 20) -> list[dict]: ...


def _id(kind, *identity):
    return f"{kind}:{fingerprint(identity)}"


def _scope(run):
    version = (run.get("provenance") or {}).get("data_sha256")
    return (run["arena_url"], run["environment"], version or f"unknown:{run['run_id']}")


def supplier_id(run, supplier):
    return _id("supplier", *_scope(run), supplier)


def export_graph(runs, reports=(), package=None):
    """Stable snapshot, suitable for idempotent upserts into a team's graph service."""
    nodes, edges = {}, {}

    def node(kind, identity, data, provenance):
        key = _id(kind, *identity)
        nodes[key] = {"id": key, "kind": kind, "scope": "evaluation_only",
                      "data": data, "provenance": provenance}
        return key

    def link(source, relation, target):
        key = _id("edge", source, relation, target)
        edges[key] = {"id": key, "source": source, "relation": relation, "target": target}

    runs = [r.model_dump() if hasattr(r, "model_dump") else r for r in runs]
    all_attempts = {(r["run_id"], a["attempt_id"]): _id("attempt", r["run_id"], a["attempt_id"])
                    for r in runs for a in r["attempts"]}
    reports = {r["run_id"]: r for r in reports}
    for run in sorted(runs, key=lambda r: r["run_id"]):
        provenance = {"run_id": run["run_id"], "arena_url": run["arena_url"],
                      "environment": run["environment"], "source": run["source"],
                      "data_sha256": (run.get("provenance") or {}).get("data_sha256"),
                      "commit": (run.get("provenance") or {}).get("commit"),
                      "recorded_at": run["updated_at"], "source_sha256": fingerprint(run)}
        rid = node("run", (run["run_id"],), {"agent": run["agent"], "status": run["status"]}, provenance)
        for attempt in run["attempts"]:
            identity = (run["run_id"], attempt["attempt_id"])
            ref = {**provenance, "attempt_id": attempt["attempt_id"],
                   "case_id": attempt["case_id"], "session_id": attempt.get("session_id")}
            aid = node("attempt", identity, {"status": attempt["status"], "score": attempt.get("score"),
                                            "result": attempt.get("result", {})}, ref)
            link(rid, "has_attempt", aid)
            cid = node("case", (*_scope(run), attempt["case_id"]), {"case_id": attempt["case_id"]},
                       {"arena_url": run["arena_url"], "environment": run["environment"],
                        "data_sha256": provenance["data_sha256"],
                        "unknown_version_run": run["run_id"] if not provenance["data_sha256"] else None})
            link(aid, "evaluates_case", cid)
            for supplier, thread in sorted(attempt.get("threads", {}).items()):
                # The entity carries identity only. Facts and provenance live on observations.
                sid = node("supplier", (*_scope(run), supplier), {"supplier_id": supplier},
                           {"arena_url": run["arena_url"], "environment": run["environment"],
                            "data_sha256": provenance["data_sha256"],
                            "unknown_version_run": run["run_id"] if not provenance["data_sha256"] else None})
                link(aid, "negotiated_with", sid)
                messages = thread if isinstance(thread, list) else thread.get("messages", [])
                for index, event in enumerate(messages):
                    mref = {**ref, "supplier_id": supplier, "message_index": index}
                    mid = node("message", (*identity, supplier, index), event, mref)
                    link(aid, "has_message", mid)
                    link(mid, "in_supplier_thread", sid)
                    for sheet_index, sheet in enumerate(event.get("term_sheets") or []):
                        oid = node("offer", (*identity, supplier, index, sheet_index), sheet, mref)
                        link(mid, "contains_offer", oid)
        report = reports.get(run["run_id"])
        # Do not attach stale feedback to a changed run snapshot.
        if report and report.get("source_sha256") == fingerprint(run):
            for finding in report["findings"]:
                fid = node("observation", (run["run_id"], fingerprint(finding)), finding, provenance)
                link(rid, "has_feedback", fid)
                for ref in finding["evidence"]:
                    aid = all_attempts.get((ref.get("run_id"), ref.get("attempt_id")))
                    if aid:
                        link(fid, "supported_by", aid)
                    sid = supplier_id(run, ref.get("supplier"))
                    if sid in nodes:
                        link(fid, "about_supplier", sid)
    if package is not None:
        version = (getattr(package, "manifest", None) or {}).get("sha256")
        facts = getattr(package, "facts", None)
        if not isinstance(version, str) or not version or not isinstance(facts, dict) or len(facts) > 10000:
            raise ValueError("versioned public facts required for graph projection")
        sources = getattr(package, "sources", {})
        for ref, value in sorted(facts.items()):
            if not isinstance(ref, str) or not isinstance(value, dict):
                continue
            provenance = {"data_sha256": version, "source_id": ref,
                          "source_layer": sources.get(ref, "unknown")}
            fact_id = node("public_fact", (version, ref), value, provenance)
            nodes[fact_id]["scope"] = "current_public_data"
            for field, kind in (("supplier", "supplier"), ("supplier_id", "supplier"),
                                ("part", "part"), ("part_id", "part")):
                identity = value.get(field)
                if isinstance(identity, str) and identity:
                    entity_id = node("current_" + kind, (version, identity),
                                     {kind + "_id": identity}, {"data_sha256": version})
                    nodes[entity_id]["scope"] = "current_public_data"
                    link(fact_id, "describes_" + kind, entity_id)
    return {"schema_version": 1, "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
            "edges": sorted(edges.values(), key=lambda e: e["id"]),
            "live_lessons_enabled": False}


class SnapshotMemory:
    """Reference reader Barış can replace with a graph-backed implementation."""

    def __init__(self, graph):
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        self.attempts = {}
        for edge in graph["edges"]:
            if edge["relation"] == "negotiated_with":
                self.attempts.setdefault(edge["target"], []).append(edge["source"])

    def supplier_history(self, run, supplier, *, purpose, limit=20):
        if purpose not in {"feedback", "live"}:
            raise ValueError("unsupported memory purpose")
        if purpose == "live":
            return []  # Requires a separately reviewed lesson projection; raw results never enter play.
        if not 1 <= limit <= 100:
            raise ValueError("memory limit must be between 1 and 100")
        found = []
        for key in self.attempts.get(supplier_id(run, supplier), []):
            item = self.nodes[key]
            ref = item["provenance"]
            if ref["run_id"] == run["run_id"] or timestamp(ref["recorded_at"]) > timestamp(run["started_at"]):
                continue
            found.append(item)
        return sorted(found, key=lambda n: (timestamp(n["provenance"]["recorded_at"]), n["id"]),
                      reverse=True)[:limit]
