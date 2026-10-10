"""Foundation semantic identity and trust regressions."""
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from negotiator.v2 import config
from negotiator.v2.core import models
from negotiator.v2.core.serialization import semantic_hash
from tests.v2.contracts.test_foundation import basis


@pytest.mark.parametrize('left,right', [('28.3400', '28.34'), ('1E+3', '1000'), ('-0.00', '0')])
def test_decimal_identity(left, right):
    a, b = models.Money(amount=Decimal(left)), models.Money(amount=Decimal(right))
    assert a.amount.as_tuple() == Decimal(left).as_tuple()
    assert semantic_hash(a) == semantic_hash(b)
    assert semantic_hash({'amount': Decimal(left)}) == semantic_hash({'amount': Decimal(right)})
    assert models.Money.model_validate_json(a.model_dump_json()) == a
    assert semantic_hash(a) != semantic_hash(models.Money(amount=Decimal(right) + 1))


def test_package_identity():
    raw = {'bindings': [{'field': 'unit_price', 'value': '28.3400'},
                        {'field': 'payment_days', 'value': 30}], 'price_basis': basis()}
    package = models.Package.model_validate_json(json.dumps(raw))
    raw['bindings'].reverse()
    assert models.Package.model_validate_json(json.dumps(raw)).fingerprint == package.fingerprint
    assert models.Package.model_validate_json(package.model_dump_json()) == package
    for bad in ('arbitrary', '0' * 64):
        with pytest.raises(ValidationError):
            models.Package.model_validate_json(json.dumps({**raw, 'fingerprint': bad}))
    raw['bindings'][0]['value'] = 31
    with pytest.raises(ValidationError):
        models.Package.model_validate_json(json.dumps({**raw, 'fingerprint': package.fingerprint}))


@pytest.mark.parametrize('field,value', [('lead_time_days', -1), ('volume_per_year', 0),
    ('contract_months', 0), ('tooling_eur', '-1'), ('effective_date', '2026-02-30'),
    ('effective_date', '20261010'), ('payment_days', True)])
def test_invalid_terms(field, value):
    with pytest.raises(ValidationError):
        models.TermBinding.model_validate_json(json.dumps({'field': field, 'value': value}))


@pytest.mark.parametrize('field,value', [('run_id', ' '), ('session_id', ''),
    ('context_version', ' '), ('config_hash', 'no'), ('case_contract_hash', 'A' * 64), ('state_version', True)])
def test_invalid_snapshot(field, value):
    raw = dict(run_id='run:1', session_id='session:1', state_version=0,
               context_version='context:1', config_hash='a' * 64, case_contract_hash='b' * 64)
    with pytest.raises(ValidationError):
        models.SnapshotRef.model_validate_json(json.dumps({**raw, field: value}))


@pytest.mark.parametrize('field,value', [('lead_time_days', 'maybe 30'), ('unit_price', True),
    ('incoterm', 'UNKNOWN'), ('effective_date', '2026-02-30'), ('index_clause', 'none')])
def test_invalid_reported_values(field, value):
    raw = dict(constraint_id='constraint:1', dimension=field, op='>=', value=value,
               condition_observation_refs=[], citations=[], authority='supplier_reported', status='stale')
    with pytest.raises(ValidationError):
        models.ReportedConstraint.model_validate_json(json.dumps(raw))


def test_reported_roundtrip():
    raw = dict(constraint_id='constraint:1', dimension='unit_price', op='>=', value='28.3400',
               condition_observation_refs=[], citations=[], authority='supplier_reported', status='stale')
    result = models.ReportedConstraint.model_validate_json(json.dumps(raw))
    assert result.value == Decimal('28.34')
    assert result.authority == 'supplier_reported'
    assert models.ReportedConstraint.model_validate_json(result.model_dump_json()) == result


def test_config_trust(p10):
    resolved = config.resolve_config(p10['config'])
    assert config.require_verified_config(resolved) is resolved
    parsed = models.EffectiveConfig.model_validate_json(resolved.model_dump_json())
    with pytest.raises(ValueError):
        config.require_verified_config(parsed)
    for changed in ({'config_hash': '0' * 64}, {'strategy_id': 'unknown'}, {'candidate_limit': 1}):
        with pytest.raises(ValueError):
            config.require_verified_config(resolved.model_copy(update=changed))
    assert config.require_verified_config(config.resolve_config(json.loads(parsed.model_dump_json())))


@pytest.mark.parametrize('field', ['retry_limit', 'candidate_limit', 'compute_limit_s'])
def test_boolean_config(p10, field):
    with pytest.raises(ValueError):
        config.resolve_config({**p10['config'], field: False if field == 'retry_limit' else True})


@pytest.mark.parametrize('field,value', [('effective_date', '2026-10-10'), ('payment_days', 0),
    ('volume_per_year', 1), ('index_clause', None), ('incoterm', 'FCA'), ('tooling_eur', '0.00')])
def test_valid_term_roundtrips(field, value):
    binding = models.TermBinding.model_validate_json(json.dumps({'field': field, 'value': value}))
    assert models.TermBinding.model_validate_json(binding.model_dump_json()) == binding


def test_raw_ambiguous_statement_remains_evidence():
    observation = models.GroundedObservation(
        observation_id='observation:1', kind='ambiguity', dimension='payment_days',
        summary='Maybe thirty days, pending approval', citations=(models.SourceRef(record_id='source:1'),),
    )
    assert models.GroundedObservation.model_validate_json(observation.model_dump_json()) == observation


def test_config_decimal_identity_and_untrusted_construction(p10):
    resolved = config.resolve_config(p10['config'])
    raw = {**p10['config'], 'price_tick': '0.0100'}
    assert config.resolve_config(raw).config_hash == resolved.config_hash
    with pytest.raises(ValueError):
        config.require_verified_config(models.EffectiveConfig.model_construct(**resolved.model_dump()))
    with pytest.raises(ValueError):
        config.resolve_config({**p10['config'], 'config_hash': '0' * 64})


@pytest.mark.parametrize('month', ['0000-01', '2026-13', '2026-00'])
def test_invalid_index_months(month):
    with pytest.raises(ValidationError):
        models.IndexClause.model_validate_json(json.dumps(dict(
            series='index:1', material_share='0.5', deadband_pct='0', base_month=month,
        )))


def test_decimal_normalization_does_not_round_to_context():
    from decimal import localcontext

    value = Decimal('12345678901234567890.1234000')
    expected = semantic_hash(models.Money(amount=value))
    with localcontext() as context:
        context.prec = 3
        assert semantic_hash(models.Money(amount=value)) == expected
    assert json.loads(models.Money(amount=value).model_dump_json())['amount'] == '12345678901234567890.1234'


def test_reported_nested_index_roundtrip():
    raw = dict(constraint_id='constraint:1', dimension='index_clause', op='==', value=dict(
        series='index:1', material_share='0.5000', deadband_pct='0.00', base_month='2026-10',
    ), condition_observation_refs=[], citations=[], authority='supplier_reported', status='stale')
    result = models.ReportedConstraint.model_validate_json(json.dumps(raw))
    assert isinstance(result.value, models.IndexClause)
    assert models.ReportedConstraint.model_validate_json(result.model_dump_json()) == result
