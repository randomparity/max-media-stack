# Review Findings

## 2026-02-12: Plex/Tautulli/Kometa Services Review (fix/various-changes)

Branch adds three new media services: Plex (media server), Tautulli (Plex analytics), and Kometa (Plex metadata manager).

### Files Changed
- services/plex.yml (new)
- services/tautulli.yml (new)
- services/kometa.yml (new)
- inventory/group_vars/mms/vars.yml (added to mms_services, mms_traefik_routes, autodeploy_groups)
- inventory/group_vars/all/vault.yml (added vault_plex_claim_token)
- inventory/group_vars/all/vault.yml.example (new, comprehensive example file)
- inventory/group_vars/proxmox/vault.yml.example (new, proxmox-specific example)
- roles/backup/templates/mms-backup.sh.j2 (added backup_plex function)
- roles/backup/templates/mms-restore.sh.j2 (added restore_plex function, case entries for tautulli/kometa)

### Findings Summary
Overall: **Good implementation following established patterns**. Service definitions are clean and consistent with existing conventions. Backup/restore logic is correct. A few issues around volume mounts, media directory exposure, and missing operational considerations.

### Critical Issues
None.

### High Priority
1. **Plex media volume exposes entire /data/media tree** — breaks least-privilege principle, exposes all movies/series/music instead of just what Plex needs
2. **Missing host_whitelist INI settings** for Plex/Tautulli (may cause API access failures through Traefik when accessed via subdomain)

