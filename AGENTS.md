# Repository Guidelines

## Project Structure & Module Organization

This repository is an Ansible project for deploying the Max Media Stack on a
Fedora VM with rootless Podman and Quadlet. Top-level playbooks live in
`playbooks/`, reusable roles live in `roles/`, and service definitions live in
`services/*.yml`. Inventory and host variables are under `inventory/`, including
vault files and `vault.yml.example` templates. Shared Jinja templates are in
`templates/`; role-specific templates stay inside each role. Wiki source content
is kept in `docs/wiki/`.

## Build, Test, and Development Commands

- `make setup` creates `.venv`, installs Python tooling, and installs Ansible
  Galaxy collections from `requirements.yml`.
- `make hooks` installs the configured pre-commit hooks.
- `make lint` runs `yamllint` and `ansible-lint` against playbooks and roles.
- `make check` runs `playbooks/site.yml` in Ansible check mode with diffs.
- `make deploy` applies the full stack with `playbooks/site.yml`.

Use `ansible-playbook playbooks/deploy-service.yml -e service_name=radarr` for
focused service deployment when appropriate.

## Coding Style & Naming Conventions

Use two-space YAML indentation and keep tasks explicit and readable. Role names
use snake_case, for example `roles/base_system` and `roles/quadlet_service`.
Service files use lowercase names matching the service key, such as
`services/sonarr.yml`. Keep role defaults in `defaults/main.yml`, handlers in
`handlers/main.yml`, and templates beside the role that owns them. Run
`make lint` before opening a pull request; the repo also uses pre-commit hooks
for YAML checks, secret detection, trailing whitespace, and large-file checks.

## Testing Guidelines

Molecule scenarios live under `roles/<role>/molecule/default/`. Add or update a
scenario when changing role behavior, especially generated Quadlet files,
firewall/system settings, or service configuration. Run focused tests with
`source .venv/bin/activate && molecule test -s default` from the role directory.
For broader validation, run `make check` to verify the site playbook can render
and plan changes without applying them.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit style, especially Renovate commits like
`chore(deps): update dependency community.general to v12.6.0`. Use an
imperative, scoped subject when possible, such as `fix(traefik): correct dynamic
router template`. Pull requests should describe the deployed behavior, list the
validation commands run, and call out any inventory, vault, DNS, or host changes
operators must make.

## Security & Configuration Tips

Do not commit secrets. Keep real credentials in Ansible Vault files and update
the matching `vault.yml.example` only with placeholder values. Treat changes to
firewall rules, published ports, Podman socket access, and SELinux labels as
security-sensitive; document the operational impact in the pull request.
