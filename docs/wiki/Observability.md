# Observability

Centralized logging and metrics stack -- Loki for log storage, Alloy for journal collection and host metrics, Prometheus for metrics storage, podman-exporter for container metrics, and Grafana for dashboards.

All five containers are managed by the `logging` role. Grafana state, Prometheus TSDB, and Loki data are disposable -- Grafana is fully provisioned from Ansible templates, while Prometheus and Loki will repopulate from live data. **None require backup.**

## Containers

| Container | Image | Port | Purpose |
|-----------|-------|------|--------|
| `loki` | `docker.io/grafana/loki` | 3100 | Log storage |
| `alloy` | `docker.io/grafana/alloy` | 12345 | Journal collector + host metrics exporter |
| `prometheus` | `docker.io/prom/prometheus` | 9090 | Metrics storage |
| `podman-exporter` | `quay.io/navidys/prometheus-podman-exporter` | 9882 | Container metrics |
| `grafana` | `docker.io/grafana/grafana` | 3000 | Dashboard UI |

| Property | Value |
|----------|-------|
| **Traefik subdomain** | `grafana.media.drc.nz` (Grafana only) |
| **Config directory** | `/home/mms/config/logging` |
| **Loki data** | `/home/mms/config/logging/loki-data` |
| **Grafana data** | `/home/mms/config/logging/grafana-data` |
| **Prometheus data** | `/home/mms/config/logging/prometheus-data` |
| **Prometheus retention** | 30 days |
| **Loki retention** | 30 days (720h) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Service Management

### Loki

```bash
systemctl --user start loki.service
systemctl --user stop loki.service
systemctl --user restart loki.service
systemctl --user status loki.service
```

### Alloy

```bash
systemctl --user start alloy.service
systemctl --user stop alloy.service
systemctl --user restart alloy.service
systemctl --user status alloy.service
```

### Prometheus

```bash
systemctl --user start prometheus.service
systemctl --user stop prometheus.service
systemctl --user restart prometheus.service
systemctl --user status prometheus.service
```

### podman-exporter

```bash
systemctl --user start podman-exporter.service
systemctl --user stop podman-exporter.service
systemctl --user restart podman-exporter.service
systemctl --user status podman-exporter.service
```

### Grafana

```bash
systemctl --user start grafana.service
systemctl --user stop grafana.service
systemctl --user restart grafana.service
systemctl --user status grafana.service
```

## Viewing Logs

```bash
# Each container
podman logs --tail 50 loki
podman logs --tail 50 alloy
podman logs --tail 50 prometheus
podman logs --tail 50 podman-exporter
podman logs --tail 50 grafana

# Systemd unit logs
journalctl --user -u loki --since today
journalctl --user -u alloy --since today
journalctl --user -u prometheus --since today
journalctl --user -u grafana --since today
```

## Health Checks

```bash
# Loki readiness
podman exec grafana curl -s http://loki:3100/ready

# Prometheus targets
curl -sf http://localhost:9090/api/v1/targets | python3 -m json.tool

# Grafana UI
curl -sf http://grafana.media.drc.nz/api/health
```

## Backup & Restore

**No backup needed.** All observability data is disposable:
- **Grafana**: Dashboards and datasources are fully provisioned from Ansible templates. Destroying and recreating `grafana-data/` loses nothing.
- **Prometheus**: TSDB data is retention-managed (30 days). It repopulates from live scrapes.
- **Loki**: Log data is retention-managed (30 days). It repopulates from the journal.

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Alloy -> Loki | `loki` | `http://loki:3100/loki/api/v1/push` | Ship journal logs |
| Prometheus -> Alloy | `alloy` | `http://alloy:12345/metrics` | Scrape host metrics |
| Prometheus -> podman-exporter | `podman-exporter` | `http://podman-exporter:9882/metrics` | Scrape container metrics |
| Grafana -> Loki | `loki` | `http://loki:3100` | Query logs |
| Grafana -> Prometheus | `prometheus` | `http://prometheus:9090` | Query metrics |

## Common Issues

### Alloy not collecting logs

Alloy reads the systemd journal via the `systemd-journal` group. Verify the `mms` user is in the group:

```bash
groups mms | grep systemd-journal
```

If the group membership was just added, the Alloy container needs a restart:

```bash
systemctl --user restart alloy.service
```

Also verify persistent journald is configured (the `base_system` role handles this). If journal data is only in-memory, Alloy won't find historical entries:

```bash
ls /var/log/journal/
```

### Grafana dashboard shows no data

Check Loki is running and healthy first:

```bash
systemctl --user status loki.service
podman logs --tail 20 loki
podman exec grafana curl -s http://loki:3100/ready
```

If Loki is healthy but Grafana still shows no data, check the Grafana datasource configuration:

```bash
cat ~/config/logging/grafana/provisioning/datasources/*.yml
```

### Prometheus scrape targets down

Check that Alloy and podman-exporter are running:

```bash
podman ps --filter name=alloy --filter name=podman-exporter
```

Verify Prometheus can reach them:

```bash
podman exec prometheus wget -q -O- http://alloy:12345/metrics | head -5
podman exec prometheus wget -q -O- http://podman-exporter:9882/metrics | head -5
```

### podman-exporter not starting

podman-exporter requires `podman.socket` to be enabled for the `mms` user:

```bash
systemctl --user status podman.socket
systemctl --user enable --now podman.socket
```

### Loki disk usage growing

Loki retains logs based on `logging_loki_retention_period` (default: 30 days / 720h). Check usage:

```bash
du -sh ~/config/logging/loki-data/
```

To reduce retention, update `logging_loki_retention_period` in `roles/logging/defaults/main.yml` and redeploy.

### Grafana state needs reset

Since Grafana is fully provisioned, you can safely destroy and recreate its state:

```bash
systemctl --user stop grafana.service
rm -rf ~/config/logging/grafana-data/*
systemctl --user start grafana.service
```

Dashboards, datasources, and alert rules will be reprovisioned automatically on startup.
