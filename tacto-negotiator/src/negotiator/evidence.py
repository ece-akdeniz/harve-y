"""Opt-in, deterministic claim decoration; does not change the package policy.

Only single-supplier price-increase cases are enabled for the first experiment.
Reconstruct used IDs from buyer messages after resume. Reserve proposed IDs too:
skipping an unsent claim is preferable to consuming the same fact twice.
"""

from dataclasses import asdict

from .claims import build_bank, case_facts, claim_keys, pick, verify
from .dossiers import load_package
from .ingestion import context_manifest, fingerprint
from .replies import evidence_constraints


class EvidencePolicy:
    def __init__(self, package=None, tracer=None, case_types=None):
        self.case_types = set(case_types if case_types is not None else ["price_increase"])
        self.package = package
        self.tracer = tracer
        self.banks = {}
        self.reserved = {}

    def enrich(self, case, threads, sid, move):
        message = move.get("message")
        if (
            case.get("type") not in self.case_types
            or len(case.get("suppliers", [])) != 1
            or not message
            or message.get("action")
            or not message.get("term_sheets")
        ):
            return move
        cid = case["case_id"]
        events = threads.get(sid, [])
        latest_supplier = next((m for m in reversed(events) if m.get("from") != "buyer"), {})
        if latest_supplier.get("status") in {"final_offer", "agreed", "walked_away", "no_bid"}:
            return move
        try:
            if self.package is None:
                self.package = load_package()
            bank_id = (cid, fingerprint(case.get("facts") or {}))
            if bank_id not in self.banks:
                self.banks[bank_id] = build_bank(case, self.package)
                if self.tracer and hasattr(self.package, "manifest"):
                    self.tracer.log("case_context", **context_manifest(case, self.package))
            facts = case_facts(case, self.package)
            used = set(self.reserved.get(cid, set()))
            for events in threads.values():
                for event in events:
                    if event.get("from") == "buyer":
                        used.update(event.get("refs") or [])
            interpretation, skip_kinds = evidence_constraints(events)
            rejected = set(interpretation["rejected_refs"])
            if self.tracer:
                self.tracer.log("reply_interpretation", case=cid, supplier=sid, **interpretation)
            if "*" in rejected:
                return move
            bank = [c for c in self.banks[bank_id] if verify(c, facts) and not rejected.intersection(c.ids)]
            chosen = pick(
                bank, used, supplier_id=sid, skip_kinds=skip_kinds,
                case_type="renewal_trade" if case["type"] == "renewal" else case["type"]
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if self.tracer:
                self.tracer.log("evidence_fallback", case=cid, error_type=type(exc).__name__)
            return move
        if not chosen:
            return move
        refs = list(dict.fromkeys([*(message.get("refs") or []), *(i for c in chosen for i in c.ids)]))
        self.reserved.setdefault(cid, set()).update(k for c in chosen for k in claim_keys(c))
        body = message.get("body", "") + "\n\n" + "\n".join(c.sentence for c in chosen)
        if self.tracer:
            self.tracer.log("evidence", case=cid, supplier=sid, claims=[asdict(c) for c in chosen])
        return {**move, "message": {**message, "body": body, "refs": refs}}
