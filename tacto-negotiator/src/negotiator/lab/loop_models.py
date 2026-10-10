"""Strict public loop records, independent of execution and transport."""

from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import check_json

ID = str


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def safe_json(self):
        check_json(self.model_dump())
        for name, value in self.model_dump().items():
            if name.endswith("_id") and value is not None:
                import re

                if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,240}", value):
                    raise ValueError("invalid identity")
        return self


class Policy(Record):
    version: str = "v1"
    min_gain: float = Field(default=1.0, ge=1)
    max_case_regression: float = Field(default=2.0, ge=0, le=2)
    min_win_fraction: float = Field(default=2 / 3, ge=2 / 3, le=1)


class Suite(Record):
    suite_id: ID
    cases: list[str] = Field(min_length=1, max_length=100)
    repetitions: int = Field(ge=3, le=100)
    runner: Literal["serial", "async"]
    arena_url: str
    environment: Literal["sandbox", "practice", "simulator"]
    data: dict[str, Any]
    max_sessions: int = Field(ge=1, le=20000)
    policy: Policy

    @model_validator(mode="after")
    def coherent(self):
        url = urlsplit(self.arena_url)
        if (
            url.scheme not in ("https", "http")
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("invalid arena origin")
        if url.path not in ("", "/") or len(set(self.cases)) != len(self.cases):
            raise ValueError("invalid cases or arena origin")
        if self.max_sessions != 2 * len(self.cases) * self.repetitions:
            raise ValueError("session ceiling differs from exact plan")
        # HTTP origin aliases must share quota reservations and session ownership.
        host = url.hostname.lower()
        if ":" in host:
            host = "[" + host + "]"
        port = url.port
        suffix = "" if port is None or port == {"http": 80, "https": 443}[url.scheme] else f":{port}"
        self.arena_url = f"{url.scheme}://{host}{suffix}"
        return self


class Family(Record):
    family_id: ID
    max_sessions: int = Field(ge=1, le=100000)
    practice_allowance: int = Field(default=0, ge=0)
    reserve: int = Field(default=0, ge=0)


class Quota(Record):
    remaining: int = Field(ge=0)
    observed_at: float = Field(ge=0)
    open_sessions: int = Field(default=0, ge=0)


class Campaign(Record):
    campaign_id: ID
    family_id: ID
    suite_id: ID
    baseline_id: ID
    candidate_id: ID
    generation: int = Field(ge=1)
    seed: int
    author: str = Field(min_length=1, max_length=200)
    hypothesis: str = Field(min_length=1, max_length=4000)
    quota: Quota | None = None


class Recommendation(Record):
    suite_id: ID
    checkpoint_id: ID
    author: str = Field(min_length=1, max_length=200)
    request_id: ID | None = None
    generation: int | None = Field(default=None, ge=1)


class Start(Record):
    attempt_id: ID
    worker_id: ID
    key_id: ID
    quota: Quota | None = None


class Outcome(Record):
    attempt_id: ID
    checkpoint_id: ID
    session_id: ID | None
    status: Literal["completed", "failed", "ambiguous", "recovered"]
    score: float | None = Field(default=None, ge=0, le=1)
    timeouts: int | None = Field(default=None, ge=0)
    result: dict[str, Any] = Field(default_factory=dict)
    threads: dict[str, Any] = Field(default_factory=dict)
    elapsed_s: float | None = Field(default=None, ge=0)


class Complete(Record):
    campaign_id: ID


class Finding(Record):
    finding_id: ID
    campaign_id: ID
    candidate_id: ID
    author: str = Field(min_length=1, max_length=200)
    observation: str = Field(min_length=1, max_length=4000)
    hypothesis: str = Field(min_length=1, max_length=4000)
    change: str = Field(min_length=1, max_length=4000)
    next_test: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    disposition: Literal["proposed", "accepted", "rejected", "tested"]
    evidence: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class Reconciliation(Record):
    attempt_id: ID
    checkpoint_id: ID
    session_id: ID
    result: dict[str, Any]
    threads: dict[str, Any] = Field(default_factory=dict)
    score: float | None = Field(default=None, ge=0, le=1)
    timeouts: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def ended(self):
        if self.result.get("ended") is not True:
            raise ValueError("owned ended session evidence required")
        return self


class NotCreated(Record):
    worker_id: ID
    attempt_id: ID
    checkpoint_id: ID
    reason: Literal["worker_preflight", "arena_rejected"]
    http_status: int | None = None

    @model_validator(mode="after")
    def definite(self):
        if self.reason == "worker_preflight" and self.http_status is not None:
            raise ValueError("preflight cannot include HTTP status")
        if self.reason == "arena_rejected" and self.http_status not in (400, 401, 403, 404, 422, 429):
            raise ValueError("definite session create rejection required")
        return self
