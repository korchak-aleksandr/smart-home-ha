# 07. Backups

All backups follow [0002. Backup principles](decisions/0002-backup-principles.md): a separate physical
device, verification of every run, health checks of the target, and alerts on failure and on silence.

| | |
|---|---|
| **What** | Home Assistant config and state (with a consistent DB snapshot), stack secrets (`.env`, `secrets/`), Grafana DB, host configs |
| **Where** | the always-attached backup drive, `/mnt/backup/archives/` |
| **Format** | one plain `backup-YYYY-MM-DD.tar.zst` per day + `.sha256`. Opens anywhere with `tar` + `zstd`, no special tool |
| **When** | daily at 03:00 (runs at the next boot if missed). Verification of all archives weekly, Sunday 05:00 |
| **Retention** | 7 days |
| **Checks** | drive health before every run, read-back checksum after every run, full re-read weekly |
| **Monitoring** | metrics for Grafana (*Server overview → Backups*), alerts later with the Telegram bot |

## 1. Backup drive

A USB drive that stays plugged into the server permanently. Even a small flash drive is enough for
configs and the Home Assistant database, and it's strictly better than a backup on the same SSD.

### Identify the drive

> ⚠️ The next steps **erase** the drive. Make sure you pick the USB drive, not the system disk.

```bash
lsblk -o NAME,SIZE,TYPE,TRAN,MODEL,FSTYPE,LABEL,MOUNTPOINTS   # TRAN=usb is the USB drive, e.g. sdb
ls -l /dev/disk/by-id/usb-*                                   # stable name with model and serial number
```

Use the `/dev/disk/by-id/usb-…` path, or double-check the `sdX` name: `sdX` letters can change between
boots and when drives are plugged in.

```bash
DEV=/dev/sdX            # ← REPLACE with the USB drive, the whole disk (not sdX1)
lsblk -dno TRAN,MODEL,SIZE $DEV   # must print "usb" and your drive's model
```

### Check the real capacity (flash drives)

Fake flash drives that report more capacity than they have are common. Writes beyond the real capacity
silently get lost, which is fatal for backups. `f3probe` detects this by writing to the drive
(**destructive**, takes a few minutes):

```bash
sudo apt install -y f3
sudo umount ${DEV}?* 2>/dev/null                   # unmount auto-mounted partitions, if any
sudo f3probe --destructive --time-ops $DEV          # expected: "Good news: The device ... is the real thing"
```

If it reports a smaller *usable* size than announced, don't use the drive for backups.

### Partition and format as ext4

```bash
sudo wipefs -a $DEV                                         # remove old partition tables and filesystem signatures
sudo parted -s $DEV mklabel gpt mkpart backup ext4 1MiB 100% # one GPT partition over the whole drive
sudo udevadm settle                                         # wait until the new partition device appears
sudo mkfs.ext4 -L backup -m 0 ${DEV}1                       # ext4 with the label "backup"
sudo tune2fs -e remount-ro ${DEV}1                          # on filesystem errors: switch to read-only
```

- **ext4** because the server is expected to lose power: ext4 has a journal and survives that. exFAT or FAT32
  can be corrupted by a power loss during a write. The downside is that macOS and Windows can't read ext4
  natively. Access backups through the server (`scp` / `rsync`) or any Linux machine, which is where you
  would restore anyway.
- `-m 0`: by default ext4 reserves 5% of the space for root. A data-only drive doesn't need that reserve.
- `-e remount-ro`: when the kernel detects filesystem errors, it turns the filesystem read-only instead of
  continuing to write. Backup jobs then fail loudly and alert, instead of writing to a damaged filesystem.

### Mount permanently with `nofail`

```bash
UUID=$(sudo blkid -s UUID -o value ${DEV}1)      # stable ID of the new filesystem
sudo mkdir -p /mnt/backup
echo "UUID=$UUID  /mnt/backup  ext4  defaults,noatime,nofail,x-systemd.device-timeout=10s  0  2" | sudo tee -a /etc/fstab
sudo systemctl daemon-reload                     # make systemd pick up the new fstab entry
sudo mount /mnt/backup
```

| Option | Why |
|--------|-----|
| `UUID=…` | Identifies the filesystem itself, not the `sdX` name, which can change. |
| `noatime` | Don't write access times on every read. That means fewer writes, so less flash wear. |
| `nofail` | **Critical.** If the drive is missing or dead, boot continues. Without it, the server stops at boot in emergency mode and needs a keyboard and display. |
| `x-systemd.device-timeout=10s` | Wait 10 s for a missing drive instead of the default 90 s. |
| `0 2` | No `dump`. Check the filesystem (`fsck`) at boot, after the root filesystem. |

### Marker file

```bash
echo "This filesystem is the backup target. Backup jobs check for this file before writing." \
  | sudo tee /mnt/backup/.backup-target
```

