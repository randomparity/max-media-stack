# Renovate Dashboard Issue 28 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the actionable dependency updates documented in GitHub issue #28 while preserving the explicit decision to stay on Python 3.13.

**Architecture:** Treat Renovate issue #28 as the source of dependency update intent, but make the repo state explicit in version-controlled files. Apply low-risk dependency updates in focused commits grouped by dependency surface: Ansible Galaxy collections, service container images, Traefik, and Renovate configuration for the blocked Python update.

**Tech Stack:** Ansible, Fedora target host, rootless Podman/Quadlet, Renovate, GitHub Actions, Python 3.13 tooling.

---

## Issue Summary

GitHub issue #28 is the Renovate Dependency Dashboard. As of 2026-05-10, it lists these actionable items:

- `docker.io/valkey/valkey` `9.0.3` -> `9.0.4`
- `lscr.io/linuxserver/tautulli` `2.17.0` -> `2.17.1`
- `containers.podman` Galaxy collection `1.19.2` -> `1.20.1`
- `docker.io/library/traefik` `v3.6` -> `v3.7`
- Closed and blocked PR #70 for GitHub Actions Python `3.13` -> `3.14`

PR #70 was closed by the repository owner on 2026-03-23 with the comment: "Not willing to update at this time." The plan therefore keeps Python at `3.13` and makes that policy explicit in Renovate config so the dashboard stops presenting the blocked update as work to do.

## File Structure

- Modify `requirements.yml`
  - Owns Ansible Galaxy collection pins, including `containers.podman`.
- Modify `roles/immich/defaults/main.yml`
  - Owns Immich stack image pins, including Valkey.
- Modify `services/tautulli.yml`
  - Owns the Tautulli service image pin.
- Modify `roles/traefik/defaults/main.yml`
  - Owns the Traefik image pin.
- Modify `renovate.json5`
  - Owns Renovate grouping, schedules, automerge policy, and ignored dependencies.

## Preflight

- [ ] **Step 1: Leave `main` before editing**

Run:

```bash
git status --short --branch
```

Expected: the branch is not `main` or `master` before code edits begin. If it is still `main`, create a work branch:

```bash
git switch -c chore/issue-28-renovate-dashboard
```

- [ ] **Step 2: Refresh issue and PR context**

Run:

```bash
gh issue view 28 --comments --json title,state,updatedAt,body,url
gh pr view 70 --comments --json title,state,closedAt,comments,url
```

Expected:

- Issue #28 is still open and still lists the same dependency updates, or newer Renovate versions are substituted into the steps below.
- PR #70 is closed because Python 3.14 was intentionally declined.

## Task 1: Update Ansible Galaxy Collection Pin

**Files:**

- Modify: `requirements.yml`

- [ ] **Step 1: Change `containers.podman` to `1.20.1`**

Edit the existing `containers.podman` entry so the file contains:

```yaml
---
collections:
  - name: community.general
    version: "12.6.0"
  - name: community.proxmox
    version: "1.6.0"
  - name: ansible.posix
    version: "2.1.0"
  - name: containers.podman
    version: "1.20.1"
```

- [ ] **Step 2: Install the pinned collection set**

Run:

```bash
make setup
```

Expected: `ansible-galaxy collection install -r requirements.yml` completes without warnings or dependency conflicts.

- [ ] **Step 3: Verify collection resolution**

Run:

```bash
source .venv/bin/activate
ansible-galaxy collection list containers.podman
```

Expected: output includes `containers.podman 1.20.1`.

- [ ] **Step 4: Commit**

Run:

```bash
git add requirements.yml
git commit -m "chore(deps): update containers.podman to 1.20.1"
```

## Task 2: Update Scheduled Service Image Pins

**Files:**

- Modify: `roles/immich/defaults/main.yml`
- Modify: `services/tautulli.yml`

- [ ] **Step 1: Update Valkey for Immich**

Edit `roles/immich/defaults/main.yml` so the Redis image line is:

```yaml
immich_redis_image: "docker.io/valkey/valkey:9.0.4"
```

- [ ] **Step 2: Update Tautulli**

Edit `services/tautulli.yml` so the image line is:

```yaml
  image: "lscr.io/linuxserver/tautulli:2.17.1"
```

- [ ] **Step 3: Run YAML and Ansible lint**

Run:

```bash
make lint
```

Expected: `yamllint` and `ansible-lint` complete with zero warnings.

- [ ] **Step 4: Run a check-mode render for affected services**

Run:

