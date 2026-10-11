import copy

from test_package_advisor import fixture

from negotiator.advice import CapacityAdvisor, candidates
from negotiator.questions import catalog


def test_registered_question_carries_complete_package_and_is_asked_once():
    case, threads, move = fixture()
    sid = move["supplier_id"]
    def choose(context, _):
        assert context["response_contract"] == "supplier-actions-v1"
        question_id, question = next((k, v) for k, v in context["registered_questions"].items()
                                     if v["field"] == "contract_months" and v["value"] == 36)
        source = context["supplier_messages"][-1]
        return {"selected_id": question_id, "support_index": 0, "acknowledgement": "consideration",
                "observations": [{"kind": "objection", "message_index": source["message_index"],
                                  "public_note_id": None, "quote": source["body"],
                                  "addressed_fields": ["contract_months"]}]}
    result, trace = CapacityAdvisor(choose, questions=True).select(case, threads, move, remaining_s=60)
    assert trace["changed"] and trace["question_id"].startswith("question_")
    assert result["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert "Could you confirm whether the attached contract term" in result["message"]["body"]
    assert move["message"]["term_sheets"][0]["terms"]["contract_months"] == 24
    threads[sid].append({"from": "buyer", "body": result["message"]["body"],
                         "term_sheets": copy.deepcopy(result["message"]["term_sheets"])})
    assert catalog(threads[sid], move["message"]["term_sheets"][0]["terms"],
                   {"p": result["message"]["term_sheets"][0]["terms"]}) == {}
    threads[sid].append({"from": sid, "status": "open",
                         "body": "No, we cannot accept a longer contract commitment.",
                         "term_sheets": copy.deepcopy(threads[sid][0]["term_sheets"])})
    remaining, _ = candidates(case, threads[sid], move["message"]["term_sheets"][0]["terms"],
                              None, 0.0)
    assert result["message"]["term_sheets"][0]["terms"] not in remaining.values()
    assert catalog(threads[sid], move["message"]["term_sheets"][0]["terms"], remaining) == {}


def test_question_requires_relevant_current_constraint_and_time():
    case, threads, move = fixture()
    def choose(context, _):
        q = next(iter(context["registered_questions"]))
        source = context["supplier_messages"][-1]
        return {"selected_id": q, "support_index": 0, "acknowledgement": "consideration",
                "observations": [{"kind": "stated_terms", "message_index": source["message_index"],
                                  "public_note_id": None, "quote": source["body"],
                                  "addressed_fields": ["contract_months"]}]}
    advisor = CapacityAdvisor(choose, questions=True)
    result, trace = advisor.select(case, threads, move, remaining_s=60)
    assert result == move and trace["reason"] == "quotation_without_trade_evidence"
    assert CapacityAdvisor(choose, questions=True).select(case, threads, move, remaining_s=20)[0] == move
    menus = []
    def inspect(context, _):
        menus.append(context["registered_questions"])
        return {"selected_id": "keep", "observations": [], "support_index": -1,
                "acknowledgement": "none"}
    CapacityAdvisor(inspect, questions=True).select(case, threads, move, remaining_s=30)
    assert menus == [{}]


def test_already_supplied_value_removes_that_question():
    case, threads, move = fixture()
    threads[move["supplier_id"]][-1]["body"] += " The 36-month value is already supplied."
    seen = []
    def keep(context, _):
        seen.append(context)
        return {"selected_id": "keep", "observations": [], "support_index": -1,
                "acknowledgement": "none"}
    CapacityAdvisor(keep, questions=True).select(case, threads, move, remaining_s=60)
    assert all(not (q["field"] == "contract_months" and q["value"] == 36)
               for q in seen[0]["registered_questions"].values())
