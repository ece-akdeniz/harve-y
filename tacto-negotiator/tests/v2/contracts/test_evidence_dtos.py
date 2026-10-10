"""Owned DTO tests; no resolver, source loading or evidence truth inference."""

import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from negotiator.v2.core.models import (
    DisclosureRule,
    EvidenceScope,
    Price,
    PriceBasis,
    Provenance,
    SourceRef,
    TemporalValidity,
)
from negotiator.v2.core.serialization import semantic_hash


@pytest.fixture
def evidence_metadata(p10):
    return {
        EvidenceScope: dict(supplier_ids=[p10['supplier_id']], part_ids=p10['case']['parts'],
                            level='part', case_id=p10['case']['case_id']),
        Provenance: dict(layer='case', source_version='fixture-case/1', content_hash='a' * 64,
                         locator='case/P10/row/1', parent_refs=[dict(record_id='record:base')],
                         parser_version='fixture/1'),
        TemporalValidity: dict(status='unknown', freshness_rule_id='fixture-explicit/1',
                               observed_at=p10['as_of'], published_at=None, valid_from='2026-10-01',
                               valid_to='2026-10-31', data_as_of='2026-10-10'),
        DisclosureRule: dict(classification='internal', permitted_recipients=[], purpose=['cost_input']),
    }


@pytest.mark.parametrize('model', [EvidenceScope, Provenance, TemporalValidity, DisclosureRule])
def test_metadata_roundtrip_frozen_and_extra_forbidden(evidence_metadata, model):
    result = model.model_validate_json(json.dumps(evidence_metadata[model]))
    assert model.model_validate_json(result.model_dump_json()) == result
    assert result.schema_version == 'negotiator-v2/1'
    assert semantic_hash(result) == semantic_hash(model.model_validate_json(result.model_dump_json()))
    with pytest.raises(ValidationError):
        result.schema_version = 'negotiator-v2/1'
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps({**evidence_metadata[model], 'authority': 'binding'}))


def test_p10_metadata_composes_with_existing_foundation(evidence_metadata, p10):
    scope = EvidenceScope.model_validate_json(json.dumps(evidence_metadata[EvidenceScope]))
    provenance = Provenance.model_validate_json(json.dumps(evidence_metadata[Provenance]))
    temporal = TemporalValidity.model_validate_json(json.dumps(evidence_metadata[TemporalValidity]))
    disclosure = DisclosureRule.model_validate_json(json.dumps(evidence_metadata[DisclosureRule]))
    basis = PriceBasis(currency='EUR', price_unit=1, part_ids=scope.part_ids,
                       quantity_basis='arena-case-quantity', source_refs=(provenance.parent_refs[0].record_id,))
    price = Price.model_validate_json(json.dumps(dict(amount='150.00', basis=basis.model_dump(mode='json'))))
    assert price.basis.part_ids == tuple(p10['case']['parts'])
    assert scope.supplier_ids == (p10['supplier_id'],)
    assert provenance.parent_refs == (SourceRef(record_id='record:base'),)
    assert temporal.observed_at == datetime.fromisoformat(p10['as_of'])
    assert temporal.valid_from == date(2026, 10, 1)
    assert disclosure.classification == 'internal'
    assert disclosure.permitted_recipients == ()


@pytest.mark.parametrize('model,field,value', [
    (EvidenceScope, 'supplier_ids', ['']), (EvidenceScope, 'part_ids', [' part:1']),
    (EvidenceScope, 'case_id', ' '), (EvidenceScope, 'level', 'plant'),
    (Provenance, 'content_hash', 'invalid'), (Provenance, 'content_hash', 'A' * 64),
    (Provenance, 'source_version', ''), (Provenance, 'locator', ' '),
    (Provenance, 'locator', 'https://user:secret@example.test/source'),
    (Provenance, 'parser_version', ''), (Provenance, 'layer', 'model_truth'),
    (TemporalValidity, 'valid_from', '2026-02-30'), (TemporalValidity, 'observed_at', '2026-10-10T12:00:00'),
    (TemporalValidity, 'published_at', '2026-10-10T12:00:00+02:00'),
    (TemporalValidity, 'freshness_rule_id', ''), (TemporalValidity, 'status', 'verified'),
    (DisclosureRule, 'classification', 'binding'), (DisclosureRule, 'permitted_recipients', ['']),
    (DisclosureRule, 'purpose', [' ']),
])
def test_invalid_metadata_rejected(evidence_metadata, model, field, value):
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps({**evidence_metadata[model], field: value}))


@pytest.mark.parametrize('model,field', [
    (EvidenceScope, 'supplier_ids'), (EvidenceScope, 'part_ids'), (Provenance, 'parent_refs'),
    (DisclosureRule, 'permitted_recipients'), (DisclosureRule, 'purpose'),
])
def test_python_collections_require_tuples(evidence_metadata, model, field):
    result = model.model_validate_json(json.dumps(evidence_metadata[model]))
    raw = result.model_dump()
    assert isinstance(raw[field], tuple)
    with pytest.raises(ValidationError):
        model.model_validate({**raw, field: list(raw[field])})


def test_temporal_unknown_is_not_silently_current():
    result = TemporalValidity(status='unknown', freshness_rule_id='unknown-source/1')
    assert result.status == 'unknown'
    assert result.observed_at is None and result.data_as_of is None
    assert TemporalValidity.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError):
        TemporalValidity(status='unknown', freshness_rule_id='rule:1', observed_at='2026-10-10T00:00:00Z')
    with pytest.raises(ValidationError):
        TemporalValidity(status='unknown', freshness_rule_id='rule:1', valid_from='2026-10-10')
    assert TemporalValidity(status='current', freshness_rule_id='rule:1',
                            observed_at=datetime(2026, 10, 10, tzinfo=UTC)).observed_at.tzinfo == UTC


def test_unknown_text_disclosure_defaults_restricted():
    result = DisclosureRule(permitted_recipients=(), purpose=())
    assert result.classification == 'restricted'
    assert DisclosureRule.model_validate_json(result.model_dump_json()) == result


def test_supplier_scorecard_scope_does_not_invent_parts():
    result = EvidenceScope(supplier_ids=('supplier:1',), part_ids=(), level='supplier')
    assert result.part_ids == ()
    assert result.case_id is None
    assert EvidenceScope.model_validate_json(result.model_dump_json()) == result
