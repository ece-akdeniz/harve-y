# V5 backbone with bounded negotiation intelligence

Date: 11 October 2026 (Europe/Zurich). Status: architecture with the first serial capacity slice
implemented locally. See [implementation and evidence](v5-intelligence-implementation-2026-10-11.md)
for the exact delivered scope, opt-in limits and remaining work.

Branch: `codex/v5-intelligence`, based on `77b42a4e5fa72bffe9d8c6705a8d76a249500aa6`.
V2 reference: `75241b550e566083febc392b76034e09f6c5bd91`.
Isolated worktree: `/tmp/harvey-v5-intelligence`. The original V2 checkout is unchanged.

## Decision

Keep PackageAgent/v5 as the economic and execution backbone. Add an adviser that understands the latest supplier reply, selects a better code-costed trade when justified, and helps communicate the approved move. The system must remain a complete V5 negotiator when inference is disabled, unavailable or rejected.

V5 already has model assistance and a restricted package adviser; extend these seams. Avoid a second orchestrator, a second closing authority, or a wholesale V2 merge. Agent roles are useful boundaries, but do not need separate model calls or an autonomous-agent framework.

The first release uses one bounded reasoning call per eligible supplier update. The normal path remains capable of negotiating without that call. A separate optional writer comes later only if it improves outcomes enough to justify latency and validation work.

## Runtime flow

```text
Owned supplier history + public case evidence
                    |
          V5 prepares its baseline move
          and code-costed alternative packages
                    |
          Combined reader / trade adviser
          (one bounded call; optional)
                    |
          Code admits or rejects the advice
          and selects one complete move
                    |
          Template message + approved claims
                    |
          Existing guards, fresh closing checks,
          deadline check, exact journaled submission
```

Urgent closing, expired computation allowance and unresolved writes bypass advice. The same case coordinator owns all accept/walk decisions. Advisers have no Arena client, credentials, journal access or authority to commit a move.

## What stays and what transfers

| Keep from V5 | Adapt selectively from V2 |
| --- | --- |
| PackageAgent case policies, anchors and concession schedules | Bounded model admission, cancellation and late-result isolation |
| Official arithmetic, supplier-cost scenarios and alternative comparison | Typed response contracts and precise admission diagnostics |
| Trade generation, evidence claims, forecast attachments and claim pacing | Supplier-scoped citations and explicit uncertainty |
| Serial/async runners, wave guards and prewarming | Trace fields distinguishing model advice, admitted advice and fallback |
| Existing closing evaluator, guards and submission ownership | Independently reconstructed message/term consistency checks |
| Existing Lab experiment workflow and source identities | Terminal/publication recovery mechanisms only where a demonstrated gap remains |

Do not transplant V2's fixed candidate fallback, conservative clarification-then-close policy or no-claim renderer over V5's richer strategy. Do not cherry-pick `75241b5` wholesale: it includes a large, interdependent V2 implementation. Port small contracts and behaviors with focused tests, preserving V5's existing interfaces.

## Three roles, one decision owner

### 1. Reader: understand what changed

Read the latest supplier message plus a compact supplier-specific history. Return supported objections, explicit refusals, conditional trades, questions, and changes since the last acknowledged buyer move. Every extracted item references an actual message/span. Preserve conditionals and distinguish a preference from a hard constraint; a quoted phrase alone is not proof that an interpretation is correct.

Initially combine this role with trade advice in one structured response. Do not copy all old messages through the model on every turn. Code supplies current standing terms and acknowledged buyer packages directly. If a condition cannot be interpreted reliably, retain it as uncertain and keep the V5 baseline.

### 2. Trade adviser: choose a useful response

Before inference, V5 generates the baseline and a small bounded set of complete, independently costed alternatives through existing trade/package-adviser functions. Include meaningful alternatives such as preserving 30-day payment instead of requesting 60 days, exchanging duration for price, or revising a delivery requirement when permitted. Candidates must be dynamically constructed from the actual case and history, not a static seed universe.

The model returns `keep` or an approved candidate ID, cited reasons, and an optional registered question/evidence ID. It does not return arbitrary executable actions or invent prices. Let it request a named tactic where useful; code owns that tactic's numbers, limits and materialization.

Internal policy compares the selected package with the baseline and executable alternative. The first version admits only alternatives within an explicit code-owned cost envelope. Default to no worse complete evaluated cost; later allow a bounded, configured concession envelope if experiments show that it unlocks useful trades. Otherwise the adviser may be unable to solve refusals that require a real concession. Do not treat nominal cost as the whole objective when relationship estimates apply.

Hard rules remain hard: fields, must-haves, disclosure, current offers, clocks and closing ownership. V5's concession schedule and package choices are strategic defaults. A cited, cost-checked alternative may override them under the envelope; do not make every V5 heuristic an immutable rule that leaves the adviser powerless.

No separate model critic or recursive research loop in the first release. Missing candidates are logged as a capability gap, not repaired through unlimited extra calls.

### 3. Communicator: explain the approved move

