# V5 combined adviser: live P10 capability trial

11 October 2026 (Europe/Zurich). **Execution passed; commercial improvement was not demonstrated.
Do not promote this candidate from this result.**

The user authorized one practice trial and selected P10 to exercise the serial capacity adviser.
Exactly one session ran, with no session rerun. The resulting Lab record was uploaded only after
the user explicitly authorized the initially rejected external publication.

| Result | Observed value |
| --- | --- |
| Lab run | `fddd79d8-9fe0-48c9-bdd9-1d5ebd600195` |
| Arena session | `5ec8db9d34cc06ae` |
| Case / supplier | `case:P10` / `sup:70410` |
| Outcome | Deal; ended; must-haves satisfied |
| Score | 0.5546564481864089 (55.47/100) |
| Closing terms | EUR 33.80/unit, 23,400 units/year, 24 months, 42-day lead time |
| Complete deal cost | EUR 1,597,720.80 |
| Opening complete cost | EUR 1,932,492.18 |
| Elapsed / buyer actions | 35.64 seconds / one proposal and one acceptance |
| Timeouts / unresolved writes | 0 / 0 |
| Practice quota | 345 before, 344 afterward; server limit 750 |

## What the model actually did

The configured model was `gpt-6-sol`, using the existing OpenAI-compatible endpoint settings.
One `capacity-advice-v1` call completed in about 4.11 seconds: 1,135 reported input tokens and
269 output tokens. One response was admitted and changed the move. No separate interpreter
call, fallback or additional model call occurred. Eight inference seconds were conservatively
reserved from the 24-second session allowance. No monetary estimate was calculated.

V5 prepared EUR 28.34/unit, 23,400 units/year, 24 months and 42-day delivery. The adviser selected
EUR 28.48 with all non-price terms unchanged. Code evaluated complete cost at EUR 1,347,084.96,
below the permitted EUR 1,353,894.1728 ceiling. The deterministic message accurately described
those terms. The supplier then issued a final standing offer at EUR 33.80 with the same volume,
duration and delivery. The shared V5 closing evaluator accepted it without another model call.

The supplier also offered EUR 31.70 with 54-day delivery and 19,890 units/year. Its prose said it
could not supply the requested delivery/volume, contradicting the first structured sheet. The
runtime used the authoritative complete standing sheet; it did not interpret prose as a binding
replacement. The recorded closing terms satisfy the case's must-haves.

## Commercial diagnosis

The adviser cited statements of the supplier's initial quoted terms and labeled them objections.
It used those citations to justify a price-only concession without addressing the supplier's
capacity/volume/delivery issue. Provenance and cost checks passed, but those checks do not establish
that the chosen response is useful. This is an observed limitation of the current admission contract.

The historical V5 summary lists P10 at 0.6551; this trial scored about **10.04 percentage points
lower**. That historical number is not a paired control with this trial's model, messages and
supplier responses. The difference does not prove that the adviser caused a regression, but
provides no evidence for promotion. Agreement alone is insufficient.

The next hypothesis should target admitting a commercially relevant response: distinguish an
initial quote from an objection, and require a price-only concession to have a specific cited
reason or reciprocal condition. Preserve the exact baseline as the control and isolate wording
effects from economic changes. Do not enable the candidate broadly or spend another session
without a separately authorized comparison. No post-trial strategy change was made to the tested
source, and the existing V5 default remains active.

## Source and evidence

- Base: `77b42a4e5fa72bffe9d8c6705a8d76a249500aa6`; dirty source was captured including new files.
- Saved source-patch SHA-256 verified:
  `953365dfebe83ebb8359404ef34cecef0a0bfdc4f848c16fcfc029806742f481`.
- Policy: `configs/score-push-v5-intelligence.json`; complete config and model identity are
  retained in the run. Eight attempts maximum, 24 reserved inference seconds, 1% per-turn
  cost envelope, one practice session. Only one call/session was consumed.
- Local root: `/tmp/v5-capacity-live-2026-10-11/`; `traces/trace.jsonl` contains the observations,
  prepared/selected messages, cost check and closing rationale. The run directory retains
  `run.json`, `source.patch` and the exact three-operation journal (session, proposal, acceptance).
- Lab destination: `https://66-201-6-11.sslip.io/`. Completed-record upload succeeded; authenticated
  GET returned HTTP 200 and its parsed record exactly equals the local final record. Verification
  is saved in `lab-retrieval.json`. The published record contains terminal result, owned transcript,
  model-advice metrics and source/config metadata; the detailed local trace and patch remain local.

Automatic approval review initially rejected external publication because authorization for that
payload/destination was not explicit. The run proceeded with local-only tracking. The user then
explicitly authorized publication; the already completed record was uploaded without opening
another session.
