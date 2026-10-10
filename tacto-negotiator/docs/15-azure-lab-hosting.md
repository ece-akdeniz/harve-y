# Azure hosting runbook for the experiment lab

This deploys the authenticated lab to one Ubuntu Azure VM. Negotiations still run on each teammate's laptop. The VM stores run records, checkpoints, findings, and the recommended version; it does not receive Arena or model credentials.

Azure App Service is deliberately excluded: Microsoft documents that its Linux filesystem is a mounted network share that cannot provide SQLite's exclusive locks. A VM-managed disk preserves the existing SQLite WAL semantics.

## Resource shape and cost

Create the VM from Azure's **Free services** page and select a Linux VM size explicitly marked eligible for the Azure for Students offer. B1s has historically received 750 included hours per month; Azure may instead show a newer eligible burstable size in a region where B1s is unavailable. Select the qualifying managed-disk size shown by the offer.

Use one VM, one managed OS disk, and one static Standard public IPv4 address. The VM and disk may be included, while the public IP can consume credit. Confirm the full estimate shown by Azure before pressing **Create**. Configure a budget alert and delete the resource group when the lab is retired.

## Create the VM in Azure Portal

1. Open **Home → Education → Free Services** and choose the eligible Linux virtual-machine offer.
2. Select the **Azure for Students** subscription and create resource group `y-agent-lab-rg`.
3. Name the VM `y-agent-lab`, choose Ubuntu Server 24.04 LTS x64, and select a nearby region with an offer-eligible size.
4. Use SSH public-key authentication. Save the generated private key locally; Azure cannot show it again.
5. Select the offer-eligible managed OS disk. Encryption at rest remains enabled.
6. Under networking, create a **static Standard public IPv4** address. Assign a unique DNS name label such as `y-agent-lab-TEAMSUFFIX`; Azure shows the resulting hostname, for example `y-agent-lab-TEAMSUFFIX.westeurope.cloudapp.azure.com`.
7. Allow inbound SSH only from your current public IP. Allow inbound TCP 80 and 443 from the Internet. Do not expose port 8000.
8. Review the displayed estimate, eligible free-service markers, region, disk, and public-IP charge before creating the resources.

## Prepare tracked source and database locally

From a verified `main` checkout, create a tracked-source archive. `git archive` excludes ignored `.env`, lab secrets, databases, local runs, and caches:

```bash
git archive --format=tar.gz --prefix=tacto-negotiator/ \
  --output=/tmp/y-agent-lab.tar.gz main -- .
sqlite3 experiments/dashboard.sqlite3 ".backup 'experiments/dashboard.sqlite3.azure-backup'"
sqlite3 experiments/dashboard.sqlite3.azure-backup "PRAGMA integrity_check;"
```

The integrity check must print `ok`. Stop the laptop dashboard immediately before the final backup so the cutover has a clear no-write boundary.

Copy both files using the VM key and hostname Azure created:

```bash
scp -i PATH_TO_VM_KEY /tmp/y-agent-lab.tar.gz \
  experiments/dashboard.sqlite3.azure-backup AZURE_USER@AZURE_HOST:/tmp/
```

## Install the lab on the VM

Connect over SSH, then install OS packages and `uv`:

```bash
sudo apt-get update
sudo apt-get install -y caddy curl git sqlite3
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo install -m 755 "$HOME/.local/bin/uv" /usr/local/bin/uv
```

Create a locked-down service account and deploy the tracked archive and database:

```bash
sudo useradd --system --home /opt/y-agent-lab --shell /usr/sbin/nologin y-agent-lab
sudo install -d -o y-agent-lab -g y-agent-lab \
  /opt/y-agent-lab /opt/y-agent-lab/app /var/lib/y-agent-lab
sudo -u y-agent-lab tar -xzf /tmp/y-agent-lab.tar.gz -C /opt/y-agent-lab/app
sudo install -m 600 -o y-agent-lab -g y-agent-lab \
  /tmp/dashboard.sqlite3.azure-backup /var/lib/y-agent-lab/dashboard.sqlite3
sudo -u y-agent-lab env HOME=/opt/y-agent-lab \
  /usr/local/bin/uv sync --locked --no-dev \
  --project /opt/y-agent-lab/app/tacto-negotiator
sudo -u y-agent-lab sqlite3 /var/lib/y-agent-lab/dashboard.sqlite3 "PRAGMA integrity_check;"
```

