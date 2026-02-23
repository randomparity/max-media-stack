# Lidarr

Music collection manager -- monitors for new releases, searches indexers, and sends downloads to SABnzbd.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/lidarr` (LSIO) |
| **Container name** | `lidarr` |
| **Internal port** | 8686 |
| **Traefik subdomain** | `lidarr.media.drc.nz` |
| **Config directory** | `/home/mms/config/lidarr` |
| **Data directory** | `/data` (NFS -- music, usenet) |
| **Health endpoint** | `http://localhost:8686/ping` |
| **Backup type** | `arr` (API backup + config backup) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start lidarr.service
systemctl --user stop lidarr.service
systemctl --user restart lidarr.service
systemctl --user status lidarr.service
```

## Viewing Logs

```bash
journalctl --user -u lidarr --since today
journalctl --user -u lidarr -f
podman logs --tail 50 lidarr
```

## Health Check

```bash
podman healthcheck run lidarr
podman exec lidarr curl -sf http://localhost:8686/ping
curl -sf http://lidarr.media.drc.nz/ping
```

## Manual Testing

```bash
podman run --rm -it \
  --name test-lidarr \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/lidarr:/config:Z \
  -v /data:/data \
  lscr.io/linuxserver/lidarr:latest
```

**LSIO image rules:**
- Use `PUID`/`PGID` environment variables -- do NOT use `--userns=keep-id` (breaks s6-overlay init)
- Use `--network mms` (the Podman network name), not `--network mms.network`
- Use `--tmpfs /run:U` for s6-overlay compatibility
- Use `:Z` on local config volumes, no SELinux labels on NFS volumes (`/data`)

**Stop the systemd service first** to avoid port/name conflicts:

```bash
systemctl --user stop lidarr.service
```

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/lidarr/`
- **API backup**: Daily at 04:30, native Lidarr `.zip` via API, saved to `/data/backups/arr-api/`

Database file backed up: `lidarr.db`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=lidarr \
  -e backup_file=/data/backups/config/lidarr/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Prowlarr -> Lidarr | `lidarr` | `http://lidarr:8686` | Indexer sync |
| Lidarr -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download client |
| Lidarr -> Prowlarr | `prowlarr` | `http://prowlarr:9696` | Search indexers |

## Common Issues

**"Root folder does not exist" or permission errors on /data**

The `/data` volume is an NFS mount. Check that the mount is active: `mount | grep nfs`. See [Troubleshooting > NFS mount problems](Troubleshooting#nfs-mount-problems).

**Metadata lookup failures**

Lidarr uses MusicBrainz for metadata. If lookups fail, it may be a rate-limiting issue -- Lidarr has built-in rate limiting but heavy library scans can hit limits. Check logs for 429 errors.
