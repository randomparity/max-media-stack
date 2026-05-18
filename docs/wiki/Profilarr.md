# Profilarr

Quality Profile and Custom Format manager for Radarr/Sonarr/Lidarr. Profilarr v2 syncs curated profiles (TRaSH-style) and custom formats into the *arr applications.

| Property | Value |
|----------|-------|
| **Image** | `ghcr.io/dictionarry-hub/profilarr` |
| **Container name** | `profilarr` |
| **Internal port** | 6868 |
| **Traefik subdomain** | `profilarr.media.example.com` |
| **Config directory** | `/home/mms/config/profilarr` |
| **Health endpoint** | `http://localhost:6868/api/v1/health` |
| **Backup type** | `arr` (config backup) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start profilarr.service
systemctl --user stop profilarr.service
systemctl --user restart profilarr.service
systemctl --user status profilarr.service
```

## Viewing Logs

```bash
journalctl --user -u profilarr --since today
journalctl --user -u profilarr -f

podman logs --tail 50 profilarr
podman logs -f profilarr
```

## Health Check

```bash
podman healthcheck run profilarr
podman exec profilarr curl -sf http://localhost:6868/api/v1/health
curl -sf http://profilarr.media.example.com/api/v1/health
```

## Backup & Restore

Profilarr uses the generic `arr` backup type -- daily encrypted tar of `/home/mms/config/profilarr/`.

```bash
# Restore from config backup
ansible-playbook playbooks/restore.yml \
  -e service_name=profilarr \
  -e backup_file=/data/backups/config/profilarr/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Notes

- Profilarr v2 introduced breaking changes from v1 (new GHCR image, new env contract). The MMS image is pinned to a v2 tag and managed by Renovate.
- The optional `parser` sidecar (for custom-format and quality-profile testing) is intentionally not deployed. Add a separate service definition if you need it.
- Profilarr runs with `PUID=0`/`PGID=0` (container root) following the LSIO pattern used by every other *arr service in MMS. Under rootless Podman with `UserNS=host`, container UID 0 maps to host UID 3000 (the `mms` user), so files in `/home/mms/config/profilarr/` are owned by `mms:mms` on the host.
