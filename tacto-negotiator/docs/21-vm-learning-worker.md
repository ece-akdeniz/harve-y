# Persistent VM learning worker

The existing y/agent lab runs `y-agent-learning.service`; this is a Python process on
the VM, independent of Codex and the owner's laptop. Its durable goal is 99/100 on
every original candidate repetition in a reviewed suite. This narrow suite target
does not establish generalization to unseen suppliers or the final competition.

`completed records → cited feedback → permitted configuration proposal → immutable
checkpoint → local tests → publication → budgeted async comparison → gates → teammate review`

The worker polls every 30 seconds. Goal state and change events live in `worker_goal`
and `worker_events` in the existing SQLite database. `/api/runs` returns its current
state as `worker`; the existing Experiments page displays one compact status line.
Campaigns remain rows in All experiments, opening their original attempts and gates.
There is no separate website. Original run and conversation records are preserved.

Configuration: `/var/lib/y-agent-lab/worker/config.json`. Credentials are in a separate
0600 `secrets.env` consumed by systemd. Source objects, supplied data, frozen checkpoints,
locked dependency cache, and migrated campaign journals stay on the VM. Never put a
password in a URL. Do not open the source HTML through `file://` as the dashboard.

The initial family is `ece-competitive-anchor-20261010-01`, with the already approved
12 sandbox sessions. Reservations are charged even after failure. The worker cannot
create or enlarge a family, cannot select practice, and does not promote. More budget
requires separately recorded user authorization and a configured, approved family.
Unsupported hypotheses remain engineering work; this process does not invent code changes.
Checkpoint publication requires repository credentials on the host. Missing credentials,
offline cache, evidence, or source objects produce a visible retryable state before starts.

For a migrated ambiguous start, explicit recovery verifies the original executor identity,
result and sole unresolved open intent. It repeats only that same `X-Move-Id` and payload,
saves a durable receipt, and never adopts a different running session on 409. It runs the
original checkpoint into a separate recovery journal if needed. Reconciliation appends
owned ended evidence; the original failure remains ineligible for promotion. A second
uncertain recovery does not silently rerun the negotiation.

Run management (owner SSH):

```
sudo systemctl status y-agent-learning
sudo journalctl -u y-agent-learning --since '10 minutes ago'
sudo systemctl stop y-agent-learning
sudo systemctl start y-agent-learning
```

One OS lock prevents concurrent VM worker instances. Campaign locks and server leases
protect execution. Stop any prior executor before migrating its durable state; do not
run the same campaign from two machines. Keep the recommendation pinned for each session.
The configured Sunday 11 October 2026 12:00 Europe/Berlin freeze blocks new starts while
allowing existing evidence to be read. Restart the worker after deploying a new worker
revision; changing the dashboard symlink alone does not reload a running Python process.
