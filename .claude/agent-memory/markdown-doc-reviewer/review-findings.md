# Review Findings

## feat/gh-issue-62-image-pruning Branch Review (2026-02-18)

### Scope
All .md files on feat/gh-issue-62-image-pruning branch (1 commit over main). Key changes: weekly systemd timer (mms-image-prune.timer) for dangling Podman image pruning in podman role, inline image pruning after successful autodeploy runs in autodeploy role. New variables: podman_prune_enabled, podman_prune_schedule, autodeploy_prune_images.

### Files Reviewed
- CLAUDE.md (80 lines)
- README.md (91 lines)
- docs/wiki/Home.md (101 lines)
- docs/wiki/Getting-Started.md (77 lines)
- docs/wiki/Configuration.md (88 lines)
- docs/wiki/Common-Operations.md (93 lines)
- docs/wiki/Auto-Deploy.md (179 lines)
- docs/wiki/Troubleshooting.md (367 lines)
- roles/podman/defaults/main.yml (17 lines)
- roles/podman/tasks/main.yml (94 lines)
- roles/podman/templates/mms-image-prune.service.j2 (7 lines)
- roles/podman/templates/mms-image-prune.timer.j2 (11 lines)
- roles/autodeploy/defaults/main.yml (20 lines)
- roles/autodeploy/templates/mms-autodeploy.sh.j2 (125 lines)

### Findings
- MEDIUM: CLAUDE.md Architecture Rootless Podman bullet (line 44) missing image pruning timer
- MEDIUM: CLAUDE.md Architecture Auto-deploy bullet (line 49) missing inline image pruning on success
- MEDIUM: Auto-Deploy.md variable table (line 134) missing autodeploy_prune_images
- MEDIUM: Troubleshooting.md missing "Disk space and image pruning" section
- LOW: Common-Operations.md (line 93) missing manual image pruning section
- LOW: Configuration.md naming conventions (line 87) missing podman_ prefix example

### Verified Accurate
- All existing documentation remains accurate -- no claims broken by this branch
- CLAUDE.md services list, roles list, repository layout all correct
- README services table, architecture diagram, security section all correct
- Auto-Deploy.md existing variable table entries match code defaults
- Troubleshooting.md existing systemd/container/autodeploy debug commands all correct
- Timer unit placed in ~/.config/systemd/user/ (correct for non-Quadlet user units)
- Timer naming follows mms- prefix convention (mms-image-prune.timer)
- autodeploy_prune_images default true, rendered via Jinja2 conditional in script template
- podman_prune_enabled controls both enable and started state via ternary
- podman_prune_schedule "Sun *-*-* 05:00:00" uses valid systemd OnCalendar syntax
- RandomizedDelaySec=300 in timer prevents thundering herd

### Still Open (Pre-existing, Not Introduced by This Branch)
- BLOCKER: Config backup path mismatch in docs vs code
- All other pre-existing gaps from prior reviews remain open

---

## feat/open-notebook-backup Branch Review (2026-02-18)

### Scope
All .md files on feat/open-notebook-backup branch (2 commits over main). Key changes: Open Notebook backup/restore added to backup role and restore playbook, open_notebook role split into setup.yml + containers.yml for Molecule testability, shared Molecule pre-tasks extracted to molecule/shared/prepare_mms_user.yml, Molecule tests added for open_notebook role.

### Files Reviewed
- CLAUDE.md (78 lines)
- README.md (89 lines)
- docs/wiki/Home.md (101 lines)
- docs/wiki/Getting-Started.md (77 lines)
- docs/wiki/Configuration.md (84 lines)
- docs/wiki/Storage-Layout.md (64 lines)
- docs/wiki/Common-Operations.md (84 lines)
- docs/wiki/Backup-and-Restore.md (166 lines)
- docs/wiki/Adding-a-New-Service.md (68 lines)
- docs/wiki/Troubleshooting.md (328 lines)
- docs/wiki/Security.md (22 lines)
- docs/wiki/_Sidebar.md (23 lines)
- .claude/agents/supply-chain-hygiene-reviewer.md (first 30 lines)
- roles/backup/defaults/main.yml (54 lines)
- roles/backup/templates/mms-backup.sh.j2 (diff)
- roles/backup/templates/mms-restore.sh.j2 (diff)
- roles/backup/tasks/main.yml (diff)
- playbooks/restore.yml (diff)
- roles/open_notebook/tasks/main.yml (diff)
- roles/open_notebook/tasks/setup.yml (new)
- roles/open_notebook/tasks/containers.yml (new)
- roles/open_notebook/molecule/default/ (3 new files)
- molecule/shared/prepare_mms_user.yml (new)