### Medium Priority
3. **Tautulli cross-container volume mount** (plex logs) is fragile and bypasses container isolation
4. **No tmpfs for Plex transcoding** (will use config dir, impacts SSD wear and performance)
5. **Kometa missing media volume mount** (can't scan library metadata without access to media files)
6. **No health check for Kometa** (deployment will skip health wait, may proceed before ready)
7. **Plex backup excludes only Cache directory** (Crash Reports, Updates, Codecs could bloat backups)
8. **No Kometa dependencies declared** (should depend on plex.service to ensure startup order)

### Low Priority
9. **Plex health check uses generic /identity endpoint** (doesn't verify library accessibility)
10. **No mms-services tier for media server services** (all default to tier 2, but Plex/Jellyfin could be separate tier)
11. **vault_plex_claim_token has no usage documentation** (users won't know it's one-time-use and should be cleared)
12. **Tautulli database not in backup_db_files** (tautulli.db present but might warrant DB-level dumps for integrity)

### Positive Patterns
- Tautulli dependency `after: plex.service` is correct and follows established pattern
- backup_type assignments are appropriate (plex=custom, tautulli/kometa=arr pattern)
- Service ordering in autodeploy groups is logical (plex/tautulli/kometa together in interactive group)
- New vault.yml.example files are excellent additions for project forks and first-time setup
- Plex restore correctly preserves Cache dir (find with ! -name Cache is correct)
- Health checks use sensible intervals (60s) and appropriate endpoints
- Traefik routes follow established pattern with subdomain/container/port mapping

---

## Immich NFS/Local Split Review (2026-02-11, commit adc4f6c)

### Scope
Split Immich volume mounts: NFS for user content (upload/, library/), local SSD for generated
content (thumbs/, encoded-video/, profile/, backups/). Container template uses three-mount overlay.
One-time migration block moves generated dirs from NFS to local. Backup excludes local media.
Migrate role rsync excludes regenerable dirs.

### Findings
- HIGH: Cross-filesystem mv (NFS->local) is not atomic; interrupted move leaves inconsistent state. Recommend rsync --remove-source-files + rescue block
- MEDIUM: NFS overlay mounts on :Z-labeled base path need SELinux runtime validation (virt_use_nfs should handle it)
- MEDIUM: Migrate rsync excludes hardcode dir list instead of referencing immich_local_dirs variable
- MEDIUM: Backup --exclude='immich/media' hardcodes path instead of deriving from variable
- LOW: immich_upload_dir name increasingly confusing alongside immich_media_dir (rename to immich_nfs_dir)
- LOW: Local subdir tasks use become: true (root) while NFS tasks use become_user: mms (inconsistent)
- LOW: selectattr('stat.exists', 'defined') in block when is redundant (stat always returns exists key)

### Positive patterns
- Three-volume overlay is correct approach: local base at /data:Z, NFS overlaid for upload + library
- Variable naming improved: immich_nfs_dirs + immich_local_dirs replaces ambiguous immich_media_dirs
- Both immich-ml and immich-server stopped before migration (fixes prior #39)
- Migration stat loop checks all immich_local_dirs, not just one (fixes prior #40)
- Marker files correctly created in both NFS and local subdirectories
- Migration mv command has proper creates/removes idempotence guards
- Backup correctly excludes local generated content from config tar
- Backup rsync of /data/photos now naturally only includes user content (correct by design)
- Migrate rsync excludes align with new architecture (skip regenerable content)

### Items addressed from prior reviews
- #36 partially addressed: NFS subdir tasks now use become_user: mms
- #14 (immich_media_dirs misleading name) replaced with clearer immich_nfs_dirs + immich_local_dirs
- #39 fixed: Both immich-ml and immich-server stopped in migration block
- #40 fixed: Block-level when checks all immich_local_dirs via stat loop

---

## fix/base-system-packages Review (2026-02-11, 6 commits)

### Scope
Replace btop package fix, import Tailscale GPG key, remove movies4k directories, wrap Immich/Traefik
in block/rescue in deploy-services.yml, fix Immich volume mount /upload->/data, create Immich media
subdirectories with .immich markers, fix ansible-lint key-order.

### Findings
- HIGH: Immich media subdir/marker tasks use become: true (root) with owner/group on NFS (root_squash will fail)
- MEDIUM: New tasks placed after image pull; minor ordering preference to group with filesystem setup
- MEDIUM: immich_upload_dir variable name now misleading (mounted at /data, not /upload)
- LOW: immich_media_dirs name slightly misleading (includes non-media dirs like backups)
- LOW: Tailscale GPG key import from remote URL (standard practice, defaults correct)
- LOW: block/rescue pattern duplicated 3x (fine for now, extract if more special services added)

### Positive patterns
- /upload -> /data mount fix correctly tracks Immich upstream change
- UPLOAD_LOCATION env var properly removed (Immich uses /data default)
- block/rescue matches deploy-one-service.yml pattern exactly
- force: false on .immich markers prevents unnecessary changed reports
- Tailscale GPG key imported before dnf install (prevents interactive prompts)
- movies4k removal clean: storage defaults + README updated together
- ansible-lint key-order fix (when before block) is correct

### Items resolved from prior reviews
- README storage layout now has complete/manual directory (was #34)

---

## fix/sabnzbd-ini-race-condition Review (2026-02-11, 6 commits)

### Scope
INI race condition fix (stop-then-apply pattern), API-based *arr backup to NAS, SABnzbd host_whitelist
fix for inter-container access, usenet complete/manual directory, bpytop package, inter-container
access documentation in README.

### Findings
- MEDIUM: _ini_check variable undefined when ini_settings not defined (short-circuit saves it but fragile)
- MEDIUM: api_backup_* variable prefix breaks backup role's backup_* naming convention
- MEDIUM: API keys visible in process table via curl -H arguments (low risk for homelab)
- LOW: api_backup_timeout (600s) vs hardcoded poll timeout (300s) are disconnected
- LOW: README storage layout missing complete/manual directory
- LOW: api_backup_services port field is dead data (script routes through Traefik on :80)
- LOW: Backup service units missing After=network-online.target (has Wants but not After)

### Positive patterns
- INI race fix is well-designed: check-mode detect -> stop -> apply -> start
- Comment block clearly explains WHY the stop-then-start is needed
- API backup script: NAS mount check, health checks, daily idempotent skip, temp-then-rename, dry-run, error counting
- API backup reads keys from config.xml at runtime (no secrets in Ansible vars)
- Handler and template patterns match existing backup role exactly
- SABnzbd host_whitelist correctly adds container hostname for inter-container DNS
- README inter-container access table is useful operational documentation

---

## feat/multi-ssh-keys Review (2026-02-10, 7 commits)

### Scope
Decouples VM hostname from Proxmox display name (mms_vm_hostname vs mms_vm_name), adds multi-SSH-key
support, fixes INI loop_var collision in quadlet_service, adds Tmpfs=/run:U to container.j2 for
s6-overlay compat, switches Jellyfin to official image, adds per-service tmpfs and configurable
NoNewPrivileges to container template, wraps mms-services.sh in {% raw %} block.

### Findings
- MEDIUM: Immich templates (4 files) missing Tmpfs=/run:U, diverging from generic container.j2
- MEDIUM: NoNewPrivileges uses `| lower` without `| bool` normalization (fragile for non-bool inputs)
- LOW: Jellyfin tmpfs /cache may need :U flag for correct rootless ownership
- LOW: sshkeys join('\n') -- Jinja2 single-quote escape behavior needs end-to-end validation
- LOW: Jellyfin health_cmd relies on curl presence in official image (acceptable, but document)

### Positive patterns
- mms_vm_hostname/mms_vm_name split is clean, fully propagated, well-scoped
- Old mms_vm_ssh_pubkey (singular) fully cleaned up, no stale references
- loop_var: ini_setting prevents real collision bug in outer-loop contexts
- Tmpfs=/run:U is correct fix for rootless Podman with s6-overlay preinit
- Configurable no_new_privileges is forward-looking (some containers need it off)
- Per-service tmpfs list is a good data-driven extension
- {% raw %} block correctly protects bash variable syntax from Jinja2
- Molecule fixture updated for mms_vm_hostname rename
- no_log: true on cloud-init task (resolves prior review item #11)
- Proxmox infra values updated (API host, node, storage names)

### Items resolved from prior reviews
- proxmox_vm cloud-init task now has no_log: true (was #11)

---

## mms-services Maintenance Script Review (fix/sabnzbd-host-whitelist, 2026-02-10)

### Scope
New mms-services shell script template deployed to ~/bin/ by base_system role. Discovers Quadlet
container services dynamically, manages start/stop with tier-based dependency ordering
(infra -> immich-app -> app -> proxy). Added base_system_home default and two deploy tasks.

### Findings
- HIGH: base_system Molecule host_vars missing mms_home and mms_quadlet_dir (converge will fail)
- MEDIUM: do_action swallows systemctl failures (exits 0 even when services fail)
- MEDIUM: 2>/dev/null on systemctl hides diagnostic error messages
- LOW: become: true on new tasks is redundant (play already sets become: true)
- LOW: "${action}ing" produces "stoping" (bad gerund)
- LOW: Tier categorization hard-coded in script (acceptable for homelab scale)
- LOW: base_system_home variable placed out of logical order in defaults

### Positive patterns
- Dynamic service discovery from .container files (no hard-coded service list)
- set -euo pipefail in generated script
- Template src path follows established {{ playbook_dir }}/../templates/ convention
- base_system_home correctly wraps mms_home through role indirection
- Task ordering correct: user create -> bin dir -> script deploy -> linger enable
- Both Ansible tasks are fully idempotent (file module + template module)

---

## Per-Group Autodeploy Schedules Review (feat/renovate-autodeploy, 2026-02-09)

### Scope
Evolves single autodeploy timer into per-group model. Each group gets own systemd timer+service
pair with independent schedule and optional service filter. Shared lock prevents concurrent deploys.
deploy-services.yml gains optional deploy_services filtering. Legacy single-unit files cleaned up.

### Findings
- MEDIUM: Stale per-group units deleted without stop/disable (running timer persists in memory)
- MEDIUM: _deploy_immich/_deploy_traefik use >- folding (string-as-boolean, saved by | bool)
- LOW: _expected_timer_files set_fact is dead code (never referenced)
- LOW: autodeploy_groups in group_vars lacks mms_ prefix (intentional but breaks convention)
- LOW: No validation that group dicts contain required 'schedule' key
- LOW: Group names not validated for safe use in filenames/bash

### Positive patterns
- Shared lock across groups prevents concurrent deploys on shared git repo
- Per-group state files and marker-based Galaxy dedup are well-designed
- Legacy cleanup properly stops/disables before removing (good pattern)
- intersect filter in deploy-services.yml prevents deploying unknown services
- Handler loop over dict2items correctly enables all group timers
- blockinfile for SSH config (fixes prior review item #15)
- After=network-online.target added to service template (fixes prior review item #18)

### Items resolved from prior reviews
- SSH config now uses blockinfile (was #15)
- Script uses {{ inventory_hostname }} not $(hostname) (was #16)
- Service unit has After=network-online.target (was #18)

---

## Autodeploy + Renovate Review (main, 2026-02-09)

### Scope
New autodeploy role (git poll + systemd timer), Renovate config for automated version PRs,
removal of podman auto-update (AutoUpdate=registry from Immich, update-services.yml deleted),
pinned Galaxy collection versions, simplified traefik image variable, Immich renovate annotation.

### Findings
- HIGH: NOPASSWD:ALL sudoers for mms user is overly broad (required for Ansible become mechanism)
- HIGH: SSH config task overwrites entire ~/.ssh/config (should use blockinfile)
- MEDIUM: $(hostname) in deploy script may not match inventory hostname mms-vm
- MEDIUM: ansible-galaxy install --force always runs with changed_when: false (hides real state)
- MEDIUM: CLAUDE.md and README.md still reference deleted update-services.yml
- MEDIUM: No validation that autodeploy_repo_url is set (timer will silently fail)
- LOW: systemd service missing After=network-online.target (has Wants but not After)
- LOW: Lock file in /tmp is world-writable (DoS risk, tmpfiles.d cleanup risk)
- LOW: Stale lock recovery has minor race condition between rmdir and mkdir
- LOW: Traefik image variable lost mms_ override capability (OK since Renovate manages it)

### Positive patterns
- Role structure follows backup role pattern closely (clean, consistent)
- Atomic lock via mkdir, stale lock detection, log rotation
- Conditional Galaxy update in script (only when requirements.yml changes)
- Secrets handling: no_log on SSH key and vault password, guarded by is defined
- Renovate config well-structured: 4 custom managers, sensible auto-merge policy
- AutoUpdate=registry correctly removed from Immich (was conflicting with pinned versions)

---

## fix/dry-run-issues Review (2026-02-08, 14 commits)

### Scope
Branch adds: Fedora cloud template creation, Proxmox API token fix, UID/GID change to 3000,
SELinux boolean change to virt_use_nfs, registries.conf regex fix, ContainerName in quadlet,
tailscale serve --bg, Immich ML python healthcheck, Immich secret via env var + printf,
dnf clean all + cloud-init wait, storage role become_user, VLAN support.

### Findings
- HIGH: dnf clean all unconditional, always changed (non-idempotent, noisy)
- HIGH: _template_exists is string "True"/"False", `not` works by accident (same as _immich_secret_needs_update)
- MEDIUM: Template creation has no partial-failure recovery (block/rescue recommended)
- MEDIUM: Molecule fixtures still use UID/GID 1100 (should be 3000)
- MEDIUM: Storage NFS dir tasks lost owner/group/mode, relies on NFS server config (implicit assumption)
- MEDIUM: CLAUDE.md and memory files reference container_use_nfs but code uses virt_use_nfs
- LOW: tailscale serve failed_when: false swallows all errors
- LOW: Template cleanup only runs when template didn't exist; stale files possible
- LOW: cloud-init wait has failed_when: false without explanatory comment
- LOW: Proxmox API params repeated 6 times in proxmox_vm role

### Positive changes
- API token_id/api_user split correctly resolves Proxmox auth
- vmid/newid clone semantics fixed
- Variable scoping (group_vars/all) solves cross-group access
- Immich secret via env var is more secure than stdin
- Python healthcheck removes curl dependency from ML image
- tailscale serve --bg prevents blocking
- ContainerName gives stable DNS names in Podman network

---

## fix/bug-fix-branch Review (2026-02-08, 15 commits)

### Addressed from initial review
- Immich secret create now has no_log: true (was missing)
- Restore.yml duplication extracted into restore_service.yml
- Dead backup task files removed (arr.yml, jellyfin.yml, etc.)
- Retention logic replaced with proper GFS in shell script
- Podman package moved from base_system to podman role (no longer installed twice)

### New findings (this branch)
- HIGH: restore_service.yml missing become/become_user/environment for rootless systemd stop/start
- HIGH: _immich_secret_needs_update uses >- folding, produces string "True"/"False" not bool; when conditions may misbehave
- MEDIUM: AutoUpdate=registry in container.j2 conflicts with pinned image versions
- MEDIUM: quadlet_service Molecule test missing mms_network_name variable (converge will fail)
- MEDIUM: CI yamllint step missing -c .yamllint.yml (uses default config, not project config)
- MEDIUM: .ansible-lint suppresses no-changed-when globally (should be targeted)
- LOW: restore_service.yml decrypt task missing changed_when
- LOW: Backup script uses grep -oP (PCRE) -- works on Fedora but not universally portable

### Still open from initial review
- immich.env.j2: DB_PASSWORD no longer in plaintext (uses Secret=), but env file still has no password field -- RESOLVED
- Service definitions still hard-code /home/mms paths -- NOT addressed
- Network quadlet still deployed in both podman role and deploy-services -- NOT addressed on this branch

---

## feat/add-traefik-proxy Full Review (2026-02-09, 9 commits)

### Scope
Adds Traefik reverse proxy role, removes per-service port publishing, removes Tailscale serve
mappings, adds pre-pull image pattern to quadlet_service/immich, adds cloud-init password for
VM console access, adds VM description with service links, bumps RAM to 16GB, updates docs.

### Findings
- HIGH: proxmox_vm cloud-init task passes cipassword with no no_log (password exposed in output)
- MEDIUM: Traefik AutoUpdate=registry conflicts with pinned image (v3.3); proxy outage if bad update
- MEDIUM: tailscale serve reset runs unconditionally with no guard; will silently wipe future manual config
- MEDIUM: mms_traefik_domain has real domain (media.drc.nz) in group_vars/all (fine for private repo)
- LOW: Dynamic config task does not notify handler (correct: watch: true picks it up, and start task covers cold start)
- LOW: No Molecule test for traefik role yet

### Positive patterns
- File provider avoids socket mount (security win)
- Clean separation: static config + dynamic config + quadlet
- Handlers follow established project pattern (daemon_reload + restart + become/env)
- container.j2 publish_ports conditional is correct and backward-compatible
- Pre-pull image pattern in quadlet_service and immich prevents systemd timeout on first boot
- First-boot health timeout (300s vs 120s) is a good operational improvement
- Tailscale serve cleanup is safe (file removal + reset)
- Comprehensive documentation updates in README, CLAUDE.md
- immich_port dead variable was cleaned up (removed from defaults)
- Dynamic config no longer notifies restart (fixed from earlier review; watch: true is correct approach)

---

## Initial Implementation Review (feat/initial-implementation, 2026-02-07, 13 commits)

### High-priority
- immich.env.j2 line 7: DB_PASSWORD in plaintext env file AND Secret= in quadlet (conflicting, password exposed in .env)
- Immich secret create tasks missing no_log: true (password appears in logs)
- Service definitions hard-code /home/mms paths instead of using {{ mms_home }}/{{ mms_config_dir }}
- restore.yml: massive code duplication, all command tasks lack idempotence guards
- Backup Ansible tasks (arr.yml, jellyfin.yml etc.) duplicate logic in mms-backup.sh.j2 script

### Medium-priority
- Network quadlet deployed in podman role AND deploy-services.yml (will always show changed on second)
- Retention logic in retention.yml calculates daily/weekly cutoffs but only deletes by monthly
- base_system handlers/main.yml has sysctl handler that is never notified
- deploy-services.yml has inline tasks for network that should be in a role or pre_tasks
- become: true at ansible.cfg level means ALL plays escalate; provision-vm.yml runs as root on localhost unnecessarily

### Low-priority
- Container health_cmd uses curl but LinuxServer images may not have curl (busybox wget instead)
- backup_age_identity_file referenced in restore.yml but never defined in defaults
- Tailscale serve script idempotence: checks port in status output but serve --https syntax may not match
- podman role packages already listed in base_system_packages (podman installed twice)
