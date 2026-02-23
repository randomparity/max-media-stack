# Tautulli

Plex analytics and monitoring -- tracks viewing history, provides notifications, and generates statistics.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/tautulli` (LSIO) |
| **Container name** | `tautulli` |
| **Internal port** | 8181 |
| **Traefik subdomain** | `tautulli.media.drc.nz` |
| **Config directory** | `/home/mms/config/tautulli` |
| **Health endpoint** | `http://localhost:8181/status` |
| **Backup type** | `arr` (config backup only, no API backup) |
| **Autodeploy group** | `interactive` (daily at 02:00) |
| **Depends on** | `plex.service` |

## Service Management

```bash
systemctl --user start tautulli.service
systemctl --user stop tautulli.service
systemctl --user restart tautulli.service
systemctl --user status tautulli.service
```

## Viewing Logs

```bash
journalctl --user -u tautulli --since today
journalctl --user -u tautulli -f
podman logs --tail 50 tautulli
```

## Health Check

```bash
podman healthcheck run tautulli
podman exec tautulli curl -sf http://localhost:8181/status
curl -sf http://tautulli.media.drc.nz/status
```

## Manual Testing

```bash
podman run --rm -it \
  --name test-tautulli \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/tautulli:/config:Z \
  -v "/home/mms/config/plex/Library/Application Support/Plex Media Server/Logs:/plex-logs:ro" \
  lscr.io/linuxserver/tautulli:latest
```

**LSIO image rules:**
- Use `PUID`/`PGID` environment variables -- do NOT use `--userns=keep-id` (breaks s6-overlay init)
- Use `--network mms`, not `--network mms.network`
- Use `--tmpfs /run:U` for s6-overlay compatibility
- Use `:Z` on local config volumes

Stop the systemd service first: `systemctl --user stop tautulli.service`

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/tautulli/`

Database file backed up: `tautulli.db`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=tautulli \
  -e backup_file=/data/backups/config/tautulli/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Tautulli -> Plex | `plex` | `http://plex:32400` | Activity monitoring |

Tautulli also reads Plex logs directly via a read-only volume mount at `/plex-logs`.

## Common Issues

**"Unable to connect to Plex" / no activity showing**

Tautulli depends on Plex (`After=plex.service` in the Quadlet). If Plex is down, Tautulli will start but cannot collect data. Check Plex first:

```bash
systemctl --user status plex.service
podman healthcheck run plex
```

**Plex log path issues**

Tautulli mounts Plex's log directory read-only. If the Plex config directory structure changes (e.g., after a Plex update), the log mount may break. Verify the path exists:

```bash
ls "/home/mms/config/plex/Library/Application Support/Plex Media Server/Logs/"
```
