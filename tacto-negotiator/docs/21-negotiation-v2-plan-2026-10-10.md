# Negotiation Engine V2 — living architecture and implementation plan

**Created:** 10 October 2026, Europe/Zurich. **Status:** architecture approved in principle; implementation handoff prepared; production tasks planned.
**Inspected checkout:** `codex-main-branch-remediation-2026-10-10`, `4c905b10be1f576de9b68be9c120cf6796ae4561`.
**Historical main baseline:** `3653046bce6dd7cbbeffe00ecf5dfd9c3edbc0ab`.
**Official kit/submodule:** `1b5516bb95ef28e37f69aa446dc62168864bca53`.

This is the living architectural plan plus executable implementation guardrails. A–F have been refined in place; tests, golden fixtures, exact task assignments and review instructions accompany them. No V2 production implementation or V1 behavior change is included. Existing uncommitted work is preserved. Future funded experiments/promotion remain separate from this offline preparation.

## Recommendation

Build V2 alongside `PackageAgent` in `negotiator.v2`. Use one orchestrated decision loop with immutable inputs and typed contracts. Evidence, supplier interpretation, strategy proposal, candidate generation, economic evaluation, candidate selection, final validation, execution, and feedback have separate responsibilities. Keep official arithmetic and canonical claim verification behind independent interfaces. Preserve the raw observations so an alternative interpreter or strategy can use them later.

The first useful product is a **persistent, evidence-aware capacity negotiation loop**. Supplier delivery constraints, commitment requests, and explicit refusals must change its next commercial decision in an inspectable way. Begin with one case and one outstanding operation, a serial scheduling mode, deterministic wording, a bounded LLM interpreter, and deterministic candidate selection. An LLM selector can then be evaluated as a separate treatment. This keeps the initial intelligence demonstration small enough to verify.

Use existing readers, claims, arithmetic, experiment storage, and provenance patterns; replace their problematic integration boundaries. V2 does not depend on repairing every V1 module or implementing dormant scaffold functions. It does depend on a trustworthy economic adapter, shared evidence resolution, final action validation, honest terminal states, and durable operation ownership. Serial scheduling does not remove those obligations.

Strategies expose two interchangeable hooks: propose commercial intents and select an approved evaluated candidate. A strategy bundle can implement both hooks; research variants can iterate through a bounded, read-only candidate/evaluation service. They cannot execute, mutate facts, manufacture binding terms, or accept an offer. Closing eligibility and complete-cost comparison belong to a deterministic case coordinator.

V1 remains selectable and its historical results remain historical. A frozen V1 checkpoint is the comparison baseline; a V1 adapter through the new execution boundary is a distinct arm if it changes behavior. Promotion of V2 requires new evidence for one frozen configuration. The P10 adviser observation motivates the capacity slice; it does not establish V2 performance.

## Review package

| Document | Content | Principal review question |
|---|---|---|
| [A — Current architecture assessment](v2/A-current-architecture.md) | Actual source paths, coupling, reuse map, current defect status, smallest safe scope | Which existing components are trustworthy enough to wrap? |
| [B — Proposed architecture](v2/B-architecture.md) | Module tree, dependency and runtime diagrams, authority, state, recovery, configuration | Does this form a coherent single negotiation loop? |
| [C — Interface specification](v2/C-interfaces.md) | Concrete model fields, Protocol sketches, invariants, errors, ownership, dependencies, contract tests | Can module owners implement independently against these contracts? |
| [D — Implementation roadmap](v2/D-roadmap.md) | Small tasks, dependencies, milestones, gates, cutline, migrations | What can we implement next without broad cleanup? |
| [E — Evaluation plan](v2/E-evaluation.md) | Capacity A–F fixtures, correctness, metamorphic behavior, restart/failure checks, ablations, hosted gates | Does evidence appropriately change behavior, and does that improve outcomes? |
| [F — Research backlog](v2/F-research-backlog.md) | Verified references, prioritized methods, assumptions, latency and comparability requirements | Can a new strategy be tested without changing foundational modules? |

The [main audit](18-main-branch-audit-2026-10-10.md), [remediation plan](19-main-branch-remediation-plan-2026-10-10.md), and [branch review](20-remediation-branch-review-2026-10-10.md) remain supporting evidence. Their broad remediation queue is not a prerequisite project for V2. Document A assigns findings to the narrower V2 boundaries and distinguishes reviewed branch changes from main defects.

## Architecture decisions and implementation defaults

