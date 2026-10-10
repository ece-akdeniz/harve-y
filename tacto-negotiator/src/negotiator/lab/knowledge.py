"""Portable evidence graph for the lab. Storage/service ownership belongs to Barış.

All exported records are evaluation-only. A supplier's claim is an attributed message,
not a verified fact. Unknown data versions deliberately cannot join across runs.
"""

from typing import Literal, Protocol

from ..ingestion import fingerprint
from .models import timestamp


class MemoryReader(Protocol):
    def supplier_history(self, run: dict, supplier: str, *, purpose: Literal["feedback", "live"],
                         case_id: str | None = None, limit: int = 20) -> list[dict]: ...


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

    def link(source, relation, target, provenance=None):
        key = _id("edge", source, relation, target, (provenance or {}).get("source_id"))
        edges[key] = {"id": key, "source": source, "relation": relation, "target": target,
                      **({"provenance": provenance} if provenance else {})}

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
        if not isinstance(version, str) or not version or not isinstance(facts, dict) or len(facts) > 50000:
            raise ValueError("versioned public facts required for graph projection")
        sources = getattr(package, "sources", {})
        relation_by_type = {"quote": "offers_part", "po": "supplies_part",
                            "ctr": "has_contract_fact", "sc": "has_performance_fact",
                            "qn": "has_quality_fact", "news": "has_news_fact",
                            "doc": "has_correspondence_fact", "contact": "has_contact_fact"}
        for ref, value in sorted(facts.items()):
            if not isinstance(ref, str) or not isinstance(value, dict):
                continue
            provenance = {"data_sha256": version, "source_id": ref,
                          "source_layer": sources.get(ref, "unknown"),
                          "observed_at": value.get("date") or value.get("quarter"),
                          "valid_from": value.get("valid_from"), "valid_to": value.get("valid_to"),
                          "confidence": value.get("confidence_pct"), "conflict_state": "none"}
            fact_id = node("public_fact", (version, ref), value, provenance)
            nodes[fact_id]["scope"] = "current_public_data"
            entities = {}
            for field, kind in (("supplier", "supplier"), ("supplier_id", "supplier"),
                                ("part", "part"), ("part_id", "part")):
                identity = value.get(field)
                if isinstance(identity, str) and identity:
                    entity_id = node("current_" + kind, (version, identity),
                                     {kind + "_id": identity}, {"data_sha256": version})
                    nodes[entity_id]["scope"] = "current_public_data"
                    link(fact_id, "describes_" + kind, entity_id)
                    entities[kind] = entity_id
            fact_type = ref.split(":", 1)[0]
            if "supplier" in entities and fact_type in relation_by_type:
                link(entities["supplier"], relation_by_type[fact_type], fact_id, provenance)
            if "supplier" in entities and "part" in entities and fact_type in {"quote", "po"}:
                link(entities["supplier"], "quoted_or_supplied_part", entities["part"], provenance)
            contact = value.get("contact_id")
            if "supplier" in entities and isinstance(contact, str) and contact and fact_type == "contact":
                contact_id = node("current_contact", (version, contact), {"contact_id": contact},
                                  {"data_sha256": version})
                nodes[contact_id]["scope"] = "current_public_data"
                link(entities["supplier"], "has_contact", contact_id, provenance)
                link(fact_id, "describes_contact", contact_id, provenance)
        conflicts = (getattr(package, "manifest", None) or {}).get("conflicts", {})
        if isinstance(conflicts, dict):
            for ref, versions in sorted(conflicts.items()):
                conflict_id = node("public_conflict", (version, ref),
                                   {"source_id": ref, "versions": versions},
                                   {"data_sha256": version, "conflict_state": "unresolved"})
                nodes[conflict_id]["scope"] = "current_public_data"
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

    def supplier_history(self, run, supplier, *, purpose, case_id=None, limit=20):
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
            if (ref["run_id"] == run["run_id"]
                    or (case_id is not None and ref["case_id"] != case_id)
                    or timestamp(ref["recorded_at"]) > timestamp(run["started_at"])):
                continue
            found.append(item)
        return sorted(found, key=lambda n: (timestamp(n["provenance"]["recorded_at"]), n["id"]),
                      reverse=True)[:limit]
