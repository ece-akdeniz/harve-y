"""One approved offline experiment: connectivity, P10, and existing three-arm benchmark.

No Arena client, sending port, retries, prompt tuning or proposal generation.
"""

import argparse
import asyncio
import json
import os
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from negotiator.v2.adapters.chat_completions import ChatCompletionConfig, ChatCompletionsTransport
from negotiator.v2.adapters.model import AsyncModelGateway
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core import models as m
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.economics.finite import SuppliedCandidateGenerator
from negotiator.v2.factory import run_recorded_decision
from negotiator.v2.intelligence.interpreter import GroundedInterpreter, InterpreterConfig
from negotiator.v2.orchestration.budgets import failure
from negotiator.v2.orchestration.offline import OfflineDecisionTrace
from negotiator.v2.strategy.selection import BoundedModelSelector, SelectorConfig
from tests.v2.contracts.test_cost_projection import AS_OF
from tests.v2.contracts.test_layered_resolver import changed
from tests.v2.contracts.test_package_evaluation import package
from tests.v2.integration.test_grounded_selection import CatalogPolicy, flexible
from tests.v2.integration.test_offline_decision import recorded
from tests.v2.integration.test_offline_decision import services as benchmark_services

from .evaluate_selection import evaluate
from .run_p10_llm import DATASET, PER_CALL_TOKENS, Clock, services
from .run_p10_llm import run as p10_preflight
from .run_selection_pilot import run as pilot_preflight

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = "gpt-4.1-mini-2025-04-14"
MAX_CALLS = 77  # connectivity 1 + P10 4 + 24 * (direct 1 + grounded 2)
INPUT_RATE, OUTPUT_RATE = Decimal("0.40"), Decimal("1.60")
CALL_USD = Decimal(PER_CALL_TOKENS) * OUTPUT_RATE / 1000000


def datasets():
    return {
        "p10": json.loads(DATASET.read_text()),
        "benchmark": json.loads((ROOT / "tests/fixtures/v2/selection-pilot.json").read_text()),
        "relationship": json.loads((ROOT / "tests/fixtures/v2/relationship.json").read_text()),
    }


def configuration():
    """Consume dotenv at entry point; never print key, URL or ambient environment."""
    provider = os.environ.get("LLM_PROVIDER", "")
    endpoint = os.environ.get("LLM_BASE_URL", "")
    model = os.environ.get("LLM_MODEL", "")
    if provider != "openai" or endpoint.rstrip("/") != "https://api.openai.com/v1":
        raise ValueError("this priced experiment requires explicitly approved direct OpenAI configuration")
    if model not in {"gpt-4.1-mini", SNAPSHOT}:
        raise ValueError("configured model must be the approved gpt-4.1-mini family")
    if not os.environ.get("LLM_API_KEY"):
        raise ValueError("LLM_API_KEY is missing")
    return ChatCompletionConfig(
        base_url=endpoint, provider_id=provider, model_id=SNAPSHOT, request_model_id=model
    ).checked()


