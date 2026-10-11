import copy

from negotiator.assessment import AssessmentStore, admit, digest, refused_candidate, stated_terms_support


def _case():
    return {"case_id": "case:fixture", "type": "capacity", "parts": ["part:one"],
            "negotiable": ["unit_price", "contract_months", "lead_time_days"]}


def _item(kind, index, quote, fields, note=None):
    return {"kind": kind, "message_index": index, "public_note_id": note,
            "quote": quote, "addressed_fields": fields}


def test_condition_refusal_and_independent_admission():
    case = _case()
    events = [
        {"from": "sales@one", "body": "We can add volume only against a binding 12-month commitment."},
        {"from": "buyer", "body": "Our offer."},
        {"from": "sales@one", "body": "We cannot agree to a 36-month commitment."},
    ]
    notes = [{"id": "doc:one", "supplier_id": "sup:one", "part": "part:one",
              "date": "2026-09-01", "text": "Delivery capacity is tight this quarter."}]
    raw = [
        _item("conditional_trade", 0, events[0]["body"], ["contract_months"]),
        _item("refusal", 2, events[2]["body"], ["contract_months"]),
        _item("objection", -1, notes[0]["text"], ["lead_time_days"], "doc:one"),
        _item("refusal", 2, "Invented supplier statement.", ["contract_months"]),
    ]
    admitted, rejected = admit(raw, case, events, "sup:one", notes, session_id="session:one")
    assert len(admitted) == 3 and rejected == [{"index": 3, "reason": "invalid_source_or_quote"}]
    assert admitted[0]["condition"] == {"antecedent": "a binding 12-month commitment.",
                                         "consequence": "We can add volume only", "status": "explicit"}
    assert admitted[0]["lifecycle"] == "superseded"
    assert admitted[0]["prior_source_id"] == admitted[1]["source"]["source_id"]
    assert admitted[1]["lifecycle"] == "active"
    assert admitted[2]["source"]["date"] == "2026-09-01"


def test_conditions_mislabeled_or_split_are_not_admitted():
    case = _case()
    body = "If you sign a 12-month contract, we can reserve the extra capacity."
    events = [{"from": "sales@one", "body": body}]
    raw = [_item("preference", 0, body, ["contract_months"]),
           _item("conditional_trade", 0, "we can reserve the extra capacity.", ["contract_months"]),
           _item("conditional_trade", 0, body, ["contract_months"])]
    admitted, rejected = admit(raw, case, events, "sup:one")
    assert len(admitted) == 1
    assert [r["reason"] for r in rejected] == ["condition_mislabeled", "condition_without_cue"]
    assert admitted[0]["condition"]["antecedent"] == "you sign a 12-month contract"


def test_field_labels_need_independent_source_cue():
    case = _case()
    events = [{"from": "sales@one", "body": "We reject a longer contract commitment."}]
    admitted, rejected = admit([_item("refusal", 0, events[0]["body"], ["lead_time_days"])],
                               case, events, "sup:one")
    assert admitted == [] and rejected[0]["reason"] == "field_without_cue"


def test_stated_delivery_terms_cannot_be_labeled_an_objection():
    case = _case()
    body = "Delivery is 42 days."
    admitted, rejected = admit([_item("objection", 0, body, ["lead_time_days"])],
                               case, [{"from": "supplier", "body": body}], "sup:one")
    assert not admitted and rejected[0]["reason"] == "objection_without_constraint"


def test_explicit_alternatives_support_only_stated_nonprice_fields():
    quote = "Alternatively, with Lieferzeit 54 days, we can offer EUR 31.90 per unit."
    assert stated_terms_support(quote, ["lead_time_days"], {"lead_time_days": 56})
    assert not stated_terms_support(quote, ["lead_time_days"], {"lead_time_days": 42})
    assert not stated_terms_support(quote, ["payment_days"], {"payment_days": 54})
    assert not stated_terms_support("Delivery is 54 days.", ["lead_time_days"],
                                    {"lead_time_days": 56})
    assert stated_terms_support("Alternativ bieten wir 60 Tage Lieferzeit an.",
                                ["lead_time_days"], {"lead_time_days": 60})


def test_payment_days_cannot_be_cited_as_delivery_evidence():
    case = {**_case(), "negotiable": ["payment_days", "lead_time_days"]}
    body = "We need payment in 30 days. Delivery in 42 days would work."
    events = [{"from": "supplier", "body": body}]
    wrong, rejected = admit([_item("objection", 0, body[:27], ["lead_time_days"])],
                            case, events, "sup:one")
    assert wrong == [] and rejected == [{"index": 0, "reason": "field_without_cue"}]
    right, rejected = admit([_item("objection", 0, body[:27], ["payment_days"]),
                             _item("preference", 0, "Delivery in 42 days would work.",
                                   ["lead_time_days"])], case, events, "sup:one")
    assert not rejected and [set(item["field_spans"]) for item in right] == [
        {"payment_days"}, {"lead_time_days"}]


def test_conditional_antecedent_must_match_candidate_terms():
    from negotiator.assessment import condition_supported

    case = {**_case(), "negotiable": ["unit_price", "payment_days", "lead_time_days"]}
    body = "If you pay in 30 days, we can deliver in 42 days."
    item, rejected = admit([_item("conditional_trade", 0, body, ["lead_time_days"])],
                           case, [{"from": "supplier", "body": body}], "sup:one")
    assert not rejected
    assert not condition_supported(item[0], {"payment_days": 60, "lead_time_days": 42})
    assert condition_supported(item[0], {"payment_days": 30, "lead_time_days": 42})


