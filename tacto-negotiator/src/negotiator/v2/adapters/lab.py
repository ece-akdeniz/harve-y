"""Local-only P10 bridge to the Lab's existing decide(case, threads) interface.

No closing authority, provider credentials or remote execution.
The simulator must terminate the session; this bridge only sends validated offers/questions.
"""

import asyncio
import hashlib
import json
import os
import re
import threading
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from ..core import models as m
from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash
from .chat_completions import ChatCompletionConfig
from .offline import OfflineRecordedInputs
from .p10 import recorded_p10


def _run_decision_bounded(coroutine, *, timeout_s):
    """Keep asyncio.run teardown off the synchronous Lab callback's deadline."""
    completed = threading.Event()
    result = {}

    def execute():
        try:
            result["value"] = asyncio.run(coroutine)
        except BaseException as error:  # returned to the owning thread below
            result["error"] = error
        finally:
            completed.set()

    worker = threading.Thread(target=execute, name="v2-decision", daemon=True)
    worker.start()
    if not completed.wait(max(0.001, timeout_s)):
        raise ContractViolation("deadline_exhausted: complete decision exceeded its original budget")
    if "error" in result:
        raise result["error"]
    return result["value"]


class _ModelCallGate:
    """Run-wide stop bit exposed to the per-decision ledger without owning dispatch."""

    def __init__(self, transport):
        self.transport = transport
        self.stopped = bool(getattr(transport, "stopped", False))

    def stop_model_calls(self, reason):
        self.stopped = True
        stopper = getattr(self.transport, "stop_model_calls", None)
        if callable(stopper):
            stopper(reason)

    async def __call__(self, request, budget):
        if self.stopped:
            return m.ModelCapacityUnavailable(
                kind="capacity_unavailable",
                call_id=request.call_id,
                model_id=request.model_id,
                elapsed_s=Decimal("0"),
                issues=(m.Issue(code="unsupported_capability", severity="error", component="model", refs=(),
                                detail="model call gate is disabled"),),
            )
        return await self.transport(request, budget)


class WallClock:
    def utcnow(self):
        return datetime.now(UTC)

    def monotonic(self):
        return time.monotonic()


class LocalFixtureTransport:
    """Scripted ambiguity/minimum responses; measures plumbing, never model intelligence."""

    async def __call__(self, request, budget):
        if request.task == "interpret":
            observations = []
            for index, msg in enumerate(request.input.conversation.messages):
                if not msg.body or msg.speaker != "supplier":
                    continue
                span = m.MessageSpan(
                    session_id=msg.session_id,
                    thread_id=msg.thread_id,
                    message_id=msg.message_id,
                    start=0,
                    end=len(msg.body),
                    quote=msg.body,
                )
                observations.append(
                    m.GroundedObservation(
                        observation_id=f"observation:{index}",
                        kind="ambiguity",
                        dimension=None,
                        summary=msg.body,
                        citations=(span,),
                    )
                )
            response = m.AssessmentDraft(
                observations=tuple(observations),
                reported_constraints=(),
                hypotheses=(),
                uncertainties=(),
                questions=(),
                unknowns=(),
            )
        else:
            # Read the authoritative zero delta; perform no economic arithmetic.
            choices = [
                o
                for o in request.input.options
                if re.search(r"cost delta from cheapest=0(?:\.0+)? [A-Z]{3}(?:;|$)", o.summary)
            ]
            if not choices:
                raise ContractViolation("unsupported_capability: fixture expects an official minimum offer")
            response = m.SelectorResponse(selected_id=min(o.candidate_id for o in choices), supporting_quote="")
        raw = response.model_dump_json()
        if request.task == "interpret" and request.prompt_version.endswith("-v3"):
            data = json.loads(raw)
            for obs in data["observations"]:
                span = obs["citations"][0]
                obs["citations"] = [
                    next(key for key, value in request.input.citation_catalog if value.message_id == span["message_id"])
                ]
            raw = json.dumps(data)
        return m.ModelSuccess(
            kind="success",
            call_id=request.call_id,
            model_id=request.model_id,
            elapsed_s=Decimal("0"),
            issues=(),
            raw_response_json=raw,
            response_hash=hashlib.sha256(raw.encode()).hexdigest(),
            usage=m.ModelUsage(),
        )


