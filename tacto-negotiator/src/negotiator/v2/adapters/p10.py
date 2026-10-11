"""Faithful single-part P10 recorded case loading; synthetic clocks, no remote authority."""

import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from ..core import models as m
from ..core.certificates import case_contract_hash
from ..core.serialization import semantic_hash
from .offline import OfflineRecordedInputs


def term_binding(field, value):
    if field in {"unit_price", "tooling_eur", "chargeback_eur_per_complaint"}:
        value = str(value)
    return dict(field=field, value=value)


def case_contract(raw, basis):
    if (
        raw["case_id"] not in {"case:P10", "case:D01", "case:D02"}
        or len(raw["suppliers"]) != 1
        or len(raw["parts"]) != 1
    ):
        raise ValueError("loader requires a reviewed one-part, one-supplier economic slice")
    b = raw["buyer"]

    def price(value):
        return {"amount": str(value), "basis": basis.model_dump(mode="json")}

    buyer = dict(
        category_goal=b["category_goal"],
        need_per_year=str(b["need_per_year"]),
        horizon_years=str(b["horizon_years"]),
        current_price=price(b["current_unit_price"]) if b["current_unit_price"] is not None else None,
        fallback_price=price(b["fallback_unit_price"]),
        interest_rate=str(b["interest_rate"]),
        reference_payment_days=b["reference_payment_days"],
        need_lead_time_days=b["need_lead_time_days"],
        fallback_risk_pct=str(b.get("fallback_risk_pct", 0)),
        index_risk_pct=str(b.get("index_risk_pct", 0)),
        late_cost_per_day={"amount": str(b.get("late_cost_per_day", 0))},
        cost_per_defect={"amount": str(b.get("cost_per_defect", 0))},
        sustainable_margin_pct=str(b["sustainable_margin_pct"])
        if b.get("sustainable_margin_pct") is not None else None,
        relationship_eur_per_point={"amount": str(b["relationship_eur_per_point"])}
        if b.get("relationship_eur_per_point") is not None else None,
        freight=[dict(incoterm=k, eur_per_unit=str(v)) for k, v in b["freight_eur_per_unit"].items()],
        index_paths=[dict(series=k, delta_fraction=str(v)) for k, v in b.get("index_paths", {}).items()],
        must_haves=b["must_haves"],
        alternative=dict(kind="unavailable", reason_code="case-has-no-executable-alternative"),
    )
    alternative = b["alternative"]
    if alternative["kind"] == "quote":
        from arena_kit.cost import closing_terms

        terms = tuple(m.TermBinding.model_validate_json(json.dumps(term_binding(k, v)))
                      for k, v in sorted(closing_terms(raw, alternative["terms"]).items()))
        ref = m.SourceRef(record_id=alternative["ref"])
        resolved = m.ResolvedTerms(bindings=terms,
            origins=tuple(m.FieldOrigin(field=t.field, source_kind="sheet", source_refs=(ref,)) for t in terms),
            version_hash="0" * 64)
        resolved = resolved.model_copy(update={"version_hash": semantic_hash(
            resolved.model_dump(mode="json", exclude={"version_hash"}))})
        buyer["alternative"] = m.AvailableAlternative(kind="available", ref=ref, terms=resolved,
            basis=basis, provenance_refs=(ref,)).model_dump(mode="json")
    elif alternative["kind"] != "none":
        raise ValueError("unsupported executable alternative kind")
    # TermBinding's strict JSON decoder resolves Decimal/date/index types without repair.
    raw_contract = dict(
        case_id=raw["case_id"],
        case_type=raw["type"],
        title=raw["title"],
        supplier_ids=raw["suppliers"],
        parts=[dict(part_id=raw["parts"][0], price_basis=basis.model_dump(mode="json"))],
        negotiable_fields=raw["negotiable"],
        fixed_terms=[term_binding(k, v) for k, v in sorted(raw["fixed_terms"].items())],
        options=[
            dict(field=k, values=v, allow_verified_standard=False) for k, v in sorted(raw["term_options"].items())
        ],
        buyer=buyer,
        round_limit=raw["round_limit"],
        case_facts=[],
        refs=raw.get("refs", []),
        contract_hash="0" * 64,
    )
    contract = m.CaseContract.model_validate_json(json.dumps(raw_contract))
    return contract.model_copy(update={"contract_hash": case_contract_hash(contract)})


