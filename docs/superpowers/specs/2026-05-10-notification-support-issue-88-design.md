# Notification Support for Issue Findings Design

## Context

GitHub issue 88 asks for a notification method when the policy-driven log
inspector identifies issues. The inspector from PR 87 already evaluates JSON
policies against generated JSONL corpora or Loki query results, writes a JSON
report, and exits nonzero for findings at or above `--fail-on`.

## Recommended Approach

Add dependency-free webhook notifications to `scripts/mms-log-inspect`. Policy
files may define notification targets with a provider, an environment-variable
name containing the webhook URL, and a minimum severity. This keeps committed
policy files free of secrets and lets the same mechanism work for Discord,
Slack, and generic webhook bridges such as WhatsApp automation services.

Alternatives considered:

- Systemd-only notifications through `OnFailure=` would require separate unit
  wiring per destination and would not work for local corpus validation.
- Native SDK integrations for every service would add dependencies and secrets
  handling complexity that the current standard-library inspector avoids.

## Policy Shape

Policies can include an optional top-level `notifications` array:

```json
{
  "notifications": [
    {
      "id": "ops-discord",
      "provider": "discord",
      "webhook_url_env": "MMS_DISCORD_WEBHOOK_URL",
      "min_severity": "warning"
    }
  ]
}
```

Supported providers are `discord`, `slack`, and `generic`. `generic` sends the
full structured report. Discord and Slack send concise text payloads accepted by
their incoming webhook APIs.

## CLI Behavior

`mms-log-inspect` will add `--notify` to enable policy-defined notifications.
By default, policy notification blocks are validated but not sent, so local test
runs and scheduled inspections remain unchanged until operators opt in. When
`--notify` is set, notifications are sent after the report is written if the
report has findings at or above each target's `min_severity`.

Notification delivery failures are operational failures. The command exits `2`
after writing the report if a configured webhook environment variable is missing
or a webhook request fails. This fail-fast behavior makes a broken notification
path visible in `systemctl --user status mms-log-inspect.service`.

## Deployment

The logging role will add:

- `logging_inspection_notifications_enabled`, default `false`
- `logging_inspection_environment_file`, default
  `{{ logging_config_dir }}/inspection/notifications.env`

When notifications are enabled, the systemd service passes `--notify` and reads
the environment file. The role creates the environment file with mode `0600` if
it does not already exist, but does not overwrite operator-managed secrets.

## Testing

Functional tests will continue using `scripts/generate-test-corpus`. New tests
will verify:

- faulty corpora trigger a Discord notification when `--notify` is enabled
- clean corpora do not send notifications
- missing webhook environment variables produce an actionable exit `2`
- Slack/generic payload formatting is valid enough for receiving endpoints
- adversarial corpora still do not trigger findings or notifications

Tests will use local HTTP servers rather than external services.

## Documentation and Examples

`docs/wiki/Observability.md` will document policy notification blocks, required
environment variables, systemd deployment, manual runs, and local corpus
validation. New example policies under `examples/log-policies/` will demonstrate
Discord, Slack, and generic webhook targets without real secrets.

## Adversarial Review

The implementation review will check for secret leakage, notification spam,
false positives from generated adversarial corpora, webhook failure handling,
provider payload correctness, and whether any follow-up work should be filed as
new GitHub issues.
