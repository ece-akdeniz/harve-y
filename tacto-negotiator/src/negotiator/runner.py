"""Async orchestration: one task per thread, RFQ coordination, wave deadlines, resume.

- `play_case`: open (or resume on 409) → fetch documents → plan → spawn a task per thread.
  Each task answers its supplier within the move budget; only the coordinator accepts.
- Deadline watchdog: at max(90 s, slowest round + 15 s) before the cap → arena_kit closing_move.
- `run_waves`: poll `/v1/cases?set=final` every few seconds, start every new case of a running
  wave (≤ 10 open sessions), stop after wave 5 has closed. Never read spectator endpoints.
"""


async def play_case(arena, case: dict, ctx, deadline: float | None = None) -> dict:
    raise NotImplementedError


async def run_set(arena, set_: str, parallel: int = 10) -> list[dict]:
    """Practice/sandbox: play every hosted case of the set, ≤ parallel at once."""
    raise NotImplementedError


async def run_waves(arena, ctx, waves: int = 5, parallel: int = 10, poll_s: float = 3.0) -> None:
    raise NotImplementedError
