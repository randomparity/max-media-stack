# Storage Layout

MMS splits storage between NFS (bulk media on TrueNAS) and local SSD (per-service config and Immich generated content).

## Directory tree

```
/data/                          # NFS from TrueNAS
├── media/
│   ├── movies/                 # Radarr / Radarr 4K library
│   ├── series/                 # Sonarr library
│   └── music/                  # Lidarr library
├── usenet/
│   ├── incomplete/             # SABnzbd in-progress
│   └── complete/
│       ├── movies/             # Completed movie downloads
│       ├── series/             # Completed TV downloads
│       ├── music/              # Completed music downloads
│       └── manual/             # Manual import staging
├── backups/
│   └── arr-api/                # *arr API backups (30-day retention)
│       ├── prowlarr/
│       ├── radarr/
│       ├── radarr4k/
│       ├── sonarr/
│       └── lidarr/
├── photos/                     # Immich user content (NFS)
│   ├── upload/                 # User uploads
│   └── library/                # External library links
└── recordings/                 # Channels DVR recordings

/home/mms/config/<service>/     # Local SSD, per-service config
/home/mms/config/immich/media/  # Local SSD, Immich generated content
├── encoded-video/              #   Transcoded video (regenerable)
├── thumbs/                     #   Thumbnails (regenerable)
├── profile/                    #   Profile images (regenerable)
└── backups/                    #   Immich internal backups
/home/mms/backups/              # Config backup staging area (age-encrypted)
```

## Design rationale

This follows the [TRaSH Guides](https://trash-guides.info/) recommended folder structure, enabling hardlinks between download and library directories.

### NFS vs local SSD

- **NFS (`/data/`)**: Bulk media, downloads, photos, and API backups. Stored on TrueNAS for capacity and redundancy.
- **Local SSD (`/home/mms/`)**: Per-service config databases and Immich generated content (thumbnails, transcoded video). Stored locally for performance.

### Immich volume split

Immich is the most complex service for storage:

- **User content** (NFS): `upload/` and `library/` under `/data/photos/` -- actual photos and videos
- **Generated content** (local SSD): thumbnails, transcoded video, and profile images under `/home/mms/config/immich/media/` -- regenerable by Immich on demand
- **Config** (local SSD): PostgreSQL database and Redis data under `/home/mms/config/immich/`

This split means backups only need to cover the config directory (database); user content lives on NFS (backed up separately by TrueNAS), and generated content is regenerable.

### SELinux labels

- Local config volumes: `:Z` for private SELinux labeling
- NFS volumes: no `:Z`/`:z` labels (uses `virt_use_nfs` SELinux boolean instead)
