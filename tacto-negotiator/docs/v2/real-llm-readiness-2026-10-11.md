# First controlled real-LLM experiment — prepared, hosted run blocked

11 October 2026, Europe/Zurich. No hosted model calls, remote Arena session starts, sent
Arena actions or remote Lab uploads. No Assignment 4, new negotiation execution framework,
operational persistence, dependency/default changes, commit or push. Existing work preserved.

## Readiness investigation

Assignments 1–3 already supply layered context assembly, official economic evaluation,
bounded supplied-candidate generation, grounded interpretation, approved-ID selection,
independent validation and hash-verifiable exact-byte diagnostic traces. The asynchronous
model gateway already supports cancellable injected transports and one shared decision ledger.
Fake gateway success did not establish HTTP/provider compatibility.

The old `negotiator.inference.InferenceConnection` is a synchronous closing-style probe. It
uses an explicitly configured OpenAI-compatible chat endpoint, but it neither consumes V2
model envelopes nor enforces the V2 shared total time/token/call budget. It was not reused
as an inference scheduler and was not activated.

Effective exported-environment plus `.env` checks found `LLM_API_KEY`, `LLM_BASE_URL` and
`LLM_MODEL` missing. `LLM_PROVIDER=openai` names a proposed wire convention, not an approved
provider or model. No exact provider/model/dataset authorization or absolute inference
allowance exists. Arena and Lab credentials are separately configured and do not authorize
inference spend. Credentials were neither printed nor modified.

After the local rehearsal and local Lab smoke completed, read-only remote GETs succeeded:

- Arena `/v1/cases?set=sandbox`: D01 and D02.
- Arena `/v1/cases?set=practice`: P10 is available and marked hosted.
- Lab suite, recommendation and findings endpoints: available. The current
  d01-d02-sandbox-serial-v1 recommendation is checkpoint
  `e1d931e4fcce49fb8fd341c40052953a`, generation 1; three findings were listed.

Thus **P10 is a practice case, not a remote sandbox case**. The controlled experiment uses
its recorded inputs locally and consumes no practice session. Readiness metadata is saved
in `/tmp/v2-readonly-readiness.json`. No spectator events/screen/leaderboard/results endpoint
was accessed. Owned-session/thread/attachment reads can be used later with an identified
owned session, but no such remote session was selected or opened in this task.

## Small integration implemented

`adapters/p10.py` loads the original one-part P10 contract, retaining buyer economics,
legal options, fixed terms, must-haves and explicit unit basis. It uses the existing focused
OfflineRecordedInputs/assembler route, with explicit disabled supplier estimates, empty
quote standards and **synthetic conservative clocks and state**. Raw observed opening
sheets/documents are outside this text-only experiment; the historical 54-day opening is
not silently repaired or turned into an admissible outgoing package. The typed model input
contains only the approved supplier body. These local clocks/state are not remote authority.
The original case arithmetic is faithfully represented; a complete current Arena observation
and document-hydration adapter remain absent.

`experiments/v2/p10-offline-input.json` copies the frozen P10 case and supplies three fixed
legal packages from its arithmetic checks. It contains the recorded opening text “Which
volume can you commit to?” and the labelled synthetic variation “We prefer delivery in 42
days.” All variants retain the identical package universe and economic inputs. The entire
input dataset is content-bound by SHA-256:
`ce7029a6689450dd3061b5203a44449630ee88b1f89e171ea4f921e9c72e2d7f`.
Raw buyer fields stay local; only reviewed V2 purpose projections may leave the process.

`adapters/chat_completions.py` implements a small async HTTP transport over existing httpx,
with explicit endpoint/provider/model and an injected AsyncClient/key. There is no ambient
credential lookup, public-provider fallback, retry, redirect, automatic model discovery,
tool invocation or inference at import/construction. It binds the existing task/prompt/schema
IDs, reads the packaged interpretation/selection prompts, includes the exact output schema,
and asks for one JSON object. It returns existing ModelResult variants. It handles refusals,
truncation, unexpected tool calls, malformed or oversized responses, capacity/HTTP failures,
usage/model mismatches, timeouts and cancellation without retaining unsafe error bodies.

