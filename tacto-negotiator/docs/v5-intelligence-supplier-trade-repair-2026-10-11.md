# V5 supplier-aware trade repair

11 October 2026. Local candidate on `codex/v5-intelligence`, base
`77b42a4e5fa72bffe9d8c6705a8d76a249500aa6`. Opt-in configuration:
`configs/score-push-v5-intelligence.json`. Default V5 remains unchanged.

## Problem and scope

The [P10 trial](v5-intelligence-p10-trial-2026-10-11.md) selected €28.48 instead of
the scheduled €28.34 with identical operational terms. The combined adviser lacked
the supplier dossier, misclassified opening quotation statements as objections, and
had an unsupported price-only concession in its menu. The supplier then returned
€33.80 at 42 days as a final offer, which the existing closing policy accepted.

The historical 56-day package-adviser run logged a better outcome (€31.80, score
0.6550996 versus 0.5546564), but used a different model/wording and was not a matched
comparison. It motivates testing a delivery-for-price exchange, not a score claim.

This change repairs operational trade selection first. Final-offer handling remains
separate: the existing final-counter calculation found zero gain for its available
candidate and infinite walk-away loss without an outside alternative. The adviser
still bypasses final offers. This change therefore does not cause another counter
after the saved €33.80 final offer.

## Implemented behavior

- Load the same supplier-scoped public dossier used by the legacy adviser. Project
  only document ID, date, kind, subject and text, with explicit supplier attribution.
  Exclude foreign supplier notes and private dossier estimates. At most 12 notes;
  oversized documents are omitted whole rather than truncating conditional language.
- Feed those notes into both candidate generation and inference. Present allowed
  options, hard must-haves and preferred delivery separately. Full-cost computation
  remains local; buyer ceilings, reservation values and evaluation scores are absent.
- Remove price-only candidates, including otherwise affordable current supplier sheets.
  Preserve complete cost-neutral exchanges: the saved P10 opening admits €27.62,
  23,400 units/year, 24 months, 56 days. Its lower price compensates for the cost of
  extending delivery beyond the 42-day preference; volume still meets the hard minimum.
- Version the response schema to `capacity-advice-v2`. Observations cite exact current
  message text or public note text and identify addressed fields. A selected exchange
  requires current-message support for every changed non-price field. Selection from
  `stated_terms` additionally requires a cited historical constraint/trade covering those
  fields. Historical notes cannot alone replace current-message support.
- Require any higher-price exchange to match a complete current supplier sheet and
  be supported as a conditional trade. Preserve the cost envelope, fresh validation,
  exact fallback, staged bookkeeping, deadline reserve and deterministic rendering.
- Trace the cited note IDs and commercial changes alongside the cited observations.

The configuration key remains `package_advice_mode: combined-v1`; it selects the
integration path, while the response contract identifies the revised evidence schema.
Legacy `PackageAdvisor` transport and response schema are unchanged.

Exact citations and field coverage establish provenance and structural relevance.
They cannot prove that a model interpreted a statement correctly, preserved every
semantic condition, or predicted supplier willingness. The revised prompt distinguishes
quoted terms from objections, gives current replies precedence over historical notes,
and directs the model to keep when a useful exchange lacks support.

## Local evidence

**146 focused tests passed** using the existing Python environment, including nine
additional cases for price-only exclusion, irrelevant/partial trade support, foreign
document citations, unsupported quotation-based changes, conditional price increases,
saved P10 exchange economics, dossier loading and unchanged final closing.

The provider transport is mocked. The saved P10 test injects a valid delivery-trade
response; it proves that the corrected input/candidate/validation path works, not that
the live model will choose it. A separate assertion checks the actual saved final
history against the unchanged closing policy; it is not a simulated reply to the
changed opening. No counterfactual supplier response or score is fabricated.

Fixture: `tests/fixtures/p10-capacity-advice-repair.json`, derived from run
`fddd79d8-9fe0-48c9-bdd9-1d5ebd600195`. It contains the first three conversation
messages, the scheduled opening and four public supplier notes, without post-run
evaluation scores. The original run, source manifest and evidence remain intact.

Legacy and disabled-advice replay outputs match the untouched baseline at all 20
decision points (P05: 12, P18: 5, synthetic P10: 3). Each output SHA-256 is
`3f65e86c962c0f5b96a43a9bf5646f9bfd0deba24995c5abe8004d5a81815ead`.
New outputs: `/tmp/v5-advice-repair-current-replay.json` and
`/tmp/v5-advice-repair-disabled-replay.json`. Scoped Ruff and diff whitespace checks
passed. Before the user-requested push, the full suite completed with **867 passed,
4 failed**: two campaign tests require the unavailable `uv` executable, and two async
wave-cap tests raise `IncompleteSession`. Both wave-cap failures reproduce on the
untouched V5 baseline as well as the candidate. Full-repository Ruff passed. These
failures remain outside the serial capacity-advice change.

The implementation/repair stage used no hosted inference, practice sessions,
external publication, push or promotion. The user subsequently authorized committing,
pushing this candidate and one new tracked P10 practice session.
The [completed rerun](v5-intelligence-p10-repair-trial-2026-10-11.md) used commit
`b789414c2d9b4164d3c4e37e3c61644bdc21d0ce`: the adviser timed out, exact V5 fallback
executed, and the outcome remained unchanged. Live trade selection remains unverified.
The next commercial check requires a separately budgeted, source-frozen P10 comparison
with consistent model/settings. Final-counter risk policy should be evaluated in a
separate candidate so its effect can be distinguished from better opening trades.
