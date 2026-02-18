# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Max Media Stack (MMS)** — Ansible project to provision and manage a full homelab media stack on a Fedora VM (Proxmox 9.x), using rootless Podman with Quadlet systemd integration.

**Services:** Prowlarr, Radarr, Radarr 4K, Sonarr, Lidarr, SABnzbd, Jellyfin, Plex, Tautulli, Kometa, Immich, Channels DVR, Navidrome, Open Notebook
**Storage:** TrueNAS NFS exports mounted at `/data`
**Access:** Traefik reverse proxy on port 80, Tailscale only (no LAN exposure)

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

# Backup
ansible-playbook playbooks/backup.yml

# Restore a service
ansible-playbook playbooks/restore.yml -e service_name=radarr -e backup_file=/path/to/backup

# Migrate from LXC
ansible-playbook playbooks/migrate.yml -e source_host=lxc-hostname
```

## Architecture

- **Rootless Podman**: All containers run as `mms` user (3000:3000) with Quadlet files in `~mms/.config/containers/systemd/`; weekly `mms-image-prune.timer` removes dangling images to prevent disk exhaustion
- **Data-driven services**: Each service defined in `services/<name>.yml`; the generic `quadlet_service` role renders templates
- **Traefik**: Reverse proxy with file provider; routes by `Host` header from `mms_traefik_routes`; publishes host port 80. Plex also publishes port 32400 for client compatibility
- **Immich** is special: multi-container (server, ML, PostgreSQL, Redis) handled by its own role; volume mounts split NFS (user content: upload, library) from local SSD (generated content: thumbs, encoded-video, profile, backups)
- **Secrets**: `ansible-vault` encrypts `vault.yml` files; vault password in `~/.vault_pass_mms`
- **Auto-deploy**: Renovate opens PRs for image updates; per-group systemd timers (`mms-autodeploy-{group}`) poll git and run `ansible-playbook` on new commits; successful deploys prune dangling images inline
- **Backups**: Two systems -- config backups (`mms-backup.timer`, daily 03:00, age-encrypted to local disk) + API backups (`mms-api-backup.timer`, daily 04:30, *arr services to NAS via Traefik); Plex backups exclude Cache, Crash Reports, Updates, and Codecs directories; Open Notebook uses cold backup (stops both app + SurrealDB containers, tars both config dirs) since SurrealDB has no hot-dump CLI

## Repository Layout

- `inventory/` — Hosts and group variables
- `playbooks/` — All playbooks (site, provision, setup, deploy, backup, migrate, etc.)
- `roles/` — Ansible roles (proxmox_vm, base_system, podman, tailscale, storage, firewall, quadlet_service, immich, traefik, backup, migrate, autodeploy, open_notebook)
- `services/` — Per-service variable definitions (YAML files loaded at deploy time)
- `templates/quadlet/` — Jinja2 templates for Podman Quadlet files (.container, .network, .volume)

## Conventions

- Variables prefixed with `mms_` for global, `vault_` for secrets
- Roles use `defaults/main.yml` for overridable defaults
- Handlers used for service restarts and daemon-reload
- SELinux: `:Z` for local config volumes, no labels for NFS (uses `virt_use_nfs` boolean)
- Immich volume split: local SSD base (`immich_media_dir`) at `/data:Z`, NFS overlays for `upload/` and `library/` (`immich_upload_dir`); generated content (`immich_local_dirs`) on local SSD, user content (`immich_nfs_dirs`) on NFS
- All services join the shared `mms.network` for inter-container DNS
- Traefik routing: `mms_traefik_domain` and `mms_traefik_routes` in `inventory/group_vars/mms/vars.yml`
- VM naming: `mms_vm_hostname` (group_vars/all) sets OS hostname and Tailscale node name; `mms_vm_name` (group_vars/proxmox) is the Proxmox display name only
- SSH keys: `mms_vm_ssh_pubkeys` is a list of public keys for cloud-init (supports multiple keys)
- Container template includes `Tmpfs=/run:U` for s6-overlay compatibility; services can declare additional `tmpfs` entries and set `no_new_privileges: false` to override the default
- Jellyfin uses the official `jellyfin/jellyfin` image (no PUID/PGID); relies on `UserNS=keep-id` for file ownership
- INI settings use a stop-then-apply pattern: check in check-mode, stop service if changes needed, apply to quiescent file, restart (avoids apps like SABnzbd overwriting changes on shutdown)
- Inter-container `host_whitelist` must include the bare container hostname (e.g., `sabnzbd`) in addition to the Traefik subdomain FQDN
- Plex backup type (`backup_type: "plex"`) stops the service and excludes regenerable directories (Cache, Crash Reports, Updates, Codecs) — similar pattern to Jellyfin's cache exclusion
- Backup role uses `backup_*` prefix for all variables; API backup variables use `backup_api_*`
- Multi-container role testability: roles like `open_notebook` split into `setup.yml` (files/templates, testable without Podman) and `containers.yml` (runtime: image pull, start, healthcheck); Molecule tests target `setup.yml` only
- Molecule shared pre-tasks: `molecule/shared/prepare_mms_user.yml` creates the mms user/group/quadlet directory; all role converge playbooks include it via `include_tasks`
- Deploy resilience: `deploy-services.yml` wraps each service (including Immich and Traefik) in `block/rescue`; a single service failure is logged and skipped, and the playbook fails at the end with a summary of all failed services
