# Adding a New Service

MMS uses a data-driven approach -- each service is defined in a YAML file and rendered by the generic `quadlet_service` role. Adding a new service takes five steps.

## 1. Create the service definition

Create `services/<name>.yml` as a nested map keyed by the service name. The `quadlet_service` role reads this top-level key when rendering the Quadlet template.

```yaml
---
# services/myservice.yml
myservice:
  name: myservice
  description: "MyService - short description"
  image: "ghcr.io/example/myservice:1.2.3"
  volumes:
    - "{{ mms_config_dir }}/myservice:/config:Z"
    - "/data/media:/media"
  environment:
    - "TZ={{ mms_timezone }}"
  health_cmd: "curl -sf http://localhost:8080/ || exit 1"
  health_interval: "60s"
  backup_type: "arr"
  backup_db_files: []
```

Look at existing files in `services/` for examples of the full set of available options (`publish_ports`, `userns`, `user`, additional `tmpfs` entries, `no_new_privileges`, etc.). `services/profilarr.yml` is a good minimal template.

## 2. Add to the services list

Add the service name to `mms_services` in `inventory/group_vars/mms/vars.yml`:

```yaml
mms_services:
  - prowlarr
  - radarr
  # ...existing services...
  - myservice    # Add here
```

## 3. Add a Traefik route

Add a route entry to `mms_traefik_routes` in `inventory/group_vars/mms/vars.yml`:

```yaml
mms_traefik_routes:
  myservice:
    subdomain: myservice          # -> myservice.media.example.com
    container: myservice          # Container name on mms.network
    port: 8080                    # Container's internal HTTP port
```

See [Traefik Reverse Proxy](Traefik-Reverse-Proxy) for more details on routing configuration.

## 4. Configure DNS

Ensure DNS is configured for the new subdomain. If you're using wildcard DNS (`*.media.example.com`), this is already handled. Otherwise, add a record for `myservice.media.example.com` pointing to your VM's Tailscale IP.

See [Traefik Reverse Proxy](Traefik-Reverse-Proxy#dns-setup) for DNS options.

## 5. Deploy

```bash
ansible-playbook playbooks/deploy-services.yml
```

Or deploy just the new service:

```bash
ansible-playbook playbooks/deploy-service.yml -e service_name=myservice
```

## Multi-container services

The data-driven `quadlet_service` pattern works for single-container services. Multi-container services like Immich (server, ML, PostgreSQL, Redis) and Open Notebook (app, SurrealDB) need their own dedicated role under `roles/` with explicit Quadlet templates for each container and handler-based service ordering.

## Backup and restore

Declare `backup_type` in the service file. Both `mms-backup.sh` and `mms-restore.sh` dispatch on this value, as does `playbooks/restore.yml`. The supported values, and the services that currently use each, are:

- `arr` — generic stop/tar/start. Used by prowlarr, profilarr, radarr, radarr4k, sonarr, lidarr, tautulli, kometa, channels, navidrome, and traefik (via `mms_special_services`). Reuse this for any service with a single config directory.
- `sabnzbd` — used by sabnzbd; extracts into the service's own subdirectory.
- `jellyfin` — used by jellyfin; bash restore excludes the cache directory.
- `plex` — used by plex; stops the service and excludes regenerable directories (Cache, Crash Reports, Updates, Codecs).
- `immich` — used by immich; multi-container restore including a PostgreSQL dump.
- `open-notebook` — used by open-notebook (via `mms_special_services`); cold backup of both the app and SurrealDB directories.

The whitelist is enforced in `playbooks/restore.yml`; declaring a value outside this list causes the restore playbook to fail before dispatch.

Adding a new value requires adding the corresponding restore function in `roles/backup/templates/mms-restore.sh.j2` (bash side) and a `playbooks/tasks/restore/restore-<type>.yml` (playbook side). Existing values just work; e.g. `backup_type: arr` for a new *arr-family service needs no additional code.
