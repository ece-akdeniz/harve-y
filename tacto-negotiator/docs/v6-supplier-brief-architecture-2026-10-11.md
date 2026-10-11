# V6 source-linked supplier briefs

Date: 11 October 2026. Status: **implemented locally and populated from the
permanent Sunday data; opt-in negotiation policy, three exploratory hosted
practices completed**.

## Data path

The permanent `tacto-negotiator/data/package` and sibling `release-sunday` load
through `VersionedPackage`. `supplier_briefs.py` collects supplier-scoped documents,
news, text-bearing citable facts and structured negotiation-history rows, plus
market documents/news. Current
case facts and approved memory can be added at runtime. Every record carries a
source ID, source type, supplier/part scope, date, text and truncation marker.
The source collector is independent of the Sunday filenames; a new citable document
or news record enters the same pipeline. Numeric terms and official term sheets
continue through the deterministic evaluator.

`negotiator prep --briefs` builds an extractive brief for every detailed supplier
without a provider call. `negotiator prep --brief-model --brief-supplier sup:...`
uses one bounded provider call per named supplier (maximum 12 names per command)
to propose observations, tentative tactics and conflicts. The model receives only
bounded source records. Code admits each observation only when its exact quote
appears in the named, supplier-scoped source. Tactics must cite admitted
observations. Unsupported items are dropped independently. An output with no
admitted observation is not saved as a model brief.

Briefs are stored under `data/briefs/<data-sha256>/<supplier>.json`, with the
source digest and model response. On load, code verifies the data version,
source records and citations. Missing, stale or edited model output falls back to
extractive source excerpts. A normal `prep --briefs` preserves valid model briefs.
The permanent package currently has 46 briefs: eight model compiled for suppliers
with new Sunday evidence and 38 extractive. A future data version gets a separate
directory; it cannot silently reuse old model advice.

The local candidate source identity is
`f25874c9414f8f8bb7b18d1af0845f5ba85a6bfc0415810c355dc2f25e6fc4c4`.
The combined config SHA-256 is
`c1083b1d1ecd671383d856cd7d2f994b74ab587c79fbb9c1474daec1de340c1e`;
the package data identity is
`00317624303f28b4cbae883fd0554d9ce88779fb40b33de7f262e6784e0b5980`.

## Negotiation path

The guarded serial negotiator obtains a brief for the current supplier and filters
part-specific records to the current case. Its runtime view is bounded to current
case evidence, a few source excerpts, up to eight cited observations, three
tentative tactics and three conflicts. The strategy LLM receives this view beside
the latest supplier reply, prepared V6 move and code-generated complete menu.
The existing packaged negotiation skill says that a newer direct supplier reply
or current case fact overrides historical brief tactics. The strategy LLM still
returns only a menu ID and an exact quote from the **latest supplier reply**;
the brief alone cannot justify a changed offer. Code rechecks legality, full cost,
source support, current history and time reserve before sending a move.

The separate final-offer reviewer receives the same bounded brief, but can only
choose from its legal counter menu and must cite the latest final reply. The
final risk screen and single coordinator still own accept, counter and walk-away.
`configs/score-push-v6-briefed.json` is an opt-in combination of strategy review
and the previously authorized exploratory final-counter policy. The default V6
configuration is unchanged; the three-case screen below does not identify a
commercial effect from the brief.

## Local evidence and limits

The semantic Mairhofer brief recognized centrally set 2027 prices, the stated
non-price topics still open for discussion, and the change from the older pricing
process. The Konvertek brief records a conflict between older chip-shortage news
and new normalisation news. The model's suggested tactics are hypotheses, not
supplier commitments or executable instructions. Eight model briefs were admitted
after 10 provider-only calls: one earlier empty response, one response rejected
before per-item admission was added, then eight successful calls. A later P10
practice measured one strategy call at 5.36 s and one final-advice call at 4.57 s,
with no timeout. This single-case result does not establish the latency percentile
gate or prove that offline brief compilation cures an opening timeout.

The implemented collector covers the currently available supplier documents,
news, text-bearing package facts, negotiation-history records, current case text
facts and approved memory.
It does not read arbitrary files outside the versioned Arena package or unapproved
historical sessions. Current structured quotes, contract terms and scorecards
remain in existing factual/economic paths. Of 46 suppliers, 38 have extractive
briefs; model interpretation for them requires explicit provider compilation.
The strategy reviewer remains limited to serial, single-supplier capacity and
renewal cases. In the three hosted practices (P11, P07, P10), all cases reached
valid deals with zero timeouts. P10 exercised both reviewers with an extractive
brief for `sup:70410`, and scored 0.6473, matching an earlier exploratory-counter
run. None of these sessions exercised a model-compiled brief; see the experiment
log for run IDs and results.

Validation completed in two local batches: 154 brief, decision, agent, release,
dossier, claim and context tests, plus 42 package-adviser, memory, question and
assessment tests. One regression confirms a historical brief quote cannot
authorize a new counter without support in the latest supplier reply.
Ruff and diff checks passed. The separate runner suite stalled
on its first slow-reply simulator test under this sandbox and was interrupted;
no runner-suite pass is claimed.
