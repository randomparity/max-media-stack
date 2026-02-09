# Max Media Stack (MMS)

Ansible project to provision and manage a full homelab media stack on a Fedora VM running on Proxmox 9.x, using rootless Podman with Quadlet systemd integration.

## Services

| Service   | URL                              | Description                    |
|-----------|----------------------------------|--------------------------------|
| Prowlarr  | `prowlarr.media.example.com`     | Indexer manager                |
| Radarr    | `radarr.media.example.com`       | Movie automation               |
| Sonarr    | `sonarr.media.example.com`       | TV show automation             |
| Lidarr    | `lidarr.media.example.com`       | Music automation               |
| SABnzbd   | `sabnzbd.media.example.com`      | Usenet downloader              |
| Jellyfin  | `jellyfin.media.example.com`     | Media server                   |
| Immich    | `immich.media.example.com`       | Photo/video management         |

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
│  │  │      ├── prowlarr  radarr  sonarr  lidarr    │  │  │
│  │  │      ├── sabnzbd   jellyfin                  │  │  │
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

Traefik is the only container that publishes a host port (80). All backend services are reached via the shared `mms.network` bridge using container-name DNS. Traffic is HTTP only — the Tailscale WireGuard tunnel already encrypts everything end-to-end.

## Prerequisites

