# V2 LLM stabilization and local Experiment Lab integration

Implemented and evaluated locally on 11 October 2026. This establishes a diagnosable,
independently validated backbone and a tracked, multi-round Lab integration. It does **not**
establish hosted interpretation reliability, strategic superiority, or Arena readiness.
Assignment 4 remains deferred pending a separately authorized evaluation and semantic review.
No hosted inference, remote negotiations, remote Lab writes, checkpoint publication, promotion,
commit, push, frozen-label change, official-arithmetic change or V1 behavior change occurred.

## A. Repository investigation and root causes

Read `LAB_PLAYBOOK.md`, repository/package `AGENTS.md`, `docs/README.md`, the implementation
checklist, hosted results, C interfaces and task specs. `docs/v2/implementation-order.md` does
not exist; the available equivalent is `implementation-order-addendum-2026-10-10.md`.
Inspected the actual interpreter/selector/grounding DTOs and services, prompts, gateway,
chat-completions transport, ledger, offline coordinator, context assembler, official evaluator,
renderer/validator, benchmark scripts/fixtures, Lab CLI/runner/models/publish/store,
checkpoint/worker/execution/recovery paths, V1 serial play loop and the pinned kit's simulator.
Existing workspace edits were preserved. The campaign promotion workflow was not invoked:
this assignment authorized local verification, not shared recommendation changes or a campaign.

Verified architecture before this change:

1. `GroundedInterpreter` projects explicitly approved supplier-only messages, excludes raw
   evidence/private economics, makes one gateway call, decodes `AssessmentDraft`, independently
   checks exact spans and bounded semantics, then assigns assessment identity/history. A
   rejected output becomes the existing exact-message ambiguity fallback.
2. `BoundedModelSelector` verifies the registered evaluated batch and supplier assessment,
   projects exact candidate/evaluation IDs, permitted terms and official relative costs, and
   requests only `selected_id` and `supporting_quote`. A quote must equal an admitted citation,
   address a changed issue and pass refusal/condition checks. Rejection preserves the existing
   certified minimum-cost fallback. Rendering and final independent evaluation remain separate.
3. Responses can fail at projection/disclosure, provider execution/envelope, JSON/schema,
   semantic relationships, source grounding, exact-ID membership, or final consumer validation.
   DTO shape alone never grants economic, approval, source or execution authority.
4. The ledger recorded transport status, usage, hashes and safe admitted raw output. The
   interpreter did **not** call `reject_raw`; only fallback `unknowns` held a coarse cause.
   Selection called `reject_raw`, but only with coarse `IssueCode`. Therefore successful
   transport and failed interpretation appeared as a successful call with no cause.
5. The Lab already executes stable `decide(case, threads)` agents through `RecordingTable` and
   the serial `play_case` loop, persists plans before sessions and outcomes before ancillary
   reads, supports multiple rounds, generic agent factories, local buffering, upload/retrieval,
   immutable checkpoint campaigns, quotas, evidence and recovery. Default agents were V1
   PackageAgent/kit NaiveAgent. V2's recorded factory was disconnected from this agent interface.
6. Existing official economic evaluation, supplied finite candidates, input-only context
   assembly, selection, fixed rendering and independent validation were reusable. A second
   experiment orchestrator, dashboard or economic implementation was unnecessary.
7. Missing links were the Lab observation/session adapter, shared bounded composition,
   safe admission diagnostics, and a demonstrated run across the actual Lab/V2 boundary.
   Full V2 closing, authentic document hydration and durable dispatch/recovery remain missing.

Established interface defects:

- Interpretation rejection never reached call diagnostics; coarse exceptions concealed the
  field/stage. The retained hosted outputs cannot reconstruct those exact failed fields.
- The v1 prompt described principles but left many required nested fields, root DTO ownership,
  enum/default choices, typed decimal wire values and examples implicit.
- Supplier questions were instructed to become `request`, but the request cue validator did
  not recognize “Which volume can you commit to?”. The corrected narrow cue admits explicit
  interrogative questions without making arbitrary source text a request.
- The schema's validation projection allows numeric Decimal alternatives even though custom
  wire validators require decimal strings. The opt-in provider schema uses the authoritative
  DTO serialization projection instead, while consumer validators remain unchanged.
- JSON-object mode guarantees neither the required DTO fields nor exact enums. The new
  structured-output option is derived from DTOs and remains independently validated.
- Selection's quote must equal an entire stored citation, not merely occur somewhere in the
  supplier message. V2 instructions now make this exact requirement, identity copying and
  the explicit minimum-ID/empty-quote fallback clear.

