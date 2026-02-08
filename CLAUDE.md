# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Max Media Stack (MMS)** — Ansible project to provision and manage a full homelab media stack on a Fedora VM (Proxmox 9.x), using rootless Podman with Quadlet systemd integration.

**Services:** Prowlarr, Radarr, Sonarr, Lidarr, SABnzbd, Jellyfin, Immich
**Storage:** TrueNAS NFS exports mounted at `/data`
**Access:** Tailscale only (no LAN exposure)

## Key Commands

```bash
# Install Galaxy collections
ansible-galaxy collection install -r requirements.yml

# Lint
ansible-lint playbooks/ roles/
yamllint .

# Dry run (check mode)
ansible-playbook playbooks/site.yml --check --diff

# Full deploy
ansible-playbook playbooks/site.yml

# Deploy single service
ansible-playbook playbooks/deploy-service.yml -e service_name=radarr

# Update all services
ansible-playbook playbooks/update-services.yml

# Backup
ansible-playbook playbooks/backup.yml

# Restore a service
ansible-playbook playbooks/restore.yml -e service_name=radarr -e backup_file=/path/to/backup

# Migrate from LXC
ansible-playbook playbooks/migrate.yml -e source_host=lxc-hostname
```

## Architecture

- **Rootless Podman**: All containers run as `mms` user (1100:1100) with Quadlet files in `~mms/.config/containers/systemd/`
- **Data-driven services**: Each service defined in `services/<name>.yml`; the generic `quadlet_service` role renders templates
- **Immich** is special: multi-container (server, ML, PostgreSQL, Redis) handled by its own role
- **Secrets**: `ansible-vault` encrypts `vault.yml` files; vault password in `~/.vault_pass_mms`

## Repository Layout

- `inventory/` — Hosts and group variables
- `playbooks/` — All playbooks (site, provision, setup, deploy, backup, migrate, etc.)
- `roles/` — Ansible roles (proxmox_vm, base_system, podman, tailscale, storage, firewall, quadlet_service, immich, backup, migrate)
- `services/` — Per-service variable definitions (YAML files loaded at deploy time)
- `templates/quadlet/` — Jinja2 templates for Podman Quadlet files (.container, .network, .volume)

## Conventions

- Variables prefixed with `mms_` for global, `vault_` for secrets
- Roles use `defaults/main.yml` for overridable defaults
- Handlers used for service restarts and daemon-reload
- SELinux: `:Z` for local config volumes, no labels for NFS (uses `container_use_nfs` boolean)
- All services join the shared `mms.network` for inter-container DNS
