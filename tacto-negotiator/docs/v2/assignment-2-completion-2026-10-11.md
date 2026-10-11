# Assignment 2 — budgeted grounded interpretation, local verification

11 October 2026. Working tree a88bf86 plus preserved prior changes. No hosted inference,
Arena sessions, credentials, dependency/default/V1 changes, commit or push. Assignment 3
was not implemented. T1.1d/T3.2/T3.3 remain partial; no supplier-understanding, negotiation
performance, full model infrastructure or live-readiness claim.

Implemented exactly the consumed 15 exports: InterpretInput, SelectionOption, SelectInput,
SimulateInput, ModelInput, ModelRequest, ModelBudget, ModelUsage, ModelSuccess, ModelRefused,
ModelInvalid, ModelTimeout, ModelCapacityUnavailable, ModelTransportFailure, ModelResult.
Unions are complete; raw-response hashes, UTC deadlines, strict counters and required failure
issues are validated. No SelectorResponse or propose task was added.

## Working path

AsyncModelGateway delegates to an injected async transport. Every invocation requires a
DecisionModelLedger, either explicitly supplied for direct component use or bound by the
coordinator. The transport resolves the explicit provider/model/protocol/prompt/schema IDs;
there is no concrete hosted provider adapter. The registered interpretation prompt is
src/negotiator/v2/intelligence/prompts/grounded-supplier-v1.txt. A future provider transport
must implement that prompt/protocol and honor the supplied total token reservation, including
input and output. Provider/tokenizer compatibility and real usage remain unmeasured.

GroundedInterpreter requires explicit InterpreterConfig: provider/protocol/model, purpose
prompt/schema versions, per-call time/token bounds, input/output size limits and approved
supplier message hashes. The first projection excludes all raw evidence and prior assessment
text, and refuses buyer/mixed history, unapproved messages, documents/sheets/metadata and
recognized private prose. It never redacts content under an original identity or silently
truncates a ConversationView. Message hashes are recomputed from exact body bytes. Approval
of source content is an explicit caller obligation; the lexical private-data guard is defense
in depth, not a universal confidentiality classifier. Prior parent/revision linkage remains
in the resulting local assessment.

Model drafts are decoded as strict AssessmentDraft. Scoped exact spans, complete conditional
antecedents, explicit numeric values/operators/dimensions, observation references, supported
kind cues, approval unknowns and contradictory active equality constraints are checked.
Summaries must be exact supporting quotes in this bounded version. Preferences remain
low/unknown-confidence hypotheses without numeric effects. Reported costs cannot become
canonical facts. Internal clarification suggestions are limited to clarify:terms and a fixed
information description; they do not register new outbound actions. Arbitrary paraphrase/
entailment, broad linguistic operators, role changes and comprehensive contradiction
resolution are not certified; uncertain/unsupported drafts fall back.

One coordinator decision binds one ledger across gateway consumers and async stages. Calls
are reserved before awaiting, capped by DecisionBudget (at most two), with no retry/reset
from new requests. Token reservations use explicit configured upper bounds; complete known
usage refunds unused capacity, partial/missing usage retains the full reservation and stays
null in attribution. Reported overruns are retained and rejected, blocking further admissions;
no claim is made that an untrusted transport can be forced to honor a remote token cap.
Elapsed queue/call time counts against the decision's total model time, compute deadline,
absolute deadline and fallback/submission reserves. Timeouts/cancellation cancel the task;
cancellation-resistant late completions are observed and never applied. External cancellation
propagates. Exceptions are mapped without copying potentially secret exception text.

Fallback retains uninterpreted cited input, the cause, call ID and parent linkage, and adds
no commercial/economic inference. The existing fixed strategy/economics/renderer/independent
validator remain in place. Traces retain filtered requests/hashes, result category, actual
elapsed time, nullable usage, charged reservations, response hashes and accepted safe raw
outputs. Rejected raw drafts are withheld. Hash verification survives trace JSON reload.
This is diagnostic storage, not durable operation ownership.

## Evaluation and verification

The 11-example interpretation-pilot.json covers conditions, preferences/constraints, refusal
scope, approval, contradictions, reported numerical claims, greetings and injection. Labels
are provisional author annotations, independent human review pending. Fake draft tests prove
routing/admission of these structures and rejection of several correct-quote/wrong-meaning
counterexamples; they do not measure model understanding. The evaluator under experiments/v2
reports category precision/recall, accuracy under bounded labels, missing examples, abstentions,
fallbacks, grounding failures and externally annotated critical errors. Unreviewed critical
annotations are explicit. Broader semantic entailment requires independent review.

Direct Assignment 2 tests: 45 passed. Existing interpreter/budget selectors: 19 xfailed due to
the still-absent complete adapters.recorded binding, with no assertion changes or new xfails.
The new tests use validated focused offline bindings and actual coordinator/economics/validator;
they do not mark that complete codec gate finished. Consumed DTO gate: 681 passed, 182 explicit
absent-export xfails. Final scoped V2, Ruff, replay and manifest results are recorded in the
catalog below; no unrelated claim/close/store/research feature was relabelled implemented.

Reproduce direct checks:

```bash
.venv/bin/python -m pytest -q tests/v2/integration/test_grounded_model.py tests/v2/contracts/test_interpretation.py tests/v2/acceptance/test_model_budget.py --v2-require intelligence.interpreter --v2-require adapters.model --v2-require orchestration.budgets
.venv/bin/ruff check src/negotiator/v2 tests/v2 experiments/v2
.venv/bin/python tests/v2/replay_v1_baseline.py
```

For the full scoped gate retain Assignment 1's complete L/M module/symbol set and add
adapters.model, intelligence.interpreter, intelligence.fallback and orchestration.budgets;
require each of the 15 exports explicitly, rather than all D12/D13.

Assignment 3 needs SelectorResponse, a bounded approved-ID selector and select projection,
code-authored summaries/relative economics, the same decision ledger and approved grounding
policy, certified fallback, and reviewed offer/question comparisons. It can consume the
assessment through the unchanged ActionSelectionPolicy seam. No database/full codec/live
execution/propose task is needed. Actual hosted semantic evaluation needs separately approved
provider/protocol/model, safe corpus and absolute allowance; none is authorized by this work.
