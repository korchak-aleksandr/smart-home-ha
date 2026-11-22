# 02. Installation media: Ubuntu Server USB stick

Download the Ubuntu Server image, verify it, write it to a USB stick and verify the stick.

**You need:** a USB stick of 4 GB or more (**it will be completely erased**), and a computer with
macOS, Linux or Windows.

## 1. Choose the image

Use the **latest Ubuntu Server LTS point release**, amd64:

- **LTS only.** LTS releases are `YY.04` in even years (24.04, 26.04, ...) and get 5 years of
  standard support. Interim releases (`YY.10`, odd `YY.04`) are supported for only 9 months. Don't
  use them on a server.
- **Latest point release.** Within an LTS, pick the highest point version (e.g. `26.04.1` over
  `26.04`). It installs with fresher packages, so there is less to update right after install.
- **Server, not Desktop.** The machine runs headless. A desktop environment only wastes resources.
- **amd64 (x86-64).** This is the architecture of Intel N-series mini PCs.

All releases are listed at <https://releases.ubuntu.com/>. The file name looks like
`ubuntu-<VERSION>-live-server-amd64.iso`.

## 2. Download and verify the image

In the examples below, `26.04.1` is used as the version. Replace it with the current latest LTS point release.

### macOS / Linux

```bash
VERSION=26.04.1                                   # latest LTS point release
ISO=ubuntu-${VERSION}-live-server-amd64.iso
cd ~/Downloads                                    # any directory with ~4 GB free

curl -fLO https://releases.ubuntu.com/${VERSION}/${ISO}            # the image (~3 GB)
curl -fLO https://releases.ubuntu.com/${VERSION}/SHA256SUMS        # official checksums
curl -fLO https://releases.ubuntu.com/${VERSION}/SHA256SUMS.gpg    # signature of the checksums
```

**Check the checksum.** This proves the download is complete and not corrupted.

```bash
# macOS
shasum -a 256 --ignore-missing -c SHA256SUMS
# Linux
sha256sum --ignore-missing -c SHA256SUMS
```

Expected output: `ubuntu-<VERSION>-live-server-amd64.iso: OK`. `--ignore-missing` skips the other
images that are listed in `SHA256SUMS` but were not downloaded.

**Optional: verify the signature.** This proves the checksums themselves come from Ubuntu. It needs
`gpg` (macOS: `brew install gnupg`).

```bash
# Import the "Ubuntu CD Image Automatic Signing Key (2012)" from Ubuntu's keyserver
curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x843938DF228D22F7B3742BC0D94AA3F0EFE21092" | gpg --import
gpg --keyid-format long --verify SHA256SUMS.gpg SHA256SUMS
```

Expected output: `Good signature from "Ubuntu CD Image Automatic Signing Key (2012) <cdimage@ubuntu.com>"`,
signed with the key `843938DF228D22F7B3742BC0D94AA3F0EFE21092`. A warning that the key is "not certified with
a trusted signature" is normal.

### Windows

Download the ISO from <https://releases.ubuntu.com/> in a browser, then in PowerShell:

```powershell
Get-FileHash .\ubuntu-26.04.1-live-server-amd64.iso -Algorithm SHA256
```

Compare the hash with the line for your file in `SHA256SUMS` from the same release page.

## 3. Write the image to the USB stick

> ⚠️ Writing is **destructive and irreversible**. Everything on the target disk is erased. Choosing the
> wrong disk (e.g. an external backup drive) destroys its data. Unplug all other external drives first.

### macOS

**Find the USB stick:**

```bash
diskutil list external
```

The command lists only external disks. Identify the stick by size and name, e.g. `/dev/disk4` with
`16.0 GB`. `diskutil info /dev/diskN` shows the model (`Device / Media Name`) if you're unsure.

**Write the image:**

```bash
DISK=disk4    # ← REPLACE with your stick's identifier from `diskutil list external`

diskutil unmountDisk /dev/$DISK                                      # release the disk from macOS
sudo dd if="$ISO" of=/dev/r$DISK bs=4m status=progress   # write the image byte-for-byte (needs sudo)
sync                                                                 # flush write buffers
```

- `/dev/rdiskN` (raw device) instead of `/dev/diskN` bypasses the macOS buffer cache. This is several
  times faster.
- A USB 2.0 stick writes at ~7 MB/s (≈7 minutes for 3 GB). A USB 3 stick is much faster.
- macOS may show *"The disk you attached was not readable by this computer"* after writing. Click
  **Ignore** or **Eject**, **never "Initialize"**: that erases the stick. The message only means macOS
  cannot read the Linux file system on it.

### Linux

```bash
lsblk -d -o NAME,SIZE,MODEL,TRAN    # find the stick: TRAN=usb, e.g. sdb
DISK=sdX                            # ← REPLACE with your stick, e.g. sdb (the whole disk, not sdb1)

sudo umount /dev/${DISK}?* 2>/dev/null                                   # unmount auto-mounted partitions
sudo dd if="$ISO" of=/dev/$DISK bs=4M status=progress oflag=sync # write the image
```

### Windows

Use [Rufus](https://rufus.ie/). If it asks, choose **"Write in DD Image mode"**. Alternatively, use
[balenaEtcher](https://etcher.balena.io/), which verifies the stick automatically after writing.

## 4. Verify the USB stick

Read back exactly as many bytes as the ISO has and compare their SHA256 with the ISO's. This checks
the raw bytes, so it works even though the host OS can't read the stick's file system. If even
one byte was written incorrectly, the hashes differ.

### macOS

```bash
diskutil unmountDisk /dev/$DISK    # macOS may auto-mount partitions after writing; unmount again

SIZE=$(stat -f %z "$ISO")          # ISO size in bytes
# read SIZE bytes from the stick (raw reads must be whole blocks, so read 1 MiB blocks and trim)
sudo dd if=/dev/r$DISK bs=1m count=$(( (SIZE + 1048575) / 1048576 )) 2>/dev/null | head -c "$SIZE" | shasum -a 256
shasum -a 256 "$ISO"               # hash of the ISO for comparison

diskutil eject /dev/$DISK          # safely eject when the hashes match
```

### Linux

```bash
SIZE=$(stat -c %s "$ISO")
sudo head -c "$SIZE" /dev/$DISK | sha256sum
sha256sum "$ISO"
sudo eject /dev/$DISK
```

**The two hashes must be identical.** If they differ, rewrite the stick. If they still differ, try another
stick.

## Next step

Configure the BIOS and install Ubuntu Server: [01. Hardware and BIOS](01-hardware-bios.md),
then [03. Ubuntu Server install](03-ubuntu-install.md).
