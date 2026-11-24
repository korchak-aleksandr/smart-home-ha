# Security configs: principles only

Firewall, fail2ban and SSH settings are described here as principles, **not** as copies of the reference server's
live config. Publishing a real server's exact exceptions and thresholds tells an attacker where the gaps are and how
to stay under the limits. Pick your own values, and keep them out of public repos.

To keep a private backup of the live configs on your workstation, use
[`scripts/backup-private-configs.sh`](../scripts/backup-private-configs.sh). It copies them into a git-ignored
`private-configs/` folder with its own local git history.

## Firewall (ufw)

- Deny all incoming traffic by default, allow outgoing.
- Open only the ports of services you actually use, and only from private home networks (`192.168.0.0/16`,
  `10.0.0.0/8`, `172.16.0.0/12`), never "from anywhere" over IPv4.
- **IPv6** has no NAT, so a global address can be reachable from the internet. Choose one, and check the router
  ([04, firewall](../docs/04-base-setup.md#3-firewall-ufw)):
  - allow IPv6 only from link-local (`fe80::/10`) and your LAN prefix (strict; update the rule if the ISP changes
    the prefix), or
  - allow IPv6 more broadly, but **only after confirming** that the router blocks inbound IPv6 from the internet.
- Ports that usually need LAN access: SSH, the Home Assistant UI, Grafana, mDNS (UDP 5353), plus per-device needs (e.g. Tuya
  discovery broadcasts, UDP 6666–6667 and 7000).
- If you reach the server by `<hostname>.local`, allow **mDNS over IPv6 too**, not only from `fe80::/10`. Clients query
  from their global IPv6 addresses, and dropping those makes the name resolve only sometimes.
- Remember that Docker's published ports bypass ufw ([05](../docs/05-docker.md#5-docker-and-the-firewall)).

## fail2ban

- Enable the `sshd` jail with `backend = systemd` (Ubuntu logs SSH to the journal).
- Choose your own thresholds (attempts, time window, ban length). Mild values are fine for a LAN-only SSH, stricter
  ones if SSH could ever be reachable from outside.
- `ignoreip` only for the server itself (`127.0.0.1/8 ::1`).

## SSH authentication

- Key-based login always. Keep password login only as a deliberate fallback, and only while SSH isn't reachable
  from the internet. Prefer a second key (e.g. on another device) over a password.
- Never allow root login with a password (Ubuntu's default `PermitRootLogin prohibit-password` is fine).
