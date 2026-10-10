"""Opt-in, deterministic claim decoration; does not change the package policy.

Only single-supplier price-increase cases are enabled for the first experiment.
Reconstruct used IDs from buyer messages after resume. Reserve proposed IDs too:
skipping an unsent claim is preferable to consuming the same fact twice.
"""

from dataclasses import asdict

from .claims import MAX_CHECKED, case_facts, claim_keys, index_relevance, pick, recent_index_claims, verify
from .context import DATA_ERRORS, build_context, content_hash
from .dossiers import load_package


class EvidencePolicy:
    def __init__(self, package=None, tracer=None, case_types=None, recent_window_types=()):
        self.recent_window_types = set(recent_window_types)
        self.case_types = set(case_types if case_types is not None else ["price_increase"]) | self.recent_window_types
        self.package = package
        self.tracer = tracer
        self.banks = {}
        self.contexts = {}
        self.context_keys = {}
        self.reserved = {}

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

    def enrich(self, case, threads, sid, move, context=None):
        message = move.get("message")
        if not self.eligible(case, move):
            return move
        cid = case["case_id"]
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
            bank = [c for c in context.candidates if verify(c, facts, self.package, case)]
            recent = case["type"] in self.recent_window_types
            if recent:  # only public index claims over windows ending at the latest month
                bank = [c for c in recent_index_claims(case, self.package, facts)
                        if verify(c, facts, self.package, case)]
            priorities, reasons = index_relevance(bank, case, self.package, threads.get(sid, []))
            # Each pre-existing ref conservatively consumes one checked-claim slot.
            budget = max(0, MAX_CHECKED - len(existing))
            chosen = pick(
                bank, used, max_claims=budget, supplier_id=sid,
                case_type="renewal_trade" if case["type"] == "renewal" else case["type"],
                index_priorities=priorities, allow_cherry_pick=recent,
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
