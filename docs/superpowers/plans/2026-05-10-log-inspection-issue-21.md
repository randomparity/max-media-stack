# Log Inspection Issue 21 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add policy-driven periodic inspection of centralized container logs collected by the existing logging role.

**Architecture:** Keep the existing Loki, Alloy, Prometheus, and Grafana stack. Add a standard-library Python inspection CLI that can evaluate JSON policies against either generated JSONL test corpora or live Loki query results, then deploy it with a rootless systemd user service and timer.

**Tech Stack:** Ansible, rootless Podman Quadlet, systemd user units, Python 3 standard library, JSON policy files, pytest functional tests.

---

## File Structure

- Create `scripts/mms-log-inspect`: reusable CLI for local corpus and Loki inspection.
- Create `scripts/generate-test-corpus`: deterministic log corpus generator for functional tests and local validation.
- Create `tests/logging/test_log_inspection.py`: behavior tests that exercise generated corpora and policy evaluation through the CLI.
- Create `examples/log-policies/*.json`: user-facing example policies that demonstrate error, disk, auth, and silence-style inspection.
- Create `roles/logging/templates/mms-log-inspect.service.j2`: rootless systemd user service that runs the CLI against Loki.
- Create `roles/logging/templates/mms-log-inspect.timer.j2`: periodic systemd user timer.
- Modify `roles/logging/defaults/main.yml`: policy, schedule, output, and threshold defaults.
- Modify `roles/logging/tasks/setup.yml`: deploy the CLI, policy files, output directory, service, and timer.
- Modify `roles/logging/tasks/containers.yml`: enable and start the timer after Loki is available.
- Modify `roles/logging/handlers/main.yml`: restart the timer when its unit changes.
- Modify `docs/wiki/Observability.md`: document policy format, examples, commands, and generated corpus testing.

## Tasks

### Task 1: Add Functional Test Skeleton

**Files:**
- Create: `tests/logging/test_log_inspection.py`
- Create: `scripts/generate-test-corpus`
- Create: `scripts/mms-log-inspect`

- [ ] Write failing pytest coverage that calls `scripts/generate-test-corpus` to create `clean.jsonl` and `faulty.jsonl`, then calls `scripts/mms-log-inspect --input-jsonl ... --policy ... --output-json ...`.
- [ ] Cover no findings for the clean corpus, findings for disk/auth/error patterns, stable JSON output, and non-zero exit for malformed policy files.
- [ ] Run `source .venv/bin/activate && pytest -q tests/logging/test_log_inspection.py`; expected result is failure because the scripts do not exist yet.
- [ ] Commit after the scripts are minimally scaffolded and tests pass:

```bash
git add scripts/generate-test-corpus scripts/mms-log-inspect tests/logging/test_log_inspection.py
git commit -m "test(logging): cover policy-driven log inspection"
```

### Task 2: Implement Local Corpus Inspection

**Files:**
- Modify: `scripts/generate-test-corpus`
- Modify: `scripts/mms-log-inspect`
- Create: `examples/log-policies/error-patterns.json`
- Create: `examples/log-policies/storage-pressure.json`
- Create: `examples/log-policies/auth-failures.json`

- [ ] Implement `generate-test-corpus` with `--scenario clean|faulty|adversarial`, `--output`, and `--entries` arguments.
- [ ] Implement JSONL entries with `timestamp`, `service`, `unit`, and `message` fields.
- [ ] Implement `mms-log-inspect` local mode with `--input-jsonl`, `--policy`, `--output-json`, and `--fail-on severity`.
- [ ] Define policy fields: `name`, `description`, `window_minutes`, and `rules`. Each rule has `id`, `severity`, `description`, `service`, `patterns`, and `threshold`.
- [ ] Treat invalid regexes, missing fields, and malformed JSON as actionable errors with exit code 2.
- [ ] Run the focused pytest file and fix until clean.
- [ ] Commit:

```bash
git add scripts/generate-test-corpus scripts/mms-log-inspect examples/log-policies tests/logging/test_log_inspection.py
git commit -m "feat(logging): add local policy log inspector"
```

### Task 3: Add Loki Query Mode and Ansible Deployment

**Files:**
- Modify: `scripts/mms-log-inspect`
- Modify: `roles/logging/defaults/main.yml`
- Modify: `roles/logging/tasks/setup.yml`
- Modify: `roles/logging/tasks/containers.yml`
- Modify: `roles/logging/handlers/main.yml`
- Create: `roles/logging/templates/mms-log-inspect.service.j2`
- Create: `roles/logging/templates/mms-log-inspect.timer.j2`

- [ ] Add `--loki-url`, `--lookback-minutes`, and `--query-limit` to `mms-log-inspect`.
- [ ] Query Loki's `/loki/api/v1/query_range` endpoint with a broad `{job="mms"}` selector, parse stream values, and reuse the same policy evaluator.
- [ ] Add role defaults for `logging_inspection_enabled`, `logging_inspection_schedule`, `logging_inspection_lookback_minutes`, `logging_inspection_query_limit`, `logging_inspection_fail_on`, `logging_inspection_policy_dir`, and `logging_inspection_output_file`.
- [ ] Deploy the CLI into `{{ logging_config_dir }}/bin/mms-log-inspect`, deploy example policies into `{{ logging_inspection_policy_dir }}`, create `{{ logging_config_dir }}/inspection`, and install service/timer units.
- [ ] Enable and start `mms-log-inspect.timer` only when `logging_inspection_enabled` is true.
- [ ] Run `make lint` and fix Ansible/YAML issues.
- [ ] Commit:

```bash
git add roles/logging scripts/mms-log-inspect
git commit -m "feat(logging): schedule periodic Loki log inspection"
```

### Task 4: Add Documentation and Example Usage

**Files:**
- Modify: `docs/wiki/Observability.md`
- Modify: `README.md` if it has an observability feature list.

- [ ] Document what the timer does, where policies live, where results are written, and how to run the inspector manually.
- [ ] Document policy schema with a concise JSON example.
- [ ] Document functional testing with `scripts/generate-test-corpus` and `scripts/mms-log-inspect`.
- [ ] Document operational commands for `systemctl --user status mms-log-inspect.timer` and reading the output JSON.
- [ ] Commit:

```bash
git add docs/wiki/Observability.md README.md
git commit -m "docs(logging): document log inspection policies"
```

### Task 5: Adversarial Review and PR

**Files:**
- Modify only files needed to fix concrete review findings.

- [ ] Review the plan adversarially before final implementation: look for target-host dependencies, timer failure behavior, false positive risks, policy bypasses, Ansible idempotence, and missing tests.
- [ ] Review the resulting diff adversarially after implementation using the same categories.
- [ ] Run `source .venv/bin/activate && pytest -q tests/logging/test_log_inspection.py`.
- [ ] Run `make lint`.
- [ ] Push the branch:

```bash
git push -u origin feat/issue-21-log-inspection
```

- [ ] Open a PR that references issue 21 and describes deployed behavior.
- [ ] If any work is deferred, file a GitHub issue for each deferred item and repeat this workflow for each new issue.
- [ ] Shepherd review comments through follow-up commits until the PR is merged.
