# V2 executable test catalog

This specifies [E](E-evaluation.md)'s engineering gate. Tests are executable now, before production V2 exists. [Expanded test manifest](../../tests/fixtures/v2/test-manifest.json) lists **every parametrized test ID**, fixture arguments, assertions, expected exceptions, owner task and failure condition, generated from collection and test source. The linked assertions are authoritative; prose here explains fixture intent and scope. Regenerate with `.venv/bin/python tests/v2/catalog.py` after reviewed additions. Expected answers remain test-only.

## Suites and result interpretation

T2.3 now has [direct cost-projection acceptance](../../tests/v2/contracts/test_cost_projection.py):
29 tests compose resolver outputs into validated EvidenceContext inputs and exercise source
changes, attribution/basis, explicit inadmissibility and projection fingerprints. Require
evidence.claims and the three newly implemented DTO symbols; internal_cost_claim/full T2.3
and official evaluation remain incomplete. The canonical hash here covers ResolvedCostInput,
not a complete EconomicContext or calculated package cost.

The first T2.1 increment adds [direct resolver acceptance](../../tests/v2/contracts/test_layered_resolver.py):
source precedence/whole-record replacement, collisions/replays, scope after source selection,
evidence-kind preservation and unchanged basis/provenance. These tests run without codec,
factory, server, or orchestration. Required-symbol gates cover D1 and the five implemented D2
exports; D2/T2.1/full-contract completion remains outstanding. The expanded manifest includes
the 53 focused resolver and supplemental contract cases.

| Suite | Purpose / when | Location |
|---|---|---|
| Contract | One port/schema/component, positive and negative invariants; after each owning task | [contracts](../../tests/v2/contracts) |
| Integration | Actual typed pipeline, artifact/record links, deterministic replay and saved results; after each milestone | [integration](../../tests/v2/integration) |
| Acceptance | Commercial metamorphic behavior, model budget, restart/uncertainty and all close reasons; before milestone promotion | [acceptance](../../tests/v2/acceptance) |

An absent module produces `xfail(UNIMPLEMENTED: exact module)`. Nothing else does. Present module import errors, absent methods, schema errors, wrong economics and failed assertions are ordinary failures. `--v2-require MODULE_PREFIX` changes missing modules under that prefix to failures; `--v2-require all` forbids missing components. Self-tests deliberately verify both outcomes. No blanket marker, catch-and-xfail, assertion removal or skip-all is permitted. A full preimplementation command can exit zero with expected failures; that does not establish an implemented milestone. Completion reports give pass/fail/xfail counts and required-prefix gates explicitly.

The autouse local network guard blocks socket connections while preserving asyncio socketpair. All provider/server tests use explicit injected fake gateways. No dotenv, credentials, new installs, remote fetches, hosted sessions or inference requests are needed. Fake-server terminal evidence is a control, never an actual Arena deal. Active opaque-sentinel routing checks are scaffolding controls; the separate typed integration test is the M1 production-interface gate.

## Golden fixtures and reference ports

| Fixture | Meaning / expected facts | Failure it detects |
|---|---|---|
| [p10.json](../../tests/fixtures/v2/p10.json) | Case verbatim from existing saved cases; opening from existing adviser tests; actual part unit 1; eight synthetic replies and controlled drafts; synthetic cost layers | Legal option/must-have/basis drift, mistaken 54-day outbound option, unsupported approval/discount, precedence/privacy mistakes |
| Same fixture packages | 28.34/42/23400/24 costs **1,335,154.08**; 56-day same package costs **1,368,754.08**; 27.60/56/23400/36 costs **1,333,891.20**, estimates off | Missed €33,600 late cost, incoherent cheaper-price versus cheaper-complete-package selection |
| [relationship.json](../../tests/fixtures/v2/relationship.json) | Existing STABILISE case/estimate; seven exact kit costs; known 49-price target €401,600; minimum near 48 | Monotonic assumption, zero returned price or lost valid certified candidate |
| [decision-record.json](../../tests/fixtures/v2/decision-record.json) | Structural ten-stage schema example with deterministic IDs/ref names; declared placeholder semantic hash | Lost stage, orphan selection, misleading failure, unknown schema; not a stored artifact closure or execution claim |
| [v1-baseline.json](../../tests/fixtures/v2/v1-baseline.json) | Historical source/tree/kit/lock/guidance/config/case hashes and exact full first message | Current remediation behavior accidentally relabelled as frozen V1 |