**Historical limits:** The approved run had 74 successful provider calls, only 1/25 admitted
interpretations and 26/49 admitted selections. Twenty-four interpretation rejections (21 generic
`model_invalid`, three `ungrounded_output`) and 23 selection grounding rejections remain
unattributable at the exact field/rule level. Prompt/schema confusion, quote substrings,
wrong candidate identities and genuinely unsupported decisions are hypotheses for individual
historic responses, not reconstructed facts. A read-only audit independently verified all
72 retained benchmark decision traces and 69 benchmark calls; its derived report is
`/tmp/v2-stabilization-historic-audit.json`. It leaves the originals unchanged and explicitly
marks rejected exact causes `unattributable`. P10/connectivity are outside that audit's denominator.

## B. Implementation and safety boundaries

- `core/diagnostics.py`: bounded typed stages/categories, sanitized error types and schema-owned
  field paths. Records only the first structural error. Arbitrary extra-field names become `*`;
  inputs, exception messages/context, secrets and rejected response text are never diagnostic data.
  Categories cover format/schema/missing/type/enum, semantic relationships, unsupported claims/
  economics, missing evidence, invalid quotes, candidate mismatch, grounding, disclosure,
  consumer validation, execution and unattributable history.
- `orchestration/budgets.py`, `adapters/model.py`, interpreter and selector: retain transport
  result independently of `consumer_admitted`, fallback use/reason and structured diagnostic.
  Both consumers propagate rejection. Successful admission is recorded only after independent
  grounding/membership checks. Legacy trace serialization preserves the historic hash projection;
  absent admission metadata remains unknown. No rejected model response is retained.
- `orchestration/offline.py`: interpretation fallback causes appear as stage warnings; successful
  execution of a fallback remains a completed stage. Boundary failures withhold exception content.
- Versioned `grounded-supplier-v2.txt` and `grounded-selection-v2.txt`: explicit fields, null/empty
  conventions, source copying, decimal strings, preference/requirement/approval/conditional/
  contradiction examples and exact selection quotations. V1 prompts remain available for replay.
  Unknown nested condition semantics retain the full original text and uncertainty rather than
  inventing a Boolean expression. Supplier assertions do not become buyer constraints or verified costs.
- `adapters/chat_completions.py`: explicit opt-in `structured_output=True`, required properties,
  closed objects and singleton enums derived from the DTO serialization schema. The conservative
  input-byte reservation includes the structured schema; it is supplied once, not redundantly
  pasted into the prompt. No retry or provider activation is added. Existing JSON-mode defaults
  and historical experiment versions remain unchanged.
- `factory.py`: moves the existing recorded-experiment composition into one reusable
  `bounded_services` function, plus an explicitly local Lab agent factory. Dependencies remain
  injected across evidence, interpretation, proposal, generation, official evaluation, selection,
  rendering and validation. The Lab contains no prompt/strategy implementation.
- `adapters/lab.py`: reviewed one-part P10 bridge, original Lab run/session identity, supplier-body
  purpose projection, all supplier message identities/history, actual accepted-message counts,
  assessment parent linkage and bounded candidates. Persists private local traces with mode 0600
  before returning only independently validated bytes. Duplicate observations require
  reconciliation; invalid validation yields no submitted message. No accept/walk action authority.
- Lab CLI/runner: optional session observation hook, local-agent preflight, and explicit
  `lab run --local-case FILE` mode using the existing official Sim through a small client seam.
  This mode fixes the environment to local simulator semantics and disables publishers even
  when remote credentials are configured. Normal runs retain their existing interfaces/defaults.
- `orchestration/metrics.py`, evaluator and experiment tools: transport/admission/fallback/validity,
  latency/reservations, official selected cost/delta and baseline identity differences are separate
  from semantic/strategic review and actual simulator agreement outcomes. Unmeasured judgments
  and hosted expenditures remain unknown. Local scripted inference expenditure is zero.