Official OpenAI documentation distinguishes JSON mode from strict schema enforcement and
specifies that `max_completion_tokens` caps generated visible and reasoning tokens. This
transport uses JSON mode plus the existing strict consumer decoders; it does not assert
that every OpenAI-compatible service supports these parameters. An explicitly confirmed
legacy `max_tokens` variant is supported without an automatic retry or protocol switch.
[Official chat-completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

The existing prompts suit a text JSON transport mechanically: they instruct exact supplier
spans, uncertainty retention and approved-ID selection. Their Pydantic schemas are supplied
as system context. Actual provider JSON support, exact model response identity, latency,
semantic competence and these narrow grounding requirements remain unmeasured. Alias model
responses are rejected if the configured ID differs; obtain the exact provider-returned ID.
The provider must also support the selected token parameter and include reasoning tokens in
completion accounting when applicable.

No tokenizer library is installed. This first transport bounds input by UTF-8 content bytes
plus 256 reserved framing tokens, then reduces the output cap so input-bound + output-cap
fits each existing ModelBudget. This is a conservative bound **only for an explicitly confirmed
byte-level tokenizer and bounded two-message framing**. The authorization must confirm that
convention; arbitrary compatible providers are not automatically supported. If it cannot
be confirmed, add an exact local tokenizer/counting adapter before inference. There is no
remote token-counting request. Missing usage conservatively retains the reservation;
reported total overruns remain charged and prevent further affordable work. A provider cannot
be forced to report usage truthfully, and the code does not promise to enforce remote billing.

`experiments/v2/run_p10_llm.py` is an experiment composition over the existing coordinator,
not a sending engine. It compares the model decision with a zero-call minimum-cost decision
on each exact batch, checks unchanged package/cost universes across language variants, and
writes complete baseline/model traces plus separate inference metrics. Traces retain
interpretation, selection references, all official costs, final validation, exact bytes,
usage, elapsed time, response hashes and fallback attribution. Reports also retain dataset,
model/protocol, prompt-byte and candidate-universe identities. No model rationale reaches
outgoing text. Production requests never contain raw buyer economics or benchmark labels.

## Local runs actually completed

The HTTP-envelope rehearsal ran the full requested path:

`P10 → focused context → interpreter → supplied generation → official economics → selector → templates → independent validator`.

It deliberately uses `httpx.MockTransport` with recorded fake JSON responses; it cannot be
mistaken for hosted evidence because reports are labelled “local fake HTTP rehearsal; no
hosted inference.” Both decisions independently validated without fallback, with two fake
calls each. Schema, wire parameters and usage handling are exercised by 26 focused tests.
The existing shared two-call ledger and 8/4-second per-purpose limits remain unchanged.
Compute is 35 seconds, total model time 12 seconds, fallback/submission reserves five seconds
each. Each call reserves 16,384 total input+output tokens, each decision at most 32,768; the
entire proposed two-message experiment reserves at most **four calls / 65,536 total tokens**.
The conservative reservation is deliberately larger than a tokenizer-based estimate.

| Fixed package | Official complete cost |
|---|---:|
| EUR 28.34; volume 23,400; contract 24 months; delivery 42 days | EUR 1,335,154.08 |
| EUR 28.34; volume 23,400; contract 24 months; delivery 56 days | EUR 1,368,754.08 |
| EUR 27.60; volume 23,400; contract 36 months; delivery 56 days | EUR 1,333,891.20 |

The recorded opening selects the minimum in the scripted rehearsal. The synthetic delivery
preference selects the 42-day package, at EUR 1,262.88 more than the minimum, with an exact
supporting span and low-confidence preference hypothesis. Official costs are unchanged.
Fake responses prove routing, not a model's commercial reasoning or supplier acceptance.
Artifacts: `/tmp/v2-p10-local-rehearsal/report.json` and its four baseline/model trace files.
Fake usage values are labelled test data, not actual inference consumption.

A second, separate smoke run used the actual existing Lab `plan_run`, `run_experiment`,
Publisher, DashboardServer and Store, alongside the pinned Arena simulator serving the
unchanged P10 case on loopback. It ran the existing **V1 PackageAgent**, not a V2 live agent,
for one local session and published only to a temporary local Lab. The run completed in
five rounds, zero timeouts, local score 0.946157564710246, and its original outcome was saved
and retrieved from the Lab. This verifies the runner/publication path and local protocol,
not V2 multi-turn effectiveness. Run ID `9e93d5bd-99d3-43cb-b38b-2a388a64c66b`; artifacts and
captured dirty-tree/data/lock provenance: `/tmp/v2-local-lab-smoke/summary.json` and `runs/`.
No remote Lab record was invented for the offline V2 decisions: its negotiated-session schema
and campaign worker currently serve V1 negotiated outcomes, not V2 offline decision scoring.

Local Lab checks initially hit the socket sandbox restriction. Re-running with localhost
access resolved it. Two checkpoint tests also needed the already-installed
`/tmp/evidence-tools/bin/uv` on PATH; no dependency was installed. The corrected command is
recorded below. There is no remaining demonstrated local Lab test failure.

## Exact runnable setup, with hosted authorization deliberately absent

From the project directory, rerun the offline rehearsal first:

```bash
.venv/bin/python -m experiments.v2.run_p10_llm --output /tmp/v2-p10-local-rehearsal
```

It produces `/tmp/v2-p10-local-rehearsal/authorization-template.json`, with
`authorized=false` and `token_accounting_confirmed=false`. Review its exact dataset and
purpose projection, obtain a named provider/exact model/base URL and confirm the JSON/token
protocol before completing an authorization copy. The four-call/65,536-token ceiling is a
**proposed allowance, not granted spend**. Approve one run only. A retry or new output directory
requires a new explicit allowance; do not reuse authorization to bypass it. A hosted-started
marker prevents silently reusing an already-started output directory after uncertainty.

Fill only the existing ignored `.env` inference entries, preserving all other settings:

```dotenv
LLM_API_KEY=<provider inference credential>
LLM_BASE_URL=<approved HTTPS base URL including its version prefix>
LLM_MODEL=<exact approved provider-returned model ID>
```

The authorization copy must match that endpoint/model, name the provider, retain the exact
dataset hash, approve its permitted projections and absolute calls/tokens, and confirm the
input-bound accounting plus selected token parameter. Credentials do not belong in that
public authorization file. The default output cap is 2,048 tokens per call. A dollar-denominated
allowance additionally needs approved input/output rates or provider-side spend controls;
no pricing/spend assumption is inferred here.

Only after that authorization and configuration exist, the prepared command is:

```bash
.venv/bin/python -m experiments.v2.run_p10_llm \
  --hosted --authorization /tmp/p10-llm-authorization.json \
  --output /tmp/v2-p10-hosted-first-run
```

Hosted mode itself repeats the local fake preflight before constructing any network-capable
model transport. It then checks exact provider/model/dataset/call/token approval and the key.
No Arena integration is invoked. The two-call decision ledger, aggregate conservative
experiment accounting, late-result rejection and certified fallbacks still apply. Reported
usage overruns increase experiment charges and block unaffordable subsequent work. Do not
rerun uncertain hosted work as an incidental troubleshooting step. **This command was not
executed: configuration and authorization are missing.**

## Remaining Arena negotiation blockers and next decision

A faithful remote run additionally needs separately authorized remote environment/case and
session allowance. P10 requires practice allowance/reserve; D01/D02 are the sandbox choices.
The V2 path lacks remote observation/document preparation, authoritative freshness/clock/
round proof, durable operation ownership/outbox/reconciliation, execution/recovery, independent
closing validation, multi-turn state/feedback and a rehearsed CLI/Lab execution composition.
None was built or silently delegated to V1 here. An offline action certificate does not
authorize a send. Arena keys and successful case-list GETs do not remove these blockers.

There are **no actual hosted-model results**. The observed local behavior supports the small
integration and diagnostic experiment, but does not justify advancing on a claim of LLM
understanding. Run the authorized interpreter/selector experiment, review exact spans and
conditions/refusals, count fallbacks/critical semantic errors, and assess commercially
admissible decisions first. The brittle bounded grounding rules, large schema context and
8/4-second timing may need improvement based on real outputs. Keep Assignment 4 unstarted
until that evidence identifies whether interpretation/selection or generation is the limiting
factor. Reactive outcomes remain necessary before negotiation-performance claims.

## Verification

```bash
.venv/bin/python -m pytest -q tests/v2/integration/test_hosted_readiness.py
PATH=/tmp/evidence-tools/bin:$PATH .venv/bin/python -m pytest -q \
  tests/test_lab_runner.py tests/test_lab_server.py tests/test_lab_policy.py \
  tests/test_lab_campaign.py tests/test_lab_loop_cli.py tests/test_lab_checkpoints.py \
  tests/test_lab_loop_store.py
.venv/bin/ruff check src/negotiator/v2 tests/v2 experiments/v2
.venv/bin/python tests/v2/replay_v1_baseline.py
.venv/bin/python tests/v2/catalog.py
git diff --check
```

The existing full L/M + Assignment-2/3 scoped gate gains
`--v2-require adapters.chat_completions --v2-require adapters.p10`. No unrelated DTOs or
unfinished-feature assertions were changed. Final counts are recorded in the test catalog.
Scoped Ruff and frozen V1 replay pass; repository-wide Ruff retains the same four unchanged
V1 violations. Local Lab socket tests require localhost permission in this environment.

Final verification: **1,203 passed, 298 expected xfailed** in the complete consumed V2
scoped gate, including the two new adapters; **26 passed** in the focused readiness suite;
**167 passed** across Lab runner/server/policy/campaign/CLI/checkpoint/store tests.
Manifest: **1,501 expanded contracts**. Scoped Ruff, frozen V1 replay and whitespace checks
pass. The broader non-V2 regression run returned **350 passed, 14 failed**; every failure
matches the recorded `a88bf86-fixed-data` baseline in
`/tmp/v2-review-regression-comparison.json`. Its two prior Lab campaign failures pass with
the existing uv executable on PATH. No V1 or Lab production source was changed. The four
repository-wide Ruff violations remain inherited. Full legacy-suite success is not claimed.

## Follow-up: requested GPT-4.1 mini comparison

The investigation above records the earlier configuration state. In the follow-up, all four
LLM settings are present, but the configured model differs from the requested GPT-4.1 mini
alias/snapshot. No credentials were printed or changed. A guarded combined connectivity/P10/
three-arm benchmark composition and an explicit $5 approval template are now prepared.
See [the reviewed run plan](hosted-comparison-plan-2026-10-11.md). No hosted call has occurred;
explicit provider/model/dataset/spend approval and the model configuration correction remain.
The plan records the documented alias/snapshot mapping, dollar reservations and benchmark
label-review limitations. Assignment 4 remains unstarted.

Follow-up final gate: **1,209 passed, 298 expected xfailed**; 32 focused checks, 1,507
manifest contracts, scoped Ruff/frozen V1 replay/whitespace pass. The user corrected the
model to gpt-4.1-mini; the effective configuration now validates. Hosted approval pending.

## Actual hosted follow-up completed

After explicit user approval of direct OpenAI, GPT-4.1 mini, reviewed P10/synthetic benchmark
projections and the $5/77-call allowance, the one-time hosted run completed: 74 calls,
182,292 known tokens, no timeouts, $0.085944 uncached usage-derived cost. P10 reproduced the
42-day selection change, but both interpretations fell back. Neither benchmark model arm
improved on the minimum-cost control; only 1/25 actual interpretation drafts was admitted.
See [the hosted results](hosted-comparison-results-2026-10-11.md) for complete distinctions,
consumer rejection counts, coarse-diagnostic limits and why Assignment 4 remains unstarted.
No Arena sessions/actions or remote Lab uploads occurred; the approval is consumed.
