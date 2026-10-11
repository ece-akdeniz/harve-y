"""Read-only contracts: no negotiation sessions or paid inference."""

import json
from datetime import UTC, datetime

import pytest

from experiments.v2.run_lab_local import DATASET
from negotiator.v2.adapters.arena_observations import conversation_from_arena
from negotiator.v2.core.errors import ContractViolation
from negotiator.v2.intelligence.citations import citation_catalog, resolve_citations, wire_schema


def observation():
    case = json.loads(DATASET.read_text())['case']
    supplier = case['suppliers'][0]
    events = [
        {'thread_id': 'thread:test', 'message_id': 'msg:0', 'from': 'supplier', 'body': 'Price EUR 33.',
         'status': 'open', 'term_sheets': [{'term_sheet_id': 'offer:0', 'terms': {'unit_price': 33}}],
         'attachments': [{'attachment_id': 'att:1', 'name': 'quote.pdf', 'type': 'pdf', 'text': 'Quote text'}]},
        {'from': 'buyer', 'body': 'Our counteroffer.', 'term_sheets': [{'terms': {'unit_price': 28}}]},
        {'thread_id': 'thread:test', 'message_id': 'msg:1', 'from': 'supplier', 'body': 'Final price EUR 30.',
         'status': 'final_offer', 'term_sheets': [{'term_sheet_id': 'offer:1', 'terms': {'unit_price': 30}}]},
    ]
    return conversation_from_arena(case, events, session_id='session:test', supplier_id=supplier,
                                   now=datetime.now(UTC), attachment_bytes={'att:1': b'original PDF bytes'})


def test_current_and_historic_sheets_documents_buyer_ack_and_final_offer():
    view = observation()
    assert view.status == 'final_offer'
    assert [m.speaker for m in view.messages] == ['supplier', 'buyer', 'supplier']
    assert view.messages[0].attachments[0].text == 'Quote text'
    assert view.messages[0].attachments[0].text_ref != 'sha256:' + view.messages[0].attachments[0].bytes_hash
    assert not view.messages[0].observed_sheets[0].standing
    assert view.messages[-1].observed_sheets[0].standing
    assert len(view.messages[-1].observed_sheets[0].complete_bindings) > 1


def test_citation_resolution_unicode_and_scope_no_model_offsets():
    view = observation()
    catalog = citation_catalog(view)
    assert len(catalog) == 2  # Buyer history cannot support a supplier claim.
    key = next(iter(catalog))
    result = json.loads(resolve_citations(json.dumps({'observations': [{'citations': [key]}]}), catalog))
    assert result['observations'][0]['citations'][0]['quote'] == view.messages[0].body
    with pytest.raises(ContractViolation, match='unknown citation ID'):
        resolve_citations('{"observations":[{"citations":["citation:forged"]}]}', catalog)
    schema = wire_schema()
    assert schema['$defs']['GroundedObservation']['properties']['citations']['items']['type'] == 'string'


def test_lab_acknowledgement_hook_excludes_uncertain_action():
    from arena_kit.client import ArenaError

    from negotiator.lab.runner import RecordingTable

    class Client:
        fail = False
        reads = 0

        def send_message(self, *args):
            if self.fail:
                raise ArenaError(409, 'late; request not acknowledged')
            return {'status': 'open'}

        def thread(self, *args):
            self.reads += 1
            return {'messages': [{'from': 'buyer', 'body': 'acknowledged by server'}]}

    class Agent:
        acknowledgements = []

        def observe_lab_acknowledgement(self, supplier, thread):
            self.acknowledgements.append(thread)

    client, agent = Client(), Agent()
    table = RecordingTable(client, None, lambda: None)
    table.session_id, table.agent = 'session:test', agent
    table.send('supplier:test', {'body': 'request'})
    assert client.reads == len(agent.acknowledgements) == 1
    client.fail = True
    with pytest.raises(ArenaError):
        table.send('supplier:test', {'body': 'unacknowledged request'})
    assert client.reads == len(agent.acknowledgements) == 1


def test_v3_provider_contract_uses_wire_schema_identity():
    from negotiator.v2.adapters.chat_completions import ChatCompletionConfig, messages_for, response_format
    from negotiator.v2.core import models as m
    from negotiator.v2.core.serialization import semantic_hash
    from tests.v2.dto_spec import example

    raw = example('ModelRequest')
    raw.update(task='interpret', prompt_version='grounded-supplier-v3',
               task_schema_version='assessment-citation-ids-v1', output_schema_hash=semantic_hash(wire_schema()))
    request = m.ModelRequest.model_validate_json(json.dumps(raw))
    config = ChatCompletionConfig(base_url='http://localhost/v1', provider_id=request.provider_id,
                                  model_id=request.model_id, protocol_id=request.protocol_id, structured_output=True)
    assert messages_for(request, config)[0]['role'] == 'system'
    schema = response_format(request, config)['json_schema']['schema']
    assert 'MessageSpan' not in schema['$defs'] and 'SourceRef' not in schema['$defs']


def test_union_diagnostic_prefers_span_branch_and_never_retains_unknown_keys():
    from pydantic import ValidationError

    from negotiator.v2.core import models as m
    from negotiator.v2.core.diagnostics import rejection

    draft = {'observations': [{'observation_id': 'observation:1', 'kind': 'ambiguity', 'dimension': None,
                              'summary': 'Text.', 'citations': [{'session_id': 'session:1', 'thread_id': 'thread:1',
                                                              'message_id': 'msg:1', 'start': 0, 'end': 2,
                                                              'quote': 'Text.', 'secret-key-value': 'sensitive'}]}],
             'reported_constraints': [], 'hypotheses': [], 'uncertainties': [], 'questions': [], 'unknowns': []}
    with pytest.raises(ValidationError) as caught:
        m.AssessmentDraft.model_validate_json(json.dumps(draft))
    diagnostic = rejection(caught.value, 'schema')
    assert 'MessageSpan' in diagnostic.field
    assert diagnostic.union_errors
    assert 'sensitive' not in diagnostic.model_dump_json()
    assert 'secret-key-value' not in diagnostic.model_dump_json()


def test_attachment_text_tampering_invalidates_provenance():
    from pydantic import ValidationError

    from negotiator.v2.core import models as m

    document = observation().messages[0].attachments[0]
    altered = document.model_dump(mode='json')
    altered['text'] = 'Forged attachment content.'
    with pytest.raises(ValidationError):
        m.DocumentRecord.model_validate_json(json.dumps(altered))