The structured-output projection follows the documented required-field/closed-object rules.
GPT-4.1 mini is documented to support structured outputs; this schema's live provider admission
has **not** been tested in this assignment. See [official structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
and the [GPT-4.1 mini model reference](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Independent semantic, grounding, disclosure, budget and final economic validation remain required.
The existing two-call, 32,768-reserved-token decision composition and time/submission reserves
are preserved. No permissive DTO parsing, arbitrary proposal generation or deterministic
negotiation-heuristic library was introduced.

## C. Experiment Lab integration matrix

“Existing” describes the audited Lab/code before this assignment; “connected” describes the
verified local bounded slice afterward.

| Component | Existing | Connected to V2 | Missing / scope limit |
|---|---|---|---|
| Scenario loading | Lab case plan and kit case loading | Reviewed P10 JSON into official Sim | Generic/multipart V2 loading |
| Negotiation observations | RecordingTable, case and original threads | Run/session IDs, bodies and message history | Authenticated hosted V2 observation adapter |
| Evidence/context assembly | V2 layered context and recorded assembler | Same assembler invoked every round | Demo has empty prepared external evidence; document hydration/quote extraction not connected |
| Supplier interpretation | GroundedInterpreter + fallback | Actual interpreter, scripted model in grounded arm | Hosted semantic quality unmeasured |
| Strategy invocation | Replaceable proposal/selection ports | Supplied bounded policy through same coordinator | Model-driven proposal/research strategy deferred |
| Candidate evaluation | Official evaluator + finite supplied generator | Same official evaluator and fixed common universe | General price search / robust scenario expansion |
| Proposal selection | Minimum and bounded LLM-ID selectors | Minimum, direct and interpretation-assisted arms | Strategic improvement not demonstrated |
| Action validation | Independent V2 final validator | Every returned message certified and digest-checked | V2 close/claims/attachments validation remains unavailable |
| Multi-round state | Lab serial loop and V2 assessment parent contract | Counts, versions, all supplier messages and parent assessments | Durable V2 event ownership/feedback/restart; final-offer distinctions |
| Action submission | Lab RecordingTable/client interface | Validated bytes go to official in-process Sim | Remote V2 dispatch/idempotency remains disabled |
| Outcome retrieval | Lab ancillary reads and saved snapshots | Simulator terminal result retrieved separately from actions | No real supplier outcome evidence |
| Experiment persistence | save_snapshot/load_snapshots, source patches, provenance | Existing run records + local trace artifacts | Full traces not uploaded/indexed in shared dashboard |
| Metrics/reporting | Lab scores/rounds and existing pilot evaluators | Admission/economics/fallback diagnostics + semantic review artifact | Human-reviewed utility/defensibility and calibrated model errors |

Actual verified path:

```text
negotiator lab run --local-case -> plan/provenance/agent_factory -> run_experiment
 -> RecordingTable.open -> official Sim.open -> observed Lab run/session identity
 -> LocalV2LabAgent.decide(case, threads) -> typed recorded context assembly
 -> GroundedInterpreter (grounded arm) / attributed echo control
 -> supplied strategy intents -> finite candidate generation -> official economics
 -> bounded ID selection / certified minimum -> fixed renderer -> independent validator
 -> certified message bytes -> RecordingTable.send -> official Sim.message
 -> next supplier observation (six rounds) / actual simulator terminal outcome
 -> existing Lab snapshots, local traces, operational metrics -> load_snapshots + trace.verify
```

The official Sim supplies its documented fixed supplier script. It computes its own terminal
result using the pinned kit; the experiment does not fabricate an outcome or replace a failure
with a valid-action count. Source/lock/data/patch fingerprints and original supplier thread
records are retained by the Lab. Deterministic package/cost behavior is reproducible; UUIDs,
wall-clock values, measured latency and resulting trace hashes vary between separate runs.
These dirty-workspace exploratory records do not constitute published immutable campaign arms.
The local adapter represents actionable simulator `final_offer` as the DTO's open thread;
original statuses remain in Lab thread evidence. It provides no production final-offer/closing mapping.

Run from the `tacto-negotiator` directory:

```bash
.venv/bin/python experiments/v2/run_lab_local.py --out /tmp/v2-lab-stabilization-final
.venv/bin/python -m experiments.v2.evaluate_stabilization --out /tmp/v2-semantic-stabilization-final
.venv/bin/python -m experiments.v2.audit_historic_admission \
  /tmp/v2-hosted-comparison-first-run --out /tmp/v2-stabilization-historic-audit.json
```

The demonstration invokes the actual Lab CLI for each arm. For a single tracked arm, after
that tool writes its reviewed public `case.json`, the equivalent command is:

```bash
.venv/bin/negotiator lab run --name 'V2 local grounded' --author local-verification \
  --hypothesis 'Verify bounded V2 across the Lab boundary' \
  --agent negotiator.v2.factory:local_lab_agent \
  --config '{"dataset_path":"experiments/v2/p10-offline-input.json","trace_root":"/tmp/v2-lab-traces","arm":"grounded"}' \
  --cases case:P10 --environment simulator --local-case /tmp/v2-lab-stabilization-final/case.json \
  --repetitions 1 --max-sessions 1 --allow-dirty --root /tmp/v2-lab-single
```

This explicit local mode does not consume hosted practice quota or upload records. The printed
practice balance belongs only to the isolated simulator. Normal configured Lab commands still
publish automatically, as the playbook describes, and require their own authorization.

## D. Evaluation evidence

Local fixture/provider-mock and regression evidence is distinct from the earlier hosted run:

| Measurement | Result | Interpretation |
|---|---|---|
| Authored interpretation draft controls | 14/14 admitted; no fallback | Structural/grounding plumbing, not live model admission |
| Separate provisional semantic checks | 14/14 controls; 14 human reviews outstanding | Synthetic draft checks, not validated supplier-understanding accuracy |
| Negative semantic evaluator control | Admission remains 100%; semantic match drops to 13/14 | Structural validity cannot substitute for understanding |
| Tracked Lab model executions | 18/18 scripted calls succeed | Six direct calls; twelve grounded calls |
| Lab interpretation admission | 6/6 grounded calls | Ambiguity-only mock; intentionally no model-quality claim |
| Lab selection admission | 12/12 | Explicit scripted minimum selections |
| Lab model fallbacks | 0/18 | Separate intentional echo controls in minimum/direct arms |
| Independently valid Lab actions | 18/18 | Six decisions per arm |
| Lab terminal outcomes | 3 completed; 3 no-deal; six rounds each; zero timeouts | Actual official simulator outcomes, zero agreement scores |
| Baseline comparison | Same minimum package in all arms; official offer cost EUR 1,333,891.20; zero deltas | No strategic improvement; agreement cost is null because there was no deal |
| Local inference expense | USD 0; usage unreported by mock and reservations explicitly recorded | No hosted token/latency claims |
| Historic trace integrity | 72/72 original benchmark traces verify | Historic exact rejected-output causes remain unattributable |

Reviewable artifacts:

- `/tmp/v2-lab-stabilization-final/report.json`, `runs/<run-id>/run.json`, local source patches,
  and `traces/<run-id>/<session-id>/decision-*.json`.
- `/tmp/v2-semantic-stabilization-final/report.json`, `predictions.json`, `human-review.json`.
  Review judgments are null; no critical-error-free or supplier-utility label is invented.
- `/tmp/v2-stabilization-historic-audit.json` and existing hosted report, kept separate.

Focused diagnostic and integration controls cover malformed JSON, missing fields, field types,
enums, extra names containing unsafe data, forged/wrong spans, wrong meanings/conditions,
unsupported economics/claims, missing evidence, exact candidate IDs, edited selection,
disclosure, transport failures, fallback warnings, invalid final validation, remote preflight,
legacy trace re-export, prompt resources, derived provider schemas and schema budget accounting.
Existing refusal/timeout/cancellation/queue/budget/private-grounding tests continue to run.
New semantics cover single/multiple preferences, refusals, conditional/combined/nested scope,
contradiction, approval uncertainty, ambiguous language, unsupported cost claims, irrelevant
language, injection, supplier questions and conditional commitments. The frozen held-out
selection fixture and labels were neither modified nor used to tune these changes.

Regression details and commands are recorded below after the final gate. The repository's
previously documented unrelated V1 failures are reported separately; they were not repaired
by changing V1 golden behavior or weakening assertions.

## E. Remaining work and smallest next experiment

Before another hosted evaluation: independently review the new public supplier texts and
semantic expectations, inspect the generated provider request/schema and input reservation,
pin prompt/schema/provider/model identities, approve the exact dataset and an absolute separate
inference allowance. The previous one-time authorization is exhausted and is not reusable.
The smallest meaningful proposed evaluation is 14 interpretation calls on these development
examples plus two paired P10 decisions (four calls) and one structured connectivity probe:
**at most 19 calls**, still at most two per negotiation decision, no retries, no Arena sessions
and no remote Lab writes. Establish a reviewed spend ceiling rather than extrapolating old
inference prices. Evaluate admission and independent semantic/critical-error review separately,
and inspect every rejection diagnostic. Do not optimize the frozen held-out corpus. **Not launched.**

Before Assignment 4: require that hosted development evaluation and human review demonstrate
usable interpretation/selection, or explicitly adjudicate remaining failures. Local schema
success is insufficient. The current proposal policy and finite candidate universe remain
bounded controls; no unrestricted generation or propose-task contract was added.

Before research-strategy experiments: implement a separately scoped strategy through the
existing injected proposal/selection ports, register any needed bounded research interface,
prepare immutable source/config/data checkpoints and a preregistered baseline comparison in
the existing Lab campaign system. Do not create another orchestration system or promote a
candidate from fixture scores. Document hydration, full source authentication, general case
loading, commitment classification beyond verbatim observations and explicit nested-condition
logic remain narrower than the complete desired supplier-understanding capability.

Before real Arena negotiations: complete V2 closing validation/authority, authoritative hosted
observation and source hydration, durable ownership/journaling/idempotent dispatch/reconciliation,
feedback and restart handling, generic scenario support and installed/checkpoint launch gates.
The local bridge deliberately has no production close/dispatch authority. Genuine agreement,
buyer realized outcome, supplier adaptation and strategic defensibility remain unmeasured.
Resolve the documented unrelated V1 regression failures for any repository-wide release.

## Final regression record

- Focused new diagnostics/derived-schema/history/selection and Lab/semantic tests: **28 passed**.
  Original provider/P10 compatibility and focused controls: **59 passed** before the final
  budget assertion addition; offline/sanitized-boundary controls: **52 passed**.
- Consumed whole-V2 gate: **1,237 passed, 298 expected unimplemented xfailed**;
  regenerated manifest: **1,535** executable contracts. The full D12 milestone remains
  unavailable: DocumentBytes, ServerObservation, GatewayResponse, GatewayRejection,
  GatewayUnknown and GatewayResult are still absent. Only the already consumed D12 model
  input symbols are required by this slice; no absence assertion was weakened.
- Lab regressions with existing uv on PATH and localhost test-server permission: **170 passed**.
- Frozen V1 replay: first move still matches **3653046**.
- Scoped Ruff and whitespace checks pass. Repository-wide Ruff retains four findings in
  unchanged legacy evaluator/guards/runner files.
- Full repository regression: **1,567 passed, 19 skipped, 298 xfailed, 15 failed**.
  The failures are in unchanged legacy context (2), evaluator (3), inference (4), runner (5)
  and scaffold (1) tests and match the earlier recorded failure families. There are no V2
  or Lab failures. Their details are preserved in `/tmp/v2-stabilization-full-final.txt`;
  this is not a clean repository-wide release gate. The first Lab attempt exposed sandbox
  socket restrictions and missing uv on PATH; enabling local test-server access and using
  the already installed `/tmp/evidence-tools/bin/uv` resolved those environmental failures.

Reproduce focused and regression checks (use the installed `uv` on your own PATH):

```bash
.venv/bin/python -m pytest -q tests/v2/integration/test_stabilization.py tests/v2/integration/test_lab_integration.py
.venv/bin/python -m pytest -q tests/v2
PATH=/tmp/evidence-tools/bin:$PATH .venv/bin/python -m pytest -q tests/test_lab*.py
PATH=/tmp/evidence-tools/bin:$PATH .venv/bin/python -m pytest -q tests --tb=short
.venv/bin/python tests/v2/replay_v1_baseline.py
.venv/bin/ruff check src/negotiator/v2 tests/v2 experiments/v2 src/negotiator/lab/cli.py src/negotiator/lab/simulator.py
.venv/bin/python -m tests.v2.catalog
git diff --check
```

The stricter consumed gate also requires the implemented module prefixes and D1–D6/D8/D10/D11/
D13 batches plus individual consumed D9/D12 symbols, as in the previous completion reports;
its captured terminal output is `/tmp/v2-stabilization-v2-final.txt`. `--v2-require all` is
not a satisfied milestone. Hosted model quality, full pipeline execution/closing and the
remaining human reviews are explicit open acceptance limits, not claimed complete.

## Follow-up: failure analysis and executable hosted preparation

The [11 October follow-up](hosted-semantic-validation-and-lab-failure-analysis-2026-10-11.md)
inspects all three original transcripts and verifies 18 trace certificates. Every supplied price
is below the simulator's EUR 29.59 floor; repeated below-threshold offers cause the observed
sixth-round walk-away. It separately records missing live terms, terminal-status semantics and
acknowledged buyer history in the bounded Lab bridge. The follow-up provides a tested, exact
19-call GPT-4.1 mini plan, separate text-based semantic review and a proposed USD 1.00 allowance.
Hosted inference and independent human adjudication remain pending explicit authorization.
