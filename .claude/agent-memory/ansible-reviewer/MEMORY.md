# MMS Ansible Reviewer Memory

## Project Architecture
- Homelab media stack on Fedora 43 VM (Proxmox 9.x), rootless Podman with Quadlet systemd
- Service user: mms (3000:3000), config at /home/mms/config/, NFS data at /data
- Tailscale-only access, firewalld default zone: drop
- SELinux enforcing: :Z for local, virt_use_nfs boolean for NFS

## Variable Conventions
- Global prefix: `mms_`, secrets prefix: `vault_`
- Role defaults use role-specific prefixes (e.g., `backup_`, `storage_`, `proxmox_vm_`)
- group_vars: all/ (global + VM specs), mms/ (NFS, services, tailscale), proxmox/ (API config + cloud image)
- VM specs moved to group_vars/all so proxmox host group can resolve them
- `mms_vm_hostname` (group_vars/all): OS hostname + Tailscale node name; `mms_vm_name` (group_vars/proxmox): Proxmox display name only
- `mms_vm_ssh_pubkeys`: list of SSH public keys (was singular `mms_vm_ssh_pubkey`)

## Provisioning Flow
- provision-vm.yml: Play 1 (SSH to proxmox) creates Fedora cloud template via qm commands
- provision-vm.yml: Play 2 (connection: local) uses Proxmox API via proxmox_vm role
- Proxmox API token: vault_proxmox_api_user contains "user@realm!tokenname", split on "!" for api_user vs api_token_id

