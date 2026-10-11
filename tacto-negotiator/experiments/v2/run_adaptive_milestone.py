"""Prepare a reviewable allowance, or execute one explicitly authorized OFFLINE hosted experiment.

Uses the existing Lab runner and official in-process Sim. Never creates an online Arena session.
"""

import argparse
import asyncio
import hashlib
import json
import os
import time
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import httpx
from arena_kit.cli import load_env

from negotiator.lab.publish import _atomic_file, save_snapshot
from negotiator.lab.runner import capture_provenance, plan_run, run_experiment
from negotiator.lab.simulator import InProcessSimulatorClient
from negotiator.v2.adapters.chat_completions import ChatCompletionConfig, ChatCompletionsTransport
from negotiator.v2.adapters.lab import WallClock
from negotiator.v2.adapters.model import AsyncModelGateway
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.factory import bounded_services, local_lab_agent
from negotiator.v2.intelligence.interpreter import GroundedInterpreter, InterpreterConfig
from negotiator.v2.orchestration.budgets import DecisionModelLedger

from .evaluate_interpretation import evaluate
from .evaluate_stabilization import FIXTURE
from .run_lab_local import DATASET, PROJECT

CONFIG = ChatCompletionConfig(
    base_url="https://api.openai.com/v1",
    provider_id="openai",
    model_id="gpt-4.1-mini-2025-04-14",
    request_model_id="gpt-4.1-mini-2025-04-14",
    structured_output=True,
)
MAX_CALLS, PER_CALL_TOKENS = 32, 98304
INPUT_RATE, OUTPUT_RATE = Decimal("0.40"), Decimal("1.60")
CALL_USD = (
    (PER_CALL_TOKENS - CONFIG.max_output_tokens) * INPUT_RATE + CONFIG.max_output_tokens * OUTPUT_RATE
) / 1000000


