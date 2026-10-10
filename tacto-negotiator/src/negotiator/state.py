"""Per-case and per-thread state, persisted to disk so a restarted runner can resume."""

from dataclasses import dataclass, field


@dataclass
class ThreadState:
    supplier_id: str
    events: list[dict] = field(default_factory=list)  # all e-mails, oldest first
    last_reply_at: float = 0.0  # monotonic time of the supplier's last move
    rounds_used: int = 0
    timeouts: int = 0
    closed: str | None = None
    pending_move_id: str | None = None  # persisted before POST, reused on retry


@dataclass
class CaseState:
    case: dict
    session_id: str
    threads: dict[str, ThreadState] = field(default_factory=dict)
    used_claim_ids: set[str] = field(default_factory=set)
    deadline: float | None = None  # wall-clock wave cap
    ended: bool = False
    result: dict | None = None

    def save(self, path) -> None:
        raise NotImplementedError

    @classmethod
    def load(cls, path) -> "CaseState":
        raise NotImplementedError
