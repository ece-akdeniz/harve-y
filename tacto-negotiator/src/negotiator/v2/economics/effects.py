"""Small, deterministic commercial direction checks for generated packages."""

from decimal import Decimal

from ..core import models as m


def supplier_reference(conversation, fields):
    """Use the latest complete standing supplier quote; never substitute buyer targets."""
    required = set(fields)
    for message in reversed(conversation.messages):
        if message.speaker != "supplier":
            continue
        for sheet in reversed(message.observed_sheets):
            available = sheet.complete_bindings or sheet.bindings
            by_field = {item.field: item for item in available}
            if sheet.standing and required.issubset(by_field):
                bindings = tuple(by_field[field] for field in fields)
                return m.CommercialReference(kind="observed_supplier_offer", bindings=bindings,
                    source_message_id=message.message_id)
    return m.CommercialReference(kind="unavailable")


def commercial_effects(reference, fields):
    before = {item.field: item for item in reference.bindings}
    descriptions = {
        "unit_price": (
            "Lower price favors buyer; higher price changes supplier gross revenue. Margin and net value unknown."
        ),
        "payment_days": (
            "More days delays supplier receipts and does not improve supplier cash flow; "
            "fewer days accelerates receipts."
        ),
        "contract_months": (
            "Longer commitment may add supplier predictability; its value and buyer exposure are unknown."
        ),
        "lead_time_days": "Shorter lead time favors buyer; supplier cost or feasibility is unknown.",
        "volume_per_year": "Volume changes affect both obligations; supplier net value is unknown.",
    }
    result = []
    for field in fields:
        prior = before.get(field)
        result.append(m.CommercialTermEffect(field=field, before=prior, buyer_direction="unknown",
            supplier_direction="unknown", note=descriptions.get(field, "Commercial impact is not established.")))
    return tuple(result)


def expected_trade_labels(reference, bindings):
    prior = {item.field: item.value for item in reference.bindings}
    candidate = {item.field: item.value for item in bindings}
    changed = {field for field, value in candidate.items() if field in prior and prior[field] != value}
    expected_requests, expected_offers = set(), set()
    for field in changed:
        old, new = prior[field], candidate[field]
        if field == "unit_price":
            (expected_requests if Decimal(new) < Decimal(old) else expected_offers).add(field)
        elif field == "payment_days":
            (expected_requests if new > old else expected_offers).add(field)
        elif field == "contract_months":
            (expected_offers if new > old else expected_requests).add(field)
        elif field == "lead_time_days":
            (expected_requests if new < old else expected_offers).add(field)
    return changed, expected_requests, expected_offers


def validate_trade_explanation(reference, response):
    """Check structured trade labels against code-derived term directions."""
    changed, expected_requests, expected_offers = expected_trade_labels(reference, response.bindings)
    if set(response.buyer_requests) != expected_requests:
        raise ValueError("unsupported_claim: buyer request labels contradict commercial direction")
    if set(response.buyer_offers) != expected_offers:
        raise ValueError("unsupported_claim: buyer offer labels contradict commercial direction")
    if not changed.issubset(set(response.supplier_value_unknown)):
        raise ValueError("unsupported_claim: supplier net value must remain unknown for changed terms")
    return changed