def plan(lab_url=None):
    source = sorted((PROJECT / "src/negotiator").rglob("*.py"))
    source += sorted((PROJECT / "src/negotiator/v2/intelligence/prompts").glob("*.txt"))
    source += sorted(Path(__file__).parent.glob("*.py")) + [DATASET, FIXTURE]
    return {
        "authorized": False,
        "token_accounting_confirmed": False,
        "environment": "simulator",
        "online_sessions": 0,
        "remote_writes": 2 if lab_url else 0,
        "lab_url": lab_url,
        "case": "case:P10",
        "model_config": asdict(CONFIG),
        "strategy": "bounded-proposal-v1",
        "schedule": "14 development interpretations; one fixed baseline; one adaptive offline negotiation",
        "local_simulator_sessions": 2,
        "max_decisions": 9,
        "max_calls": MAX_CALLS,
        "max_total_reserved_tokens": MAX_CALLS * PER_CALL_TOKENS,
        "per_call_total_token_limit": PER_CALL_TOKENS,
        "max_output_tokens": CONFIG.max_output_tokens,
        "max_usd": "2.00",
        "conservative_reserved_usd": str(MAX_CALLS * CALL_USD),
        "input_usd_per_million": str(INPUT_RATE),
        "output_usd_per_million": str(OUTPUT_RATE),
        "token_accounting": "UTF-8 byte upper bound plus schema and 256 framing tokens; confirm this convention",
        "retries": 0,
        "automatic_reruns": 0,
        "stop_on_transport_failure": True,
        "source_sha256": semantic_hash(
            {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
        ),
        "held_out_calls": 0,
        "semantic_labels": "unchanged provisional development expectations; human review pending",
    }


class OfflineAllowance:
    """Durably reserve each call before dispatch; no refund or retries."""

    def __init__(self, output, *, max_calls=MAX_CALLS, max_usd=Decimal("2.00")):
        self.path = output / "inference-ledger.json"
        self.max_calls, self.max_usd = max_calls, max_usd
        self.calls, self.reserved, self.stopped = [], Decimal(0), False

    def stop_model_calls(self, reason):
        # Synchronous: cancellation cleanup may otherwise run after the next consumer.
        self.stopped = True
        self.persist()

    async def __call__(self, request, budget):
        if self.stopped or len(self.calls) >= self.max_calls or budget.max_tokens > PER_CALL_TOKENS:
            raise ValueError("inference allowance exhausted or stopped")
        if self.reserved + CALL_USD > self.max_usd:
            raise ValueError("inference dollar ceiling exhausted")
        self.reserved += CALL_USD
        row = {
            "call_id": str(request.call_id),
            "task": request.task,
            "status": "reserved",
            "reserved_tokens": budget.max_tokens,
            "reserved_usd": str(CALL_USD),
        }
        self.calls.append(row)
        self.persist()
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                result = await ChatCompletionsTransport(
                    config=CONFIG, api_key=os.environ["LLM_API_KEY"], client=client
                )(request, budget)
            row.update(
                status=result.kind, usage=result.usage.model_dump(mode="json") if result.kind == "success" else None
            )
            if result.kind != "success":
                self.stopped = True
            elif result.usage.input_tokens is not None and result.usage.output_tokens is not None:
                cost = (result.usage.input_tokens * INPUT_RATE + result.usage.output_tokens * OUTPUT_RATE) / 1000000
                row["estimated_usd"] = str(cost)
                if cost > CALL_USD:
                    self.stopped = True
            return result
        except BaseException:
            self.stopped = True
            row["status"] = "interrupted-or-failed"
            raise
        finally:
            row["latency_s"] = time.monotonic() - started
            self.persist()

    def persist(self):
        _atomic_file(
            self.path,
            json.dumps({"reserved_usd": str(self.reserved), "stopped": self.stopped, "calls": self.calls}, indent=2),
        )


async def interpretations(output, allowance):
    fixture, dataset = json.loads(FIXTURE.read_text()), json.loads(DATASET.read_text())
    predictions = []
    clock = WallClock()
    for example in fixture["examples"]:
        if allowance.stopped:
            raise ValueError("hosted transport stopped; no further calls")
        body = example["label"]["text"]
        inputs = recorded_p10({**dataset, "supplier_messages": [body]}, message=body, now=clock.utcnow())
        assembler, _ = bounded_services(inputs, clock)
        snapshot = assembler.assemble(inputs)
        ledger = DecisionModelLedger(budget=inputs.budget, clock=clock, token_limit=PER_CALL_TOKENS)
        config = InterpreterConfig(
            provider_id=CONFIG.provider_id,
            protocol_id=CONFIG.protocol_id,
            model_id=CONFIG.model_id,
            prompt_version="grounded-supplier-v3",
            task_schema_version="assessment-citation-ids-v1",
            max_tokens=PER_CALL_TOKENS,
            time_limit_s=Decimal("8"),
            approved_message_hashes=(snapshot.conversation.messages[0].content_hash,),
            max_input_chars=64000,
        )
        assessment = await GroundedInterpreter(
            model=AsyncModelGateway(transport=allowance, ledger=ledger), clock=clock, config=config
        ).interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
        predictions.append({"id": example["label"]["id"], "assessment": assessment.model_dump(mode="json")})
        _atomic_file(output / "predictions.json", json.dumps(predictions, indent=2))
    labels = {**fixture, "examples": [e["label"] for e in fixture["examples"]]}
    report = evaluate(labels, predictions)
    _atomic_file(output / "interpretation-report.json", json.dumps(report, indent=2))
    if report["semantic_correct"] < 12:
        raise ValueError("development usability gate failed; no adaptive run")


def execute(output, authorization, lab_url=None):
    expected = plan(lab_url)
    approved = json.loads(authorization.read_text())
    if approved != {**expected, "authorized": True, "token_accounting_confirmed": True}:
        raise ValueError("explicit approval must exactly match this source/model/call/token/dollar plan")
    load_env()
    if lab_url:
        from .run_hosted_sandbox import verify_lab_access

        verify_lab_access(lab_url)
    if not os.environ.get("LLM_API_KEY"):
        raise ValueError("LLM_API_KEY missing")
    from .run_hosted_sandbox import verify_model_access

    verify_model_access()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    # This authorization is single-use across output directories and process restarts.
    marker = authorization.with_name(authorization.name + ".consumed")
    with os.fdopen(os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        stream.write(semantic_hash(approved))
        stream.flush()
        os.fsync(stream.fileno())
    _atomic_file(output / "approved-plan.json", json.dumps(approved, indent=2))
    allowance = OfflineAllowance(output)
    dataset = json.loads(DATASET.read_text())
    provenance, patch = capture_provenance(PROJECT, data_dir=PROJECT / "tests/fixtures/v2", allow_dirty=True)
    runs = {}
    for arm in ("minimum", "adaptive"):
        config = {
            "dataset_path": str(DATASET),
            "trace_root": str(output / "traces"),
            "arm": arm,
            "closing_authority": True,
            "model_config_json": json.dumps(asdict(CONFIG)) if arm == "adaptive" else None,
        }
        run = plan_run(
            name=f"V2 hosted-inference OFFLINE {arm}",
            author="authorized-offline-validation",
            hypothesis="Citation-ID interpretation and model-generated offers adapt through official Sim and Lab.",
            agent="negotiator.v2.factory:local_lab_agent",
            config=config,
            cases=["case:P10"],
            repetitions=1,
            max_sessions=1,
            environment="simulator",
            arena_url="http://localhost/simulations/" + semantic_hash((output.name, arm)),
            provenance=provenance,
        )

        runs[arm] = run
        save_snapshot(run, output / "runs", patch=patch)
    try:
        asyncio.run(interpretations(output, allowance))
        if allowance.stopped:
            raise ValueError("hosted transport stopped")
    except BaseException:
        # Interpretation failure is part of this tracked experiment, even when no
        # simulator negotiation starts. Preserve and publish both original plans.
        for run in runs.values():
            run.status = "failed"
            attempt = run.attempts[0]
            attempt.status, attempt.error = "failed", "development interpretation gate failed; no simulator session"
            attempt.result = {"development_evidence_json": json.dumps({
                "inference_ledger": json.loads(allowance.path.read_text()) if allowance.path.exists() else None,
                "interpretation_report": json.loads((output / "interpretation-report.json").read_text())
                if (output / "interpretation-report.json").exists() else None,
                "predictions": json.loads((output / "predictions.json").read_text())
                if (output / "predictions.json").exists() else None})}
            run.revision += 1
            save_snapshot(run, output / "runs")
            if lab_url:
                from .run_hosted_sandbox import publish_verified

                publish_verified(run, lab_url, output)
        raise
    for arm, run in runs.items():
        def create_agent(arm=arm):
            agent = local_lab_agent(
                dataset_path=DATASET,
                trace_root=output / "traces",
                arm=arm,
                transport=allowance if arm == "adaptive" else None,
                closing_authority=True,
                model_config=CONFIG if arm == "adaptive" else None,
            )
            agent.requires_complete_history = True
            agent.validation_evidence = {
                "interpretation_report_json": (output / "interpretation-report.json").read_text(),
                "predictions_json": (output / "predictions.json").read_text(),
                "approved_plan_json": (output / "approved-plan.json").read_text(),
                "development_inference_ledger_json": allowance.path.read_text(),
            }
            return agent

        final = run_experiment(
            run, output / "runs", InProcessSimulatorClient(dataset["case"]), create_agent, patch=patch
        )
        if lab_url:
            from .run_hosted_sandbox import publish_verified

            publish_verified(final, lab_url, output)
        if final.status != "completed" or allowance.stopped:
            raise ValueError("tracked offline run failed or transport stopped; no rerun")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--lab-url", help="explicitly include publication of two completed runs in the allowance")
    args = parser.parse_args()
    if args.authorization is None:
        args.out.mkdir(parents=True, exist_ok=True)
        _atomic_file(args.out / "authorization-template.json", json.dumps(plan(args.lab_url), indent=2))
        print("Prepared offline-only allowance; hosted calls=0; online sessions=0")
    else:
        execute(args.out, args.authorization, args.lab_url)


if __name__ == "__main__":
    main()
