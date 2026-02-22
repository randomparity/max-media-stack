# Radarr 4K

Second Radarr instance for managing 4K movie downloads separately from the standard library.

> This page documents only the differences from the standard [Radarr](Radarr) instance. Refer to that page for general operations, manual testing, and troubleshooting -- substitute `radarr4k` for `radarr` in all container names, config paths, subdomains, and backup paths.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/radarr` (LSIO) -- same image as Radarr |
| **Container name** | `radarr4k` |
| **Internal port** | 7878 |
| **Traefik subdomain** | `radarr4k.media.drc.nz` |
| **Config directory** | `/home/mms/config/radarr4k` |
| **Data directory** | `/data` (NFS) |
| **Health endpoint** | `http://localhost:7878/ping` |
| **Backup type** | `arr` (API backup + config backup) |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start radarr4k.service
systemctl --user stop radarr4k.service
systemctl --user restart radarr4k.service
systemctl --user status radarr4k.service
```

## Key Differences from Radarr

- **Container name**: `radarr4k` (not `radarr`)
- **Config directory**: `/home/mms/config/radarr4k` (separate database and config)
- **Traefik subdomain**: `radarr4k.media.drc.nz`
- **Quality profiles**: Configured for 4K/UHD content
- **Root folder**: Typically points to a separate 4K movies directory under `/data`

## Manual Testing

```bash
podman run --rm -it \
  --name test-radarr4k \
  --network mms \
  --tmpfs /run:U \
  -e PUID=3000 \
  -e PGID=3000 \
  -e TZ=America/New_York \
  -v /home/mms/config/radarr4k:/config:Z \
  -v /data:/data \
  lscr.io/linuxserver/radarr:latest
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Prowlarr -> Radarr 4K | `radarr4k` | `http://radarr4k:7878` | Indexer sync |
| Radarr 4K -> SABnzbd | `sabnzbd` | `http://sabnzbd:8080` | Download client |
