# Standalone inference probe finalization repair

Date: 11 October 2026 (Europe/Zurich). Local implementation and scripted verification only.
No provider call, Arena request, Lab write, push or promotion was authorized or performed.
The consumed authorization and original partial execution artifacts were retained unchanged.

## Cause and changes

The standalone probe previously wrote its trace and report only after `asyncio.run()` returned.
A local reproduction finished the decision but stalled during executor shutdown. This sandbox
rejects socket-pair sends, which can prevent worker completion from waking the asyncio loop.
HTTPX DNS resolution uses that executor. The original interrupted process has no captured stack;
this is a reproduced failure mechanism, not proof of its exact original transport exception.

The probe now starts exactly one spawned worker under a synchronous process supervisor. The
worker persists its verified trace and result inside the coroutine before loop teardown. The
supervisor enforces the original 35-second whole-worker allowance and allows at most two seconds
of cleanup after a report becomes available, clipped by the original deadline. A stuck child is
terminated, then killed if termination does not finish within the cleanup allowance. Process
termination waits are bounded. Existing reservations are retained and a forcibly stopped ledger
is marked stopped. No child retry or replacement occurs. Timeout and runner exceptions produce
local result reports; exception text is withheld. Private atomic writes use unique temporary
files so leftovers from an interrupted writer cannot block timeout-report persistence. Provider-side work and charges may continue
following local process termination.

Recorded validation now uses recorded `as_of` plus real monotonic elapsed time. Server observations,
thread/wave deadline evidence and source references are retained unchanged. The computation budget
is based on the same replay clock; the supervisor independently enforces real elapsed time. This
is explicitly labeled offline replay in the plan and report. It does not establish that a past
session is currently actionable, and it does not change online validation.

The report uses `ModelCallTrace.usage` instead of dictionary subscripting. Unknown token cost is
reported as null rather than zero. The probe wrapper forwards synchronous stop notifications to
its durable allowance. Transport failures retain HTTP status or exception class without error
text, URLs, credentials or response bodies; those safe issues are also saved in raw call rows.

The plan now includes cleanup and replay-clock policy, and source changes alter its fingerprint.
Old authorization remains consumed and cannot authorize a new execution. A future probe still
requires a fresh exact allowance and a separately prepared unused execution destination.

## Local verification

- Initial related suites: 97 passed (probe, hosted readiness, grounded model, adaptive proposal).
- After diagnostic/report changes: probe plus hosted readiness, 36 passed.
- After the additional durable-stop regression: probe suite, 4 passed.
- Scoped Ruff: all checks passed. `git diff --check`: clean.

Regressions demonstrate persisted fallback trace and valid offline action despite intentionally
stalled executor cleanup; bounded whole-worker timeout reporting; report generation with known
usage; unchanged recorded server clocks; synchronous durable allowance revocation; and safe
ConnectError, ReadTimeout and HTTP-status diagnostics without retries or secret disclosure.
A separate scripted replay of the preserved D01 input returned a selected, valid fallback.
No hosted latency, strategy quality or successful provider connectivity claim is made.

## Real-provider repair verification

The user subsequently granted standing authority for as many sandbox runs as necessary.
Four fresh inference-only probes (retry-02 through retry-05) used eight model calls. Token
usage was reported for all eight; aggregate token-rate cost estimate is USD 0.0174648. This
excludes earlier attempts with unknown usage/reserved costs. One authenticated model-access
GET succeeded in 0.724 seconds; it was not an inference call. No Arena session, submission,
Lab publication, push or promotion occurred. No individual request was retried.

| Attempt | Interpretation | Proposal | Decision/runner result | Estimated token cost |
| --- | --- | --- | --- | --- |
| retry-02 | Success, 6.857 s; grounding rejected | Success, 2.436 s; contradictory labels | Proposal rejection diagnostic itself failed; cannot decide, complete saved trace/report | $0.0050568 |
| retry-03 | Admitted, 3.025 s | Admitted, 2.689 s | Model-generated action independently valid; caller 6.252 s | $0.0041132 |
| retry-04 | Admitted, 3.412 s | Rejected, 2.797 s; missing payment uncertainty | Certified fixed fallback valid; caller 6.724 s | $0.0041660 |
| retry-05 | Admitted, 2.908 s | Admitted, 2.747 s | Model-generated action independently valid; caller 6.176 s | $0.0041288 |

retry-02's prepared measurement plan requested 30/15-second stages, but spawned workers did
not inherit parent module overrides and actually ran the original 9/5-second caps. This
configuration mismatch is retained as evidence and was fixed before retry-03: workers now
read limits from the persisted approved plan, and the supervisor receives the actual compute
limit. retry-03 used the longer measurement plan. retry-04 and retry-05 used the original
9/5-second stages, 15-second aggregate model allowance and 35-second compute limit. Production
stage caps were not increased. The final full decision took 5.725 seconds.

Further fixes:

- Proposal commercial-effect rejection now uses a schema-supported grounding diagnostic stage.
  Previously `commercial_effects` was not an allowed stage and diagnostic construction raised
  ValidationError inside the rejection handler, preventing fallback.
- The conservative interpreter prompt now explicitly requests at most one exact-source ambiguity
  observation per supplier message, instead of itemized paraphrases or observed-sheet defaults.
  This aligns with existing grounding requirements and reduced this D01 output from 1,044 tokens
  in retry-02 to 301 in retry-05. This is source preservation, not deeper supplier inference.
- The proposer prompt explicitly includes unchanged terms and continuous price fields omitted by
  discrete options, and distinguishes trade direction from unknown supplier net value. It requires
  uncertainty for changed payment terms as well as price and duration. Validators remain intact.
- The CLI accepts fresh `--output` destinations; exact output is still bound and checked in each
  approved plan. This supports repeat runs without overwriting consumed authorization/artifacts.

Final regressions: 77 passed across inference probe, grounded model, adaptive proposal and
commercial-effects suites. Scoped Ruff and `git diff --check` passed. Added checks cover
contradictory trade labels falling back safely and the worker honoring persisted compute/model
limits. The earlier hosted-readiness checks remain recorded above.

Final evidence:
`/tmp/v2-d01-inference-probe-2026-10-11-retry-05/execution/result.json`,
`decision-trace.json`, `raw-model-outputs.jsonl`, `inference-ledger.json`, and `approved-plan.json`.
The final proposal is EUR 50.00, 45-day payment, 24-month contract, effective 2026-12-01. It was
selected and independently validated offline, never submitted. All failed/rejected attempts
remain available. These samples demonstrate working inference/admission/finalization, not
supplier acceptance, commercial optimality or tail-latency reliability.

Official documentation consulted: [latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization).
The document identifies generated output length as a latency factor; the numbers above are our
saved measurements, not a general provider latency guarantee.
