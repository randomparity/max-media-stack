# SABnzbd

Usenet download client -- receives NZB files from Radarr, Sonarr, and Lidarr and downloads from Usenet providers.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/sabnzbd` (LSIO) |
| **Container name** | `sabnzbd` |
| **Internal port** | 8080 |
| **Traefik subdomain** | `sabnzbd.media.drc.nz` |
| **Config directory** | `/home/mms/config/sabnzbd` |
| **Data directory** | `/data` (NFS -- usenet downloads) |
| **Health endpoint** | `http://localhost:8080/api?mode=version` |
| **Backup type** | `sabnzbd` (config backup only) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start sabnzbd.service
systemctl --user stop sabnzbd.service
systemctl --user restart sabnzbd.service
systemctl --user status sabnzbd.service
```

## Viewing Logs

```bash
journalctl --user -u sabnzbd --since today
journalctl --user -u sabnzbd -f
podman logs --tail 50 sabnzbd
```

## Health Check

```bash
podman healthcheck run sabnzbd
podman exec sabnzbd curl -sf http://localhost:8080/api?mode=version
curl -sf http://sabnzbd.media.drc.nz/api?mode=version
```

## Manual Testing

```bash
podman run --rm -it \
  --name test-sabnzbd \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/sabnzbd:/config:Z \
  -v /data:/data \
  lscr.io/linuxserver/sabnzbd:latest
```

**LSIO image rules:**
- Use `PUID`/`PGID` environment variables -- do NOT use `--userns=keep-id` (breaks s6-overlay init)
- Use `--network mms` (the Podman network name), not `--network mms.network`
- Use `--tmpfs /run:U` for s6-overlay compatibility
- Use `:Z` on local config volumes, no SELinux labels on NFS volumes (`/data`)

Stop the systemd service first: `systemctl --user stop sabnzbd.service`

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/sabnzbd/`
- **No API backup** -- SABnzbd is not an *arr service

Config file backed up: `sabnzbd.ini`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=sabnzbd \
  -e backup_file=/data/backups/config/sabnzbd/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Radarr -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download requests |
| Radarr 4K -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download requests |
| Sonarr -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download requests |
| Lidarr -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download requests |

## Common Issues

**"Access denied" / `host_whitelist` errors**

SABnzbd restricts access by hostname. The MMS deployment uses an INI stop-then-apply pattern to configure `host_whitelist` in `sabnzbd.ini`:

```ini
[misc]
host_whitelist = sabnzbd.media.drc.nz,sabnzbd
```

The whitelist must include **both** the Traefik FQDN (`sabnzbd.media.drc.nz`) and the bare container hostname (`sabnzbd`). The bare hostname is needed for inter-container connections from the *arr services.

If you see access denied errors after a manual config change:

1. Stop the service (SABnzbd overwrites its INI on shutdown):
   ```bash
   systemctl --user stop sabnzbd.service
   ```
2. Edit `/home/mms/config/sabnzbd/sabnzbd.ini` and fix the `host_whitelist` value
3. Restart:
   ```bash
   systemctl --user start sabnzbd.service
   ```

**INI changes not persisting**

SABnzbd writes its config to `sabnzbd.ini` on shutdown. If you edit the file while SABnzbd is running, your changes will be overwritten when the service stops. Always stop the service before editing the INI file. The Ansible deploy handles this automatically with the stop-then-apply pattern.

**Download speed issues**

Check that the NFS mount for `/data/usenet` is responsive:

```bash
dd if=/dev/zero of=/data/usenet/test bs=1M count=100 oflag=direct && rm /data/usenet/test
```

If writes are slow, check NFS server health and network connectivity.