The repository archive contains the top-level `tacto-negotiator` directory, so the project path above is intentional.

Create `/etc/y-agent-lab.env` with mode `0600`; use the existing lab password and upload token, and do not add Arena or model keys:

```bash
sudo install -m 600 -o root -g root /dev/null /etc/y-agent-lab.env
sudoedit /etc/y-agent-lab.env
```

```dotenv
LAB_PASSWORD=EXISTING_LAB_PASSWORD
LAB_UPLOAD_TOKEN=EXISTING_LAB_UPLOAD_TOKEN
LAB_HOST=127.0.0.1
PORT=8000
LAB_DB=/var/lib/y-agent-lab/dashboard.sqlite3
LAB_SECURE_COOKIES=1
```

Install this systemd unit as `/etc/systemd/system/y-agent-lab.service`:

```ini
[Unit]
Description=y/agent experiment lab
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=y-agent-lab
Group=y-agent-lab
WorkingDirectory=/opt/y-agent-lab/app/tacto-negotiator
EnvironmentFile=/etc/y-agent-lab.env
ExecStart=/opt/y-agent-lab/app/tacto-negotiator/startup.sh
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/y-agent-lab

[Install]
WantedBy=multi-user.target
```

Make the secrets file private, start the service, and verify it only listens on loopback:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now y-agent-lab
sudo systemctl status y-agent-lab --no-pager
curl -fsS http://127.0.0.1:8000/ >/dev/null
```

## Enable public HTTPS

Replace `/etc/caddy/Caddyfile` with the Azure hostname and loopback proxy:

```caddyfile
AZURE_HOST {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8000
}
```

Validate and reload Caddy:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo journalctl -u caddy -n 50 --no-pager
```

Caddy obtains and renews the public TLS certificate. DNS must resolve to the static public IP, and inbound ports 80/443 must be open for certificate issuance. Keep port 8000 closed in Azure.

## Verify and cut over teammates

Before changing team configuration, verify all of the following:

- `https://AZURE_HOST` loads without a certificate warning and login survives refresh;
- the prior `Baris Test` run and score are visible;
- the loop page shows the existing checkpoints, findings, and recommendation;
- an authenticated read works from a laptop;
- one existing locally saved snapshot syncs without opening an Arena session.

Then update each laptop's ignored `.env`:

```dotenv
LAB_URL=https://AZURE_HOST
LAB_UPLOAD_TOKEN=THE_EXISTING_UPLOAD_TOKEN
LAB_AUTHOR=TEAMMATE_NAME
```

Run `uv run --locked negotiator lab sync` to retry buffered local uploads. Lab commands publish automatically; plain `negotiator play`, `negotiator run`, starter-kit commands, and custom scripts do not.

## Updates, backup, rollback, and cleanup

For an update, create a fresh `git archive` from the reviewed commit, transfer it, unpack it into a new versioned directory, run `uv sync --locked --no-dev`, and change the systemd working and executable paths. Keep the previous directory until the service and UI checks pass.

Back up SQLite through its backup API while the service is stopped:

```bash
sudo systemctl stop y-agent-lab
sudo -u y-agent-lab sqlite3 /var/lib/y-agent-lab/dashboard.sqlite3 \
  ".backup '/var/lib/y-agent-lab/dashboard.sqlite3.backup'"
sudo -u y-agent-lab sqlite3 /var/lib/y-agent-lab/dashboard.sqlite3.backup "PRAGMA integrity_check;"
sudo systemctl start y-agent-lab
```

Download backups over SCP and keep them outside Git and team chat. Enable Azure's automatic guest patching where offered, review `apt` security updates, and use Azure Backup or disk snapshots if the retained lab history becomes difficult to recreate.

If validation fails, leave teammates on the laptop URL, restart the laptop dashboard, and inspect `journalctl -u y-agent-lab` and `journalctl -u caddy`. To roll back a release, point systemd to the previous versioned directory; restore a database backup only when its integrity check passes.

Delete `y-agent-lab-rg` after downloading the final backup when the lab is retired. Deleting only the VM can leave disks and the public IP incurring charges.
