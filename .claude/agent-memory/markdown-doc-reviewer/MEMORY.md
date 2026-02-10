# MMS Documentation Reviewer Memory

## Document Inventory
- `CLAUDE.md` -- Developer onboarding / AI assistant context (68 lines)
- `README.md` -- Full project README with architecture, Quick Start, operations, Proxmox setup, Traefik, age encryption, Auto-Deploy (~600 lines)
- `.claude/agents/ansible-reviewer.md` -- Ansible review agent definition
- `.claude/agents/supply-chain-hygiene-reviewer.md` -- Supply-chain review agent definition
- `.claude/agents/markdown-doc-reviewer.md` -- This agent's definition

## Terminology Conventions
- "Rootless Podman" (capitalized)
- "Quadlet" (capitalized when referring to the systemd integration)
- "mms" (lowercase when referring to the user/service name)
- SELinux boolean: `virt_use_nfs` (NOT `container_use_nfs` -- fixed in commit a222f8c)
- Variable prefixes: `mms_` (global), `vault_` (secrets)
- Heading style: sentence case in both CLAUDE.md and README.md
- List markers: `-` consistently
- Code blocks: `bash` for shell, `yaml` for YAML, bare fence for ASCII art

## Known Documentation Gaps (as of 2026-02-10)
- No CHANGELOG documenting the UID/GID change from 1100 to 3000
- No migration guide for existing deployments
- Fedora version (43) not mentioned in prose of CLAUDE.md or README.md (only in inventory)
- No LICENSE or CONTRIBUTING files (acceptable for personal homelab)
- ~~README line 106 lists `vault_backup_age_public_key`~~ RESOLVED: now correctly uses `mms_backup_age_public_key`
- Dead variable `immich_port` in roles/immich/defaults/main.yml (no longer published)
- ~~CLAUDE.md roles list missing `autodeploy` role~~ RESOLVED: autodeploy now listed
- ~~CLAUDE.md Architecture section missing auto-deploy/Renovate bullet~~ RESOLVED: auto-deploy bullet present
- CLAUDE.md Conventions missing: `mms_vm_hostname`/`mms_vm_name` split, `mms_vm_ssh_pubkeys` list, `Tmpfs=/run:U`, per-service `tmpfs`, `NoNewPrivileges`, Jellyfin official image
- README Quick Start step 2 file descriptions stale (VM specs/SSH keys moved to group_vars/all)
- supply-chain-hygiene-reviewer.md services list missing Channels DVR and Navidrome

## Source of Truth for Key Values
- UID/GID: `inventory/group_vars/all/vars.yml` lines 23-25 (currently 3000:3000)
- VM hostname: `inventory/group_vars/all/vars.yml` line 6 (`mms_vm_hostname`)
- VM display name: `inventory/group_vars/proxmox/vars.yml` line 18 (`mms_vm_name`)
- SSH public keys: `inventory/group_vars/all/vars.yml` lines 18-20 (`mms_vm_ssh_pubkeys` -- list)
- Traefik domain: `inventory/group_vars/all/vars.yml` line 50 (`mms_traefik_domain`)
- SELinux boolean: `roles/base_system/defaults/main.yml` line 20 (`virt_use_nfs`)
- Fedora version: `inventory/group_vars/proxmox/vars.yml` line 14 (Fedora 43)
- Services list: `inventory/group_vars/mms/vars.yml` lines 25-33
- Traefik routes: `inventory/group_vars/mms/vars.yml` lines 36-72 (`mms_traefik_routes`)
- Traefik role defaults: `roles/traefik/defaults/main.yml` (image, port 80, log level)
- Autodeploy defaults: `roles/autodeploy/defaults/main.yml` (groups, branch, timeout, retention)
- Autodeploy inventory override: `inventory/group_vars/mms/vars.yml` lines 74-94 (repo URL, groups)
- Jellyfin image: `services/jellyfin.yml` (`docker.io/jellyfin/jellyfin`, no PUID/PGID)
- Container template: `templates/quadlet/container.j2` (Tmpfs=/run:U, per-service tmpfs, NoNewPrivileges)
- Playbook names: `playbooks/` directory

## Review History
- 2026-02-08: Full review of all .md files on fix/dry-run-issues branch (15 commits over main)
  - Found 3 files with stale UID 1100 (CLAUDE.md, README.md, supply-chain-hygiene-reviewer.md)
  - Found 1 missed Molecule fixture (testapp.yml PUID/PGID still 1100)
  - Found 1 stale ansible-reviewer memory entry (item #10 re: container_use_nfs)
  - SELinux boolean in CLAUDE.md already correctly says virt_use_nfs
  - README structure is comprehensive and well-organized
  - See review-findings.md for details
- 2026-02-08: Review of CLAUDE.md + README.md on feat/add-traefik-proxy branch
  - Traefik integration well-documented: architecture diagram, DNS setup, config, verification
  - No stale tailscale serve or port-publishing references in docs
  - tailscale role code correctly cleans up legacy serve (lines 44-52)
  - ASCII diagram line 32 is 1 char too wide (formatting bug)
  - README line 106: stale `vault_backup_age_public_key` (pre-existing, not Traefik-related)
  - CLAUDE.md missing `mms_traefik_domain`/`mms_traefik_routes` in Conventions section
- 2026-02-09: Review of Auto-Deploy section on feat/renovate-autodeploy branch
  - Per-group `autodeploy_groups` feature well-documented with examples
  - Variable table matches role defaults exactly
  - deploy-services.yml `deploy_services` filtering logic verified correct
  - Grammar fix needed on line 531 ("for that group's timer fires")
  - CLAUDE.md needs autodeploy role added to roles list and Architecture section
  - Autodeploy variable naming (bare vs mms_ prefix) could use a clarifying note
  - Missing troubleshooting/rollback/disable guidance (backlog items)
  - See review-findings.md for details
- 2026-02-10: Full review of all .md files on feat/multi-ssh-keys branch (9 commits over main)
  - `mms_vm_hostname`/`mms_vm_name` split not documented in CLAUDE.md or README.md
  - `mms_vm_ssh_pubkeys` (list) not reflected in README Quick Start (still says singular "SSH public key")
  - README Quick Start step 2 file descriptions stale (VM specs moved to group_vars/all)
  - CLAUDE.md Conventions missing: variable split, SSH keys list, Tmpfs/NoNewPrivileges, Jellyfin image
  - supply-chain-hygiene-reviewer.md missing Channels DVR and Navidrome
  - CLAUDE.md roles list now correctly includes autodeploy (prior gap resolved)
  - README backup variable name now correct (`mms_backup_age_public_key`, prior gap resolved)
  - Immich templates all have Tmpfs=/run:U (prior ansible-reviewer item #27 resolved)
  - See review-findings.md for details
