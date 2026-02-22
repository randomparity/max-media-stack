# Channels DVR

Live TV and DVR server -- records TV from HDHomeRun tuners and streaming sources.

| Property | Value |
|----------|-------|
| **Image** | `fancybits/channels-dvr` (Official, digest-pinned) |
| **Container name** | `channels` |
| **Internal port** | 8089 |
| **Published port** | 8089 (host) -> 8089 (container) |
| **Traefik subdomain** | `channels.media.drc.nz` |
| **Config directory** | `/home/mms/config/channels` |
| **Recordings directory** | `/data/recordings` (NFS) |
| **Health endpoint** | `http://localhost:8089` |
| **Backup type** | `channels` (config backup only) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Service Management

```bash
systemctl --user start channels.service
systemctl --user stop channels.service
systemctl --user restart channels.service
systemctl --user status channels.service
```

## Viewing Logs

```bash
journalctl --user -u channels --since today
journalctl --user -u channels -f
podman logs --tail 50 channels
```

## Health Check

```bash
podman healthcheck run channels
podman exec channels curl -sf http://localhost:8089
curl -sf http://channels.media.drc.nz

# Also accessible on the published port
curl -sf http://localhost:8089
```

## Manual Testing

```bash
# Stop the running service first
systemctl --user stop channels.service

podman run --rm -it \
  --name test-channels \
  --network mms \
  --userns=keep-id \
  --tmpfs /run:U \
  -p 8089:8089 \
  -e TZ=America/New_York \
  -v /home/mms/config/channels:/channels-dvr:Z \
  -v /data/recordings:/shares/DVR \
  fancybits/channels-dvr:latest
```

**Official image rules:**
- Use `--userns=keep-id` -- maps container user to the `mms` user (3000:3000)
- Use `--network mms`, not `--network mms.network`
- Use `--tmpfs /run:U`
- Use `:Z` on local config volumes, no SELinux labels on NFS recordings volume
- Published port 8089 is needed for direct client access

**Note:** The production deployment uses a digest-pinned image (`latest@sha256:...`) for reproducibility. For testing, `latest` is fine.

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/channels/`
- No database files listed (Channels manages its own internal database)

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=channels \
  -e backup_file=/data/backups/config/channels/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

Channels DVR has no direct dependencies on other MMS containers. It communicates with HDHomeRun tuners on the local network and stores recordings to NFS.

## Common Issues

**Recordings directory not writable**

The recordings directory is an NFS mount at `/data/recordings`. Verify it's mounted and writable:

```bash
mount | grep recordings
touch /data/recordings/test && rm /data/recordings/test
```

See [Troubleshooting > NFS mount problems](Troubleshooting#nfs-mount-problems).

**HDHomeRun tuner not detected**

Channels needs network access to discover HDHomeRun tuners. Since the container is on the `mms` bridge network, it can reach the LAN. If tuner discovery fails, check that the tuner is on an accessible network and try adding it manually by IP in the Channels UI.

**Image update behavior**

Channels DVR uses a digest-pinned `latest` tag. Renovate updates the digest hash when new versions are published. This ensures the exact image version is tracked even though the tag is `latest`.
