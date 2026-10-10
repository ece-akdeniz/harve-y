# Measured demo for the team

These are hosted practice results, not a forecast of the final or jury prize.

## Lead with the decision

The agent negotiates the package, not just unit price. It calculates buyer cost in code,
uses verified supplier-specific facts, and keeps fixed terms private and unchanged.

## P04: buy the commitment the supplier values

The supplier dossier says discounts require a multi-year agreement. The baseline kept a
12-month agreement and scored 5.64. The candidate offered 24 months at the same annual
20,000 units, negotiated EUR 4.94 with 90-day payment, and scored 86.04. A fresh paired
confirmation reproduced both numbers. Complete cost fell from EUR 198,715.67 to 196,852.67.

Show [the measured replay](../experiments/replays/p04-package-evidence.html). The delivery
claim was verified, but package-only achieved the same score; do not attribute the gain to
that claim. The evidence supports the package trade as the useful change in this experiment.

## P11: price the penalty instead of demanding it for free

The supplier repeatedly charged for a high chargeback. The baseline obtained EUR 48.00
with EUR 500 chargeback and scored 31.44. The selected refinement started with a permitted
lower chargeback and later traded it to zero for a lower price. It closed at EUR 45.50,
300 ppm, zero chargeback, with payment still fixed at 60 days: score 70.99, repeated once.

The complete-cost evaluator explicitly charges EUR 2,146.50 for residual defects. It still
prefers the cheaper package: C = EUR 750,082.50 versus the baseline EUR 787,686. The actual
historical 2,376 ppm and electricity-index claims were verified. Historical defects and the
future 300 ppm commitment are different facts. The agent ignored supplier requests to
negotiate payment, because that field is fixed in this case.

Show [the measured replay](../experiments/replays/p11-chargeback-evidence.html), the supplier's
chargeback objection, our conditional package change, and the complete cost breakdown.

## What we can claim

These gains repeated, with valid deals, zero actual thread timeouts and no contradicted claims.
Exact repeats may be cached, so they demonstrate reproducibility rather than significance.
One frozen ten-case comparison is still required before claiming the combined policy improves
its mean without material regressions. Final wave/recovery and Sunday release readiness are
separate gates. The overall jury prize is not determined by these practice scores alone.