| ID | Recommendation | Reason | Status |
|---|---|---|---|
| ADR-01 | Add `negotiator.v2`; leave V1 module names in place | `evidence.py` and `policy.py` already exist; moving them first adds migration work without intelligence | Approved in principle; default selected |
| ADR-02 | Strict frozen Pydantic models plus Python Protocols | Pydantic already exists; domain stays independent of provider, database, and runtime implementations | Approved in principle; default selected |
| ADR-03 | One decision loop; serial case scheduling first | Limits orchestration risk while proving semantic adaptation; async RFQs have a separate admission gate | Approved in principle; default selected |
| ADR-04 | SQLite transactional event log, snapshots, and operation outbox | Atomic state/version/claim reservation/intent commit; repository already uses SQLite | Approved in principle; default selected |
| ADR-05 | Grounded LLM interpretation; deterministic selection first | Separates interpretation benefit from model ranking benefit; both hooks remain replaceable | Approved in principle; default selected |
| ADR-06 | Finite certified price candidates for relationship cases initially | Avoids dependence on the defective general inverse; all selected ticks are evaluated with official costs | Approved in principle; default selected |
| ADR-07 | Templates and canonical claims only for initial outward text | Clear confidentiality and factual validation; free-form writer is a later independent hypothesis | Approved in principle; default selected |
| ADR-08 | One resolved config/factory for supported CLI and Lab paths | Avoids the current guidance, policy, environment, and checkpoint activation differences | Approved in principle; default selected |
| ADR-09 | Preserve observations independently of assessments and strategy memory | Future research may need different interpretations; restart preserves attempted and refused exchanges | Approved in principle; default selected |

Alternatives and consequences are detailed in B and C. Approval of this document establishes scope and contracts, not readiness to run a hosted campaign.

## Tracking implementation

Update this file as milestones progress. Do not check off a milestone from source existence or a model rationale alone. Put evidence links in the relevant task row in D, then summarize here. Use `planned`, `in_progress`, `blocked`, `verified_local`, `verified_hosted`, or `deferred`; record a concrete dependency for `blocked`.

| Milestone | Outcome | Status | Evidence / owner |
|---|---|---|---|
| M0 | Assessment, architecture, contracts and executable handoff | Verified local preparation; architecture approved in principle | A–F, tests/fixtures/task handoff; production owner unassigned |
| M1 | Complete typed offline skeletal loop, effective config, persistent DecisionRecord and replay | in_progress | T1.1a–c hardened; four metadata DTOs and 40 consumed T1.1d exports verified_local; D1/D3/D4 complete, D2 partial; [D evidence](v2/D-roadmap.md) |
| M2 | Unified evidence resolution and prebuilt context | in_progress | T2.1 direct typed resolver and T2.3 cost_input verified_local; validated context DTO implemented; full builder/claim/estimate consumers pending; [approved concurrent A/B delivery](v2/implementation-order-addendum-2026-10-10.md) |
| M3 | Grounded capacity supplier interpreter | Planned | — |
| M4 | Capacity intents, certified candidates and interchangeable selection | in_progress | Oracle and direct package evaluator verified_local; batch/close evaluator and strategy pending |
| M5 | Durable validated serial negotiation loop and feedback | Planned | — |
| M6 | Controlled local comparison, Lab/config integration and funded performance evaluation | Planned | — |
| M7 | Additional categories, async scale and research variants | Deferred from first slice | — |

The M5 local vertical slice depends on M1–M4 and the execution gate, not on hosted performance or M7. Evaluation fixtures begin in M1, and runtime/state work can proceed alongside evidence and interpretation once the contracts are frozen. See D's dependency graph and named tasks.

For every implementation task, retain this completion record:

```text
Task / milestone / owner:
Contract and config schema versions:
Commit / checkpoint / data and prompt fingerprints:
Implemented behavior and deliberately deferred scope:
Local tests and trace / replay links:
Migration and restart evidence:
Hosted or inference authorization, usage, IDs; or not run:
Acceptance criterion met / unmet:
Known gaps, decision, rollback procedure:
```

Maintain a dated change log below. Contract changes require a new contract version and a list of affected consumers/tests; do not silently reinterpret old traces or checkpoints. Implementation detail may change while the authority and acceptance criteria remain fixed. If scope changes, amend the criterion before claiming completion and preserve the reason.

## Most important risks and open decisions

