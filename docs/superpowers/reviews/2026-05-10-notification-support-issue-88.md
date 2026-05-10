# Notification Support Issue 88 Adversarial Review

## Plan Review

- Secret handling: notification policy files reference environment-variable
  names only. Webhook URLs are not committed, rendered into reports, or printed
  in errors.
- Scope control: the implementation supports webhook-compatible providers only.
  Native WhatsApp APIs were not added because they require provider-specific
  credentials, approvals, and dependencies outside the current issue.
- Operator control: scheduled notifications are disabled by default. Enabling
  them is an explicit inventory/default override.
- Local validation: tests use `scripts/generate-test-corpus` for clean, faulty,
  and adversarial data, plus local HTTP receivers instead of external services.

## Code Review

- Notification sends happen after the JSON report is written, so operators keep
  the report even when webhook delivery fails.
- Missing webhook environment variables return exit `2` with the variable name
  and no secret value.
- Clean corpora and adversarial near-miss corpora do not send notifications.
- Discord and Slack receive concise text payloads. Generic webhook targets
  receive structured report data suitable for automation bridges.
- The systemd user service reads the notification environment file only when
  `logging_inspection_notifications_enabled` is true.
- The Ansible task creates `notifications.env` with mode `0600` and
  `force: false`, so redeploys do not overwrite operator-managed secrets.
- Notification examples live outside `examples/log-policies/` because that
  directory is deployed as active policy configuration by the logging role.

## Verification

- `.venv/bin/python -m pytest -q tests/logging/test_log_inspection.py`
- `.venv/bin/python -m pytest -q tests/logging/test_logging_role_notifications.py`
- `make lint`

## Deferred Work

None. No follow-up GitHub issues are required for issue 88. Native WhatsApp API
support is intentionally out of scope because the generic webhook provider can
feed WhatsApp bridge services without adding a new dependency or credential
model.
