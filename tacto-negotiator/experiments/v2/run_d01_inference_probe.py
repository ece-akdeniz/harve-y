"""Prepare or execute one authorized D01-recorded, two-call inference-only probe."""

import argparse
import asyncio
import hashlib
import json
import multiprocessing
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from arena_kit.cli import load_env

from negotiator.v2.adapters.lab import WallClock
from negotiator.v2.adapters.offline import OfflineRecordedInputs
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.factory import bounded_services, run_recorded_decision
from negotiator.v2.orchestration.budgets import DecisionModelLedger

from .run_adaptive_milestone import (
    CALL_USD,
    CONFIG,
    INPUT_RATE,
    OUTPUT_RATE,
    PER_CALL_TOKENS,
    OfflineAllowance,
)

PROJECT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = Path("/tmp/v2-d01-hosted-execution-2026-10-11")
TRACE_PATH = ARTIFACT_ROOT / "traces/04a6789d-593b-4722-a7f4-5f289da374f1/de6f67ea54658727/decision-000.json"
OBSERVATION_PATH = ARTIFACT_ROOT / "traces/04a6789d-593b-4722-a7f4-5f289da374f1/de6f67ea54658727/observation-000.json"
OUTPUT_ROOT = Path("/tmp/v2-d01-inference-probe-2026-10-11")
STAGE_LIMITS = {"interpret": 9.0, "propose": 5.0}
TOTAL_MODEL_SECONDS = Decimal("15")
COMPUTE_SECONDS = Decimal("35")
RESERVE_SECONDS = Decimal("5")
CLEANUP_SECONDS = 2.0
MAX_CALLS = 2
MAX_TOKENS = MAX_CALLS * PER_CALL_TOKENS
MAX_USD = CALL_USD * MAX_CALLS


def load_d01_inputs():
    trace_data = json.loads(TRACE_PATH.read_bytes())
    recorded = trace_data["recorded_input_bytes"]
    inputs = OfflineRecordedInputs.model_validate_json(recorded)
    observation = json.loads(OBSERVATION_PATH.read_bytes())
    messages = inputs.server.threads[0].conversation.messages
    if (
        inputs.server.session_id != observation["session_id"]
        or not messages
        or messages[0].message_id != observation["messages"][0]["message_id"]
        or semantic_hash(messages[0]) != semantic_hash(observation["messages"][0])
    ):
        raise ValueError("D01 observation does not match the recorded decision input")
    return trace_data, recorded, inputs, observation


def source_fingerprint():
    paths = sorted((PROJECT / "src/negotiator").rglob("*.py"))
    paths += sorted((PROJECT / "src/negotiator/v2/intelligence/prompts").glob("*.txt"))
    paths += [Path(__file__), Path(__file__).with_name("run_adaptive_milestone.py"), TRACE_PATH, OBSERVATION_PATH]
    return semantic_hash({str(path.relative_to(PROJECT)) if path.is_relative_to(PROJECT) else str(path):
                          hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})


def plan():
    _, recorded, inputs, observation = load_d01_inputs()
    return {
        "authorized": False,
        "token_accounting_confirmed": False,
        "experiment": "d01-recorded-inference-only-v2",
        "provider_id": CONFIG.provider_id,
        "model_id": CONFIG.model_id,
        "request_model_id": CONFIG.request_model_id,
        "base_url": CONFIG.base_url,
        "protocol_id": CONFIG.protocol_id,
        "token_parameter": CONFIG.token_parameter,
        "structured_output": CONFIG.structured_output,
        "framing_token_reserve": CONFIG.framing_token_reserve,
        "max_response_bytes": CONFIG.max_response_bytes,
        "prompts": {
            "interpret": "grounded-supplier-v3/assessment-citation-ids-v1",
            "propose": "bounded-proposal-v2/proposal-response-v2",
        },
        "source_sha256": source_fingerprint(),
        "recorded_input_sha256": hashlib.sha256(recorded.encode()).hexdigest(),
        "observation_sha256": hashlib.sha256(OBSERVATION_PATH.read_bytes()).hexdigest(),
        "case_id": inputs.case.case_id,
        "session_id_from_recorded_observation": observation["session_id"],
        "supplier_id": inputs.target_supplier_id,
        "supplier_message_id": observation["messages"][0]["message_id"],
        "max_calls": MAX_CALLS,
        "call_order": ["interpret", "propose"],
        "proposal_uses_pipeline_assessment_including_documented_fallback": True,
        "retries": 0,
        "automatic_reruns": 0,
        "per_call_reserved_tokens": PER_CALL_TOKENS,
        "max_total_reserved_tokens": MAX_TOKENS,
        "max_output_tokens_per_call": CONFIG.max_output_tokens,
        "token_accounting": (
            "Transport checks UTF-8 input byte bound plus schema/framing; reserve full per-call cap "
            "when provider usage is unknown"
        ),
        "max_usd": str(MAX_USD),
        "conservative_reserved_usd_per_call": str(CALL_USD),
        "input_usd_per_million": str(INPUT_RATE),
        "output_usd_per_million": str(OUTPUT_RATE),
        "stage_time_limits_s": STAGE_LIMITS,
        "total_model_time_limit_s": str(TOTAL_MODEL_SECONDS),
        "compute_limit_s": str(COMPUTE_SECONDS),
        "cleanup_limit_s": CLEANUP_SECONDS,
        "validation_clock": "recorded-as-of plus monotonic elapsed; offline replay only",
        "fallback_reserve_s": str(RESERVE_SECONDS),
        "submission_reserve_s": str(RESERVE_SECONDS),
        "arena_sessions": 0,
        "arena_message_posts": 0,
        "lab_publication_writes": 0,
        "output_path": str(OUTPUT_ROOT),
    }


