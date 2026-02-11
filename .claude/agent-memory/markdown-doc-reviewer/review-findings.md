# Review Findings

## fix/sabnzbd-ini-race-condition Branch Review (2026-02-11)

### Scope
All .md files on fix/sabnzbd-ini-race-condition branch (7 commits over main). Key changes: INI race condition fix (stop-then-apply), API-based *arr backup to NAS, SABnzbd host_whitelist for inter-container access, usenet complete/manual directory, bpytop package, inter-container access table in README.

### Files Reviewed
- CLAUDE.md (71 lines)
- README.md (642 lines)
- .claude/agents/supply-chain-hygiene-reviewer.md (185 lines)
- .claude/agents/ansible-reviewer.md (185 lines)
- roles/backup/defaults/main.yml (46 lines)
- roles/backup/tasks/main.yml (127 lines)
- roles/backup/templates/mms-api-backup.sh.j2 (231 lines)
- roles/backup/templates/mms-api-backup.service.j2 (15 lines)
- roles/backup/templates/mms-api-backup.timer.j2 (11 lines)
- roles/backup/templates/mms-backup.service.j2 (15 lines)
- roles/backup/handlers/main.yml (28 lines)
- roles/quadlet_service/tasks/main.yml (183 lines)
- roles/storage/defaults/main.yml (24 lines)
- roles/base_system/defaults/main.yml (27 lines)
- services/sabnzbd.yml (21 lines)
- inventory/group_vars/mms/vars.yml (98 lines)

### Findings
- HIGH: README Backup section (lines 157-167) missing API backup system entirely (04:30, *arr to NAS, 30-day retention)
- HIGH: README Storage Layout (lines 190-208) missing /data/backups/ NFS mount
- HIGH: README Prerequisites (line 79) missing "backups" in NFS exports list
- MEDIUM: CLAUDE.md Architecture (lines 44-49) missing backup subsystem bullet
- MEDIUM: CLAUDE.md Conventions (lines 59-70) missing INI race pattern, host_whitelist pattern, backup_api_* prefix
- MEDIUM: README Backup section retention line (167) conflates config and API backup retention policies
- LOW: No manual trigger/log commands for API backup in README (Auto-Deploy section has this pattern)
- LOW: supply-chain-hygiene-reviewer.md services list still missing Channels DVR and Navidrome (pre-existing)

### Verified Accurate
- Variable rename api_backup_* -> backup_api_* fully applied in code (defaults, script template); no stale doc refs
- After=network-online.target present in both mms-backup.service.j2 and mms-api-backup.service.j2
- Inter-container access table (README lines 49-73): all hostnames, ports, and URLs match service definitions and mms_traefik_routes
- Storage layout diagram correctly includes complete/manual (line 202)
- SABnzbd host_whitelist in services/sabnzbd.yml correctly has both FQDN and bare hostname
- backup_api_services in defaults match the four *arr services in mms_services
- backup_api_schedule default "04:30" does not conflict with backup_schedule "03:00"
- NFS mount for /data/backups added in inventory/group_vars/mms/vars.yml lines 23-25
- bpytop correctly added to base_system_packages (line 18); no doc change needed for utility package
- CLAUDE.md Key Commands still accurate; no new playbooks introduced
- CLAUDE.md roles list still accurate (backup role already listed)
- README.md Services table unchanged and correct

---

## feat/multi-ssh-keys Branch Review (2026-02-10)

### Scope
All .md files in the repository, cross-referenced against codebase on feat/multi-ssh-keys branch (9 commits over main). Key changes: mms_vm_hostname/mms_vm_name split, multi-SSH-key support, Tmpfs=/run:U in container template + Immich templates, per-service tmpfs, configurable NoNewPrivileges, Jellyfin official image, INI loop_var fix.

### Files Reviewed
- CLAUDE.md (67 lines)
- README.md (615 lines)
- .claude/agents/supply-chain-hygiene-reviewer.md (185 lines)
- .claude/agents/ansible-reviewer.md (185 lines)
- .claude/agent-memory/ansible-reviewer/MEMORY.md (115 lines)
- .claude/agent-memory/ansible-reviewer/review-findings.md (228 lines)
- inventory/group_vars/all/vars.yml (66 lines)
- inventory/group_vars/proxmox/vars.yml (19 lines)
- inventory/group_vars/mms/vars.yml (95 lines)
- templates/quadlet/container.j2 (53 lines)
- services/jellyfin.yml (17 lines)
- roles/proxmox_vm/defaults/main.yml (35 lines)
- roles/proxmox_vm/tasks/main.yml (101 lines)
- roles/base_system/defaults/main.yml (26 lines)
- roles/tailscale/defaults/main.yml (6 lines)
- roles/quadlet_service/tasks/main.yml (129 lines)
- roles/immich/templates/ (4 .container.j2 files)

