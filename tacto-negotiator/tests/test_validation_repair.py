"""The repair model uses a separate contract and cannot create offer terms."""

import json

from negotiator.package_advisor import complete
from negotiator.skill_docs import load_skill
from negotiator.validation_repair import response_schema


def test_repair_schema_lists_only_approved_actions():
    context = {"original_contract": "negotiation-strategy-v1",
               "source_context": {"approved_packages": {"package:one": {}},
                                  "registered_questions": {"question:one": {}}}}
    schema = response_schema(context)
    assert schema["properties"]["selected_id"]["enum"] == [
        "keep", "package:one", "question:one"]
    assert schema["properties"]["kind"]["enum"][-1] == "stated_terms"


def test_repair_uses_independent_provider_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://primary.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "primary-test-key")
    monkeypatch.setenv("LLM_MODEL", "primary-test-model")
    monkeypatch.setenv("VALIDATION_LLM_BASE_URL", "https://validator.invalid/v1")
    monkeypatch.setenv("VALIDATION_LLM_API_KEY", "validator-test-key")
    monkeypatch.setenv("VALIDATION_LLM_MODEL", "validator-test-model")
    sent = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(
                {"selected_id": "keep", "message_index": -1, "quote": ""})}}]}

    class Client:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, url, **kwargs):
            sent.append((url, kwargs))
            return Response()

    monkeypatch.setattr("negotiator.package_advisor.httpx.Client", Client)
    context = {"response_contract": "validation-repair-v1",
               "skill_sha256": load_skill("validation", "validation-repair").sha256,
               "original_contract": "final-offer-advice-v1",
               "source_context": {"approved_packages": {"counter:one": {}},
                                  "latest_supplier_message": {"message_index": 2, "body": "Offer."}},
               "rejection_reason": "unsupported_citation",
               "rejected_response": {"selected_id": "counter:one", "message_index": 2,
                                     "quote": "Invented."}}
    assert complete(context, 5).response["selected_id"] == "keep"
    url, kwargs = sent[0]
    assert url == "https://validator.invalid/v1/chat/completions"
    assert kwargs["json"]["model"] == "validator-test-model"
    assert kwargs["headers"]["Authorization"] == "Bearer validator-test-key"
    assert "# Validation repair" in kwargs["json"]["messages"][0]["content"]
    assert kwargs["json"]["response_format"]["json_schema"]["schema"]["properties"]["selected_id"]["enum"] == [
        "keep", "counter:one"]
