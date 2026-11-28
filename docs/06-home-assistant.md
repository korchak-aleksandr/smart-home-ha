# 06. Home Assistant

Run Home Assistant (Container installation method) with Docker Compose. The compose file lives in this repo at
[`stack/compose.yaml`](../stack/compose.yaml) and is deployed to `/opt/smart-home` on the server.

## Layout on the server

```
/opt/smart-home/
  compose.yaml               # copied from stack/compose.yaml in this repo
  .env                       # local values (TZ, later tokens); git-ignored, created from stack/.env.example
  homeassistant/config/      # all Home Assistant configuration and state; backed up, never committed
```

## 1. Prerequisites on the host

Home Assistant uses the host's Bluetooth stack (BlueZ) over D-Bus. Install it even if you have no Bluetooth
devices yet. Otherwise HA finds the adapter and fills its log with Bluetooth errors.

```bash
sudo apt install -y bluez                  # Bluetooth daemon (bluetoothd)
sudo systemctl enable --now bluetooth
bluetoothctl show | grep -E 'Controller|Powered'   # expected: a controller, Powered: yes
```

Open the web UI port in the firewall, for the LAN only:

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8123 proto tcp comment "Home Assistant UI from LAN"
```

If `homeserver.local` resolves to the server's IPv6 address, also allow port 8123 over IPv6. Pick the strict or broad
option from [04, IPv6](04-base-setup.md#ipv6).

## 2. Deploy

```bash
sudo install -d -o "$USER" -g "$USER" -m 755 /opt/smart-home   # stack directory, owned by you
```

Copy the stack files from your clone of this repo (run on your workstation):

```bash
rsync -a stack/compose.yaml stack/.env.example homeserver:/opt/smart-home/
```

On the server:

```bash
cd /opt/smart-home
cp -n .env.example .env              # first time only; then edit .env (TZ)
mkdir -p homeassistant/config
docker compose config --quiet        # validate compose.yaml and .env
docker compose pull                  # download the pinned image
docker compose up -d                 # start in the background
docker compose logs -f homeassistant # watch the startup (Ctrl+C to stop watching)
```

The first start takes a minute or two. Then open **`http://homeserver.local:8123`** (← REPLACE hostname).

## 3. The compose file explained

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:2026.11.2
    network_mode: host
    environment:
      TZ: ${TZ:?set TZ in .env}
    volumes:
      - ./homeassistant/config:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
    cap_add: [NET_ADMIN, NET_RAW]
    security_opt: [apparmor:unconfined]
    restart: unless-stopped
```

| Setting | Why |
|---------|-----|
| `image: …:2026.11.2` | **Pinned version**, the official image from GitHub Container Registry. Never `latest`: a commit must describe exactly what runs. |
| `network_mode: host` | Device discovery (mDNS/zeroconf, SSDP) and many local integrations need the host network. ufw applies to host-network containers, unlike published ports ([05](05-docker.md#5-docker-and-the-firewall)). |
| `TZ` | Timezone, from `.env`. `:?` makes compose fail loudly if it's missing. |
| `./homeassistant/config:/config` | All HA state: configuration, database, credentials. This is what gets backed up. |
| `/run/dbus:/run/dbus:ro` | Lets HA talk to the host's BlueZ for Bluetooth. |
| `cap_add: NET_ADMIN, NET_RAW` | Bluetooth adapter management (scanning, automatic recovery). Much narrower than `privileged: true`, which the upstream example uses. |
| `security_opt: apparmor:unconfined` | Ubuntu's default Docker AppArmor profile **blocks D-Bus**, so Bluetooth can't work under it. This disables AppArmor confinement for this one container. |
| `restart: unless-stopped` | Start at boot and after crashes. Only a manual `docker compose stop` keeps it down. |

### Bluetooth troubleshooting

The symptoms appear one after another as each layer is fixed:

| Log message | Cause | Fix |
|-------------|-------|-----|
| `AttributeError: 'NoneType' object has no attribute 'send'` / `Failed to force stop scanner` | No D-Bus connection to BlueZ | Install `bluez` on the host, mount `/run/dbus` |
| `Missing required permissions for Bluetooth management` | Capabilities missing | `cap_add: NET_ADMIN, NET_RAW` |
| Still `Failed to force stop scanner`, plus `apparmor="DENIED" operation="dbus_method_call"` in `journalctl -k` | AppArmor blocks D-Bus | `security_opt: apparmor:unconfined` |

## 4. First-time setup (onboarding)

In the browser at `http://homeserver.local:8123`:

1. **Create the owner account.** Use a strong, unique password and store it in a password manager. This account has
   full control of the house.
2. **Location, timezone, units.** Location is used for sun-based automations and weather. It's stored only on your
   server.
3. **Analytics:** optional, your choice.
4. HA lists devices it discovered on the network. You can add them now or later.

## 5. Mobile app

Install the official **Home Assistant** app (App Store / Google Play, by Nabu Casa). Always connect **by name**, not
by IP:

1. Join the home Wi-Fi with the phone.
2. Open the app. It usually finds the server on its own via mDNS. Otherwise, enter `http://homeserver.local:8123`
   (← REPLACE hostname).
