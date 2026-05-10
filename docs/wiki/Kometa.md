# Kometa

Plex metadata manager -- automatically manages collections, overlays, and metadata for Plex libraries on a schedule.

| Property | Value |
|----------|-------|
| **Image** | `lscr.io/linuxserver/kometa` (LSIO) |
| **Container name** | `kometa` |
| **Internal port** | None (batch process, no web UI) |
| **Traefik subdomain** | None |
| **Config directory** | `/home/mms/config/kometa` |
| **Health endpoint** | None |
| **Backup type** | `arr` (config backup only, no API backup, no database) |
| **Autodeploy group** | `interactive` (daily at 02:00) |
| **Depends on** | `plex.service` |

## Service Management

```bash
systemctl --user start kometa.service
systemctl --user stop kometa.service
systemctl --user restart kometa.service
systemctl --user status kometa.service
```

Kometa runs as a long-lived container that wakes at the configured time (`KOMETA_TIMES=06:00`) to process metadata, then sleeps until the next run.

## Viewing Logs

```bash
journalctl --user -u kometa --since today
journalctl --user -u kometa -f
podman logs --tail 100 kometa
```

Kometa logs are verbose during runs. Look for `Run` and `Finished` markers to identify run boundaries.

## Manual Testing

Testing Kometa configuration is common since config changes can break collection/overlay processing. Run a one-shot test container:

```bash
# Stop the running service first
systemctl --user stop kometa.service

# Run interactively with immediate execution
podman run --rm -it \
  --name test-kometa \
  --userns=host \
  --network mms \
  --tmpfs /run:U \
  -e PUID=0 \
  -e PGID=0 \
  -e TZ=America/New_York \
  -e KOMETA_RUN=true \
  -v /home/mms/config/kometa:/config:Z \
  lscr.io/linuxserver/kometa:latest
```

**Critical: `KOMETA_RUN=true`** triggers an immediate run instead of waiting for the scheduled time. Without this, the container will just sleep.

**LSIO image rules (these are critical for Kometa testing):**
- Use `PUID`/`PGID` environment variables -- do **NOT** use `--userns=keep-id` (breaks s6-overlay preinit, causing `s6-overlay-suexec: fatal: unable to exec /etc/s6-overlay/s6-rc.d/init/run: Operation not permitted`)
- Use `--userns=host` so rootless Podman maps the host `mms` user to root inside the container for s6-overlay startup
- Use `PUID=0`/`PGID=0` so files written by Kometa remain editable by the host `mms` user
- Use `--network mms` (the Podman network name), not `--network mms.network` (that's the Quadlet filename, not the network)
- Use `--tmpfs /run:U` for s6-overlay compatibility (`:U` chowns to container user)
- Use `:Z` on the config volume for SELinux private labeling

**Fix file ownership after manual runs:**

If you ran a test container with different user mappings (or accidentally with `PUID=3000`), config files may end up owned by a rootless Podman subuid such as `592823`. Fix with:

```bash
podman unshare chown -R 0:0 /home/mms/config/kometa
```

## Backup & Restore

- **Config backup**: Daily at 03:00, encrypted with age, saved to `/data/backups/config/kometa/`
- No database files (Kometa stores config in YAML files)

```bash
ansible-playbook playbooks/restore.yml \
  -e service_name=kometa \
  -e backup_file=/data/backups/config/kometa/<backup-file>.tar.zst.age \
  -e backup_age_identity_file=/path/to/age-identity.txt
```

## Inter-Container Connections

| Direction | Target | URL | Purpose |
|-----------|--------|-----|---------|
| Kometa -> Plex | `plex` | `http://plex:32400` | Library metadata management |

Kometa requires a Plex token and server URL in its config. The connection uses the internal container hostname since both are on the `mms` network.

## Common Issues

**s6-overlay init failure with `--userns=keep-id`**

This is the most common gotcha when manually testing Kometa. LSIO images use s6-overlay which requires running as root inside the container, then dropping to the PUID/PGID user. Using `--userns=keep-id` maps the host user directly, breaking s6-overlay's privilege model:

```
s6-overlay-suexec: fatal: unable to exec /etc/s6-overlay/s6-rc.d/init/run: Operation not permitted
```

**Solution:** Use `UserNS=host` with `PUID=0` and `PGID=0`. Rootless Podman still maps container root to the host `mms` user, so s6-overlay can start and Kometa-written files stay editable from the host.

**"Network mms.network not found"**

Podman network names don't include the `.network` suffix -- that's the Quadlet file extension. Use `--network mms`:

```bash
# Wrong:
podman run --network mms.network ...

# Right:
podman run --network mms ...
```

**Config files owned by wrong user**

After a manual run, files in `/home/mms/config/kometa` may be owned by a different UID inside the user namespace. Fix ownership:

```bash
podman unshare chown -R 0:0 /home/mms/config/kometa
```

**Kometa can't connect to Plex**

First verify Plex is running and reachable from within the container network:

```bash
podman exec kometa curl -sf http://plex:32400/identity
```

This checks connectivity only. Plex may return `200 OK` from `/identity` even with
an invalid token, so do not use this endpoint to validate credentials.

Validate the Plex token against an authenticated API endpoint:

```bash
podman exec kometa curl -i \
  "http://plex:32400/library/sections?X-Plex-Token=<plex-token>"
```

A valid token returns `200 OK` with a `MediaContainer` listing libraries. An
invalid token returns `401 Unauthorized`.

Also verify the Plex URL in Kometa's config YAML uses the container hostname
(`http://plex:32400`), not a Traefik URL. Check both the global `plex:` block
and any per-library `plex:` overrides.
