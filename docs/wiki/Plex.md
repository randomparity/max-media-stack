# Plex

Media server with rich client support -- streams movies, TV shows, and music. The most complex single-container service in MMS due to its custom user namespace mapping, published port, and s6-overlay run script.

| Property | Value |
|----------|-------|
| **Image** | `docker.io/plexinc/pms-docker` (Official) |
| **Container name** | `plex` |
| **Internal port** | 32400 |
| **Published port** | 32400 (host) -> 32400 (container) |
| **Traefik subdomain** | `plex.media.drc.nz` |
| **Config directory** | `/home/mms/config/plex` |
| **Media directories** | `/data/media/movies`, `/data/media/series`, `/data/media/music` (NFS, read-only) |
| **Health endpoint** | `http://localhost:32400/identity` |
| **Backup type** | `plex` (config backup, large dirs excluded) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Service Management

```bash
systemctl --user start plex.service
systemctl --user stop plex.service
systemctl --user restart plex.service
systemctl --user status plex.service
```

## Viewing Logs

```bash
journalctl --user -u plex --since today
journalctl --user -u plex -f
podman logs --tail 50 plex
```

## Health Check

```bash
podman healthcheck run plex
podman exec plex curl -sf http://localhost:32400/identity
curl -sf http://plex.media.drc.nz/identity

# Also accessible directly on the published port
curl -sf http://localhost:32400/identity
```

## Manual Testing

Plex has a unique configuration -- it uses `userns: keep-id:uid=0,gid=0` to map the host `mms` user to root inside the container (required by the official Plex image).

```bash
# Stop the running service first
systemctl --user stop plex.service

podman run --rm -it \
  --name test-plex \
  --network mms \
  --userns=keep-id:uid=0,gid=0 \
  --group-add keep-groups \
  --tmpfs /run:U \
  --tmpfs /transcode:U \
  -p 32400:32400 \
  -e TZ=America/New_York \
  -e PLEX_UID=0 \
  -e PLEX_GID=0 \
  -e CHANGE_CONFIG_DIR_OWNERSHIP=false \
  -v /home/mms/config/plex:/config:Z \
  -v /home/mms/config/plex/plex-run.sh:/etc/services.d/plex/run \
  -v /data/media/movies:/data/media/movies:ro \
  -v /data/media/series:/data/media/series:ro \
  -v /data/media/music:/data/media/music:ro \
  docker.io/plexinc/pms-docker:latest
```

**Key points:**
- `--userns=keep-id:uid=0,gid=0` maps host mms (3000) to root (0) inside the container
- `PLEX_UID=0` and `PLEX_GID=0` tell Plex to run as root inside the container (which is actually mms outside)
- `CHANGE_CONFIG_DIR_OWNERSHIP=false` prevents Plex from chowning config files
- The `plex-run.sh` script is a custom s6-overlay run script
- `/transcode` is a tmpfs for transcoding scratch space
- Published port 32400 is required for direct Plex client connections
- Media volumes are read-only NFS mounts -- no SELinux labels

**Claim token**: For first-time setup, add `-e PLEX_CLAIM=<token>`. Get a claim token from https://www.plex.tv/claim/. The token expires after 4 minutes. The production deployment stores this in Ansible vault as `vault_plex_claim_token`.

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/plex/`
- **Excluded directories**: Cache, Crash Reports, Updates, Codecs (all regenerable)

Database file backed up: `Plug-in Support/Databases/com.plexapp.plugins.library.db`

The Plex backup type stops the service before creating the backup to ensure database consistency, then restarts it.

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=plex \
  -e backup_file=/data/backups/config/plex/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Tautulli -> Plex | `plex` | `http://plex:32400` | Activity monitoring |
| Kometa -> Plex | `plex` | `http://plex:32400` | Metadata management |

Plex also publishes port 32400 directly for client compatibility (some Plex clients require direct server access rather than reverse proxy).

## Common Issues

**Plex not accessible via Traefik**

Plex works via both Traefik (`plex.media.drc.nz`) and direct port 32400. If Traefik routing fails but direct access works, the issue is with Traefik configuration. See [Traefik](Traefik).

**"Not authorized" after restore**

After restoring from backup, Plex may need to be re-claimed. Generate a new claim token from https://www.plex.tv/claim/ and redeploy with the updated `vault_plex_claim_token`.

**Library scan shows no media**

Check NFS mounts are active:

```bash
mount | grep nfs
ls -la /data/media/movies/
```

**Permission errors**

Plex uses the unusual `keep-id:uid=0,gid=0` namespace mapping. Files in `/home/mms/config/plex` should be owned by 3000:3000 on the host (which maps to 0:0 inside the container). If permissions are wrong:

```bash
podman unshare chown -R 3000:3000 /home/mms/config/plex
```

**ADVERTISE_IP warning**

The `ADVERTISE_IP` environment variable is set to the Tailscale IP. If the Tailscale IP changes, update `inventory/group_vars/all/vars.yml` and redeploy.
