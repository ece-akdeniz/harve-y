from types import SimpleNamespace

from negotiator.advice import digest
from negotiator.decision_contract import decision_record
from negotiator.state import Journal


def test_decision_record_matches_persisted_exact_payload(tmp_path):
    case = {"case_id": "case:one"}
    threads = {"sup:one": [{"from": "supplier", "body": "Please respond."}]}
    message = {"body": "We propose the attached terms. Could you review them?",
               "term_sheets": [{"terms": {"unit_price": 10}}]}
    decision = {"supplier_id": "sup:one", "message": message}
    agent = SimpleNamespace(_advice_pending={"baseline_payload": "baseline-digest",
                                             "selected_id": "package:one", "candidate_count": 3,
                                             "evidence_ids": ["sha256:source"]}, model_budget=None)
    record = decision_record(agent, case, threads, decision, runner="async")
    assert record["baseline_move_digest"] == "baseline-digest"
    assert record["selected_id"] == "package:one"
    assert record["mandatory_content"] == ["Could you review them?"]
    journal = Journal(tmp_path / "transport.jsonl")
    intent = journal.intent(case["case_id"], "session:one", "sup:one", "send", message,
                            decision_record=record)
    restored = Journal(journal.path).pending(session_id="session:one")[0]
    assert restored["move_id"] == intent["move_id"]
    assert restored["payload"] == message
    assert restored["decision_record"]["final_payload_digest"] == digest(restored["payload"])
