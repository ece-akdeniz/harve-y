"""Verified D01/D02/P10 readiness through the existing Lab runner, never a second execution loop."""

from datetime import timedelta
from decimal import Decimal

from ..core import models as m
from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash
from .lab import LocalV2LabAgent


class VerifiedOnlineV2LabAgent(LocalV2LabAgent):
    local_only = False
    requires_complete_history = True
    requires_bounded_terminal_collection = True
    version = "v2-lab-hosted/2"

    def __init__(self, *, execution_allowance, **kwargs):
        if (
            execution_allowance.get("authorized") is not True
            or execution_allowance.get("environment") not in {"sandbox", "practice"}
            or execution_allowance.get("online_sessions") != 1
            or execution_allowance.get("retries") != 0
            or execution_allowance.get("max_calls") not in {18, 36}
            or execution_allowance.get("max_total_reserved_tokens") != execution_allowance.get("max_calls", 0) * 98304
            or execution_allowance.get("max_usd") not in {"1.00", "2.00"}
            or not (execution_allowance.get("offline_verification") is True
                    or execution_allowance.get("direct_sandbox_validation") is True
                    and execution_allowance.get("environment") == "sandbox")
            or execution_allowance.get("remote_lab_verified") is not True
        ):
            raise ContractViolation("unsupported_capability: exact single-session online approval and gates required")
        if kwargs.get("transport") is None or kwargs.get("model_config") is None or kwargs.get("arm") != "adaptive":
            raise ContractViolation("unsupported_capability: authorized real model strategy required online")
        super().__init__(closing_authority=True, **kwargs)
        if (
            self.model_config.provider_id == "local-fixture"
            or self.model_config.base_url.startswith("http:")
            or execution_allowance.get("model_id") != self.model_config.model_id
            or getattr(self.transport, "max_calls", None) != execution_allowance["max_calls"]
            or getattr(self.transport, "max_usd", None) != Decimal(execution_allowance["max_usd"])
        ):
            raise ContractViolation("unsupported_capability: online model/allowance configuration mismatch")
        if execution_allowance.get("case_hash") != semantic_hash(self.dataset["case"]):
            raise ContractViolation("scope_mismatch: online allowance differs from reviewed case")
        cid = self.dataset["case"]["case_id"]
        if execution_allowance.get("direct_sandbox_validation") is True and cid != "case:D01":
            raise ContractViolation("unsupported_capability: direct first-stage approval is scoped to D01")
        expected = {"case:D01": ("sandbox", 18, "1.00"),
                    "case:D02": ("sandbox", 36, "2.00"),
                    "case:P10": ("practice", 18, "1.00")}.get(cid)
        if expected != (execution_allowance["environment"], execution_allowance["max_calls"],
                        execution_allowance["max_usd"]):
            raise ContractViolation("unsupported_capability: case-specific allowance mismatch")
        self.execution_allowance = execution_allowance
        self.observed_server = None

    def validate_lab_case(self, case):
        # Catalog identity is checked before POST. Each reviewed case retains its own
        # options, price basis, alternative and buyer defaults.
        if case != self.dataset["case"]:
            raise ContractViolation("unsupported_capability: server case differs from reviewed hosted contract")

    def observe_lab_server_state(self, state, *, requested_at, received_at):
        if (
            state.get("session_id") != self.session_id
            or state.get("case_id") != self.dataset["case"]["case_id"]
            or state.get("status") not in {"open", "ended"}
        ):
            raise ContractViolation("scope_mismatch: foreign or unidentified server observation")
        self.observed_server = state, requested_at, received_at

    def decide(self, case, threads):
        if self.observed_server is None:
            raise ContractViolation("missing_source: online decision requires an authoritative session read")
        raw, _, _ = self.observed_server
        if raw["status"] != "open":
            raise ContractViolation("invalid_terminal_proof: ended session cannot receive another action")
        return super().decide(case, threads)

    def normalize_live_inputs(self, inputs, supplier):
        raw, requested_at, received_at = self.observed_server
        live = raw["threads"][supplier]
        rounds, seconds = self.thread_rounds(supplier), live.get("seconds_left")
        if type(rounds) is not int or rounds < 0 or not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            raise ContractViolation("rounds_unknown: missing authoritative online rounds/clock")
        if live.get("offer_id") != inputs.server.threads[0].standing_offer_id:
            raise ContractViolation("stale_state: standing offer differs between session and thread reads")
        if Decimal(str(seconds)) <= 0 or rounds >= inputs.case.round_limit:
            raise ContractViolation("deadline_exhausted: no admitted online decision window")
        ref = "sha256:" + semantic_hash(raw)
        deadline = requested_at + timedelta(seconds=float(seconds))
        thread = inputs.server.threads[0].model_copy(
            update={
                "rounds": m.RoundEvidence(
                    limit=inputs.case.round_limit,
                    server_rounds_used=rounds,
                    accepted_buyer_messages=inputs.server.threads[0].rounds.accepted_buyer_messages,
                    confidence="authoritative",
                    source_ref=ref,
                ),
                "clock": m.ClockEvidence(
                    kind="thread",
                    snapshot_requested_at=requested_at,
                    snapshot_received_at=received_at,
                    seconds_left=Decimal(str(seconds)),
                    conservative_deadline_at=deadline,
                    confidence="conservative",
                    source_ref=ref,
                ),
            }
        )
        server = inputs.server.model_copy(
            update={"threads": (thread,), "observed_at": received_at, "observation_hash": semantic_hash(raw)}
        )
        state = inputs.state.model_copy(update={"server": server})
        budget = inputs.budget.model_copy(update={"deadline_at": min(deadline, inputs.budget.deadline_at)})
        from .arena_observations import with_quote_standards

        normalized = inputs.model_copy(update={"server": server, "state": state, "budget": budget})
        return with_quote_standards(normalized, self.authoritative_threads[supplier], supplier_id=supplier,
                                    now=received_at) if supplier in self.authoritative_threads else normalized

    def validate_lab_dispatch(self, supplier_id, message, current_thread):
        raw, requested_at, _ = self.observed_server
        live = raw["threads"][supplier_id]
        seconds = live.get("seconds_left")
        rounds = self.thread_rounds(supplier_id)
        if (
            raw.get("status") != "open"
            or type(rounds) is not int
            or not message.get("action") and rounds >= self.dataset["case"]["round_limit"]
            or not isinstance(seconds, (float, int))
            or isinstance(seconds, bool)
            or seconds <= 0
            or self.clock.utcnow() >= requested_at + timedelta(seconds=seconds)
        ):
            raise ContractViolation("deadline_exhausted: online dispatch lacks a current server window")
        expected_rounds = sum(e.get("from") == "buyer" for e in self.authoritative_threads[supplier_id])
        if rounds != expected_rounds:
            raise ContractViolation("stale_state: server-counted rounds changed or include unprocessed timeouts")
        if message.get("action", {}).get("type") == "accept" and (
            message["action"]["term_sheet_id"] != live.get("offer_id")
        ):
            raise ContractViolation("stale_state: live standing offer changed before closing")
        if message.get("action"):
            if self.pending_message != {"supplier_id": supplier_id, "message": message}:
                raise ContractViolation("invalid_schema: closing payload changed")
            self.closing.validate(self.pending_message, case=self.dataset["case"],
                                  threads=self.closing_threads(supplier_id, current_thread["messages"]))
            return
        return super().validate_lab_dispatch(supplier_id, message, current_thread)

    def validate_lab_http_dispatch(self, supplier_id, message, intent):
        # The full remote refresh/history validation ran immediately before intent
        # persistence. Recheck only the already observed local clock here, after fsync.
        super().validate_lab_http_dispatch(supplier_id, message, intent)
        if self.observed_server is None:
            raise ContractViolation("missing_source: no owned server clock for HTTP dispatch")
        raw, requested_at, _ = self.observed_server
        live = raw.get("threads", {}).get(supplier_id, {})
        seconds = live.get("seconds_left")
        if (raw.get("status") != "open" or not isinstance(seconds, (int, float))
                or isinstance(seconds, bool) or seconds <= 0
                or self.clock.utcnow() >= requested_at + timedelta(seconds=seconds)):
            raise ContractViolation("deadline_exhausted: online permit expired before HTTP dispatch")

    def thread_rounds(self, supplier):
        raw, _, _ = self.observed_server
        if type(raw.get("rounds")) is not int:
            raise ContractViolation("rounds_unknown: missing authoritative rounds/clock")
        if len(self.dataset["case"]["suppliers"]) == 1:
            return raw["rounds"]
        # Arena session rounds sum per-thread moves. Timeouts cannot be assigned from
        # that sum, so require the exact acknowledged total before admitting a move.
        counts = {sid: sum(e.get("from") == "buyer" for e in events)
                  for sid, events in self.authoritative_threads.items()}
        if set(counts) != set(self.dataset["case"]["suppliers"]) or sum(counts.values()) != raw["rounds"]:
            raise ContractViolation("stale_state: RFQ rounds require complete acknowledged histories without timeouts")
        return counts[supplier]

    def closing_threads(self, supplier, events):
        return {**self.authoritative_threads, supplier: events}

    def select_lab_supplier(self, case, threads):
        raw, _, _ = self.observed_server
        eligible = [sid for sid in case["suppliers"]
                    if raw["threads"][sid].get("status") not in {"walked_away", "no_bid", "ended"}]
        if not eligible:
            raise ContractViolation("invalid_terminal_proof: no live supplier; retrieve terminal result")
        return min(eligible, key=lambda sid: (self.thread_rounds(sid), raw["threads"][sid]["seconds_left"], sid))

    def decision_dataset(self, supplier):
        # The arithmetic oracle remains one-supplier/one-part. Each target receives a
        # faithful economic slice; the case coordinator compares every live bidder.
        case = {**self.dataset["case"], "suppliers": [supplier]}
        candidates = self.dataset.get("candidate_terms_by_supplier", {}).get(supplier, self.dataset["candidate_terms"])
        return {**self.dataset, "case": case, "candidate_terms": candidates}

    def should_close(self, case, supplier, events, count):
        raw, requested_at, _ = self.observed_server
        elapsed = (self.clock.utcnow() - requested_at).total_seconds()
        live = [sid for sid in case["suppliers"]
                if raw["threads"][sid].get("status") in {"open", "final_offer", "agreed"}]
        if any(raw["threads"][sid]["seconds_left"] - elapsed <= 15 for sid in live):
            return True
        interviewed = all(self.thread_rounds(sid) > 0 for sid in live)
        return (count >= case["round_limit"] - 1 or
                interviewed and any(raw["threads"][sid].get("status") == "agreed" for sid in live))

    def prior_market_evidence(self, supplier):
        # Public observed rival packages inform internal comparison only. Renderer
        # sends validated own packages; it does not disclose these notes to suppliers.
        import json

        return ("Buyer category goal: " + self.dataset["case"]["buyer"]["category_goal"] +
                "; supplier full costs are unestimated; do not infer a hidden floor or sustainable margin.",) + tuple(
                     "Observed rival standing package: " + json.dumps({"supplier_id": sid,
                     "term_sheets": events[-1].get("term_sheets", [])}, sort_keys=True)
                     for sid, events in self.authoritative_threads.items() if sid != supplier and events)

    def observe_lab_outcome(self, result, threads):
        import json

        from arena_kit.docs import read_document

        from negotiator.lab.publish import _atomic_file

        from .arena_observations import conversation_from_arena

        conversations = {}
        for sid, thread in threads.items():
            for event in thread["messages"]:
                for att in event.get("attachments", []):
                    att["text"] = read_document(att["name"], self.attachment_bytes[att["attachment_id"]])
            conversations[sid] = conversation_from_arena(self.dataset["case"], thread["messages"],
                session_id=self.session_id, supplier_id=sid, now=self.clock.utcnow(),
                attachment_bytes=self.attachment_bytes).model_dump(mode="json")
        self.terminal_evidence = {"state": self.terminal_state, "result": result, "conversations": conversations}
        _atomic_file(self.trace_root / self.run_id / self.session_id / "terminal-observation.json",
                     json.dumps(self.terminal_evidence, indent=2))

    def experiment_evidence(self):
        import json

        evidence = super().experiment_evidence()
        evidence["observations_json"] = [o.model_dump_json() for o in self.observations]
        evidence["terminal_json"] = json.dumps(getattr(self, "terminal_evidence", None), sort_keys=True)
        evidence["inference_ledger_json"] = json.dumps(getattr(self.transport, "calls", []), sort_keys=True)
        return evidence