```bash
source .venv/bin/activate
ansible-playbook playbooks/deploy-service.yml -e service_name=tautulli --check --diff
ansible-playbook playbooks/site.yml --check --diff --tags immich
```

Expected:

- Tautulli planned diff changes only the Tautulli image tag.
- Immich planned diff changes only the Valkey image tag or generated units that include it.

- [ ] **Step 5: Commit**

Run:

```bash
git add roles/immich/defaults/main.yml services/tautulli.yml
git commit -m "chore(deps): update valkey and tautulli images"
```

## Task 3: Update Traefik Image Pin

**Files:**

- Modify: `roles/traefik/defaults/main.yml`

- [ ] **Step 1: Update Traefik**

Edit `roles/traefik/defaults/main.yml` so the image line is:

```yaml
traefik_image: "docker.io/library/traefik:v3.7"
```

- [ ] **Step 2: Run Traefik role Molecule test**

Run:

```bash
source .venv/bin/activate
cd roles/traefik
molecule test -s default
```

Expected: Molecule converge and verify steps pass. If Docker or Podman backend access is unavailable locally, run this instead and record the limitation in the PR:

```bash
source .venv/bin/activate
ansible-playbook playbooks/site.yml --check --diff --tags traefik
```

- [ ] **Step 3: Run lint**

Run:

```bash
make lint
```

Expected: zero warnings.

- [ ] **Step 4: Commit**

Run:

```bash
git add roles/traefik/defaults/main.yml
git commit -m "chore(deps): update traefik to v3.7"
```

## Task 4: Make Python 3.13 Policy Explicit

**Files:**

- Modify: `renovate.json5`

- [ ] **Step 1: Add `ignoreDeps` for Python runtime updates**

Keep the existing package rule that disables Python updates, and add a top-level `ignoreDeps` entry near the existing schedule/timezone settings:

```json5
{
  $schema: 'https://docs.renovatebot.com/renovate-schema.json',
  extends: [
    'config:recommended',
  ],
  schedule: [
    'before 6am on Monday',
  ],
  timezone: 'America/New_York',
  ignoreDeps: [
    'python',
  ],
  ignorePaths: [
    'roles/quadlet_service/molecule/**',
  ],
```

- [ ] **Step 2: Validate Renovate config syntax**

Run:

```bash
docker run --rm \
  -v "$PWD:/repo" \
  -w /repo \
  renovate/renovate:43.59.0 \
  renovate-config-validator renovate.json5
```

Expected: Renovate reports that the config is valid. If Docker is unavailable locally, validate in the Renovate dashboard after pushing and record that local validation was skipped.

- [ ] **Step 3: Commit**

Run:

```bash
git add renovate.json5
git commit -m "chore(renovate): ignore python runtime updates"
```

## Task 5: Final Verification and Dashboard Cleanup

**Files:**

- No additional file changes expected.

- [ ] **Step 1: Run final repo validation**

Run:

```bash
make lint
make check
```

Expected:

- `make lint` completes with zero warnings.
- `make check` completes without failed tasks. Planned service diffs are limited to dependency version updates.

- [ ] **Step 2: Review the final diff**

Run:

```bash
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- requirements.yml roles/immich/defaults/main.yml services/tautulli.yml roles/traefik/defaults/main.yml renovate.json5
```

Expected: the diff contains only the dependency pin updates and the Renovate `ignoreDeps` policy.

- [ ] **Step 3: Push branch and open PR**

Run:

```bash
git push -u origin chore/issue-28-renovate-dashboard
gh pr create \
  --title "chore(deps): resolve Renovate dashboard updates" \
  --body "Updates the scheduled dependency pins from Renovate issue #28 and keeps Python on 3.13 by adding an explicit Renovate ignore for the declined Python 3.14 update.

Validation:
- make lint
- make check
- ansible-galaxy collection list containers.podman
- molecule test -s default from roles/traefik, or documented fallback check-mode validation"
```

- [ ] **Step 4: Let Renovate refresh the dashboard**

After the PR merges, either wait for the next scheduled Renovate run or check the manual job checkbox in issue #28:

```text
Check this box to trigger a request for Renovate to run again on this repository
```

Expected:

- The Valkey, Tautulli, `containers.podman`, and Traefik items disappear from "Awaiting Schedule".
- The Python 3.14 blocked item disappears because `python` is ignored.

## Self-Review

- Spec coverage: The plan covers every actionable item listed in issue #28 on 2026-05-10.
- Placeholder scan: No placeholder markers or undefined implementation steps remain.
- Type and file consistency: All file paths and dependency names match the current repo files and Renovate dashboard text.
