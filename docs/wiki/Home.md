# Max Media Stack (MMS)

Ansible project to provision and manage a full homelab media stack on a Fedora VM running on Proxmox 9.x, using rootless Podman with Quadlet systemd integration.

## Services

| Service   | URL                              | Description                    |
|-----------|----------------------------------|--------------------------------|
| Prowlarr  | `prowlarr.media.example.com`     | Indexer manager                |
| Radarr    | `radarr.media.example.com`       | Movie automation               |
| Radarr 4K | `radarr4k.media.example.com`     | 4K movie automation            |
| Sonarr    | `sonarr.media.example.com`       | TV show automation             |
| Lidarr    | `lidarr.media.example.com`       | Music automation               |
| SABnzbd   | `sabnzbd.media.example.com`      | Usenet downloader              |
| Jellyfin  | `jellyfin.media.example.com`     | Media server                   |
| Plex      | `plex.media.example.com`         | Media server                   |
| Tautulli  | `tautulli.media.example.com`     | Plex analytics/monitoring      |
| Kometa    | ---                              | Plex metadata manager (no UI)  |
| Immich    | `immich.media.example.com`       | Photo/video management         |
| Channels  | `channels.media.example.com`     | Live TV and DVR                |
| Navidrome | `navidrome.media.example.com`    | Music streaming server         |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Proxmox 9.x Host                                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Fedora VM (mms)                                   │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  Rootless Podman (mms user, 3000:3000)       │  │  │
│  │  │                                              │  │  │
│  │  │  traefik (:80) ─── Host header routing       │  │  │
│  │  │      │                                       │  │  │
│  │  │      ├── prowlarr  radarr  radarr4k          │  │  │
│  │  │      ├── sonarr  lidarr  sabnzbd             │  │  │
│  │  │      ├── jellyfin  plex  channels             │  │  │
│  │  │      ├── tautulli  kometa  navidrome         │  │  │
│  │  │      └── immich-server  immich-ml            │  │  │
│  │  │          immich-postgres immich-redis        │  │  │
│  │  │            ┌───────────┐                     │  │  │
│  │  │            │mms.network│                     │  │  │
│  │  │            └───────────┘                     │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                    │  │
│  │  Tailscale ──── encrypted tunnel (no LAN expose)   │  │
│  │  NFS ────────── TrueNAS /data                      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

Traefik is the only container that publishes a host port (80). All backend services are reached via the shared `mms.network` bridge using container-name DNS. Traffic is HTTP only -- the Tailscale WireGuard tunnel already encrypts everything end-to-end.

## Inter-Container Access

All containers share the `mms.network` bridge and reach each other by container name. When configuring one service to talk to another (e.g., adding SABnzbd as a download client in Radarr), use these internal URLs:

| Container        | Hostname           | Port  | Internal URL                        |
|------------------|--------------------|-------|-------------------------------------|
| Prowlarr         | `prowlarr`         | 9696  | `http://prowlarr:9696`              |
| Radarr           | `radarr`           | 7878  | `http://radarr:7878`                |
| Radarr 4K        | `radarr4k`         | 7878  | `http://radarr4k:7878`              |
| Sonarr           | `sonarr`           | 8989  | `http://sonarr:8989`                |
| Lidarr           | `lidarr`           | 8686  | `http://lidarr:8686`                |
| SABnzbd          | `sabnzbd`          | 8080  | `http://sabnzbd:8080`               |
| Jellyfin         | `jellyfin`         | 8096  | `http://jellyfin:8096`              |
| Plex             | `plex`             | 32400 | `http://plex:32400`                 |
| Tautulli         | `tautulli`         | 8181  | `http://tautulli:8181`              |
| Channels DVR     | `channels`         | 8089  | `http://channels:8089`              |
| Navidrome        | `navidrome`        | 4533  | `http://navidrome:4533`             |
| Immich Server    | `immich-server`    | 2283  | `http://immich-server:2283`         |
| Immich ML        | `immich-ml`        | 3003  | `http://immich-ml:3003`             |
| Immich PostgreSQL| `immich-postgres`  | 5432  | `immich-postgres:5432` (TCP)        |
| Immich Redis     | `immich-redis`     | 6379  | `immich-redis:6379` (TCP)           |
| Traefik          | `traefik`          | 80    | `http://traefik:80`                 |

Common connections to configure:

- **Radarr/Radarr 4K/Sonarr/Lidarr -> SABnzbd**: Add as download client using `http://sabnzbd:8080`
- **Radarr/Radarr 4K/Sonarr/Lidarr -> Prowlarr**: Prowlarr pushes indexers to the \*arrs via their internal URLs
- **Prowlarr -> \*arrs**: Add each app under Settings > Apps using its internal URL above
- **Tautulli -> Plex**: Configure Plex Media Server using `http://plex:32400`; Plex logs are already mounted via volume

## Documentation

- [Getting Started](Getting-Started) -- Prerequisites and first-time setup
- [Configuration](Configuration) -- Inventory variables and secrets
- [Proxmox API Setup](Proxmox-API-Setup) -- API token creation and permissions
- [Storage Layout](Storage-Layout) -- Directory structure and NFS mounts
- [Traefik Reverse Proxy](Traefik-Reverse-Proxy) -- DNS setup and routing config
- [Security](Security) -- Security model overview
- [Common Operations](Common-Operations) -- Day-to-day commands
- [Backup & Restore](Backup-and-Restore) -- Backup system, encryption, and restore procedures
- [Auto-Deploy](Auto-Deploy) -- Renovate integration and deploy groups
- [Adding a New Service](Adding-a-New-Service) -- Extending the stack
- [Troubleshooting](Troubleshooting) -- Common issues and debug commands