On Linux, a drive is **mounted over** an ordinary directory. If the drive isn't mounted (unplugged, dead, or
skipped at boot thanks to `nofail`), `/mnt/backup` is just an empty directory on the system SSD. A backup job
would happily write there and report success, while the "backup" sits on the same disk as the data. Backup
jobs therefore check **both** `mountpoint -q /mnt/backup` and the presence of `.backup-target` before writing
anything. The marker also catches a *different* drive mounted there by mistake.

### Make the empty mount point immutable

A second guard at the filesystem level: mark the **underlying** empty directory as immutable. When the drive
isn't mounted, any write to `/mnt/backup` fails with *Permission denied*, even as root, instead of silently
landing on the SSD. The flag lives on the directory *under* the mount, so the mounted drive isn't affected.

```bash
sudo umount /mnt/backup             # the flag must be set on the empty directory, not on the drive
ls -A /mnt/backup                   # must print nothing: the directory is empty
sudo chattr +i /mnt/backup          # set the immutable flag
lsattr -d /mnt/backup               # expected: ----i--------- /mnt/backup
sudo touch /mnt/backup/test         # expected: "Permission denied" (nothing can be written while unmounted)
sudo mount /mnt/backup              # mount the drive again; writes to it work as usual
```

To remove the flag later (e.g. to delete the mount point): `sudo chattr -i /mnt/backup` while unmounted.

### Verify

```bash
findmnt /mnt/backup                  # mounted, rw
df -h /mnt/backup                    # size and free space
sudo tune2fs -l ${DEV}1 | grep -E 'Errors behavior|Reserved block count'   # Remount read-only / 0
```

Write/read-back test with a checksum:

```bash
dd if=/dev/urandom of=/tmp/rwtest bs=1M count=64 status=none                        # 64 MiB of random data
sudo dd if=/tmp/rwtest of=/mnt/backup/.rwtest bs=1M conv=fsync                      # write + flush; shows write speed
echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null                               # force the next read from the drive
sudo dd if=/mnt/backup/.rwtest of=/dev/null bs=1M                                   # read; shows read speed
sha256sum /tmp/rwtest; sudo sha256sum /mnt/backup/.rwtest                           # the hashes must match
sudo rm -f /mnt/backup/.rwtest /tmp/rwtest
```

A USB 2.0 flash drive typically writes 4–10 MB/s and reads ~20 MB/s.

Also confirm that boot tolerates a missing drive. Optional, but it proves `nofail` works: unplug the drive,
reboot, check that the server comes up, then plug the drive back in and run `sudo mount /mnt/backup`.

### Health checks (for backup jobs)

Cheap flash drives usually have no SMART data and die without warning, so health is checked actively before
every backup run:

| Check | Command | Failure means |
|-------|---------|---------------|
| Mounted, right drive | `mountpoint -q /mnt/backup && test -f /mnt/backup/.backup-target` | Drive missing or not mounted (writes would also fail thanks to `chattr +i`) |
| Writable | `findmnt -no OPTIONS /mnt/backup` doesn't contain `ro` | Remounted read-only after errors |
| Read/write | write a small random file, `sync`, drop caches, read it back, compare checksums | Failing flash |
| Free space | `df --output=pcent /mnt/backup` | Drive full |
| Filesystem errors | `sudo tune2fs -l <partition> \| grep 'FS Error count'` (only shown when errors have occurred) | Corruption detected |
| Kernel I/O errors | `journalctl -k --since -1day \| grep -iE 'I/O error\|ext4-fs error'` | Failing drive or cable |

Any failed check aborts the backup and sends an alert.

Example drive: [SanDisk Cruzer Fit 16 GB](../devices/usb-storage/sandisk-cruzer-fit-16gb/README.md).

## 2. What is backed up

| Included | Path |
|----------|------|
| Home Assistant: config, `.storage` (accounts, integrations, device keys), automations, custom components | `/opt/smart-home/homeassistant/config` |
| Home Assistant history DB, as a **consistent snapshot** (`sqlite3 .backup`, the SQLite online backup API: HA keeps running and writing) | `…/home-assistant_v2.db` |
| Stack: compose file, `.env`, `secrets/`, monitoring config | `/opt/smart-home` |
| Grafana's own DB (users, preferences; dashboards are in git anyway) | `/opt/smart-home/grafana/grafana.db` |
| Host configs: netplan (incl. Wi-Fi), ufw, fail2ban, SSH server drop-ins, sudoers, Docker, systemd units, fstab, avahi, sysctl, udev, apt sources | `/etc/...` |

| Not included | Why |
|--------------|-----|
| Metrics history (VictoriaMetrics) | Nice to have, not worth the size and the flash writes. Monitoring starts fresh after a restore. |
| Grafana plugins, HA `.cache`, `tts`, logs | Re-created automatically |
| Docker images | Versions are pinned in git and pulled again |
| The OS itself | Reinstalled by following these guides |

**No encryption** for the local drive: it's physically inside the server, and the data (Wi-Fi password, HA device keys,
local service passwords) is low-value. Revisit when sensitive data appears. Off-site copies must be encrypted
([0002](decisions/0002-backup-principles.md)).

When a service with its own data directory is added to the stack (e.g. Mosquitto, Zigbee2MQTT), it goes into the
backup in the same change.

