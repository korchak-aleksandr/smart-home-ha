# SanDisk Cruzer Fit 16 GB

Tiny USB flash drive, used as the always-attached backup drive. Setup: [07. Backups → Backup drive](../../../docs/07-backups.md#1-backup-drive).

| Property | Value |
|----------|-------|
| Interface | USB 2.0 |
| Usable size | 14.91 GB (`f3probe`: real capacity, not fake) |
| Write speed | ~4 MB/s (`dd`, 64 MiB, `conv=fsync`) |
| Read speed | ~21 MB/s |
| Filesystem | ext4, GPT, label `backup`, mounted at `/mnt/backup` |
| `f3probe --destructive` time | ~5 minutes |

## Notes

- The slow write speed is fine for configs and the Home Assistant database. It isn't suitable for camera
  recordings.
- No SMART data, so health is checked actively before each backup (see the health-check table in the guide).
- A Linux installer written to it adds several partitions. `wipefs -a` cleans them up before formatting.
