# Navidrome

Music streaming server -- provides a Subsonic-compatible API for music playback from clients like DSub, Symfonium, or the built-in web UI.

| Property | Value |
|----------|-------|
| **Image** | `deluan/navidrome` (Official) |
| **Container name** | `navidrome` |
| **Internal port** | 4533 |
| **Traefik subdomain** | `navidrome.media.drc.nz` |
| **Config directory** | `/home/mms/config/navidrome` |
| **Music directory** | `/data/media/music` (NFS, read-only) |
| **Health endpoint** | `http://localhost:4533/ping` |
| **Backup type** | `navidrome` (config backup) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Service Management

```bash
systemctl --user start navidrome.service
systemctl --user stop navidrome.service
systemctl --user restart navidrome.service
systemctl --user status navidrome.service
```

## Viewing Logs

```bash
journalctl --user -u navidrome --since today
journalctl --user -u navidrome -f
podman logs --tail 50 navidrome
```

## Health Check

Navidrome uses `wget` instead of `curl` for health checks (no curl in the image):

```bash
podman healthcheck run navidrome

# Manual check from inside the container
podman exec navidrome wget -q --spider http://localhost:4533/ping

# Via Traefik
curl -sf http://navidrome.media.drc.nz/ping
```

## Manual Testing

Navidrome uses an explicit `user` field instead of `--userns=keep-id` or PUID/PGID:

```bash
# Stop the running service first
systemctl --user stop navidrome.service

podman run --rm -it \
  --name test-navidrome \
  --network mms \
  --userns=keep-id \
  --user 3000:3000 \
  --tmpfs /run:U \
  -e TZ=America/New_York \
  -e ND_LOGLEVEL=info \
  -e ND_ENABLEINSIGHTSCOLLECTOR=false \
  -e ND_ENABLEEXTERNALSERVICES=false \
  -v /home/mms/config/navidrome:/data:Z \
  -v /data/media/music:/music:ro \
  deluan/navidrome:latest
```

**Official image rules:**
- Use `--userns=keep-id` with `--user 3000:3000` -- Navidrome runs as the specified user directly
- Use `--network mms`, not `--network mms.network`
- Use `--tmpfs /run:U`
- Use `:Z` on local config volume, no SELinux labels on NFS music volume
- Mount music as read-only (`:ro`)

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/navidrome/`

Database file backed up: `navidrome.db`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=navidrome \
  -e backup_file=/data/backups/config/navidrome/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

Navidrome has no direct dependencies on other MMS containers. It reads music from NFS mounts and serves content to clients via Traefik.

## Common Issues

**Music library not showing / empty scan**

Check that the NFS mount for music is active and readable:

```bash
mount | grep music
ls -la /data/media/music/
```

See [Troubleshooting > NFS mount problems](Troubleshooting#nfs-mount-problems).

**Health check using wget, not curl**

The Navidrome image does not include `curl`. The health check uses `wget -q --spider`. If you're testing health manually from inside the container, use `wget`:

```bash
podman exec navidrome wget -q --spider http://localhost:4533/ping
```

**Insights collector / external services**

The deployment disables `ND_ENABLEINSIGHTSCOLLECTOR` and `ND_ENABLEEXTERNALSERVICES` for privacy. If you need Last.fm scrobbling or other external integrations, these can be re-enabled in the service definition.