[fakes.py](../../tests/v2/fakes.py) demonstrates explicit clock, model and Arena ports; ScriptedPipeline supplies narrow stage methods and records inputs without commercial algorithms. Test-local builders select draft/response/state fixtures and raw malformed wire inputs. C §8.5 defines the typed RecordedInputs codec. For each feature module, its contract test constructs the concrete port independently; missing evidence/interpreter/economics implementations cannot be replaced with a magic fake returning expected errors. M1 may use declared typed scripted ports for the full loop while those features are incomplete.

## Executable coverage and exact failure conditions

Read each linked test for the complete positive/negative assertion; the expanded manifest gives every parameter instance.

| Test source / owner | Fixture or controlled change | Required invariant / failure condition |
|---|---|---|
| [foundation](../../tests/v2/contracts/test_foundation.py) / T1.1a–b | Price 28.34, units 1/100/1000; zero/negative/NaN/infinity/bool; unknown fields; bad types; original P10 and STABILISE | Strict schema and immutable decimal roundtrip; exact protocol signatures; kit components/totals to cent; nonmonotonic known root. Any coercion, unit division, wrong argument order or arithmetic drift fails; every declared port has a signature-matched minimal fake |
| [guardrails](../../tests/v2/contracts/test_guardrails.py) / T1.1c/T1.3 | Present broken module vs absent module; changed legacy env; stage order/orphan selection/failure/version; raw bad message limits | Missing-component xfail is narrow; required missing is fail; no import bug hidden; config unchanged by env; misleading records rejected; normalizer changes actual raw payloads and strips answers |
| [boundaries](../../tests/v2/contracts/test_boundaries.py) / T1.1b | Thirteen forbidden and five permitted sample imports, actual future source graph | Forbidden dependencies/dynamic imports rejected; allowed oracle/port injection accepted; no vacuous empty-namespace architecture claim. Any forbidden actual import fails |
| [evidence](../../tests/v2/contracts/test_evidence.py) / T2.1/3 | Synthetic cost 132.64 base→140 release→150 case; deleted case confidence; same-priority 151 collision; future/stale dates; foreign supplier; 100/1000 basis | Whole case replacement and provenance; no backfill; blocking no-winner conflict; temporal labels; no scope fallback to shadowed base; raw amounts/basis retained; context/record hashes invalidate; identical claim/estimate refs |
| [preparation](../../tests/v2/contracts/test_preparation.py) / T2.2 | Encoded prepared artifact, changed expected base/release/parser; corrupt JSON; changed record | Warm/cold contexts identical; changed frozen sources/parser/content rejected, never silently rebuilt or discovered |
| [interpretation](../../tests/v2/contracts/test_interpretation.py) / T3.2 | delivery/longer/shorter/refusal/uncertain/contradiction drafts; wrong quote/offset/message/session; provider errors; injection | Attributed original spans; reported constraint doesn't change case; approval/discount unknown and no invented numeric effect; contradiction retained; invalid output fallback; no binding action/private economics/tools in model input; one call, zero retries |
| [economics](../../tests/v2/contracts/test_economics.py) / T4.1/2 | P10 three packages; relationship finite ticks; current quote 30/DAP vs master60/FCA; impossible1000-day must-have; incompatible unit100 | Exact official totals/components; valid positive prices across both curve sides; corrected supplier reference changes actual economics; arithmetic zero-division/overflow yields no fabricated cost; infeasible generation empty; complete legal options/ticks/budget; unavailable alternate tagged, mismatched basis rejected |
| [selection](../../tests/v2/contracts/test_selection.py) / T4.3/4 | approved/rejected batch; unnecessary question; invalid ID/edited cost/malformed/timeout selector | Selected ID/evaluation/hash belong to approved immutable set; question is not a zero-cost offer; bad model selection has certified fallback and explicit reason |
| [validation](../../tests/v2/contracts/test_validation.py) / T5.1 | Nine raw term faults, eighteen action/claim/state/limit faults and five positive boundaries | Invalid outputs are rejected with **specified IssueCode**, never snapped; valid payload remains unchanged; live standing/recipient/cost/clock/pending/privacy checked; exact protocol maxima obeyed |
| [state](../../tests/v2/contracts/test_state.py) / T1.4/T5.2 | CAS duplicate/stale commit; duplicate source event; conflicting stored record; missing terminal proof; two assessment revisions | Atomic single outbox/permit; stale version conflict without another operation; exact dedupe; immutable record/history; no unproven terminal state |
| [pipeline](../../tests/v2/integration/test_pipeline.py) / M1 | fake routing, actual typed full loop, repeated frozen inputs, changed mock model output, reopened SQLite | All ten stages wired and persisted; exact demo package/cost; payload identity links dispatch; deterministic semantic/payload hashes; model output variability recorded; restart record reload doesn't send |
| [behavior](../../tests/v2/acceptance/test_behavior.py) / T4.3 | Flip longer36 to shorter12; append greeting; refusal; approval/contradiction; controlled cheap versus expensive 36-month packages | Intent direction changes; greeting preserves intent AND selected package/cost; refusal suppresses unsupported exchange; uncertainty clarifies; cheaper grounded variant changes selected package; expensive preference cannot override ceiling; injection never accepts/discloses |
| [model budget](../../tests/v2/acceptance/test_model_budget.py) / T3.2/3 | Hanging async provider with .02s limit; success returned after fake clock advances60s | Cancel/fallback within .25s outer bound; late success not applied; no waiting for daemon/background mutation |
| [recovery](../../tests/v2/acceptance/test_recovery.py) / T5.2–4 | Three uncertain send replies then restart; rejected closes/open server; five closing triggers; replaced standing offer; unknown open; proposal/parser/evaluator errors; refusal restart | Same pending ID/hash/exact bytes; no fresh session/conflicting accept; recovery_required stays nonterminal; authoritative fake terminal only; all close reasons use same valid standing economic decision; faults supervised/no sends; refusal history retained |

