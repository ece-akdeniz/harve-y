"""Async client for the arena API.

Contract (docs/00-challenge.md, kit brief/api.md):
- `X-API-Key` on every call; one `X-Move-Id` per logical POST, reused on retry (idempotent).
  The caller owns the move id so it can be journalled before the request leaves.
- 180 s timeout on message POSTs (supplier think time up to ~1 min, plus queueing).
- One key-wide limiter: ≤ 10 calls/s per key across all sessions (we pace at ~8, no bursts).
- During the Live Final the agent must never read spectator endpoints.
"""

import asyncio
import os
import time

import httpx
from arena_kit.client import MAX_RETRY_AFTER_S, MOVE_ID_HEADER, REMAINING_HEADER, ArenaError

FORBIDDEN_PATHS = (
    "/v1/events",
    "/v1/events/stream",
    "/screen",
    "/v1/screen",
    "/leaderboard",
    "/v1/leaderboard",
    "/results",
    "/v1/results",
)
RETRY_STATUS = {429, 500, 502, 503, 504}
TIMEOUT_S = 180.0


class ForbiddenEndpoint(RuntimeError):
    pass


class UncertainOutcome(Exception):
    """A POST whose fate is unknown (transport error after retries): reconcile before moving on."""

    def __init__(self, move_id: str, cause: Exception):
        super().__init__(f"uncertain outcome for move {move_id}: {cause!r}")
        self.move_id, self.cause = move_id, cause


def assert_allowed(path: str) -> None:
    """Raise if `path` is a spectator endpoint the agent may not read."""
    clean = "/" + path.split("?", 1)[0].strip("/")
    for p in (clean, "/v1" + clean):  # AsyncArena paths are relative to /v1
        if any(p == f or p.startswith(f + "/") for f in FORBIDDEN_PATHS):
            raise ForbiddenEndpoint(f"the agent may not read {clean}")


class RateLimiter:
    """Evenly spaced slots: at most `rate` calls per second, never a burst. Shared key-wide."""

    def __init__(self, rate: float = 8.0, clock=time.monotonic):
        self.interval, self.clock, self._next = 1.0 / rate, clock, 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        # Reserve the next slot from the actual wake time. A delayed wake followed by an
        # absolute pre-reserved slot can otherwise create a burst for sequential callers.
        async with self._lock:
            while (delay := self._next - self.clock()) > 0:
                await asyncio.sleep(delay)
            self._next = self.clock() + self.interval


class AsyncArena:
    """httpx.AsyncClient wrapper. Methods mirror arena_kit.client.ArenaClient; POSTs take a move id."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        calls_per_s: float = 8.0,
        *,
        retries: int = 3,
        transport=None,
        timeout: float = TIMEOUT_S,
        limiter: RateLimiter | None = None,
    ):
        base_url = (base_url or os.environ.get("ARENA_URL", "")).rstrip("/")
        if not base_url:
            raise ValueError("set ARENA_URL or pass base_url")
        key = api_key or os.environ.get("ARENA_API_KEY")
        headers = {"X-API-Key": key} if key else {}
        self.retries = retries
        self.limiter = limiter or RateLimiter(calls_per_s)
        self.practice_remaining: int | None = None
        self.http = httpx.AsyncClient(
            base_url=f"{base_url}/v1", headers=headers, timeout=timeout, transport=transport
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _call(self, method, path, body=None, params=None, raw=False, move_id=None):
        assert_allowed(path)
        headers = {MOVE_ID_HEADER: move_id} if move_id else {}
        r = None
        for attempt in range(self.retries + 1):
            await self.limiter.wait()
            try:
                r = await self.http.request(method, path, json=body, params=params, headers=headers)
            except httpx.TransportError as e:
                if attempt == self.retries:
                    if method == "POST":
                        raise UncertainOutcome(move_id or "", e) from e
                    raise
                await asyncio.sleep(0.5 * 2**attempt)
                continue
            wait = r.headers.get("Retry-After", "")
            short = wait.isdigit() and int(wait) <= MAX_RETRY_AFTER_S
            if r.status_code not in RETRY_STATUS or attempt == self.retries or (r.status_code == 429 and not short):
                break
            await asyncio.sleep(float(wait) if wait.isdigit() else 0.5 * 2**attempt)
        if (left := r.headers.get(REMAINING_HEADER, "")).isdigit():
            self.practice_remaining = int(left)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except (ValueError, AttributeError):
                detail = r.text
            raise ArenaError(r.status_code, detail)
        return r.content if raw else r.json()

    async def me(self) -> dict:
        return await self._call("GET", "/me")

    async def cases(self, set_: str) -> list[dict]:
        return await self._call("GET", "/cases", params={"set": set_})

    async def open_session(self, case_id: str, move_id: str) -> dict:
        return await self._call("POST", "/sessions", {"case_id": case_id}, move_id=move_id)

    async def send(self, session_id: str, supplier_id: str, message: dict, move_id: str) -> dict:
        path = f"/sessions/{session_id}/threads/{supplier_id}/messages"
        return await self._call("POST", path, {"message": message}, move_id=move_id)

    async def thread(self, session_id: str, supplier_id: str) -> dict:
        return await self._call("GET", f"/sessions/{session_id}/threads/{supplier_id}")

    async def session(self, session_id: str) -> dict:
        return await self._call("GET", f"/sessions/{session_id}")

    async def attachment(self, session_id: str, attachment_id: str) -> bytes:
        return await self._call("GET", f"/sessions/{session_id}/attachments/{attachment_id}", raw=True)
