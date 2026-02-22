# Jellyfin

Free and open-source media server -- streams movies, TV shows, and music to clients.

| Property | Value |
|----------|-------|
| **Image** | `docker.io/jellyfin/jellyfin` (Official) |
| **Container name** | `jellyfin` |
| **Internal port** | 8096 |
| **Traefik subdomain** | `jellyfin.media.drc.nz` |
| **Config directory** | `/home/mms/config/jellyfin` |
| **Media directory** | `/data/media` (NFS, read-only) |
| **Health endpoint** | `http://localhost:8096/health` |
| **Backup type** | `jellyfin` (config backup, cache excluded) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Service Management

```bash
systemctl --user start jellyfin.service
systemctl --user stop jellyfin.service
systemctl --user restart jellyfin.service
systemctl --user status jellyfin.service
```

## Viewing Logs

```bash
journalctl --user -u jellyfin --since today
journalctl --user -u jellyfin -f
podman logs --tail 50 jellyfin
```

## Health Check

```bash
podman healthcheck run jellyfin
podman exec jellyfin curl -sf http://localhost:8096/health
curl -sf http://jellyfin.media.drc.nz/health
```

## Manual Testing

Jellyfin uses the **official image** (not LSIO) -- it relies on `UserNS=keep-id` for file ownership instead of PUID/PGID.

```bash
# Stop the running service first
systemctl --user stop jellyfin.service

podman run --rm -it \
  --name test-jellyfin \
  --network mms \
  --userns=keep-id \
  --tmpfs /run:U \
  --tmpfs /cache:U \
  -e TZ=America/New_York \
  -v /home/mms/config/jellyfin:/config:Z \
  -v /data/media:/data/media:ro \
  docker.io/jellyfin/jellyfin:latest
```

**Official image rules:**
- Use `--userns=keep-id` -- maps container user to the `mms` user (3000:3000)
- Do NOT use `PUID`/`PGID` (not supported by official images)
- Use `--network mms` (the Podman network name), not `--network mms.network`
- Use `--tmpfs /run:U` and `--tmpfs /cache:U` -- cache is a tmpfs to avoid persisting transcoding artifacts
- Use `:Z` on local config volumes, no SELinux labels on NFS volumes
- Mount media as read-only (`:ro`) -- Jellyfin only needs to read media files

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/jellyfin/`
- Cache directory is excluded from backups (regenerable content)

Database file backed up: `jellyfin.db`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=jellyfin \
  -e backup_file=/data/backups/config/jellyfin/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

Jellyfin has no direct dependencies on other MMS containers. It reads media from NFS mounts and serves content to clients via Traefik.

## Common Issues

**Library scan shows no media**

Check that NFS mounts are active and the media directory is readable:

```bash
mount | grep nfs
ls -la /data/media/movies/
```

See [Troubleshooting > NFS mount problems](Troubleshooting#nfs-mount-problems).

**Transcoding failures**

Transcoding uses the `/cache` tmpfs. If the tmpfs is too small for large transcode jobs, you may need to switch to a persistent volume. Check available memory since tmpfs uses RAM:

```bash
free -h
```

**Permission errors on config files**

Jellyfin uses `UserNS=keep-id`, so files in `/home/mms/config/jellyfin` should be owned by 3000:3000. Verify:

```bash
ls -la /home/mms/config/jellyfin/
```
