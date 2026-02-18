# Auto-Deploy

MMS uses [Renovate](https://docs.renovatebot.com/) to discover container image updates and systemd timers on the VM to automatically deploy changes merged to `main`. Renovate opens PRs for version bumps (auto-merging patch and minor), and per-group autodeploy timers poll the git repo on independent schedules, running `ansible-playbook` when new commits are detected.

Deploy groups let you schedule non-interactive backend services (Prowlarr, Radarr, etc.) to deploy frequently while deferring interactive services (Jellyfin, Plex, Immich) to off-hours windows when restarts won't disrupt users.

## How it works

1. Renovate scans `services/*.yml`, role defaults, and `requirements.yml` for pinned versions
2. When updates are available, Renovate opens a PR (grouped by ecosystem: LinuxServer, Immich, Galaxy)
3. Patch and minor updates auto-merge after CI passes; major updates require manual review
4. Per-group `mms-autodeploy-{group}.timer` units detect new commits and deploy their service subset

## GitHub repository setup

### 1. Generate a deploy key

On your workstation, generate an ed25519 SSH key pair for the VM to pull from GitHub:

```bash
ssh-keygen -t ed25519 -C "mms-autodeploy" -f mms_deploy_key -N ""
```

This creates `mms_deploy_key` (private) and `mms_deploy_key.pub` (public).

### 2. Add the deploy key to GitHub

In your GitHub repository settings (**Settings > Deploy keys**):

1. Click **Add deploy key**
2. Title: `mms-autodeploy`
3. Key: paste the contents of `mms_deploy_key.pub`
4. Leave **Allow write access** unchecked (read-only is sufficient)
5. Click **Add key**

### 3. Configure branch protection

In **Settings > Branches**, add a rule for `main`:

1. Check **Require a pull request before merging**
2. Check **Require status checks to pass before merging** and add `lint` as a required check
3. Check **Require branches to be up to date before merging**

### 4. Enable auto-merge

In **Settings > General > Pull Requests**, check **Allow auto-merge**.

### 5. Install Renovate

1. Go to the [Renovate GitHub App](https://github.com/apps/renovate) and install it for your repository
2. Renovate will open an onboarding PR -- review and merge it
3. Subsequent PRs will follow the schedule and rules in `renovate.json5`

## Vault variables

The autodeploy role requires two vault-encrypted secrets. Add them to `inventory/group_vars/all/vault.yml`:

```bash
ansible-vault edit inventory/group_vars/all/vault.yml
```

Add:

```yaml
# Private deploy key for git clone/fetch (contents of mms_deploy_key)
vault_autodeploy_ssh_key: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----

# Ansible vault password (so the VM can decrypt vault files during deploy)
vault_mms_vault_password: "your-vault-password"
```

Alternatively, encrypt the deploy key inline:

```bash
ansible-vault encrypt_string --name vault_autodeploy_ssh_key < mms_deploy_key
```

After adding the vault variables, delete the local key files:

```bash
rm mms_deploy_key mms_deploy_key.pub
```

## Inventory variable

The repo URL is configured in `inventory/group_vars/mms/vars.yml`:

```yaml
mms_autodeploy_repo_url: "git@github.com:randomparity/max-media-stack.git"
```

Update this if your repository URL differs.

## Deploy and verify

Run the base setup playbook to deploy the autodeploy role:

```bash
ansible-playbook playbooks/setup-base.yml
```

Then verify on the VM:

```bash
# Check per-group timers are active
systemctl --user list-timers 'mms-autodeploy-*'

# Trigger a manual deploy for a specific group
systemctl --user start mms-autodeploy-backend.service
systemctl --user start mms-autodeploy-interactive.service

# Check logs
journalctl --user -u mms-autodeploy-backend --since today
journalctl --user -u mms-autodeploy-interactive --since today

# View deploy logs (per-group)
ls ~/logs/autodeploy/deploy-backend-*.log
ls ~/logs/autodeploy/deploy-interactive-*.log
```

## Configuration

The autodeploy role accepts these defaults (override in inventory vars):

| Variable | Default | Description |
|----------|---------|-------------|
| `autodeploy_groups` | `{default: {schedule: "*-*-* *:00/30:00"}}` | Per-group deploy schedules (see below) |
| `autodeploy_branch` | `main` | Git branch to track |
| `autodeploy_playbook` | `playbooks/deploy-services.yml` | Playbook to run on changes |
| `autodeploy_timeout` | `1800` | Max deploy duration in seconds |
| `autodeploy_log_retention` | `30` | Number of log files to keep |
| `autodeploy_prune_images` | `true` | Prune dangling Podman images after successful deploy |

### Deploy groups

`autodeploy_groups` is a dict where each key is a group name with its own `schedule` and optional `services` list. Each group gets its own systemd timer+service pair (`mms-autodeploy-{group}.timer`).

A shared lock file prevents concurrent deploys across groups. Each group tracks its own last-deployed SHA in a state file, so it only deploys when there are new commits it hasn't processed yet. Timers include a 60-second randomized delay to avoid thundering-herd effects when multiple groups share the same schedule.

**Default config** (single group, deploys everything every 30 min):

```yaml
autodeploy_groups:
  default:
    schedule: "*-*-* *:00/30:00"
    # services: omitted = deploy all
```

**Two-group config** (backend every 30 min, interactive at 2 AM):

```yaml
autodeploy_groups:
  backend:
    schedule: "*-*-* *:00/30:00"
    services:
      - prowlarr
      - radarr
      - radarr4k
      - sonarr
      - lidarr
      - sabnzbd
      - traefik
  interactive:
    schedule: "*-*-* 02:00:00"
    services:
      - jellyfin
      - plex
      - tautulli
      - kometa
      - immich
      - channels
      - navidrome
      - open-notebook
```

When `services` is omitted from a group, the playbook deploys everything. When specified, only the listed services are deployed when the group's timer fires.
