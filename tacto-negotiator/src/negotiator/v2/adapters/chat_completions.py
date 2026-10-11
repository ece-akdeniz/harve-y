"""Explicit async chat-completions transport. No retries, credentials lookup or import calls."""

import hashlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from importlib.resources import files
from urllib.parse import urlsplit

import httpx

from ..core import models as m
from ..core.citation_ids import wire_schema
from ..core.serialization import semantic_hash

PROMPTS = {
    "propose": ("bounded-proposal-v1", "proposal-response-v1", "bounded-proposal-v1.txt", m.ProposalResponse),
    "propose-v2": ("bounded-proposal-v2", "proposal-response-v2", "bounded-proposal-v2.txt", m.ProposalResponseV2),
    "propose-v3": ("bounded-proposal-v3", "proposal-response-v3", "bounded-proposal-v3.txt", m.ProposalResponseV3),
    "interpret-v3": ("grounded-supplier-v3", "assessment-citation-ids-v1",
                     "grounded-supplier-v3.txt", m.AssessmentDraft),
    "interpret": ("grounded-supplier-v1", "assessment-draft-v1", "grounded-supplier-v1.txt", m.AssessmentDraft),
    "interpret-v2": ("grounded-supplier-v2", "assessment-draft-v1", "grounded-supplier-v2.txt", m.AssessmentDraft),
    "select-v2": ("grounded-selection-v2", "selector-response-v1", "grounded-selection-v2.txt", m.SelectorResponse),
    "select": ("grounded-selection-v1", "selector-response-v1", "grounded-selection-v1.txt", m.SelectorResponse),
}


@dataclass(frozen=True)
class ChatCompletionConfig:
    base_url: str
    provider_id: str
    model_id: str
    protocol_id: str = "chat-completions-json-v1"
    token_parameter: str = "max_completion_tokens"
    max_output_tokens: int = 2048
    framing_token_reserve: int = 256
    max_response_bytes: int = 131072
    request_model_id: str | None = None
    structured_output: bool = False

    def checked(self):
        url = urlsplit(self.base_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.scheme != "https"
            and not (url.scheme == "http" and local)
            or not self.provider_id
            or not self.model_id
            or self.protocol_id != "chat-completions-json-v1"
            or self.token_parameter not in {"max_tokens", "max_completion_tokens"}
            or type(self.max_output_tokens) is not int
            or self.max_output_tokens <= 0
            or type(self.framing_token_reserve) is not int
            or self.framing_token_reserve < 256
            or self.max_response_bytes <= 0
        ):
            raise ValueError("explicit compatible chat-completions configuration required")
        if self.request_model_id is not None and self.request_model_id != self.model_id and not (
            self.provider_id == "openai"
            and self.base_url.rstrip("/") == "https://api.openai.com/v1"
            and self.request_model_id == "gpt-4.1-mini"
            and self.model_id == "gpt-4.1-mini-2025-04-14"
        ):
            raise ValueError("unapproved request/response model mapping")
        return self


def failure(request, kind, detail, elapsed):
    cls, code = {
        "invalid": (m.ModelInvalid, "model_invalid"),
        "refused": (m.ModelRefused, "model_invalid"),
        "timeout": (m.ModelTimeout, "model_timeout"),
        "capacity_unavailable": (m.ModelCapacityUnavailable, "unsupported_capability"),
        "transport_failure": (m.ModelTransportFailure, "recovery_required"),
    }[kind]
    return cls(
        kind=kind,
        call_id=request.call_id,
        model_id=request.model_id,
        elapsed_s=elapsed,
        issues=(m.Issue(code=code, severity="error", component="adapters.chat_completions", refs=(), detail=detail),),
    )


def messages_for(request, config):
    suffix = ("-v3" if request.prompt_version.endswith("-v3")
              else "-v2" if request.prompt_version.endswith("-v2") else "")
    entry = PROMPTS.get(request.task + suffix)
    if (
        entry is None
        or request.provider_id != config.provider_id
        or request.model_id != config.model_id
        or request.protocol_id != config.protocol_id
        or request.prompt_version != entry[0]
        or request.task_schema_version != entry[1]
        or request.output_schema_hash != semantic_hash(
            wire_schema() if request.task == "interpret" and suffix == "-v3" else entry[3].model_json_schema())
    ):
        raise ValueError("unsupported purpose/configuration/schema identity")
    prompt = files("negotiator.v2.intelligence").joinpath("prompts", entry[2]).read_text()
    schema = json.dumps(wire_schema() if request.task == "interpret" and request.prompt_version.endswith("-v3")
                        else entry[3].model_json_schema(),
                        separators=(",", ":"), ensure_ascii=False)
    contract_instruction = (
        "\nReturn only JSON matching the supplied response_format schema."
        if config.structured_output else "\nReturn only JSON matching this exact schema:\n" + schema
    )
    return [
        {"role": "system", "content": prompt + contract_instruction},
        {"role": "user", "content": request.input.model_dump_json()},
    ]


