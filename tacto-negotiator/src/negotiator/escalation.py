"""Pricing-committee escalation (opt-in: policy.committee_escalation_types).

A supplier whose own note says price changes above a threshold need its pricing committee, and
which holds its standing price while our ask is further away than that threshold, is asked to put
the proposal to that committee. Public facts only: the threshold from the supplier's dossier note,
the gap from its own standing sheet and our offered price.
"""


def request(threshold: float, standing_price: float, our_price: float) -> str | None:
    """The escalation sentence, or None when the gap is within the supplier's own band."""
    if not threshold or not standing_price or our_price >= standing_price:
        return None
    gap = (standing_price - our_price) / standing_price * 100
    if gap <= threshold:
        return None
    return (f"Our proposal is {gap:.1f} % below your current offer. As you explained, price changes above "
            f"{threshold:g} % need the approval of your pricing committee; please put this proposal to the "
            "committee so that your answer reflects its decision rather than your own band.")
