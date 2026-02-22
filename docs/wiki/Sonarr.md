# Sonarr

TV series collection manager -- monitors for new episodes, searches indexers, and sends downloads to SABnzbd.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/sonarr` (LSIO) |
| **Container name** | `sonarr` |
| **Internal port** | 8989 |
| **Traefik subdomain** | `sonarr.media.drc.nz` |
| **Config directory** | `/home/mms/config/sonarr` |
| **Data directory** | `/data` (NFS -- series, usenet) |
| **Health endpoint** | `http://localhost:8989/ping` |
| **Backup type** | `arr` (API backup + config backup) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start sonarr.service
systemctl --user stop sonarr.service
systemctl --user restart sonarr.service
systemctl --user status sonarr.service
```

## Viewing Logs

```bash
journalctl --user -u sonarr --since today
journalctl --user -u sonarr -f
podman logs --tail 50 sonarr
```

## Health Check

```bash
podman healthcheck run sonarr
podman exec sonarr curl -sf http://localhost:8989/ping
curl -sf http://sonarr.media.drc.nz/ping
```

## Manual Testing

```bash
podman run --rm -it \
  --name test-sonarr \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/sonarr:/config:Z \
  -v /data:/data \
  lscr.io/linuxserver/sonarr:latest
```

**LSIO image rules:**
- Use `PUID`/`PGID` environment variables -- do NOT use `--userns=keep-id` (breaks s6-overlay init)
- Use `--network mms` (the Podman network name), not `--network mms.network`
- Use `--tmpfs /run:U` for s6-overlay compatibility
- Use `:Z` on local config volumes, no SELinux labels on NFS volumes (`/data`)

**Stop the systemd service first** to avoid port/name conflicts:

```bash
systemctl --user stop sonarr.service
```

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/sonarr/`
- **API backup**: Daily at 04:30, native Sonarr `.zip` via API, saved to `/data/backups/arr-api/`

Database file backed up: `sonarr.db`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=sonarr \
  -e backup_file=/data/backups/config/sonarr/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Prowlarr -> Sonarr | `sonarr` | `http://sonarr:8989` | Indexer sync |
| Sonarr -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download client |
| Sonarr -> Prowlarr | `prowlarr` | `http://prowlarr:9696` | Search indexers |

## Common Issues

**"Root folder does not exist" or permission errors on /data**

The `/data` volume is an NFS mount. Check that the mount is active: `mount | grep nfs`. See [Troubleshooting > NFS mount problems](Troubleshooting#nfs-mount-problems).

**Download client connection refused**

Verify SABnzbd is running: `podman exec sonarr curl -sf http://sabnzbd:8080/api?mode=version`
