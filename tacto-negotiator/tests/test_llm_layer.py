"""Opt-in model layer: shared client/budget and `model_traits` (verbatim quotes, union, fallbacks)."""

import json
import os
import time
from pathlib import Path

import pytest
from arena_kit.cost import total_cost

from negotiator import llm_traits
from negotiator.agent import PackageAgent
from negotiator.llm import LlmClient, TurnBudget
from negotiator.optimizer import alternative_cost
from negotiator.policy import PolicyConfig

DATA = Path(os.environ.get("ARENA_DATA", "data/package"))
needs_data = pytest.mark.skipif(not (DATA / "facts.json").is_file(), reason="data package not present")


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def msg(status, *sheets, body=""):
    return {"from": "sales", "status": status, "body": body, "attachments": [{
        "name": "quote-1.pdf", "text": "Our standard terms\nPayment terms (days net) 30\nIncoterm FCA"}],
        "term_sheets": [{"term_sheet_id": i, "terms": t} for i, t in sheets]}


def stub(answer):
    """A complete_fn with the bounded_call signature returning `answer` (or raising it)."""
    def fn(context, timeout_s):
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer):
            return answer(context, timeout_s)
        return json.loads(json.dumps(answer))
    return fn


SOURCES = [{"id": "doc:1", "text": "Call with sales: they could take additional parts at short notice; "
                                   "the second shift has been on hold since spring."},
           {"id": "doc:2", "text": "Could you settle our invoices in 10 days? We would give a cash discount."}]


# -- quote validator ------------------------------------------------------------------------------
def test_fabricated_or_paraphrased_quotes_are_dropped():
    raw = {"traits": [
        {"trait": "idle_capacity", "quote": "the second shift has been on hold since spring", "source": "doc:1"},
        {"trait": "wants_fast_payment", "quote": "they want faster payment for a discount", "source": "doc:2"},
        {"trait": "wants_fast_payment", "quote": "settle our invoices in 10 days", "source": "doc:2"},
        {"trait": "liquidity_crisis", "quote": "the second shift has been on hold", "source": "doc:9"},
        {"trait": "made_up_trait", "quote": "the second shift has been on hold", "source": "doc:1"},
        {"trait": "idle_capacity", "quote": "short", "source": "doc:1"},
    ]}
    out = llm_traits.validate(raw, SOURCES)
    assert [(x["trait"], x["source"]) for x in out] == [
        ("idle_capacity", "doc:1"), ("wants_fast_payment", "doc:2"), ("liquidity_crisis", "doc:1")]
    assert all(llm_traits.verbatim(x["quote"], next(s["text"] for s in SOURCES if s["id"] == x["source"]))
               for x in out)


def test_whitespace_only_differences_count_as_verbatim_but_word_changes_do_not():
    text = "price changes above 2 %\nneed the approval of their   pricing committee"
    assert llm_traits.verbatim("price changes above 2 % need the approval of their pricing committee", text)
    assert not llm_traits.verbatim("price changes above 3 % need the approval of their pricing committee", text)


def test_aliases_map_onto_existing_lever_names():
    raw = {"traits": [{"trait": "capacity_idle", "quote": "the second shift has been on hold", "source": "doc:1"}]}
    assert llm_traits.validate(raw, SOURCES)[0]["trait"] == "idle_capacity"


# -- client, timeouts, budget ---------------------------------------------------------------------
def test_timeout_and_garbage_fall_back_to_no_traits_and_are_recorded():
    def slow(context, timeout_s):
        time.sleep(0.3)
        return {"traits": []}

    client = LlmClient(slow, timeout_s=0.05)
    assert llm_traits.extract(client, SOURCES) == []
    client = LlmClient(stub(ValueError("boom")))
    assert llm_traits.extract(client, SOURCES) == []
    client = LlmClient(stub({"traits": "not a list"}))
    assert llm_traits.extract(client, SOURCES) == []
    m = client.metrics()
    assert m["calls"] == 1 and m["fallbacks"] == 0 and m["by_kind"]["traits"]["calls"] == 1


def test_turn_budget_skips_calls_once_spent_or_window_short():
    b = TurnBudget(budget_s=8.0)
    assert b.allow("traits", window_s=59)
    assert not b.allow("traits", window_s=10)
    b.charge(7.5)
    assert not b.allow("choice")
    assert b.timeout_for() == 0.5
    assert [s["kind"] for s in b.skipped] == ["traits", "choice"]


