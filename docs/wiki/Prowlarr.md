# Prowlarr

Indexer manager for Usenet and torrent trackers -- provides unified search across indexers for Radarr, Sonarr, and Lidarr.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/prowlarr` (LSIO) |
| **Container name** | `prowlarr` |
| **Internal port** | 9696 |
| **Traefik subdomain** | `prowlarr.media.drc.nz` |
| **Config directory** | `/home/mms/config/prowlarr` |
| **Health endpoint** | `http://localhost:9696/ping` |
| **Backup type** | `arr` (API backup + config backup) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start prowlarr.service
systemctl --user stop prowlarr.service
systemctl --user restart prowlarr.service
systemctl --user status prowlarr.service
```

## Viewing Logs

```bash
# Systemd unit logs
journalctl --user -u prowlarr --since today
journalctl --user -u prowlarr -f

# Container logs directly
podman logs --tail 50 prowlarr
podman logs -f prowlarr
```

## Health Check

```bash
# Via Podman health check
podman healthcheck run prowlarr

# Manual check from inside the container
podman exec prowlarr curl -sf http://localhost:9696/ping

# Via Traefik
curl -sf http://prowlarr.media.drc.nz/ping
```

## Manual Testing

To run Prowlarr outside of systemd for config testing or debugging:

```bash
podman run --rm -it \
  --name test-prowlarr \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/prowlarr:/config:Z \
  lscr.io/linuxserver/prowlarr:latest
```

**LSIO image rules:**
- Use `PUID`/`PGID` environment variables -- do NOT use `--userns=keep-id` (breaks s6-overlay init)
- Use `--network mms` (the Podman network name), not `--network mms.network` (that's the Quadlet filename)
- Use `--tmpfs /run:U` for s6-overlay compatibility (`:U` chowns to container user)
- Use `:Z` on local config volumes for SELinux private labeling

**Stop the systemd service first** to avoid port/name conflicts:

```bash
systemctl --user stop prowlarr.service
```

## Backup & Restore

Prowlarr uses two backup mechanisms:

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/prowlarr/`
- **API backup**: Daily at 04:30, native Prowlarr `.zip` via API, saved to `/data/backups/arr-api/`

Database file backed up: `prowlarr.db`

```bash
# Restore from config backup
ansible-playbook playbooks/restore.yml \
  -e service_name=prowlarr \
  -e backup_file=/data/backups/config/prowlarr/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Prowlarr -> Radarr | `radarr` | `http://radarr:7878` | Push indexers |
| Prowlarr -> Radarr 4K | `radarr4k` | `http://radarr4k:7878` | Push indexers |
| Prowlarr -> Sonarr | `sonarr` | `http://sonarr:8989` | Push indexers |
| Prowlarr -> Lidarr | `lidarr` | `http://lidarr:8686` | Push indexers |

When configuring download clients or apps in Prowlarr's UI, use the bare container hostname (e.g., `radarr`) since all containers share the `mms` network.

## Common Issues

**Indexers failing to connect**

Check that Prowlarr can reach external sites. If running in a test container, verify `--network mms` was used (provides DNS resolution and internet access).

**API key mismatch after restore**

After restoring from backup, the API key may change. Update the API key in any services that connect to Prowlarr (Radarr, Sonarr, Lidarr) via their Settings > Indexers page.
