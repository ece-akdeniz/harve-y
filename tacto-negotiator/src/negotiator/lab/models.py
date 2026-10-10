"""Bounded v1 experiment snapshots and conservative descriptive comparisons."""

import json
import math
import re
import statistics
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .reconcile import recovered_result

MAX_PAYLOAD = 2 * 1024 * 1024
MAX_ATTEMPTS = 200
SECRET_KEYS = re.compile(r"(^|_)(api_key|password|token|secret|authorization|credentials)(_|$)", re.I)
Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9_:.-]*$")]
Text = Annotated[str, Field(max_length=4096)]
Count = Annotated[int, Field(ge=0, le=1000000)]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or len(value) > 2048
    ):
        raise ValueError("invalid URL")
    return value.rstrip("/")


def check_json(value: Any, depth: int = 0) -> None:
    if depth > 12:
        raise ValueError("JSON nesting too deep")
    if isinstance(value, dict):
        if len(value) > 2000:
            raise ValueError("too many fields")
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 256 or SECRET_KEYS.search(key):
                raise ValueError("invalid or private field")
            check_json(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > 5000:
            raise ValueError("too many values")
        for child in value:
            check_json(child, depth + 1)
    elif isinstance(value, str):
        if len(value) > 65536:
            raise ValueError("text too long")
    elif value is None or isinstance(value, bool):
        pass
    elif isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("nonfinite number")
    else:
        raise ValueError("not JSON")


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class Provenance(StrictModel):
    commit: Annotated[str | None, Field(max_length=64)] = None
    dirty: bool | None = None
    patch_sha256: Annotated[str | None, Field(pattern=r"^[a-f0-9]{64}$")] = None
    lock_sha256: Annotated[str | None, Field(pattern=r"^[a-f0-9]{64}$")] = None
    data_sha256: Annotated[str | None, Field(pattern=r"^[a-f0-9]{64}$")] = None


class Quota(StrictModel):
    used: Count
    left: Count
    limit: Count
    checked_at: str

    @model_validator(mode="after")
    def valid(self):
        timestamp(self.checked_at)
        if self.used + self.left != self.limit:
            raise ValueError("inconsistent quota")
        return self


def timestamp(value: str) -> datetime:
    if len(value) > 50:
        raise ValueError("invalid timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


class Attempt(StrictModel):
    attempt_id: Identifier
    case_id: Identifier
    repeat: Annotated[int, Field(ge=1, le=MAX_ATTEMPTS)]
    status: Literal["pending", "running", "completed", "failed"]
    session_id: Identifier | None = None
    replay_url: Annotated[str | None, Field(max_length=2048)] = None
    score: Annotated[float | None, Field(ge=0, le=1)] = None
    rounds: Count | None = None
    elapsed_s: Annotated[float | None, Field(ge=0, le=604800)] = None
    timeouts: Count | None = None
    error: Annotated[str | None, Field(max_length=1024)] = None
    result: dict[str, Any] = Field(default_factory=dict)
    threads: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid(self):
        if self.replay_url is not None:
            safe_url(self.replay_url)
        if self.status != "completed" and self.score is not None:
            raise ValueError("only completed attempts can be scored")
        if self.status == "pending" and self.session_id is not None:
            raise ValueError("pending attempt has a session")
        check_json(self.result)
        check_json(self.threads)
        return self


class Run(StrictModel):
    schema_version: Literal[1]
    run_id: Identifier
    revision: Annotated[int, Field(ge=1, le=2147483647)]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    author: Annotated[str, Field(min_length=1, max_length=120)]
    hypothesis: Text
    agent: Annotated[str, Field(min_length=1, max_length=256)]
    config: dict[str, Any]
    source: Literal["tracked", "imported"]
    environment: Literal["simulator", "sandbox", "practice"]
    arena_url: Annotated[str, Field(max_length=2048)]
    baseline_id: Identifier | None = None
    started_at: str
    updated_at: str
    status: Literal["running", "completed", "failed", "interrupted"]
    cases: Annotated[list[Identifier], Field(min_length=1, max_length=MAX_ATTEMPTS)]
    repetitions: Annotated[int, Field(ge=1, le=MAX_ATTEMPTS)]
    provenance: Provenance | None
    quota: Quota | None
    attempts: Annotated[list[Attempt], Field(min_length=1, max_length=MAX_ATTEMPTS)]

    @model_validator(mode="after")
    def valid(self):
        # Literal alone permits bools for 1; require a real integer.
        if type(self.schema_version) is not int:
            raise ValueError("invalid schema version")
        self.arena_url = safe_url(self.arena_url)
        if timestamp(self.updated_at) < timestamp(self.started_at):
            raise ValueError("invalid timestamp order")
        if len(set(self.cases)) != len(self.cases) or len(self.cases) * self.repetitions > MAX_ATTEMPTS:
            raise ValueError("invalid case plan")
        planned = {(case, repeat) for case in self.cases for repeat in range(1, self.repetitions + 1)}
        actual = {(a.case_id, a.repeat) for a in self.attempts}
        if actual != planned or len(self.attempts) != len(planned):
            raise ValueError("attempt plan mismatch")
        if len({a.attempt_id for a in self.attempts}) != len(self.attempts):
            raise ValueError("duplicate attempt ID")
        if self.status == "completed" and any(a.status != "completed" for a in self.attempts):
            raise ValueError("completed run has unfinished attempts")
        if self.baseline_id == self.run_id:
            raise ValueError("self baseline")
        check_json(self.config)
        if len(json.dumps(self.model_dump(), allow_nan=False).encode()) > MAX_PAYLOAD:
            raise ValueError("snapshot too large")
        return self


MANIFEST_FIELDS = (
    "schema_version",
    "run_id",
    "name",
    "author",
    "hypothesis",
    "agent",
    "config",
    "source",
    "environment",
    "arena_url",
    "baseline_id",
    "started_at",
    "cases",
    "repetitions",
    "provenance",
)


def metrics(attempts: list[Attempt]) -> dict:
    scores = [a.score for a in attempts if a.status == "completed" and a.score is not None]
    complete = len(scores) == len(attempts) and bool(attempts)
    observed = statistics.mean(scores) if scores else None
    return {
        "planned": len(attempts),
        "completed": sum(a.status == "completed" for a in attempts),
        "failed": sum(a.status == "failed" for a in attempts),
        "pending": sum(a.status in {"pending", "running"} for a in attempts),
        "scored": len(scores),
        "recovered": sum(recovered_result(a.model_dump()) is not None for a in attempts),
        "mean_score": observed if complete else None,
        "observed_mean": observed,
        "min_score": min(scores) if scores else None,
        "deals": sum(a.status == "completed" and a.result.get("deal") is True for a in attempts),
        "elapsed_s": sum(a.elapsed_s or 0 for a in attempts),
        "timeouts": sum(a.timeouts or 0 for a in attempts),
    }


def summarize(run: Run) -> dict:
    fields = (
        "run_id",
        "name",
        "author",
        "hypothesis",
        "agent",
        "source",
        "environment",
        "arena_url",
        "status",
        "started_at",
        "updated_at",
        "baseline_id",
        "provenance",
        "revision",
    )
    body = run.model_dump()
    return {**{key: body[key] for key in fields}, "metrics": metrics(run.attempts)}


def compare(baseline: Run, candidate: Run) -> dict:
    warnings = []
    same_environment = baseline.environment == candidate.environment and baseline.arena_url == candidate.arena_url
    if not same_environment:
        warnings.append("Arena or environment differs; overall delta is unavailable.")
    if set(baseline.cases) != set(candidate.cases):
        warnings.append("Unmatched cases are visible; only common complete cases contribute to overall delta.")
    if baseline.repetitions != candidate.repetitions:
        warnings.append("Repetition counts differ.")
    for label, run in (("Baseline", baseline), ("Candidate", candidate)):
        if run.source == "imported":
            warnings.append(f"{label} is imported; code and configuration provenance is unknown.")
        if run.provenance is None or not run.provenance.data_sha256:
            warnings.append(f"{label} data fingerprint is unknown.")
        if run.provenance and run.provenance.dirty:
            warnings.append(f"{label} uses dirty code and cannot be reproduced from Git alone.")
    if (
        baseline.provenance
        and candidate.provenance
        and baseline.provenance.data_sha256
        and candidate.provenance.data_sha256
        and baseline.provenance.data_sha256 != candidate.provenance.data_sha256
    ):
        warnings.append("Data fingerprints differ.")
    rows, deltas = [], []
    for case in sorted(set(baseline.cases) | set(candidate.cases)):
        left = metrics([a for a in baseline.attempts if a.case_id == case])
        right = metrics([a for a in candidate.attempts if a.case_id == case])
        delta = (
            right["mean_score"] - left["mean_score"]
            if left["mean_score"] is not None and right["mean_score"] is not None
            else None
        )
        if delta is not None:
            deltas.append(delta)
        rows.append(
            {
                "case_id": case,
                "baseline_mean": left["mean_score"],
                "candidate_mean": right["mean_score"],
                "delta": delta,
                "baseline_scored": left["scored"],
                "candidate_scored": right["scored"],
                "baseline_planned": left["planned"],
                "candidate_planned": right["planned"],
                "baseline_failed": left["failed"],
                "candidate_failed": right["failed"],
            }
        )
    if any(r["delta"] is None for r in rows):
        warnings.append("Incomplete or missing cells have no delta; observed scores are partial.")
    return {
        "baseline": summarize(baseline),
        "candidate": summarize(candidate),
        "warnings": warnings,
        "mean_delta": statistics.mean(deltas) if deltas and same_environment else None,
        "cases": rows,
        "comparable": bool(deltas) and same_environment,
    }
