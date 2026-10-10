# Nebius lab deployment

The [Deploy y/agent lab](../../.github/workflows/deploy-nebius-lab.yml) workflow runs on every push to `main` and can also be started manually. It runs the lab server tests and Ruff with locked dependencies, archives tracked `tacto-negotiator` source, then streams it over SSH to the existing Nebius VM. The VM installs locked dependencies into a new release, atomically switches `current`, restarts the dashboard, and restores the previous release if the health check fails. The SQLite database and lab credentials stay under `/var/lib/y-agent-lab` and are never part of the archive.

The workflow needs repository secret `NEBIUS_LAB_SSH_KEY`. Its value is the dedicated private key held by the VM owner; do not commit it. The corresponding public key is installed for the `lab-deploy` account with `restrict` and a forced command. That account cannot open an SSH shell or read the dashboard database or credentials. Its only sudo permission is restarting `y-agent-lab.service`. The VM host key is pinned in `.github/nebius-lab-known-hosts`.

The public dashboard is https://66-201-6-11.sslip.io/. Teammates need the separate `LAB_PASSWORD`; the CI key is solely for deployment. If a push fails tests or deployment, the current dashboard continues serving its previous release. The GitHub Actions run shows the tested and deployed commit.
