"""Conservative index evidence candidate; no supplier-cost or personality inference.

Only series referenced by the case or its parts' cost-driver records are eligible. Exact calendar-year
windows avoid treating thirteen sparse observations as twelve months.
"""

import math
import re
from dataclasses import dataclass

INDEX_ID = re.compile(r"idx:([A-Za-z0-9_-]+)@(\d{4}-\d{2})\Z")


def _month(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        return None
    year, month = map(int, value.split("-"))
    return year * 12 + month - 1 if 1 <= month <= 12 else None


def _index(ref, fact):
    match = INDEX_ID.fullmatch(ref)
    if not match or not isinstance(fact, dict):
        return None
    series, month = match.groups()
    value = fact.get("value")
    if (fact.get("series") != series or fact.get("month") != month or _month(month) is None
            or isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        return None
    return series, month, float(value)


@dataclass(frozen=True)
class IndexClaim:
    refs: tuple[str, str]
    change_pct: float

    def sentence(self, facts):
        """Recompute before rendering; reject a changed or unsupported assertion."""
        rows = [_index(ref, facts.get(ref)) for ref in self.refs]
        if any(row is None for row in rows):
            raise ValueError("unknown or malformed index fact")
        (series, start, before), (other, end, after) = rows
        change = (after / before - 1) * 100
        if (series != other or _month(end) - _month(start) != 12
                or not math.isfinite(self.change_pct)
                or not math.isclose(change, self.change_pct, abs_tol=1e-9)):
            raise ValueError("unsupported index assertion")
        return (f"The {series} index changed {change:+.2f}% from {start} to {end} "
                f"({self.refs[0]}, {self.refs[1]}).")


def cost_driver_series(package):
    """Base-package part/series links; weights are not external cost assertions."""
    if package.db is None:
        return {}
    links = {}
    for row in package.query("SELECT DISTINCT part_id, series_id FROM cost_drivers", limit=100000):
        links.setdefault(row["part_id"], set()).add(row["series_id"])
    return links


def index_claims(case, facts, series_by_part=None):
    """One recent year-on-year observation per case-referenced series, lowest first."""
    if case.get("type") != "price_increase":
        return []
    allowed = {m.group(1) for ref in case.get("refs", []) if (m := INDEX_ID.fullmatch(ref))}
    for part in case.get("parts", []):
        allowed.update((series_by_part or {}).get(part, ()))
    rows = {ref: row for ref, fact in facts.items() if (row := _index(ref, fact))}
    if not rows:
        return []
    latest = max(_month(row[1]) for row in rows.values())
    claims = []
    for series in sorted(allowed):
        candidates = sorted(((ref, row) for ref, row in rows.items() if row[0] == series),
                            key=lambda item: item[1][1], reverse=True)
        if not candidates:
            continue
        end_ref, (_, end, after) = candidates[0]
        start = f"{int(end[:4]) - 1:04d}{end[4:]}"
        start_ref = f"idx:{series}@{start}"
        if start_ref not in rows or latest - _month(end) > 12:
            continue
        change = (after / rows[start_ref][2] - 1) * 100
        if math.isfinite(change):
            claims.append(IndexClaim((start_ref, end_ref), change))
    return sorted(claims, key=lambda claim: (claim.change_pct, claim.refs))


def supplier_rejects_indices(events):
    """Conservative textual veto, not a claim about hidden supplier economics.

    Only supplier prose is inspected. A prior rejection keeps the index path off
    for this thread; no attempt is made to infer when a hedge expires.
    """
    for message in events:
        if message.get("from") == "buyer":
            continue
        body = (message.get("body") or "").lower()
        if re.search(r"\b(?:hedged|hedging|bought forward|fixed energy contract)\b", body):
            return True
        if re.search(r"\b(?:index|indices|market data)\b[^.!?\n]{0,100}"
                     r"(?:not relevant|irrelevant|do not reflect|does not reflect|not our costs)", body):
            return True
        if any(c.get("result") == "contradicted" for c in message.get("claim_results") or []):
            return True
    return False


def evidence_for_offer(case, package_facts, threads, limit=2, series_by_part=None, supplier_id=None):
    """Select unused citations across the case from confirmed buyer history.

    Repeated decisions on unchanged history produce the same message. Actual retry
    persistence and concurrent reservation remain the runtime's responsibility.
    """
    facts = {**package_facts, **(case.get("facts") or {})}
    if supplier_id is not None:
        events = threads.get(supplier_id, [])
        replies = [m for m in events if m.get("from") != "buyer"]
        if replies and replies[-1].get("status") in {"final_offer", "agreed", "walked_away", "no_bid"}:
            return []
        if supplier_rejects_indices(events):
            return []
    used = set()
    for events in threads.values():
        for message in events:
            if message.get("from") != "buyer":
                continue
            used.update(message.get("refs") or [])
            used.update(m.group(0) for m in re.finditer(
                r"idx:[A-Za-z0-9_-]+@\d{4}-\d{2}", message.get("body") or ""))
    selected = []
    for claim in index_claims(case, facts, series_by_part):
        # A positive input-price change supports the supplier unless we have a
        # verified cost decomposition. This candidate has no such decomposition.
        if claim.change_pct > 0:
            continue
        if used.intersection(claim.refs):
            continue
        if len(selected) >= min(2, max(0, limit)):
            break
        selected.append((claim, claim.sentence(facts)))
        used.update(claim.refs)
    return selected
