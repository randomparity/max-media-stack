# Getting Started

This guide walks you through deploying the Max Media Stack from scratch.

## Prerequisites

- Proxmox 9.x with API token configured (see [Proxmox API Setup](Proxmox-API-Setup))
- SSH key access to the Proxmox host as `root` from the Ansible control machine (used to create the Fedora cloud image template via `qm` commands)
- TrueNAS with NFS exports for media, usenet, photos, and backups
- Tailscale account with pre-generated auth key
- Ansible 2.15+ with collections: `community.general`, `community.proxmox`, `ansible.posix`, `containers.podman`
- `age` encryption key pair for backups (see [Backup & Restore](Backup-and-Restore#backup-encryption-with-age))

## 1. Install dependencies

```bash
ansible-galaxy collection install -r requirements.yml
```

## 2. Configure inventory

Edit the following files with your environment details:

- `inventory/group_vars/all/vars.yml` -- VM specs, SSH public keys, timezone, user/path settings, Traefik domain
- `inventory/group_vars/proxmox/vars.yml` -- Proxmox API host, node, storage, VM display name
- `inventory/group_vars/mms/vars.yml` -- NFS mounts, services list, Traefik routes, autodeploy config

See [Configuration](Configuration) for a detailed breakdown of each variable file.

## 3. Configure secrets

First, create a vault password file:

```bash
echo 'your-vault-password' > ~/.vault_pass_mms
chmod 0600 ~/.vault_pass_mms
```

**Fresh install** -- the vault files contain commented-out placeholders in plain text. Edit them with your values, then encrypt:

```bash
# Edit the plaintext vault files with your real values
$EDITOR inventory/group_vars/proxmox/vault.yml
$EDITOR inventory/group_vars/all/vault.yml

# Encrypt them
ansible-vault encrypt inventory/group_vars/proxmox/vault.yml
ansible-vault encrypt inventory/group_vars/all/vault.yml
```

**Already encrypted** -- if the vault files have been encrypted previously, use `ansible-vault edit` to decrypt in your `$EDITOR`, make changes, and re-encrypt on save:

```bash
ansible-vault edit inventory/group_vars/proxmox/vault.yml
ansible-vault edit inventory/group_vars/all/vault.yml
```

See [Configuration](Configuration#secrets) for the full list of vault variables.

## 4. Deploy

```bash
# Full deployment (provision VM + configure + deploy services)
ansible-playbook playbooks/site.yml

# Or step by step:
ansible-playbook playbooks/provision-vm.yml
ansible-playbook playbooks/setup-base.yml
ansible-playbook playbooks/deploy-services.yml
```

## Next steps

- [Common Operations](Common-Operations) -- Deploying individual services, backups, restores, and migrations
- [Traefik Reverse Proxy](Traefik-Reverse-Proxy) -- Set up DNS and routing
- [Auto-Deploy](Auto-Deploy) -- Configure automated container image updates
