# 03. Ubuntu Server install

Install Ubuntu Server on the mini PC, reserve its IP address on the router, and set up SSH key login.
After this step, the display and keyboard can be unplugged for good.

**Before you start:**

- BIOS prepared and booted from the USB stick, see [01. Hardware and BIOS](01-hardware-bios.md).
- The mini PC is connected to the router **with an Ethernet cable**. A wired connection is more
  reliable for a smart home server, and the installer configures it automatically.
- Your workstation (laptop) has an SSH key. Check with `ls ~/.ssh/*.pub`. If there is none, create one
  with `ssh-keygen -t ed25519`.

## 1. Installer walkthrough

In the boot menu, choose **Try or Install Ubuntu Server**. Navigate with `Tab` / arrow keys, select with
`Enter`, toggle checkboxes with `Space`.

| Screen | What to choose |
|--------|----------------|
| Language | `English` |
| Installer update available | **Update to the new installer** (if offered) |
| Keyboard configuration | your layout, e.g. `English (US)` |
| Type of installation | **Ubuntu Server** (not *minimized*). Leave *third-party drivers* unchecked. |
| Network configuration | The wired interface (`enp…` / `eno…`) gets an address via DHCP. **Write down the IP address**, e.g. `192.168.1.50/24`. `/24` is the subnet mask. The address itself is `192.168.1.50`. |
| Proxy | leave empty |
| Ubuntu archive mirror | keep the default, wait for the mirror test to pass |
| Guided storage configuration | See [below](#2-storage-use-the-whole-disk). |
| Profile configuration | See [below](#3-profile). |
| Upgrade to Ubuntu Pro | **Skip for now** |
| SSH configuration | ☑ **Install OpenSSH server**. ☑ *Allow password authentication over SSH* (see [step 7](#7-password-login-over-ssh)). *Import SSH key*: only if your public key is on GitHub/Launchpad, otherwise **No**. |
| Featured server snaps | select **nothing**. Docker is installed separately in [04. Docker](04-docker.md). |

When **Reboot Now** appears, select it. When asked to *remove the installation medium*, pull out the USB
stick (no "safe eject" is needed, the installer has already released it) and press `Enter`.

After the reboot, the console shows `<hostname> login:`. You don't need to log in there.

## 2. Storage: use the whole disk

On **Guided storage configuration**:

- ☑ **Use an entire disk**. Select the internal SSD, **not** the USB stick. This erases the preinstalled OS.
- ☑ **Set up this disk as an LVM group**: keep it.
- ☐ **Encrypt the LVM group with LUKS**: **leave it off.** With encryption, every boot waits for a passphrase
  typed on a keyboard, so the server can't come back on its own after a power outage.

> ⚠️ **The LVM trap.** By default the installer gives the root volume (`ubuntu-lv`) only ~100 GB and leaves the rest
> of the disk unallocated.

On the **Storage configuration** summary:

1. Under **USED DEVICES**, select `ubuntu-lv` → **Edit**.
2. Set **Size** to the maximum shown next to the field (`max`).
3. **Save** and check that `ubuntu-lv` now takes almost the whole disk.
4. **Done** → *Confirm destructive action* → **Continue**.

If you already installed with the default size, you can grow the volume later without reinstalling:

```bash
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv   # grow the LV and its filesystem (-r) to all free space
```

## 3. Profile

| Field | Notes |
|-------|-------|
| Your name | Display name only (cosmetic). Spaces and capitals are fine. |
| Server's name | Hostname, e.g. `homeserver`. Lowercase letters, digits and hyphens, not at the start or end. |
| Username | Your login. Short, lowercase, e.g. `alex`. `root` is not allowed. Avoid `admin`, `ubuntu` and `user`: bots try these first. The user gets full rights via `sudo` anyway. |
| Password | Strong password. Needed for `sudo` and as a fallback login. |

## 4. Reserve the IP address on the router

By default, the router may give the server a different address after a reboot. Bind the address to the
server's network card so that it never changes:

1. Get the MAC address of the wired interface. Either read it on the router's list of connected devices, or on the
   server:
   ```bash
   ip -br link    # brief list of interfaces with MAC addresses, e.g. enp2s0 ... aa:bb:cc:dd:ee:ff
   ```
2. In the router's web admin, find **DHCP reservation**. It is also called *DHCP Static IP*, *Static
   lease* or *Address reservation*, usually under *LAN* or *DHCP Server*.
3. Add the MAC address and the IP address the server got during install, e.g. `192.168.1.50`. Apply.

No reboot is needed: the server keeps its current address and gets the same one on every renewal.

Router examples: [`devices/router/`](../devices/router/).

If the router has no reservation feature, configure a static IP on the server instead (netplan). Pick an
address **outside** the router's DHCP range to avoid conflicts.

## 5. Copy your SSH key to the server

On your workstation:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <user>@192.168.1.50   # ← REPLACE user and IP
```

This appends your **existing** public key to `~/.ssh/authorized_keys` on the server. It asks for the server
password once. Expected output: `Number of key(s) added: 1`.

## 6. SSH alias

Add a host alias to `~/.ssh/config` on your workstation so that `ssh homeserver` is enough:

```
Host homeserver
  User <user>
  Hostname 192.168.1.50
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly=yes
```

- `IdentitiesOnly=yes` offers only this key, not every key in your agent.
- Test it: `ssh homeserver` should log in without a password prompt.

Quick health check after the first login:

```bash
lsb_release -ds    # Ubuntu version
df -h /            # root filesystem size — should be close to the full disk (see the LVM trap)
free -h            # memory
ip -4 -br addr     # IP addresses
```

## 7. Password login over SSH

Password login over SSH stays **enabled** in this setup as a fallback: if the workstation with the key is
lost, you can still log in from any other device with the password. The server is reachable only from the
home network (no port forwarding on the router), so the risk is low. Use a strong password.

If you prefer key-only access (e.g. if you ever expose SSH outside the home network), first make sure
key login works, then:

```bash
echo "PasswordAuthentication no" | sudo tee /etc/ssh/sshd_config.d/10-no-password.conf   # disable password login
sudo systemctl reload ssh                                                               # apply without dropping sessions
```

Keep a second key (e.g. on another device) before doing this.

## Done

The display and keyboard can be unplugged. All further work happens over SSH. Next:
[04. Docker](04-docker.md).
