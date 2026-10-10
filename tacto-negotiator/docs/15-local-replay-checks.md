# Local response-policy checks — 10 October 2026

This is an experimental, opt-in decision change. It has not been run against hosted suppliers,
promoted to the shared lab recommendation, or shown to improve scores. No model is integrated.

## What changed

- `free_concessions`: preserve the baseline ability to adopt supplier-proposed terms that have
  no additional buyer cost, including P05's 35-day delivery. Only permitted terms are considered.
- `rfq_close_guard`: an open, nonleading supplier's local convergence waits while the leading
  supplier remains workable. The hold ends before the buyer deadline; missing timing retains
  conservative closing. It does not assume that more bargaining will produce savings.
- `response_types`: consider a supplier's explicitly priced alternative, a cheaper historical
  package, or a quoted index clause explicitly required for the current duration. A historical
  package is only a counterproposal and always requires a new standing offer. Inverse pricing
  keeps proposed complete cost no higher than the scheduled proposal or current standing offer.

Each switch respects the existing two-switch, three-moves and twenty-second limits. Supplier
economics estimates still disable inverse-cost response trades because monotonicity is unverified.
The new flags default off. `configs/candidate.json` is unchanged. The local experiment config
is a diagnostic combination, not a proposed all-case deployment configuration.

## Evidence and limitations

Eight curated decision prefixes cover six known defects/hypotheses and two preservation checks.
Only messages available at the selected decision are supplied to the agent. Gold annotations,
later replies, final scores, historical Cbest and competitor information are not policy inputs.
Remaining time is a controlled boundary-test input, not a reconstructed latency measurement.

The initial check expected P08's zero-deadband clause. Inspection showed the supplier's quoted
5% deadband alternative had lower complete cost, so the annotation was corrected to permit
any already-quoted valid clause. This is a development regression set, not unbiased model scoring.

The broad scan reads 24 saved sessions, with 134 open-thread prefixes and 77 unique inputs.
Each prefix is evaluated independently; later historical replies are never treated as responses
to changed proposals. RFQ single-thread scans do not reconstruct concurrent state. A separate
timestamp-aligned P05 snapshot exercises the losing-supplier close condition.

**Historical fidelity is unverified.** Saved messages lack downloaded quote text, so supplier
standard defaults are unavailable. The independent review reproduced this discrepancy in P05:
reconstructed opening payments were 90 days versus the recorded 30/45/30 days. These are
synthetic guard checks, not faithful reproductions of those negotiations. Existing attachment
text is preserved when supplied, but missing defaults are never inferred from future offers.
Before using replay results for policy selection, recover the contemporaneous quote documents
and verify the baseline proposals against the recorded journal. No baseline-fidelity claim or
score estimate is supported by the current checks.

No local check predicts future supplier behaviour. P02 still uses the existing aggressive price
schedule: considering a 30-day exchange is not proof that its requested discount is attainable.
Final-offer risk remains unchanged. Unanswered supplier questions and evidence materiality remain
future work; this patch does not claim to solve all interpretation weaknesses.

## Reproduce without arena or model calls

From this candidate's `tacto-negotiator` directory, set `ARENA_DATA` to the existing public data
package. Keep credentials out of the candidate. Supply the tooling checkout's local run directory:

```sh
uv run --locked python tools/replay_decisions.py --all-saved \
  --runs-root /absolute/tooling/tacto-negotiator/experiments/runs \
  --output /absolute/ignored/report.json
uv run --locked pytest -q
uv run --locked ruff check .
```

The replay tool blocks network connections during agent decisions and exits nonzero on failed
annotations, invalid proposals, increased proposal cost or missing batch evidence. Trace output
records source hashes, source-session provenance, configuration and considered/selected trades.

## Jev / Clef decision

Both are plausible interpretation challengers, not demonstrated improvements here. TypeSafe
recommends atomic typed questions; Cloudflare's Clef-Flash provides a compatible decision API
and open 9B weights. The published local example uses CUDA. This Mac has 16 GiB RAM; we did not
download weights, install a model runtime, obtain credentials or make model calls.

