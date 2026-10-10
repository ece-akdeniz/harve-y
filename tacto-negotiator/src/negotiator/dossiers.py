"""Per-supplier dossiers from the data package (and the Sunday release).

A dossier is everything the data says about one supplier, with citable IDs kept:
master data, intel (credit index now vs. 12 m ago, equity, owner type), news (topic-tagged),
notes/letters/e-mails, scorecards, our payment lateness, negotiation history (asked vs. settled),
contracts and clauses, quotes, price conditions, should-cost for its parts.
Prototype: tools/build_dossiers.py.
"""

from dataclasses import dataclass, field


@dataclass
class Dossier:
    supplier_id: str
    name: str
    country: str
    category: str
    intel: dict = field(default_factory=dict)
    news: list[dict] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)  # {id, date, kind, subject, text}
    scorecard: dict = field(default_factory=dict)
    payment_lateness_days: float | None = None
    history: list[dict] = field(default_factory=list)
    should_cost: dict = field(default_factory=dict)  # part_id -> row
    traits: set[str] = field(default_factory=set)


def build(package) -> dict[str, Dossier]:
    """All detailed suppliers (`suppliers.detail = 'full'`), keyed by `sup:` id."""
    raise NotImplementedError


def for_case(dossiers: dict[str, Dossier], case: dict) -> dict[str, Dossier]:
    """Dossiers for the case's suppliers; hidden cases may add facts via `case['facts']`."""
    raise NotImplementedError
