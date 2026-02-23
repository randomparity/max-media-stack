# Radarr

Movie collection manager -- monitors for new releases, searches indexers, and sends downloads to SABnzbd.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/radarr` (LSIO) |
| **Container name** | `radarr` |
| **Internal port** | 7878 |
| **Traefik subdomain** | `radarr.media.drc.nz` |
| **Config directory** | `/home/mms/config/radarr` |
| **Data directory** | `/data` (NFS -- movies, usenet) |
| **Health endpoint** | `http://localhost:7878/ping` |
| **Backup type** | `arr` (API backup + config backup) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start radarr.service
systemctl --user stop radarr.service
systemctl --user restart radarr.service
systemctl --user status radarr.service
```

## Viewing Logs

```bash
# Systemd unit logs
journalctl --user -u radarr --since today
journalctl --user -u radarr -f

# Container logs directly
podman logs --tail 50 radarr
podman logs -f radarr
```

## Health Check

```bash
# Via Podman health check
podman healthcheck run radarr

# Manual check
podman exec radarr curl -sf http://localhost:7878/ping

# Via Traefik
curl -sf http://radarr.media.drc.nz/ping
```

## Manual Testing

To run Radarr outside of systemd for config testing or debugging:

```bash
podman run --rm -it \
  --name test-radarr \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/radarr:/config:Z \
  -v /data:/data \
  lscr.io/linuxserver/radarr:latest
```

**LSIO image rules:**
- Use `PUID`/`PGID` environment variables -- do NOT use `--userns=keep-id` (breaks s6-overlay init)
- Use `--network mms` (the Podman network name), not `--network mms.network` (that's the Quadlet filename)
- Use `--tmpfs /run:U` for s6-overlay compatibility
- Use `:Z` on local config volumes, but NO SELinux labels on NFS volumes (`/data`)

**Stop the systemd service first** to avoid port/name conflicts:

```bash
systemctl --user stop radarr.service
```

## Backup & Restore

Radarr uses two backup mechanisms:

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/radarr/`
- **API backup**: Daily at 04:30, native Radarr `.zip` via API, saved to `/data/backups/arr-api/`

Database file backed up: `radarr.db`

```bash
# Restore from config backup
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/data/backups/config/radarr/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Prowlarr -> Radarr | `radarr` | `http://radarr:7878` | Indexer sync |
| Radarr -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download client |
| Radarr -> Prowlarr | `prowlarr` | `http://prowlarr:9696` | Search indexers |

When configuring connections in Radarr's UI, use the bare container hostname (e.g., `sabnzbd`) since all containers share the `mms` network.

## Common Issues

**"Root folder does not exist" or permission errors on /data**

The `/data` volume is an NFS mount. Check that the mount is active and accessible:

```bash
mount | grep nfs
ls -la /data/media/movies/
```

If the mount is stale, see [Troubleshooting > NFS mount problems](Troubleshooting#nfs-mount-problems).

**Download client connection refused**

Verify SABnzbd is running and reachable from the Radarr container:

```bash
podman exec radarr curl -sf http://sabnzbd:8080/api?mode=version
```

**API key mismatch after restore**

After restoring, update the API key in Prowlarr's app connections and any other services that reference Radarr.
