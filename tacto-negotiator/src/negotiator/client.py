"""Async client for the arena API.

Contract (docs/00-challenge.md, kit brief/api.md):
- `X-API-Key` on every call; fresh `X-Move-Id` on every POST, reused on retry (idempotent).
- 180 s timeout on message POSTs (supplier think time up to ~1 min).
- Global limiter: ≤ 10 calls/s per key across all sessions (aim for ~8).
- During the Live Final the agent must never read spectator endpoints.
"""

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


class ForbiddenEndpoint(RuntimeError):
    pass


def assert_allowed(path: str) -> None:
    """Raise if `path` is a spectator endpoint the agent may not read."""
    clean = path.split("?", 1)[0].rstrip("/")
    if any(clean == p or clean.startswith(p + "/") for p in FORBIDDEN_PATHS):
        raise ForbiddenEndpoint(f"the agent may not read {clean}")


class AsyncArena:
    """httpx.AsyncClient wrapper. Methods mirror arena_kit.client.ArenaClient."""

    def __init__(self, base_url: str, api_key: str, calls_per_s: float = 8.0):
        raise NotImplementedError

    async def me(self) -> dict: ...
    async def cases(self, set_: str) -> list[dict]: ...
    async def open_session(self, case_id: str) -> dict: ...
    async def send(self, session_id: str, supplier_id: str, message: dict, move_id: str) -> dict: ...
    async def thread(self, session_id: str, supplier_id: str) -> dict: ...
    async def session(self, session_id: str) -> dict: ...
    async def attachment(self, session_id: str, attachment_id: str) -> bytes: ...
