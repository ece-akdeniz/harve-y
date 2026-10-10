# Azure lab hosting implementation plan

**Goal:** Make the existing lab deployable to a stable Azure Linux VM and document a safe database cutover.

**Architecture:** Keep the current authenticated server and SQLite schema. Add managed-host environment defaults at the CLI boundary and a repository startup file. Run it as an unprivileged systemd service on a VM-managed disk, behind Caddy HTTPS. Teammates publish over the existing API.

## Tasks

1. Add failing CLI tests for managed-host environment defaults and explicit local overrides.
2. Implement strict environment parsing without changing existing local defaults.
3. Add a versioned startup file using the installed module and environment-backed configuration.
4. Add an Azure VM runbook covering free-service selection, static DNS, HTTPS, service isolation, source deployment, migration, verification, teammate cutover, backup, rollback, patching, and cleanup.
5. Record the infrastructure change in the experiment log; it consumes no Arena quota and changes no negotiator behavior.
6. Run focused tests, the full locked Python suite, Ruff, and the lab UI test suites.
7. Create a consistent ignored database backup and tracked-source archive for the initial Azure transfer, inspect both, and keep secrets out of all artifacts.
