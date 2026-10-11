"""Controlled recorded P10 decisions. Hosted calls require explicit experiment authorization."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

import httpx
from dotenv import load_dotenv

from negotiator.v2.adapters.chat_completions import ChatCompletionConfig, ChatCompletionsTransport
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.factory import bounded_services as services
from negotiator.v2.factory import run_recorded_decision

DATASET = Path(__file__).with_name("p10-offline-input.json")
PER_CALL_TOKENS = 16384
DECISION_TOKENS = 32768


class Clock:
    def utcnow(self):
        return datetime.now(UTC)

    def monotonic(self):
        return time.monotonic()




class LocalResponses:
    """Explicit fake HTTP envelope rehearsal, never used as a hosted result."""

    def __init__(self, body):
        self.body, self.calls = body, []

    async def __call__(self, wire):
        payload = json.loads(wire.content)
        self.calls.append(payload)
        projection = json.loads(payload["messages"][1]["content"])
        if projection["kind"] == "interpret":
            msg = projection["conversation"]["messages"][0]
            span = dict(
                session_id=msg["session_id"],
                thread_id=msg["thread_id"],
                message_id=msg["message_id"],
                start=0,
                end=len(msg["body"]),
                quote=msg["body"],
            )
            response = dict(
                observations=[
                    dict(
                        observation_id="observation:local",
                        kind="ambiguity",
                        dimension=None,
                        summary=msg["body"],
                        citations=[span],
                    )
                ],
                reported_constraints=[],
                hypotheses=[],
                uncertainties=[],
                questions=[],
                unknowns=[],
            )
            if "prefer" in msg["body"]:
                response["hypotheses"] = [
                    dict(
                        hypothesis_id="hypothesis:local",
                        dimension="lead_time_days",
                        relation="prefers",
                        direction="unknown",
                        summary=msg["body"],
                        supporting_refs=[span],
                        contradicting_refs=[],
                        confidence="low",
                        status="active",
                    )
                ]
        else:
            # Fixed reviewed rehearsal IDs, read from the real projection. No fake economics.
            offers = [o for o in projection["options"] if o["summary"].startswith("Offer:")]
            chosen = (
                next(o for o in offers if "lead_time_days=42" in o["summary"])
                if "prefer" in self.body
                else next(o for o in offers if "unit_price=27.6" in o["summary"])
            )
            response = dict(
                selected_id=chosen["candidate_id"], supporting_quote=self.body if "prefer" in self.body else ""
            )
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 400},
            },
        )


def authorization_template(dataset):
    return dict(
        authorized=False,
        provider_id="",
        model_id="",
        base_url="",
        protocol_id="chat-completions-json-v1",
        token_parameter="max_completion_tokens",
        token_accounting="utf8-byte-upper-bound-v1",
        token_accounting_confirmed=False,
        framing_token_reserve=256,
        dataset_hash=semantic_hash(dataset),
        max_calls=4,
        max_total_tokens=65536,
        max_output_tokens_per_call=2048,
        permitted_data="Only the reviewed V2 message/assessment/action projections of this exact dataset.",
    )


def check_authorization(auth, dataset, config):
    if (
        auth.get("authorized") is not True
        or auth.get("token_accounting_confirmed") is not True
        or auth.get("token_accounting") != "utf8-byte-upper-bound-v1"
        or auth.get("dataset_hash") != semantic_hash(dataset)
        or any(
            auth.get(key) != getattr(config, key)
            for key in (
                "provider_id",
                "model_id",
                "base_url",
                "protocol_id",
                "token_parameter",
                "framing_token_reserve",
            )
        )
        or auth.get("max_output_tokens_per_call") != config.max_output_tokens
        or type(auth.get("max_calls")) is not int
        or auth["max_calls"] < 4
        or type(auth.get("max_total_tokens")) is not int
        or auth["max_total_tokens"] < 65536
    ):
        raise ValueError("exact provider/model/dataset and absolute call/token authorization required")


async def run(output, *, hosted=False, authorization=None):
    dataset = json.loads(DATASET.read_text())
    output.mkdir(parents=True, exist_ok=True)
    # Always complete local rehearsal before creating any real network-capable transport.
    if hosted:
        await run(output / "local-preflight")
        if authorization is None:
            raise ValueError("hosted mode requires an authorization file")
        auth = json.loads(authorization.read_text())
        config = ChatCompletionConfig(
            base_url=os.environ.get("LLM_BASE_URL", ""),
            provider_id=auth.get("provider_id", ""),
            model_id=os.environ.get("LLM_MODEL", ""),
            token_parameter=auth.get("token_parameter", ""),
            framing_token_reserve=auth.get("framing_token_reserve", 0),
        ).checked()
        check_authorization(auth, dataset, config)
        key = os.environ.get("LLM_API_KEY", "")
        if not key:
            raise ValueError("LLM_API_KEY is missing")
    else:
        config = ChatCompletionConfig(
            base_url="http://127.0.0.1", provider_id="local-rehearsal", model_id="recorded-fake"
        )
        key = "local-rehearsal-key"
        (output / "authorization-template.json").write_text(
            json.dumps(authorization_template(dataset), indent=2) + "\n"
        )
    if hosted:
        # A run artifact, not negotiation persistence: never silently reuse an online
        # output directory after an uncertain or completed inference experiment.
        with (output / "hosted-started.json").open("x") as marker:
            json.dump({"dataset_hash": semantic_hash(dataset), "reserved_calls": 4, "reserved_tokens": 65536}, marker)
    rows, charged, calls = [], 0, 0
    universe = None
    for index, body in enumerate(dataset["supplier_messages"]):
        # Absolute experiment allowance is charged conservatively before each decision.
        if hosted and (calls + 2 > auth["max_calls"] or charged + DECISION_TOKENS > auth["max_total_tokens"]):
            rows.append(dict(message_index=index, status="not_run", reason="absolute_inference_allowance_exhausted"))
            break
        clock = Clock()
        inputs = recorded_p10(dataset, message=body, now=clock.utcnow())
        assembler, baseline = services(inputs, clock)
        baseline_trace = await run_recorded_decision(inputs, assembler=assembler, coordinator=baseline)
        local = LocalResponses(body)
        async with httpx.AsyncClient(
            transport=None if hosted else httpx.MockTransport(local), follow_redirects=False, trust_env=False
        ) as client:
            transport = ChatCompletionsTransport(config=config, api_key=key, client=client)
            assembler, coordinator = services(inputs, clock, transport, config)
            trace = await run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator)
        if trace.validation is None or trace.validation.kind != "valid":
            raise ValueError("offline decision failed independent validation")
        if not hosted and (
            trace.assessment.status != "ok" or trace.decision.fallback_code is not None or len(local.calls) != 2
        ):
            raise ValueError("local provider-envelope rehearsal failed")
        if baseline_trace.evaluations != trace.evaluations:
            raise ValueError("baseline/model economic batches differ")
        current = semantic_hash(
            [(i.candidate.contents, tuple(r.nominal_cost for r in i.economic)) for i in trace.evaluations.items]
        )
        if universe is not None and current != universe:
            raise ValueError("supplier-language variation changed alternatives or official economics")
        universe = current
        for label, recorded in (("baseline", baseline_trace), ("model", trace)):
            recorded.verify()
            (output / f"message-{index}-{label}.json").write_text(recorded.model_dump_json(indent=2) + "\n")
        model_calls = sum(c.charged_tokens > 0 for c in trace.model_calls)
        calls += model_calls
        # Keep reservation charges across decisions even if providers refund actual usage.
        charged += sum(max(PER_CALL_TOKENS, c.charged_tokens) for c in trace.model_calls if c.charged_tokens > 0)
        rows.append(
            dict(
                message_index=index,
                assessment_status=trace.assessment.status,
                baseline_candidate=baseline_trace.decision.candidate_id,
                selected_candidate=trace.decision.candidate_id,
                selected_kind=trace.rendered.kind,
                fallback_code=trace.decision.fallback_code,
                official_costs=[str(r.nominal_cost.amount) for i in trace.evaluations.items for r in i.economic],
                validation=trace.validation.kind,
                calls=model_calls,
                input_tokens=[c.usage.input_tokens for c in trace.model_calls],
                output_tokens=[c.usage.output_tokens for c in trace.model_calls],
                latency_s=[float(c.elapsed_s) for c in trace.model_calls],
                trace_hash=trace.trace_hash,
            )
        )
    prompt_hashes = {
        name: hashlib.sha256(files("negotiator.v2.intelligence").joinpath("prompts", name).read_bytes()).hexdigest()
        for name in ("grounded-supplier-v1.txt", "grounded-selection-v1.txt")
    }
    report = dict(
        provider_id=config.provider_id,
        model_id=config.model_id,
        protocol_id=config.protocol_id,
        token_parameter=config.token_parameter,
        input_accounting="utf8-byte-upper-bound-v1",
        framing_token_reserve=config.framing_token_reserve,
        prompt_hashes=prompt_hashes,
        evidence="hosted model" if hosted else "local fake HTTP rehearsal; no hosted inference",
        dataset_hash=semantic_hash(dataset),
        candidate_universe_hash=universe,
        calls=calls,
        experiment_reserved_tokens=charged,
        results=rows,
    )
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hosted", action="store_true")
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    load_dotenv(Path.cwd() / ".env", override=False)
    asyncio.run(run(args.output, hosted=args.hosted, authorization=args.authorization))
