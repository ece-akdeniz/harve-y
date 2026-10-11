# V6 source-linked final-offer LLM review

Date: 11 October 2026. This began as an opt-in local implementation. The default
`configs/score-push-v6.json` remains unchanged. Its first byte identity was
`e71233c7445ba770dc093576d6f279d31851a1bb6b749481e5d23b0333d96412`;
the manifest now identifies the later exploratory-counter candidate. The earlier
P2–P6 record describes the preceding candidate identity.

`configs/score-push-v6-final-advice.json` enables `final_advice_mode: select-v1` on the
serial capacity/renewal adviser, with an explicit 0.20 walk-risk bound. The existing
package-selection contract remains separate. When its prepared move would accept a
supplier's final offer, the final reviewer sees the current supplier reply and term
sheets, earlier supplier replies, current case options and must-haves, bounded
supplier-scoped public dossier facts and notes, and source-valid observations reconstructed from
the owned assessment ledger. The LLM returns only `keep` or a code-generated complete
counter ID and an exact quote from the latest supplier reply. Neither model rationale
nor a numerical claim enters the buyer's outbound message.

The counter menu uses cheaper legal supplier alternatives. For the saved P10 final
reply, the supplier's offered 54-day variant is outside the case's 35/42/56-day
options; the menu contains a **buyer counter** at the seller's EUR31.90 price with a
legal 56-day lead. This is not represented as a supplier promise or an acceptable
standing sheet. Code checks the exact source quote, field relevance, explicit
refusals, full cost, must-haves, one-counter limit, per-update reservation,
20-second closing reserve and pre-dispatch freshness. The provider has eight seconds
at most; the opening and final adviser share the session's eight-call/24-second
reservation ceiling. Timeout, malformed output and invalid evidence retain the
prepared accept. Final review attempts and admitted observations are journalled;
unknown attempts are charged on restart.

An active counter additionally requires a comparable executable outside quote or
current contract and the independent final-review risk screen. P10 has no such
alternative. Its LLM review can log a cited recommendation, but the code must still
accept its valid standing offer. `shadow-v1` can be used to measure recommendations
without changing any action. The reviewer is disabled outside the initially supported
serial single-supplier path and is skipped under the wave guard or with too little time.

Local verification: 68 focused final/advice/policy tests passed with the supplied
data package, including legal P10 normalization, scoped ingested notes, strict
provider schema, no-alternative veto, active finite-alternative counter, provider
fault, restart accounting and stale-thread blocking. Ruff and `git diff --check`
passed. A broader run reached the previously known sandbox stall in the async
worker-crash test; no broader pass is claimed. The public data package exposes four
notes for P10's supplier. A fake-provider dry run with the actual scoped dossier
and saved final reply built a 4,117-byte context with three notes, three history
rows and one legal cheaper counter.

One tracked P10 practice session was subsequently run with this config (run
`59c67205-59ca-4dba-b187-b1de4eeb0c39`; full evidence in `experiments/LOG.md`).
The final reviewer selected the legal EUR31.90/56-day buyer counter in 2.50 seconds,
but the risk gate rejected dispatch because P10 has no comparable executable outside
alternative. The agent accepted EUR33.80/42 days and scored 0.5546564482, matching
the prior live diagnostic. The opening capacity adviser separately timed out at 8.01
seconds. This one run demonstrates recognition, not a score gain or a measured
general failure rate.

## Exploratory counter after the live diagnostic

The opt-in `configs/score-push-v6-final-explore.json` sets `explore-v1` and disables
opening adviser calls for this isolated final-decision test. It preserves the V6
opening package and reserves model time for the smaller final-review contract. The
default and the prior `select-v1` config still retain the standing offer when there
is no executable outside alternative.

`explore-v1` makes the downside explicit from the case's published buyer fields:
`need_per_year * horizon_years * fallback_unit_price * (1 + fallback_risk_pct/100)`.
This is the case-priced cost of covering all need after no deal, **not** a supplier
quote or a prediction that spot supply will be available. It never replaces the
`alternative` field or the regular closing evaluator. A legal, cited counter needs
positive cost gain, at least 20 seconds of closing reserve, the one-counter budget,
and a no-deal loss no greater than the config's explicit 40% of standing cost.
The review logs the possible loss and break-even walk probability; the actual walk
probability remains unknown. This is an exploratory risk preference, not a claim of
positive expected value. Missing fallback inputs or loss beyond the bound retain
the standing offer. Fresh pre-dispatch term, source, deadline and cost checks remain.

For the saved live P10 supplier reply, a local fake-provider replay selected and
pre-dispatch validated the EUR31.90/56-day counter with zero opening provider calls.
The replayed thread omits PDF defaults, so its exact cost differs from the live
session; the decision path and terms were checked, not a predicted Arena outcome.
With its case-priced no-deal scenario, the break-even walk probability is about
8.6%. There is no calibrated supplier walk estimate.

One later tracked P10 practice run (`6ddfcb54-5f8c-49e7-89ac-7e35cd46a64e`)
sent the legal counter, received the supplier's agreement, and accepted it. Score
was 0.6472939821 with zero Arena timeouts, versus 0.5546564482 in the prior
diagnostic that accepted the standing offer. The opening adviser made zero calls;
the final reviewer completed in 2.90 seconds. See `experiments/LOG.md` and the
original run for exact terms, costs and trace. This is one exposed practice reply,
not a calibrated walk estimate or evidence of general reliability. The exploratory
config remains opt-in and unpromoted.
