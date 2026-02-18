# Security

MMS follows a defense-in-depth approach with multiple layers of isolation and access control.

## Network isolation

- **Tailscale only**: The default firewalld zone is `drop`; only the `tailscale0` interface is in the `trusted` zone. The VM is not reachable from the LAN.
- **Minimal port exposure**: Only Traefik (port 80) and Plex (port 32400) publish host ports. All other services are internal to the container network (`mms.network`).
- **HTTP only**: There is no TLS at Traefik -- the Tailscale WireGuard tunnel provides end-to-end encryption for all traffic. Adding TLS would be redundant and add certificate management complexity.

## Container security

- **Rootless Podman**: All containers run as the unprivileged `mms` user (UID/GID 3000:3000). No containers run as root.
- **No socket mount**: Traefik uses the file provider to discover routes. The Podman socket is never mounted into any container, eliminating a common container escape vector.
- **SELinux enforcing**: Config volumes use `:Z` for private labeling. NFS volumes rely on the `virt_use_nfs` SELinux boolean instead of `:z`/`:Z` labels.

## Secrets management

- **Ansible Vault**: All sensitive values (API tokens, database passwords, deploy keys) are stored in `ansible-vault` encrypted files.
- **Vault password file**: Stored at `~/.vault_pass_mms` with `0600` permissions on the Ansible control machine.
- **Backup encryption**: Config backups are encrypted with `age` before storage. The private key (identity file) is kept off the MMS server. See [Backup & Restore](Backup-and-Restore#backup-encryption-with-age) for details.
