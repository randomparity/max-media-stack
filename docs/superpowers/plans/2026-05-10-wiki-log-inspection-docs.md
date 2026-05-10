# Wiki Log Inspection Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the project wiki so operators have complete documentation for policy-driven log inspection and webhook notifications added in PRs #87 and #89.

**Architecture:** Keep the detailed operator guide on `docs/wiki/Observability.md`, then update cross-cutting wiki pages that describe networking, security, storage, operations, and troubleshooting. Do not duplicate the full policy schema across pages; link back to Observability from summary pages.

**Tech Stack:** GitHub wiki Markdown, Ansible logging role, rootless Podman Quadlet, user systemd timers, Loki, Python standard-library CLI scripts.

---

## PR Review Summary

PR #87, `feat(logging): add policy-driven log inspection`, added:

- `scripts/mms-log-inspect`, a dependency-free Python CLI that evaluates JSON policies against either Loki `query_range` results or local JSONL corpora.
- `scripts/generate-test-corpus` for deterministic `clean`, `faulty`, and `adversarial` policy test data.
- Example policies in `examples/log-policies/` for application errors, storage pressure, and authentication failures.
- Logging role deployment of `mms-log-inspect.service` and `mms-log-inspect.timer` under `~/.config/systemd/user`.
- Loopback-only Loki host publishing with `PublishPort=127.0.0.1:3100:3100`.
- Default inspection settings in `roles/logging/defaults/main.yml`, including 15-minute schedule, 60-minute lookback, 5000-entry query limit, and critical failure threshold.

PR #89, `feat(logging): add notification support for issues`, added:

- Policy-defined `notifications` targets behind the `--notify` CLI flag.
- Discord, Slack, and generic webhook payload formats.
- Optional scheduled notification delivery controlled by `logging_inspection_notifications_enabled`.
- Private `notifications.env` creation at mode `0600`, with `force: false` so redeploys do not overwrite operator secrets.
- Example notification policy in `examples/log-notification-policies/notification-webhooks.json`, intentionally outside the deployed active policy directory.
- Tests for notification payloads and logging role secret-file behavior.

## Documentation Gaps Found

- `docs/wiki/Observability.md` contains first-pass docs, but it should be reorganized into a complete runbook with clear sections for architecture, configuration variables, policy schema, report schema, exit codes, scheduling, notifications, local validation, deployment workflow, and troubleshooting.
- `docs/wiki/Home.md` and `docs/wiki/Security.md` still state that only Traefik and Plex publish host ports. They need to distinguish LAN-exposed ports from Loki's loopback-only host binding.
- `docs/wiki/Storage-Layout.md` omits `logging/bin/`, `logging/inspection/`, deployed policies, `latest-report.json`, and `notifications.env`.
- `docs/wiki/Common-Operations.md` does not include common log-inspection commands for running the timer, inspecting the report, validating policies, or enabling notifications.
- `docs/wiki/Troubleshooting.md` lacks cross-cutting checks for `mms-log-inspect.service`, Loki loopback readiness, invalid policy JSON, notification environment variables, and webhook failures.
- `docs/wiki/_Sidebar.md` is acceptable as-is because Observability already exists under Services, but a future implementation may choose to move it to Operations if the wiki is reorganized.

## File Structure

- Modify `docs/wiki/Observability.md`: primary complete documentation for log inspection and notifications.
- Modify `docs/wiki/Home.md`: update architecture text so loopback-only Loki publishing is accurate.
- Modify `docs/wiki/Security.md`: document Loki loopback exposure and notification secret handling.
- Modify `docs/wiki/Storage-Layout.md`: add the new inspection directories and files under logging storage.
- Modify `docs/wiki/Common-Operations.md`: add day-to-day operator commands for log inspection.
- Modify `docs/wiki/Troubleshooting.md`: add focused failure diagnosis for policies, reports, Loki access, and notifications.

### Task 1: Rework Observability Into The Source Of Truth

**Files:**
- Modify: `docs/wiki/Observability.md`

- [ ] **Step 1: Add an architecture subsection after the opening property table**

Add a concise section that documents the execution flow:

```markdown
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
```

- [ ] **Step 2: Add a configuration variables table near the architecture section**

Document the defaults from `roles/logging/defaults/main.yml`:

