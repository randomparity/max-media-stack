# Configuration

MMS uses Ansible inventory variables and vault-encrypted secrets to configure the deployment.

## Inventory files

### `inventory/group_vars/all/vars.yml`

Global settings that apply to the entire deployment:

- VM specs (CPU, memory, disk)
- SSH public keys for cloud-init
- Timezone
- User and path settings (the `mms` user, config/backup directories)
- Traefik domain (`mms_traefik_domain`)
- Backup age public key (`mms_backup_age_public_key`)

### `inventory/group_vars/proxmox/vars.yml`

Proxmox-specific settings:

- API host and node name
- Storage backend
- VM display name (`mms_vm_name`)

### `inventory/group_vars/mms/vars.yml`

Service-level configuration:

- NFS mount definitions
- Services list (`mms_services`)
- Traefik routes (`mms_traefik_routes`)
- Autodeploy config (`mms_autodeploy_repo_url`, `autodeploy_groups`)

## Secrets

Secrets are stored in vault-encrypted files. Use `ansible-vault edit` to modify them.

### `inventory/group_vars/proxmox/vault.yml`

| Variable | Description |
|----------|-------------|
| `vault_proxmox_api_user` | API token in `user@realm!tokenid` format (e.g., `ansible@pam!mms`) |
| `vault_proxmox_api_token_secret` | Token secret UUID from Proxmox |

### `inventory/group_vars/all/vault.yml`

| Variable | Description |
|----------|-------------|
| `vault_tailscale_auth_key` | Tailscale pre-auth key |
| `vault_immich_db_password` | Immich PostgreSQL password |
| `vault_plex_claim_token` | Plex claim token for initial setup (get from https://plex.tv/claim, clear after first run) |
| `vault_autodeploy_ssh_key` | Private deploy key for git clone/fetch (see [Auto-Deploy](Auto-Deploy#vault-variables)) |
| `vault_mms_vault_password` | Ansible vault password for VM-side deploys (see [Auto-Deploy](Auto-Deploy#vault-variables)) |

### Managing vault files

Create a vault password file (one-time setup):

```bash
echo 'your-vault-password' > ~/.vault_pass_mms
chmod 0600 ~/.vault_pass_mms
```

Edit encrypted vault files:

```bash
ansible-vault edit inventory/group_vars/proxmox/vault.yml
ansible-vault edit inventory/group_vars/all/vault.yml
```

Encrypt plaintext vault files (fresh install):

```bash
ansible-vault encrypt inventory/group_vars/proxmox/vault.yml
ansible-vault encrypt inventory/group_vars/all/vault.yml
```

## Variable naming conventions

- `mms_` prefix -- global project variables
- `vault_` prefix -- encrypted secrets
- Role-specific prefixes (e.g., `autodeploy_`, `backup_`) -- role defaults in `roles/<name>/defaults/main.yml`
