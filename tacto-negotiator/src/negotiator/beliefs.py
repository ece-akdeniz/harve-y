"""What we believe about a supplier, updated from its replies.

Signals: which of our MESO sheets it answered and how its counter moved per field; status
(open/final_offer/agreed); claim results and its stated reasons; reply_delay_days; documents
(cost breakdown XLSX elements); traits from the dossier as priors.
"""

from dataclasses import dataclass, field


@dataclass
class Belief:
    field_weights: dict[str, float] = field(default_factory=dict)  # how much it values each field
    price_floor_est: float | None = None
    patience: float = 1.0  # drops with timeouts, pushes after final_offer, contradicted claims
    concession_rate: float | None = None
    notes: list[str] = field(default_factory=list)


def prior(traits: set[str]) -> Belief:
    raise NotImplementedError


def update(belief: Belief, our_sheets: list[dict], reply: dict) -> Belief:
    raise NotImplementedError
