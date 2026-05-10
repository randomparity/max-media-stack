# Observability

Centralized logging and metrics stack -- Loki for log storage, Alloy for journal collection and host metrics, Prometheus for metrics storage, podman-exporter for container metrics, and Grafana for dashboards.

All five containers are managed by the `logging` role. The role also installs a
policy-driven log inspection timer that queries Loki on a schedule and writes the
latest JSON report to disk. Grafana state, Prometheus TSDB, and Loki data are
disposable -- Grafana is fully provisioned from Ansible templates, while
Prometheus and Loki will repopulate from live data. **None require backup.**

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
| **Log inspection timer** | Every 15 minutes |
| **Log inspection policies** | `/home/mms/config/logging/inspection/policies` |
| **Latest inspection report** | `/home/mms/config/logging/inspection/latest-report.json` |
| **Notification env file** | `/home/mms/config/logging/inspection/notifications.env` |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Log Inspection Architecture

Alloy ships user journal entries to Loki with the `job="mms"` label. The logging
role publishes Loki on `127.0.0.1:3100` so host-side tools can query it without
exposing Loki to the LAN. `mms-log-inspect.timer` starts
`mms-log-inspect.service` every 15 minutes by default.

The service runs:

```bash
~/config/logging/bin/mms-log-inspect \
  --loki-url http://localhost:3100 \
  --lookback-minutes 60 \
  --query-limit 5000 \
  --policy ~/config/logging/inspection/policies \
  --output-json ~/config/logging/inspection/latest-report.json \
  --fail-on critical
```

When notifications are enabled, systemd also loads
`~/config/logging/inspection/notifications.env` and appends `--notify`.

## Configuration Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `logging_inspection_enabled` | `true` | Enables and starts `mms-log-inspect.timer`. |
| `logging_inspection_schedule` | `*-*-* *:00/15:00` | User systemd calendar schedule. |
| `logging_inspection_lookback_minutes` | `60` | Loki lookback window per scheduled run. |
| `logging_inspection_query_limit` | `5000` | Maximum Loki entries requested per run. |
| `logging_inspection_fail_on` | `critical` | Severity threshold that makes the service exit `1`. |
| `logging_inspection_policy_dir` | `{{ logging_config_dir }}/inspection/policies` | Active policy directory. |
| `logging_inspection_output_file` | `{{ logging_config_dir }}/inspection/latest-report.json` | Latest report path. |
| `logging_inspection_notifications_enabled` | `false` | Adds `--notify` and loads the env file. |
| `logging_inspection_environment_file` | `{{ logging_config_dir }}/inspection/notifications.env` | Private secret file. |

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

### Log Inspection

```bash
systemctl --user start mms-log-inspect.service
systemctl --user status mms-log-inspect.service
systemctl --user status mms-log-inspect.timer
systemctl --user list-timers mms-log-inspect.timer
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

# Latest policy inspection report
python3 -m json.tool ~/config/logging/inspection/latest-report.json
```

## Log Inspection Policies

The `logging` role installs `mms-log-inspect`, a dependency-free Python CLI that
queries Loki's local API and evaluates JSON policy files. Loki is published on
`127.0.0.1:3100` only so the host-side timer can query it without exposing Loki
on the LAN.

Default example policies are deployed from `examples/log-policies/` to
`~/config/logging/inspection/policies/`. Add custom `*.json` files to that
directory and restart the timer if the schedule changed:

```bash
systemctl --user restart mms-log-inspect.timer
```

Policy files use this shape:

```json
{
  "name": "storage-pressure",
  "description": "Detect log messages that indicate storage exhaustion.",
  "window_minutes": 60,
  "rules": [
    {
      "id": "disk-full",
      "severity": "critical",
      "description": "A service reports that disk space is exhausted.",
      "service": "*",
      "patterns": ["no space left on device", "ENOSPC", "disk full"],
      "threshold": 1
    }
  ]
}
```

Supported severities are `info`, `warning`, and `critical`. `service` can be
`*`, a service name such as `radarr`, or a systemd unit such as
`radarr.service`. `patterns` are Python regular expressions evaluated
case-insensitively against each log line. A rule becomes a finding when the
number of matching log entries is greater than or equal to `threshold`.

### Policy Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Stable policy name shown in reports and generic webhook payloads. |
| `description` | yes | Operator-facing description of the policy intent. |
| `window_minutes` | yes | Intended review window; keep it at or below the configured lookback. |
| `notifications` | no | Webhook targets evaluated only when `--notify` is set. |
| `rules` | yes | Non-empty array of rule objects. |

### Rule Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable rule identifier shown in reports and notification text. |
| `severity` | yes | `info`, `warning`, or `critical`. |
| `description` | yes | Finding description shown in reports. |
| `service` | yes | `*`, a service label such as `radarr`, or a unit such as `radarr.service`. |
| `patterns` | yes | Non-empty array of Python regular expressions, matched case-insensitively. |
| `threshold` | yes | Positive integer match count required to create a finding. |

