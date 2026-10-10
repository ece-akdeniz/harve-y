"""Opt-in, deterministic claim decoration; does not change the package policy.

Only single-supplier price-increase cases are enabled for the first experiment.
Reconstruct used IDs from buyer messages after resume. Reserve proposed IDs too:
skipping an unsent claim is preferable to consuming the same fact twice.
"""

from dataclasses import asdict

from arena_kit.cost import total_cost

from .claims import (
    DEFAULT_DISCLOSURE,
    MAX_CHECKED,
    case_facts,
    claim_keys,
    index_relevance,
    pick,
    public_rival_quotes,
    verify,
)
from .context import DATA_ERRORS, build_context, content_hash
from .dossiers import load_package


class EvidencePolicy:
    def __init__(self, package=None, tracer=None, case_types=None, rival_quote_types=(), index_window_types=()):
        self.case_types = set(case_types if case_types is not None else ["price_increase"])
        # Opt-in: disclose a documented, still-valid public rival quote for the case part when its
        # complete cost (case cost model) beats the supplier's standing sheet.
        self.rival_quote_types = set(rival_quote_types or ())
        # Opt-in: allow the verified buyer-favourable index window (<= 12 months, ending in the last 12)
        # for listed cost drivers whose latest 12-month change supports the supplier.
        self.index_window_types = set(index_window_types or ())
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

    def cheaper_rivals(self, case, events, sid):
        """Public rival quotes whose complete buyer cost beats the supplier's standing sheet."""
        if case.get("type") not in self.rival_quote_types:
            return []
        standing = next((e for e in reversed(events) if e.get("from") != "buyer" and e.get("term_sheets")), None)
        if standing is None:
            return []
        c_standing = min(total_cost(case, s.get("terms") or {}) for s in standing["term_sheets"])
        cited = {r for e in events if e.get("from") == "buyer" for r in e.get("refs") or []}
        out = []
        for claim, terms in public_rival_quotes(case, self.package):
            if claim.supplier_id != sid or set(claim.ids) & cited:
                continue
            c_rival = total_cost(case, terms)
            if c_rival < c_standing:
                out.append(claim)
            if self.tracer:
                self.tracer.log("rival_quote_check", case=case["case_id"], supplier=sid, ids=list(claim.ids),
                                c_rival=c_rival, c_standing=c_standing, cites=c_rival < c_standing)
        return out

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
            disclosures = DEFAULT_DISCLOSURE
            if case["type"] in self.index_window_types:  # only the most recent fall, never a stale window
                bank = [c for c in bank if not c.cherry_picked or c.note.startswith("recent buyer window")]
            rivals = self.cheaper_rivals(case, threads.get(sid, []), sid)
            if rivals:
                bank = [c for c in bank if c.kind != "rival_quote"] + rivals
                disclosures = DEFAULT_DISCLOSURE | {"reveals_rival"}
            priorities, reasons = index_relevance(bank, case, self.package, threads.get(sid, []))
            # Each pre-existing ref conservatively consumes one checked-claim slot.
            budget = max(0, MAX_CHECKED - len(existing))
            chosen = pick(
                bank, used, max_claims=budget, supplier_id=sid,
                case_type="renewal_trade" if case["type"] == "renewal" else case["type"],
                index_priorities=priorities, disclosures=disclosures,
                allow_cherry_pick=case["type"] in self.index_window_types,
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
