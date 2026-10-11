"""Layered declared evidence assembly, not independent source authentication."""

from datetime import datetime

from ..core import models as m
from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash
from .resolver import LayeredEvidenceResolver


def prepared_hash(prepared: m.PreparedEvidence) -> str:
    return semantic_hash(prepared.model_dump(mode="json", exclude={"prepared_at", "integrity_hash", "artifact_id"}))


def context_version(context: m.EvidenceContext) -> str:
    return "sha256:" + semantic_hash(context.model_dump(mode="json", exclude={"context_version"}))


class LayeredContextBuilder:
    def __init__(self, *, resolver=None):
        self.resolver = resolver or LayeredEvidenceResolver()

    def build_context(
        self,
        prepared: m.PreparedEvidence,
        case: m.CaseContract,
        server: m.ServerState,
        documents: tuple[m.DocumentRecord, ...],
        as_of: datetime,
    ) -> m.EvidenceContext:
        prepared = m.PreparedEvidence.model_validate_json(prepared.model_dump_json())
        if (
            prepared_hash(prepared) != prepared.integrity_hash
            or prepared.artifact_id != "sha256:" + prepared.integrity_hash
        ):
            raise ContractViolation("invalid_schema: prepared projection identity mismatch")
        if server.case_id != case.case_id or server.status != "open":
            raise ContractViolation("scope_mismatch: context needs declared open server for this case")
        if prepared.prepared_at > as_of or server.observed_at > as_of:
            raise ContractViolation("future_source: preparation/server observation is later than context clock")
        # Document descriptors carry no source bytes or verified extraction; never turn them
        # into facts or quote standards implicitly. Preserve them in the offline input trace.
        if documents:
            raise ContractViolation("unsupported_capability: document hydration remains unimplemented")
        # Case overlays are a separate public input; resolve them with prepared
        # revisions before checking applicability, without changing their authority.
        input_records = prepared.records + case.case_facts
        records, conflicts, gaps = self.resolver.resolve(
            input_records,
            case_id=case.case_id,
            supplier_ids=case.supplier_ids,
            part_ids=tuple(p.part_id for p in case.parts),
        )
        current = []
        for record in records:
            temporal = record.temporal
            future = any(x is not None and x > as_of for x in (temporal.observed_at, temporal.published_at)) or any(
                x is not None and x > as_of.date() for x in (temporal.data_as_of, temporal.valid_from)
            )
            expired = temporal.valid_to is not None and temporal.valid_to < as_of.date()
            status = "future" if future else "stale" if expired else temporal.status
            # Derive only explicit date contradictions. No freshness rule execution or
            # promotion from unknown/stale to current; raw records remain in preparation.
            current.append(record.model_copy(update={"temporal": temporal.model_copy(update={"status": status})}))
        result = m.EvidenceContext(
            context_version="pending",
            case_id=case.case_id,
            supplier_ids=case.supplier_ids,
            part_ids=tuple(p.part_id for p in case.parts),
            as_of=as_of,
            prepared_artifact_id=prepared.artifact_id,
            records=tuple(current),
            conflicts=conflicts,
            gaps=gaps,
            relevance=(),
            source_versions=tuple(dict.fromkeys(r.provenance.source_version for r in input_records)),
        )
        return result.model_copy(update={"context_version": context_version(result)})