def _atomic_private_json(path, value):
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)



class ProbeAllowance:
    """Enforce exactly one ordered interpretation/proposal transport invocation."""

    def __init__(self, output):
        self.inner = OfflineAllowance(output, max_calls=MAX_CALLS, max_usd=MAX_USD)
        self.expected = ("interpret", "propose")
        self.calls = []
        self.output = output
        self.raw_path = output / "raw-model-outputs.jsonl"

    def stop_model_calls(self, reason):
        self.inner.stop_model_calls(reason)

    @property
    def stopped(self):
        return self.inner.stopped

    async def __call__(self, request, budget):
        index = len(self.calls)
        if index >= len(self.expected) or request.task != self.expected[index]:
            raise ValueError("probe permits only the ordered interpretation and proposal calls")
        self.calls.append(request.task)
        started = time.monotonic()
        result = await self.inner(request, budget)
        elapsed = time.monotonic() - started
        row = {
            "task": request.task,
            "call_id": str(request.call_id),
            "result_kind": result.kind,
            "issues": [issue.model_dump(mode="json") for issue in result.issues],
            "latency_s": elapsed,
            "usage": result.usage.model_dump(mode="json") if result.kind == "success" else None,
            "usage_unknown": result.kind != "success" or result.usage.input_tokens is None
                              or result.usage.output_tokens is None,
            "raw_response_json": result.raw_response_json if result.kind == "success" else None,
            "response_sha256": result.response_hash if result.kind == "success" else None,
            "provider_reported_cost": (
                str(result.usage.reported_cost)
                if result.kind == "success" and result.usage.reported_cost is not None else None
            ),
            "estimated_cost_from_reported_tokens": (
                str((Decimal(result.usage.input_tokens) * INPUT_RATE
                     + Decimal(result.usage.output_tokens) * OUTPUT_RATE) / Decimal(1_000_000))
                if result.kind == "success" and result.usage.input_tokens is not None
                and result.usage.output_tokens is not None else None
            ),
        }
        with self.raw_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return result


class RecordedProbeClock(WallClock):
    """Replay recorded time without changing any observed server-clock evidence."""

    def __init__(self, as_of):
        self.as_of = as_of
        self.started = time.monotonic()

    def utcnow(self):
        return self.as_of + timedelta(seconds=time.monotonic() - self.started)


async def _execute_probe(inputs, output, allowance):
    clock = RecordedProbeClock(inputs.as_of)
    now = clock.utcnow()
    budget = inputs.budget.model_copy(update={
        "deadline_at": now + timedelta(seconds=float(COMPUTE_SECONDS)),
        "compute_limit_s": COMPUTE_SECONDS,
        "model_call_limit": MAX_CALLS,
        "model_time_limit_s": TOTAL_MODEL_SECONDS,
        "fallback_reserve_s": RESERVE_SECONDS,
        "submission_reserve_s": RESERVE_SECONDS,
    })
    inputs = inputs.model_copy(update={"budget": budget})
    assembler, coordinator = bounded_services(
        inputs,
        clock,
        allowance,
        CONFIG,
        prompt_revision="v3",
        arm="adaptive",
    )
    coordinator.model_token_limit = MAX_TOKENS
    original_limits = DecisionModelLedger.stage_caps_s
    DecisionModelLedger.stage_caps_s = {**original_limits, **STAGE_LIMITS}
    started = time.monotonic()
    try:
        trace = await run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator)
    finally:
        DecisionModelLedger.stage_caps_s = original_limits
    elapsed = time.monotonic() - started
    trace.verify()
    return trace, elapsed


