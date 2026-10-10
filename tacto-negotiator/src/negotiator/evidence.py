"""Opt-in, deterministic claim decoration; does not change the package policy.

Only single-supplier price-increase cases are enabled for the first experiment.
Reconstruct used IDs from buyer messages after resume. Reserve proposed IDs too:
skipping an unsent claim is preferable to consuming the same fact twice.
"""

from dataclasses import asdict

from .claims import build_bank, case_facts, claim_keys, pick, verify
from .dossiers import load_package


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
        try:
            if cid not in self.banks:
                if self.package is None:
                    self.package = load_package()
                self.banks[cid] = build_bank(case, self.package)
            facts = case_facts(case, self.package)
            used = set(self.reserved.get(cid, set()))
            for events in threads.values():
                for event in events:
                    if event.get("from") == "buyer":
                        used.update(event.get("refs") or [])
            bank = [c for c in self.banks[cid] if verify(c, facts)]
            chosen = pick(
                bank, used, supplier_id=sid, case_type="renewal_trade" if case["type"] == "renewal" else case["type"]
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
