# Combined-latest-updates compared with the V2 plan

Reviewed 10 October 2026. Remote refreshed successfully. Inspected
`origin/codex/combined-latest-updates` at **11815351a38dd55ed7d5eda68fddcca18c6f1142**.
Its common ancestor with the V2 development branch is historical main
`3653046bce6dd7cbbeffe00ecf5dfd9c3edbc0ab`; it does not contain the remediation
branch used by [the V2 plan](21-negotiation-v2-plan-2026-10-10.md).
Both pin the official kit to `1b5516bb95ef28e37f69aa446dc62168864bca53`.

**Conclusion: yes, most of the problems motivating V2 remain.** This branch
implements additional useful interpretation, evidence feedback, data diagnostics,
and supplier memory. It is consequently ahead of the plan's inspected checkout
in some features, but it does not supply V2's independent validation, unified
economic/evidence resolution, durable strategic state, or reproducible common
launch boundary. The plan's descriptions should be updated if this becomes the
development baseline; its architectural recommendation still applies.

## Findings against A §4

All source references below describe the reviewed remote SHA, **not the current
working-tree version of those files**.

| Plan finding | Remote branch result | Evidence |
|---|---|---|
| F1 inverse pricing | Partially improved; ordinary regression from the remediation checkout is absent. Relationship inversion remains a bounded sampling heuristic. | `economics.py:40–93` searches 513 grid points plus references, refines and checks rounded prices. An ordinary €181,200 target returns 15.00. This is useful certification, not proof that every feasible relationship interval will be found. |
| F2 terminal truth | Rejected-close fallback improved, but success semantics remain unsafe. | `runner.py:539–544` raises `IncompleteSession` for a still-live server. However `runner.py:536–537` calls `_end(reply.get("result", reply))` after any successful close response without requiring authoritative terminal evidence. `runner.py:208–209` trusts a previously journalled result before reconciliation. |
| F3 async supervision | Worker exception propagation and task cleanup implemented; runtime readiness unverified. | `runner.py:568–585` watches worker completions and cancels/gathers tasks in `finally`. Bounded async simulator checks did not complete in this review; see verification limits below. Do not carry over the plan's exact remediation-loop diagnosis as if the implementations were identical. |
| F4 quote standards precedence | **Still present.** | `evaluator.py:20–26` prefers a nonempty estimate standard wholesale. Probe: estimate 60/FCA plus current quote 30/DAP returns 60/FCA. |
| F5 cost overlays | **Still present.** | `dossiers.py:127–143` loads SQL first and excludes case facts with an existing ID. Probe: case replacement of `cost:310010` with 999 still returns SQL unit cost 132.64 for `sup:70110`. |
| F6 explicit data fallback | Base-path fix present; release-path gap remains. | `dossiers.py:36–43` rejects an invalid explicit base path. `VersionedPackage` inherits official release discovery; passing a nonexistent explicit release silently returns `release=None`. |
| F7 infeasible packages / final validation | **Still present; stronger than in the remediation checkout.** | `optimizer.py:51–79` returns its initial package when no combination satisfies must-haves. Probe requiring lead ≤1 returns lead 35. `guards.check` remains `NotImplementedError`; `play.py:149–154` and `runner.py:520–525` transmit without that validator. `economics.evaluate` validates selected economic calls, not every outgoing action. |
| F8 uncertain operation ownership | Partly improved, still incomplete. | Exhausted uncertain retries raise and retain the pending intent (`runner.py:340–342`). However closed/moved threads or changed standing offers cause abandonment without operation-specific proof (`runner.py:304–324`). Durable serial POST ownership is not implemented by ordinary `play_case`. |
| F9 awaited lock | **Still present.** | `runner.py:352–358` holds the state lock across awaited proposal work. Model pre-reading moved outside the lock, but the general proposal await remains inside it. |
| F10 real deadlines | Partly improved; core gap remains. | Refresh uses session observation time before thread fetch (`runner.py:260–292`). Serial still invents a fresh trade deadline each iteration (`play.py:133–135`); async open/send still derive a fresh window from local receipt (`runner.py:227–230,461–463`). Buyer work exceeding the limit only produces a warning. |
| F11 limiter scope | Local spacing improved; team-key scope unresolved. | `client.py:54–66` serializes limiter callers, but `AsyncArena` creates its own limiter unless supplied one (`client.py:88`). This does not establish one limit across processes/hosts/serial clients. |
| F12 round accounting | **Still present.** | Proposal/runtime decisions continue using buyer-message history and `moves_left`; uncertain reconciliation infers progress from buyer counts (`runner.py:319–322`). No shared authoritative operation/round projection replaces this. |
| F13 restart strategy | Persistent cross-session memory added; active negotiation state remains incomplete. | `agent.py:142–145` keeps previous packages, counter budgets, rival challenges and first-seen times in memory. History reconstruction in `propose` is conditional on `self.policy` (`agent.py:391–402`). Cross-session learning is distinct from replaying the current case after a crash. |
| F14 units, uncertainty, payment | **Still present in active legacy paths.** | `dossiers.py:156` selects the first part; `:190–191` only notes a price-unit mismatch. `full_cost_range` is produced without scenario selection in the ordinary evaluator. `optimizer.py:124–127` retains the approximate payment threshold: 0.666667% versus exact 0.671141% for 60→30 days at 8%. New `supplier_costs.py` adds a separate, unit-matched estimate path rather than unifying resolution. |
| Config divergence | Improved checkpoint coverage; common factory still absent. | Checkpoints now support policy/model/memory settings. CLI uses `RuntimeGuidance` (`cli.py:86,99`); Lab factories/worker instantiate `PackageAgent` directly (`lab/runner.py:142`, `lab/worker.py:124`). Checkpoint schema does not freeze `conditional_exchange` or package-adviser activation. |
| Trace/report divergence | **Still present.** | `_offer` mutates `prev` and logs before transmission (`agent.py:258–261`); serial adviser can subsequently replace its package (`agent.py:375–383`). `report.py:108` derives decisions from those logs; no transactional final acknowledged-action record replaces them. |

