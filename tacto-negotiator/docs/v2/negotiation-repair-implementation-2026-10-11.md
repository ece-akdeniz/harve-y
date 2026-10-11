# V2 negotiation repair implementation

Date: 11 October 2026 (Europe/Zurich). Local implementation and focused verification only.

## Changes

- The adaptive proposal contract is now `bounded-proposal-v3` / `proposal-response-v3`. It asks for
  complete bindings, scoped citations and rationale; code derives buyer request/offer direction and
  records supplier value as unknown. The historical v2 response validator remains available.
- The adaptive path preserves trusted supplier spans deterministically and names the assessment
  `deterministic-evidence-copy-v1`. It makes one proposer call and does not claim semantic
  interpretation. Full semantic extraction remains available in the separate grounded arm.
- A rejected proposal can trigger one registered clarification, never the fixed-minimum package.
  Acknowledged question history is checked across the thread. When a clarification has already been
  sent, or the authoritative thread is final, the Lab routes to the shared independently validated
  closing evaluator before further model work.
- Offer and clarification emails use deterministic templates. Offer values are rendered from the
  selected package, and final validation reconstructs the expected body and package before issuing
  the payload certificate. A focused tampering regression covers offer text.
- Clarification dispatch now passes the Lab's final validation seam without assuming a term sheet.

## Verification

Focused command:

```text
PYTHONPATH=. .venv/bin/pytest -q \
  tests/v2/integration/test_adaptive_proposal.py \
  tests/v2/integration/test_commercial_effects.py \
  tests/v2/integration/test_grounded_model.py \
  tests/v2/integration/test_hosted_sandbox.py \
  tests/v2/integration/test_lab_integration.py \
  tests/v2/integration/test_offline_decision.py \
  tests/v2/contracts/test_strategy_boundary.py
```

Result: **133 passed**. Ruff passed on `src/negotiator/v2` and the touched focused tests;
`git diff --check` passed. The environment has no `uv` executable, so the checked-in `.venv`
pytest/Ruff entry points were used.

No hosted session was opened. The existing local integration replay and refusal/invalid-proposal
regressions were used; a fresh saved comparison against the historical D01 artifacts was not run.
No claim is made about strategy superiority or realized D01 economics. The next hosted capability
trial still needs applicable explicit session authority and a fresh source-bound allowance.

## Source identity and workspace state

- Base revision: `a88bf86820214be9fdf4e0d4e679675d946e0607`.
- New prompt/schema identity: `bounded-proposal-v3` / `proposal-response-v3`.
- Renderer/validator identity: `email-templates-v2`.
- SHA-256 over the ordered per-file SHA-256 output for the implementation and focused regression
  files listed below: `65ae1bcacc927341132208910d4b2aacc3163d171cccc4ece7361753c210fb11`.

Fingerprint inputs: `src/negotiator/v2/strategy/proposal.py`,
`src/negotiator/v2/intelligence/testing.py`, `src/negotiator/v2/factory.py`,
`src/negotiator/v2/adapters/lab.py`, `src/negotiator/v2/adapters/chat_completions.py`,
`src/negotiator/v2/core/models.py`, `src/negotiator/v2/execution/render.py`,
`src/negotiator/v2/execution/validation.py`,
`src/negotiator/v2/intelligence/prompts/bounded-proposal-v3.txt`, and the four focused test files
listed in the verification command.

The workspace already contained extensive unrelated modifications and untracked implementation
artifacts before this repair began. They were preserved. This report fingerprints only the repair
implementation and its focused regression files, not the complete workspace tree.