def plan(data, config):
    heldout = [e for e in data["benchmark"]["examples"] if e["split"] == "held-out"]
    import hashlib

    digest = hashlib.sha256(json.dumps(heldout, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != data["benchmark"]["held_out_sha256"]:
        raise ValueError("frozen held-out subset changed")
    return {
        "authorized": False,
        "provider": "OpenAI direct",
        "base_url": config.base_url,
        "request_model": config.request_model_id,
        "response_model": config.model_id,
        "dataset_hashes": {k: semantic_hash(v) for k, v in data.items()},
        "permitted_projection": "Existing V2 message/assessment/action projections only; no raw buyer data or labels",
        "max_usd": "5.00",
        "input_usd_per_million": str(INPUT_RATE),
        "output_usd_per_million": str(OUTPUT_RATE),
        "max_calls": MAX_CALLS,
        "max_total_reserved_tokens": MAX_CALLS * PER_CALL_TOKENS,
        "max_output_tokens_per_call": 2048,
        "conservative_usd_reservation": str(MAX_CALLS * CALL_USD),
        "token_accounting_confirmed": False,
        "token_accounting": "utf8-byte-upper-bound-v1; two messages plus 256 framing tokens",
        "held_out_sha256": digest,
        "held_out_review": data["benchmark"]["review_status"],
        "single_run": True,
    }


def approve(auth, expected):
    comparable = {k: v for k, v in expected.items() if k not in {"authorized", "token_accounting_confirmed"}}
    if auth.get("authorized") is not True or auth.get("token_accounting_confirmed") is not True:
        raise ValueError("explicit provider/model/dataset/$5 and token accounting approval required")
    if any(auth.get(k) != v for k, v in comparable.items()):
        raise ValueError("authorization differs from reviewed experiment plan")


class SpendGuard:
    """Reserve before every attempt, including failed/cancelled/unknown-usage requests."""

    def __init__(self, transport, *, max_usd=Decimal("5.00"), max_calls=MAX_CALLS):
        self.transport = transport
        self.max_usd, self.max_calls = max_usd, max_calls
        self.reserved = Decimal(0)
        self.calls = []

    async def __call__(self, request, budget):
        if budget.max_tokens > PER_CALL_TOKENS or len(self.calls) >= self.max_calls:
            raise ValueError("absolute call/token experiment allowance exhausted")
        if self.reserved + CALL_USD > self.max_usd:
            raise ValueError("absolute experiment expenditure ceiling exhausted")
        self.reserved += CALL_USD
        row = {
            "call_id": str(request.call_id),
            "task": request.task,
            "status": "incomplete",
            "reserved_usd": str(CALL_USD),
            "input_tokens": None,
            "output_tokens": None,
        }
        self.calls.append(row)
        started = time.monotonic()
        try:
            result = await self.transport(request, budget)
            row["status"] = result.kind
            row["transport_issues"] = [i.detail for i in result.issues]
            if result.kind == "success":
                row.update(input_tokens=result.usage.input_tokens, output_tokens=result.usage.output_tokens)
                if result.usage.input_tokens is not None and result.usage.output_tokens is not None:
                    cost = (result.usage.input_tokens * INPUT_RATE + result.usage.output_tokens * OUTPUT_RATE) / 1000000
                    row["uncached_usage_cost_usd"] = str(cost)
                    # Stop further work if a provider reports spending outside the reservation.
                    self.reserved += max(Decimal(0), cost - CALL_USD)
            return result
        except asyncio.CancelledError:
            row["status"] = "cancelled"
            raise
        finally:
            row["latency_s"] = time.monotonic() - started

    def report(self):
        return {
            "attempts": len(self.calls),
            "reserved_usd": str(self.reserved),
            "uncached_reported_usage_cost_usd": str(
                sum((Decimal(c.get("uncached_usage_cost_usd", "0")) for c in self.calls), Decimal(0))
            ),
            "unknown_usage_calls": sum(c["input_tokens"] is None or c["output_tokens"] is None for c in self.calls),
            "billing_note": (
                "Usage-derived estimate, no cache discount; "
                "reservations cover unknown/rejected calls. Not a provider invoice."
            ),
            "calls": self.calls,
        }


class HistoricalClock:
    """Synthetic offline evidence clock, real elapsed inference time; no remote authority."""

    def __init__(self):
        self.start = time.monotonic()

    def utcnow(self):
        return AS_OF + timedelta(seconds=time.monotonic() - self.start)

    def monotonic(self):
        return time.monotonic()


def attach(coordinator, snapshot, config, transport, clock, arm):
    gateway = AsyncModelGateway(transport=transport)
    ic = InterpreterConfig(
        provider_id=config.provider_id,
        protocol_id=config.protocol_id,
        model_id=config.model_id,
        prompt_version="grounded-supplier-v1",
        task_schema_version="assessment-draft-v1",
        max_tokens=PER_CALL_TOKENS,
        time_limit_s=Decimal("8"),
        approved_message_hashes=tuple(msg.content_hash for msg in snapshot.conversation.messages),
    )
    if arm == "grounded":
        coordinator.interpreter = GroundedInterpreter(model=gateway, clock=clock, config=ic)
    if arm != "minimum":
        coordinator.selector = BoundedModelSelector(
            model=gateway,
            clock=clock,
            config=SelectorConfig(
                **{
                    **ic.model_dump(),
                    "prompt_version": "grounded-selection-v1",
                    "task_schema_version": "selector-response-v1",
                    "time_limit_s": Decimal("4"),
                }
            ),
        )
        coordinator.model_token_limit = 32768


async def benchmark_decision(data, example, arm, config, transport):
    clock = HistoricalClock()
    inputs = recorded(flexible(data["relationship"]), amount=example["amount"], body=example["text"])
    inputs = changed(
        inputs,
        budget=changed(
            inputs.budget,
            model_call_limit=2,
            model_time_limit_s=Decimal("12"),
            compute_limit_s=Decimal("35"),
            fallback_reserve_s=Decimal("5"),
            submission_reserve_s=Decimal("5"),
        ),
    )
    assembler, coordinator = benchmark_services(inputs, clock=clock)
    snapshot = assembler.assemble(inputs)
    packages = tuple(
        package(
            {"unit_price": 49, "payment_days": 60, "lead_time_days": lead, "contract_months": months},
            snapshot.context.economic,
        )
        for lead, months in ((21, 12), (49, 12), (21, 36))
    )
    inputs = changed(inputs, packages=packages)
    coordinator.generator = SuppliedCandidateGenerator(packages=packages)
    coordinator.proposal = CatalogPolicy(supplier_id="sup:F")
    attach(coordinator, snapshot, config, transport, clock, arm)
    return await run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator)


def record(trace, example_id, arm):
    trace.verify()
    if trace.validation is None or trace.validation.kind != "valid":
        raise ValueError("independent final validation failed")
    selected = next(i for i in trace.evaluations.items if i.candidate.candidate_id == trace.decision.candidate_id)
    action = selected.candidate.contents
    if action.kind == "question":
        label = action.question_id
    else:
        bindings = {t.field: t.value for t in action.packages[0].bindings}
        label = (
            "delivery"
            if bindings["lead_time_days"] == 49
            else ("commitment" if bindings["contract_months"] == 12 else "minimum")
        )
    if example_id.startswith("p10:"):
        label = action.kind
    return dict(
        example_id=example_id,
        arm=arm,
        action=label,
        admitted=True,
        selected_candidate_id=trace.decision.candidate_id,
        selected_contents_hash=semantic_hash(selected.candidate.contents),
        universe_hash=semantic_hash(
            [(i.candidate.contents, tuple(r.nominal_cost for r in i.economic)) for i in trace.evaluations.items]
        ),
        official_costs=[str(r.nominal_cost.amount) for r in selected.economic],
        all_official_costs=[str(r.nominal_cost.amount) for i in trace.evaluations.items for r in i.economic],
        assessment_status=trace.assessment.status,
        fallback=trace.decision.fallback_code is not None,
        fallback_code=trace.decision.fallback_code,
        grounded_departure=label != "minimum"
        and bool(trace.decision.citations)
        and trace.decision.fallback_code is None,
        calls=len(trace.model_calls),
        charged_tokens=sum(c.charged_tokens for c in trace.model_calls),
        unknown_usage_calls=sum(
            c.usage.input_tokens is None or c.usage.output_tokens is None for c in trace.model_calls
        ),
        latency_s=sum(float(c.elapsed_s) for c in trace.model_calls),
        model_outputs=[
            dict(task=c.request.task, transport_status=c.result_kind, rejection_cause=c.cause)
            for c in trace.model_calls
        ],
        batch_hash=trace.evaluations.batch_hash,
        trace_hash=trace.trace_hash,
    )


async def connectivity(preflight, config, guard, output):
    trace = OfflineDecisionTrace.model_validate_json((preflight / "message-0-model.json").read_text())
    original = trace.model_calls[-1].request
    option = next(o for o in original.input.options if o.candidate_id == trace.decision.candidate_id)
    request = changed(
        original,
        call_id=uuid4(),
        correlation_id=uuid4(),
        provider_id=config.provider_id,
        model_id=config.model_id,
        protocol_id=config.protocol_id,
        input=changed(original.input, options=(option,)),
    )
    budget = m.ModelBudget(
        deadline_at=Clock().utcnow() + timedelta(seconds=4),
        time_limit_s=Decimal("4"),
        max_tokens=PER_CALL_TOKENS,
        max_calls=1,
        retry_limit=0,
    )
    try:
        async with asyncio.timeout(4):
            result = await guard(request, budget)
    except TimeoutError:
        result = failure(request, "timeout", "structured connectivity deadline exceeded", Decimal("4"))
    valid = False
    if result.kind == "success":
        try:
            decoded = m.SelectorResponse.model_validate_json(result.raw_response_json)
            valid = decoded.selected_id == option.candidate_id and decoded.supporting_quote == ""
        except ValueError:
            pass
    (output / "connectivity.json").write_text(
        json.dumps(
            {
                "transport_status": result.kind,
                "structured_response_valid": valid,
                "requested_model": config.request_model_id,
                "response_model": config.model_id,
                "calls": guard.calls,
            },
            indent=2,
        )
        + "\n"
    )
    if not valid:
        raise ValueError("structured connectivity test failed; remaining hosted work stopped")


async def run(output, authorization=None):
    output.mkdir(parents=True, exist_ok=True)
    # Required local tests first; these never create a hosted transport.
    await p10_preflight(output / "fake-p10")
    await pilot_preflight(output / "fake-benchmark")
    data = datasets()
    config = (
        configuration()
        if authorization is not None
        else ChatCompletionConfig(
            base_url="https://api.openai.com/v1",
            provider_id="openai",
            model_id=SNAPSHOT,
            request_model_id="gpt-4.1-mini",
        )
    )
    expected = plan(data, config)
    (output / "authorization-template.json").write_text(json.dumps(expected, indent=2) + "\n")
    if authorization is None:
        return {"status": "prepared; no hosted calls", "plan": expected}
    approve(json.loads(authorization.read_text()), expected)
    with (output / "hosted-started.json").open("x") as marker:
        json.dump(expected, marker)
    report = {"evidence": "actual hosted inference", "plan": expected, "p10": [], "records": []}
    async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
        transport = ChatCompletionsTransport(config=config, api_key=os.environ["LLM_API_KEY"], client=client)
        guard = SpendGuard(transport)
        try:
            await connectivity(output / "fake-p10", config, guard, output)
            for index, body in enumerate(data["p10"]["supplier_messages"]):
                clock = Clock()
                inputs = recorded_p10(data["p10"], message=body, now=clock.utcnow())
                baseline_assembler, baseline_coordinator = services(inputs, clock)
                baseline = await run_recorded_decision(
                    inputs, assembler=baseline_assembler, coordinator=baseline_coordinator
                )
                assembler, coordinator = services(inputs, clock, guard, config)
                trace = await run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator)
                if semantic_hash(
                    [(i.candidate.contents, i.economic) for i in trace.evaluations.items]
                ) != semantic_hash([(i.candidate.contents, i.economic) for i in baseline.evaluations.items]):
                    raise ValueError("P10 economics changed from deterministic baseline")
                row = record(trace, f"p10:{index}", "grounded")
                row["baseline_candidate_id"] = baseline.decision.candidate_id
                row["decision_changed"] = baseline.decision.candidate_id != trace.decision.candidate_id
                report["p10"].append(row)
                (output / f"p10-{index}.json").write_text(trace.model_dump_json(indent=2) + "\n")
                (output / f"p10-{index}-baseline.json").write_text(baseline.model_dump_json(indent=2) + "\n")
            for example in data["benchmark"]["examples"]:
                universes = []
                for arm in ("minimum", "direct", "grounded"):
                    trace = await benchmark_decision(data, example, arm, config, guard)
                    universes.append(semantic_hash(trace.evaluations))
                    report["records"].append(record(trace, example["id"], arm))
                    (output / f"{example['id'].replace(':', '-')}-{arm}.json").write_text(
                        trace.model_dump_json(indent=2) + "\n"
                    )
                if len(set(universes)) != 1:
                    raise ValueError("strategy arms have different evaluated universes")
            report["scoring"] = evaluate(data["benchmark"], report["records"])
            report["scoring"]["evidence"] = "actual hosted inference; provisional author labels"
            report["scoring"]["limitations"] = [
                "Independent human label review pending; held-out is frozen, not independently reviewed.",
                "forged:0/1 labels test injected fake faults; exclude them from semantic quality conclusions.",
                "No Arena outcomes; offline supplier-language decisions only.",
            ]
            reviewed_manifest = {
                **data["benchmark"],
                "examples": [e for e in data["benchmark"]["examples"] if not e["id"].startswith("forged:")],
            }
            report["semantic_scoring"] = evaluate(reviewed_manifest, report["records"])["arms"]
            report["paired_changes"] = []
            for arm in ("minimum", "direct", "grounded"):
                for pair in sorted({e["pair_id"] for e in data["benchmark"]["examples"]}):
                    ids = [e["id"] for e in data["benchmark"]["examples"] if e["pair_id"] == pair]
                    rows = [r for r in report["records"] if r["arm"] == arm and r["example_id"] in ids]
                    same_universe = len({r["universe_hash"] for r in rows}) == 1
                    if pair != "cost-only" and not same_universe:
                        raise ValueError("paired language comparison changed official universe")
                    report["paired_changes"].append(
                        dict(
                            arm=arm,
                            pair=pair,
                            action_changed=len({r["action"] for r in rows}) != 1,
                            package_changed=len({r["selected_contents_hash"] for r in rows}) != 1,
                            same_economic_universe=same_universe,
                        )
                    )
            report["status"] = "complete"
        except Exception:
            report["status"] = "stopped; inspect safe artifacts; no automatic retry"
            raise
        finally:
            report["inference"] = guard.report()
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    load_dotenv(Path.cwd() / ".env", override=False)
    asyncio.run(run(args.output, args.authorization))