3. **iOS:** allow **Local Network** access when asked. Without it, the app can't see the server. If you denied it,
   enable it under *Settings → Privacy & Security → Local Network → Home Assistant*.
4. Log in with your HA account.
5. In the app: **Settings → Companion App → (server) → Internal URL** = `http://homeserver.local:8123`, and add your
   home Wi-Fi name under **Home network / SSIDs**. The app then knows it's at home and uses the local name.

Optional during setup: **location** and **notifications**. Notifications are pushed via Apple/Google, so they also
arrive away from home. Location sends **GPS coordinates** to the server: they're stored in history and backups. For
home/away without coordinates, use [presence detection](devices/presence.md) and set the app's location access to
*Never*. The app has no access away from home
by design, see [0003](decisions/0003-remote-access-via-telegram-bot.md).

If the app says *"no connection"* while at home, the cause is almost always name resolution. See
[03, mDNS troubleshooting](03-ubuntu-install.md#mdns-troubleshooting).

## 6. Updating Home Assistant

Updates are deliberate: never automatic, always one commit.

1. Read the release notes, especially **Backward-incompatible changes**: <https://www.home-assistant.io/blog/>.
2. Back up `homeassistant/config` (see [07. Backups](07-backups.md)).
3. Change the image tag in `stack/compose.yaml`, commit.
4. Deploy and restart:
   ```bash
   rsync -a stack/compose.yaml homeserver:/opt/smart-home/        # on your workstation
   cd /opt/smart-home && docker compose pull && docker compose up -d   # on the server
   ```
5. **Rollback:** put the previous tag back (it's in git history) and run the same commands. If the new version
   migrated the database, restore the backup from step 2.

Find the current stable version: <https://github.com/home-assistant/core/releases/latest>.

## 7. Planned components

Home Assistant OS ships these as "apps" (add-ons). In a Container setup, each one is its own container in
`stack/compose.yaml`, or a component inside HA's config directory. They get added as devices arrive:

| Component | Purpose | In this setup |
|-----------|---------|---------------|
| **Marketplace** (formerly [HACS](https://hacs.xyz/)) | Community store for custom integrations and dashboard cards (catalog: `hacs/default`) | **Built into Home Assistant** (2026.11 has it) and enabled automatically: sidebar → *Marketplace*, or `/marketplace`. Don't install the old HACS custom integration: HA removes it at startup as legacy. |
| [Matter Server](https://github.com/home-assistant-libs/python-matter-server) | Matter devices (over Wi-Fi/Ethernet and over Thread) | Container with `network_mode: host` (Matter needs IPv6 on the LAN). **Matter over Thread** additionally needs a Thread border router: an OpenThread Border Router container plus a radio stick with Thread firmware. |
| [Zigbee2MQTT](https://www.zigbee2mqtt.io/) | Zigbee devices through a USB coordinator stick | `koenkk/zigbee2mqtt` container, stick passed in as `/dev/serial/by-id/…` |
| [Mushroom](https://github.com/piitaya/lovelace-mushroom) | Dashboard cards (via Marketplace) | Start with HA's built-in **Sections** view and **Tile** cards. They share Mushroom's design language. Add Mushroom cards where the built-in ones fall short (chips, template cards). |
| [Node-RED](https://nodered.org/) | Visual flow editor for complex automations | Optional, see [0004](decisions/0004-automations-in-home-assistant.md) |
| [MCP Server](https://www.home-assistant.io/integrations/mcp_server/) (built in) | Lets AI clients (Claude, ...) read states and control devices through Assist | Optional. If used: a dedicated **non-admin** HA user and token, and expose to Assist only the needed entities (not persons or trackers: their states go to the AI provider). It can't change configuration. Avoid community MCP add-ons with admin access: they change HA outside git. |

> One radio stick runs **either** Zigbee **or** Thread firmware, not both at once. Home Assistant deprecated the
> multiprotocol firmware. For Zigbee devices *and* Matter-over-Thread devices, plan for two sticks.

Check device support before buying: [docs/devices](devices/README.md).

## 8. HTTPS (later)

Let's Encrypt only issues certificates for **public domain names** it can verify. It can't issue them for `.local`
names or private IPs. Two options for a server that isn't reachable from the internet:

1. **Own domain + DNS-01 challenge.** Prove domain ownership with a DNS TXT record via your DNS provider's API (e.g.
   [lego](https://go-acme.github.io/lego/) with `--dns cloudflare`). The name (e.g. `ha.example.com`) points to the
   server's LAN address. No inbound ports, and every browser trusts the certificate.
2. **Local certificate authority** ([Caddy](https://caddyserver.com/docs/automatic-https#local-https) `tls internal`,
   or [step-ca](https://smallstep.com/docs/step-ca/)). Issues certificates for any name, including `homeserver.local`,
   but its root certificate must be installed once on every client device.

## 9. MQTT broker (Mosquitto)

[Mosquitto](https://mosquitto.org/) is the message bus for devices that talk MQTT: Wi-Fi devices with a "private
MQTT" option (e.g. [Qingping air monitors](../devices/air-quality/qingping-cgs2/README.md)), and Zigbee2MQTT later.
Devices publish to the broker, Home Assistant subscribes to it.

| File | Where | In git |
|------|-------|--------|
| `stack/mosquitto/config/mosquitto.conf` | `/opt/smart-home/mosquitto/config/` | yes: one plain-MQTT listener on 1883, no anonymous access, persistence, logs to `docker logs` |
| `stack/mosquitto/config/acl` | same | yes: which user may use which topics |
| `passwd` (hashed passwords) | same | **no**, created on the server |
| `credentials/<user>` (plaintext passwords, mode 600) | `/opt/smart-home/mosquitto/credentials/` | **no**. Kept because some devices store the password and can only be reconfigured by a factory reset. Backed up with the stack. |

**Users:** one per client type, each limited by the ACL: `homeassistant` (all topics), `qingping` (`qingping/#`
only). A device that leaks its password can then only publish its own data.

**No TLS:** plain MQTT is acceptable inside the home network, and some devices reject self-signed certificates. The
container runs on the host network, so ufw applies: port 1883 is open to the LAN only, never forward it on the router.

### Deploy

1. Copy the config, create a password per user and the password file (the commands print no passwords):
   ```bash
   rsync -a stack/compose.yaml homeserver:/opt/smart-home/
   rsync -a stack/mosquitto homeserver:/opt/smart-home/
   ssh homeserver 'cd /opt/smart-home && mkdir -p mosquitto/data mosquitto/credentials && chmod 700 mosquitto/credentials
     for u in homeassistant qingping; do [ -s mosquitto/credentials/$u ] || (umask 077; openssl rand -hex 16 > mosquitto/credentials/$u); done
     sudo touch mosquitto/config/passwd
     for u in homeassistant qingping; do
       docker run --rm -v "$PWD/mosquitto/config:/m" eclipse-mosquitto:2.0.23 mosquitto_passwd -b /m/passwd $u "$(cat mosquitto/credentials/$u)"
     done
     sudo chown -R 1883:1883 mosquitto/config mosquitto/data && sudo chmod 700 mosquitto/config/passwd mosquitto/config/acl'
   ```
   `openssl rand -hex 16` makes a random 32-character password. `mosquitto_passwd` stores only its hash. The
   container runs as user 1883 (`mosquitto`), which must own `passwd` and `acl`. Mosquitto warns about (and future
   versions refuse) files that others can read.
2. Open the port to the LAN and start the broker (`sudo`):
   ```bash
   ssh homeserver 'sudo ufw allow from 192.168.0.0/16 to any port 1883 proto tcp comment "MQTT (Mosquitto) from LAN"
     cd /opt/smart-home && docker compose up -d mosquitto && docker logs mosquitto'
   ```
   `chown: /mosquitto/config: Read-only file system` in the log is harmless: the image's entrypoint tries to take
   ownership of the read-only config mount.
3. Test: a message from `qingping` arrives, a topic outside its ACL is dropped, a wrong password is refused:
   ```bash
   ssh homeserver 'cd /opt/smart-home; HA=$(cat mosquitto/credentials/homeassistant); QP=$(cat mosquitto/credentials/qingping)
     docker exec mosquitto mosquitto_sub -h 127.0.0.1 -u homeassistant -P "$HA" -t "#" -v -W 4 &
     sleep 1
     docker exec mosquitto mosquitto_pub -h 127.0.0.1 -u qingping -P "$QP" -t qingping/TEST/up -m allowed
     docker exec mosquitto mosquitto_pub -h 127.0.0.1 -u qingping -P "$QP" -t other/topic -m dropped
     docker exec mosquitto mosquitto_pub -h 127.0.0.1 -u qingping -P wrong -t qingping/TEST/up -m refused; wait'
   ```
   Expected: only `qingping/TEST/up allowed` is printed, and the last command reports *not authorised*.

### Connect Home Assistant

*Settings → Devices & services → Add integration → MQTT*: broker `127.0.0.1`, port `1883`, username
`homeassistant`, and the password. Read it **in your own terminal**, don't paste it into chats or tickets:
`ssh homeserver cat /opt/smart-home/mosquitto/credentials/homeassistant`.

### Changes later

- **Config or ACL:** edit in git, copy with `sudo install -o 1883 -g 1883 -m 700` (ACL) or `-m 644` (config) into
  `mosquitto/config/`, then `docker compose restart mosquitto`. A plain `rsync` as your user would leave files the
  container can't read.
- **New client type** (e.g. Zigbee2MQTT): add a `user` block to `acl`, add the user to the password loop above, and
  restart the container.
- **Never change a password that a device has stored** (e.g. Qingping): that device then needs a factory reset.

## Useful commands

```bash
cd /opt/smart-home
docker compose ps                              # status
docker compose logs --tail 100 homeassistant   # recent logs
docker compose restart homeassistant           # restart HA
docker logs --tail 50 mosquitto               # MQTT broker: connections, auth errors
docker compose logs --since 10m homeassistant | grep -E 'ERROR|WARNING'   # recent problems
```
