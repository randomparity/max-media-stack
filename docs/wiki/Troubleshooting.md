# Troubleshooting

Cross-cutting issues and debug commands for the MMS deployment. All commands below should be run as the `mms` user on the VM unless otherwise noted.

For service-specific troubleshooting, see the individual service pages listed in the sidebar.

## Systemd service debugging

MMS services run as user-level systemd units under the `mms` user.

```bash
# List all MMS container units
systemctl --user list-units 'mms-*'

# Check a specific service
systemctl --user status radarr.service

# View recent logs for a service
journalctl --user -u radarr --since today

# Follow logs in real time
journalctl --user -u radarr -f

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
podman logs radarr
podman logs --tail 50 -f radarr

# Inspect container config (volumes, env, networking)
podman inspect radarr

# Check container health status
podman healthcheck run radarr

# Exec into a running container
podman exec -it radarr /bin/bash

# Check resource usage
podman stats --no-stream
```

**Common issue: Container stuck in "Created" or restart loop**

Check the logs for the root cause, then restart:

```bash
podman logs radarr
systemctl --user restart radarr.service
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
systemd-analyze --user verify radarr.service

# Check what the generator produced
systemctl --user cat radarr.service
```

**Common issue: "Unit foo.service not found"**

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
grep age_public_key ~/mms/inventory/group_vars/all/vars.yml
```

**Common issue: "age: error: no identity matched"**

The identity file (private key) doesn't match the public key used for encryption. Verify you're using the correct identity file:

```bash
age --decrypt -i /path/to/identity.txt < backup.tar.zst.age > /dev/null
```

**Common issue: Permission denied during restore**

The service must be stopped before restoring. The restore playbook handles this, but if restoring manually, stop the service first:

```bash
systemctl --user stop radarr.service
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

## Service-specific issues

Each service has its own wiki page with detailed troubleshooting. See:

- [Prowlarr](Prowlarr) -- Indexer manager
- [Radarr](Radarr) / [Radarr 4K](Radarr-4K) -- Movie managers
- [Sonarr](Sonarr) -- TV series manager
- [Lidarr](Lidarr) -- Music manager
- [SABnzbd](SABnzbd) -- Usenet downloader
- [Jellyfin](Jellyfin) -- Media server
- [Plex](Plex) -- Media server
- [Tautulli](Tautulli) -- Plex analytics
- [Kometa](Kometa) -- Plex metadata manager
- [Channels DVR](Channels-DVR) -- Live TV and DVR
- [Navidrome](Navidrome) -- Music streaming
- [Immich](Immich) -- Photo management (multi-container)
- [Open Notebook](Open-Notebook) -- AI notebook (multi-container)
- [Traefik](Traefik) -- Reverse proxy operations
- [Observability](Observability) -- Loki, Alloy, Prometheus, Grafana, podman-exporter