### Findings
- HIGH: Backup-and-Restore.md config backups section (line 14) missing Open Notebook cold backup behavior
- HIGH: Troubleshooting.md missing Open Notebook section (Immich has one at line 302)
- MEDIUM: Storage-Layout.md directory tree (line 33) missing open-notebook/ and open-notebook-db/ under /home/mms/config/
- MEDIUM: Common-Operations.md Restore section (line 39) missing Open Notebook restore example
- MEDIUM: Backup-and-Restore.md Restore section (line 49) missing Open Notebook restore example
- LOW: CLAUDE.md Conventions missing Molecule shared pre-tasks and role split (setup.yml/containers.yml) pattern

### Verified Accurate
- CLAUDE.md:9 services list includes Open Notebook
- CLAUDE.md:50 Backups bullet correctly updated with cold backup description and SurrealDB rationale
- CLAUDE.md:56 roles list includes open_notebook
- CLAUDE.md:76 backup_* prefix convention accurately describes naming pattern
- CLAUDE.md:77 deploy resilience pattern accurately described
- README.md:22 services table includes Open Notebook with correct URL
- README.md:40 architecture diagram includes open-notebook + open-notebook-db
- README.md:85 security section correctly says Traefik (80) and Plex (32400)
- Home.md:22 services table includes Open Notebook
- Home.md:40 architecture diagram includes open-notebook containers
- Home.md:77-78 inter-container access table includes Open Notebook (8502) and Open Notebook DB (8000)
- Configuration.md:57-58 vault table includes vault_open_notebook_db_password and vault_open_notebook_encryption_key
- Adding-a-New-Service.md:71 mentions Open Notebook as multi-container example
- supply-chain-hygiene-reviewer.md:19 includes Open Notebook in services list
- Backup role defaults: backup_open_notebook_app_service and backup_open_notebook_db_service follow backup_* prefix
- Backup script: backup_open_notebook() follows same pattern as backup_immich() (cold backup)
- Restore script: restore_open_notebook() follows same pattern as restore_immich_config()
- Restore playbook: stops both containers, restores, fixes ownership, restarts in dependency order
- Molecule shared pre-tasks correctly create mms user/group/quadlet dir with UID/GID 3000

### Prior Issues Resolved on This Branch
- Open Notebook now present in README and all wiki pages (was HIGH from 2026-02-17)
- Configuration.md vault table now includes all vault variables (was HIGH from 2026-02-17)
- "Only Traefik publishes host port" corrected to include Plex 32400 (was HIGH from 2026-02-17)

### Still Open (Pre-existing, Not Introduced by This Branch)
- BLOCKER: Config backup path in docs vs code mismatch (/home/mms/backups/ vs /data/backups/config)
- MEDIUM: Traefik-Reverse-Proxy.md says mms_traefik_domain is in group_vars/mms/vars.yml (actually in all)
- MEDIUM: Auto-Deploy example two-group config missing channels, navidrome, open-notebook

---

## feat/open-notebook Branch Review (2026-02-17)

### Scope
All .md files on feat/open-notebook branch (4 commits over main). Key changes: Open Notebook service added (app + SurrealDB, own role), vault variables added, docs restructured (README slimmed, wiki pages added in docs/wiki/).

### Files Reviewed
- CLAUDE.md (78 lines)
- README.md (89 lines)
- docs/wiki/Home.md (97 lines)
- docs/wiki/Getting-Started.md (77 lines)
- docs/wiki/Configuration.md (84 lines)
- docs/wiki/Proxmox-API-Setup.md (88 lines)
- docs/wiki/Storage-Layout.md (64 lines)
- docs/wiki/Traefik-Reverse-Proxy.md (57 lines)
- docs/wiki/Security.md (22 lines)
- docs/wiki/Common-Operations.md (84 lines)
- docs/wiki/Backup-and-Restore.md (166 lines)
- docs/wiki/Auto-Deploy.md (176 lines)
- docs/wiki/Adding-a-New-Service.md (68 lines)
- docs/wiki/Troubleshooting.md (328 lines)
- docs/wiki/_Sidebar.md (23 lines)
- docs/wiki/_Footer.md (1 line)
- .claude/agents/supply-chain-hygiene-reviewer.md (185 lines)
- roles/open_notebook/ (defaults, tasks, handlers, templates)
- inventory/group_vars/all/vars.yml (67 lines)
- inventory/group_vars/mms/vars.yml (123 lines)
- inventory/group_vars/all/vault.yml.example (33 lines)
- services/plex.yml (31 lines)
- playbooks/deploy-services.yml (72 lines)
- roles/backup/defaults/main.yml (50 lines)
- roles/backup/templates/mms-backup.sh.j2 (221 lines)
- playbooks/restore.yml (83 lines)