def response_format(request, config):
    if not config.structured_output:
        return {"type": "json_object"}
    if request.task == "propose":
        contract = (m.ProposalResponseV3 if request.prompt_version == "bounded-proposal-v3" else
                    m.ProposalResponseV2 if request.prompt_version == "bounded-proposal-v2" else m.ProposalResponse)
    else:
        contract = m.AssessmentDraft if request.task == "interpret" else m.SelectorResponse
    schema = (wire_schema() if request.task == "interpret" and getattr(request, "prompt_version", "").endswith("-v3")
              else contract.model_json_schema(mode="serialization"))

    def strict(node):
        if isinstance(node, dict):
            # Provider annotations consume the same bounded input reservation as constraints.
            # Omit prose metadata; preserve property maps whose fields have these names.
            for annotation in ("title", "description"):
                if isinstance(node.get(annotation), str):
                    node.pop(annotation)
            node.pop("default", None)
            if "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            # JSON Schema const is equivalent to a one-value enum.
            if "const" in node:
                node["enum"] = [node.pop("const")]
            for value in node.values():
                strict(value)
        elif isinstance(node, list):
            for value in node:
                strict(value)

    strict(schema)
    return {"type": "json_schema", "json_schema": {
        "name": request.task + "_response", "strict": True, "schema": schema,
    }}


def input_token_upper_bound(messages, framing_reserve, structured_format=None):
    """Conservative text-byte bound, conditional on confirmed byte-level tokenizer/framing.

    This is not a tokenizer estimate or a universal bound for arbitrary compatible providers.
    The experiment authorization must confirm this convention before any hosted call.
    """
    format_bytes = (len(json.dumps(structured_format, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
                    if structured_format is not None else 0)
    return sum(len(m["content"].encode("utf-8")) for m in messages) + framing_reserve + format_bytes


class ChatCompletionsTransport:
    def __init__(self, *, config: ChatCompletionConfig, api_key: str, client: httpx.AsyncClient):
        self.config = config.checked()
        if not api_key or client.follow_redirects:
            raise ValueError("explicit credentials and nonredirecting async client required")
        self._api_key, self.client = api_key, client

    async def __call__(self, request: m.ModelRequest, budget: m.ModelBudget) -> m.ModelResult:
        started = time.monotonic()

        def elapsed():
            return Decimal(str(max(0, time.monotonic() - started)))

        try:
            messages = messages_for(request, self.config)
            output_format = response_format(request, self.config)
            bound = input_token_upper_bound(messages, self.config.framing_token_reserve,
                                            output_format if self.config.structured_output else None)
            output_limit = min(self.config.max_output_tokens, budget.max_tokens - bound)
            if output_limit <= 0:
                return failure(request, "capacity_unavailable", "input leaves no output token allowance", elapsed())
            body = {
                "model": self.config.request_model_id or self.config.model_id,
                "messages": messages,
                self.config.token_parameter: output_limit,
                "response_format": output_format,
                "stream": False,
            }
            # Stream the HTTP bytes only to bound envelope size; no model streaming/retries.
            async with self.client.stream(
                "POST",
                self.config.base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + self._api_key},
                json=body,
                timeout=float(budget.time_limit_s),
                follow_redirects=False,
            ) as response:
                if response.status_code == 429:
                    return failure(request, "capacity_unavailable", "provider capacity unavailable", elapsed())
                if response.status_code != 200:
                    return failure(
                        request, "transport_failure",
                        f"provider HTTP request rejected (status {response.status_code}); body withheld", elapsed()
                    )
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > self.config.max_response_bytes:
                        return failure(request, "invalid", "oversized provider envelope", elapsed())
            data = json.loads(raw)
            choices = data["choices"]
            if len(choices) != 1:
                return failure(request, "invalid", "one provider choice required", elapsed())
            choice = choices[0]
            message = choice["message"]
            if message.get("refusal") or choice.get("finish_reason") == "content_filter":
                return failure(request, "refused", "provider refused; content withheld", elapsed())
            if choice.get("finish_reason") != "stop" or message.get("tool_calls") or message.get("function_call"):
                return failure(request, "invalid", "incomplete or nontext provider output", elapsed())
            content = message["content"]
            if not isinstance(content, str):
                return failure(request, "invalid", "provider content must be text", elapsed())
            usage = data.get("usage") or {}
            result = m.ModelSuccess(
                kind="success",
                call_id=request.call_id,
                model_id=data["model"],
                elapsed_s=elapsed(),
                issues=(),
                raw_response_json=content,
                response_hash=hashlib.sha256(content.encode()).hexdigest(),
                usage=m.ModelUsage(
                    input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens")
                ),
            )
            if (
                result.model_id != request.model_id
                or result.usage.input_tokens is not None
                and result.usage.input_tokens > bound
                or result.usage.output_tokens is not None
                and result.usage.output_tokens > output_limit
            ):
                # Ledger retains actual successful usage and rejects total-reservation overruns.
                # A within-total provider violation is an invalid successful envelope, so
                # conservative unknown/full-reservation accounting remains in force.
                if (result.usage.input_tokens or 0) + (result.usage.output_tokens or 0) > budget.max_tokens:
                    return result
                return failure(request, "invalid", "provider identity/token-bound violation", elapsed())
            return result
        except httpx.TimeoutException as error:
            return failure(request, "timeout", f"provider HTTP timeout ({type(error).__name__})", elapsed())
        except httpx.HTTPError as error:
            return failure(request, "transport_failure",
                           f"provider transport failed ({type(error).__name__}); details withheld", elapsed())
        except (ValueError, KeyError, TypeError, AttributeError):
            return failure(request, "invalid", "malformed provider envelope/configuration", elapsed())
