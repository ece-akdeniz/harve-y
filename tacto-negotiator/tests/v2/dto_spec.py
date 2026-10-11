"""Test-only contract examples; never imported by production."""
import copy
import json
from pathlib import Path

CONTRACT = json.loads(Path(__file__).with_name('dto-contracts.json').read_text())
DEFINITIONS = CONTRACT['definitions']


def example(name):
    source = DEFINITIONS.get(name, {}).get('example', CONTRACT['existing_examples'].get(name))
    if source is None:
        raise AssertionError(f'Undeclared example: {name}')
    return expand(copy.deepcopy(source))


def expand(value):
    if isinstance(value, list):
        return [expand(item) for item in value]
    if isinstance(value, dict):
        if '$example' in value:
            result = example(value['$example'])
            result.update({key: expand(item) for key, item in value.items() if key != '$example'})
            return result
        return {key: expand(item) for key, item in value.items()}
    return value


def negative_example(name):
    return patch_example(example(name), DEFINITIONS[name]['negative'])


def patch_example(result, mutations):
    for path, value in mutations.items():
        target = result
        parts = path.split('.')
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        last = int(parts[-1]) if isinstance(target, list) else parts[-1]
        target[last] = expand(copy.deepcopy(value))
    return result


def assert_example_shape(name, value):
    """Check handoff data itself against declared types; this is not a runtime validator."""
    import re
    from datetime import date, datetime, timedelta
    from decimal import Decimal
    from uuid import UUID

    from pydantic import TypeAdapter

    from negotiator.v2.core import models

    if name in CONTRACT['existing_examples']:
        TypeAdapter(getattr(models, name)).validate_json(json.dumps(value))
        return
    if name in DEFINITIONS:
        spec = DEFINITIONS[name]
        if 'union' in spec:
            matches = [member for member in spec['union']
                       if value.get(spec['discriminator']) == DEFINITIONS[member]['example'][spec['discriminator']]]
            assert len(matches) == 1, name
            assert_example_shape(matches[0], value)
            return
        assert isinstance(value, dict), name
        assert set(value) <= {'schema_version', *spec['fields']}, name
        for key, field in spec['fields'].items():
            assert key in value or not field['required'], (name, key)
            if key not in value or (value[key] is None and not field['required']):
                continue
            assert_example_shape(field['type'], value[key])
        return
    if name == 'IdSpanPair':
        assert isinstance(value, list) and len(value) == 2, name
        assert_example_shape('Id', value[0])
        assert_example_shape('MessageSpan', value[1])
        return
    if name.startswith('T['):
        assert isinstance(value, list), name
        for item in value:
            assert_example_shape(name[2:-1], item)
    elif name.startswith('L['):
        choices = name[2:-1].split(',')
        assert (type(value) is bool and value is True) if choices == ['True'] else value in choices
    elif name in ('Id', 'Label', 'Summary', 'str'):
        assert type(value) is str
        if name != 'str':
            assert value.strip()
        if name == 'Id':
            assert value == value.strip()
        if name == 'Summary':
            assert len(value) <= 1000
    elif name in ('Decimal', 'NonnegativeDecimal', 'PositiveDecimal', 'Percent'):
        assert type(value) is str
        number = Decimal(value)
        assert number.is_finite()
        if name in ('NonnegativeDecimal', 'Percent'):
            assert number >= 0
        if name == 'PositiveDecimal':
            assert number > 0
        if name == 'Percent':
            assert number <= 100
    elif name in ('NonnegativeInt', 'PositiveInt', 'ZeroInt'):
        assert type(value) is int
        assert value >= (1 if name == 'PositiveInt' else 0)
        if name == 'ZeroInt':
            assert value == 0
    elif name == 'bool':
        assert type(value) is bool
    elif name == 'Hash':
        assert re.fullmatch('[0-9a-f]{64}', value)
    elif name == 'ArtifactRef':
        assert re.fullmatch('sha256:[0-9a-f]{64}', value)
    elif name == 'UUID':
        assert str(UUID(value)) == value
    elif name == 'Date':
        assert date.fromisoformat(value).isoformat() == value
    elif name == 'UTC':
        assert datetime.fromisoformat(value).utcoffset() == timedelta(0)
    elif name == 'Month':
        assert re.fullmatch('[0-9]{4}-(0[1-9]|1[0-2])', value)
        assert date.fromisoformat(value + '-01')
    elif name == 'Quarter':
        assert re.fullmatch('[0-9]{4}Q[1-4]', value) and int(value[:4]) > 0
    elif name == 'CountryCode':
        assert re.fullmatch('[A-Z]{2}', value)
    elif name == 'RelativePath':
        assert value and not value.startswith('/') and '\\' not in value and '\x00' not in value
        assert all(part not in ('', '.', '..') for part in value.split('/'))
    elif name in ('TermField', 'TermValue', 'IssueCode', 'Citation'):
        TypeAdapter(getattr(models, name)).validate_json(json.dumps(value))
    else:
        raise AssertionError(f'Unresolved field type: {name}')
