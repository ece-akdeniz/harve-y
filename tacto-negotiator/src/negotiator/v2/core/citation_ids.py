"""Versioned wire citations resolved from trusted, scoped whole-message spans."""

import json

from . import models as m
from .errors import ContractViolation
from .serialization import semantic_hash


def citation_catalog(conversation):
    return {
        'citation:' + semantic_hash((msg.session_id, msg.thread_id, msg.message_id, msg.content_hash)): m.MessageSpan(
            session_id=msg.session_id, thread_id=msg.thread_id, message_id=msg.message_id,
            start=0, end=len(msg.body), quote=msg.body,
        )
        for msg in conversation.messages if msg.speaker == 'supplier' and msg.body
    }


def wire_schema():
    schema = m.AssessmentDraft.model_json_schema()

    def replace(node):
        if isinstance(node, dict):
            branches = node.get('anyOf', [])
            if {b.get('$ref') for b in branches if isinstance(b, dict)} == {
                '#/$defs/SourceRef', '#/$defs/MessageSpan'}:
                node.clear()
                node.update(type='string', pattern=r'^citation:[0-9a-f]{64}$')
            else:
                for value in node.values():
                    replace(value)
        elif isinstance(node, list):
            for value in node:
                replace(value)
    replace(schema)
    definitions = schema.get('$defs', {})
    reachable = set()

    def visit(node):
        if isinstance(node, dict):
            ref = node.get('$ref', '')
            if ref.startswith('#/$defs/') and ref[8:] not in reachable:
                name = ref[8:]
                reachable.add(name)
                visit(definitions[name])
            for key, value in node.items():
                if key != '$defs':
                    visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    schema['$defs'] = {key: value for key, value in definitions.items() if key in reachable}
    return schema


def resolve_citations(raw, catalog):
    data = json.loads(raw)
    citation_fields = {'citations', 'supporting_refs', 'contradicting_refs'}

    def resolve(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in citation_fields:
                    if not isinstance(value, list):
                        raise ContractViolation('ungrounded_output: citation IDs require a list')
                    resolved = []
                    for ref in value:
                        if not isinstance(ref, str) or ref not in catalog:
                            raise ContractViolation('missing_source: unknown citation ID')
                        resolved.append(catalog[ref].model_dump(mode='json'))
                    node[key] = resolved
                else:
                    resolve(value)
        elif isinstance(node, list):
            for value in node:
                resolve(value)
    resolve(data)
    return json.dumps(data)
