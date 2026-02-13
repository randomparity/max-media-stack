# Adding a New Service

MMS uses a data-driven approach -- each service is defined in a YAML file and rendered by the generic `quadlet_service` role. Adding a new service takes five steps.

## 1. Create the service definition

Create `services/<name>.yml` with the service configuration:

```yaml
# services/myservice.yml
service_image: "lscr.io/linuxserver/myservice:1.2.3"
service_port: 8080
service_volumes:
  - "{{ mms_config_dir }}/myservice:/config:Z"
  - "/data/media:/media"
service_healthcheck:
  test: "curl -f http://localhost:8080 || exit 1"
  interval: "30s"
  timeout: "10s"
  retries: 3
```

Look at existing files in `services/` for examples of the full set of available options (environment variables, tmpfs mounts, labels, etc.).

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