- Proxmox 9.x with API token configured (see [Proxmox API Token Setup](#proxmox-api-token-setup) below)
- SSH key access to the Proxmox host as `root` from the Ansible control machine (used to create the Fedora cloud image template via `qm` commands)
- TrueNAS with NFS exports for media, usenet, and photos
- Tailscale account with pre-generated auth key
- Ansible 2.15+ with collections: `community.general`, `community.proxmox`, `ansible.posix`, `containers.podman`
- `age` encryption key pair for backups (see [Backup Encryption with age](#backup-encryption-with-age) below)

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

## Backup Encryption with age

MMS encrypts backups using `age`, a simple file encryption tool. Encryption uses a public key (safe to store in config); decryption requires the corresponding private key (identity file), which should be kept offline or in a secure location — never on the backup server itself.

The `age` package is automatically installed on the MMS VM by the backup role. You only need to install it on your **workstation** for key generation and restores.

### Installing age

```bash
# Fedora / RHEL 9+
sudo dnf install age

# Ubuntu / Debian (21.04+)
sudo apt install age

# macOS
brew install age
```

This installs two binaries: `age` (encrypt/decrypt) and `age-keygen` (key generation). Verify with:

```bash
age --version
age-keygen --version
```

### Generating keys

`age` supports two key types. Either works with MMS.

**Option A: Native age keys (recommended)**

```bash
age-keygen -o age-identity.txt
```

This creates `age-identity.txt` containing both keys:

```
# created: 2026-01-15T10:30:00Z
# public key: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
AGE-SECRET-KEY-1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

The public key (starts with `age1...`) goes in your Ansible config. Keep the identity file safe for restores.

**Option B: SSH keys**

If you already have an ed25519 SSH key, `age` can encrypt to it directly — no extra key generation needed:

```bash
# Your existing public key works as the age recipient
cat ~/.ssh/id_ed25519.pub
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... user@host
```

For restores, `age` uses the corresponding private key (`~/.ssh/id_ed25519`).

### Configuration

Set the public key in `inventory/group_vars/all/vars.yml`:

```yaml
# Native age key:
mms_backup_age_public_key: "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"

# Or SSH public key:
mms_backup_age_public_key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..."
```

Leave empty to disable backup encryption:

```yaml
mms_backup_age_public_key: ""
```

### Restoring encrypted backups

The restore playbook needs the private key (identity file) path:

```bash
# With a native age identity file:
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/home/mms/backups/radarr/radarr-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt

# With an SSH private key:
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/home/mms/backups/radarr/radarr-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=~/.ssh/id_ed25519
```

### Key management best practices

- Store the identity file (private key) **off the MMS server** — on your workstation, in a password manager, or on an encrypted USB drive
- The public key is not sensitive and is safe to commit to the repository
- If you lose the identity file, encrypted backups cannot be recovered
- Test a restore after initial setup to confirm the key pair works end-to-end

## Auto-Deploy

MMS uses [Renovate](https://docs.renovatebot.com/) to discover container image updates and systemd timers on the VM to automatically deploy changes merged to `main`. Renovate opens PRs for version bumps (auto-merging patch and minor), and per-group autodeploy timers poll the git repo on independent schedules, running `ansible-playbook` when new commits are detected.

Deploy groups let you schedule non-interactive backend services (Prowlarr, Radarr, etc.) to deploy frequently while deferring interactive services (Jellyfin, Immich) to off-hours windows when restarts won't disrupt users.

### How it works

1. Renovate scans `services/*.yml`, role defaults, and `requirements.yml` for pinned versions
2. When updates are available, Renovate opens a PR (grouped by ecosystem: LinuxServer, Immich, Galaxy)
3. Patch and minor updates auto-merge after CI passes; major updates require manual review
4. Per-group `mms-autodeploy-{group}.timer` units detect new commits and deploy their service subset

### GitHub repository setup

#### 1. Generate a deploy key

On your workstation, generate an ed25519 SSH key pair for the VM to pull from GitHub:

```bash
ssh-keygen -t ed25519 -C "mms-autodeploy" -f mms_deploy_key -N ""
```

This creates `mms_deploy_key` (private) and `mms_deploy_key.pub` (public).

#### 2. Add the deploy key to GitHub

In your GitHub repository settings (**Settings > Deploy keys**):

1. Click **Add deploy key**
2. Title: `mms-autodeploy`
3. Key: paste the contents of `mms_deploy_key.pub`
4. Leave **Allow write access** unchecked (read-only is sufficient)
5. Click **Add key**

#### 3. Configure branch protection

In **Settings > Branches**, add a rule for `main`:

1. Check **Require a pull request before merging**
2. Check **Require status checks to pass before merging** and add `lint` as a required check
3. Check **Require branches to be up to date before merging**

#### 4. Enable auto-merge

In **Settings > General > Pull Requests**, check **Allow auto-merge**.

#### 5. Install Renovate

1. Go to the [Renovate GitHub App](https://github.com/apps/renovate) and install it for your repository
2. Renovate will open an onboarding PR — review and merge it
3. Subsequent PRs will follow the schedule and rules in `renovate.json5`

### Vault variables

The autodeploy role requires two vault-encrypted secrets. Add them to `inventory/group_vars/all/vault.yml`:

```bash
ansible-vault edit inventory/group_vars/all/vault.yml
```

Add:

```yaml
# Private deploy key for git clone/fetch (contents of mms_deploy_key)
vault_autodeploy_ssh_key: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----

# Ansible vault password (so the VM can decrypt vault files during deploy)
vault_mms_vault_password: "your-vault-password"
```

Alternatively, encrypt the deploy key inline:

```bash
ansible-vault encrypt_string --name vault_autodeploy_ssh_key < mms_deploy_key
```

After adding the vault variables, delete the local key files:

```bash
rm mms_deploy_key mms_deploy_key.pub
```

### Inventory variable

The repo URL is already configured in `inventory/group_vars/mms/vars.yml`:

```yaml
mms_autodeploy_repo_url: "git@github.com:randomparity/max-media-stack.git"
```

Update this if your repository URL differs.

### Deploy and verify

Run the base setup playbook to deploy the autodeploy role:

```bash
ansible-playbook playbooks/setup-base.yml
```

Then verify on the VM:

```bash
# Check per-group timers are active
systemctl --user list-timers 'mms-autodeploy-*'

# Trigger a manual deploy for a specific group
systemctl --user start mms-autodeploy-backend.service
systemctl --user start mms-autodeploy-interactive.service

# Check logs
journalctl --user -u mms-autodeploy-backend --since today
journalctl --user -u mms-autodeploy-interactive --since today

# View deploy logs (per-group)
ls ~/logs/autodeploy/deploy-backend-*.log
ls ~/logs/autodeploy/deploy-interactive-*.log
```

### Configuration

The autodeploy role accepts these defaults (override in inventory vars):

| Variable | Default | Description |
|----------|---------|-------------|
| `autodeploy_groups` | `{default: {schedule: "*-*-* *:00/30:00"}}` | Per-group deploy schedules (see below) |
| `autodeploy_branch` | `main` | Git branch to track |
| `autodeploy_playbook` | `playbooks/deploy-services.yml` | Playbook to run on changes |
| `autodeploy_timeout` | `1800` | Max deploy duration in seconds |
| `autodeploy_log_retention` | `30` | Number of log files to keep |

#### Deploy groups

`autodeploy_groups` is a dict where each key is a group name with its own `schedule` and optional `services` list. Each group gets its own systemd timer+service pair (`mms-autodeploy-{group}.timer`).

A shared lock file prevents concurrent deploys across groups. Each group tracks its own last-deployed SHA in a state file, so it only deploys when there are new commits it hasn't processed yet. Timers include a 60-second randomized delay to avoid thundering-herd effects when multiple groups share the same schedule.

**Default config** (single group, deploys everything every 30 min):

```yaml
autodeploy_groups:
  default:
    schedule: "*-*-* *:00/30:00"
    # services: omitted = deploy all
```

**Two-group config** (backend every 30 min, interactive at 2 AM):

```yaml
autodeploy_groups:
  backend:
    schedule: "*-*-* *:00/30:00"
    services:
      - prowlarr
      - radarr
      - sonarr
      - lidarr
      - sabnzbd
      - traefik
  interactive:
    schedule: "*-*-* 02:00:00"
    services:
      - jellyfin
      - immich
```

When `services` is omitted from a group, the playbook deploys everything. When specified, only the listed services are deployed when the group's timer fires.

## Adding a New Service

1. Create `services/<name>.yml` with the service definition (image, volumes, health check)
2. Add the service name to `mms_services` list in `inventory/group_vars/mms/vars.yml`
3. Add a Traefik route entry to `mms_traefik_routes` (see [Traefik Reverse Proxy](#traefik-reverse-proxy) below)
4. Ensure DNS is configured for the new subdomain (see [DNS Setup](#dns-setup))
5. Deploy: `ansible-playbook playbooks/deploy-services.yml`

## Traefik Reverse Proxy

Services are accessed via hostname-based routing through a Traefik reverse proxy instead of per-service port numbers. Traefik uses the **file provider** — Ansible generates the routing config from `mms_traefik_routes`, so no Docker/Podman socket is mounted.

### DNS Setup

Configure wildcard DNS so `*.media.example.com` resolves to your VM's Tailscale IP:

1. Find your VM's Tailscale IP: `tailscale ip -4` on the VM
2. Add a wildcard DNS record pointing to that IP. How you do this depends on your DNS setup:
   - **Tailscale MagicDNS**: Not applicable — use a custom DNS server or `/etc/hosts`
   - **Local DNS (Pi-hole, AdGuard, etc.)**: Add a wildcard record `*.media.example.com` → `<tailscale-ip>`
   - **Public DNS**: Add a wildcard A record for `*.media.example.com` → `<tailscale-ip>` (safe since the IP is only reachable via Tailscale)
   - **Hosts file** (quick test): Add entries for each service in `/etc/hosts` on your client

### Configuration

Set your domain in `inventory/group_vars/mms/vars.yml`:

```yaml
mms_traefik_domain: media.example.com   # Replace with your actual domain
```

Routes are defined in `mms_traefik_routes`. To add a route for a new service:

```yaml
mms_traefik_routes:
  myservice:
    subdomain: myservice          # → myservice.media.example.com
    container: myservice          # Container name on mms.network
    port: 8080                    # Container's internal HTTP port
```

After changing `mms_traefik_routes`, re-run the deploy playbook to apply:

```bash
ansible-playbook playbooks/deploy-services.yml
```

### Verifying

After deployment, test from any Tailscale client (once DNS is configured):

```bash
# Quick check from the VM itself
curl -H "Host: radarr.media.example.com" http://localhost

# From a Tailscale client with DNS configured
curl http://radarr.media.example.com
```

## Security

- **Tailscale only**: Default firewalld zone is `drop`; only `tailscale0` interface is in `trusted` zone
- **No direct port exposure**: Only Traefik publishes a host port (80); all backend services are internal to the container network
- **No socket mount**: Traefik uses the file provider, not the Podman socket
- **HTTP only**: No TLS at Traefik — the Tailscale WireGuard tunnel provides end-to-end encryption
- **Rootless Podman**: No containers run as root
- **SELinux enforcing**: Config volumes use `:Z` for private labeling
- **Secrets encrypted**: All sensitive values in ansible-vault encrypted files
- **Backup encryption**: Backups encrypted with `age` before storage