### Findings
- BLOCKER: Config backup path documented as `/home/mms/backups/` (local SSD) in Backup-and-Restore.md:10, Storage-Layout.md:38, Common-Operations.md:44,52, Troubleshooting.md:182 -- but actual `mms_backup_dir` is `/data/backups/config` (NFS). All restore command examples use wrong path.
- HIGH: Open Notebook absent from README services table, README architecture diagram, Home.md services table and architecture diagram, Configuration.md vault variables, all other wiki pages
- HIGH: README:84, Home.md:8, Security.md:8 say "only Traefik publishes a host port (80)" but Plex publishes 32400 (services/plex.yml:6-7)
- HIGH: Configuration.md:46-54 vault table missing: vault_backup_age_public_key, vault_vm_password, vault_open_notebook_db_password, vault_open_notebook_encryption_key
- MEDIUM: Traefik-Reverse-Proxy.md:18 says mms_traefik_domain is in group_vars/mms/vars.yml; actually in group_vars/all/vars.yml:50
- MEDIUM: supply-chain-hygiene-reviewer.md:19 missing Open Notebook from services list
- MEDIUM: Auto-Deploy.md:165-173 example two-group config missing channels, navidrome, open-notebook from interactive group
- LOW: Home.md:18 Kometa URL uses `---` (three hyphens) vs README's em dash
- INFO: Open Notebook is NOT in mms_services (by design, like Immich) -- has its own role, deployed in deploy-services.yml block
- INFO: Open Notebook is NOT backed up by config backup system (not in mms_services iteration)
- INFO: Restore playbook only supports: prowlarr, radarr, radarr4k, sonarr, lidarr, jellyfin, sabnzbd, immich -- not plex, tautulli, kometa, channels, navidrome, traefik, open-notebook

### Verified Accurate
- CLAUDE.md:9 services list correctly includes Open Notebook
- CLAUDE.md:56 roles list correctly includes open_notebook
- CLAUDE.md:47 Architecture Immich bullet correctly describes volume split
- CLAUDE.md:49 Architecture auto-deploy bullet correct
- CLAUDE.md:50 Architecture backup bullet correctly describes both systems
- CLAUDE.md:77 Conventions deploy resilience pattern correct
- deploy-services.yml correctly includes Open Notebook block/rescue (lines 40-52)
- Traefik route for open-notebook correctly maps port 8502 (Next.js frontend)
- Open Notebook health check on port 5055 (FastAPI backend) is valid (both ports run in container)
- Autodeploy interactive group in inventory correctly includes open-notebook
- vault.yml.example correctly has vault_open_notebook_db_password and vault_open_notebook_encryption_key
- Getting-Started.md prerequisites correctly list NFS exports including backups
- Getting-Started.md correctly references all three vault file groups
- Proxmox-API-Setup.md permissions list is correct and detailed
- Troubleshooting.md is comprehensive and commands are accurate
- Wiki sidebar navigation covers all pages
- requirements.yml correctly lists 4 Galaxy collections with pinned versions
- Inter-container access table in Home.md: all ports match service definitions

---

## feat/immich-split-volumes Branch Review (2026-02-11)

### Scope
All .md files on feat/immich-split-volumes branch (1 commit over main). Key change: Immich volume mounts split from single NFS Volume= to three-mount overlay (local SSD base at /data:Z, NFS overlays for upload/ and library/). Generated content (thumbs, encoded-video, profile, backups) on local SSD. One-time migration block. Backup excludes regenerable content. Migrate rsync excludes regenerable dirs.

### Files Reviewed
- CLAUDE.md (76 lines)
- README.md (674 lines)
- .claude/agents/ansible-reviewer.md (185 lines)
- .claude/agents/supply-chain-hygiene-reviewer.md (185 lines)
- roles/immich/defaults/main.yml (37 lines)
- roles/immich/tasks/main.yml (379 lines)
- roles/immich/templates/immich-server.container.j2 (27 lines)
- roles/backup/templates/mms-backup.sh.j2 (199 lines)
- roles/backup/defaults/main.yml (49 lines)
- roles/migrate/tasks/immich.yml (92 lines)
- inventory/group_vars/mms/vars.yml (104 lines)
- inventory/group_vars/all/vars.yml (67 lines)

