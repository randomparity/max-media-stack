# Common Operations

Day-to-day commands for managing the media stack. Sections below cover deployment (single service, all services, full site), backup, restore, migration from existing LXC containers, lint, image pruning, log inspection, and dry-run/check-mode workflows.

## Deploy a single service

```bash
ansible-playbook playbooks/deploy-service.yml -e service_name=radarr
```

## Deploy all services

```bash
ansible-playbook playbooks/deploy-services.yml
```

## Full deployment

Provision the VM, configure the base system, and deploy all services:

```bash
ansible-playbook playbooks/site.yml

# Or step by step:
ansible-playbook playbooks/provision-vm.yml
ansible-playbook playbooks/setup-base.yml
ansible-playbook playbooks/deploy-services.yml
```

## Backup

```bash
# Run backups for all services
ansible-playbook playbooks/backup.yml
```

See [Backup & Restore](Backup-and-Restore) for details on automated timers, retention, encryption, and restore procedures.

## Restore

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/data/backups/config/radarr/radarr-2025-01-15.tar.zst.age
```

For encrypted backups, pass the identity file:

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/data/backups/config/radarr/radarr-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

Multi-container services (e.g., Open Notebook) work the same way:

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=open-notebook \
  -e backup_file=/data/backups/config/open-notebook/open-notebook-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

See [Backup & Restore](Backup-and-Restore#restoring-encrypted-backups) for full restore instructions.

## Migrate from existing LXC containers

```bash
ansible-playbook playbooks/migrate.yml -e source_host=old-lxc-host
```

This will:

1. Create a Proxmox snapshot for rollback
2. Verify SQLite integrity on source
3. Rsync config directories to the new VM (Immich skips regenerable content: thumbnails, transcoded video, profile images)
4. Fix ownership and start services
5. Verify health checks pass

## Lint

```bash
ansible-lint playbooks/ roles/
yamllint .
```

## Image pruning

Dangling container images are cleaned up automatically by a weekly timer and after each successful autodeploy. To run a manual prune:

```bash
# Prune dangling images only
podman image prune -f

# Check disk usage
podman system df
```

## Log inspection

```bash
# Run an inspection immediately
systemctl --user start mms-log-inspect.service

# Check the scheduled timer
systemctl --user status mms-log-inspect.timer
systemctl --user list-timers mms-log-inspect.timer

# Read the latest report
python3 -m json.tool ~/config/logging/inspection/latest-report.json

# Validate policies locally before deployment
scripts/generate-test-corpus \
  --scenario faulty \
  --entries 40 \
  --output /tmp/mms-faulty.jsonl
scripts/mms-log-inspect \
  --input-jsonl /tmp/mms-faulty.jsonl \
  --policy examples/log-policies \
  --output-json /tmp/mms-log-report.json \
  --fail-on critical
```

See [Observability](Observability#log-inspection-policies) for the policy schema,
notification setup, and troubleshooting notes.

## Dry run

```bash
ansible-playbook playbooks/site.yml --check --diff
```
