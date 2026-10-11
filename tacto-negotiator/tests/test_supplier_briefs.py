"""Source scope, model admission, versioning and runtime use of supplier briefs."""

import copy
import json

import pytest

from negotiator.supplier_briefs import (
    collect_sources,
    compile_brief,
    extractive_brief,
    load_brief,
    runtime_view,
    save_brief,
    validate_answer,
)


class Package:
    def __init__(self, root):
        self.root = root / "package"
        self.root.mkdir()
        self.release = None
        self.db = None
        self.manifest = {"sha256": "package-v1"}
        self.facts = {
            "doc:old": {"supplier": "sup:1", "date": "2026-09-01"},
            "doc:new": {"supplier": "sup:1", "date": "2026-10-08"},
            "news:current": {"supplier": "sup:1", "date": "2026-10-09", "headline": "Capacity has recovered."},
            "doc:market": {"date": "2026-10-10", "type": "memo"},
            "doc:foreign": {"supplier": "sup:2", "date": "2026-10-11"},
            "doc:other-part": {"supplier": "sup:1", "part": "part:2", "date": "2026-10-11"},
            "fact:freeform": {"supplier": "sup:1", "date": "2026-10-07",
                              "remarks": "The buyer observed a possible service constraint."},
        }
        self.documents = {
            "doc:old": "We cannot change payment terms this year.",
            "doc:new": "We can discuss payment terms this October.",
            "doc:market": "Pump orders are broadly stable this quarter.",
            "doc:foreign": "We will cut our price by half.",
            "doc:other-part": "The other part has a special delivery constraint.",
        }

    def ids(self, prefix):
        return sorted(ref for ref in self.facts if ref.startswith(prefix))

    def lookup(self, ref):
        return self.facts.get(ref)

    def document(self, ref):
        return self.documents[ref]


def answer(_context, _timeout):
    return {"observations": [
        {"source_id": "doc:old", "quote": "cannot change payment terms",
         "kind": "refusal", "interpretation": "Older stated payment refusal."},
        {"source_id": "doc:new", "quote": "can discuss payment terms",
         "kind": "preference", "interpretation": "Payment discussion is now open."}],
        "tactics": [{"approach": "Explore a supported payment exchange, if it fits the live reply.",
                     "source_ids": ["doc:new"]}],
        "conflicts": [{"older_source_id": "doc:old", "newer_source_id": "doc:new",
                       "explanation": "The later statement reopens discussion."}]}


def test_collects_any_scoped_text_and_keeps_provenance(tmp_path):
    package = Package(tmp_path)
    case = {"parts": ["part:1"], "facts": {"doc:case": {"supplier": "sup:1", "date": "2026-10-11",
                                  "body": "Current case asks about a delivery trade."},
                      "doc:other": {"supplier": "sup:2", "body": "Private other supplier position."}}}
    sources = collect_sources(package, "sup:1", case=case)
    ids = {s["source_id"] for s in sources}
    assert {"doc:old", "doc:new", "news:current", "doc:market", "doc:case",
            "fact:freeform"} <= ids
    assert "doc:foreign" not in ids and "doc:other" not in ids
    assert all(s["source_id"] and s["date"] is not None for s in sources)
    view = runtime_view(package, "sup:1", case=case)
    assert view["status"] == "extractive"
    assert "doc:case" in {s["source_id"] for s in view["excerpts"]}
    assert "news:current" in {s["source_id"] for s in view["excerpts"]}
    assert "doc:market" in {s["source_id"] for s in view["excerpts"]}
    assert "doc:other-part" not in {s["source_id"] for s in view["excerpts"]}