def recorded_p10(dataset, *, message, now, model_call_limit=2):
    if message not in dataset["supplier_messages"]:
        raise ValueError("message must belong to the declared experiment dataset")
    raw = dataset["case"]
    basis = m.PriceBasis(
        currency="EUR",
        price_unit=dataset["price_unit"],
        part_ids=tuple(raw["parts"]),
        quantity_basis="arena-case-quantity",
        source_refs=(raw["case_id"],),
    )
    contract = case_contract(raw, basis)
    packages = tuple(
        m.Package(
            bindings=tuple(
                m.TermBinding.model_validate_json(json.dumps(term_binding(k, v))) for k, v in sorted(terms.items())
            ),
            price_basis=basis,
        )
        for terms in dataset["candidate_terms"]
    )
    msg = m.ConversationMessage(
        session_id="session:offline-p10",
        thread_id="thread:offline-p10",
        message_id="message:offline-p10-1",
        supplier_id=contract.supplier_ids[0],
        speaker="supplier",
        body=message,
        observed_sheets=(),
        attachments=(),
        claim_results=(),
        received_at=now,
        content_hash=hashlib.sha256(message.encode()).hexdigest(),
    )
    conversation = m.ConversationView(
        session_id=msg.session_id, thread_id=msg.thread_id, messages=(msg,), version_hash=semantic_hash((msg,))
    )
    standards = m.ResolvedStandards(bindings=(), field_origins=(), version_hash="0" * 64)
    standards = standards.model_copy(
        update={"version_hash": semantic_hash(standards.model_dump(mode="json", exclude={"version_hash"}))}
    )
    provenance = "sha256:" + semantic_hash((dataset, "synthetic-offline-state"))
    thread = m.ServerThread(
        thread_id=msg.thread_id,
        supplier_id=msg.supplier_id,
        status="open",
        conversation=conversation,
        standards=standards,
        rounds=m.RoundEvidence(
            limit=raw["round_limit"],
            accepted_buyer_messages=0,
            conservative_remaining=raw["round_limit"],
            confidence="conservative",
            source_ref=provenance,
        ),
        clock=m.ClockEvidence(
            kind="thread",
            snapshot_requested_at=now,
            snapshot_received_at=now,
            conservative_deadline_at=now + timedelta(seconds=60),
            confidence="conservative",
            source_ref=provenance,
        ),
    )
    server = m.ServerState(
        session_id=msg.session_id,
        case_id=contract.case_id,
        status="open",
        threads=(thread,),
        observed_at=now,
        observation_hash=semantic_hash((thread, now.isoformat())),
    )
    state = m.NegotiationState(
        run_id="run:offline-p10",
        attempt_id=UUID(int=10),
        case=contract,
        server=server,
        strategic=m.StrategicState(
            assessments=(), attempts=(), refusals=(), claim_usage=(), outstanding_questions=(), feedback=(), memory=()
        ),
        operations=(),
        version=0,
        config_hash=semantic_hash(dataset),
        runtime_status="ready",
        issues=(),
    )
    manifest = m.SourceManifest(
        source_id="recorded:p10-offline",
        content_hash=semantic_hash(dataset),
        files=(),
        declared_version="p10-recorded-input/1",
    )
    prepared = m.PreparedEvidence(
        artifact_id="sha256:" + "0" * 64,
        integrity_hash="0" * 64,
        base_manifest=manifest,
        parser_versions=("p10-recorded-input/1",),
        records=(),
        indexes=(),
        prepared_at=now,
    )
    digest = semantic_hash(prepared.model_dump(mode="json", exclude={"prepared_at", "integrity_hash", "artifact_id"}))
    prepared = prepared.model_copy(update={"integrity_hash": digest, "artifact_id": "sha256:" + digest})
    return OfflineRecordedInputs(
        prepared=prepared,
        case=contract,
        server=server,
        documents=(),
        as_of=now,
        state=state,
        budget=m.DecisionBudget(
            deadline_at=now + timedelta(seconds=35),
            compute_limit_s=Decimal("35"),
            model_call_limit=model_call_limit,
            model_time_limit_s=Decimal("12"),
            candidate_limit=20,
            fallback_reserve_s=Decimal("5"),
            submission_reserve_s=Decimal("5"),
            clock_refs=(provenance,),
        ),
        target_supplier_id=msg.supplier_id,
        cost_policy=m.CostPolicy(
            policy_id="recorded-p10-bounded",
            comparison="nominal",
            tick=Decimal("0.01"),
            price_bounds=m.PriceInterval(
                minimum=m.Price(amount=Decimal("0.01"), basis=basis),
                maximum=m.Price(amount=Decimal("100"), basis=basis),
            ),
            fallback_rule="preserve_baseline_if_feasible",
            alternative_rule="compare_executable_else_no_deal_score",
        ),
        estimate_mode="disabled_explicit",
        cost_assumptions=(),
        packages=packages,
    )
