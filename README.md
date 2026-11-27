# smart-home-ha

A self-hosted smart home built on **Home Assistant** running on a small x86 mini PC.

This repository is a reproducible, step-by-step guide plus all the configs needed to go from a bare
mini PC to a working smart home: BIOS setup, OS install, Docker stack, Home Assistant, backups,
a Telegram bot for control and alerts, and device integrations.

It is written so that **you can hand it to an AI coding agent** (Claude Code, Codex, etc.) and let the
agent walk you through the setup on your own hardware. Agent instructions live in [AGENTS.md](AGENTS.md).

## Reference hardware

| Component | Value |
|-----------|-------|
| Mini PC   | Beelink Mini S13 |
| CPU       | Intel N150 (4C/4T, up to 3.6 GHz) |
| RAM       | 16 GB DDR4 |
| Storage   | 512 GB SSD |

Any comparable x86-64 mini PC (Intel N100/N150/N200, etc.) should work with minor BIOS differences.

## Stack

- **OS:** Ubuntu Server LTS
- **Runtime:** Docker + Docker Compose
- **Core:** Home Assistant (container)
- **Backups:** verified, health-checked and alerting backups to a separate drive, off-site later ([principles](docs/decisions/0002-backup-principles.md))
- **Control & alerts:** Telegram bot, also the way to control the house remotely, without a public IP or open ports ([why](docs/decisions/0003-remote-access-via-telegram-bot.md))
- **Devices:** integrations grouped by device class (vacuums, Zigbee, cameras, climate, ...)

Everything runs as Docker containers on a single Ubuntu host — no Proxmox, no Home Assistant OS VM.
See [why](docs/decisions/0001-docker-on-single-host.md). Automations are built in Home Assistant itself, as
YAML in git ([why](docs/decisions/0004-automations-in-home-assistant.md)).

Before buying a device, check support: [docs/devices](docs/devices/README.md).

## Repository layout

```
docs/                       # step-by-step guides, read in order
  01-hardware-bios.md       # BIOS: auto power-on after power loss, boot order
  02-install-media.md       # download, verify and write the Ubuntu Server USB stick
  03-ubuntu-install.md      # OS install, SSH, mDNS, network
  04-base-setup.md          # timezone, updates, firewall, fail2ban, watchdog, SSD health
  05-docker.md              # Docker and Compose
  06-home-assistant.md      # Home Assistant deployment
  07-backups.md             # backup jobs and restore procedure
  08-monitoring.md          # VictoriaMetrics + Grafana: host, disks, Wi-Fi, containers, HA, energy cost
  09-telegram-bot.md        # Telegram bot for control and alerts
  devices/                  # device support resources, generic guide per device class
  decisions/                # architecture decision records (why things are done this way)
stack/                      # docker-compose files, service configs, .env.example
  ha-packages/              # Home Assistant config as packages (metrics, outdoor sensors)
  ha-dashboards/            # Home Assistant YAML dashboards (details pages)
  ha-www/                   # static files served by HA under /local/ (icons)
configs/                    # verified host config files by component (fail2ban, docker, netplan, ...)
devices/<class>/<model>/    # concrete, model-specific examples (e.g. vacuum/roborock-q7-max)
scripts/                    # helper scripts (backups, maintenance)
```

Generic guides describe a **class** of devices. Concrete models live separately under `devices/` as
examples — add your own model next to them without touching the generic docs.

## Roadmap

- [x] [BIOS: power on after power loss, boot from USB](docs/01-hardware-bios.md)
- [x] [Installation media: Ubuntu Server USB stick](docs/02-install-media.md)
- [x] [Ubuntu Server install, SSH, mDNS, Wi-Fi](docs/03-ubuntu-install.md)
- [x] [Base server setup: updates, firewall, fail2ban, watchdog, SSD health](docs/04-base-setup.md)
- [x] [Docker and Compose](docs/05-docker.md)
- [x] [Home Assistant container](docs/06-home-assistant.md)
- [x] [Monitoring: VictoriaMetrics, Grafana, exporters, energy cost estimate](docs/08-monitoring.md)
- [x] [Backups: daily verified archives on the backup drive, 7 days, metrics](docs/07-backups.md)
- [ ] Wi-Fi devices: [robot vacuum](docs/devices/robot-vacuum.md) ✅, [dehumidifier](docs/devices/dehumidifier.md) ✅, [air quality monitor](docs/devices/air-quality.md) (planned)
- [x] [Presence (who is home) without location data](docs/devices/presence.md)
- [x] [Outdoor conditions: official air-quality station, UV, Saharan dust, sea temperature](docs/devices/outdoor-conditions.md)
- [ ] Matter, Zigbee (radio stick, Matter Server, Mosquitto, Zigbee2MQTT)
- [ ] Dashboards (built-in Sections + Mushroom)
- [ ] Telegram bot: control, alerts, remote scenarios
- [ ] Device classes and model examples

## Using this repo with an AI agent

1. Clone the repository.
2. Open it with your agent (Claude Code, Codex, or any agent that reads `AGENTS.md`).
3. Ask it to guide you, e.g. *"Walk me through setting up this smart home on my mini PC, starting from the BIOS."*
4. Tell the agent which devices you own — it will use the generic class guides and the model examples
   in `devices/` to configure them.

## Secrets

**No secrets are stored in this repository.** All tokens, passwords, IPs and hostnames are placeholders.
Real values go into local files that are ignored by git (`.env`, `secrets.yaml`). Copy `*.example`
files and fill them in locally.

## License

[MIT](LICENSE)