### Findings
- HIGH: README.md:71 says "SSH public key" (singular) and points to group_vars/mms; keys are now a list in group_vars/all
- HIGH: README.md:70-72 Quick Start step 2 file descriptions are stale (VM specs and SSH keys moved from mms to all)
- HIGH: CLAUDE.md missing mms_vm_hostname/mms_vm_name split in Conventions (key architectural decision)
- MEDIUM: CLAUDE.md Conventions missing Tmpfs=/run:U, per-service tmpfs, configurable NoNewPrivileges
- MEDIUM: CLAUDE.md Conventions missing Jellyfin official image note (no PUID/PGID)
- MEDIUM: supply-chain-hygiene-reviewer.md:19 services list missing Channels DVR and Navidrome

### Previously Flagged Issues Now Resolved
- README vault_backup_age_public_key -> now correctly mms_backup_age_public_key
- CLAUDE.md roles list now includes autodeploy
- CLAUDE.md Architecture section now has auto-deploy/Renovate bullet
- Immich templates now have Tmpfs=/run:U (ansible-reviewer item #27)
- sshkeys join('\n') replaced with YAML block scalar (ansible-reviewer item #30)
- Jellyfin /cache tmpfs has :U flag (ansible-reviewer item #29)
- CLAUDE.md Conventions now includes Traefik routing line

### Verified Accurate
- CLAUDE.md Key Commands: all 8 playbook commands match filesystem (site, deploy-service, deploy-services, backup, restore, migrate, provision-vm, setup-base)
- CLAUDE.md Repository Layout: all directories match; roles list includes all 12 roles including autodeploy
- CLAUDE.md Architecture: 6 bullets accurate (Rootless Podman, data-driven, Traefik, Immich, Secrets, Auto-deploy)
- CLAUDE.md Access line: correctly says Traefik reverse proxy on port 80
- README.md Services table: 9 services with correct subdomain URLs match mms_traefik_routes
- README.md Architecture diagram: UID/GID correctly 3000:3000, traefik as entry point
- README.md Proxmox API Token Setup: SDN.Use correctly added with explanation and permission command
- README.md Auto-Deploy section: all accurate (config table, examples, vault vars)
- README.md Traefik, Backup, Restore, Security sections: all accurate
- UID/GID consistently 3000:3000 across all docs
- No stale references to update-services.yml in any doc
- No stale references to LSIO/linuxserver in any doc
- container.j2 template: Tmpfs=/run:U present, per-service tmpfs loop present, NoNewPrivileges configurable
- All 4 Immich container templates have Tmpfs=/run:U
- Jellyfin service definition: official image, /cache:U tmpfs, no PUID/PGID
- base_system defaults: hostname from mms_vm_hostname (line 7)
- tailscale defaults: hostname from mms_vm_hostname (line 2)
- proxmox_vm defaults: name from mms_vm_name (line 14)
- proxmox_vm tasks: sshkeys uses YAML block scalar with for loop (lines 59-62)
- quadlet_service tasks: INI loop uses loop_var: ini_setting (line 125)

---

## fix/dry-run-issues Branch Review (2026-02-08)

### Scope
All .md files in the repository, cross-referenced against codebase on fix/dry-run-issues branch (15 commits over main).

### Files Reviewed
- CLAUDE.md (67 lines)
- README.md (378 lines)
- .claude/agents/supply-chain-hygiene-reviewer.md (185 lines)
- .claude/agents/ansible-reviewer.md (185 lines)
- .claude/agent-memory/ansible-reviewer/MEMORY.md (73 lines)
- .claude/agent-memory/ansible-reviewer/review-findings.md (81 lines)

### Findings
- HIGH: CLAUDE.md:47 says UID 1100:1100, inventory says 3000:3000
- HIGH: README.md:25 ASCII diagram says 1100:1100, should be 3000:3000
- MEDIUM: supply-chain-hygiene-reviewer.md:18 says 1100:1100, should be 3000:3000
- MEDIUM: ansible-reviewer MEMORY.md item #10 claims container_use_nfs unfixed, but a222f8c fixed it
- MEDIUM: testapp.yml molecule fixture missed by a222f8c (PUID/PGID still 1100)
- LOW: Fedora version not stated in CLAUDE.md or README.md prose
- LOW: No CHANGELOG for breaking UID/GID change

### Verified Accurate
- CLAUDE.md Key Commands: all playbook paths match filesystem
- CLAUDE.md Repository Layout: all directories and roles match
- CLAUDE.md Conventions: SELinux boolean correctly says virt_use_nfs
- README.md Services table: ports match service definitions
- README.md Prerequisites: includes SSH root access (commit 09e318e)
- README.md Quick Start commands: all playbook names exist
- README.md Storage Layout: matches TRaSH Guides pattern
- README.md "Adding a New Service": references correct files and variable names

## feat/add-traefik-proxy Branch Review (2026-02-08)

### Scope
CLAUDE.md (68 lines) and README.md (430 lines) on feat/add-traefik-proxy branch, cross-referenced against traefik role, inventory, service definitions, and tailscale role.

### Findings
- MEDIUM: README.md:32 ASCII diagram line is 61 chars (should be 60, one extra space)
- MEDIUM: README.md:106 lists `vault_backup_age_public_key` (doesn't exist); actual var is `mms_backup_age_public_key` in vars.yml
- LOW: CLAUDE.md Conventions section does not mention `mms_traefik_domain` or `mms_traefik_routes`
- LOW: README.md Traefik section missing redeployment instructions after route changes
- LOW: README.md "Adding a New Service" missing DNS reminder
- LOW: ansible-reviewer MEMORY.md:26 still describes tailscale serve mappings (stale)
- LOW: Dead variable `immich_port` in roles/immich/defaults/main.yml (never used in templates)

### Verified Accurate
- CLAUDE.md Access line: correctly says "Traefik reverse proxy on port 80, Tailscale only"
- CLAUDE.md Architecture: includes Traefik bullet with file provider and mms_traefik_routes
- CLAUDE.md Roles list: includes traefik role
- README.md Architecture diagram: correctly shows traefik (:80) as single entry point
- README.md Traefik section: DNS setup, configuration, verification all accurate
- README.md Security section: correctly describes no socket mount, HTTP-only rationale
- README.md Services table URLs: match mms_traefik_routes subdomains + mms_traefik_domain
- Traefik dynamic template: routes match mms_traefik_routes structure documented in README
- Tailscale role: correctly cleans up legacy serve config (lines 44-52)
- No service definitions have publish_ports (confirmed: all 6 service YAML files checked)
- Immich server container template: no PublishPort directive
- deploy-services.yml: traefik role deployed last (after quadlet_service and immich)
- Collections in requirements.yml match README Prerequisites

## feat/renovate-autodeploy Branch Review (2026-02-09)

### Scope
Auto-Deploy section of README.md (lines 361-532) and CLAUDE.md on feat/renovate-autodeploy branch, cross-referenced against autodeploy role (defaults, tasks, templates, handlers), deploy-services.yml playbook, renovate.json5, and inventory vars.

### Files Reviewed
- README.md (~600 lines, focused on lines 361-532)
- CLAUDE.md (68 lines)
- roles/autodeploy/defaults/main.yml (18 lines)
- roles/autodeploy/tasks/main.yml (227 lines)
- roles/autodeploy/templates/mms-autodeploy.sh.j2 (119 lines)
- roles/autodeploy/templates/mms-autodeploy.service.j2 (15 lines)
- roles/autodeploy/templates/mms-autodeploy.timer.j2 (12 lines)
- roles/autodeploy/handlers/main.yml (22 lines)
- playbooks/deploy-services.yml (36 lines)
- renovate.json5 (75 lines)
- inventory/group_vars/mms/vars.yml (80 lines)

### Findings
- MEDIUM: CLAUDE.md:54 roles list missing `autodeploy`
- MEDIUM: CLAUDE.md Architecture section has no auto-deploy/Renovate bullet
- MEDIUM: README.md:486-494 variable table uses bare role default names but `autodeploy_repo_url` derives from `mms_autodeploy_repo_url`; naming relationship not explained
- LOW: README.md:531 grammar: "for that group's timer fires" -> "when the group's timer fires"
- LOW: README.md:498-500 no mention of RandomizedDelaySec=60 timer jitter
- LOW: No troubleshooting, rollback, or disable guidance for auto-deploy

### Verified Accurate
- Configuration table variable names and defaults match roles/autodeploy/defaults/main.yml exactly
- `autodeploy_groups` default (single group, 30-min schedule) matches code
- Two-group example matches actual inventory at inventory/group_vars/mms/vars.yml:65-79
- deploy-services.yml `deploy_services` variable filtering logic correctly handles both omitted and specified services
- Immich and Traefik are correctly handled as special cases in deploy-services.yml (lines 15-18, 27-35)
- Script template correctly passes `deploy_services` as JSON via `-e` flag (line 93)
- Shared lock file across groups confirmed in script (mkdir-based atomic lock)
- Per-group state file tracking confirmed (STATE_FILE="${STATE_DIR}/last-deployed-${GROUP}")
- Stale lock detection confirmed (compares lock age to TIMEOUT)
- Galaxy collection dedup across groups confirmed (REQS_MARKER mechanism)
- Vault variables (`vault_autodeploy_ssh_key`, `vault_mms_vault_password`) match tasks/main.yml usage
- setup-base.yml includes autodeploy role (line 11)
- renovate.json5 package rules match README description (auto-merge patch/minor, manual major)
- renovate.json5 grouping matches README (LinuxServer, Immich, Galaxy)
- Legacy single-unit cleanup present in tasks (lines 122-151)
