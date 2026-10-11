# D01 repair trial — 11 October 2026

## Result

One fresh D01 sandbox session ran through the tracked hosted runner with the repaired source.
The Arena session completed in two rounds with **a deal, zero timeouts and score 0.0**. The
supplier accepted terms identical to its opening offer: EUR 52.90 per unit, 30-day payment,
12-month contract, effective 1 December 2026. The shared closing evaluator independently
accepted the supplier's standing sheet. This is an execution pass, not evidence of a commercial
improvement or strategy superiority.

The model did not negotiate a concession. It made one admitted `bounded-proposal-v3` call and
returned the supplier's terms unchanged. Its input assessment was
`deterministic-evidence-copy-v1`; no semantic interpretation call occurred. The supplier's
agreement is an observed outcome, while the score of zero indicates no Arena score benefit.

## Run identity and controls

- Lab run: `15500f1f-0048-437d-acad-cfbd79098c8d`.
- Arena session: `21fed09494f89548`; case `case:D01`, supplier `sup:DEMO-F1`.
- Model: `gpt-4.1-mini-2025-04-14`; one proposal call, 2.845 seconds, 3,501 input and 185 output
  tokens. Usage-rate estimate: USD 0.0016964; provider-reported cost was unavailable.
- Reserved: 98,304 tokens / USD 0.0417792 of the allowance (18 calls, 1,769,472 reserved tokens,
  USD 1 maximum). One Arena session and one Lab publication; zero retries or reruns.
- Source SHA-256 in the fresh single-use allowance: `300c68189a2c4cfda92eb8b856ed7c8338b02bae2f98ea9a2bf2ad6e792d1d24`.
- Lab record retrieval and normal listing both verified. Terminal evidence is complete and the
  submission journal has no unresolved move.
- Local artifacts: `/tmp/v2-d01-repair-execution-2026-10-11-01/`. The fresh allowance and its
  consumed marker are under `/tmp/v2-d01-repair-trial-2026-10-11-01/`.

## Review and metric correction

The decision trace verifies the proposal response, complete package, deterministic email and
independent action validation. The package matches the supplier's opening quote, so the proposal
cost equals the opening cost: EUR 448,810.67. The same-observation finite candidate minimum is
EUR 398,400.00; that comparison is not an attainable supplier offer or realized savings.

The immutable published run summary incorrectly reported `interpretation_admitted: true` and
`strategy: bounded-proposal-v2`. The trace proves the actual path: one `propose` call using
`bounded-proposal-v3`, and no interpreter call. Local code now derives interpretation admission
from an admitted interpretation model call and reports the v3/evidence-copy strategy identity.
Regression checks passed after this correction. The original remote run and publication were not
rewritten; this discrepancy remains attached to the original report for honest review.

Targeted post-run verification: 28 adaptive-proposal, Lab-integration and hosted-adapter checks
passed; scoped Ruff and `git diff --check` passed. No additional hosted call or session was made.
Do not infer general negotiation capability from one accepted unchanged opening quote. Any next
trial should first review this complete transcript and the metric discrepancy.
