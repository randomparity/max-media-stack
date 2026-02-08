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
│  │  │          ┌─────────-─┐                  │  │  │
│  │  │          │mms.network│                  │  │  │
│  │  │          └──────────-┘                  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │                                               │  │
│  │  Tailscale ──── HTTPS access (no LAN expose)  │  │
│  │  NFS ────────── TrueNAS /data                 │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

- Proxmox 9.x with API token configured (see [Proxmox API Token Setup](#proxmox-api-token-setup) below)
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

### 3. Configure secrets

First, create a vault password file:

```bash
echo 'your-vault-password' > ~/.vault_pass_mms
chmod 0600 ~/.vault_pass_mms
```

**Fresh install** — the vault files contain commented-out placeholders in plain text. Edit them with your values, then encrypt:

```bash
# Edit the plaintext vault files with your real values
$EDITOR inventory/group_vars/proxmox/vault.yml
$EDITOR inventory/group_vars/all/vault.yml

# Encrypt them
ansible-vault encrypt inventory/group_vars/proxmox/vault.yml
ansible-vault encrypt inventory/group_vars/all/vault.yml
```

**Already encrypted** — if the vault files have been encrypted previously, use `ansible-vault edit` to decrypt in your `$EDITOR`, make changes, and re-encrypt on save:

```bash
ansible-vault edit inventory/group_vars/proxmox/vault.yml
ansible-vault edit inventory/group_vars/all/vault.yml
```

`inventory/group_vars/proxmox/vault.yml` — Proxmox API credentials:
- `vault_proxmox_api_user` — API token in `user@realm!tokenid` format (e.g., `ansible@pam!mms`)
- `vault_proxmox_api_token_secret` — Token secret UUID from Proxmox

`inventory/group_vars/all/vault.yml` — Service credentials:
- `vault_tailscale_auth_key` — Tailscale pre-auth key
- `vault_immich_db_password` — Immich PostgreSQL password
- `vault_backup_age_public_key` — Age public key for backup encryption

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
│   ├── series/                  # Sonarr library
│   └── music/                  # Lidarr library
├── usenet/
│   ├── incomplete/             # SABnzbd in-progress
│   └── complete/
│       ├── movies/             # Completed movie downloads
│       ├── series/              # Completed TV downloads
│       └── music/              # Completed music downloads
└── photos/                     # Immich uploads

/home/mms/config/<service>/     # Local SSD, per-service config
/home/mms/backups/              # Backup staging area
```

This follows the [TRaSH Guides](https://trash-guides.info/) recommended folder structure, enabling hardlinks between download and library directories.

## Proxmox API Token Setup

MMS uses the Proxmox API to provision and manage VMs. Create a dedicated user and API token with the minimum required permissions.

### 1. Create the user and token

In the Proxmox web UI (**Datacenter > Permissions**):

1. Go to **Users** and create a new user:
   - User name: `ansible`
   - Realm: `pam` (Linux PAM)
   - No password needed (token-only access)

2. Go to **API Tokens** and create a token for the user:
   - User: `ansible@pam`
   - Token ID: `mms`
   - **Uncheck** "Privilege Separation" (token inherits the user's permissions)

3. Copy the token secret — it is only shown once.

Or via the CLI on the Proxmox host:

```bash
pveum user add ansible@pam
pveum user token add ansible@pam mms --privsep 0
```

### 2. Create a custom role with least-privilege permissions

```bash
pveum role add MMS-Provisioner --privs \
  "VM.Allocate VM.Clone VM.Config.Cloudinit VM.Config.CPU VM.Config.Disk VM.Config.Memory VM.Config.Network VM.Config.Options VM.Audit VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit VM.Snapshot VM.Snapshot.Rollback"
```

Permission breakdown:

| Permission | Used by |
|---|---|
| `VM.Allocate` | Create new VMs from clone |
| `VM.Clone` | Clone template to new VM |
| `VM.Config.Cloudinit` | Set cloud-init user, SSH keys, IP |
| `VM.Config.CPU` | Set core count |
| `VM.Config.Disk` | Resize root disk |
| `VM.Config.Memory` | Set RAM |
| `VM.Config.Network` | Set bridge/NIC |
| `VM.Config.Options` | General VM configuration |
| `VM.Audit` | Query VM info and status |
| `VM.PowerMgmt` | Start/stop VM |
| `VM.Snapshot`, `VM.Snapshot.Rollback` | Pre-migration snapshots (migrate role) |
| `Datastore.AllocateSpace` | Allocate disk on storage |
| `Datastore.Audit` | Query storage info |

### 3. Assign the role to the user

```bash
pveum acl modify /vms/<VMID> --user ansible@pam --role MMS-Provisioner
```

Replace `<VMID>` with your VM ID (e.g., `202`), or use `/vms` to grant access to all VMs on the node.

If the token needs access to clone from a template on a specific storage:

```bash
pveum acl modify /storage/<STORAGE> --user ansible@pam --role MMS-Provisioner
```

### 4. Store credentials in the vault

The vault expects the full `user@realm!tokenid` format:

```bash
ansible-vault edit inventory/group_vars/proxmox/vault.yml
```

```yaml
vault_proxmox_api_user: "ansible@pam!mms"
vault_proxmox_api_token_secret: "<token-secret-from-step-1>"
```

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
