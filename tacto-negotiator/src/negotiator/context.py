"""Internal, case-scoped evidence snapshot. Construction never reserves or sends claims."""

import copy
import hashlib
import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import dossiers, traits
from .claims import Claim, build_bank, case_facts, check

SCHEMA_VERSION = "evidence-context-v1"
DATA_ERRORS = (OSError, ValueError, KeyError, TypeError, ZeroDivisionError, sqlite3.Error)


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@dataclass
class EvidenceContext:
    """Private inspection record; only policy-selected Claim sentences may leave the agent."""

    case_id: str
    supplier_ids: tuple[str, ...]
    part_ids: tuple[str, ...]
    data_version: dict
    facts: dict
    sources: dict
    candidates: list[Claim] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    failed_checks: list[dict] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    @property
    def version(self):
        return content_hash(asdict(self))

    def to_dict(self):
        return {**asdict(self), "version": self.version, "audience": "internal"}

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def export(self, path):
        """Explicit local export, containing private candidates; never attach to a message."""
        Path(path).write_text(self.to_json(), encoding="utf-8")


def build_context(case, package):
    """Reuse merged facts, claim bank and dossier classifiers without runtime side effects.

    A supplied package is required for normal runtime use. None permits case-only inspection.
    Claim preparation failures are visible and result in an empty bank; optional signal failures
    do not discard otherwise valid claims. The snapshot must be rebuilt when inputs change.
    """
    facts = copy.deepcopy(case_facts(case, package))
    root = getattr(package, "root", None)
    release = getattr(package, "release", None)
    files = {}
    origins = {}
    manifests = {}
    for base in (root, release):
        if base:
            for path in sorted(Path(base).rglob("*")):
                if path.is_file():
                    files[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.name == "datapackage.json":
                        manifest = json.loads(path.read_text(encoding="utf-8"))
                        snapshot = re.search(r"Data as of (\d{4}-\d{2}-\d{2})", manifest.get("description", ""))
                        manifests[str(path.resolve())] = {
                            "name": manifest.get("name"), "version": manifest.get("version"),
                            "snapshot_date": snapshot.group(1) if snapshot else None,
                        }
                    if path.name == "facts.json":
                        layer = "release" if base == release else "base"
                        origins.update({ref: {"layer": layer, "path": str(path.resolve())}
                                        for ref in json.loads(path.read_text(encoding="utf-8"))})
    context = EvidenceContext(
        case["case_id"], tuple(case.get("suppliers") or []), tuple(case.get("parts") or []),
        {"root": str(root) if root else None, "release": str(release) if release else None,
         "files": files, "manifests": manifests, "package_facts_sha256": content_hash(getattr(package, "facts", {})),
         "case_sha256": content_hash(case)}, {}, {},
    )
    if not any(m["snapshot_date"] for m in manifests.values()):
        context.gaps.append({"area": "data_version", "reason": "snapshot date not recorded"})
    if package is None:
        context.gaps.append({"area": "package", "reason": "case facts only"})
    try:
        candidates = build_bank(case, package, False)
        for claim in candidates:
            reason = check(claim, facts, package, case)
            if reason:
                context.failed_checks.append({"kind": claim.kind, "ids": list(claim.ids), "reason": reason})
            else:
                context.candidates.append(claim)
    except DATA_ERRORS as exc:
        context.gaps.append({"area": "claims", "reason": type(exc).__name__})
        context.candidates.clear()
    relevant = set(case.get("refs") or []) | set(case.get("facts") or {})
    relevant.update(i for c in context.candidates for i in c.ids)
    relevant.update(i for c in context.failed_checks for i in c["ids"])
    for ref, fact in facts.items():
        if isinstance(fact, dict) and (
            fact.get("supplier") in context.supplier_ids or fact.get("part") in context.part_ids
        ):
            relevant.add(ref)
    for ref in sorted(relevant):
        if ref not in facts:
            context.gaps.append({"area": "fact", "id": ref, "reason": "missing reference"})
            continue
        context.facts[ref] = facts[ref]
        fact = facts[ref]
        origin = {"layer": "case", "path": None} if ref in (case.get("facts") or {}) else origins.get(
            ref, {"layer": "package_merged", "path": None})
        if ref in (case.get("facts") or {}) and ref in getattr(package, "facts", {}):
            if fact != package.facts[ref]:
                context.gaps.append({"area": "overlay", "id": ref, "reason": "case overrides package fact"})
        units = {k: v for k, v in {
            "value": fact.get("unit"), "otd_pct": "%", "ppm": "ppm", "days": "days",
            "unit_price": fact.get("currency", "EUR"), "unit_cost": fact.get("currency", "EUR"),
        }.items() if k in fact} if isinstance(fact, dict) else {}
        context.sources[ref] = {**origin, "sha256": content_hash(fact), "units": units,
                                "price_unit": fact.get("price_unit") if isinstance(fact, dict) else None}
        if isinstance(fact, dict) and "value" in fact and not fact.get("unit"):
            context.gaps.append({"area": "unit", "id": ref, "reason": "index unit not recorded"})
    if package is not None and getattr(package, "db", None) is not None:
        try:
            ds = {sid: d for sid in context.supplier_ids if (d := dossiers.build_one(package, sid))}
            ds = dossiers.for_case(ds, case)
            for sid in context.supplier_ids:
                if sid not in ds:
                    context.gaps.append({"area": "signals", "supplier_id": sid,
                                         "reason": "supplier dossier unavailable"})
            for sid, dossier in ds.items():
                for trait in sorted(traits.classify(dossier)):
                    ids = traits.evidence(dossier, trait)
                    records = [r for r in [*dossier.notes, *dossier.news] if r["id"] in ids]
                    context.signals.append({"supplier_id": sid, "kind": trait, "source_ids": ids,
                                            "observed_dates": [r.get("date") for r in records],
                                            "supporting_records": copy.deepcopy(records),
                                            "interpretation": "classifier hypothesis",
                                            "freshness": "unchecked"})
                    if not ids:
                        context.gaps.append({"area": "signal", "supplier_id": sid, "kind": trait,
                                             "reason": "classifier supplies no citable source IDs"})
                    for ref in ids:
                        record = next((r for r in [*dossier.notes, *dossier.news] if r["id"] == ref), {})
                        context.sources.setdefault(ref, {"layer": "dossier", "sha256": content_hash(record),
                                                         "units": {}})
                        context.facts.setdefault(ref, record)
        except DATA_ERRORS as exc:
            context.gaps.append({"area": "signals", "reason": type(exc).__name__})
    else:
        context.gaps.append({"area": "signals", "reason": "supplier database unavailable"})
    for kind in ("notice", "index_change", "scorecard_otd", "scorecard_ppm"):
        if not any(c.kind == kind for c in context.candidates):
            context.gaps.append({"area": "claims", "kind": kind, "reason": "no valid candidate from existing builder"})
    context.gaps.append({"area": "signals", "reason": "existing dossier overlay covers case news only"})
    return context
