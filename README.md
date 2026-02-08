# Max Media Stack (MMS)

Ansible project to provision and manage a full homelab media stack on a Fedora VM running on Proxmox 9.x, using rootless Podman with Quadlet systemd integration.

## Services

| Service   | Port | Description                    |
|-----------|------|--------------------------------|
| Prowlarr  | 9696 | Indexer manager                |
| Radarr    | 7878 | Movie automation               |
| Sonarr    | 8989 | TV show automation             |
| Lidarr    | 8686 | Music automation               |
| SABnzbd   | 8080 | Usenet downloader              |
| Jellyfin  | 8096 | Media server                   |
| Immich    | 2283 | Photo/video management         |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Proxmox 9.x Host                                   │
│  ┌───────────────────────────────────────────────┐  │
│  │  Fedora VM (mms)                              │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Rootless Podman (mms user, 1100:1100)  │  │  │
│  │  │                                         │  │  │
│  │  │  prowlarr  radarr  sonarr  lidarr       │  │  │
│  │  │  sabnzbd   jellyfin                     │  │  │
│  │  │  immich-server  immich-ml               │  │  │
│  │  │  immich-postgres immich-redis           │  │  │
│  │  │          ┌──────────┐                   │  │  │
│  │  │          │mms.network│                  │  │  │
│  │  │          └──────────┘                   │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │                                               │  │
│  │  Tailscale ──── HTTPS access (no LAN expose)  │  │
│  │  NFS ────────── TrueNAS /data                 │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

- Proxmox 9.x with API token configured
- TrueNAS with NFS exports for media, usenet, and photos
- Tailscale account with pre-generated auth key
- Fedora cloud image template on Proxmox
- Ansible 2.15+ with collections: `community.general`, `community.proxmox`, `ansible.posix`, `containers.podman`
- `age` encryption key pair for backups (public key in config, private key kept offline)

## Quick Start

### 1. Install dependencies

```bash
ansible-galaxy collection install -r requirements.yml
```

### 2. Configure inventory

Edit the following files with your environment details:

- `inventory/group_vars/proxmox/vars.yml` — Proxmox API host, node, storage
- `inventory/group_vars/mms/vars.yml` — VM specs, NFS server IP, SSH public key
- `inventory/group_vars/all/vars.yml` — Timezone, user settings

### 3. Create vault files

```bash
# Create vault password file
echo 'your-vault-password' > ~/.vault_pass_mms
chmod 0600 ~/.vault_pass_mms

# Encrypt secrets
ansible-vault encrypt inventory/group_vars/all/vault.yml
ansible-vault encrypt inventory/group_vars/proxmox/vault.yml
```

Required secrets:
- `vault_proxmox_api_user` — Proxmox API token user
- `vault_proxmox_api_token_secret` — Proxmox API token secret
- `vault_tailscale_auth_key` — Tailscale pre-auth key
- `vault_immich_db_password` — Immich PostgreSQL password

### 4. Deploy

```bash
# Full deployment (provision VM + configure + deploy services)
ansible-playbook playbooks/site.yml

# Or step by step:
ansible-playbook playbooks/provision-vm.yml
ansible-playbook playbooks/setup-base.yml
ansible-playbook playbooks/deploy-services.yml
```

## Common Operations

### Deploy a single service

```bash
ansible-playbook playbooks/deploy-service.yml -e service_name=radarr
```

### Update all services

```bash
ansible-playbook playbooks/update-services.yml
```

### Backup

```bash
# Run backups for all services
ansible-playbook playbooks/backup.yml
```

Backups run automatically via systemd timers:
- **Daily at 03:00** — Config backups for all services
- **Weekly** — Immich photo uploads (rsync)

Retention: 7 daily, 4 weekly, 6 monthly. All backups encrypted with `age`.

### Restore

```bash
ansible-playbook playbooks/restore.yml -e service_name=radarr -e backup_file=/home/mms/backups/radarr-2024-01-15.tar.zst.age
```

### Migrate from existing LXC containers

```bash
ansible-playbook playbooks/migrate.yml -e source_host=old-lxc-host
```

This will:
1. Create a Proxmox snapshot for rollback
2. Verify SQLite integrity on source
3. Rsync config directories to the new VM
4. Fix ownership and start services
5. Verify health checks pass

## Storage Layout

```
/data/                          # NFS from TrueNAS
├── media/
│   ├── movies/                 # Radarr library
│   ├── tv/                     # Sonarr library
│   └── music/                  # Lidarr library
├── usenet/
│   ├── incomplete/             # SABnzbd in-progress
│   └── complete/
│       ├── movies/             # Completed movie downloads
│       ├── tv/                 # Completed TV downloads
│       └── music/              # Completed music downloads
└── photos/                     # Immich uploads

/home/mms/config/<service>/     # Local SSD, per-service config
/home/mms/backups/              # Backup staging area
```

This follows the [TRaSH Guides](https://trash-guides.info/) recommended folder structure, enabling hardlinks between download and library directories.

## Adding a New Service

1. Create `services/<name>.yml` with the service definition (image, ports, volumes, health check)
2. Add the service name to `mms_services` list in `inventory/group_vars/mms/vars.yml`
3. Add a Tailscale serve entry to `mms_tailscale_serve` if needed
4. Deploy: `ansible-playbook playbooks/deploy-service.yml -e service_name=<name>`

## Security

- **Tailscale only**: Default firewalld zone is `drop`; only `tailscale0` interface is in `trusted` zone
- **Rootless Podman**: No containers run as root
- **SELinux enforcing**: Config volumes use `:Z` for private labeling
- **Secrets encrypted**: All sensitive values in ansible-vault encrypted files
- **Backup encryption**: Backups encrypted with `age` before storage