### Input mutation bindings (never expected-output switches)

Raw bad terms live in wire_message only; baseline packages/context remain independently valid. The typed codec wraps raw message bytes in the internal recipient/snapshot action frame for validate_wire; its post certificate hashes the outgoing message only. Missing field removes contract_months. mixed_accept_offer adds action alongside sheets. subject/body/ref/sheet/attachment counts are actual over-limit arrays/text. Private body states a known prohibited reservation amount. Claim fixture records supply real disclosure/freshness and canonical IDs: internal_claim is cost:310010 internal; hallucinated_claim ID is absent; stale_claim has valid_to before as_of; claims_4 supplies four independently verified disclosable fixture claims. refs20 positive has twenty existing disclosable references. Exact max text uses an approved template/style fixture, not arbitrary model text. Raw artifacts remain available for rejection evidence.

State-only mutations: stale_state sets rendered source version one below current state; pending_operation adds one owned unresolved operation; expired_deadline places conservative deadline before fake now; wrong_recipient uses sup:OTHER; nonstanding_accept names an alternative sheet; accept_above_alternative installs an executable valid cheaper alternate and a more expensive valid standing offer. Context/state snapshot hashes are recomputed consistently except when the test deliberately creates a stale binding. These require typed test builder fixtures; codec must not synthesize an invalid result from their label.

Replay schedules: acknowledged_send gives one authoritative fake send reply; uncertain_send gives three uncertain results and unchanged authoritative open state; close_rejected gives three definite422 rejections plus open observation; terminal_confirmed replaces illegal incoming54 with a valid current standing `offer:valid-standing` using the frozen42-day package, then acknowledges a terminal close; standing_offer_changed seeds a pending accept and observes a different standing ID before dispatch; unknown_open seeds the same owned open with no session ID. Reject-close and unknown schedules never add TerminalEvidence. Exceptions are injected port doubles, not source-module conditionals.

Selection fixtures: baseline offer plus unnecessary clarification has no approval unknown; invalid_id points outside batch; edited_cost adds unauthorized economics; malformed is non-JSON; timeout is typed timeout/exception. Controlled candidate lists are positive code-admitted synthetic price surfaces, not discovered or learned quotes. Always certify their full cost/basis and filter by grounded direction plus baseline before selection.

## Additional tests to write before their owning implementation

The current executable suite is substantial but does not claim to cover every later transport/data behavior. These named test specifications are mandatory subtask outputs, not optional wishlist or current passes. Add positive/negative cases before implementing each owning feature and regenerate the manifest.

