# Traefik

Reverse proxy operations -- day-to-day management, debugging, and troubleshooting of the Traefik container.

> For architecture, DNS setup, and configuration, see [Traefik Reverse Proxy](Traefik-Reverse-Proxy).

| Property | Value |
|----------|-------|
| **Image** | `docker.io/library/traefik` (Official) |
| **Container name** | `traefik` |
| **Published port** | 80 (host) -> 80 (container) |
| **Config directory** | `/home/mms/config/traefik` |
| **Dynamic config** | `/home/mms/config/traefik/dynamic/*.yml` |
| **Backup type** | Config backup |
| **Autodeploy group** | `backend` (every 30 min) |

## Service Management

```bash
systemctl --user start traefik.service
systemctl --user stop traefik.service
systemctl --user restart traefik.service
systemctl --user status traefik.service
```

## Viewing Logs

```bash
journalctl --user -u traefik --since today
journalctl --user -u traefik -f
podman logs --tail 50 traefik
```

## Health Check

```bash
# Test that Traefik is serving (returns 404 for unknown hosts, which is OK)
curl -s -o /dev/null -w "%{http_code}" http://localhost

# Test a specific route
curl -sf -H "Host: radarr.media.drc.nz" http://localhost
curl -sf http://radarr.media.drc.nz
```

## Manual Testing

```bash
# Stop the running service first
systemctl --user stop traefik.service

podman run --rm -it \
  --name test-traefik \
  --network mms \
  --userns=keep-id \
  --tmpfs /run:U \
  -p 80:80 \
  -v /home/mms/config/traefik:/etc/traefik:Z \
  docker.io/library/traefik:latest
```

**Official image rules:**
- Use `--userns=keep-id`
- Use `--network mms`, not `--network mms.network`
- Use `--tmpfs /run:U`
- Published port 80 is the only externally-accessible port (besides Plex 32400 and Channels 8089)

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/traefik/`

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=traefik \
  -e backup_file=/data/backups/config/traefik/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Routing Verification

```bash
# Check the generated dynamic configuration
ls ~/config/traefik/dynamic/
cat ~/config/traefik/dynamic/*.yml

# Test each service route
for svc in prowlarr radarr radarr4k sonarr lidarr sabnzbd jellyfin plex tautulli channels navidrome immich notebook grafana; do
  echo -n "$svc: "
  curl -s -o /dev/null -w "%{http_code}" -H "Host: ${svc}.media.drc.nz" http://localhost
  echo
done

# Test from inside Traefik container (backend connectivity)
podman exec traefik wget -q --spider http://radarr:7878
```

## Common Issues

**404 errors on a service route**

Traefik is running but the route doesn't match the `Host` header. Check:

1. The dynamic config has the correct subdomain:
   ```bash
   cat ~/config/traefik/dynamic/*.yml | grep -A5 radarr
   ```
2. DNS resolves correctly:
   ```bash
   dig radarr.media.drc.nz
   ```
3. The `Host` header matches exactly:
   ```bash
   curl -v -H "Host: radarr.media.drc.nz" http://localhost
   ```

**502 Bad Gateway / connection refused to backend**

The backend container is not running or not on the `mms` network:

```bash
# Check the backend is running
podman ps | grep radarr

# Test connectivity from Traefik
podman exec traefik wget -q --spider http://radarr:7878

# Verify network membership
podman network inspect mms | grep radarr
```

**DNS not resolving**

The wildcard DNS record may not be configured. See [Traefik Reverse Proxy](Traefik-Reverse-Proxy#dns-setup) for setup instructions. Quick workaround:

```bash
# Add to /etc/hosts on the client
echo "<tailscale-ip> radarr.media.drc.nz sonarr.media.drc.nz" | sudo tee -a /etc/hosts
```

**Routes not updating after deploy**

Traefik uses the file provider and watches for changes. If routes aren't updating, restart Traefik:

```bash
systemctl --user restart traefik.service
```
