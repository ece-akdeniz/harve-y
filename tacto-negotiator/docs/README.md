# Start hacking

**Build Tacto. First target: one complete negotiation and an instrumented RFQ sandbox run.**
Do not begin by implementing every strategy or polishing a dashboard.

Team times are Europe/Berlin, Saturday 10 and Sunday 11 October 2026.

## First 15 minutes

1. Assign Runtime, Evidence and Evaluation/pitch owners; Samet owns Decision/integration.
2. Follow [root setup](../README.md). Custom prep/play/run/report commands now execute; serial remains the
   default, async is explicit. Current hosted results are in experiments/LOG.md.
3. Read [implementation gates](10-implementation-checklist.md) together. Agree on package,
   claim, thread-state and closing-proposal records before splitting up.
4. Runtime + Evaluation run D01 and the D02 timing probe. Decision builds full-cost checks.
   Evidence prepares supplier facts and validates units. Save observations, not assumptions.
5. Ask the [design questions](08-open-questions.md): queued RFQ calls, closing near the wave
   cap, price-unit normalization and jury criteria.

## First useful version

One custom case completes end to end. The coordinator exists from the first concurrent runner;
every closing path runs identical checks. Invalid/stale offers cannot be accepted; model work
has a bounded fallback; a request cannot be duplicated on retry. Costs and decisions are traced.
Hosted timing is measured. Then scale to multiple cases.

## Read by role

| Owner | Read first | First deliverable |
|---|---|---|
| Decision / Samet | 02, 03, 10 | Complete-package evaluator and closing policy |
| Runtime | 00, 02, 06, 10 | D02 clock evidence and safe coordinator |
| Evidence | 01, 02, 03 | Typed facts with supplier, part, units and dates |
| Evaluation/pitch | 04, 05, 07 | Baseline report, quota ledger and replay requirements |

## Document map

- [Coding-agent lab playbook](../LAB_PLAYBOOK.md): laptop setup and the tracked experiment workflow.
- [00 — Challenge contract](00-challenge.md): official rules, score, limits and schedule.
- [01 — Research](01-research.md): reproduced findings, estimates and hypotheses.
- [02 — Architecture](02-architecture.md): ownership, state, deadlines and interfaces.
- [03 — Playbook](03-playbook.md): hard checks versus policies to test.
- [04 — Experiments](04-experiments.md): quota, holdout and promotion criteria.
- [05 — Team and timeline](05-team-and-timeline.md): build order and milestones.
- [06 — Final runbook](06-final-runbook.md): release, preflight, freeze and recovery.
- [07 — Pitch](07-pitch.md): demonstrate judgment with measured evidence.
- [08 — Open questions](08-open-questions.md): organizer answers and resulting decisions.
- [09 — Risks](09-risks.md): failure modes and validation.
- [10 — Implementation checklist](10-implementation-checklist.md): actual scaffold gaps and gates.
- [11 — Pipeline and win plan](11-pipeline-and-win-plan.md): one-page order, gates and cut list.
- [12 — Measured improvement plan](12-measured-improvement-plan.md): full hosted coverage, P04 target,
  reproduced policy gaps and the next bounded experiment sequence.

- [13 — Staged experiments](13-staged-experiments.md): current implementation, four-run screening,
  conditional 52-session ceiling, stop gates and FAQ implications. Supersedes document 12's budget.

- [14 — Measured demo](14-measured-demo.md): two defensible replay stories and their limits.

- [15 — Azure lab hosting](15-azure-lab-hosting.md): stable App Service deployment, database
  migration, validation, team cutover, backup and cleanup.

- [12 — Experiment dashboard](12-experiment-dashboard.md): shared laptop-hosted dashboard,
  local experiment runners, comparisons, buffering and importing previous attempts.

- [13 — Agent experiment loop](13-agent-experiment-loop.md): immutable checkpoints, bounded
  comparisons, cited findings, recovery and safe local/recommendation restore.

- [15 — Evidence stage plan](15-evidence-stage-plan.md): prioritized data correctness, case-aware
  supplier signals, claim validation and gated experiments for the Evidence owner.

- [16 — Evidence context](16-evidence-context.md): implemented shared interface, local P01 export and hosted-run handoff checklist.

## Sources and evidence labels

- [17 — Independent inference setup](17-inference-setup.md): local credential placement,
  opt-in Lab probe and later validation commands; setup has not been executed or validated.
- [18 — Supplier knowledge and memory](18-supplier-knowledge-and-memory.md): current public
  facts, immutable conversations, feedback boundary and remaining integration work.
- [19 — Supplier learning loop](19-supplier-learning-loop.md): local data and run triggers,
  retryable feedback, bounded candidate drafts and reviewed promotion.
- [20 — Lab deployment handoff](20-lab-deployment-handoff.md): additive migration and
  endpoint checks for the shared server.

The custom arena runner loads [runtime negotiation guidance](../src/negotiator/AGENTS.md)
through `guidance.py` on every `negotiator play/run` launch. Its structured settings
are executed and hashed in the run trace; research prose alone does not implement
a new policy. See the root README for the distinction from the starter `arena` agent.

Audited kit and current lockfile: `1b5516bb95ef28e37f69aa446dc62168864bca53`.
[Source snapshot](https://github.com/tacto-ai/negotiation-arena-kit/tree/1b5516bb95ef28e37f69aa446dc62168864bca53).
Start with `brief/api.md`, `brief/brief.md`, `brief/submission.md`, `data/company.md`,
`data/README.md` and row-level provenance. Record upgrades and rerun relevant checks.
Resolve conflicting official statements with the desk; public jury weighting is still unresolved.

- **CONTRACT:** official rule/API, subject to recorded organizer clarification.
- **MEASURED LOCAL:** kit/data/simulator reproduction; not hosted persuasion evidence.
- **MEASURED HOSTED:** saved run IDs and configuration support the observation.
- **INFERRED / HYPOTHESIS:** plausible explanation or policy awaiting an experiment.
- **IMPLEMENTED:** code and relevant checks exist; a plan or scaffold test is insufficient.

Hosted sandbox observations are recorded in [the experiment log](../experiments/LOG.md).
They do not establish generalization, final readiness or a winning probability.
