"""Pure source-layer resolution, before supplier/part/case applicability.

Input records remain available to the caller as the shadowed revision archive.
Temporal status is preserved; this increment does not derive freshness or truth.
"""

from ..core.models import Conflict, EvidenceRecord, Issue, IssueCode

_PRIORITY = {"base": 0, "release": 1, "case": 2}
_RULE = "base-release-case/1"


def _issue(code: IssueCode, refs: tuple[str, ...], detail: str) -> Issue:
    return Issue(code=code, severity="error", component="evidence.resolver", refs=refs, detail=detail)


def _applicable(record: EvidenceRecord, case_id: str, suppliers: tuple[str, ...], parts: tuple[str, ...]) -> bool:
    scope = record.scope
    if scope.case_id is not None and scope.case_id != case_id:
        return False
    if scope.supplier_ids and not set(scope.supplier_ids).intersection(suppliers):
        return False
    if scope.part_ids and not set(scope.part_ids).intersection(parts):
        return False
    # Payload ownership cannot be broadened by an incomplete outer scope.
    supplier = getattr(record.payload, "supplier", None)
    part = getattr(record.payload, "part", None)
    payload_parts = getattr(record.payload, "part_ids", ())
    return not (
        supplier is not None and supplier not in suppliers
        or part is not None and part not in parts
        or payload_parts and not set(payload_parts).intersection(parts)
    )


class LayeredEvidenceResolver:
    def __init__(self, *, admit_live_quotes=False):
        self.admit_live_quotes = admit_live_quotes

    def priority(self, record):
        if (self.admit_live_quotes and record.provenance.layer == "session"
                and record.kind == "canonical" and record.payload.kind == "quote"
                and record.provenance.parser_version == "arena-kit-quote-terms/1"
                and record.scope.case_id and record.temporal.status == "current"):
            return 3
        return _PRIORITY.get(record.provenance.layer)

    def resolve(
        self,
        records: tuple[EvidenceRecord, ...],
        *,
        case_id: str,
        supplier_ids: tuple[str, ...],
        part_ids: tuple[str, ...],
    ) -> tuple[tuple[EvidenceRecord, ...], tuple[Conflict, ...], tuple[Issue, ...]]:
        """Return selected applicable revisions, resolution conflicts, and blocking issues.

        Unsupported layers and conflicting record identities fail closed for affected
        canonical groups. Unkeyed records resolve only by their own record identity.
        An applicable lower version never revives an inapplicable higher version.
        """
        if not isinstance(records, tuple) or any(not isinstance(record, EvidenceRecord) for record in records):
            raise TypeError("resolver inputs must be a tuple of validated EvidenceRecord objects")
        for value in (supplier_ids, part_ids):
            if not isinstance(value, tuple):
                raise TypeError("target identifier collections must be tuples")
        if any(not isinstance(value, str) or not value.strip() or value != value.strip()
               for value in (case_id, *supplier_ids, *part_ids)):
            raise ValueError("target identifiers must be nonempty and unpadded")

        by_id: dict[str, EvidenceRecord] = {}
        damaged_ids: set[str] = set()
        groups: dict[tuple[str, str], list[EvidenceRecord]] = {}
        issues: list[Issue] = []
        for record in records:
            if record.record_id in by_id and by_id[record.record_id] != record:
                damaged_ids.add(record.record_id)
            by_id.setdefault(record.record_id, record)
            key = ("canonical", record.canonical_id) if record.canonical_id is not None else (
                "record", record.record_id,
            )
            groups.setdefault(key, []).append(record)
        for record_id in sorted(damaged_ids):
            issues.append(_issue("source_conflict", (record_id,), "Record identity has contradictory content."))

        selected: list[EvidenceRecord] = []
        conflicts: list[Conflict] = []
        for (kind, identity), group in sorted(groups.items()):
            if any(record.record_id in damaged_ids for record in group):
                continue
            unique = {record.record_id: record for record in group}
            candidates = tuple(unique[key] for key in sorted(unique))
            unsupported = tuple(record.record_id for record in candidates if self.priority(record) is None)
            if unsupported:
                issues.append(_issue("unsupported_capability", unsupported, "Source layer has no admitted priority."))
                continue
            priority = max(self.priority(record) for record in candidates)
            top = tuple(record for record in candidates if self.priority(record) == priority)
            if len(top) > 1:
                refs = tuple(record.record_id for record in top)
                conflicts.append(Conflict(canonical_id=identity, candidate_record_ids=refs,
                                          rule_id=_RULE, blocking=True, reason_code="same_priority_collision"))
                issues.append(_issue("source_conflict", refs, "Highest-priority source revisions disagree."))
                continue
            winner = top[0]
            if kind == "canonical" and len(candidates) > 1:
                conflicts.append(Conflict(canonical_id=identity,
                                          candidate_record_ids=tuple(record.record_id for record in candidates),
                                          winning_record_id=winner.record_id, rule_id=_RULE,
                                          blocking=False, reason_code="layer_precedence"))
            if not _applicable(winner, case_id, supplier_ids, part_ids):
                issues.append(_issue("scope_mismatch", (winner.record_id,),
                                     "Selected revision is outside target scope."))
                continue
            selected.append(winner)

        return tuple(selected), tuple(conflicts), tuple(issues)
