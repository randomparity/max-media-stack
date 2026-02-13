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
| Kometa    | —                                | Plex metadata manager (no UI)  |
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

## Quick Start

```bash
ansible-galaxy collection install -r requirements.yml   # Install dependencies
# Edit inventory/group_vars/*/vars.yml and vault.yml     # Configure
ansible-playbook playbooks/site.yml                      # Deploy everything
```

See the **[Getting Started](https://github.com/randomparity/max-media-stack/wiki/Getting-Started)** guide for full prerequisites and step-by-step instructions.

## Documentation

Full documentation is in the **[Wiki](https://github.com/randomparity/max-media-stack/wiki)**:

| Topic | Description |
|-------|-------------|
| [Getting Started](https://github.com/randomparity/max-media-stack/wiki/Getting-Started) | Prerequisites and first-time setup |
| [Configuration](https://github.com/randomparity/max-media-stack/wiki/Configuration) | Inventory variables and secrets |
| [Proxmox API Setup](https://github.com/randomparity/max-media-stack/wiki/Proxmox-API-Setup) | API token creation and permissions |
| [Storage Layout](https://github.com/randomparity/max-media-stack/wiki/Storage-Layout) | Directory structure and NFS mounts |
| [Traefik Reverse Proxy](https://github.com/randomparity/max-media-stack/wiki/Traefik-Reverse-Proxy) | DNS setup and routing configuration |
| [Security](https://github.com/randomparity/max-media-stack/wiki/Security) | Security model overview |
| [Common Operations](https://github.com/randomparity/max-media-stack/wiki/Common-Operations) | Day-to-day commands |
| [Backup & Restore](https://github.com/randomparity/max-media-stack/wiki/Backup-and-Restore) | Backup system, encryption, and restore procedures |
| [Auto-Deploy](https://github.com/randomparity/max-media-stack/wiki/Auto-Deploy) | Renovate integration and deploy groups |
| [Adding a New Service](https://github.com/randomparity/max-media-stack/wiki/Adding-a-New-Service) | Extending the stack |
| [Troubleshooting](https://github.com/randomparity/max-media-stack/wiki/Troubleshooting) | Common issues and debug commands |

## Security

- **Tailscale only** — default firewalld zone is `drop`; only `tailscale0` is trusted
- **No direct port exposure** — only Traefik publishes a host port (80)
- **No socket mount** — Traefik uses the file provider, not the Podman socket
- **Rootless Podman** — no containers run as root
- **SELinux enforcing** — config volumes use `:Z` for private labeling
- **Secrets encrypted** — all sensitive values in ansible-vault encrypted files
- **Backup encryption** — backups encrypted with `age` before storage