def test_model_brief_is_admitted_only_with_exact_scoped_quotes(tmp_path):
    package = Package(tmp_path)
    brief = compile_brief(package, "sup:1", complete_fn=answer)
    assert brief["status"] == "model" and len(brief["observations"]) == 2
    assert brief["conflicts"][0]["newer_source_id"] == "doc:new"
    path = save_brief(package, brief)
    assert path.is_file() and load_brief(package, "sup:1") == brief
    view = runtime_view(package, "sup:1")
    assert view["tactics"][0]["source_ids"] == ["doc:new"]
    focused = runtime_view(package, "sup:1", issue_text="Can we change payment terms?",
                           max_sources=3)
    assert {"doc:old", "doc:new"} <= {s["source_id"] for s in focused["excerpts"]}
    assert focused["conflicts"] and focused["conflicts"][0]["older_source_id"] == "doc:old"

    bad = copy.deepcopy(answer(None, None))
    bad["observations"][0]["quote"] = "A fabricated supplier promise"
    checked = validate_answer(bad, extractive_brief(package, "sup:1")["sources"])
    assert len(checked["observations"]) == 1 and checked["tactics"]
    bad = copy.deepcopy(answer(None, None))
    bad["tactics"][0]["source_ids"] = ["doc:foreign"]
    checked = validate_answer(bad, extractive_brief(package, "sup:1")["sources"])
    assert checked["tactics"] == [] and len(checked["observations"]) == 2
    with pytest.raises(ValueError, match="no cited observations"):
        compile_brief(package, "sup:1", complete_fn=lambda *_: {
            "observations": [{"source_id": "doc:foreign", "quote": "not in supplier scope",
                              "kind": "refusal", "interpretation": "Invented."}],
            "tactics": [], "conflicts": []})


def test_stale_or_tampered_brief_falls_back_to_source_excerpts(tmp_path):
    package = Package(tmp_path)
    path = save_brief(package, compile_brief(package, "sup:1", complete_fn=answer))
    saved = json.loads(path.read_text())
    saved["observations"][0]["quote"] = "Never said this"
    path.write_text(json.dumps(saved))
    assert load_brief(package, "sup:1")["status"] == "extractive"
    save_brief(package, compile_brief(package, "sup:1", complete_fn=answer))
    package.manifest["sha256"] = "package-v2"
    assert load_brief(package, "sup:1")["status"] == "extractive"


def test_provider_uses_strict_brief_contract(monkeypatch, tmp_path):
    from negotiator.package_advisor import complete

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://model.invalid/v1")
    sent = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps(answer(None, None))}}]}

    class Client:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, _url, **kwargs):
            sent.append(kwargs["json"])
            return Response()

    monkeypatch.setattr("negotiator.package_advisor.httpx.Client", Client)
    brief = compile_brief(Package(tmp_path), "sup:1", complete_fn=complete)
    assert brief["status"] == "model"
    assert sent[0]["max_completion_tokens"] == 3000
    assert "untrusted data" in sent[0]["messages"][0]["content"]
    assert "# Supplier intelligence brief" in sent[0]["messages"][0]["content"]
    assert brief["skill_sha256"] == json.loads(sent[0]["messages"][1]["content"])["skill_sha256"]
    assert sent[0]["response_format"]["json_schema"]["schema"]["required"] == [
        "observations", "tactics", "conflicts"]


