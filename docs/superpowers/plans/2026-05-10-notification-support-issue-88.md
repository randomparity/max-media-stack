# Notification Support for Issue 88 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notify operators through webhook targets when log inspection policies produce findings.

**Architecture:** Extend the existing dependency-free Python inspector with policy-defined notification targets and provider-specific payload builders. Keep secrets in environment variables, wire scheduled runs through systemd only when explicitly enabled, and verify behavior with generated JSONL corpora plus local webhook servers.

**Tech Stack:** Python standard library, pytest, Ansible templates, JSON policy files, systemd user units.

---

## File Structure

- `scripts/mms-log-inspect`: add notification policy parsing, payload building,
  webhook delivery, `--notify`, and notification-aware exit handling.
- `tests/logging/test_log_inspection.py`: add functional tests using
  `scripts/generate-test-corpus` and local HTTP webhook receivers.
- `examples/log-policies/notification-webhooks.json`: demonstrate Discord,
  Slack, and generic webhook targets with environment-variable references.
- `roles/logging/defaults/main.yml`: add notification deployment defaults.
- `roles/logging/tasks/setup.yml`: create a private notification environment
  file without overwriting operator secrets.
- `roles/logging/templates/mms-log-inspect.service.j2`: include optional
  `EnvironmentFile=` and `--notify`.
- `docs/wiki/Observability.md`: document how to enable, configure, test, and
  operate notifications.
- `docs/superpowers/reviews/2026-05-10-notification-support-issue-88.md`:
  adversarial plan and code review notes.

## Tasks

### Task 1: Notification Policy Parsing

- [ ] Add failing tests for valid notification blocks and unsupported providers.
- [ ] Run `.venv/bin/python -m pytest -q tests/logging/test_log_inspection.py`
  and verify the new tests fail because notifications are not parsed.
- [ ] Add a `NotificationTarget` dataclass and validation for `id`, `provider`,
  `webhook_url_env`, and `min_severity`.
- [ ] Re-run the focused test file and verify it passes.
- [ ] Commit with `feat(logging): parse notification targets`.

### Task 2: Webhook Payloads and Delivery

- [ ] Add failing tests that use `scripts/generate-test-corpus --scenario faulty`
  and a local HTTP server to assert Discord notifications are sent for findings.
- [ ] Add failing tests for clean and adversarial corpora asserting no webhook
  request is sent.
- [ ] Implement provider payload builders for `discord`, `slack`, and `generic`.
- [ ] Implement webhook POST delivery with clear errors and no secret logging.
- [ ] Re-run the focused test file and verify it passes.
- [ ] Commit with `feat(logging): send webhook notifications for findings`.

### Task 3: Scheduled Deployment Wiring

- [ ] Add failing assertions that the service template includes notification
  flags and environment file behavior when enabled.
- [ ] Add defaults for disabled-by-default notification deployment.
- [ ] Create the private `notifications.env` only when missing and with mode
  `0600`.
- [ ] Update the systemd service template to conditionally read the environment
  file and pass `--notify`.
- [ ] Run `.venv/bin/python -m pytest -q tests/logging/test_log_inspection.py`
  and `make lint`.
- [ ] Commit with `feat(logging): wire scheduled notification delivery`.

### Task 4: Examples, Docs, and Adversarial Review

- [ ] Add `examples/log-policies/notification-webhooks.json` with Discord,
  Slack, and generic webhook examples using environment-variable names only.
- [ ] Update `docs/wiki/Observability.md` with policy syntax, secret setup,
  generated-corpus testing, and manual run examples.
- [ ] Write `docs/superpowers/reviews/2026-05-10-notification-support-issue-88.md`
  covering plan risks, code risks, test evidence, and deferred work decisions.
- [ ] Run focused tests and `make lint`.
- [ ] Commit with `docs(logging): document notification webhooks`.

### Task 5: PR and Follow-Up Handling

- [ ] Review `git diff main...HEAD` for unnecessary complexity and secret leaks.
- [ ] Push `feat/issue-88-notifications`.
- [ ] Open a PR that closes issue 88 and lists validation commands.
- [ ] If review or implementation defers work, file GitHub issues for each
  deferred item and repeat this process for those issues.
- [ ] Shepherd the PR until merge, subject to repository permissions and remote
  review availability.
