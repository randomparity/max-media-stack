# Open Notebook

AI-powered notebook application -- provides a web interface for note-taking with LLM integration. Runs as a two-container stack with a SurrealDB database backend.

| Container | Image | Port | Health |
|-----------|-------|------|--------|
| `open-notebook` | `docker.io/lfnovo/open_notebook` | 8502 | Internal |
| `open-notebook-db` | `docker.io/surrealdb/surrealdb` | 8000 | `/surreal isready` |

| Property | Value |
|----------|-------|
| **Traefik subdomain** | `notebook.media.drc.nz` |
| **App config directory** | `/home/mms/config/open-notebook` |
| **DB config directory** | `/home/mms/config/open-notebook-db` |
| **Backup type** | Cold backup (both containers stopped) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Service Management

```bash
# App container
systemctl --user start open-notebook.service
systemctl --user stop open-notebook.service
systemctl --user restart open-notebook.service
systemctl --user status open-notebook.service

# Database container
systemctl --user start open-notebook-db.service
systemctl --user stop open-notebook-db.service
systemctl --user restart open-notebook-db.service
systemctl --user status open-notebook-db.service
```

**Startup order:** SurrealDB must be running and ready before the app container starts. The Quadlet file uses `After=` to enforce this.

## Viewing Logs

```bash
# App logs
podman logs --tail 50 open-notebook
podman logs -f open-notebook

# SurrealDB logs (check here first for database issues)
podman logs --tail 50 open-notebook-db

# Systemd unit logs
journalctl --user -u open-notebook --since today
journalctl --user -u open-notebook-db --since today
```

## Health Check

```bash
# Check SurrealDB readiness
podman exec open-notebook-db /surreal isready -e http://localhost:8000

# Check both containers are running
podman ps --filter name=open-notebook
```

## Manual Testing

Open Notebook is managed by a dedicated role with split setup (`setup.yml` for templates, `containers.yml` for runtime). For debugging, log inspection is usually more practical than running containers manually.

If needed:

```bash
# Stop both services
systemctl --user stop open-notebook.service
systemctl --user stop open-notebook-db.service

# Test SurrealDB separately
podman run --rm -it \
  --name test-surrealdb \
  --network mms \
  --userns=keep-id \
  --tmpfs /run:U \
  -v /home/mms/config/open-notebook-db:/data:Z \
  docker.io/surrealdb/surrealdb:latest \
  start --log info file:/data/database.db
```

## Backup & Restore

Open Notebook uses a **cold backup** strategy -- both the app and SurrealDB containers are stopped before the backup, then restarted afterward. This causes brief downtime but is necessary because SurrealDB has no hot-dump CLI tool.

The backup creates a single tar archive containing both `open-notebook/` and `open-notebook-db/` config directories.

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/open-notebook/`
- **Brief downtime** during backup window

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=open-notebook \
  -e backup_file=/data/backups/config/open-notebook/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

The restore playbook handles stopping/starting both containers and restoring both directories from the single archive.

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| App -> SurrealDB | `open-notebook-db` | `ws://open-notebook-db:8000` | Database |

## Common Issues

**App won't connect to database**

Check SurrealDB logs first -- the database must be fully ready before the app connects:

```bash
podman logs open-notebook-db
podman exec open-notebook-db /surreal isready -e http://localhost:8000
```

If SurrealDB is in a restart loop, check for storage or permission errors in its logs.

If needed, restart in order (database first, then app):

```bash
systemctl --user restart open-notebook-db.service
# Wait for DB to be ready
sleep 5
systemctl --user restart open-notebook.service
```

**Database corruption after unclean shutdown**

SurrealDB can be sensitive to unclean shutdowns. If the database won't start after a crash or power loss, check its logs for recovery messages. Restore from the most recent backup if recovery fails.

**Backup causes downtime**

This is expected. The cold backup window is brief (typically under a minute) and runs at 03:00 when usage is minimal.
