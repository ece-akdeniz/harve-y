"""Opt-in, deterministic claim decoration; does not change the package policy.

Only single-supplier price-increase cases are enabled for the first experiment.
Reconstruct used IDs from buyer messages after resume. Reserve proposed IDs too:
skipping an unsent claim is preferable to consuming the same fact twice.
"""

from dataclasses import asdict

from .claims import MAX_CHECKED, case_facts, claim_keys, index_relevance, pick, verify
from .context import DATA_ERRORS, build_context, content_hash
from .dossiers import load_package
from .replies import evidence_constraints


class EvidencePolicy:
    def __init__(self, package=None, tracer=None, case_types=None, interpretation=None):
        self.case_types = set(case_types if case_types is not None else ["price_increase"])
        self.package = package
        self.tracer = tracer
        self.banks = {}
        self.contexts = {}
        self.context_keys = {}
        self.reserved = {}
        self.interpretation = interpretation

    def eligible(self, case, move):
        message = move.get("message") or {}
        return (
            case.get("type") in self.case_types
            and len(case.get("suppliers", [])) == 1
            and bool(message.get("term_sheets"))
            and not message.get("action")
        )

    def context_for(self, case):
        """Prepare/cache a snapshot; no selection, reservations or sends."""
        if self.package is None:
            self.package = load_package()
        cid = case["case_id"]
        key = content_hash({"case": case, "facts": self.package.facts})
        if self.context_keys.get(cid) != key:
            context = build_context(case, self.package)
            self.contexts[cid] = context
            self.context_keys[cid] = key
            self.banks[cid] = context.candidates
            if self.tracer:
                self.tracer.log("evidence_context", case=cid, context_version=context.version,
                                context=context.to_dict())
        return self.contexts[cid]

    def fallback(self, case, exc):
        if self.tracer:
            self.tracer.log("evidence_fallback", case=case["case_id"], error_type=type(exc).__name__)

    def enrich(self, case, threads, sid, move, context=None, rfq_claims=0):
        """`rfq_claims` > 0 enables RFQ (multi-supplier) decoration with at most that many claims,
        excluding our internal should-cost; the single-supplier gate stays for every other path."""
        message = move.get("message")
        rfq = rfq_claims > 0 and case.get("type") == "rfq"
        if rfq:
            if not message or not message.get("term_sheets") or message.get("action"):
                return move
        elif not self.eligible(case, move):
            return move
        cid = case["case_id"]
        events = threads.get(sid, [])
        latest_supplier = next((m for m in reversed(events) if m.get("from") != "buyer"), {})
        if latest_supplier.get("status") in {"final_offer", "agreed", "walked_away", "no_bid"}:
            return move
        try:
            context = context if context is not None else self.context_for(case)
            if (
                context.case_id != cid
                or context.supplier_ids != tuple(case.get("suppliers") or [])
                or context.part_ids != tuple(case.get("parts") or [])
            ):
                raise ValueError("context scope mismatch")
            facts = case_facts(case, self.package)
            used = set(self.reserved.get(cid, set()))
            for events in threads.values():
                for event in events:
                    if event.get("from") == "buyer":
                        used.update(event.get("refs") or [])
            existing = set(message.get("refs") or [])
            used.update(existing)
            interpretation, skip_kinds = evidence_constraints(
                events, self.interpretation.get(sid) if self.interpretation else None
            )
            skip_kinds.update(lesson["avoid_claim_kind"] for lesson in interpretation.get("lessons", [])
                              if lesson.get("avoid_claim_kind"))
            rejected = set(interpretation["rejected_refs"])
            if self.tracer:
                self.tracer.log("reply_interpretation", case=cid, supplier=sid, **interpretation)
            if "*" in rejected:
                return move
            bank = [c for c in context.candidates if verify(c, facts, self.package, case)
                    and not rejected.intersection(c.ids) and c.kind not in skip_kinds]
            priorities, reasons = index_relevance(bank, case, self.package, threads.get(sid, []))
            # Each pre-existing ref conservatively consumes one checked-claim slot.
            budget = max(0, MAX_CHECKED - len(existing))
            if rfq:
                budget = min(budget, rfq_claims)
            chosen = pick(
                bank, used, max_claims=budget, supplier_id=sid,
                case_type="renewal_trade" if case["type"] == "renewal" else case["type"],
                index_priorities=priorities,
                skip_kinds=frozenset({"should_cost"}) if rfq else frozenset(),
            )
        except DATA_ERRORS as exc:
            self.fallback(case, exc)
            return move
        if self.tracer:
            self.tracer.log("evidence_selection", case=cid, supplier=sid, context_version=context.version,
                            index_relevance=reasons, available_slots=budget,
                            selected=[{"kind": c.kind, "ids": list(c.ids)} for c in chosen])
        if not chosen:
            return move
        refs = list(dict.fromkeys([*(message.get("refs") or []), *(i for c in chosen for i in c.ids)]))
        self.reserved.setdefault(cid, set()).update(k for c in chosen for k in claim_keys(c))
        body = message.get("body", "") + "\n\n" + "\n".join(c.sentence for c in chosen)
        if self.tracer:
            self.tracer.log("evidence", case=cid, supplier=sid, context_version=context.version,
                            claims=[asdict(c) for c in chosen])
        return {**move, "message": {**message, "body": body, "refs": refs}}