def execute(authorization_path):
    approved = json.loads(authorization_path.read_text())
    expected = {**plan(), "authorized": True, "token_accounting_confirmed": True}
    if approved != expected:
        raise ValueError("authorization must exactly match the frozen probe plan")
    load_env()
    if not os.environ.get("LLM_API_KEY"):
        raise ValueError("LLM_API_KEY is missing")
    marker = authorization_path.with_name(authorization_path.name + ".consumed")
    with marker.open("x", encoding="utf-8") as stream:
        stream.write(semantic_hash(approved) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    run_output = OUTPUT_ROOT / "execution"
    run_output.mkdir(parents=True, mode=0o700, exist_ok=False)
    _atomic_private_json(run_output / "started.json", {
        "authorization_sha256": semantic_hash(approved), "started_at": datetime.now(UTC).isoformat(),
        "max_calls": MAX_CALLS, "max_total_reserved_tokens": MAX_TOKENS,
    })
    _atomic_private_json(run_output / "approved-plan.json", approved)
    _, _, inputs, _ = load_d01_inputs()
    return _supervise_probe(inputs, run_output, compute_seconds=float(COMPUTE_SECONDS),
                            cleanup_seconds=CLEANUP_SECONDS)


async def _persist_probe(inputs, run_output, allowance):
    # Publish evidence before asyncio.run enters cancellation/executor teardown.
    trace, wall_seconds = await _execute_probe(inputs, run_output, allowance)
    _atomic_private_json(run_output / "decision-trace.json", json.loads(trace.model_dump_json()))
    return _report_probe(trace, wall_seconds, run_output, allowance)


def _report_probe(trace, wall_seconds, run_output, allowance):
    elapsed_by_call = {str(call.request.call_id): float(call.elapsed_s) for call in trace.model_calls}
    calls = [{
        "task": call.request.task,
        "result_kind": call.result_kind,
        "latency_s": str(call.elapsed_s),
        "reserved_tokens": call.charged_tokens,
        "usage": call.usage.model_dump(mode="json"),
        "usage_unknown": call.usage.input_tokens is None or call.usage.output_tokens is None,
        "consumer_admitted": call.consumer_admitted,
        "fallback_used": call.fallback_used,
        "cause": call.cause,
    } for call in trace.model_calls]
    raw_rows = _read_jsonl(allowance.raw_path)
    model_candidates = [candidate for generation in trace.generations for candidate in generation.candidates
                        if candidate.candidate_builder_id == "bounded-proposal-v2"]
    selected_builder = next((candidate.candidate_builder_id for generation in trace.generations
                             for candidate in generation.candidates
                             if trace.decision and candidate.candidate_id == trace.decision.candidate_id), None)
    report = {
        "status": "complete" if len(allowance.calls) == MAX_CALLS else "partial_model_execution",
        "reserved_transport_invocations": len(allowance.inner.calls),
        "transport_call_order": allowance.calls,
        "individual_calls": calls,
        "total_inference_latency_s": str(sum(
            float(row["latency_s"]) if "latency_s" in row else elapsed_by_call[row["call_id"]]
            for row in allowance.inner.calls
        )),
        "transport_cleanup_pending": any("latency_s" not in row for row in allowance.inner.calls),
        "whole_decision_wall_s": wall_seconds,
        "validation_clock": "recorded-as-of plus monotonic elapsed; offline replay only",
        "cleanup_status": "pending",
        "reserved_tokens": sum(row["reserved_tokens"] for row in allowance.inner.calls),
        "reserved_usd": str(allowance.inner.reserved),
        "estimated_cost_from_reported_tokens_usd": str(sum(
            (Decimal(row["estimated_cost_from_reported_tokens"]) for row in raw_rows
             if row["estimated_cost_from_reported_tokens"] is not None), Decimal(0)))
            if raw_rows and all(row["estimated_cost_from_reported_tokens"] is not None for row in raw_rows) else None,
        "provider_reported_cost_usd": [row["provider_reported_cost"] for row in raw_rows],
        "reported_usage_unknown": any(
            row["usage_unknown"] for row in raw_rows
        ) or any(
            row.usage.input_tokens is None or row.usage.output_tokens is None
            for row in trace.model_calls
        ),
        "interpretation": trace.assessment.model_dump(mode="json") if trace.assessment else None,
        "proposal_response_admitted": any(call.request.task == "propose" and call.consumer_admitted
                                          for call in trace.model_calls),
        "model_proposal_candidate_ids": [candidate.candidate_id for candidate in model_candidates],
        "selected_candidate_builder_id": selected_builder,
        "validated_action_is_model_generated": bool(
            trace.validation and trace.validation.kind == "valid" and trace.decision
            and selected_builder == "bounded-proposal-v2"
        ),
        "validation_kind": trace.validation.kind if trace.validation else None,
        "validation_issues": [issue.model_dump(mode="json") for issue in trace.validation.report.issues]
                            if trace.validation and trace.validation.kind == "invalid" else [],
        "selected_candidate_id": str(trace.decision.candidate_id) if trace.decision else None,
        "commercial_reasoning_review": "human review required; see raw-model-outputs.jsonl and decision-trace.json",
        "arena_sessions": 0,
        "arena_message_posts": 0,
        "lab_publication_writes": 0,
    }
    _atomic_private_json(run_output / "result.json", report)
    return report


def _probe_worker(raw_inputs, run_output):
    global STAGE_LIMITS, TOTAL_MODEL_SECONDS, COMPUTE_SECONDS
    try:
        # Spawn does not inherit parent module overrides. Use the exact persisted plan.
        approved = json.loads((run_output / "approved-plan.json").read_text())
        STAGE_LIMITS = approved["stage_time_limits_s"]
        TOTAL_MODEL_SECONDS = Decimal(approved["total_model_time_limit_s"])
        COMPUTE_SECONDS = Decimal(approved["compute_limit_s"])
        inputs = OfflineRecordedInputs.model_validate_json(raw_inputs)
        allowance = ProbeAllowance(run_output)
        asyncio.run(_persist_probe(inputs, run_output, allowance))
    except BaseException as error:
        # Never serialize exception text: provider errors may contain credentials.
        if not (run_output / "result.json").exists():
            _atomic_private_json(run_output / "result.json", {
                "status": "runner_failed", "error_type": type(error).__name__,
                "arena_sessions": 0, "arena_message_posts": 0, "lab_publication_writes": 0,
            })


def _supervise_probe(inputs, run_output, *, worker=_probe_worker,
                     compute_seconds=float(COMPUTE_SECONDS), cleanup_seconds=CLEANUP_SECONDS):
    """One worker, no retries; retain artifacts even if asyncio teardown stalls."""
    process = multiprocessing.get_context("spawn").Process(
        target=worker, args=(inputs.model_dump_json(), run_output), daemon=True,
    )
    started = time.monotonic()
    deadline = started + compute_seconds
    report_path = run_output / "result.json"
    process.start()
    forced = False
    try:
        while process.is_alive():
            now = time.monotonic()
            if report_path.exists():
                deadline = min(deadline, now + cleanup_seconds)
            if now >= deadline:
                forced = True
                break
            process.join(timeout=min(0.05, deadline - now))
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=cleanup_seconds)
            if process.is_alive():
                process.kill()
                process.join(timeout=cleanup_seconds)
    ledger_path = run_output / "inference-ledger.json"
    if forced and ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        ledger["stopped"] = True
        _atomic_private_json(ledger_path, ledger)
    if report_path.exists():
        report = json.loads(report_path.read_text())
    else:
        report = {
            "status": "runner_timeout" if forced else "runner_failed",
            "arena_sessions": 0, "arena_message_posts": 0, "lab_publication_writes": 0,
        }
    report["cleanup_status"] = "terminated" if forced else "complete"
    report["runner_wall_s"] = time.monotonic() - started
    _atomic_private_json(report_path, report)
    return report


def _read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main():
    global OUTPUT_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    # The exact output destination is part of the approved plan and checked by execute().
    OUTPUT_ROOT = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.authorization is None:
        authorization = plan()
        _atomic_private_json(args.output / "authorization-template.json", authorization)
        print(json.dumps({"status": "prepared", "authorization": str(args.output / "authorization-template.json"),
                          "source_sha256": authorization["source_sha256"],
                          "max_calls": MAX_CALLS, "max_total_reserved_tokens": MAX_TOKENS,
                          "max_usd": str(MAX_USD), "network_calls": 0}, indent=2))
        return
    print(json.dumps(execute(args.authorization), indent=2))


if __name__ == "__main__":
    main()