```markdown
## Configuration Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `logging_inspection_enabled` | `true` | Enables and starts `mms-log-inspect.timer`. |
| `logging_inspection_schedule` | `*-*-* *:00/15:00` | User systemd calendar schedule. |
| `logging_inspection_lookback_minutes` | `60` | Loki lookback window per scheduled run. |
| `logging_inspection_query_limit` | `5000` | Maximum Loki entries requested per run. |
| `logging_inspection_fail_on` | `critical` | Severity threshold that makes the service exit `1`. |
| `logging_inspection_policy_dir` | `{{ logging_config_dir }}/inspection/policies` | Active deployed policy directory. |
| `logging_inspection_output_file` | `{{ logging_config_dir }}/inspection/latest-report.json` | Latest JSON report path. |
| `logging_inspection_notifications_enabled` | `false` | Adds `--notify` and loads the notification env file. |
| `logging_inspection_environment_file` | `{{ logging_config_dir }}/inspection/notifications.env` | Private webhook secret file. |
```

- [ ] **Step 3: Expand the policy schema section**

Keep the current example, then add a field reference table:

```markdown
### Policy Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Stable policy name shown in reports and generic webhook payloads. |
| `description` | yes | Operator-facing description of the policy intent. |
| `window_minutes` | yes | Policy author's intended review window. Keep it at or below `logging_inspection_lookback_minutes`. |
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
```

- [ ] **Step 4: Add report schema and exit-code documentation**

```markdown
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
```

- [ ] **Step 5: Expand notification provider docs**

Document target fields, provider payloads, secret handling, and provider-side
setup. Use the current official setup references when writing the wiki page:

- Discord developer docs: <https://docs.discord.com/developers/platform/webhooks>
- Discord support guide: <https://support.discord.com/hc/en-us/articles/228383668>
- Slack incoming webhook docs: <https://api.slack.com/messaging/webhooks>

```markdown
### Notification Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable notification target identifier. |
| `provider` | yes | `discord`, `slack`, or `generic`. |
| `webhook_url_env` | yes | Environment variable containing the webhook URL. |
| `min_severity` | yes | Lowest severity sent to this target. |

Scheduled notifications are opt-in. Set
`logging_inspection_notifications_enabled: true`, deploy the logging service,
then populate `~/config/logging/inspection/notifications.env` on the host or
from Ansible Vault-managed content. The role creates the file with mode `0600`
and does not overwrite it on later deploys.
```

- [ ] **Step 6: Add provider-side webhook setup examples**

Add service-side setup examples before the manual notification command. These
examples must explain how to create the destination webhook before configuring
MMS.

````markdown
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
install -m 0600 /dev/null ~/config/logging/inspection/notifications.env
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
install -m 0600 /dev/null ~/config/logging/inspection/notifications.env
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
````

- [ ] **Step 7: Add deployment workflow guidance**

```markdown
## Policy Deployment Workflow

1. Edit or add a policy under `examples/log-policies/` in the repository.
2. Validate it locally with `scripts/generate-test-corpus` and `scripts/mms-log-inspect`.
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
```

- [ ] **Step 8: Add focused common issues for the new feature**

Add these subsections under `## Common Issues`:

```markdown
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
grep -v '^#' ~/config/logging/inspection/notifications.env
python3 -m json.tool ~/config/logging/inspection/latest-report.json
```
```

### Task 2: Fix Wiki Network And Security Consistency

**Files:**
- Modify: `docs/wiki/Home.md`
- Modify: `docs/wiki/Security.md`

- [ ] **Step 1: Update Home architecture text**

Replace the sentence beginning `Traefik and Plex are the only containers that publish host ports` with:

```markdown
Traefik and Plex are the only services reachable through externally bound host
ports (80 and 32400 respectively). Loki also publishes `127.0.0.1:3100` for
host-local log inspection, but it is bound to loopback only and is not reachable
from the LAN or Tailscale peers. All other backend services are reached via the
shared `mms.network` bridge using container-name DNS. Traffic is HTTP only --
the Tailscale WireGuard tunnel already encrypts user-facing traffic end-to-end.
```

- [ ] **Step 2: Update Security network isolation**

Replace the `Minimal port exposure` bullet with:

```markdown
- **Minimal port exposure**: Only Traefik (port 80) and Plex (port 32400) are externally reachable. Loki binds `127.0.0.1:3100` only for host-local inspection; it is not LAN-exposed. Other services are internal to the container network (`mms.network`).
```

- [ ] **Step 3: Add notification secret handling to Security**

Under `## Secrets management`, add:

```markdown
- **Webhook URLs**: Log-inspection notification webhooks belong in Ansible Vault or in the deployed `~/config/logging/inspection/notifications.env` file. The logging role creates that file with mode `0600` and does not overwrite it on redeploy.
```

### Task 3: Document Storage And Operator Commands

**Files:**
- Modify: `docs/wiki/Storage-Layout.md`
- Modify: `docs/wiki/Common-Operations.md`

- [ ] **Step 1: Expand the logging storage tree**

Replace the logging tree block with entries for the new inspection files:

