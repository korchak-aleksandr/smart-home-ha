# 03. Ubuntu Server install

Install Ubuntu Server on the mini PC, reserve its IP address on the router, and set up SSH key login.
After this step, the display and keyboard can be unplugged for good.

**Before you start:**

- BIOS prepared and booted from the USB stick, see [01. Hardware and BIOS](01-hardware-bios.md).
- The mini PC is connected to the router **with an Ethernet cable**. A wired connection is more
  reliable for a smart home server (stable, low latency, no radio interference), and the installer
  configures it automatically. Wi-Fi can be prepared later as a fallback, see
  [step 9](#9-network-optional-interfaces-and-wi-fi-readiness).
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
| Featured server snaps | select **nothing**. Docker is installed separately in [05. Docker](05-docker.md). |

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

## 4. Reach the server by name (mDNS)

The router may give the server a different IP address after a reboot, and the address also differs between
Ethernet and Wi-Fi (each interface has its own MAC address). Instead of tracking addresses, make the server
answer to **`<hostname>.local`**, e.g. `homeserver.local`, on whatever interface and IP it currently has.

This uses **mDNS** (multicast DNS, a part of "Zeroconf"). It's the same technology Apple calls *Bonjour*: on
the local network, a device announces its own name, and nobody needs to configure a DNS server.
On Linux, the standard implementation is **Avahi**. Ubuntu Desktop and most Linux desktops ship it by default,
and printers and AirPlay/Chromecast discovery rely on the same mechanism.

Log in once with the password, using the IP from the installer:

```bash
ssh <user>@192.168.1.50                  # ← REPLACE user and IP
sudo apt install -y avahi-daemon         # mDNS responder: announces <hostname>.local on the LAN
```

From your workstation, check that the name resolves:

```bash
ping -c 2 homeserver.local               # ← REPLACE hostname
```

- **macOS, iOS, Linux desktops, Windows 10+** resolve `.local` names out of the box. Android support varies.
- mDNS works **only inside the local network** (one subnet). It doesn't cross VPNs or routed networks.
- It doesn't conflict with Home Assistant's own device discovery (zeroconf) later on.
- **Cache after an address change.** When the server switches interfaces (e.g. Ethernet → Wi-Fi) or gets a new IP,
  clients may keep the old address cached for ~2 minutes (the mDNS record TTL is 120 s), and `ssh` hangs trying
  it. Wait a couple of minutes, or flush the cache on macOS:
  `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`.

### Avahi settings

Restrict avahi to the real network interfaces and answer over both IPv4 and IPv6:

```bash
sudo sed -i -E \
  -e 's/^#?allow-interfaces=.*/allow-interfaces=enp1s0,enp2s0,wlo1/' \
  -e 's/^#?use-ipv6=.*/use-ipv6=yes/' \
  -e 's/^#?publish-aaaa-on-ipv4=.*/publish-aaaa-on-ipv4=yes/' \
  -e 's/^#?publish-a-on-ipv6=.*/publish-a-on-ipv6=yes/' \
  /etc/avahi/avahi-daemon.conf          # ← REPLACE interface names with yours (ip -br link)
sudo systemctl restart avahi-daemon
```

- `allow-interfaces`: without it, avahi also announces the name on **Docker's bridge** (`docker0`, `172.17.0.1`). Clients
  then get an unreachable address, and the name flaps whenever Docker changes its interfaces.
- IPv6 on, and A/AAAA records over both protocols: some routers deliver mDNS over IPv6 reliably but not over
  IPv4 (see below). The firewall must then allow SSH/HA over IPv6 ([04, IPv6](04-base-setup.md#ipv6)).

### mDNS troubleshooting

`<hostname>.local` stops resolving after a while, but works right after `sudo systemctl restart avahi-daemon`:

- **IGMP snooping on the router.** The router forwards IPv4 multicast (mDNS uses `224.0.0.251`) only to devices
  that recently joined the group, but never asks them to renew, so the membership expires. Symptom: on the server,
  `sudo tcpdump -ni wlo1 udp port 5353` shows no IPv4 queries from the client, while IPv6 (`fe80::…`) ones arrive.
  Fix: answer over IPv6 (avahi settings above), or turn off IGMP snooping on the router. Don't turn it off if IPTV
  runs through that router.
- **Stale client cache** after an address change (e.g. Ethernet → Wi-Fi): wait ~2 minutes, or flush on macOS:
  `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`.
- **Router DNS:** many ISP routers don't register DHCP hostnames in their DNS, so a plain `homeserver` (without
  `.local`) won't resolve there. Check: `dig +short @<router-ip> homeserver`.

### Fallback: reserve the IP address on the router

For clients without mDNS, or devices that must be configured with an IP, bind the server's address on the
router (DHCP reservation). This is optional.

1. Get the MAC address of the interface (each interface has its own). Either read it on the router's list of
   connected devices, or on the server:
   ```bash
   ip -br link    # brief list of interfaces with MAC addresses, e.g. enp2s0 ... aa:bb:cc:dd:ee:ff
   ```
2. In the router's web admin, find **DHCP reservation**. It is also called *DHCP Static IP*, *Static
   lease* or *Address reservation*, usually under *LAN* or *DHCP Server*.
3. Add the MAC address and the IP address, e.g. `192.168.1.50`. Apply. No reboot is needed.

Router examples: [`devices/router/`](../devices/router/).

**When devices depend on the server's IP, the reservation is mandatory.** Some devices (e.g. sensors that send data
to an MQTT broker on the server) store the server's IP address and can't use `.local` names. Reserve the IP of every
interface the server may use (Ethernet and Wi-Fi).

### Moving to a new network

Devices store the Wi-Fi name and password, and some store the server's IP. To move without re-pairing or factory
resetting anything, configure the new router to match the old network:

1. the **same Wi-Fi name (SSID) and password**;
2. the **same subnet**, e.g. `192.168.1.0/24` (router LAN settings);
3. the **same reserved IP for the server**. If the server switches from Wi-Fi to Ethernet at the new place, reserve
   that same IP for the Ethernet interface's MAC address.

## 5. Copy your SSH key to the server

On your workstation:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <user>@homeserver.local   # ← REPLACE user and hostname
```

This appends your **existing** public key to `~/.ssh/authorized_keys` on the server. It asks for the server
password once. Expected output: `Number of key(s) added: 1`.

## 6. SSH alias

Add a host alias to `~/.ssh/config` on your workstation so that `ssh homeserver` is enough:

```
Host homeserver
  User <user>
  Hostname homeserver.local
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly=yes
  SetEnv LC_CTYPE=C.UTF-8
  ConnectTimeout 10
```

- `Hostname homeserver.local` is the mDNS name from [step 4](#4-reach-the-server-by-name-mdns). It keeps
  working when the IP changes or the server switches between Ethernet and Wi-Fi.
- `IdentitiesOnly=yes` offers only this key, not every key in your agent.
- `SetEnv LC_CTYPE=C.UTF-8` is for **macOS** workstations. macOS sends `LC_CTYPE=UTF-8`, a locale name
  Linux doesn't know, so every `apt` run on the server prints *"perl: warning: Setting locale failed"*.
  This line sends a valid value instead. Not needed on Linux workstations.
- `ConnectTimeout 10` fails fast instead of hanging when the address is unreachable (see the mDNS cache note in
  [step 4](#4-reach-the-server-by-name-mdns)).
- Test it: `ssh homeserver` should log in without a password prompt.

Quick health check after the first login:

```bash
lsb_release -ds    # Ubuntu version
df -h /            # root filesystem size — should be close to the full disk (see the LVM trap)
free -h            # memory
ip -4 -br addr     # IP addresses
```

## 7. Password login over SSH

Decide whether to keep password login over SSH:

| | Keep it | Disable it |
|---|---|---|
| Pros | Fallback if the device with your key is lost: log in from anywhere on the LAN with the password | Nothing to brute-force; the strongest option |
| Cons | Can be brute-forced; needs a strong password and [fail2ban](04-base-setup.md#4-brute-force-protection-fail2ban) | Lose the key = console access needed (display + keyboard) |

Keep it only while SSH isn't reachable from the internet. A second key on another device (e.g. a phone) is a better
fallback than a password. To switch to key-only login, first make sure key login works, then:

```bash
echo "PasswordAuthentication no" | sudo tee /etc/ssh/sshd_config.d/10-no-password.conf   # disable password login
sudo systemctl reload ssh                                                               # apply without dropping sessions
```

## 8. Passwordless sudo (optional)

By default, `sudo` asks for the user's password. If an AI agent runs the setup over SSH, it can't type
that password, so every privileged command has to be run by hand. Allow passwordless `sudo` for your user
(run once, asks for the password one last time):

```bash
ssh -t homeserver 'echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/90-$USER-nopasswd && sudo chmod 440 /etc/sudoers.d/90-$USER-nopasswd && sudo visudo -c'
```

- This writes a separate rule file to `/etc/sudoers.d/`. `chmod 440` is required: sudo ignores rule files with
  looser permissions.
- `visudo -c` validates the syntax, so a typo can't lock you out of `sudo`. Expected output: `parsed OK`.
- To undo it, delete the file: `sudo rm /etc/sudoers.d/90-<user>-nopasswd`.

Trade-off: anyone who gets into your user account gets root without a password. On a server reachable
only from the home network, this changes little: such a person could also wait for you to type the
password.

## 9. Network: optional interfaces and Wi-Fi readiness

### Mark unused Ethernet ports as optional

Many mini PCs have two Ethernet ports. The installer adds **both** to the network config, and at every
boot `systemd-networkd-wait-online` waits for the unplugged one until it times out. Boot then takes
**~2 minutes longer**, and every service that waits for the network (Docker, Home Assistant) starts that
much later.

Check it:

```bash
systemd-analyze blame | grep wait-online                                   # ~2min = the problem
systemctl cat systemd-networkd-wait-online.service | grep ExecStart        # lists the interfaces it waits for
```

Fix it: in `/etc/netplan/00-installer-config.yaml`, add `optional: true` to the unused port. Example with
`enp2s0` wired and `enp1s0` unused:

```yaml
network:
  version: 2
  ethernets:
    enp2s0:                  # primary: wired, DHCP reservation on the router
      dhcp4: true
      dhcp6: true
      accept-ra: true
    enp1s0:                  # second port: unused; optional so boot does not wait for it
      match:
        macaddress: aa:bb:cc:dd:ee:ff   # ← REPLACE (keep what the installer wrote)
      set-name: enp1s0
      dhcp4: true            # still gets an address if you ever plug the cable here
      optional: true
```

Apply it:

```bash
sudo cp -a /etc/netplan/00-installer-config.yaml /root/00-installer-config.yaml.orig   # backup first
sudo nano /etc/netplan/00-installer-config.yaml                                         # edit
sudo netplan generate && sudo netplan apply                                             # validate, then apply
```

`netplan generate` fails on a syntax error before anything changes. Since the wired interface's settings
stay the same, `apply` doesn't drop the SSH session.

**Always plug the cable into the same port.** The DHCP reservation is bound to that port's MAC address.

### Wi-Fi readiness

Wi-Fi is a useful fallback even if it isn't used day to day. To make it ready to configure:

1. **Driver:** Intel Wi-Fi cards work out of the box (`iwlwifi`). Check that the interface exists:
   `ip -br link` should list a `wl…` interface, e.g. `wlo1`. No extra drivers are needed.
2. **`wpasupplicant`:** it handles WPA2/WPA3 authentication. The installer adds it only when you install
   *without* a cable, so on a wired install it's usually missing. `iw` is a tool to scan for networks.
   ```bash
   sudo apt install -y wpasupplicant iw
   ```
3. **Check:** scan for networks. Your home network should appear with a strong signal (around -30 to -60 dBm):
   ```bash
   sudo iw dev wlo1 scan | grep -E 'SSID:|signal:'   # ← REPLACE wlo1 with your interface name
   ```

### Connect to Wi-Fi

Use [`scripts/setup-wifi.sh`](../scripts/setup-wifi.sh). It asks for the network name and the password (hidden
input, so the password never ends up in shell history or chat logs) and writes `/etc/netplan/60-wifi.yaml`
(root-only, mode 600). It validates the config before applying it.

Do this **while the cable is still connected**, so a mistake can't cut you off:

```bash
scp scripts/setup-wifi.sh homeserver:~/                    # copy the script to the server
ssh -t homeserver 'WIFI_COUNTRY=CY ~/setup-wifi.sh'        # ← REPLACE CY with your country code
```

- `-t` gives the script a terminal, so it can ask for the password.
- `WIFI_COUNTRY` sets the regulatory domain. Without it, Linux uses the restrictive "world" domain, and
  some 5 GHz channels are unavailable.
- Expected output: the Wi-Fi interface with an IPv4 address, e.g. `wlo1  UP  192.168.1.51/24`.

The Wi-Fi interface has its own MAC address, so it gets a **different IP** than Ethernet. With mDNS
([step 4](#4-reach-the-server-by-name-mdns)), `homeserver.local` keeps working on either one.

### Turn off Wi-Fi power saving

By default, the Wi-Fi radio sleeps between beacons from the router and wakes up every 100–300 ms. That's
good for a laptop, which starts its own connections. A server mostly **receives** traffic: SSH, the Home
Assistant UI, sensors pushing updates, mDNS queries. Every incoming packet waits for the radio to wake up, which
adds latency and drops. Intel Wi-Fi on Linux is also known to lose connections in this mode. The savings are
around 0.5–1 W, so turn it off:

```bash
# udev rule: turn power saving off whenever a Wi-Fi interface appears (at boot, after driver reload)
echo 'ACTION=="add", SUBSYSTEM=="net", KERNEL=="wl*", RUN+="/usr/sbin/iw dev $name set power_save off"' \
  | sudo tee /etc/udev/rules.d/81-wifi-powersave-off.rules
sudo udevadm control --reload            # load the new rule
sudo iw dev wlo1 set power_save off      # apply now, without a reboot (← REPLACE wlo1)
iw dev wlo1 get power_save               # expected: Power save: off
```

### Wired or Wi-Fi as the main connection

Boot waits only for interfaces **without** `optional: true`. Exactly one connection should be required: the
one the server actually uses. Otherwise boot either waits ~2 minutes for a missing link, or services start
before the network is up.

| Mode | Ethernet (`enp2s0` in `00-installer-config.yaml`) | Wi-Fi (`wlo1` in `60-wifi.yaml`) |
|------|------------------------------------------------|----------------------------------|
| **Wired** (recommended) | no `optional` | `optional: true` (fallback) |
| **Wi-Fi only** (no cable at the location) | `optional: true` | no `optional` |

`setup-wifi.sh` writes Wi-Fi as optional by default. Run it with `WIFI_REQUIRED=1` for the Wi-Fi-only mode,
or edit the files by hand. After any change:

```bash
sudo netplan generate && sudo netplan apply                       # validate and apply
systemctl cat systemd-networkd-wait-online.service | grep ExecStart   # shows which interface boot waits for
```

The route metric (Ethernet 100, Wi-Fi 600) makes traffic prefer the cable whenever both are connected.

## Done

The display and keyboard can be unplugged. All further work happens over SSH. Next:
[04. Base server setup](04-base-setup.md).
