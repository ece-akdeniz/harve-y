"""Scoped closing authority through the existing shared evaluator and guards."""

from arena_kit.docs import standard_terms

from negotiator.evaluator import close_decision, eligible_sheets, supplier_for
from negotiator.guards import check

from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash


class ScopedClosingAuthority:
    def __init__(self, *, run_id, session_id, case_hash):
        self.run_id, self.session_id, self.case_hash = run_id, session_id, case_hash

    def decide(self, *, run_id, session_id, case, threads, estimates=None, reason):
        if run_id != self.run_id or session_id != self.session_id or semantic_hash(case) != self.case_hash:
            raise ContractViolation("scope_mismatch: closing authority belongs to another case/session")
        proposal = close_decision(case, threads, estimates, reason)
        return self.validate(proposal, case=case, threads=threads, estimates=estimates)

    def validate(self, proposal, *, case, threads, estimates=None):
        # Independently recompute every standing sheet and complete official cost.
        expected = close_decision(case, threads, estimates, "independent-validation")
        if proposal != expected:
            raise ContractViolation("infeasible: close differs from independent all-thread comparison")
        supplier = proposal["supplier_id"]
        action = proposal["message"]["action"]
        if action["type"] == "accept":
            eligible = eligible_sheets(
                case, threads[supplier], supplier_for(estimates, supplier, standard_terms(threads[supplier]))
            )
            if not any(sheet_id == action["term_sheet_id"] for _, sheet_id, _ in eligible):
                raise ContractViolation("scope_mismatch: acceptance is not the recipient's standing offer")
        check(case, supplier, proposal["message"], threads, {"estimates": estimates})
        return proposal
