# 07. Backups

All backups follow [0002. Backup principles](decisions/0002-backup-principles.md): a separate physical
device, verification of every run, health checks of the target, and alerts on failure and on silence.

This guide currently covers the **backup drive**. Backup jobs, verification, health checks and restore are
added as they are implemented.

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
