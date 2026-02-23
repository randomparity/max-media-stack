# Immich

Self-hosted photo and video management -- provides Google Photos-like features with AI-powered search, face detection, and automatic organization. Runs as a multi-container stack with four services.

| Container | Image | Port | Health |
|-----------|-------|------|--------|
| `immich-server` | `ghcr.io/immich-app/immich-server` | 2283 | `http://localhost:2283/api/server/ping` |
| `immich-ml` | `ghcr.io/immich-app/immich-machine-learning` | 3003 | Internal |
| `immich-postgres` | `docker.io/tensorchord/pgvecto-rs` | 5432 | pg_isready |
| `immich-redis` | `docker.io/valkey/valkey` | 6379 | Internal |

| Property | Value |
|----------|-------|
| **Traefik subdomain** | `immich.media.drc.nz` |
| **Config directory** | `/home/mms/config/immich` |
| **Local media directory** | `/home/mms/config/immich/media` (SSD, generated content) |
| **NFS upload directory** | `/data/photos` (user content) |
| **Backup type** | Config backup (local SSD content excluded) |
| **Autodeploy group** | `interactive` (daily at 02:00) |

## Volume Split

Immich uses a split volume strategy to optimize performance:

| Type | Path | Storage | Content |
|------|------|---------|---------|
| **NFS** | `/data/photos/upload` | TrueNAS | Uploaded photos/videos |
| **NFS** | `/data/photos/library` | TrueNAS | External library imports |
| **Local SSD** | `~/config/immich/media/encoded-video` | VM disk | Transcoded video |
| **Local SSD** | `~/config/immich/media/thumbs` | VM disk | Thumbnails |
| **Local SSD** | `~/config/immich/media/profile` | VM disk | Profile images |
| **Local SSD** | `~/config/immich/media/backups` | VM disk | Internal backups |

Generated content on local SSD is excluded from config backups since it's regenerable.

## Service Management

```bash
# All four containers
systemctl --user start immich-postgres.service
systemctl --user start immich-redis.service
systemctl --user start immich-server.service
systemctl --user start immich-ml.service

# Or restart them in order
systemctl --user restart immich-postgres.service
systemctl --user restart immich-redis.service
systemctl --user restart immich-server.service
systemctl --user restart immich-ml.service
```

**Startup order matters:** PostgreSQL must be ready before the server starts. Redis should also be running. The Quadlet files use `After=` dependencies to enforce this.

## Viewing Logs

```bash
# Server logs (most useful for debugging)
podman logs --tail 100 immich-server
podman logs -f immich-server

# Database logs
podman logs --tail 50 immich-postgres

# ML engine logs
podman logs --tail 50 immich-ml

# Redis logs
podman logs --tail 50 immich-redis

# Systemd unit logs
journalctl --user -u immich-server --since today
```

## Health Check

```bash
# Server health
podman healthcheck run immich-server
curl -sf http://immich.media.drc.nz/api/server/ping

# PostgreSQL health
podman healthcheck run immich-postgres

# Check all containers are running
podman ps --filter name=immich
```

## Manual Testing

Immich is managed by a dedicated Ansible role (not the generic `quadlet_service` role), so manual testing is less common. If needed, test the server container:

```bash
# Stop all Immich services first
systemctl --user stop immich-server.service immich-ml.service
systemctl --user stop immich-redis.service immich-postgres.service

# Start just PostgreSQL and Redis for the server to connect to
# (manual testing of the full stack is complex -- usually better to debug via logs)
```

For most debugging, inspecting logs and health checks is more practical than running containers manually.

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/immich/`
- **Excluded**: Local SSD generated content (thumbnails, transcoded video, profiles) -- all regenerable
- **Included**: PostgreSQL data directory, Redis data, server config

NFS content (uploads, library) is backed up separately by TrueNAS snapshots.

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=immich \
  -e backup_file=/data/backups/config/immich/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Server -> PostgreSQL | `immich-postgres` | `postgresql://immich-postgres:5432/immich` | Database |
| Server -> Redis | `immich-redis` | `redis://immich-redis:6379` | Cache/queue |
| Server -> ML | `immich-ml` | `http://immich-ml:3003` | AI processing |
| ML -> Redis | `immich-redis` | `redis://immich-redis:6379` | Job queue |

All containers communicate on the shared `mms` network using container hostnames.

## Common Issues

**Server won't start / connection refused**

Almost always a database issue. Check PostgreSQL first:

```bash
podman logs immich-postgres
podman healthcheck run immich-postgres
```

If PostgreSQL is healthy but the server still can't connect, verify the database credentials match between the server environment and the PostgreSQL container.

**ML processing stuck / slow**

The ML container handles face detection, CLIP embeddings, and smart search. Check its logs:

```bash
podman logs --tail 50 immich-ml
```

ML processing is CPU-intensive. Check resource usage:

```bash
podman stats --no-stream --filter name=immich
```

**Upload directory not writable**

The upload directory is an NFS mount at `/data/photos`. Verify it's mounted and writable:

```bash
mount | grep photos
touch /data/photos/test && rm /data/photos/test
```

**Thumbnails not generating after restore**

After restoring from backup, generated content (thumbnails, transcoded video) will be missing since it's excluded from backups. Immich will regenerate this content automatically, but it takes time. You can trigger a manual regeneration from the Immich admin UI under Jobs.