First release: extend V5's deterministic message composition with supported acknowledgement and trade-explanation blocks selected by the admitted advice. Bind all numerical statements, package descriptions, claims and disclosures to approved code-generated content. This gives the supplier an actual response without requiring a second inference call.

Later, an optional model writer may arrange approved blocks or rewrite non-commercial connective text. It receives only the outgoing package, approved public facts and acknowledgement material—not internal targets, reservation costs, alternative costs or urgency. Protect the whole message's meaning: checking numerical equality alone does not catch invented promises, approval or exclusivity. If the allowed form cannot be validated, use the deterministic message.

Keep private reasoning separate from outgoing text. Never forward an adviser rationale directly to the supplier.

## Small integration surface

- `agent.py`: preserve the baseline decision path; add a single advice seam before final enrichment/rendering.
- `model_assist.py` and `package_advisor.py`: unify overlapping inference into one reader/adviser response and extend beyond capacity cases behind configuration.
- A small `advice.py` module if needed: request/response types, admission and call-budget ownership. Avoid spreading a new DTO hierarchy across the application.
- `replies.py` / existing history helpers: source-linked observations and acknowledgements.
- Existing `_offer`, evidence and claim functions: deterministic communication from the selected move.
- `policy.py` and CLI/Lab config: explicit opt-in mode, allowed case types, total call/time allowance and concession envelope. Existing V5 defaults remain the comparison control.
- Runner: one absolute deadline and bounded concurrent advice slots across suppliers; no per-stage deadline reset.

Important implementation trap: generating a V5 move currently updates fields such as `prev` and some policy bookkeeping. Advice must not leave state describing a discarded baseline or record an unsent claim as sent. Audit these mutations first. Stage decision changes until selection/submission ownership is established, or use a narrowly scoped decision draft and apply only the chosen changes. On acknowledgement, rebuild authoritative package history from server evidence. Do not run `decide()` twice to generate baseline and candidate arms on the same mutable agent.

## Failure and memory semantics

An advice failure selects the already prepared V5 move, freshly validated against current state. It never selects an unrelated minimum package, silently accepts the opening quote, or forces early closing solely because the model failed. If state changed during inference, discard advice and recompute safely within the original deadline; otherwise use existing closing/recovery behavior.

A writer failure keeps the chosen package and falls back only its wording. A stale observation, external cancellation, expired dispatch window or uncertain POST blocks sending through the existing execution owner. No adviser retries Arena requests. Any V2-derived revocation mechanism must be integrated with the existing runner rather than become a competing owner.

Keep a compact per-supplier record: last processed message identity, supported objections and conditions, previously rejected packages, outstanding question, selected tactic and subsequent observed response. Rebuild essentials from owned history on restart. Supplier beliefs expire or are revised when contradicted. Cross-run learning remains an explicit reviewed-memory feature, not automatic promotion of speculative observations.

## Deadline-focused implementation sequence

1. **Protect V5 behavior (30–60 min target).** Replay saved observations with intelligence disabled; assert identical outgoing actions. Inventory state mutations, package-adviser seams, async restrictions and existing timing budgets. Preserve baseline configuration and source identity.
2. **Ship reader/adviser integration (90–120 min target).** One call, a small useful candidate set, cited interpretation/selection, code-owned cost envelope, exact baseline fallback, and no new dependency. Start with one case family; do not enable all policies at once.
3. **Improve communication (30–45 min target).** Supported acknowledgement and trade explanation, term/claim consistency tests, template fallback. Defer arbitrary prose generation.
4. **Verify then measure (45–60 min local target).** Replay refusal and payment-trade examples, test timeout/staleness and state isolation, then prepare one bounded tracked comparison if applicable experiment authority and time remain.

Timeboxes are engineering targets, not guarantees. With only two hours, finish baseline parity plus a narrow candidate-selection adviser; keep existing email templates. Do not add separate reader, strategist, critic and writer network calls under time pressure.

## Evidence required before claiming improvement

- Intelligence disabled preserves V5's actions on identical recorded states.
- Timeout, malformed output and foreign citations preserve a valid baseline without extra submissions or leaked state.
- A paired change in supplier evidence produces an appropriate different recommendation where the candidate set supports it; harmless wording changes do not randomly change economics.
- Refused packages are recognized, conditional requests retain their conditions, and valid holding strategies require an explicit reason rather than accidental repetition.
- Selected terms, body, claim references and attachments agree; adversarial supplier instructions cannot change authority or disclose private data.
- Multi-supplier advice remains isolated and cannot exhaust the entire execution window through queued work.
- Report transport success, advice admission, actual changed actions, timeouts, latency, inference usage, complete deal cost, no-deal outcomes and score separately.

Use V5 alone versus V5+advice under the same case/source/config conditions. Isolate message-only experiments because changed text can change supplier responses. Historical V5 practice scores and V2's repaired D01 opening-price agreement are not a controlled comparison. Neither an admitted model answer nor one agreement proves commercial improvement.

This branch now includes the opt-in serial capacity adviser described in the implementation report.
The broader architecture remains a proposal. No dependencies were added and no hosted inference,
Arena session, Lab publication, push or deployment was performed.