1. **Relationship economics in P10:** it has `secure_supply`, no executable alternative, and a supplier-health penalty. A no-estimate historical reproduction is useful but is not an uncertainty-aware procurement release. The first slice must explicitly evaluate validated estimate scenarios or declare estimates unavailable and limit its claim accordingly.
2. **Protocol evidence is incomplete:** authoritative round/deadline fields and idempotent-operation lookup may be insufficient. The gateway must preserve uncertainty and stop/resume safely; it cannot invent clocks or prove cancellation from a local timeout.
3. **Grounded text can still be commercially wrong:** exact quotes prove attribution, not entailment, approval authority, or willingness. Label uncertainty; test refusals, conditional clauses, role boundaries, and contradictions.
4. **Baseline distinction:** development starts at `4c905b1`; historical comparison is frozen at `3653046` with explicit config/source hashes and exact first payload. Its focused sixty tests pass, while development inherits four classified failures. See A §7; no remediation merge or V1 fix accompanies this plan.
5. **Limited real capacity evidence:** use P10 for legality and recorded behavior; use altered supplier replies as synthetic behavioral fixtures. Additional independent cases and held-out suppliers are required before a general capacity improvement claim.
6. **First-slice choices:** confirm the owner roles, approved provider/data destination for future model tests, estimate policy, and experiment budget before those dependent implementation stages. These are tracked decisions, not blockers to preparing the contracts and local fixtures.
7. **Schedule:** this plan does not promise full V2 before the repository's 11 October 2026 freeze. M7 and promotion remain separate work. No calendar estimate is credible until owners and scope are assigned.

## Executable handoff

- [Test catalog](v2/test-catalog.md): three suites, actual fixtures, expected assertions/failure conditions and owning tasks.
- [Expanded machine-readable test manifest](../tests/fixtures/v2/test-manifest.json): all 1176 collected parameter cases with executable assertions and owners.
- [Task specifications](v2/task-specs.md): exact paths/ports/imports/instructions/reuse/dependencies/acceptance/exclusions; small M1 subassignments.
- [Coding guide](v2/implementation-guide.md): required-prefix gates, replay/baseline commands and completion reporting.
- [Architecture compliance checklist](v2/compliance-checklist.md): objective review criteria with evidence.
- [First three copy-ready prompts](v2/first-three-prompts.md): T1.1a strict values/serialization, T1.1b grounded assessment/ports, T1.1c DecisionRecord/effective config.

The first three shared-contract assignments merge serially. Then complete remaining DTO batches and the typed codec; evidence, economics, interpreter with a fake provider, validator with injected ports and state work can proceed independently. M1 itself must pass the complete offline loop, persistence and reproducibility gates, not merely create interfaces. Richer interpretation, strategy, state recovery and launch integration remain subsequent milestones.

## Preparation verification — 10 October 2026

The new executable suite has **66 passes and 175 explicit UNIMPLEMENTED expected failures** across **241 cases**. Missing production modules account for the expected failures; present implementation defects fail normally. Expected-failure guardrails themselves are tested. Active checks cover actual P10 case preservation, exact independent kit arithmetic/nonmonotonic costs, frozen baseline metadata, raw input fault construction, fake port routing and positive/negative import guards. This does not claim that unimplemented components work.

**Ruff on tests/v2: all checks passed. Frozen historical V1 full first-message replay: exact match.** The same six legacy modules passed **60/60** in pristine exported historical main; current development had **56 passes/4 inherited failures**, classified in A §7. Repository-wide Ruff reports four inherited source lint errors (A §7); new tests/v2 lint passes. No fresh full-suite pass is claimed. All A–F links and expanded test/task references are validated in the handoff check; diagrams were not browser-rendered.

Files added/edited are planning documents and new tests/fixtures only. Existing production source, V1 tests, dependencies, runtime settings and experiment results were preserved. No hosted negotiation/model quota, remote fetch, publication or deployment was used. Additional transport/source/crash/launch tests are explicitly catalogued as task deliverables before those features are implemented; they are not claimed as current passes.

## Change log

| Date | Change | Evidence |
|---|---|---|
| 2026-10-10 | Initial A–F planning package; current-branch inspection and bounded offline checks | A §6; no production source, test, dependency or runtime configuration changes |
| 2026-10-10 | Refined approved architecture into frozen handoff; three executable suites, P10/relationship/record/baseline goldens, exact tasks, compliance guide and first prompts | 66 passed / 175 missing-component xfails; Ruff and frozen V1 replay passed; no production implementation |


## Remaining T1.1d contract handoff — 10 October 2026

From `a88bf86`, [C §8.9](v2/C-interfaces.md) and [task-specs D1–D16 prompts](v2/task-specs.md)
now define all remaining DTO fields, defaults, invariants and owners. [Roadmap evidence](v2/D-roadmap.md)
classifies 380 passes and 796 expected failures: new tests describe 160 missing concrete/union
exports without implementing them. Existing V2 passes and 120 component expected failures
are unchanged. Production T1.1d remains partial; this is a verified specification handoff.
