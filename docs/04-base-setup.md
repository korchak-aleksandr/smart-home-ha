# 04. Base server setup

Make the fresh Ubuntu install a reliable, unattended server: correct time, automatic security updates,
a firewall, brute-force protection, automatic recovery from hangs, and SSD health monitoring.

All commands run on the server over SSH. They assume passwordless `sudo`
([03, step 8](03-ubuntu-install.md#8-passwordless-sudo-optional)). Otherwise `sudo` asks for the password.

## 1. Timezone

```bash
sudo timedatectl set-timezone Europe/Nicosia    # ← REPLACE with your zone, list: timedatectl list-timezones
timedatectl                                     # check: Time zone, "System clock synchronized: yes"
```

Logs, backup schedules and cron jobs use local time. Home Assistant has its own timezone setting, but the host
should match. Time synchronization (NTP via `chrony`) is enabled by default on Ubuntu Server.

## 2. Updates

### Update everything now

```bash
sudo apt update                    # refresh package lists
sudo apt full-upgrade -y           # install all updates (including ones that add/remove dependencies)
sudo apt autoremove -y             # remove packages that are no longer needed
cat /var/run/reboot-required 2>/dev/null || echo "no reboot required"   # kernel/libc updates need a reboot
```

### Automatic security updates with automatic reboot

Ubuntu Server installs **security updates automatically** every day (`unattended-upgrades`), but by default it
**never reboots**. A kernel update only takes effect after a reboot. Until then, the server keeps running the old,
vulnerable kernel indefinitely. Allow a reboot at night, **only when an update requires it**:

```bash
sudo tee /etc/apt/apt.conf.d/52unattended-upgrades-local <<'EOF'
// Local overrides for unattended-upgrades
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF
apt-config dump | grep -E 'Unattended-Upgrade::(Automatic-Reboot|Remove-Unused)'   # check the effective values
```

- A separate `52-…` file overrides the defaults in `50unattended-upgrades` and survives package upgrades.
- Cost: Home Assistant is unavailable for about a minute at 04:00 on nights after a kernel update.
- Only Ubuntu packages are updated this way. Docker images are pinned and updated deliberately
  (see [0001](decisions/0001-docker-on-single-host.md)).

## 3. Firewall (ufw)

Policy: **deny all incoming traffic. Allow only the services you use, and only from the home network.** The
commands below show the pattern. Adapt the ports and ranges to your setup. General principles:
[configs/security.md](../configs/security.md).

```bash
sudo ufw default deny incoming                       # block everything incoming by default
sudo ufw default allow outgoing                      # the server may connect anywhere
sudo ufw allow from 192.168.0.0/16 to any port 22 proto tcp comment "SSH from LAN"
sudo ufw allow from 192.168.0.0/16 to any port 5353 proto udp comment "mDNS"
sudo ufw allow from fe80::/10 to any port 5353 proto udp comment "mDNS IPv6 link-local"
sudo ufw --force enable                              # activate now and at every boot
sudo ufw status verbose
```

- `192.168.0.0/16` covers every `192.168.x.x` network, so the rules keep working after moving to another router or
  flat. If your router uses `10.x.x.x` or `172.16–31.x.x`, use `10.0.0.0/8` or `172.16.0.0/12` instead.
- Add the SSH allow rule **before** `enable`. Already-open SSH sessions survive enabling the firewall.
- The Home Assistant port is opened the same way in [06. Home Assistant](06-home-assistant.md).

### IPv6

Most ISPs hand out **global IPv6 addresses** (check with `ip -6 addr`: an address starting with `2…` or `3…`).
IPv6 has no NAT, so a global address is reachable from the internet **unless the router's IPv6 firewall blocks
inbound connections**. Many ISP routers do this by default, but check yours (often *Security → Firewall* or
*IPv6 firewall*).

When mDNS works only over IPv6 ([03, mDNS troubleshooting](03-ubuntu-install.md#mdns-troubleshooting)), clients get
the server's global IPv6 address for `<hostname>.local`, so the firewall must let them in over IPv6. Options:

| Option | Rule | Trade-off |
|--------|------|-----------|
| Strict | allow SSH/HA from your LAN prefix only, e.g. `sudo ufw allow proto tcp from 2001:db8:1:2::/64 to any port 22` | Safe without trusting the router. Update the rule if the ISP changes the prefix. |
| Broad | allow SSH/HA over IPv6 from any address | Simple, but **only after confirming** the router blocks inbound IPv6 from the internet |

Also consider **stable-privacy IPv6 addresses**, so the address doesn't embed the network card's MAC (EUI-64) and
can't be guessed: set `ipv6-address-generation: stable-privacy` for the interface in netplan.

> ⚠️ **Docker bypasses ufw** for containers with published ports (`ports: "8080:80"`). Docker writes its own
> firewall rules that take effect before ufw's, so such a port is open regardless of ufw. Home Assistant runs with
> `network_mode: host`, and ufw does apply to it. For other containers, publish ports bound to a specific address
> (`"127.0.0.1:8080:80"`), never bare `"8080:80"`. See [05. Docker](05-docker.md#5-docker-and-the-firewall).

## 4. Brute-force protection (fail2ban)

fail2ban watches the SSH log and temporarily bans IP addresses with too many failed logins. It's cheap insurance
whenever password login over SSH is enabled.

```bash
sudo apt install -y fail2ban
sudo tee /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
# Example thresholds: choose your own (see below).
maxretry = 5
findtime = 10m
bantime  = 1h
# Never ban the server itself.
ignoreip = 127.0.0.1/8 ::1
# Read logs from the systemd journal.
backend = systemd

[sshd]
enabled = true
EOF
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd        # jail status, failed attempts, banned IPs
```

- `jail.local` overrides the packaged `jail.conf` and survives upgrades.
- **Pick your own thresholds** and don't publish them: knowing the exact limits lets an attacker pace attempts just
  below them. For SSH reachable only from the LAN, mild values are fine. Avoid escalating bans
  (`bantime.increment`) if you don't want to risk locking yourself out for days.
- LAN addresses are deliberately **not** in `ignoreip`: a compromised device on the LAN should get banned too.
- Key-based logins never count as failures. Only wrong passwords and invalid users do.
- **Banned yourself?** Wait for the ban to expire, or unban from another device or the console:
  `sudo fail2ban-client set sshd unbanip <your-ip>`.
- Test it without locking yourself out: from the server itself run `ssh invaliduser@127.0.0.1`. The fail2ban log
  (`sudo tail /var/log/fail2ban.log`) should show `Ignore 127.0.0.1 by ignoreself rule`, which proves that failures are
  detected.

## 5. Hardware watchdog: auto-reboot on hangs

A server that freezes (kernel deadlock, hardware glitch) stays frozen until someone pulls the plug. A **hardware
watchdog** is a timer in the chipset that reboots the machine unless the OS "pings" it regularly. systemd pings it,
so if the system hangs for 30 seconds, the board resets itself.

Intel chipsets have one (`iTCO_wdt`). AMD uses `sp5100_tco`. **Ubuntu deny-lists all watchdog drivers**, and the
usual `/etc/modules-load.d/` mechanism honours that list. Only an explicit `modprobe` loads the driver, so load it
with a small boot service:

```bash
sudo tee /etc/systemd/system/watchdog-driver.service <<'EOF'
# Load the Intel TCO hardware watchdog driver early at boot.
# Ubuntu deny-lists watchdog drivers, and modules-load.d honours that list; an explicit modprobe does not.
[Unit]
Description=Load Intel TCO hardware watchdog driver
DefaultDependencies=no
Before=sysinit.target
ConditionPathExists=!/dev/watchdog0

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/modprobe iTCO_wdt

[Install]
WantedBy=sysinit.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable watchdog-driver.service

# Tell systemd to use the watchdog: reset after 30 s without a ping; also guard a stuck reboot (10 min)
sudo mkdir -p /etc/systemd/system.conf.d
printf '[Manager]\nRuntimeWatchdogSec=30s\nRebootWatchdogSec=10min\n' | sudo tee /etc/systemd/system.conf.d/watchdog.conf
```

Reboot, then check:

```bash
journalctl -b | grep -i 'hardware watchdog'    # expected: "Using hardware watchdog /dev/watchdog0: 'iTCO_wdt'"
sudo wdctl                                      # Device /dev/watchdog0, Timeout: 30 seconds
```

If `/dev/watchdog0` never appears even after `sudo modprobe iTCO_wdt`, the watchdog may be disabled in the BIOS.

## 6. Reboot on kernel panic

By default, a kernel panic leaves the machine halted with an error on the (absent) screen. Reboot automatically
after 10 seconds instead:

```bash
printf 'kernel.panic = 10\n' | sudo tee /etc/sysctl.d/90-panic-reboot.conf
sudo sysctl --system           # apply now
sysctl kernel.panic            # expected: kernel.panic = 10
```

## 7. Never sleep

Ubuntu Server doesn't suspend on its own, but a sleeping smart home server is a broken one. Make it impossible:

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

## 8. Cap the journal size

```bash
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=1G\n' | sudo tee /etc/systemd/journald.conf.d/size.conf
sudo systemctl restart systemd-journald
```

The default cap is up to 4 GB. 1 GB holds months of logs for a home server and means fewer writes to the SSD.

## 9. SSD health (SMART)

```bash
sudo apt install -y smartmontools
sudo smartctl -H /dev/sda          # overall health: PASSED          (← REPLACE sda; NVMe: /dev/nvme0)
sudo smartctl -A /dev/sda          # attributes
```

Key attributes: `Reallocated_Sector_Ct` (should stay 0), `Wear_Leveling_Count` / `Percentage Used` (wear),
`Temperature_Celsius`, `UDMA_CRC_Error_Count` (cable/connection errors). The `smartd` daemon is enabled on install
and checks all disks periodically. Alerts from it are wired to Telegram in [08. Telegram bot](08-telegram-bot.md).

USB flash drives usually don't support SMART. The backup drive is checked actively instead
([07. Backups](07-backups.md#health-checks-for-backup-jobs)).

## 10. Firmware updates

```bash
sudo fwupdmgr refresh                # download the update catalogue (LVFS)
sudo fwupdmgr get-updates            # list available firmware updates
```

Small mini PC vendors rarely publish BIOS updates to LVFS, but SSD firmware and the **UEFI dbx** (the Secure Boot
revocation list) often show up. The dbx is only enforced **when Secure Boot is enabled**. Check with
`mokutil --sb-state`. With Secure Boot disabled (many mini PCs ship that way), a dbx update has no effect, so skip
it. With Secure Boot enabled, apply it (`sudo fwupdmgr update`, then reboot) while a display and keyboard are at
hand: if Secure Boot ever refuses to boot afterwards, recovery means disabling Secure Boot in the BIOS.

## 11. Tools

```bash
sudo apt install -y htop ncdu jq tmux git
```

| Tool | Use |
|------|-----|
| `htop` | processes, CPU and memory usage |
| `ncdu` | what is taking disk space |
| `jq` | read and filter JSON (APIs, Docker output) |
| `tmux` | terminal sessions that survive a dropped SSH connection |
| `git` | version control |

## Verify after a reboot

```bash
sudo systemctl reboot
```

Then:

```bash
timedatectl show -p Timezone --value                  # your timezone
sudo ufw status | head -1                             # Status: active
systemctl is-active fail2ban smartd                   # active, active
journalctl -b | grep -i 'hardware watchdog'           # watchdog in use
sysctl kernel.panic                                   # 10
systemctl is-enabled suspend.target                   # masked
systemctl --failed                                    # 0 loaded units listed
```
