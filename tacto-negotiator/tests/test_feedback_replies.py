from negotiator.evidence import EvidencePolicy
from negotiator.lab.checkpoints import requires_data, resolve_config
from negotiator.lab.feedback import FeedbackAgent
from negotiator.replies import MAX_CHARS, interpret

pytest_plugins = ["test_evidence"]


def test_hedging_objection_switches_to_other_verified_arguments(context):
    case, move, package, _ = context
    threads = {"sup:F": [{"from": "supplier", "status": "open", "body": "Our energy is hedged."}]}
    result = EvidencePolicy(package).enrich(case, threads, "sup:F", move)
    assert "idx:ENERGY@2026-08" not in result["message"]["refs"]
    assert "sc:F@2026Q3" in result["message"]["refs"]
    assert result["message"]["term_sheets"] == move["message"]["term_sheets"]


def test_final_offer_receives_no_new_argument(context):
    case, move, package, _ = context
    threads = {"sup:F": [{"from": "supplier", "status": "final_offer", "body": "Last offer."}]}
    assert EvidencePolicy(package).enrich(case, threads, "sup:F", move) == move


def test_bounded_extraction_ignores_buyer_and_negated_hedging():
    result = interpret([{"from": "buyer", "body": "We think you are hedged"},
                        {"from": "supplier", "body": "We are not hedged. We prefer faster payment."}])
    assert [s["kind"] for s in result["signals"]] == ["payment_trade"]
    assert result["signals"][0]["message_index"] == 1
    assert interpret([{"body": "x" * (MAX_CHARS + 1)}])["truncated"]


def test_feedback_preserves_failure_and_recovered_score():
    attempt = {"attempt_id": "a", "case_id": "case:P10", "status": "failed", "score": None,
               "timeouts": None, "result": {"reconciled_result": {"score": 0.4532}}, "threads": {}}
    report = FeedbackAgent().review({"run_id": "run", "attempts": [attempt]})
    assert {f["category"] for f in report["findings"]} == {"change", "recovery", "unknown"}
    assert attempt["score"] is None and attempt["status"] == "failed"
    assert not report["policy_changed"]
    assert "0.4532" in report["findings"][1]["observation"]


def test_feedback_identifies_coverage_without_claiming_optimal_tenor():
    report = FeedbackAgent().review({"run_id": "run", "attempts": [{
        "attempt_id": "a", "case_id": "case:P04", "status": "completed", "timeouts": 0,
        "result": {"must_haves_ok": True, "cost_breakdown": {"uncovered_need": 94000}}, "threads": {}}]})
    test = next(f for f in report["findings"] if f["category"] == "test")
    assert "94000.00" in test["observation"]
    assert "not automatically" in test["next_test"]


def test_checkpoint_supports_explicit_policy_and_requires_data():
    config = resolve_config({"estimates": {}, "policy": {"version": 1, "package_types": ["renewal"],
                                                         "evidence_types": ["quality"]}})
    assert config["policy"]["package_types"] == ["renewal"]
    assert config["claims"] is True and requires_data(config)
