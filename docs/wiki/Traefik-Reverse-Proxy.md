# Traefik Reverse Proxy

Services are accessed via hostname-based routing through a Traefik reverse proxy instead of per-service port numbers. Traefik uses the **file provider** -- Ansible generates the routing config from `mms_traefik_routes`, so no Docker/Podman socket is mounted.

## DNS setup

Configure wildcard DNS so `*.media.example.com` resolves to your VM's Tailscale IP:

1. Find your VM's Tailscale IP: `tailscale ip -4` on the VM
2. Add a wildcard DNS record pointing to that IP. How you do this depends on your DNS setup:
   - **Tailscale MagicDNS**: Not applicable -- use a custom DNS server or `/etc/hosts`
   - **Local DNS (Pi-hole, AdGuard, etc.)**: Add a wildcard record `*.media.example.com` -> `<tailscale-ip>`
   - **Public DNS**: Add a wildcard A record for `*.media.example.com` -> `<tailscale-ip>` (safe since the IP is only reachable via Tailscale)
   - **Hosts file** (quick test): Add entries for each service in `/etc/hosts` on your client

## Configuration

Set your domain in `inventory/group_vars/all/vars.yml`:

```yaml
mms_traefik_domain: media.example.com   # Replace with your actual domain
```

Routes are defined in `mms_traefik_routes`. To add a route for a new service:

```yaml
mms_traefik_routes:
  myservice:
    subdomain: myservice          # -> myservice.media.example.com
    container: myservice          # Container name on mms.network
    port: 8080                    # Container's internal HTTP port
```

After changing `mms_traefik_routes`, re-run the deploy playbook to apply:

```bash
ansible-playbook playbooks/deploy-services.yml
```

## Verifying

After deployment, test from any Tailscale client (once DNS is configured):

```bash
# Quick check from the VM itself
curl -H "Host: radarr.media.example.com" http://localhost

# From a Tailscale client with DNS configured
curl http://radarr.media.example.com
```

## How it works

Traefik is the only container that uses Ansible-managed host port publishing (port 80). Plex also publishes port 32400 directly for client compatibility. All other services are internal to the `mms.network` bridge. Traefik routes incoming HTTP requests based on the `Host` header to the appropriate backend container.

Traffic is HTTP only -- there is no TLS at Traefik. The Tailscale WireGuard tunnel already provides end-to-end encryption for all traffic between clients and the VM. See [Security](Security) for more details.