Sources checked: [TypeSafe introduction](https://docs.typesafe.ai/introduction),
[Clef-Flash model card](https://huggingface.co/Cloudflare/clef-flash), and
[Cloudflare model documentation](https://developers.cloudflare.com/workers-ai/models/clef-flash/).

Before considering a model, freeze atomic interpretation labels and evaluate held-out conversation
groups, including contradictions and fixed-term requests. Split by session/case, not individual
turns from the same conversation. Calibration, abstention, latency and constraint violations matter
alongside label accuracy. These eight hand-selected regressions are insufficient for model selection.

## Next hosted gate

No hosted session is authorized by this document. After local review, one separately approved
experiment should change one policy group and specify the decision expected to differ. Inspect
that complete replay before releasing another session. Use the shared lab workflow and current
recommendation for any campaign; do not relabel historical imports as verified campaign outcomes.

## Full local dialogues and fault injection

`tools/local_simulation.py` runs the real async coordinator and PackageAgent against the
kit's in-memory supplier simulator, with socket connections blocked. Both arms have identical
package configuration; only `response_types`, `free_concessions`, and `rfq_close_guard` differ.
This comparator is not the historical hosted baseline commit or a claims-enabled production policy.

The three normal cases (S01 price increase, S02 RFQ, S03 renewal) finish at identical scores
in both arms: 82.90, 72.78 and 88.56 on a 0–100 display scale. Three S02 fault scenarios
(lost reply, injected stale close, compressed wave deadline) also finish validly for both arms.
All twelve scenario/arm combinations complete with must-haves satisfied, no thread timeouts,
no duplicate session opens and no unresolved journal requests.

The compressed wave scenario naturally produces one stale-close 422 in each arm while a reply
is in flight. The coordinator refreshes and accepts the current offer before the cap. The first
harness run marked this as failure because it required zero request rejections; the reviewed
check explicitly allows at most one recovered close-only 422 for that scenario and separately
reports `strict_zero_rejections: false`. No production policy or recovery code was changed.
Both the original and reviewed reports are retained locally. These repeats are diagnostic,
not independent statistical samples.

The kit supplier uses a fixed price script and ignores the economics of payment, liability
and clauses. Its cases omit quality/raw-material negotiation and its benchmark permits free
non-price terms. Therefore these scores cannot rank policies for hosted P02/P08/P11 or establish
persuasion benefits. Synthetic refusal trajectories complement, rather than validate, that model.

```sh
ARENA_DATA=/absolute/public/package uv run --locked python tools/local_simulation.py \
  --output-dir experiments/runs/local-sim-UNIQUE
```

Use a fresh output directory; the harness refuses to overwrite a dialogue's evidence.

### Stateful synthetic refusal checks

`tests/test_response_trajectories.py` contains five complete bounded decision trajectories:
three payment discounts around complete-cost break-even, and two liability-package branches
(retained versus withdrawn). Only the starting prefix is historical; each subsequent supplier
reply is generated from the actual proposal using explicitly synthetic package-price floors.
The agent is reconstructed from history at every decision. Tests block socket connections.

All five preserve permitted fields, fixed P11 payment, bounded package switches and fresh
standing-offer acceptance. They expose strategic weaknesses despite those safety passes:
P02 continues with a very aggressive scheduled price after refusal; P11 may explore an
unpriced zero-chargeback package after the previous alternative is withdrawn. This is not
proof those moves fail on hosted suppliers, but does show that the response patch alone
is insufficient to establish a good adaptive bargaining policy.

Next local hypotheses: make repeated refusals alter the proposed concession; distinguish a
rejected price from an unavailable package; track whether another trade would add information
before spending a move. Test these against both flexible and stubborn synthetic opponents.
Do not tune exclusively to a synthetic supplier's invented floor or report these as arena gains.
