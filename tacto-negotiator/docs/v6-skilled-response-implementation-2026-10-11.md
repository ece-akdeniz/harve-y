# V6 role skills and model-written buyer responses

Date: 11 October 2026. Status: **implemented in the isolated V6 worktree; local
tests passed; no hosted practice or provider call for this change**.

## Runtime roles

The brief compiler loads `src/negotiator/skills/brief/SKILL.md` from the installed
package. Its instruction distinguishes direct supplier statements, third-party
reports, dated quantitative facts and inference. It keeps conflicts visible and
requires source-linked observations. New model briefs record the compiler skill hash.
The eight earlier model briefs were created under the previous inline prompt and
remain source-validated; they have no new compiler-skill hash.

The strategy adviser loads `src/negotiator/skills/negotiation/SKILL.md`. The expanded
skill describes active listening, calibrated questions, objective standards,
private alternative discipline, approved anchoring, conditional reciprocal trades,
logrolling, and multiple equivalent approved package options.
It requires the adviser to read current supplier language and dated source-linked
context alongside the approved quantitative terms, allowed options, must-haves,
volume, delivery, payment and complete commercial changes. Historical context does
not authorize a new move without the latest supplier reply.

The final-offer adviser loads `src/negotiator/skills/final/SKILL.md`. It treats the
current final reply and standing sheet as the primary evidence, reviews only legal
counter IDs, and leaves downside and closing authority to code. All three skills are
versioned package resources; the provider request checks their content hashes.

## Opt-in buyer prose

`configs/score-push-v6-skilled.json` adds `llm_response_mode: skill-v1` to the
previously tested briefed candidate. This setting requires the live serial strategy
and final advisers. Their existing bounded calls now return a `body` field alongside
the selected ID and citation; no second live model call is added. The strategy call
can write the buyer email even when it keeps the prepared package. The final call
can write the counter email when code admits the selected counter. Both see the
supplier's latest message, scoped brief, case constraints and approved terms.

The attached term sheets, legal menu, economics, verified claim decorator and
coordinator remain authoritative. Code admits model prose only when it is bounded,
does not contain private leak phrases, unsupported numeric values or source IDs,
promises, URLs, or a missing selected question. Numeric values in prose must match
the corresponding field of the selected term sheet. If the prose fails, code sends its prepared text while retaining
an otherwise valid package decision. Verified evidence sentences may still be
appended by code after the model-written main email. When no adviser is eligible or
a provider call fails, the existing deterministic message is sent.

The current writing scope is **serial, single-supplier capacity and renewal cases**,
the same scope as the live strategy adviser. Other case types and the async RFQ runner
keep their existing messages. Accept and walk-away remain coordinator actions, not
model-written email. This candidate has not been measured in Arena and is not
promoted to the default V6 configuration.

## Provenance and verification

Source manifest: `experiments/v6-skilled-source-manifest.json`, candidate identity
`b8f4e66e5e92fa72be8c3e04a72af9e6e11268710d7615cd7adc374c92c10369`.
Config SHA-256: `d87eb7bbb5c06447714bf0391fec6830589d4fd207fcb8898feb913f39bd3eb6`.
The three resource hashes are recorded in the source manifest and runtime metrics.

Focused adviser, brief, policy, agent, evidence and context tests passed locally,
including model-authored keep and counter messages, fresh dispatch validation,
unsafe-prose fallback, strict provider schemas and package-resource loading from a
zip archive. These checks establish wiring and local safety gates, not a commercial
improvement. The full hosted latency and outcome effects remain unmeasured.
