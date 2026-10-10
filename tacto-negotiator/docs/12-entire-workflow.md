# Entire Graph and Brain: implemented workflow and next features

Graph v0.4.0 and Brain v0.1.0 are installed locally. The CLI's help is authoritative:
this Graph release uses `search`, whereas the online main-branch guide uses `query`.

## Use now

- Graph locates evidence selection, its caller in PackageAgent, and covering tests:
  `entire graph search --repo . --head --profile full --query 'supplier evidence index rejection and offer selection'`.
- Brain retains experiment conclusions and their session IDs. Retrieve relevant lessons
  before changing a policy with `entire brain brief 'improve negotiation argument selection' --no-semantic --json`.
- Keep quantitative results in `tacto-negotiator/experiments/LOG.md`, which is reviewable
  in Git. Brain facts summarize that evidence; they do not replace it.
- Initial setup uses `--no-backfill --no-daemon --agent none`: no autonomous model
  extraction, no recurring service or token spend. Refresh after meaningful commits.
- Uncommitted user settings must never be committed just to satisfy Brain's clean-tree
  requirement. Build committed code from a temporary local clone with the same origin.

## Planned features, not implemented

1. **Experiment recall:** retrieve earlier policies, scores, failures and source commits
   before spending practice quota. Success: a new tuning session can explain the failed
   broad-index experiment using its actual replay IDs and qualified conclusions.
2. **Policy change impact:** use Graph to identify callers and relevant tests before
   changing scoring, acceptance or evidence selection. Current code and tests remain
   authoritative; the graph can miss dynamic calls.
3. **Evidence-linked pitch:** link a problem, code change, test and hosted replay for each
   claimed improvement. Do not present installed tooling or a single run as a performance gain.
4. **Session-derived lessons:** once Codex hooks are approved and sessions are captured,
   review and retain lessons from those sessions. Model-backed extraction is a separate,
   optional step; it is not enabled by this setup.

Brain is developer project memory, not the buyer's live supplier-state engine. Negotiation
history and recipient-scoped citation state still come from the arena's case threads.
The production agent must not consume spectator leaderboard data during the final.

## Known limitation

`entire status` reports seven Codex hooks awaiting approval via `/hooks`. Installation
alone does not prove that this desktop chat is being captured. Initial Brain setup found
zero sessions to distill. Verify a captured session before claiming session-based memory.

Official sources: https://github.com/entireio/entire-graph and
https://github.com/entireio/entire-brain.