## Roles (13)
- proxmox_vm: Provision VM from cloud-init template (API calls, connection: local)
- base_system: OS config, mms user, packages, SELinux, sysctl, cloud-init wait, ~/bin/mms-services script
- podman: Rootless config, registries, storage, quadlet dir, image prune timer
- storage: NFS mounts, TRaSH-guide directory structure (NFS dirs use become_user, no explicit owner/group)
- firewall: firewalld with drop default, tailscale trusted
- tailscale: Install, auth (serve mappings removed in Traefik branch)
- quadlet_service: Generic data-driven container deployment from services/*.yml
- immich: Special-cased multi-container (server, ML, postgres, redis), ML uses python healthcheck
- open_notebook: Multi-container (SurrealDB + app), env-file secrets with vault_, curl healthcheck on app, split into setup.yml + containers.yml for Molecule testability
- traefik: Reverse proxy with file provider, Host-header routing via mms_traefik_routes
- backup: Scripts, systemd timers, retention, encryption with age
- autodeploy: Git-based auto-deploy with systemd timer, polls repo and runs deploy-services.yml
- migrate: LXC-to-VM migration with rsync, DB dump, healthchecks

## Services (13 as of 2026-02-17)
- *arr stack: prowlarr, radarr, radarr4k, sonarr, lidarr (all LSIO images, arr backup type)
- Downloads: sabnzbd (LSIO, custom backup with ini subset)
- Media servers: jellyfin (official), plex (LSIO), channels (fancybits)
- Media tools: tautulli (LSIO, Plex analytics), kometa (LSIO, Plex metadata), navidrome (music)
- Photos: immich (special multi-container role)
- AI/Research: open-notebook (lfnovo/open_notebook + SurrealDB, special multi-container role)
- Reverse proxy: traefik (official, file provider)

## Key Patterns
- Data-driven services: services/*.yml loaded by include_vars, rendered by quadlet templates
- Rootless systemd: XDG_RUNTIME_DIR + DBUS_SESSION_BUS_ADDRESS environment vars required
- Handlers pattern: daemon_reload + restart per role, all need XDG/DBUS env
- Network quadlet deployed by both podman role and deploy-services playbook (duplication)
- Immich DB secret: passed via env var + printf pipe to avoid /proc exposure
- Immich server volume: three-mount overlay -- local SSD base at /data:Z, NFS /data/upload, NFS /data/library
- Immich storage split: NFS holds user content (upload, library), local SSD holds regenerable (encoded-video, thumbs, profile, backups)
- Immich mount-check: .immich marker files in each data subdir (Immich verifies on startup)
- Immich data subdirs split: immich_nfs_dirs (upload, library) + immich_local_dirs (encoded-video, thumbs, profile, backups)
- Immich local media dir: {{ mms_config_dir }}/immich/media (on local SSD)
- Immich one-time migration block: moves generated dirs from NFS to local SSD (guarded by stat check)
- Traefik: file provider (no socket mount), Host-header routing, only container with PublishPort
- Traefik dynamic config uses watch: true, so changes are picked up without restart (but Ansible still notifies restart)
- Service definitions no longer have publish_ports; container.j2 wraps PublishPort in `is defined` guard
- container.j2 now has `Tmpfs=/run:U` (s6-overlay compat), per-service `tmpfs` list, configurable `NoNewPrivileges`
- Immich templates (4 files) still hardcoded, diverging from generic container.j2 pattern
- quadlet_service INI loop uses `loop_var: ini_setting` to avoid collision with outer loops
- Jellyfin switched from LSIO to official `jellyfin/jellyfin` (no PUID/PGID, uses UserNS=keep-id)
- mms-services.sh.j2 uses {% raw %} block to prevent Jinja2 parsing of bash ${var} syntax
- Autodeploy: Renovate creates PRs for version bumps, per-group timers poll git and run deploy-services.yml
- Autodeploy replaces podman auto-update; AutoUpdate=registry removed from Immich, update-services.yml deleted
- Autodeploy per-group: autodeploy_groups dict defines schedule + optional services filter per group
- deploy-services.yml supports optional deploy_services extra-var to filter which services are deployed
- Shared lock file (/tmp/mms-autodeploy.lock) prevents concurrent deploys across groups
- Per-group state files track last-deployed SHA independently; Galaxy dedup via marker files
- Galaxy collections pinned to exact versions in requirements.yml (Renovate manages updates via galaxy datasource)
- Project-level templates at templates/ referenced via {{ playbook_dir }}/../templates/ (established convention)
- mms-services script: tier-based start/stop ordering (infra -> immich-app -> app -> proxy)
- quadlet_service INI race fix: check-mode detect -> stop -> apply -> start (avoids config overwrite on shutdown)
- Backup role: two systems -- config backups (mms-backup.*) + API backups (mms-api-backup.*) for *arr services to NAS
- API backup uses Host-header routing through Traefik on localhost:80 (no direct container ports)
- API backup reads API keys from config.xml at runtime (no secrets in Ansible vars)
- Image pruning: two-layer approach -- weekly systemd timer (podman role) + inline post-deploy prune (autodeploy role)
- Prune units in ~/.config/systemd/user/ (not quadlet dir); Persistent=true + RandomizedDelaySec=300

## Recurring Anti-pattern: String-as-Boolean Facts
- set_fact with Jinja2 comparison produces strings "True"/"False", NOT booleans
- `not "False"` is False (works by accident), but `"False" | bool` is False (correct)
- Affected: _template_exists in provision-vm.yml, _immich_secret_needs_update in immich role, _deploy_immich/_deploy_traefik/_deploy_open_notebook in deploy-services.yml
- Fix: always use `| bool` filter, or test the raw condition directly

## Review History
See review-findings.md for detailed findings from all reviews.

## Known Issues (as of 2026-02-11)
### Resolved
- ~~Dead backup task files~~ removed
- ~~Restore playbook duplication~~ extracted to restore_service.yml
- ~~Retention logic incomplete~~ replaced with GFS in shell script
- ~~No .ansible-lint or Molecule~~ added both
- ~~No no_log on immich secrets~~ added
- ~~Podman installed in base_system too~~ moved to podman role
- ~~Proxmox API token_id was wrong (used api_user for both)~~ fixed with split('!')
- ~~Clone task used vmid instead of template vmid~~ fixed with vmid/newid
- ~~registries.conf regex escaping broken~~ fixed with double backslash
- ~~tailscale serve blocked without --bg~~ fixed
- ~~Immich ML healthcheck used curl (not available in image)~~ replaced with python urllib
- ~~VM specs inaccessible from proxmox group~~ moved to group_vars/all

### Still Open
1. Service definitions hard-code /home/mms paths instead of variables
2. Network quadlet deployed in both podman role and deploy-services.yml
3. restore_service.yml missing become/become_user/environment for rootless systemd
4. AutoUpdate=registry in container.j2 conditional is now dead code (no service sets auto_update)
5. _immich_secret_needs_update and _template_exists produce string not bool
6. CI yamllint step uses default config not .yamllint.yml
7. Molecule fixtures hardcode UID/GID 1100, should be 3000
8. migrate role defaults still reference 1100 as fallback
9. dnf clean all runs unconditionally, always reports changed
10. CLAUDE.md still references container_use_nfs (should be virt_use_nfs)
11. ~~proxmox_vm cloud-init task missing no_log (cipassword exposed in output)~~ fixed with no_log: true
12. tailscale serve reset runs unconditionally, should be guarded
13. Traefik not yet included in backup role config
14. CLAUDE.md and README.md reference deleted update-services.yml
15. ~~autodeploy SSH config task overwrites entire ~/.ssh/config~~ fixed with blockinfile
16. ~~autodeploy script uses $(hostname)~~ fixed: uses {{ inventory_hostname }} template var
17. autodeploy NOPASSWD:ALL sudoers is overly broad (documented as required for Ansible become)
18. ~~autodeploy systemd service missing After=network-online.target~~ fixed in per-group version
19. No Molecule test for autodeploy role
20. Stale per-group autodeploy units are file-deleted without stop/disable first
21. _expected_timer_files set_fact is dead code in autodeploy tasks
22. autodeploy_groups in group_vars lacks mms_ prefix (intentional override, but breaks convention)
23. No validation that autodeploy group dicts contain required 'schedule' key
24. Group names in autodeploy_groups are not validated (used in filenames and bash)
25. base_system Molecule host_vars missing mms_home and mms_quadlet_dir (converge broken by mms-services script)
26. mms-services script exits 0 even when service actions fail (silent failure)
27. ~~Immich templates missing Tmpfs=/run:U~~ fixed: added to all 4 Immich templates
28. ~~container.j2 NoNewPrivileges uses `| lower` without `| bool`~~ fixed: added `| bool` filter
29. ~~Jellyfin tmpfs /cache may need :U flag~~ fixed: changed to `/cache:U`
30. ~~sshkeys join('\n') in proxmox_vm~~ fixed: replaced with YAML block scalar for reliable newlines
31. Backup role api_backup_* variables break naming convention (should be backup_api_*)
32. Backup service units (mms-backup.service, mms-api-backup.service) missing After=network-online.target
33. api_backup_services duplicates port data from mms_traefik_routes (port field unused in script)
34. ~~README storage layout missing complete/manual directory~~ fixed: movies4k removed, manual present
35. No Molecule test for backup role
36. ~~Immich media subdir tasks use become: true (root) with owner/group on NFS (root_squash will fail)~~ partially fixed: NFS tasks now use become_user, local tasks still root
37. immich_upload_dir variable name is misleading (now only used for NFS paths, sits alongside immich_media_dir)
38. No Molecule test for immich role
39. ~~Migration block stops immich-server but not immich-ml~~ fixed: both stopped in commit adc4f6c
40. ~~Migration block-level when only checks thumbs dir~~ fixed: checks all immich_local_dirs via stat loop
41. Migrate role rsync excludes hardcode dir list instead of referencing immich_local_dirs variable
42. Backup --exclude='immich/media' assumes immich_media_dir is under mms_config_dir/immich/media (fragile coupling)
43. Local generated content (thumbs, transcodes) not backed up -- intentional but undocumented tradeoff
44. Migration mv across filesystems (NFS->local) is not atomic; rsync --remove-source-files is safer
45. NFS overlay on :Z-labeled base volume needs SELinux runtime validation (virt_use_nfs should handle it)
46. Inconsistent become/become_user between NFS and local dir creation tasks in immich role
47. ~~open_notebook env file templates missing no_log~~ fixed: no_log: true on both env templates
48. mms-services.sh get_tier() missing open-notebook-db in tier 0 (infra)
49. open_notebook HealthCmd uses curl -- verify curl exists in lfnovo/open_notebook image
50. ~~No meta/main.yml for open_notebook role~~ fixed: meta/main.yml exists
51. ~~No Molecule test for open_notebook role~~ fixed: Molecule tests added for setup.yml
52. Restore playbook chown runs after services started for open-notebook (should be before)
53. Open-notebook backup script hardcodes directory names (open-notebook, open-notebook-db) in tar command
54. Podman prune units always deployed even when podman_prune_enabled: false (dead files on disk)
55. No Molecule test for podman role prune timer tasks
