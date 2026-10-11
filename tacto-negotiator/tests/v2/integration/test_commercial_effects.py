"""Focused checks for code-derived commercial directions and proposal admission."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from experiments.v2.run_lab_local import DATASET
from negotiator.v2.adapters.p10 import recorded_p10, term_binding
from negotiator.v2.core import models as m
from negotiator.v2.economics.effects import (
    commercial_effects,
    expected_trade_labels,
    supplier_reference,
    validate_trade_explanation,
)


def _reference(**terms):
    bindings = tuple(m.TermBinding.model_validate_json(json.dumps(term_binding(k, v))) for k, v in terms.items())
    return m.CommercialReference(kind="observed_supplier_offer", bindings=bindings, source_message_id="message:quote")


def _response(bindings, reference, *, requests=None, offers=None, unknown=None):
    changed, expected_requests, expected_offers = expected_trade_labels(reference, bindings)
    return m.ProposalResponseV2(
        bindings=bindings,
        citation_ids=(),
        buyer_requests=tuple(expected_requests if requests is None else requests),
        buyer_offers=tuple(expected_offers if offers is None else offers),
        supplier_value_unknown=tuple(changed if unknown is None else unknown),
        rationale="Code checked buyer direction; supplier net value remains unknown.",
    )


def test_payment_days_45_instead_of_30_is_buyer_request_and_delays_receipts():
    ref = _reference(payment_days=30)
    response = _response((m.TermBinding(field="payment_days", value=45),), ref)
    validate_trade_explanation(ref, response)
    effect = commercial_effects(ref, ("payment_days",))[0]
    assert effect.buyer_direction == "unknown"  # No candidate exists until the model proposes one.
    assert "delays supplier receipts" in effect.note
    assert response.buyer_requests == ("payment_days",) and not response.buyer_offers


def test_lower_price_is_buyer_request_without_claiming_supplier_margin():
    ref = _reference(unit_price=Decimal("52.90"))
    response = _response((m.TermBinding(field="unit_price", value=Decimal("50.50")),), ref)
    validate_trade_explanation(ref, response)
    assert response.buyer_requests == ("unit_price",)
    assert "Margin and net value unknown" in commercial_effects(ref, ("unit_price",))[0].note


def test_longer_contract_is_a_buyer_offer_but_not_proven_compensation():
    ref = _reference(contract_months=12)
    response = _response((m.TermBinding(field="contract_months", value=24),), ref)
    validate_trade_explanation(ref, response)
    effect = commercial_effects(ref, ("contract_months",))[0]
    assert response.buyer_offers == ("contract_months",)
    assert response.supplier_value_unknown == ("contract_months",)
    assert effect.buyer_direction == effect.supplier_direction == "unknown"
    assert "its value" in effect.note and "unknown" in effect.note


def test_unsupported_supplier_costs_are_not_inferred_from_commercial_projection():
    ref = _reference(unit_price=Decimal("52.90"))
    effect = commercial_effects(ref, ("unit_price",))[0]
    assert not {"supplier_cost", "supplier_margin", "reservation_price"} & set(m.CommercialReference.model_fields)
    assert "supplier gross revenue" in effect.note and "net value unknown" in effect.note


def test_reciprocal_price_payment_and_duration_trade_is_admitted_with_uncertainty():
    ref = _reference(unit_price=Decimal("52.90"), payment_days=30, contract_months=12)
    bindings = (
        m.TermBinding(field="unit_price", value=Decimal("50.50")),
        m.TermBinding(field="payment_days", value=45),
        m.TermBinding(field="contract_months", value=24),
    )
    response = _response(bindings, ref)
    assert set(response.buyer_requests) == {"unit_price", "payment_days"}
    assert response.buyer_offers == ("contract_months",)
    assert set(validate_trade_explanation(ref, response)) == {"unit_price", "payment_days", "contract_months"}


def test_payment_direction_contradiction_is_rejected():
    ref = _reference(payment_days=30)
    response = _response((m.TermBinding(field="payment_days", value=45),), ref,
                         requests=(), offers=("payment_days",))
    with pytest.raises(ValueError, match="labels contradict commercial direction"):
        validate_trade_explanation(ref, response)


def test_latest_supplier_quote_updates_reference_after_new_message():
    class Clock:
        def utcnow(self):
            return datetime.now(UTC)

    data = json.loads(DATASET.read_text())
    inputs = recorded_p10(data, message=data["supplier_messages"][0], now=Clock().utcnow())
    old = inputs.server.threads[0].conversation.messages[0]
    fields = inputs.case.negotiable_fields

    def sheet(message, price):
        terms = dict(data["candidate_terms"][0], unit_price=price)
        bindings = tuple(m.TermBinding.model_validate_json(json.dumps(term_binding(k, terms[k]))) for k in fields)
        cite = m.MessageSpan(session_id=message.session_id, thread_id=message.thread_id,
            message_id=message.message_id, start=0, end=len(message.body), quote=message.body)
        return m.ObservedSheet(bindings=bindings, complete_bindings=bindings, source_message_ref=cite,
            standing=True, parse_issues=())

    first = old.model_copy(update={"observed_sheets": (sheet(old, Decimal("52.90")),)})
    newer = old.model_copy(update={"message_id": "message:new-quote", "body": "We can revise the price.",
        "content_hash": "a" * 64, "observed_sheets": ()})
    newer = newer.model_copy(update={"observed_sheets": (sheet(newer, Decimal("51.75")),)})
    conversation = inputs.server.threads[0].conversation.model_copy(update={"messages": (first, newer)})
    reference = supplier_reference(conversation, fields)
    assert reference.source_message_id == "message:new-quote"
    assert next(x.value for x in reference.bindings if x.field == "unit_price") == Decimal("51.75")


def test_proposal_projection_keeps_supplier_refusal_and_active_constraint():
    class Clock:
        def utcnow(self):
            return datetime.now(UTC)

    data = json.loads(DATASET.read_text())
    inputs = recorded_p10(data, message=data["supplier_messages"][0], now=Clock().utcnow())
    original = inputs.server.threads[0].conversation.messages[0]
    refusal = "We refuse payment after 30 days; that condition is not approved."
    message = original.model_copy(update={"body": refusal, "content_hash": "b" * 64})
    span = m.MessageSpan(session_id=message.session_id, thread_id=message.thread_id,
        message_id=message.message_id, start=0, end=len(refusal), quote=refusal)
    constraint = m.ReportedConstraint(constraint_id="constraint:payment-refusal", dimension="payment_days",
        op="<=", value=30, condition_observation_refs=(), citations=(span,),
        authority="supplier_reported", status="active")
    snapshot = m.SnapshotRef(run_id="run:refusal", session_id=message.session_id, state_version=1,
        context_version="sha256:" + "1" * 64, config_hash="2" * 64, case_contract_hash="3" * 64)
    assessment = m.SupplierAssessment(assessment_id="assessment:refusal", supplier_id=inputs.target_supplier_id,
        snapshot=snapshot, revision=1, observations=(), reported_constraints=(constraint,), hypotheses=(),
        uncertainties=(), questions=(), unknowns=(), status="ok", interpreter_id="fixture", model_call_id="call:1")
    conversation = inputs.server.threads[0].conversation.model_copy(update={"messages": (message,)})
    projection = m.ProposeInputV2(kind="propose", snapshot=snapshot, supplier_id=inputs.target_supplier_id,
        conversation=conversation, assessment=assessment, negotiable_fields=inputs.case.negotiable_fields,
        options=inputs.case.options, citation_catalog=(), must_haves=inputs.case.buyer.must_haves,
        commercial_reference=m.CommercialReference(kind="unavailable"),
        commercial_effects=commercial_effects(m.CommercialReference(kind="unavailable"),
            inputs.case.negotiable_fields))
    assert projection.conversation.messages[0].body == refusal
    assert projection.assessment.reported_constraints[0].dimension == "payment_days"
    assert projection.assessment.reported_constraints[0].value == 30