## What this branch does add

- `ModelAssist` reads supplier text with quote-grounded structured observations,
  bounded input and provider timeouts. It is a functioning interpreter, so the
  plan's description of the inspected checkout as lacking a general interpreter
  cannot be copied unchanged to this branch.
- Claim selection reacts to contradicted references and index objections through
  `replies.py` and `evidence.py:81–92`. The statement that supplier claim feedback
  never affects selection is no longer accurate here.
- Payment requests can add code-generated package variants. Capacity/delivery
  signals add clarification wording (`agent.py:242–255`); they do not drive the
  persistent capacity-intent/candidate/feedback loop specified by V2.
- Versioned ingestion records hashes, conflicting versions and missing-table
  warnings. It does not resolve SQL/case/release economics consistently.
- Reviewed memory snapshots can influence bounded initial package preferences;
  Lab adds supplier knowledge, learning, feedback and policy-candidate records.
  These are reusable components, not evidence of complete active-case recovery.

## Difference from the plan's four inherited regressions

The following tests all passed on this remote branch:

- `test_evaluator.py::test_price_for_cost_inverts_total_cost`
- `test_evaluator.py::test_final_offer_gets_at_most_one_counter_then_close`
- `test_evaluator.py::test_final_offer_lets_open_rival_beat_it_once`
- `test_context.py::test_agent_obtains_context_and_preserves_offer_and_close`

Those four failures are specific to the remediation development baseline described
in A §7. They should not be used as evidence that this remote branch fails those
same examples. Conversely, passing those examples does not remove the unresolved
runtime, data and architectural findings above.

## Verification and limits

Source was exported to `/tmp/combined-branch-review-20261010`; the existing checkout
and its production files were not switched or edited. Tests used that export's
`src` via `PYTHONPATH`, the existing Python environment, and explicit pinned kit
data at `/home/ugur/harve-y/negotiation-arena-kit/data`. Installed official cost
source matched the pinned submodule bytes.

- Six focused suites (evaluator, context, package adviser, guidance, dossiers,
  cost-neutral delivery): **67 passed**.
- Expanded focused checks adding fresh-data economics, reply feedback and model
  assistance, excluding its async completion test: **93 passed, 1 deselected**.
- Ruff on exported `src/negotiator`: **all checks passed**.
- Direct probes reproduced quote precedence, ignored case cost replacement,
  infeasible default-package return, approximate payment threshold and silently
  omitted explicit release. Ordinary inverse reproduction returned 15.00.
- Full-suite attempt hit its **60-second process bound** without finishing.
  It showed failures/errors before timing out; exported trees also lack Git and
  repository/submodule layout needed by some Lab tests. These are not presented
  as a clean, attributable full-suite defect count.
- `test_runner.py::test_two_thread_rfq_slow_replies_no_timeouts` did not finish
  within an **8-second process bound**. The model async completion test also
  stalled in the earlier focused run and was interrupted. These are incomplete
  runtime checks in this environment, not a proven diagnosis of one shared hang.

No hosted Arena sessions, inference calls, campaign budget, publication, or
deployment were used. Current working-tree edits observed during the review were
preserved. Only this review document was added to the working tree.
