# Troubleshooting

Common issues and debug commands for the MMS deployment. All commands below should be run as the `mms` user on the VM unless otherwise noted.

## Systemd service debugging

MMS services run as user-level systemd units under the `mms` user.

```bash
# List all MMS container units
systemctl --user list-units 'mms-*'

# Check a specific service
systemctl --user status mms-radarr.service

# View recent logs for a service
journalctl --user -u mms-radarr --since today

# Follow logs in real time
journalctl --user -u mms-radarr -f

# Check all timers (backups, autodeploy)
systemctl --user list-timers
```

**Common issue: "Failed to connect to bus"**

If `systemctl --user` or `journalctl --user` fails with a D-Bus error, ensure the environment variables are set:

```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
```

This typically happens when SSH-ing directly as the `mms` user or using `sudo -u mms`. The user session must be active via `loginctl`.

**Common issue: "User session not active"**

Ensure lingering is enabled so the user session starts at boot:

```bash
# As root:
loginctl enable-linger mms
```

## Container issues

```bash
# List running containers
podman ps

# View container logs
podman logs mms-radarr
podman logs --tail 50 -f mms-radarr

# Inspect container config (volumes, env, networking)
podman inspect mms-radarr

# Check container health status
podman healthcheck run mms-radarr

# Exec into a running container
podman exec -it mms-radarr /bin/bash

# Check resource usage
podman stats --no-stream
```

**Common issue: Container stuck in "Created" or restart loop**

Check the logs for the root cause, then restart:

```bash
podman logs mms-radarr
systemctl --user restart mms-radarr.service
```

If the container won't start at all, check that the image was pulled successfully:

```bash
podman images | grep radarr
```

## Quadlet and systemd generator

MMS uses Podman Quadlet files in `~/.config/containers/systemd/` to define containers as systemd units.

```bash
# List Quadlet files
ls ~/.config/containers/systemd/

# After modifying a Quadlet file, reload the generator
systemctl --user daemon-reload

# Verify a unit file is valid
systemd-analyze --user verify mms-radarr.service

# Check what the generator produced
systemctl --user cat mms-radarr.service
```

**Common issue: "Unit mms-foo.service not found"**

After creating or modifying Quadlet files, you must run `systemctl --user daemon-reload` for systemd to pick up the changes. The Ansible deploy handles this automatically via handlers.

## NFS mount problems

NFS mounts are defined in `/etc/fstab` and mounted at `/data/`.

```bash
# Check mount status
mount | grep nfs

# Remount if stale
sudo umount -l /data/media && sudo mount /data/media

# Test NFS connectivity
showmount -e <truenas-ip>
```

**Common issue: "Stale file handle"**

This occurs when the NFS server was restarted or the export was modified. Force unmount and remount:

```bash
sudo umount -l /data/media
sudo mount /data/media
```

**Common issue: SELinux denials with NFS volumes**

NFS volumes must NOT use `:Z` or `:z` SELinux labels. Instead, enable the `virt_use_nfs` SELinux boolean:

```bash
# Check current state
getsebool virt_use_nfs

# Enable (the Ansible base_system role does this automatically)
sudo setsebool -P virt_use_nfs on
```

Check for AVC denials:

```bash
sudo ausearch -m avc --start today | grep nfs
```

## Rootless Podman pitfalls

**Environment variables**: User-level systemd operations require `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` to be set. Ansible tasks that interact with the `mms` user's systemd must include:

```yaml
become: true
become_user: mms
environment:
  XDG_RUNTIME_DIR: "/run/user/{{ mms_uid }}"
  DBUS_SESSION_BUS_ADDRESS: "unix:path=/run/user/{{ mms_uid }}/bus"
```

**Lingering**: The `mms` user must have lingering enabled (`loginctl enable-linger mms`) so that user services start at boot and survive SSH disconnects.

**Subuids/subgids**: Rootless Podman requires subuid/subgid mappings. These are configured by the `podman` role. Verify with:

```bash
grep mms /etc/subuid /etc/subgid
```

**tmpfs mounts**: The `crun` runtime does NOT support `uid=`/`gid=` as tmpfs mount options. Use `Tmpfs=/run:U` in Quadlet files instead -- the `:U` flag is a Podman extension that chowns the mount to match the container user.

## Backup and restore failures

### Config backup issues

```bash
# Check backup timer
systemctl --user list-timers mms-backup.timer

# View backup logs
journalctl --user -u mms-backup --since today

# List existing backups
ls -la /data/backups/config/
```

**Common issue: age encryption errors**

If backups fail with age-related errors, verify the public key is set correctly:

```bash
# Check the configured key
grep age_public_key /home/mms/mms/inventory/group_vars/all/vars.yml
```

### Restore issues

**Common issue: "age: error: no identity matched"**

The identity file (private key) doesn't match the public key used for encryption. Verify you're using the correct identity file:

```bash
# Check what public key the backup was encrypted with
age --decrypt -i /path/to/identity.txt < backup.tar.zst.age > /dev/null
```

**Common issue: Permission denied during restore**

The service must be stopped before restoring. The restore playbook handles this, but if restoring manually, stop the service first:

```bash
systemctl --user stop mms-radarr.service
```

## Auto-deploy issues

```bash
# Check autodeploy timers
systemctl --user list-timers 'mms-autodeploy-*'

# View autodeploy logs
journalctl --user -u mms-autodeploy-backend --since today

# Check deploy logs
ls ~/logs/autodeploy/

# View most recent deploy log
ls -t ~/logs/autodeploy/deploy-*.log | head -1 | xargs cat
```

**Common issue: Deploy stuck / lock file**

A stale lock file can prevent deploys. Check and remove if the previous deploy process is not running:

```bash
# Check for lock file
ls -la ~/autodeploy/.deploy.lock

# Check if a deploy is actually running
pgrep -f ansible-playbook

# Remove stale lock (only if no deploy is running)
rm ~/autodeploy/.deploy.lock
```

**Common issue: "Permission denied (publickey)"**

The deploy key is not configured correctly. Verify SSH access to GitHub:

```bash
ssh -i ~/.ssh/mms_deploy_key -T git@github.com
```

**Common issue: Deploys not triggering**

Each group tracks its own SHA. If the state file has the latest commit, the deploy won't run:

```bash
# Check stored SHA per group
cat ~/autodeploy/.last-sha-*

# Compare with remote
cd ~/autodeploy/repo && git fetch && git rev-parse origin/main
```

## Traefik routing issues

**404 errors**: Traefik is running but the route doesn't match.

```bash
# Check Traefik is running
systemctl --user status mms-traefik.service

# Test with explicit Host header from the VM
curl -H "Host: radarr.media.example.com" http://localhost

# Check the generated Traefik config
cat ~/config/traefik/dynamic/*.yml
```

**Wrong backend / connection refused**: The backend container may not be running or is on a different network.

```bash
# Verify the backend container is running
podman ps | grep radarr

# Test direct connectivity to the backend
podman exec mms-traefik curl -s http://radarr:7878

# Check the container is on mms.network
podman network inspect mms | grep radarr
```

**DNS not resolving**: The wildcard DNS record may not be configured.

```bash
# Test DNS resolution
dig myservice.media.example.com

# Workaround: use /etc/hosts on the client
echo "<tailscale-ip> radarr.media.example.com" | sudo tee -a /etc/hosts
```

## Immich-specific issues

Immich is a multi-container stack (server, ML, PostgreSQL, Redis) with specific startup ordering.

```bash
# Check all Immich containers
podman ps | grep immich

# Startup order: postgres -> redis -> server + ML
systemctl --user status mms-immich-postgres.service
systemctl --user status mms-immich-redis.service
systemctl --user status mms-immich-server.service
systemctl --user status mms-immich-ml.service

# View server logs (most useful for debugging)
podman logs --tail 100 mms-immich-server
```

**Common issue: Server won't start**

Usually a database connection issue. Check that PostgreSQL is running and healthy first:

```bash
podman logs mms-immich-postgres
podman healthcheck run mms-immich-postgres
```

## Disk space and image pruning

Container image updates leave behind old (dangling) images that accumulate over time. MMS has two cleanup mechanisms:

1. **Weekly timer** (`mms-image-prune.timer`) -- runs `podman image prune -f` on a schedule (default: Sunday 05:00)
2. **Post-deploy prune** -- the autodeploy script prunes dangling images after each successful deploy

```bash
# Check the prune timer
systemctl --user list-timers mms-image-prune.timer

# View prune logs
journalctl --user -u mms-image-prune --since today

# Manual prune (dangling images only)
podman image prune -f

# Check disk usage
podman system df

# List dangling images
podman images --filter dangling=true
```

**Common issue: Disk full despite pruning**

If the root filesystem is filling up, check whether non-dangling (tagged) images are accumulating. The timer and autodeploy only prune dangling images. To remove all unused images (including tagged ones not used by any container):

```bash
podman image prune -af
```

## Open Notebook-specific issues

Open Notebook is a two-container stack: the app container (`mms-open-notebook`) and a SurrealDB database container (`mms-open-notebook-db`). SurrealDB must be running and ready before the app can connect.

```bash
# Check both containers
podman ps | grep open-notebook

# Check systemd unit status
systemctl --user status mms-open-notebook.service
systemctl --user status mms-open-notebook-db.service

# View app logs
podman logs --tail 50 mms-open-notebook

# View SurrealDB logs (check here first for DB issues)
podman logs --tail 50 mms-open-notebook-db

# Test SurrealDB readiness
podman exec mms-open-notebook-db /surreal isready -e http://localhost:8000
```

**Common issue: App won't connect to database**

Check SurrealDB logs first -- the database must be fully ready before the app can connect. If SurrealDB is in a restart loop, check its logs for storage or permission errors:

```bash
podman logs mms-open-notebook-db
```

If needed, restart in order (database first, then app):

```bash
systemctl --user restart mms-open-notebook-db.service
systemctl --user restart mms-open-notebook.service
```

**Note:** Backups for Open Notebook cause brief downtime because they use a cold backup strategy (both containers are stopped during the backup).