class AdaptiveFixtureTransport(LocalFixtureTransport):
    """Offline authored control only: reads public sheets/history, never simulator internals."""

    async def __call__(self, request, budget):
        if request.task != "propose":
            return await super().__call__(request, budget)
        source = request.input
        supplier = [
            s
            for msg in source.conversation.messages
            if msg.speaker == "supplier"
            for s in msg.observed_sheets
            if s.standing
        ]
        buyers = [s for msg in source.conversation.messages if msg.speaker == "buyer" for s in msg.observed_sheets]
        if not supplier:
            raise ContractViolation("missing_source: control requires a public supplier offer")
        terms = {t.field: t.value for t in supplier[-1].complete_bindings}
        price = terms["unit_price"]
        # This fixture deliberately exercises new terms and multi-round change; it is not a strategy claim.
        prior = next((t.value for t in buyers[-1].bindings if t.field == "unit_price"), None) if buyers else None
        terms["unit_price"] = ((price + prior) / 2 if prior else price * Decimal("0.96")).quantize(Decimal("0.01"))
        options = {o.field: o.values for o in source.options}
        terms["volume_per_year"] = max(options["volume_per_year"])
        terms["contract_months"] = 24
        terms["lead_time_days"] = 42
        from ..economics.effects import expected_trade_labels
        from .p10 import term_binding

        requests, offers = (), ()
        if source.commercial_reference.kind == "observed_supplier_offer":
            _, requests, offers = expected_trade_labels(source.commercial_reference,
                tuple(m.TermBinding(field=k, value=terms[k]) for k in source.negotiable_fields))
        response_body = {
            "bindings": [term_binding(k, terms[k]) for k in source.negotiable_fields],
            "citation_ids": [source.citation_catalog[-1][0]] if buyers and source.citation_catalog else [],
            "rationale": "Authored control revises price from the public supplier offer and buyer history.",
        }
        if request.task_schema_version == "proposal-response-v2":
            response_body.update({"buyer_requests": sorted(requests), "buyer_offers": sorted(offers),
                                  "supplier_value_unknown": tuple(source.negotiable_fields)})
        contract = (
            m.ProposalResponseV3
            if request.task_schema_version == "proposal-response-v3"
            else m.ProposalResponseV2
        )
        response = contract.model_validate_json(json.dumps(response_body, default=str))
        raw = response.model_dump_json()
        return m.ModelSuccess(
            kind="success",
            call_id=request.call_id,
            model_id=request.model_id,
            elapsed_s=Decimal("0"),
            issues=(),
            raw_response_json=raw,
            response_hash=hashlib.sha256(raw.encode()).hexdigest(),
            usage=m.ModelUsage(),
        )