| ID / owner | Fixture / expected invariant / failure condition |
|---|---|
| PREP-01–06 / T2.2 | Current warm/cold/mismatch tests are executable; additionally explicit missing base/release must raise before open. Source/parser changes may rebuild only via an explicit pre-clock command, never frozen runtime discovery |
| CONTEXT-01–04 / T2.4 | Same case with one new/replaced letter/message/document changes context; unchanged bytes do not. P07/P15 retain all parts; XLSX formula strings retain provenance without recalculation. Wrong basket scope blocks claims |
| MODEL-01–06 / T3.3 | Existing budget cases plus semaphore queue consumes total deadline, provider refusal/partial JSON, cancellation capacity release and zero late writes. Fake transport only; no provider inferred from connectivity probe |
| STORE-01–04 / T5.2 | Crash barriers before transaction, after outbox insert and before/after commit; reopen exposes either all or none of state/reservations/outbox. Corrupt artifact/snapshot, conflicting source key and out-of-order accepted messages cannot fabricate terminal/rounds |
| TIME-01–04 / T5.3 | Delayed observation/limiter/parsing consumes window from snapshot request, cached old reply doesn't refresh60s, server-counted timeout consumes round, stopped lease prevents dispatch. No guessed deadline/round allowance |
| ENDPOINT-01 / T5.3 | Typed allowed-method requests plus spectator alias/subpath/percent-encoded/traversal paths; anything outside canonical agent allowlist rejected before fake transport receives it |
| FEEDBACK-01–03 / T5.4 | One-field delta stays attributed; multi-field sheet stays combined; ambiguous claim index remains unknown; repeated ack doesn't double-use a claim; answered question and refusal survive restart. No causal persuasion inference |
| LEGACY-01–03 / T5.5 | Invalid legacy output rejected, legacy close converted to fresh request, v1-adapted identity kept separate; original frozen first move remains exact |
| LAUNCH-01–04 / T6.2 | Same explicit V2 config through CLI/standalone/checkpoint/installed path yields same first proposal/activation; old worker rejects new envelope before open; legacy paths unchanged |
| EXT-01 / T4.4/T7 | Swap dummy proposal/selection/research bundle under identical ports; all generated batches certified/recorded and read-only. No modifications to foundational packages permitted |
| NUM-01–05 / deferred T4.5 | If solver approved: ordinary known root, both relationship roots/chosen branch, unreachable below minimum, local minimum/tick rounding, positive certification after refinement; never test by expecting legacy helper's incorrect answer |

Live provider semantic accuracy, independent hosted performance and later async load remain separate funded gates in E. Passing mocks and official arithmetic is necessary engineering evidence, not evidence of negotiation improvement.


## Final remaining-DTO declaration tests — 10 October 2026

contracts/test_remaining_dtos.py owns T1.1d D1–D16: each export has a concrete positive
example, round-trip/frozen check, specific invalid mutation, extra/version rejection and exact
field/default assertions. Fifty explicit scenario cases cover source authority, registered
estimates, scenario coverage, malformed provider content and close/message boundaries.
Definitions/examples are test-only tests/v2/dto-contracts.json, hydrate with dto_spec.example.
Missing declared symbols may xfail only here; --v2-dto-require D1 (or a symbol/all) makes them
fail. Once a symbol exists, import/dependency/invariant/type errors fail normally. Existing
require() semantics and earlier assertions remain unchanged. Run this gate with every completed
batch plus existing --v2-require core/config checks; do not count pending DTO xfails as passes.

The global `--v2-require all` milestone gate also requires every declared remaining DTO.
Batch gates do not weaken that final all-components/all-schemas requirement.

### Assignment 1 consumer regression gate — 11 October 2026

`tests/v2/integration/test_consumer_regressions.py` adds 17 direct/coordinator cases for
CaseContract overlays, scope/conflict/identity/authority failures without lower-layer revival,
whole-record optional-field deletion, deterministic duplicates, exact outgoing fields and
price precision. Inputs refresh preparation/case/economic/render identities; package identities
are reconstructed normally. Require the existing addendum L/M module/symbol closure.

Result: scoped V2 1,030 passed / 364 explicitly unfinished xfails; official adapter/package
parity 47 passed; V2 Ruff, frozen V1 replay (3653046), and whitespace checks pass.
The manifest now has 1,394 cases. No existing assertions or frozen fixtures were changed.