## 3. Install

```bash
sudo apt install -y sqlite3 zstd
sudo install -m 755 scripts/backup.sh /usr/local/sbin/smart-home-backup          # from this repo, copied to the server
sudo cp configs/systemd/backup.service configs/systemd/backup.timer \
        configs/systemd/backup-verify.service configs/systemd/backup-verify.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer backup-verify.timer
sudo systemctl start backup.service                                             # first run now
journalctl -u backup.service -o cat | tail -3                                   # "[backup] OK: backup-....tar.zst"
systemctl list-timers 'backup*'                                                 # next runs
```

Settings (paths, retention, free-space threshold) are variables at the top of the script and can be overridden with
`Environment=` in the service.

## 4. How a run works

`smart-home-backup run`. Every step aborts the run on failure and records the failed step in the metrics:

1. **Drive health** (the checks from [Health checks](#health-checks-for-backup-jobs)): mounted and marked, not
   read-only, ≥ 20% free, no ext4 errors, no kernel I/O errors in the last 24 h, 4 MiB write → read-back → checksum.
2. **HA DB snapshot** with `sqlite3 .backup`, checked with `PRAGMA quick_check`.
3. **Archive**: `tar` the included paths (excluding the live DB) + append the snapshot under the DB's original path,
   compress with zstd.
4. **Copy** to the drive as `*.partial`, flush.
5. **Verify on the drive**: drop the file from the page cache, read it back **from the device**, compare SHA-256,
   test zstd integrity. Only then rename to the final name and write `.sha256`.
6. **Rotate**: delete archives older than 7 days. Only happens after a verified new archive exists.
7. **Metrics** → `/var/lib/node_exporter/textfile/backup.prom`.

`smart-home-backup verify` (weekly) re-reads **every** archive from the device and checks SHA-256 + zstd integrity.
This also exercises the flash drive itself.

> Reading "from the device": some USB flash drives reject `O_DIRECT` reads (`dd iflag=direct` fails with *Invalid
> input*). The script drops the file's cached pages instead (`dd iflag=nocache count=0`) and then reads normally.

## 5. Metrics

| Metric | Meaning |
|--------|---------|
| `smart_home_backup_last_success_timestamp_seconds` | last successful run. Alert if older than 26 h |
| `smart_home_backup_last_run_success` | 1/0 for the last run |
| `smart_home_backup_last_failed_step{step="..."}` | where the last failed run stopped (`drive_mounted`, `drive_read_write`, `ha_db_snapshot`, ...) |
| `smart_home_backup_last_duration_seconds`, `_last_size_bytes`, `_archives` | duration, newest archive size, archives on the drive |
| `smart_home_backup_verify_success`, `_verify_timestamp_seconds`, `_verify_archives_checked/_failed` | weekly verification |

Grafana: *Server overview → Backups*.

## 6. Restore

List and inspect:

```bash
sudo ls -l /mnt/backup/archives/
sudo tar -I zstd -tvf /mnt/backup/archives/backup-YYYY-MM-DD.tar.zst | less     # contents
```

Paths in the archive are relative to `/` (e.g. `opt/smart-home/homeassistant/config/...`).

### Home Assistant only

Use the **same or a newer** HA version than at backup time: a newer HA migrates the DB, an older one can't open it.
The version is pinned in `stack/compose.yaml` (git history has the version of any date).

```bash
cd /opt/smart-home
docker compose stop homeassistant
sudo mv homeassistant/config homeassistant/config.before-restore                 # keep the current state, just in case
sudo tar -I zstd -xf /mnt/backup/archives/backup-YYYY-MM-DD.tar.zst -C / opt/smart-home/homeassistant/config
docker compose start homeassistant
```

The archive's `home-assistant_v2.db` is the consistent snapshot, so no `-wal`/`-shm` files are needed. Devices come
back as they were, as long as they weren't re-paired after the backup (re-pairing changes their keys). On new
hardware, only the Bluetooth adapter is re-discovered.

### A single file or host config

```bash
sudo tar -I zstd -xf /mnt/backup/archives/backup-YYYY-MM-DD.tar.zst -C /tmp/restore etc/fail2ban/jail.local
```

### Whole server (new SSD or new machine)

1. Install Ubuntu and do the base setup by following guides 01–05.
2. Plug in the backup drive, mount it ([section 1](#1-backup-drive)).
3. Extract `opt/smart-home` (stack, secrets, Grafana DB, HA) and the needed `etc/...` files, then
   `docker compose up -d` in `/opt/smart-home`.
4. Re-fetch community dashboards ([08](08-monitoring.md)), re-run `systemctl daemon-reload`, and enable the timers.

## Home Assistant's built-in backups: not used

HA has its own backups (*Settings → System → Backups*), in its own encrypted format. They do the same for HA alone:
a copy of the config with a consistent DB. The daily archive above covers HA plus secrets, Grafana and host configs,
with drive checks and metrics, so the built-in feature stays off. Skip HA's "set up backups" prompt.