def test_conditional_antecedent_cannot_swap_values_between_fields():
    from negotiator.assessment import condition_supported

    case = {**_case(), "negotiable": ["payment_days", "contract_months"]}
    body = "If you pay in 30 days and sign a 36-month contract, we can reserve capacity."
    event, rejected = admit([_item("conditional_trade", 0, body, ["contract_months"])],
                            case, [{"from": "supplier", "body": body}], "sup:one")
    assert not rejected
    assert condition_supported(event[0], {"payment_days": 30, "contract_months": 36})
    assert not condition_supported(event[0], {"payment_days": 36, "contract_months": 30})


def test_german_payment_and_delivery_have_distinct_spans():
    case = {**_case(), "negotiable": ["payment_days", "lead_time_days"]}
    body = "Zahlung in 30 Tagen ist nötig. Die Lieferzeit beträgt 42 Tage."
    events = [{"from": "supplier", "body": body}]
    payment, delivery = body.split(". ")
    admitted, rejected = admit([_item("objection", 0, payment, ["payment_days"]),
                                _item("stated_terms", 0, delivery, ["lead_time_days"])],
                               case, events, "sup:one")
    assert not rejected
    assert [item["observations"][0]["value"] for item in admitted] == [30, 42]
    assert admitted[0]["observations"][0]["source_span"]["end"] <= len(payment)
    assert admitted[1]["observations"][0]["source_span"]["start"] > len(payment)


def test_restart_round_trip_discards_stale_and_foreign_state(tmp_path):
    case = _case()
    events = [{"from": "sales@one", "body": "We cannot agree to a longer contract."}]
    admitted, rejected = admit([_item("refusal", 0, events[0]["body"], ["contract_months"])],
                               case, events, "sup:one", session_id="session:one")
    assert not rejected
    store = AssessmentStore(tmp_path / "assessment.jsonl")
    store.append(admitted)
    assert store.reconstruct(case, events, "sup:one", session_id="session:one") == admitted
    assert store.reconstruct(case, events, "sup:one", session_id="session:other") == []
    updated = copy.deepcopy(events)
    updated[0]["body"] += " A newer reply changes the history."
    assert digest(updated) != digest(events)
    assert store.reconstruct(case, updated, "sup:one", session_id="session:one") == []


def test_restart_drops_old_field_confused_observation(tmp_path):
    case = {**_case(), "negotiable": ["payment_days", "lead_time_days"]}
    events = [{"from": "supplier", "body": "We need payment in 30 days."}]
    item, _ = admit([_item("objection", 0, events[0]["body"], ["payment_days"])],
                    case, events, "sup:one", session_id="session:one")
    bad = copy.deepcopy(item[0])
    bad["fields"] = ["lead_time_days"]
    store = AssessmentStore(tmp_path / "assessment.jsonl")
    store.append([bad])
    assert store.reconstruct(case, events, "sup:one", session_id="session:one") == []


def test_reservation_is_charged_after_restart(tmp_path):
    store = AssessmentStore(tmp_path / "assessment.jsonl")
    store.append([{"record": "reservation", "session_id": "session:one", "supplier_id": "sup:one",
                   "update_hash": "abc", "seconds": 8.0}])
    assert store.reservations("session:one")[0]["update_hash"] == "abc"
    assert store.reservations("session:other") == []


def test_source_valid_fact_survives_new_reply_and_new_refusal_supersedes_it(tmp_path):
    case = _case()
    events = [{"from": "sales@one", "body": "Longer contracts help our capacity plan."}]
    first, _ = admit([_item("objection", 0, events[0]["body"], ["contract_months"])],
                     case, events, "sup:one", session_id="session:one")
    store = AssessmentStore(tmp_path / "assessment.jsonl")
    store.append(first)
    events.append({"from": "sales@one", "body": "We cannot accept longer contracts now."})
    second, _ = admit([_item("refusal", 1, events[1]["body"], ["contract_months"])],
                      case, events, "sup:one", session_id="session:one")
    store.append(second)
    rebuilt = store.reconstruct(case, events, "sup:one", session_id="session:one")
    assert len(rebuilt) == 2
    assert rebuilt[0]["lifecycle"] == "superseded"
    assert rebuilt[1]["lifecycle"] == "active"


def test_explicit_corrected_contract_statement_supersedes_old_refusal(tmp_path):
    case = _case()
    events = [{"from": "supplier", "body": "We cannot accept a longer contract."}]
    old, _ = admit([_item("refusal", 0, events[0]["body"], ["contract_months"])],
                   case, events, "sup:one", session_id="session:one")
    events.append({"from": "supplier", "body": "We can now accept a 36-month contract."})
    new, _ = admit([_item("concession", 1, events[1]["body"], ["contract_months"])],
                   case, events, "sup:one", session_id="session:one")
    store = AssessmentStore(tmp_path / "assessment.jsonl")
    store.append(old + new)
    rebuilt = store.reconstruct(case, events, "sup:one", session_id="session:one")
    assert [item["lifecycle"] for item in rebuilt] == ["superseded", "active"]


def test_explicit_refusal_blocks_matching_trade_until_newer_acceptance():
    reference = {"contract_months": 24, "unit_price": 28.34}
    candidate = {**reference, "contract_months": 36}
    events = [{"from": "sales@one", "body": "We cannot accept a longer commitment."}]
    assert refused_candidate(events, reference, candidate)
    events.append({"from": "sales@one", "body": "We can accept a 36-month contract now."})
    assert not refused_candidate(events, reference, candidate)
    assert not refused_candidate(events[:1], reference, reference)
