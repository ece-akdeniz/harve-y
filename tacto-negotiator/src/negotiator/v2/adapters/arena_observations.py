"""Public Arena thread normalization shared by simulator and hosted contract inputs.

This reader grants no execution or closing authority. Only server-returned buyer
messages are acknowledged; proposals and locally submitted requests are excluded.
"""

import hashlib
import json

from arena_kit.cost import closing_terms
from arena_kit.docs import standard_terms

from ..core import models as m
from ..core.errors import ContractViolation
from ..core.serialization import semantic_hash
from .p10 import term_binding


def bindings(terms):
    return tuple(m.TermBinding.model_validate_json(json.dumps(term_binding(k, v)))
                 for k, v in sorted(terms.items()))


def with_quote_standards(inputs, events, *, supplier_id, now):
    """Attach standards parsed by the official reader to their original quote evidence."""
    terms = standard_terms(events)
    if not terms:
        return inputs
    attachment = next(att for msg in reversed(events) for att in msg.get("attachments", [])
                      if att.get("name", "").startswith("quote") and att.get("text"))
    basis = inputs.case.parts[0].price_basis
    price = next(t.value for msg in reversed(inputs.server.threads[0].conversation.messages)
                 for sheet in msg.observed_sheets for t in sheet.complete_bindings if t.field == "unit_price")
    observed = bindings(terms)
    payload = m.QuoteFact(kind="quote", supplier=supplier_id, part_ids=basis.part_ids,
                         price=m.Price(amount=price, basis=basis), observed_terms=observed)
    rid = "quote:" + semantic_hash((inputs.server.session_id, supplier_id, attachment))
    record = m.EvidenceRecord(record_id=rid, canonical_id=rid, kind="canonical", payload=payload,
        scope=m.EvidenceScope(supplier_ids=(supplier_id,), part_ids=basis.part_ids,
                              level="part", case_id=inputs.case.case_id),
        provenance=m.Provenance(layer="session", source_version=rid,
            content_hash=semantic_hash(attachment), locator=attachment["attachment_id"], parent_refs=(),
            parser_version="arena-kit-quote-terms/1"),
        temporal=m.TemporalValidity(status="current", observed_at=now, freshness_rule_id="owned-live-quote/1"),
        disclosure=m.DisclosureRule(classification="supplier_own", permitted_recipients=(supplier_id,),
                                   purpose=("cost_input",)))
    ref = m.SourceRef(record_id=rid, canonical_id=rid)
    standard = m.ResolvedStandards(bindings=observed,
        field_origins=tuple(m.FieldOrigin(field=t.field, source_kind="quote", source_refs=(ref,)) for t in observed),
        version_hash="0" * 64)
    standard = standard.model_copy(update={"version_hash": semantic_hash(
        standard.model_dump(mode="json", exclude={"version_hash"}))})
    prepared = inputs.prepared.model_copy(update={"records": inputs.prepared.records + (record,)})
    digest = semantic_hash(prepared.model_dump(mode="json", exclude={"prepared_at", "integrity_hash", "artifact_id"}))
    prepared = prepared.model_copy(update={"integrity_hash": digest, "artifact_id": "sha256:" + digest})
    thread = inputs.server.threads[0].model_copy(update={"standards": standard})
    server = inputs.server.model_copy(update={"threads": (thread,)})
    return inputs.model_copy(update={"prepared": prepared, "server": server,
                                     "state": inputs.state.model_copy(update={"server": server})})


def conversation_from_arena(case, events, *, session_id, supplier_id, now, attachment_bytes):
    supplier_events = [e for e in events if e.get('from') not in {'buyer', 'arena'}]
    if not supplier_events:
        raise ContractViolation('scope_mismatch: missing supplier thread')
    thread_id = supplier_events[0]['thread_id']
    latest = supplier_events[-1]
    standing_id = (latest.get('term_sheets') or [{}])[0].get('term_sheet_id')
    messages = []
    for index, event in enumerate(events):
        speaker = event.get('from') if event.get('from') in {'buyer', 'arena'} else 'supplier'
        if speaker == 'supplier' and event['thread_id'] != thread_id:
            raise ContractViolation('scope_mismatch: mixed Arena threads')
        # Official buyer history has no server message ID. Identity derives from its
        # position and exact acknowledged payload, never from a pending proposal.
        message_id = event.get('message_id') or 'buyer:' + semantic_hash((session_id, thread_id, index, event))
        body = event.get('body', '')
        span = m.MessageSpan(session_id=session_id, thread_id=thread_id, message_id=message_id,
                             start=0, end=len(body), quote=body)
        sheets = tuple(m.ObservedSheet(
            offer_id=s.get('term_sheet_id'), bindings=bindings(s['terms']),
            complete_bindings=bindings(closing_terms(case, s['terms'], standard_terms(events[:index + 1]))),
            source_message_ref=span,
            standing=speaker == 'supplier' and s.get('term_sheet_id') == standing_id,
            parse_issues=(),
        ) for s in event.get('term_sheets', []))
        docs = []
        for att in event.get('attachments', []):
            raw = attachment_bytes.get(att['attachment_id'])
            if raw is None or not isinstance(att.get('text'), str):
                raise ContractViolation('missing_source: attachment bytes/text unavailable')
            text = att['text']
            docs.append(m.DocumentRecord(
                attachment_id=att['attachment_id'], name=att['name'], media_type=att.get('type', 'unknown'),
                bytes_hash=hashlib.sha256(raw).hexdigest(), text=text,
                text_ref='sha256:' + hashlib.sha256(text.encode()).hexdigest(),
                structured_refs=(), parse_status='ok', issues=(),
            ))
        claims = tuple(m.ClaimCheckResult(argument_index=r['index'], result=r['result'], source_message_ref=span)
                       for r in event.get('claim_results', []))
        messages.append(m.ConversationMessage(
            session_id=session_id, thread_id=thread_id, message_id=message_id, supplier_id=supplier_id,
            speaker=speaker, body=body, observed_sheets=sheets, attachments=tuple(docs), claim_results=claims,
            received_at=now, in_reply_to=event.get('in_reply_to'),
            content_hash=hashlib.sha256(body.encode()).hexdigest(),
        ))
    status = latest.get('status', 'open')
    return m.ConversationView(session_id=session_id, thread_id=thread_id, messages=tuple(messages),
                              status=status, version_hash=semantic_hash((status, messages)))
