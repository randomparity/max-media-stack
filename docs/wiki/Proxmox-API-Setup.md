# Proxmox API Setup

MMS uses the Proxmox API to provision and manage VMs. Create a dedicated user and API token with the minimum required permissions.

## 1. Create the user and token

In the Proxmox web UI (**Datacenter > Permissions**):

1. Go to **Users** and create a new user:
   - User name: `ansible`
   - Realm: `pam` (Linux PAM)
   - No password needed (token-only access)

2. Go to **API Tokens** and create a token for the user:
   - User: `ansible@pam`
   - Token ID: `mms`
   - **Uncheck** "Privilege Separation" (token inherits the user's permissions)

3. Copy the token secret -- it is only shown once.

Or via the CLI on the Proxmox host:

```bash
pveum user add ansible@pam
pveum user token add ansible@pam mms --privsep 0
```

## 2. Create a custom role with least-privilege permissions

```bash
pveum role add MMS-Provisioner --privs \
  "VM.Allocate VM.Clone VM.Config.Cloudinit VM.Config.CPU VM.Config.Disk VM.Config.Memory VM.Config.Network VM.Config.Options VM.Audit VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit VM.Snapshot VM.Snapshot.Rollback SDN.Use"
```

Permission breakdown:

| Permission | Used by |
|---|---|
| `VM.Allocate` | Create new VMs from clone |
| `VM.Clone` | Clone template to new VM |
| `VM.Config.Cloudinit` | Set cloud-init user, SSH keys, IP |
| `VM.Config.CPU` | Set core count |
| `VM.Config.Disk` | Resize root disk |
| `VM.Config.Memory` | Set RAM |
| `VM.Config.Network` | Set bridge/NIC |
| `VM.Config.Options` | General VM configuration |
| `VM.Audit` | Query VM info and status |
| `VM.PowerMgmt` | Start/stop VM |
| `VM.Snapshot`, `VM.Snapshot.Rollback` | Pre-migration snapshots (migrate role) |
| `Datastore.AllocateSpace` | Allocate disk on storage |
| `Datastore.Audit` | Query storage info |
| `SDN.Use` | Attach VM NIC to VLAN-tagged bridge |

## 3. Assign the role to the user

```bash
pveum acl modify /vms/<VMID> --user ansible@pam --role MMS-Provisioner
```

Replace `<VMID>` with your VM ID (e.g., `202`), or use `/vms` to grant access to all VMs on the node.

If the token needs access to clone from a template on a specific storage:

```bash
pveum acl modify /storage/<STORAGE> --user ansible@pam --role MMS-Provisioner
```

If the VM uses a VLAN tag on an SDN-managed bridge, grant `SDN.Use` on the zone:

```bash
pveum acl modify /sdn/zones/<ZONE>/<BRIDGE>/<VLAN> --user ansible@pam --role MMS-Provisioner
```

Replace `<ZONE>`, `<BRIDGE>`, and `<VLAN>` with your SDN zone name, bridge, and VLAN tag (e.g., `/sdn/zones/localnetwork/vmbr0/20`).

## 4. Store credentials in the vault

The vault expects the full `user@realm!tokenid` format:

```bash
ansible-vault edit inventory/group_vars/proxmox/vault.yml
```

```yaml
vault_proxmox_api_user: "ansible@pam!mms"
vault_proxmox_api_token_secret: "<token-secret-from-step-1>"
```