class LocalV2LabAgent:
    local_only = True
    version = "v2-lab-p10-local/1"

    def __init__(
        self,
        *,
        dataset_path,
        trace_root,
        arm="grounded",
        clock=None,
        transport=None,
        runtime_builder=None,
        run_decision=None,
        metrics=None,
        closing_authority=False,
        model_config=None,
    ):
        if arm not in {"minimum", "direct", "grounded", "adaptive"}:
            raise ValueError("unknown bounded strategy arm")
        if runtime_builder is None or run_decision is None or metrics is None:
            raise ValueError("instantiate the Lab adapter through the V2 factory")
        self.runtime_builder, self.run_decision, self.metrics = runtime_builder, run_decision, metrics
        self.dataset = json.loads(Path(dataset_path).read_text())
        self.arm, self.clock = arm, clock or WallClock()
        if model_config is not None and transport is None:
            raise ValueError("a hosted model configuration requires an explicitly authorized transport")
        if isinstance(model_config, dict):
            model_config = ChatCompletionConfig(**model_config).checked()
        self.transport = transport or (AdaptiveFixtureTransport() if arm == "adaptive" else LocalFixtureTransport())
        self.model_transport = _ModelCallGate(self.transport)
        self.closing_enabled = closing_authority
        self.closing_events = []
        self.model_config = model_config
        self.pending_message = None
        self.trace_root = Path(trace_root)
        self.traces = []
        self.baseline_evaluations = []
        self.attachment_bytes = {}
        self.observations = []
        self.authoritative_threads = {}
        self.previous = None
        self.observation = None
        self.session_id = None
        self.run_id = None
        self.terminal_state = None
        self.supplier_memory = {}
        self.execution_revoked = False

    def select_lab_supplier(self, case, threads):
        return case["suppliers"][0]

    def decision_dataset(self, supplier):
        return self.dataset

    def closing_threads(self, supplier, events):
        return {supplier: events}

    def prior_market_evidence(self, supplier):
        return ()

    def should_close(self, case, supplier, events, count):
        return count >= case["round_limit"] - 1 or any(e.get("status") == "agreed" for e in events[-1:])

    def observe_lab_terminal(self, state):
        if state.get("status") != "ended" or state.get("session_id") != self.session_id:
            raise ContractViolation("invalid_terminal_proof: owned session has no authoritative terminal state")
        self.terminal_state = state

    def observe_lab_acknowledgement(self, supplier_id, thread):
        # Fresh remote histories omit locally decoded attachment text. Normalize both
        # the acknowledged history and final dispatch read from the same owned bytes.
        from arena_kit.docs import read_document

        for event in thread["messages"]:
            for attachment in event.get("attachments", []):
                if "text" not in attachment and attachment["attachment_id"] in self.attachment_bytes:
                    attachment["text"] = read_document(
                        attachment["name"], self.attachment_bytes[attachment["attachment_id"]]
                    )
        self.authoritative_threads[supplier_id] = thread["messages"]

    def observe_lab_attachment(self, attachment_id, content):
        self.attachment_bytes[attachment_id] = content

    def observe_lab_session(self, run_id, session_id):
        """Identity supplied by RecordingTable after the actual session is opened."""
        if self.session_id is not None:
            raise ContractViolation("scope_mismatch: one agent per Lab attempt")
        self.run_id, self.session_id = run_id, session_id
        if self.closing_enabled:
            from .closing import ScopedClosingAuthority

            self.closing = ScopedClosingAuthority(
                run_id=run_id, session_id=session_id, case_hash=semantic_hash(self.dataset["case"])
            )

    def decide(self, case, threads):
        if self.execution_revoked:
            raise ContractViolation("recovery_required: previous decision exceeded its execution window")
        if case != self.dataset["case"] or not self.session_id:
            raise ContractViolation("unsupported_capability: reviewed P10 local Lab session required")
        supplier = self.select_lab_supplier(case, threads)
        self.previous, self.observation = self.supplier_memory.get(supplier, (None, None))
        events = self.authoritative_threads.get(supplier, threads[supplier])
        # Hydrate authoritative reads from bytes already downloaded by the kit.
        from arena_kit.docs import read_document

        for event in events:
            for att in event.get("attachments", []):
                if "text" not in att and att["attachment_id"] in self.attachment_bytes:
                    att["text"] = read_document(att["name"], self.attachment_bytes[att["attachment_id"]])
        count = sum(e.get("from") == "buyer" for e in events)
        authoritative_final = any(e.get("status") == "final_offer" for e in events[-1:])
        from ..core.question_actions import QUESTION_TEMPLATES

        clarification_exhausted = any(
            event.get("from") == "buyer"
            and any(template in event.get("body", "") for template in QUESTION_TEMPLATES.values())
            for event in events
        )
        if (
            clarification_exhausted
            and not self.closing_enabled
            and not self.should_close(case, supplier, events, count)
        ):
            raise ContractViolation(
                "unsupported_capability: clarification exhausted; shared closing authority required"
            )
        if authoritative_final and not self.closing_enabled:
            raise ContractViolation(
                "unsupported_capability: authoritative final offer requires shared closing authority"
            )
        if self.closing_enabled and (
            authoritative_final or clarification_exhausted or self.should_close(case, supplier, events, count)
        ):
            close_reason = (
                "authoritative-final-offer" if authoritative_final else
                "clarification-exhausted" if clarification_exhausted else
                "agreed-or-reserved-final-round"
            )
            result = self.closing.decide(
                run_id=self.run_id,
                session_id=self.session_id,
                case=case,
                threads=self.closing_threads(supplier, events),
                reason=close_reason,
            )
            self.closing_events.append(
                {"state_hash": semantic_hash(events), "decision": result, "reason": close_reason}
            )
            directory = self.trace_root / self.run_id / self.session_id
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            (directory / "closing.json").write_text(json.dumps(self.closing_events))
            self.pending_message = result
            return result
        if count >= case["round_limit"]:
            raise ContractViolation("unsupported_capability: V2 closing authority remains unavailable")
        if self.observation is not None and supplier not in self.authoritative_threads:
            raise ContractViolation("recovery_required: no authoritative action acknowledgement")
        observation = semantic_hash(events)
        if observation == self.observation:
            raise ContractViolation("recovery_required: duplicate observation requires reconciliation")
        now = self.clock.utcnow()
        supplier_events = [(i, e) for i, e in enumerate(events) if e.get("from") != "buyer"]
        # The recorded seed supplies the reviewed case and finite candidate universe.
        # The Arena observation below supplies the actual public negotiation history.
        bodies = [e.get("body", "") for _, e in supplier_events]
        dataset = {**self.decision_dataset(supplier), "supplier_messages": bodies}
        inputs = recorded_p10(dataset, message=bodies[-1], now=now, model_call_limit=0 if self.arm == "minimum" else 2)
        from .arena_observations import conversation_from_arena

        conversation = conversation_from_arena(
            case,
            events,
            session_id=self.session_id,
            supplier_id=supplier,
            now=now,
            attachment_bytes=self.attachment_bytes,
        )
        directory = self.trace_root / self.run_id / self.session_id
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        decision_index = len(self.traces)
        observation_path = directory / f"observation-{decision_index:03d}.json"
        with os.fdopen(os.open(observation_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
            output.write(conversation.model_dump_json())
        self.observations.append(conversation)
        thread = inputs.server.threads[0].model_copy(
            update={
                "thread_id": conversation.thread_id,
                "conversation": conversation,
                "status": conversation.status,
                "standing_offer_id": next(
                    (s.offer_id for msg in reversed(conversation.messages) for s in msg.observed_sheets if s.standing),
                    None,
                ),
                "rounds": inputs.server.threads[0].rounds.model_copy(
                    update={
                        "accepted_buyer_messages": count,
                        "conservative_remaining": case["round_limit"] - count,
                    }
                ),
            }
        )
        server = inputs.server.model_copy(
            update={
                "session_id": self.session_id,
                "threads": (thread,),
                "observation_hash": observation,
            }
        )
        strategic = inputs.state.strategic.model_copy(
            update={
                "assessments": (self.previous,) if self.previous else (),
            }
        )
        state = inputs.state.model_copy(
            update={
                "run_id": self.run_id,
                "server": server,
                "version": count,
                "strategic": strategic,
                "config_hash": semantic_hash((self.version, self.arm, self.dataset)),
            }
        )
        inputs = OfflineRecordedInputs.model_validate_json(
            inputs.model_copy(
                update={
                    "server": server,
                    "state": state,
                    "previous_assessment": self.previous,
                }
            ).model_dump_json()
        )
        normalizer = getattr(self, "normalize_live_inputs", None)
        if callable(normalizer):
            inputs = OfflineRecordedInputs.model_validate_json(normalizer(inputs, supplier).model_dump_json())
        config = self.model_config or ChatCompletionConfig(
            base_url="http://localhost/v1",
            provider_id="local-fixture",
            model_id="explicit-scripted-fixture",
            structured_output=True,
        )
        assembler, coordinator = self.runtime_builder(
            inputs,
            self.clock,
            self.model_transport if self.arm != "minimum" else None,
            config,
            prompt_revision="v3",
            arm=self.arm,
        )
        left = min(
            float(inputs.budget.compute_limit_s),
            (inputs.budget.deadline_at - self.clock.utcnow()).total_seconds()
            - float(inputs.budget.submission_reserve_s),
        )
        try:
            trace = _run_decision_bounded(
                self.run_decision(inputs, assembler=assembler, coordinator=coordinator), timeout_s=left
            )
        except BaseException:
            self.execution_revoked = True
            self.model_transport.stop_model_calls("decision_deadline")
            raise
        trace.verify()
        # Same-observation counterfactual, kept separate from the realized baseline run.
        snapshot = m.DecisionSnapshot.model_validate_json(trace.snapshot_bytes)
        from ..core.certificates import policy_issues

        fixed = tuple(
            coordinator.evaluator.evaluate_package(p, supplier, snapshot.context.economic) for p in inputs.packages
        )
        fixed = tuple(result for result in fixed if not policy_issues((result,), snapshot.context.economic))
        self.baseline_evaluations.append(fixed)
        directory = self.trace_root / self.run_id / self.session_id
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / f"decision-{decision_index:03d}.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(trace.model_dump_json())
        (directory / f"baseline-economics-{decision_index:03d}.json").write_text(
            json.dumps([result.model_dump(mode="json") for result in fixed])
        )
        self.traces.append(trace)
        if trace.validation is None or trace.validation.kind != "valid" or trace.validated_message_bytes is None:
            raise ContractViolation("infeasible: local V2 decision did not pass independent validation")
        self.previous, self.observation = trace.assessment, observation
        self.supplier_memory[supplier] = self.previous, self.observation
        self.pending_message = {"supplier_id": supplier, "message": json.loads(trace.validated_message_bytes)}
        return self.pending_message

    def validate_lab_dispatch(self, supplier_id, message, current_thread):
        """RecordingTable refreshes state before every POST; no certificate bypass."""
        from arena_kit.docs import read_document

        for event in current_thread["messages"]:
            for att in event.get("attachments", []):
                if "text" not in att and att["attachment_id"] in self.attachment_bytes:
                    att["text"] = read_document(att["name"], self.attachment_bytes[att["attachment_id"]])
        if self.pending_message != {"supplier_id": supplier_id, "message": message}:
            raise ContractViolation("invalid_schema: dispatch differs from the validated proposal")
        expected = self.authoritative_threads.get(supplier_id)
        if expected is not None and semantic_hash(current_thread["messages"]) != semantic_hash(expected):
            raise ContractViolation("stale_state: authoritative history changed before dispatch")
        if message.get("action"):
            if not self.closing_enabled:
                raise ContractViolation("unsupported_capability: closing authority was not issued")
            self.closing.validate(
                self.pending_message, case=self.dataset["case"],
                threads=self.closing_threads(supplier_id, current_thread["messages"])
            )
        else:
            trace = self.traces[-1]
            if self.clock.utcnow() >= trace.validation.action.expires_at:
                raise ContractViolation("deadline_exhausted: action certificate expired before dispatch")
            if not message.get("term_sheets"):
                if trace.rendered.kind != "question" or trace.validation.kind != "valid":
                    raise ContractViolation("invalid_schema: non-offer dispatch lacks a certified clarification")
                return
            from arena_kit.cost import total_cost
            from arena_kit.docs import standard_terms

            cost = total_cost(
                self.dataset["case"], message["term_sheets"][0]["terms"], standard_terms(current_thread["messages"])
            )
            selected = next(
                i for i in trace.evaluations.items if i.candidate.candidate_id == trace.decision.candidate_id
            )
            if abs(Decimal(str(cost)) - selected.economic[0].nominal_cost.amount) > Decimal("0.01"):
                raise ContractViolation("source_conflict: live quote standards differ from evaluated economics")

    def validate_lab_http_dispatch(self, supplier_id, message, intent):
        """Fast local permit check after intent fsync, immediately before HTTP."""
        if self.execution_revoked:
            raise ContractViolation("recovery_required: execution was revoked before HTTP dispatch")
        if self.pending_message != {"supplier_id": supplier_id, "message": message}:
            raise ContractViolation("invalid_schema: journaled payload differs from the approved action")
        if self.arm != "minimum":
            trace = self.traces[-1] if self.traces else None
            if trace is None or trace.validation is None or self.clock.utcnow() >= trace.validation.action.expires_at:
                raise ContractViolation("deadline_exhausted: action certificate expired before HTTP dispatch")

    def observe_lab_outcome(self, result, threads):
        from arena_kit.docs import read_document

        from .arena_observations import conversation_from_arena

        supplier = self.dataset["case"]["suppliers"][0]
        events = threads[supplier]["messages"]
        for event in events:
            for att in event.get("attachments", []):
                if "text" not in att:
                    att["text"] = read_document(att["name"], self.attachment_bytes[att["attachment_id"]])
        conversation = conversation_from_arena(
            self.dataset["case"],
            events,
            session_id=self.session_id,
            supplier_id=supplier,
            now=self.clock.utcnow(),
            attachment_bytes=self.attachment_bytes,
        )
        terminal = m.TerminalEvidence(
            session_id=self.session_id,
            status="ended",
            proof_ref="sha256:" + semantic_hash(result),
            source_kind="gateway_observation",
            observed_at=self.clock.utcnow(),
            deal=result.get("deal"),
            offer_id=result.get("offer_id"),
            supplier_id=result.get("supplier_id"),
            cost=m.Money(amount=Decimal(str(result["c_deal"]))) if result.get("c_deal") is not None else None,
            score=Decimal(str(result["score"])) if result.get("score") is not None else None,
            end_reason=(self.terminal_state or {}).get("end_reason") or result.get("end_reason"),
        )
        path = self.trace_root / self.run_id / self.session_id / "terminal-observation.json"
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
            output.write(
                json.dumps(
                    {"terminal": terminal.model_dump(mode="json"), "conversation": conversation.model_dump(mode="json")}
                )
            )

    def experiment_metrics(self):
        decisions = []
        for trace, fixed in zip(self.traces, self.baseline_evaluations, strict=True):
            row = self.metrics(trace)
            minimum = min((r.nominal_cost.amount for r in fixed), default=None)
            cost = Decimal(row["official_cost"]) if row["official_cost"] is not None else None
            row.update(
                fixed_baseline_cost=str(minimum) if minimum is not None else None,
                delta_from_fixed_baseline=str(cost - minimum) if minimum is not None and cost is not None else None,
            )
            decisions.append(row)
        costs = [Decimal(c["estimated_usd"]) for c in getattr(self.transport, "calls", []) if "estimated_usd" in c]
        return {
            "evidence": (
                "hosted model inference; official online Arena"
                if not self.local_only
                else "hosted model inference; official contract simulator"
                if self.model_config
                else "local scripted model; official contract simulator outcomes"
            ),
            "arm": self.arm,
            "closing": self.closing_events,
            "model": (self.model_config.model_id if self.model_config else "explicit-scripted-fixture"),
            "strategy": ("bounded-proposal-v3+deterministic-evidence-copy-v1"
                         if self.arm == "adaptive" else "finite-supplied-v1"),
            "estimated_inference_usd": str(sum(costs, Decimal(0))) if costs else None,
            "reserved_inference_usd": str(self.transport.reserved) if hasattr(self.transport, "reserved") else "0",
            "decisions": decisions,
        }

    def experiment_evidence(self):
        from ..core.lab_evidence import decision_evidence

        return {"scope": "admitted stage outputs; complete official thread retained separately",
                "decisions": [decision_evidence(trace) for trace in self.traces],
                "validation_evidence": getattr(self, "validation_evidence", None),
                "closing": self.closing_events}