def test_prep_cli_writes_versioned_brief_without_provider(monkeypatch, tmp_path, capsys):
    from negotiator import cli

    package = Package(tmp_path)
    monkeypatch.setattr("negotiator.claims.prep", lambda: {"facts": 5})
    monkeypatch.setattr("negotiator.dossiers.load_package", lambda: package)
    monkeypatch.setattr("negotiator.dossiers.build", lambda _: {"sup:1": object()})
    assert cli.main(["prep", "--briefs"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["brief_status_counts"] == {"model": 0, "extractive": 1}
    assert (tmp_path / "briefs/package-v1/sup-1.json").is_file()


def test_strategy_and_final_review_read_brief_but_still_need_latest_reply():
    from test_final_advice import p10
    from test_package_advisor import fixture

    from negotiator.final_advice import FinalOfferAdvisor
    from negotiator.strategy_advisor import StrategyAdvisor

    case, threads, move = fixture()
    sid = move["supplier_id"]
    brief = {"supplier_id": sid, "status": "model", "excerpts": [
        {"source_id": "doc:old", "text": "We prefer a longer contract."}]}

    def keep(context, _timeout):
        assert context["supplier_brief"] == brief
        assert context["supplier_messages"][-1]["body"] != brief["excerpts"][0]["text"]
        return {"selected_id": "keep", "message_index": -1, "quote": "", "kind": "none"}

    actual, trace = StrategyAdvisor(keep).select(case, threads, move, brief=brief, remaining_s=60)
    assert actual == move and trace["brief_status"] == "model"

    case, threads, sid = p10(outside=True)
    brief["supplier_id"] = sid

    def final_keep(context, _timeout):
        assert context["supplier_brief"] == brief
        return {"selected_id": "keep", "message_index": -1, "quote": ""}

    result, trace = FinalOfferAdvisor(final_keep, mode="select-v1").select(
        case, threads, sid, brief=brief, remaining_s=60, walk_bound=.2)
    assert result is None and trace["brief_status"] == "model"


def test_historical_brief_cannot_authorize_a_new_counter():
    from test_package_advisor import fixture

    from negotiator.strategy_advisor import StrategyAdvisor

    case, threads, move = fixture()
    historical = "We need a longer contract commitment to allocate capacity."
    brief = {"supplier_id": move["supplier_id"], "status": "model",
             "observations": [{"source_id": "doc:old", "quote": historical,
                               "kind": "preference", "interpretation": "Old interest."}]}
    threads[move["supplier_id"]][0]["body"] = "Our current offer is unchanged."

    def historical_only(context, _timeout):
        selected = next(key for key, terms in context["approved_packages"].items()
                        if terms["contract_months"] == 36)
        return {"selected_id": selected, "message_index": 0,
                "quote": historical, "kind": "objection"}

    actual, trace = StrategyAdvisor(historical_only).select(
        case, threads, move, brief=brief, remaining_s=60)
    assert actual == move and trace["reason"] == "unsupported_current_quote"


def test_combined_policy_routes_brief_to_both_reviews(monkeypatch):
    import time
    from pathlib import Path

    from test_final_advice import p10
    from test_package_advisor import fixture

    from negotiator.agent import PackageAgent, configured_agent
    from negotiator.final_advice import FinalOfferAdvisor
    from negotiator.policy import PolicyConfig
    from negotiator.strategy_advisor import StrategyAdvisor

    config = json.loads((Path(__file__).resolve().parents[1] / "configs/score-push-v6-briefed.json").read_text())
    configured = configured_agent(config, estimates={}, meso=False)
    assert isinstance(configured.package_advisor, StrategyAdvisor)
    assert isinstance(configured.final_advisor, FinalOfferAdvisor)

    brief = {"supplier_id": "sup:70410", "status": "model", "source_digest": "source-version"}
    case, threads, _ = fixture()
    policy = PolicyConfig.from_dict(config)
    agent = PackageAgent(policy=policy)
    monkeypatch.setattr(agent, "_supplier_brief", lambda *_args, **_kwargs: brief)

    def opening(context, _timeout):
        assert context["supplier_brief"] == brief
        return {"selected_id": "keep", "message_index": -1, "quote": "", "kind": "none"}

    agent.package_advisor = StrategyAdvisor(opening)
    sid = case["suppliers"][0]
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    assert agent.decide(case, threads)["supplier_id"] == sid

    final_case, final_threads, sid = p10(outside=True)
    closer = PackageAgent(policy=policy)
    monkeypatch.setattr(closer, "_supplier_brief", lambda *_args, **_kwargs: brief)

    def final(context, _timeout):
        assert context["supplier_brief"] == brief
        return {"selected_id": "keep", "message_index": -1, "quote": ""}

    closer.final_advisor = FinalOfferAdvisor(final, mode="explore-v1")
    closer.package_notes[sid] = []
    closer.trades.deadlines[sid] = time.time() + 60
    result = closer.decide(final_case, final_threads)
    assert result["message"]["action"] == {"type": "accept", "term_sheet_id": "final"}