def test_reader_caches_per_supplier_and_prefetches_in_parallel():
    calls = []

    def fn(context, timeout_s):
        calls.append(context[1]["texts"][0]["id"])
        time.sleep(0.2)
        return {"traits": [{"trait": "idle_capacity", "quote": context[1]["texts"][0]["text"][:40],
                            "source": context[1]["texts"][0]["id"]}]}

    class D:
        def __init__(self, i):
            self.notes = [{"id": f"doc:{i}", "text": f"supplier {i}: they could take additional parts at short notice"}]
            self.traits = set()

    reader = llm_traits.TraitReader(LlmClient(fn))
    started = time.monotonic()
    reader.prefetch_async({f"sup:{i}": D(i) for i in range(3)}).result(timeout=2)
    assert time.monotonic() - started < 0.5  # three reads, concurrently
    assert sorted(calls) == ["doc:0", "doc:1", "doc:2"]
    assert reader.traits("sup:2") == {"idle_capacity"} and reader.evidence("sup:2", "idle_capacity") == ["doc:2"]
    reader.read("sup:2", D(2))
    assert len(calls) == 3  # cache hit, no new call


# -- agent integration ----------------------------------------------------------------------------
@needs_data
def test_model_only_fast_payment_trait_activates_the_lever_with_a_quoted_source(monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    c = case("case:P02")  # supplier 70510 has no fast-payment note: regex trait absent
    sid = c["suppliers"][0]
    from negotiator.dossiers import build_one, load_package

    note = build_one(load_package(), sid).notes[0]
    answer = {"traits": [{"trait": "wants_fast_payment", "quote": note["text"][:60], "source": note["id"]}]}
    policy = PolicyConfig.from_dict({"version": 1, "fast_payment_types": ["price_increase"],
                                     "model_traits": ["price_increase"]})
    agent = PackageAgent(policy=policy, claims=False, llm=stub(answer))
    off = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "fast_payment_types": ["price_increase"]}),
                       claims=False)
    m0 = msg("open", ("offer:0", {"unit_price": 380.0, "payment_days": 30}))
    terms_on = agent.propose(c, {sid: [m0]}, sid)["message"]["term_sheets"][0]["terms"]
    terms_off = off.propose(c, {sid: [m0]}, sid)["message"]["term_sheets"][0]["terms"]
    options = c["term_options"]["payment_days"]
    assert terms_off["payment_days"] != min(options) and terms_on["payment_days"] == min(options)
    assert agent.trait_reader.evidence(sid, "wants_fast_payment") == [note["id"]]
    assert agent.llm.metrics()["calls"] == 1


@needs_data
def test_model_only_trait_never_raises_cost_above_schedule_or_alternative(monkeypatch):
    """Traits only switch between code-priced packages: the offer's C stays at or below the plain
    schedule's C and below the alternative, for every trait the model could assert."""
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    c = case("case:P02")
    sid = c["suppliers"][0]
    from negotiator.dossiers import build_one, load_package

    note = build_one(load_package(), sid).notes[0]
    m0 = msg("open", ("offer:0", {"unit_price": 380.0, "payment_days": 30}))
    std = {"payment_days": 30, "incoterm": "FCA"}
    base_policy = {"version": 1, "fast_payment_types": ["price_increase"], "package_types": ["price_increase"]}
    plain = PackageAgent(policy=PolicyConfig.from_dict(base_policy), claims=False)
    c_plain = total_cost(c, plain.propose(c, {sid: [m0]}, sid)["message"]["term_sheets"][0]["terms"], std)
    for trait in sorted(llm_traits.TRAITS):
        answer = {"traits": [{"trait": trait, "quote": note["text"][:60], "source": note["id"]}]}
        agent = PackageAgent(policy=PolicyConfig.from_dict({**base_policy, "model_traits": ["price_increase"]}),
                             claims=False, llm=stub(answer))
        terms = agent.propose(c, {sid: [m0]}, sid)["message"]["term_sheets"][0]["terms"]
        c_model = total_cost(c, terms, std)
        assert c_model <= c_plain + 1e-6, trait
        assert c_model < alternative_cost(c), trait


def test_missing_llm_env_leaves_rules_only(monkeypatch):
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    agent = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "model_traits": ["bundling"]}), claims=False)
    assert agent.llm is None and agent.trait_reader is None
    assert agent.experiment_metrics()["llm"] is None


def test_fresh_llm_config_is_v3_plus_model_fields():
    v3 = json.loads(Path("configs/score-push-v3.json").read_text())
    cfg = json.loads(Path("configs/fresh-llm.json").read_text())
    types = ["bundling", "capacity", "price_increase", "quality", "raw_material", "renewal", "rfq"]
    assert cfg == {**v3, "model_traits": types, "model_choice": types, "model_answers": types}
    assert json.loads(Path("configs/fresh-llm-run.json").read_text())["policy_config"] == cfg
    PolicyConfig.load("configs/fresh-llm.json")
