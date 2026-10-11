# First three implementation prompts

These are historical T1.1a–c assignments, now implemented with completion evidence in D.
The current queue follows the [approved capability addendum](implementation-order-addendum-2026-10-10.md).
The T2.1 resolver, T2.3 resolved-cost projection and T4.1 official arithmetic oracle are
verified locally, alongside direct T4.1 package evaluation. Explicit source-cost estimate
construction now feeds direct comparison; selection and independent validation remain next. A/B components progress
together as their exact consumed contracts become available. The complete offline loop remains
required for M1 completion.

## Prompt 1 — T1.1a: strict domain values and canonical serialization

```text
Implement T1.1a only in tacto-negotiator, starting from development revision
4c905b10be1f576de9b68be9c120cf6796ae4561; preserve existing working changes.
Read docs/v2/C-interfaces.md sections1–2 and8.1, docs/v2/task-specs.md:T1.1a,
and tests/v2/contracts/test_foundation.py before coding.
Create src/negotiator/v2/__init__.py (empty), core/__init__.py, models.py,
errors.py and serialization.py. Use existing Pydantic and standard Python.
Implement FrozenModel, PriceBasis, Price, Money, IndexClause, TermBinding,
Package, SourceRef, MessageSpan, SnapshotRef, Issue and IssueCode exactly as
specified. Strict frozen fields, immutable nested tuples, no extras, no booleans
as integers/prices, finite amounts, positive Price/price_unit, real dates/months,
unique package fields. JSON Decimal storage uses strings. Do not snap/round
invalid values. Implement canonical_json and semantic_hash with sorted UTF-8
JSON/SHA256, NaN rejected. No provider, Arena, SQLite, legacy or strategy imports.
Run:
.venv/bin/python -m pytest -q tests/v2/contracts/test_foundation.py --v2-require core.models --v2-require core.serialization -k 'price or basis or term_bindings or canonical'
.venv/bin/python -m pytest -q tests/v2/contracts/test_boundaries.py
.venv/bin/ruff check tests/v2 src/negotiator/v2
Required owned tests must pass; later absent modules may remain UNIMPLEMENTED.
Do not weaken tests or implement services, assessment or future algorithms.
Do not modify V1, dependencies/defaults, read .env or make hosted/model calls.
Update the T1.1a completion evidence/status in D/main tracker. Report exact
owned-file/test results and remaining unimplemented scope; don't claim M1 done.
```

## Prompt 2 — T1.1b: grounded assessment models and exact Protocols

```text
Implement T1.1b only after T1.1a. Read C-interfaces.md sections2–3 and8.2/8.4/8.7,
task-specs.md:T1.1b and tests/v2/support.py:PORT_SIGNATURES.
Extend only core/models.py and create core/ports.py. Implement GroundedObservation,
ReportedConstraint, PreferenceHypothesis including direction, AssessmentUncertainty,
ClarificationQuestion, EstimatedEffect, SupplierAssessment and AssessmentDraft.
Keep observations, supplier-reported constraints, hypotheses and uncertainties
separate. Active observations/reported constraints/inferred preferences require
valid-shaped refs; constraints remain supplier_reported; approval/conditional/
contradictory gaps stay explicit. Exact quote offsets are Unicode and nonnegative.
No model output can carry binding action/pricing authority. Preserve revision/parent
fields. Define all C Protocol signatures, including clock and injected arithmetic/
canonical-claim oracles, with exact parameters, return annotations and sync/async
forms. Forward annotations for later models are allowed; empty service classes
claiming implementation are not. Core imports only stdlib/Pydantic/core.
Run:
.venv/bin/python -m pytest -q tests/v2/contracts/test_foundation.py --v2-require core.ports -k exact_port_signatures
.venv/bin/python -m pytest -q tests/v2/contracts/test_guardrails.py --v2-require core.models -k assessment_draft
.venv/bin/python -m pytest -q tests/v2/contracts/test_boundaries.py
.venv/bin/ruff check tests/v2 src/negotiator/v2
Do not implement interpreter/provider calls, strategy, pricing, historical learning
or constraint enforcement from supplier prose. Do not change V1/dependencies/tests
or consume quotas. Update T1.1b with precise evidence and incomplete scope.
```

## Prompt 3 — T1.1c: immutable DecisionRecord and effective config

```text
Implement T1.1c only after T1.1a/b. Read C-interfaces.md sections8.3/8.5/8.7/8.8,
task-specs.md:T1.1c, decision-record.json and the P10 config block in tests/fixtures/v2.
Extend core/models.py/serialization.py; create config.py. Implement DecisionStage,
DecisionRecord, EffectiveConfig and resolve_config with the exact documented fields,
literal versions, strict parsing and canonical config hash. Record has ten ordered
stages, immutable revision/parent/artifact refs, selected→evaluation and executed→
validated-operation links. Completed stages need artifacts; failed/skipped stages
need reason codes. Diagnostic strings for negative structural tests are
orphan_selection, stage_order and stage_issue_required. Schema-only refs don't
need to be stored yet; actual artifact/semantic closure validation is T1.4.
resolve_config must reject extras/unknown registered IDs and never consult ambient
legacy or LLM environment variables. Core/config imports only their allowed graph.
Run:
.venv/bin/python -m pytest -q tests/v2/contracts/test_guardrails.py --v2-require core.models --v2-require config -k 'record_schema or record_invariants or effective_config'
.venv/bin/python -m pytest -q tests/v2/contracts/test_foundation.py --v2-require core.serialization -k canonical
.venv/bin/python -m pytest -q tests/v2/contracts/test_boundaries.py
.venv/bin/ruff check tests/v2 src/negotiator/v2
Do not implement store/coordinator, replay codec, transport, default agent switches,
LLM behavior/portfolios or UI. Do not modify V1/dependencies/assertions/goldens or
make service calls. Update T1.1c evidence and status, list what is still missing.
M1 is complete only after later typed-codec/full-offline-loop/persistence tasks pass.
```
