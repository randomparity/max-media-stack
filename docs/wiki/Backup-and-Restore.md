# Backup & Restore

MMS uses two backup systems -- config backups (local, encrypted) and API backups (\*arr services to NAS).

## Backup overview

### Config backups

- **Schedule**: Daily at 03:00 via `mms-backup.timer`
- **Location**: `/data/backups/config/` (NFS)
- **Format**: `tar.zst.age` (compressed, encrypted)
- **Retention**: 7 daily, 4 weekly, 6 monthly

Config backups capture each service's configuration directory. Immich config backups exclude locally-generated content (thumbnails, transcoded video, profile images) stored in `/home/mms/config/immich/media/` -- this content is regenerable and will be recreated automatically by Immich when needed. Plex config backups exclude the Cache, Crash Reports, Updates, and Codecs directories -- all regenerable content that Plex recreates automatically. Open Notebook uses a cold backup -- both the app and SurrealDB containers are stopped before creating a single tar archive of `open-notebook/` and `open-notebook-db/` config directories, then restarted. This is necessary because SurrealDB has no hot-dump CLI tool.

### API backups

- **Schedule**: Daily at 04:30 via `mms-api-backup.timer`
- **Location**: `/data/backups/arr-api/` (NFS)
- **Format**: Native \*arr `.zip` files
- **Retention**: 30 days
- **Services**: Prowlarr, Radarr, Radarr 4K, Sonarr, Lidarr

API backups are triggered via each service's API and downloaded through Traefik on localhost.

## Manual backup

```bash
# Run config backups for all services
ansible-playbook playbooks/backup.yml
```

### Inspecting API backups on the VM

```bash
# Check API backup timer status
systemctl --user list-timers mms-api-backup.timer

# Trigger a manual API backup
systemctl --user start mms-api-backup.service

# View API backup logs
journalctl --user -u mms-api-backup --since today

# Dry-run (logs what would happen without making changes)
DRY_RUN=true /home/mms/bin/mms-api-backup.sh
```

## Restore

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/data/backups/config/radarr/radarr-2025-01-15.tar.zst.age
```

For encrypted backups, provide the identity file path:

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/data/backups/config/radarr/radarr-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

Multi-container services like Open Notebook use the same restore command -- the playbook handles stopping/starting both containers and restoring both directories from the single archive automatically.

## Backup encryption with age

MMS encrypts config backups using `age`, a simple file encryption tool. Encryption uses a public key (safe to store in config); decryption requires the corresponding private key (identity file), which should be kept offline or in a secure location -- never on the backup server itself.

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

If you already have an ed25519 SSH key, `age` can encrypt to it directly -- no extra key generation needed:

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
  -e backup_file=/data/backups/config/radarr/radarr-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt

# With an SSH private key:
ansible-playbook playbooks/restore.yml \
  -e service_name=radarr \
  -e backup_file=/data/backups/config/radarr/radarr-2025-01-15.tar.zst.age \
  -e backup_age_identity_file=~/.ssh/id_ed25519
```

### Key management best practices

- Store the identity file (private key) **off the MMS server** -- on your workstation, in a password manager, or on an encrypted USB drive
- The public key is not sensitive and is safe to commit to the repository
- If you lose the identity file, encrypted backups cannot be recovered
- Test a restore after initial setup to confirm the key pair works end-to-end