### Findings
- HIGH: README Storage Layout (line 234) /data/photos/ described as "Immich uploads" -- now only holds upload/ and library/ (user content)
- HIGH: README Storage Layout (lines 237-238) missing /home/mms/config/immich/media/ for Immich generated content
- HIGH: CLAUDE.md Architecture (line 47) Immich bullet missing volume split
- MEDIUM: CLAUDE.md Conventions missing Immich three-mount overlay pattern and variable names
- MEDIUM: README Backup section (lines 168-170) missing note that Immich config backup excludes regenerable content
- MEDIUM: README Migrate section (lines 205-210) missing note about rsync skipping regenerable dirs
- LOW: README Storage Layout /data/photos/ comment understates scope ("uploads" vs "user content")

### Verified Accurate
- Backup script --exclude='immich/media' correctly matches immich_media_dir relative path under config dir
- Backup rsync of photos dir naturally only syncs NFS content (correct by design)
- Migrate rsync excludes (thumbs, encoded-video, profile, backups) match immich_local_dirs exactly
- Container template three-mount order is correct: base first, overlays second
- immich_media_dir resolves to /home/mms/config/immich/media (mms_config_dir = /home/mms/config)
- immich_upload_dir = /data/photos (unchanged NFS mount)
- Agent .md files (ansible-reviewer, supply-chain-hygiene-reviewer) have no Immich volume references to update
- README Architecture diagram unaffected (shows container relationships, not volume mounts)
- README Prerequisites unaffected (NFS exports list unchanged)
- README Quick Start unaffected (volume split is internal)

---

## fix/base-system-packages Branch Review (2026-02-11)

### Scope
All .md files on fix/base-system-packages branch (6 commits over main). Key changes: btop replaces bpytop, movies4k directories removed, Immich/Traefik block/rescue deploy resilience, Immich volume /upload->/data, Immich media subdirectories + .immich markers, ansible-lint key-order fix, Tailscale GPG key import.

### Files Reviewed
- CLAUDE.md (75 lines)
- README.md (673 lines)
- .claude/agents/ansible-reviewer.md (185 lines)
- .claude/agents/supply-chain-hygiene-reviewer.md (185 lines)
- .claude/agent-memory/ansible-reviewer/MEMORY.md (125 lines)
- .claude/agent-memory/ansible-reviewer/review-findings.md (255 lines)
- .claude/agent-memory/markdown-doc-reviewer/MEMORY.md (107 lines)
- .claude/agent-memory/markdown-doc-reviewer/review-findings.md (220 lines)
- roles/base_system/defaults/main.yml (27 lines)
- roles/immich/defaults/main.yml (30 lines)
- roles/immich/tasks/main.yml (229 lines)
- roles/immich/templates/immich-server.container.j2 (27 lines)
- roles/immich/templates/immich.env.j2 (10 lines)
- roles/storage/defaults/main.yml (22 lines)
- playbooks/deploy-services.yml (55 lines)
- roles/migrate/defaults/main.yml (34 lines)

### Findings
- MEDIUM: CLAUDE.md Conventions missing deploy resilience pattern (block/rescue for all services including Immich/Traefik)
- LOW: Agent memory files (4 occurrences) reference stale "bpytop" instead of "btop"

### Not Affected (Verified Clean)
- No Markdown file references bpytop by name -- only agent memory files
- No Markdown file references movies4k -- README diagram correctly removes complete/movies4k on this branch
- No Markdown file references /upload container mount path or UPLOAD_LOCATION env var
- No Markdown file references Immich media subdirectories or .immich marker files
- migrate role /opt/immich/upload is the LXC source path (correct, not affected by container mount change)
- README Storage Layout /data/photos comment ("Immich uploads") remains accurate -- the NFS mount path didn't change
- Tailscale GPG key import is internal to role, not documented

### Verified Accurate
- CLAUDE.md Key Commands: all playbook paths match filesystem
- CLAUDE.md Repository Layout: all directories and roles match
- CLAUDE.md Architecture: all bullets accurate
- README Services table: unchanged and correct
- README Architecture diagram: accurate
- README Storage Layout: correctly updated (movies4k removed from complete/ tree)
- README Backup section: unchanged and accurate for this branch's scope

---

## fix/sabnzbd-ini-race-condition Branch Review (2026-02-11)

### Scope
All .md files on fix/sabnzbd-ini-race-condition branch (7 commits over main). Key changes: INI race condition fix (stop-then-apply), API-based *arr backup to NAS, SABnzbd host_whitelist for inter-container access, usenet complete/manual directory, btop package, inter-container access table in README.

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
- btop correctly added to base_system_packages (line 18); no doc change needed for utility package
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