Run an inspection manually against Loki:

```bash
~/config/logging/bin/mms-log-inspect \
  --loki-url http://localhost:3100 \
  --lookback-minutes 60 \
  --query-limit 5000 \
  --policy ~/config/logging/inspection/policies \
  --output-json ~/config/logging/inspection/latest-report.json \
  --fail-on critical
```

The command exits `1` when findings at or above `--fail-on` exist. The systemd
service uses that exit code so critical policy matches are visible through
`systemctl --user status mms-log-inspect.service` and
`journalctl --user -u mms-log-inspect.service`.

## Reports And Exit Codes

The report is always written before notification delivery. It has this shape:

```json
{
  "generated_at": "2026-05-10T12:00:00Z",
  "summary": {
    "critical": 1,
    "warning": 2,
    "info": 0
  },
  "findings": [
    {
      "policy": "storage-pressure",
      "rule_id": "disk-full",
      "severity": "critical",
      "description": "A service reports that disk space is exhausted.",
      "match_count": 1,
      "threshold": 1,
      "matches": [
        {
          "timestamp": "2026-05-10T12:00:00Z",
          "service": "sabnzbd",
          "unit": "sabnzbd.service",
          "message": "write failed: no space left on device"
        }
      ]
    }
  ]
}
```

| Exit code | Meaning |
|-----------|---------|
| `0` | Inspection completed and no findings met `--fail-on`. |
| `1` | Inspection completed and findings met or exceeded `--fail-on`. |
| `2` | Input, policy, Loki query, report write, or notification delivery failed. |

Only the first 10 matching log entries are included per finding.

### Notifications

Policies can notify webhook-compatible services when findings are present.
Notifications are disabled by default. Enable scheduled notifications in
inventory or role defaults:

```yaml
logging_inspection_notifications_enabled: true
```

When enabled, the logging role creates
`~/config/logging/inspection/notifications.env` with mode `0600` if it does not
already exist. Add webhook URLs there using the environment-variable names from
your policy files:

```bash
MMS_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
MMS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
MMS_GENERIC_WEBHOOK_URL=https://example.invalid/mms-alert-bridge
```

Do not commit real webhook URLs. Keep them in Ansible Vault or edit the
deployed `notifications.env` on the host.

Add a `notifications` array to any policy file:

```json
{
  "name": "storage-pressure",
  "description": "Detect log messages that indicate storage exhaustion.",
  "window_minutes": 60,
  "notifications": [
    {
      "id": "ops-discord",
      "provider": "discord",
      "webhook_url_env": "MMS_DISCORD_WEBHOOK_URL",
      "min_severity": "warning"
    }
  ],
  "rules": [
    {
      "id": "disk-full",
      "severity": "critical",
      "description": "A service reports that disk space is exhausted.",
      "service": "*",
      "patterns": ["no space left on device", "ENOSPC", "disk full"],
      "threshold": 1
    }
  ]
}
```

Supported providers are:

| Provider | Payload |
|----------|---------|
| `discord` | `{"content": "..."}` |
| `slack` | `{"text": "..."}` |
| `generic` | Structured JSON with `summary`, `findings`, and `generated_at` |

Use `generic` for automation bridges, including services that forward webhook
payloads to WhatsApp.

### Notification Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable notification target identifier. |
| `provider` | yes | `discord`, `slack`, or `generic`. |
| `webhook_url_env` | yes | Environment variable containing the webhook URL. |
| `min_severity` | yes | Lowest severity sent to this target. |

### Discord Setup

Create a Discord incoming webhook for a specific text channel:

1. In Discord, open the target server.
2. Open **Server Settings**.
3. Open **Integrations**.
4. Open **Webhooks**.
5. Create a webhook.
6. Choose the channel that should receive MMS alerts.
7. Name the webhook, for example `MMS Log Inspection`.
8. Copy the webhook URL.

Store the URL on the MMS host:

```bash
mkdir -p ~/config/logging/inspection
touch ~/config/logging/inspection/notifications.env
chmod 0600 ~/config/logging/inspection/notifications.env
$EDITOR ~/config/logging/inspection/notifications.env
```

Add:

```bash
MMS_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Then reference that variable from a policy:

```json
{
  "id": "ops-discord",
  "provider": "discord",
  "webhook_url_env": "MMS_DISCORD_WEBHOOK_URL",
  "min_severity": "warning"
}
```

See the Discord webhook docs at
<https://docs.discord.com/developers/platform/webhooks> and the Discord support
guide at <https://support.discord.com/hc/en-us/articles/228383668>.

### Slack Setup

Create a Slack incoming webhook:

1. Create or open a Slack app for the workspace.
2. Open **Incoming Webhooks** in the app configuration.
3. Turn on **Activate Incoming Webhooks**.
4. Select **Add New Webhook to Workspace**.
5. Choose the channel that should receive MMS alerts.
6. Copy the generated webhook URL.

Store the URL on the MMS host:

```bash
mkdir -p ~/config/logging/inspection
touch ~/config/logging/inspection/notifications.env
chmod 0600 ~/config/logging/inspection/notifications.env
$EDITOR ~/config/logging/inspection/notifications.env
```

Add:

```bash
MMS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Then reference that variable from a policy:

```json
{
  "id": "ops-slack",
  "provider": "slack",
  "webhook_url_env": "MMS_SLACK_WEBHOOK_URL",
  "min_severity": "critical"
}
```

See the Slack incoming webhook docs at
<https://api.slack.com/messaging/webhooks>.

### Generic Webhook Setup

Use `generic` for services that accept arbitrary JSON over HTTP, including
automation bridges and notification relays.

1. Create the destination webhook in the receiving service.
2. Confirm it accepts `POST` requests with `Content-Type: application/json`.
3. Copy the destination URL.
4. Store it in `~/config/logging/inspection/notifications.env`.

```bash
MMS_GENERIC_WEBHOOK_URL=https://example.invalid/mms-alert-bridge
```

Then reference that variable from a policy:

```json
{
  "id": "automation-bridge",
  "provider": "generic",
  "webhook_url_env": "MMS_GENERIC_WEBHOOK_URL",
  "min_severity": "critical"
}
```

The generic provider sends structured JSON with `notification_id`, `summary`,
`findings`, and `generated_at`.

A complete example is available at
`examples/log-notification-policies/notification-webhooks.json`. Copy it into
`~/config/logging/inspection/policies/` only after setting the referenced
environment variables.

Run a notification-enabled inspection manually:

```bash
set -a
source ~/config/logging/inspection/notifications.env
set +a

~/config/logging/bin/mms-log-inspect \
  --loki-url http://localhost:3100 \
  --lookback-minutes 60 \
  --query-limit 5000 \
  --policy ~/config/logging/inspection/policies \
  --output-json ~/config/logging/inspection/latest-report.json \
  --fail-on critical \
  --notify
```

Notification failures exit `2` after writing the JSON report. Missing webhook
environment variables are reported by variable name only.

## Policy Deployment Workflow

1. Edit or add a policy under `examples/log-policies/` in the repository.
2. Validate it locally with `scripts/generate-test-corpus` and
   `scripts/mms-log-inspect`.
3. Deploy the logging service:

```bash
ansible-playbook playbooks/deploy-service.yml -e service_name=logging
```

4. On the host, confirm the policy exists:

```bash
ls -l ~/config/logging/inspection/policies/
```

5. Run one inspection immediately:

```bash
systemctl --user start mms-log-inspect.service
systemctl --user status mms-log-inspect.service
python3 -m json.tool ~/config/logging/inspection/latest-report.json
```

### Testing Policies Locally

Use `scripts/generate-test-corpus` to create deterministic JSONL logs, then run
the same inspector against those files before deploying policy changes:

```bash
scripts/generate-test-corpus \
  --scenario faulty \
  --entries 40 \
  --output /tmp/mms-faulty.jsonl

scripts/mms-log-inspect \
  --input-jsonl /tmp/mms-faulty.jsonl \
  --policy examples/log-policies \
  --output-json /tmp/mms-log-report.json \
  --fail-on critical

python3 -m json.tool /tmp/mms-log-report.json
```

Available scenarios are `clean`, `faulty`, and `adversarial`. Use `clean` to
check false positives, `faulty` to confirm expected detections, and
`adversarial` to review near-miss log lines that should not trigger policies.
For notification tests, point policy `webhook_url_env` values at a local webhook
receiver or a disposable test channel before using production destinations,
then add `--notify` to the inspection command.

## Health Checks

```bash
# Loki readiness
podman exec grafana curl -s http://loki:3100/ready
curl -sf http://127.0.0.1:3100/ready

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

### Log inspection service exits with status 1

Status `1` means the inspector ran successfully and found policy matches at or
above `logging_inspection_fail_on`. Read the report first:

```bash
python3 -m json.tool ~/config/logging/inspection/latest-report.json
```

### Log inspection service exits with status 2

Status `2` means execution failed. Check stderr in the user journal:

```bash
journalctl --user -u mms-log-inspect.service --since today
```

Common causes are invalid JSON, unsupported severity or provider names, missing
policy files, Loki query failures, and missing webhook environment variables.

### Notifications are not sent

Verify scheduled notifications are enabled, the environment file is loaded, and
the policy has findings at or above the target's `min_severity`:

```bash
systemctl --user cat mms-log-inspect.service
grep -E '^[A-Z0-9_]+=' ~/config/logging/inspection/notifications.env | cut -d= -f1
python3 -m json.tool ~/config/logging/inspection/latest-report.json
```

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
