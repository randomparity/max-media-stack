# Issue 21 Log Inspection Adversarial Review

## Plan Review

The original plan correctly separated centralized collection from periodic
inspection: Loki and Alloy already existed, while the missing work was a policy
runner, examples, generated corpora, tests, and operator documentation.

Findings reviewed before implementation:

- Target-host dependencies: resolved by using Python standard library only and
  JSON policies instead of requiring PyYAML or another runtime package.
- Testability: resolved by adding `scripts/generate-test-corpus` and local
  JSONL inspection mode so policies can be tested without a live Loki instance.
- Policy examples: resolved by adding example policies for application errors,
  storage pressure, and authentication failures.
- False positives: addressed with an adversarial corpus that includes near-miss
  log lines and verifies they do not trigger the example test policy.
- Deployment access: plan required a host-side timer to query Loki. Code review
  confirmed this needed a loopback-only Loki port binding.

## Code Review

Findings reviewed after implementation:

- Systemd unit path: the first deployment used the Quadlet directory for the
  inspection `.service` and `.timer`. That would not load as ordinary user
  systemd units. Fixed in commit `fix(logging): install inspection units in user
  systemd` by deploying to `{{ mms_home }}/.config/systemd/user`.
- Loki exposure: the inspector needs host access to Loki. Fixed by publishing
  `127.0.0.1:3100:3100`, which avoids LAN exposure while enabling local API
  checks.
- Policy window mismatch: example policies use a 60-minute window. The deployed
  timer now queries a 60-minute lookback by default.
- Malformed policies: covered by functional tests that require actionable
  errors and exit code 2 for invalid JSON policy content.
- PR risk: no follow-up work is deferred. If reviewers request notification
  delivery, silence detection beyond pattern policies, or persistent historical
  reports, those should be filed as separate issues because they add new
  behavior beyond issue 21's periodic inspection request.
