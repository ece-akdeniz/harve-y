# V6 negotiation strategy LLM layer

Date: 11 October 2026. Status: **local opt-in implementation; no live provider or Arena validation yet**.

`configs/score-push-v6-strategy.json` enables `package_advice_mode: strategy-v1` for
single-supplier capacity and renewal negotiations. The deterministic V6 agent first
prepares its ordinary move on isolated draft state. The strategy reviewer receives
that move, the latest supplier messages, earlier buyer packages, bounded public
supplier notes, case requirements, and code-generated complete alternatives and
questions. It selects `keep`, a listed package ID, or a registered question ID.

The packaged [negotiation decision skill](../src/negotiator/skills/negotiation/SKILL.md)
instructs the reviewer to look for a current supplier constraint, preserve explicit
conditions, exchange concessions across the complete package, and abstain when an
alternative has no support. Its bytes and SHA-256 are recorded in the run trace.
The model returns a four-field JSON decision: ID, latest supplier message index,
exact source quote, and observation kind. It cannot write the outbound offer or
set an acceptance or walk-away action. Code checks the quote and interpretation,
refusals, term legality, full cost, fresh state, deadline reserve, and candidate
membership. Code renders the selected complete package or question. Failed or
late review retains the prepared move. The existing coordinator owns final closure;
the separate opt-in final-offer reviewer remains available for that stage.

The new contract is smaller than the earlier opening adviser contract that timed
out on the observed P10 practice. The config permits at most two calls and reserves
at most 16 seconds per session; each call has an eight-second bound. A call is
reserved in the assessment journal before dispatch so an uncertain restart cannot
repeat it. `strategy-shadow-v1` records recommendations without changing moves.
The LLM receives directions of commercial changes, not buyer cost deltas, targets,
reservation values, credentials, or post-run scores. Supplier messages and public
notes are treated as untrusted data.

Local verification: 96 focused strategy/advice/final/policy/launch tests passed,
including strict provider JSON, a legal package selection, registered question,
invalid evidence and provider timeout fallback, stale-state blocking, restart
accounting, default-config isolation, and loading the skill from a zipped package.
Ruff and `git diff --check` passed. The CLI launch test uses a fake Arena client;
it is not a live practice. No new provider or hosted Arena calls were made.

This is a bounded first implementation, not evidence of better negotiation scores.
It cannot invent a new package, phrase a novel free-text counter, or interpret every
possible supplier expression. The previous P10 eight-second opening timeout remains
a live risk until the shorter contract's provider latency is measured. The skill
does not override the independent final-offer risk policy.

The later [source-linked brief architecture](v6-supplier-brief-architecture-2026-10-11.md)
adds an offline semantic compiler and a bounded brief to both strategy and final
review contexts. Its local validation and provider-only compilation are recorded
separately; this original strategy-layer test record remains historical.