```markdown
/home/mms/config/logging/           # Observability stack config
├── bin/                            #   Host-side helper scripts
│   └── mms-log-inspect             #   Policy-driven log inspector
├── inspection/                     #   Log inspection runtime state
│   ├── policies/                   #   Active JSON inspection policies
│   ├── latest-report.json          #   Most recent inspection report
│   └── notifications.env           #   Optional webhook URLs, mode 0600
├── loki/                           #   Loki config + alert rules
├── alloy/                          #   Alloy collector config
├── grafana/                        #   Grafana config + provisioning
├── prometheus/                     #   Prometheus scrape config
├── loki-data/                      #   Loki log storage (retention-managed)
├── grafana-data/                   #   Grafana SQLite DB (disposable)
└── prometheus-data/                #   Prometheus TSDB (retention-managed, disposable)
```

- [ ] **Step 2: Add Common Operations commands**

Add this section before `## Lint`:

```markdown
## Log inspection

```bash
# Run an inspection immediately
systemctl --user start mms-log-inspect.service

# Check the scheduled timer
systemctl --user status mms-log-inspect.timer
systemctl --user list-timers mms-log-inspect.timer

# Read the latest report
python3 -m json.tool ~/config/logging/inspection/latest-report.json

# Validate policies locally before deployment
scripts/generate-test-corpus --scenario faulty --entries 40 --output /tmp/mms-faulty.jsonl
scripts/mms-log-inspect \
  --input-jsonl /tmp/mms-faulty.jsonl \
  --policy examples/log-policies \
  --output-json /tmp/mms-log-report.json \
  --fail-on critical
```

See [Observability](Observability#log-inspection-policies) for the policy schema,
notification setup, and troubleshooting notes.
```

### Task 4: Add Cross-Cutting Troubleshooting

**Files:**
- Modify: `docs/wiki/Troubleshooting.md`

- [ ] **Step 1: Add a log-inspection troubleshooting section**

Add this section after `## Systemd service debugging`:

```markdown
## Log inspection troubleshooting

```bash
# Timer and service status
systemctl --user status mms-log-inspect.timer
systemctl --user status mms-log-inspect.service
journalctl --user -u mms-log-inspect.service --since today

# Loki loopback health from the host
curl -sf http://127.0.0.1:3100/ready

# Latest report
python3 -m json.tool ~/config/logging/inspection/latest-report.json
```

Status `1` from `mms-log-inspect.service` means findings met the configured
`--fail-on` threshold. Status `2` means the inspector failed before completing
or notification delivery failed. Invalid policy JSON, unsupported severity
values, missing webhook environment variables, and Loki query failures are the
most common causes.
```

- [ ] **Step 2: Link back to Observability**

At the end of the new section, add:

```markdown
For policy schema details and notification examples, see
[Observability](Observability#log-inspection-policies).
```

### Task 5: Verify The Wiki Update

**Files:**
- Verify: `docs/wiki/Observability.md`
- Verify: `docs/wiki/Home.md`
- Verify: `docs/wiki/Security.md`
- Verify: `docs/wiki/Storage-Layout.md`
- Verify: `docs/wiki/Common-Operations.md`
- Verify: `docs/wiki/Troubleshooting.md`

- [ ] **Step 1: Check for stale port-exposure wording**

Run:

```bash
rg -n "only (Traefik|Traefik and Plex)|only containers that publish|Minimal port exposure" docs/wiki README.md
```

Expected: no wiki page claims that only Traefik and Plex publish host ports without mentioning Loki's loopback-only binding.

- [ ] **Step 2: Check for all feature terms in the wiki**

Run:

```bash
rg -n "mms-log-inspect|notifications.env|latest-report.json|logging_inspection_notifications_enabled|127\\.0\\.0\\.1:3100" docs/wiki
```

Expected: each term appears in the relevant operator pages.

- [ ] **Step 3: Run markdown/link sanity checks available in the repo**

Run:

```bash
make lint
```

Expected: `yamllint` and `ansible-lint` complete with zero warnings and zero failures. If the repository does not lint Markdown, still run this because the documentation changes reference Ansible variables and role behavior.

- [ ] **Step 4: Review the final diff manually**

Run:

```bash
git diff -- docs/wiki/Observability.md docs/wiki/Home.md docs/wiki/Security.md docs/wiki/Storage-Layout.md docs/wiki/Common-Operations.md docs/wiki/Troubleshooting.md
```

Expected: the diff documents the current implementation only. It should not promise undeployed notification providers, dashboards, Alertmanager integration, automatic WhatsApp delivery, or policy formats beyond the JSON schema implemented by `scripts/mms-log-inspect`.
