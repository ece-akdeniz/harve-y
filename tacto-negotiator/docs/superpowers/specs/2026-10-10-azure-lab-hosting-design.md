# Azure lab hosting design

## Goal

Move the shared experiment lab from a developer laptop tunnel to one stable Azure host while preserving its existing history, authentication, and laptop publishing workflow.

## Design

- Run one small Ubuntu Azure VM with a managed OS disk. SQLite stays on the VM's local block device, where its WAL and exclusive locking semantics are supported.
- Do not use Azure App Service persistent storage for this database. Microsoft documents that its Linux filesystem is a mounted network share that blocks SQLite exclusive locks.
- Use a B1s or another Azure-for-Students free-service-eligible Linux size shown by the portal. Keep one VM and confirm the displayed compute, disk, and public-IP estimate before creation.
- Run the existing lab server as an unprivileged systemd service. Caddy terminates public HTTPS and proxies only to the server's loopback listener.
- Use a static Standard public IP with an Azure `REGION.cloudapp.azure.com` DNS label. This avoids a separate domain purchase while giving Caddy a stable TLS hostname.
- Supply only `LAB_PASSWORD` and `LAB_UPLOAD_TOKEN` to the service. Arena and model keys remain on team laptops.
- Deploy tracked source as a Git archive and copy a consistent SQLite backup separately. Neither secrets nor the database enter Git.

## Cutover and rollback

Create and verify the Azure VM before changing laptop `LAB_URL` values. Stop writes briefly, take a SQLite backup, transfer it over SSH, and verify login, run history, loop state, and an authenticated upload. The laptop host remains available until those checks pass. Rollback means restoring the old URL; the source database is retained unchanged.

## Cost boundary

The Azure for Students offer may include 750 monthly hours for an eligible Linux VM and a qualifying managed disk, but availability and included SKUs vary. A static public IP or a non-eligible disk can still consume credit. The owner must confirm the estimate displayed by Azure before creating the resources, configure a budget alert, and delete the resource group when the lab is no longer needed.