R3 qualification: CostPolicy's existing v1 validator requires tick 0.01 (C §8.9).
The review's 0.05 probe used model_copy, bypassing that validator. The economic consumer
now explicitly rejects unsupported ticks even with a refreshed fingerprint; valid v1 prices
49.00/49.01/49.05 pass and 49.005 fails. A valid 0.05 policy and its 49.00/49.05 acceptance
cannot be delivered without a separately approved contract revision. No revision was made.
Assignment 2, source authentication/freshness, claims/closing and execution remain unfinished.

### Assignment 2 grounded model gate — 11 October 2026

See [the completion note](assignment-2-completion-2026-10-11.md) for scope, configuration,
filtering, attribution and limitations. test_grounded_model.py adds 45 direct/coordinator
contracts; the manifest contains 1,439 expanded cases. Scoped V2 with the complete existing
L/M requirements plus adapters.model, intelligence.interpreter, intelligence.fallback and
orchestration.budgets and all 15 consumed gateway names: **1,137 passed, 302 xfailed**.
Consumed DTO contracts: **681 passed, 182 xfailed**. Direct plus original interpreter/budget
selectors: **45 passed, 19 xfailed** (absent complete adapters.recorded binding). No old
assertions/xfail conditions were changed. Ruff over V2 and experiments/v2, frozen first-move
replay (3653046) and whitespace checks pass.

The 11-example interpretation pilot has provisional labels pending independent review.
Scripted drafts verify schema/span and bounded semantic admission, not LLM understanding.
No provider was called and no hosted accuracy or negotiation outcome was measured.

## Assignment 3 — approved-ID strategic selection, 11 October 2026

Consumed SelectorResponse; bounded strategy.selection, shared grounding helpers and fixed
approval/conditions catalog; focused test_grounded_selection.py and 24-scenario three-arm
fake-response pilot. Independent semantic/admissible-set review and real-model performance
remain unmeasured. See assignment-3-completion-2026-10-11.md for projections, limitations,
reproduction, held-out identity and Assignment-4 handoff. No existing assertion/xfail policy
changed; full adapters.recorded/claims/close/store/research capabilities remain unfinished.

Verification: **1,177 passed, 298 expected xfailed** in the complete consumed L/M +
Assignment-2 + strategy.selection/SelectorResponse scoped gate. Focused Assignment-3 tests:
**36 passed**. Manifest: **1,475 expanded contracts**. V2/tests/experiment Ruff, frozen V1
first-message replay, and whitespace checks pass. Repository-wide Ruff reports the four
unchanged V1 violations documented in the completion report. No hosted quality measurement.

## Controlled real-LLM readiness — 11 October 2026

26 focused test_hosted_readiness.py cases verify the real P10 loader, provider wire/schema/
usage/timeout/refusal/cancellation/budget negatives, exact authorization and labelled local
rehearsal. Hosted compatibility and semantics remain unmeasured. Existing regression gate
adds adapters.chat_completions and adapters.p10; no broad recorded codec, persistence or
Assignment-4 closure. See real-llm-readiness-2026-10-11.md for setup and local Lab evidence.

Final verification: **1,203 passed, 298 expected xfailed** in the complete consumed V2
scoped gate, including the two new adapters; **26 passed** in the focused readiness suite;
**167 passed** across Lab runner/server/policy/campaign/CLI/checkpoint/store tests.
Manifest: **1,501 expanded contracts**. Scoped Ruff, frozen V1 replay and whitespace checks
pass. The broader non-V2 regression run returned **350 passed, 14 failed**; every failure
matches the recorded `a88bf86-fixed-data` baseline in
`/tmp/v2-review-regression-comparison.json`. Its two prior Lab campaign failures pass with
the existing uv executable on PATH. No V1 or Lab production source was changed. The four
repository-wide Ruff violations remain inherited. Full legacy-suite success is not claimed.

Six further hosted-readiness checks cover dotenv-to-wire consumption without credential traces,
strict OpenAI alias/snapshot mapping, failed-call dollar reservations, exact combined approval,
common-universe benchmark composition and full mock comparison/restart rejection. Focused suite:
**32 passed**. Manifest: **1,507 expanded contracts**. No hosted inference in tests.

Follow-up final gate: **1,209 passed, 298 expected xfailed**; 32 focused checks, 1,507
manifest contracts, scoped Ruff/frozen V1 replay/whitespace pass. The user corrected the
model to gpt-4.1-mini; the effective configuration now validates. Hosted approval pending.
