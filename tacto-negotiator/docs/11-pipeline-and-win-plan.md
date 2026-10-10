# 11 - Pipeline and win plan

One page to run the hackathon from. Details live in 00-10; this file sets the order, the gates,
and what we cut when time runs out. Roles follow `AGENTS.md`: Decision (Samet), Runtime,
Evidence, Evaluation/pitch. Times are Europe/Berlin.

## How we win

Two separate prizes need two separate proofs.

| Prize | What decides it | Our proof |
|---|---|---|
| Tacto track | Mean normalized score over the Live Final cases; zero failed cases | Reliable runtime + complete-cost decisions + non-price levers + verified claims |
| Overall (jury, criteria unconfirmed) | Judgment, clarity, demo | One measured replay where the agent recognised a supplier constraint and found a package better for us **and** viable for them, with every figure traceable |

Pitch line: *Our agent finds better procurement agreements - and shows the evidence and
trade-offs behind every decision.* Report measured arena results only.

Score priorities, in order (each step only after the one before is safe):

1. **No zeros.** Every case closes before the cap with a valid, must-have-compliant deal or a
   justified walk. One lost case costs more than any tactic gains.
2. **Never accept worse than the alternative** (complete cost, standard terms resolved).
3. **Non-price levers.** Contract length, incoterm and payment terms move C by the same order
   as several percent of price (S03: 24 -> 12 months +EUR 288k, DAP -> EXW +EUR 111k, payment
   60 -> 14 +EUR 40k vs price -1 % -EUR 39k). Trade what is cheap for us and valuable to them.
4. **Verified claims** against unjustified increases (index proxy below the ask: P01, P13).
   Never cite where the index supports the supplier (P02, P14).
5. **RFQ competition:** parallel threads, deliberate valid rival-quote disclosure.
6. **Supplier modelling:** traits and cash value for relationship goals.

## Pipeline

```text
OFFLINE (before any clock)
  package (+ Sunday overlay) -> dossiers -> typed facts -> candidate claims (pre-verified)
  case -> fixed terms, must-haves, alternative, goal -> candidate package grid -> C for each

PER CASE (one coordinator, one worker per thread)
  open session -> fetch quote PDFs (defaults) -> opening package(s)
  loop per reply:
    authoritative state (offer, status, rounds, seconds_left)
    -> interpret reply (model, bounded; template fallback)
    -> policy proposes: send package(s) + claims | consider accept | consider walk
    -> guards validate (schema, must-haves, C < alternative, claim checks, no leaks)
    -> coordinator serialises sends and every close (incl. agreed and deadline fallback)
    -> journal (move id, payload) -> POST -> trace
  close margin: max(90 s, slowest round + 15 s) before wave cap

AFTER
  trace.jsonl -> report (scores, C components, failures) -> replay viewer -> pitch
```

## Build order and gates

No stage starts until the gate before it passes on hosted or sandbox runs.

| Stage | Owner lead | Done when (gate) |
|---|---|---|
| G0 Baseline | Runtime + Evaluation | Official naive agent ran D01, D02; D02 clock/timeout behaviour recorded; quota ledger started |
| G1 Safe single case | Decision + Runtime | Custom agent closes D01 end to end; complete-cost evaluator, must-have and alternative checks on every close path; journal + idempotent retry; template writer only |
| G2 Safe concurrency | Runtime | 10 cases in parallel, 0 timeouts, 0 duplicate moves, coordinator owns accept and walk; finishes with margin |
| G3 Beat baseline | Decision + Evaluation | v1 beats E0 mean and worst case over >= 2 runs x 10 cases (**confidence checkpoint**) |
| G4 Evidence | Evidence | Claim bank: 0 contradicted claims on 10 cases; units and dates validated |
| G5 Levers + model | Decision | Lever packages / MESO tested as experiments (keep only measured gains); model writer with bounded fallback, p95 within budget |
| G6 Supplier model | Decision + Evidence | Traits and supplier cash value used for relationship goals; measured, not assumed |
| G7 Sunday data | Evidence | Overlay ingested, claims rebuilt, regression run green |
| G8 Release | Runtime | Preflight on final machine, tagged commit, runner started before 12:00 freeze |

Pitch track runs in parallel from G3: Evaluation/pitch builds the replay viewer from the same
trace, not a separate demo path.

## Critical path (Saturday 13:00 -> Sunday 13:00)

| Time | Target | Cut if late |
|---|---|---|
| Sat 13:00-14:00 | G0 | - |
| 14:00-17:00 | G1 | model writer (templates suffice) |
| 17:00-18:00 | G2 | - (never cut) |
| 18:00 | G3 checkpoint | if no: fix the gap, skip G5/G6 tonight |
| 18:00-21:00 | G4, replay viewer skeleton | trait classifier |
| 21:00-01:00 | G5, G6 experiments | G6 entirely |
| 01:00-07:00 | sleep in shifts; holdout runs only from committed configs | new features |
| Sun 08:00-09:00 | G7 | - |
| 09:00 | preflight; choose final config by measured score | - |
| 10:30 | feature freeze | - |
| 11:30-12:00 | G8: tag, submit, start runner; hands off | - |
| 12:00-13:00 | Live Final: watch spectator screen as humans only | - |
| 13:00 | pitch if top 10 | - |

## Decision rules

- **Promote a change** only if it improves mean score on the same case set without raising
  failures, over >= 2 runs. Log it in `experiments/LOG.md`.
- **Revert** anything that adds a timeout, a guard bypass or a contradicted claim, regardless
  of score.
- **Quota:** follow the budget in `04-experiments.md` (protected reserve of 46 sessions for
  regressions, refresh and preflight). The window is rolling 24 h; there is no midnight reset.
- **Model:** choose the cheapest model that holds score; tail latency beats eloquence.
- **Unknown rule:** ask the desk, record the answer in `08-open-questions.md`, then code it.

## Pitch (5 + 2 min), prepared from G3 on

1. Problem: procurement negotiations hide cost in terms, not price (one slide, one number).
2. Live replay of one case: reply -> interpretation -> packages with C -> guard checks ->
   claim with source -> deal. Every figure clickable to its fact or term sheet.
3. The judgment moment: supplier constraint recognised, package better for both.
4. Measured results: Live Final score, failure count, baseline comparison.
5. Limits stated plainly: simulated suppliers, partial cost proxies, one dataset.

## Not doing

Training or fine-tuning, new frameworks, a separate demo agent, savings claims beyond arena
results, any agent access to events, screen, leaderboard or results endpoints.
