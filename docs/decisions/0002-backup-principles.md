# 0002. Backup principles

- **Status:** accepted
- **Date:** 2026-11-22

## Context

A smart home server accumulates state that is painful to recreate: Home Assistant configuration and
history, device pairings (Zigbee network keys), automations, and secrets. The server runs unattended and
powers back on by itself after outages, so problems with backups go unnoticed unless something reports them.

The most common way backups fail is not a missing backup job. Backups fail **silently**: the job stopped
running, the target disk died or was never mounted, or the archive is corrupt and nobody tried to restore it.

## Decision

Every backup in this repository follows these rules. Agents and humans adding a backup job must implement
all of them. A job that skips one is incomplete.

1. **A different physical device.** Backups never go to the same disk as the data. A USB drive that stays
   plugged into the server is the minimum: it protects against SSD failure and human error.
2. **Verify every backup.** After writing, check integrity (e.g. `restic check`, or checksums of the written
   archive read back from the target). **An unverified backup counts as no backup.**
3. **Monitor the backup target's health.** At minimum, before every run:
   - the target is **actually mounted** (`mountpoint -q`). Otherwise the job writes into an empty directory on the system
     SSD, which looks like success;
   - a write → read-back → checksum test of a small file passes;
   - free space is above a threshold;
   - no filesystem errors are reported (e.g. the ext4 error count in `tune2fs -l`, I/O errors in the kernel log).
   
   Cheap USB flash drives usually have no SMART data and fail without warning. That's why the active read/write
   test matters.
4. **Alert on failure, and on silence.** A failed run, a failed verification or a failed health check sends an alert
   (Telegram). Also alert when **no successful backup happened** within the expected interval (a "dead man's
   switch"): a job that silently stopped running produces no failure messages.
5. **Test restores.** Periodically restore from the backup into a scratch location and check the result. Document the
   restore procedure next to the backup procedure.
6. **A robust filesystem on the target.** Use a journaling filesystem (ext4) for always-attached backup drives:
   the server is expected to lose power, and non-journaling filesystems (exFAT, FAT32) can be corrupted by
   that. Mount the target with `nofail`, so a missing or dead drive never blocks boot.
7. **An off-site copy (later).** A drive inside the same case doesn't survive theft, fire or a power surge. A second,
   off-site copy (e.g. cloud storage, encrypted) completes the setup (3-2-1 rule: 3 copies, 2 media, 1 off-site).
8. **Secrets are backed up, but not to git.** `.env` files and `secrets.yaml` are part of the backup. They never
   go into this repository. Off-site copies must be encrypted.

## Consequences

- Backup scripts are a bit more complex than a plain `tar` in cron, but failures become visible.
- The Telegram bot (see the roadmap) is a dependency for alerting. Until it exists, health-check failures must at
  least be logged and visible on login.
