"""Finalized DTO handoff. Only absent declared symbols may xfail in this suite.

--v2-dto-require D1 (or a symbol/all) makes absence fail. Existing symbols never xfail.
"""
import json

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from negotiator.v2.core import models
from tests.v2.dto_spec import (
    CONTRACT,
    DEFINITIONS,
    assert_example_shape,
    example,
    expand,
    negative_example,
    patch_example,
)

NAMES = tuple(DEFINITIONS)


def declared_type(request, name):
    if not hasattr(models, name):
        required = request.config.getoption('--v2-dto-require')
        if 'all' in request.config.getoption('--v2-require'):
            required = [*required, 'all']
        if any(item in ('all', name, DEFINITIONS[name]['batch']) for item in required):
            pytest.fail(f'Required T1.1d DTO absent: {name}')
        pytest.xfail(f'UNIMPLEMENTED DTO: {name} ({DEFINITIONS[name]["batch"]})')
    return getattr(models, name)


def decode(target, raw):
    return TypeAdapter(target).validate_json(json.dumps(raw, ensure_ascii=False))


@pytest.mark.parametrize('name', NAMES)
def test_declared_dto_positive_and_roundtrip(request, name):
    target = declared_type(request, name)
    result = decode(target, example(name))
    assert isinstance(result, BaseModel)
    assert_frozen_tree(result)
    assert_declared_python_types(target, result)
    assert result.schema_version == CONTRACT['contract_version']
    assert decode(target, json.loads(result.model_dump_json())) == result
    with pytest.raises(ValidationError):
        result.schema_version = CONTRACT['contract_version']


@pytest.mark.parametrize('name', NAMES)
def test_declared_dto_rejects_specific_domain_fault(request, name):
    target = declared_type(request, name)
    with pytest.raises(ValidationError):
        decode(target, negative_example(name))


@pytest.mark.parametrize('name', NAMES)
def test_declared_dto_rejects_extra_fields_and_wrong_version(request, name):
    target = declared_type(request, name)
    raw = example(name)
    with pytest.raises(ValidationError):
        decode(target, {**raw, 'executable_authority': True})
    with pytest.raises(ValidationError):
        decode(target, {**raw, 'schema_version': 'negotiator-v2/999'})


@pytest.mark.parametrize('name', [name for name in NAMES if 'fields' in DEFINITIONS[name]])
def test_declared_dto_exact_field_inventory_and_defaults(request, name):
    target = declared_type(request, name)
    fields = DEFINITIONS[name]['fields']
    assert set(target.model_fields) == {'schema_version', *fields}
    for key, spec in fields.items():
        assert target.model_fields[key].is_required() == spec['required'], key
        if not spec['required']:
            default = spec['default']
            assert target.model_fields[key].default == (() if default == [] else default), key


@pytest.mark.parametrize('name', NAMES)
def test_spec_examples_and_negative_mutations_are_concrete(name):
    raw = example(name)
    assert_example_shape(name, raw)
    assert '$example' not in json.dumps(raw)
    assert json.dumps(raw, sort_keys=True) != json.dumps(negative_example(name), sort_keys=True)
    assert isinstance(raw, dict)
    assert DEFINITIONS[name]['invariants']
    assert DEFINITIONS[name]['negative']


def test_required_absent_dto_fails_and_present_symbol_is_not_hidden(monkeypatch):
    from types import SimpleNamespace

    request = SimpleNamespace(config=SimpleNamespace(getoption=lambda _: ['D1']))
    monkeypatch.delattr(models, 'IndexFact', raising=False)
    with pytest.raises(pytest.fail.Exception, match='Required T1.1d DTO absent'):
        declared_type(request, 'IndexFact')
    milestone = SimpleNamespace(config=SimpleNamespace(
        getoption=lambda option: ['all'] if option == '--v2-require' else [],
    ))
    with pytest.raises(pytest.fail.Exception, match='Required T1.1d DTO absent'):
        declared_type(milestone, 'IndexFact')
    monkeypatch.setattr(models, 'IndexFact', int, raising=False)
    assert declared_type(request, 'IndexFact') is int
    with pytest.raises(ValidationError):
        decode(declared_type(request, 'IndexFact'), example('IndexFact'))


def test_symbol_absence_gate_is_limited_to_named_specification_tests(monkeypatch):
    from types import SimpleNamespace

    request = SimpleNamespace(config=SimpleNamespace(getoption=lambda _: []))
    monkeypatch.delattr(models, 'IndexFact', raising=False)
    with pytest.raises(pytest.xfail.Exception, match='UNIMPLEMENTED DTO: IndexFact'):
        declared_type(request, 'IndexFact')


def test_every_batch_is_bounded_and_every_reference_has_an_example():
    from collections import Counter

    counts = Counter(spec['batch'] for spec in DEFINITIONS.values())
    assert len(counts) == 16
    assert all(count <= 15 for count in counts.values())
    assert all(not field['type'].startswith(('dict', 'Any'))
               for spec in DEFINITIONS.values() for field in spec.get('fields', {}).values())
    for name in NAMES:
        assert_example_shape(name, example(name))


@pytest.mark.parametrize('case', CONTRACT['additional_cases'], ids=lambda case: case['name'] + ':' + case['label'])
def test_explicit_authority_and_economic_scenarios(request, case):
    target = declared_type(request, case['name'])
    raw = patch_example(expand(case['example']), case['patch'])
    if case['valid']:
        result = decode(target, raw)
        assert decode(target, json.loads(result.model_dump_json())) == result
    else:
        with pytest.raises(ValidationError):
            decode(target, raw)


@pytest.mark.parametrize('case', [case for case in CONTRACT['additional_cases'] if case['valid']],
                         ids=lambda case: case['name'] + ':' + case['label'])
def test_additional_positive_example_shapes(case):
    assert_example_shape(case['name'], patch_example(expand(case['example']), case['patch']))



def assert_frozen_tree(value):
    if isinstance(value, BaseModel):
        assert isinstance(value, models.FrozenModel)
        for name in type(value).model_fields:
            assert_frozen_tree(getattr(value, name))
    elif isinstance(value, tuple):
        for item in value:
            assert_frozen_tree(item)
    else:
        assert not isinstance(value, (dict, list, set))


def assert_declared_python_types(target, result):
    from datetime import date, datetime
    from decimal import Decimal

    spec = DEFINITIONS.get(type(result).__name__)
    assert spec is not None
    for name, field in spec['fields'].items():
        value = getattr(result, name)
        if value is None:
            continue
        token = field['type']
        if token.startswith('T['):
            assert isinstance(value, tuple)
            with pytest.raises(ValidationError):
                type(result).model_validate({**result.model_dump(), name: list(value)})
        elif token in ('Decimal', 'NonnegativeDecimal', 'PositiveDecimal', 'Percent'):
            assert isinstance(value, Decimal)
            with pytest.raises(ValidationError):
                type(result).model_validate({**result.model_dump(), name: str(value)})
        elif token in ('NonnegativeInt', 'PositiveInt', 'ZeroInt'):
            assert type(value) is int
            with pytest.raises(ValidationError):
                decode(target, {**result.model_dump(mode='json'), name: True})
        elif token == 'bool':
            assert type(value) is bool
        elif token in ('Date', 'UTC'):
            assert type(value) is (date if token == 'Date' else datetime)
            with pytest.raises(ValidationError):
                type(result).model_validate({**result.model_dump(), name: value.isoformat()})
