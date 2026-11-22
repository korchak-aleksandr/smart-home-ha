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
| Storage   | 500 GB SSD |

Any comparable x86-64 mini PC (Intel N100/N150/N200, etc.) should work with minor BIOS differences.

## Stack

- **OS:** Ubuntu Server LTS
- **Runtime:** Docker + Docker Compose
- **Core:** Home Assistant (container)
- **Backups:** scheduled local + off-site backups of configs and data
- **Control & alerts:** Telegram bot
- **Devices:** integrations grouped by device class (vacuums, Zigbee, cameras, climate, ...)

## Repository layout

```
docs/                       # step-by-step guides, read in order
  01-hardware-bios.md       # BIOS: auto power-on after power loss, boot order
  02-ubuntu-install.md      # OS install and base hardening
  03-docker.md              # Docker and Compose
  04-home-assistant.md      # Home Assistant deployment
  05-backups.md             # backup jobs and restore procedure
  06-telegram-bot.md        # Telegram bot for control and alerts
  devices/<class>.md        # generic guide per device class
stack/                      # docker-compose files, service configs, .env.example
devices/<class>/<model>/    # concrete, model-specific examples (e.g. vacuum/roborock-q7-max)
scripts/                    # helper scripts (backups, maintenance)
```

Generic guides describe a **class** of devices. Concrete models live separately under `devices/` as
examples — add your own model next to them without touching the generic docs.

## Roadmap

- [ ] BIOS: restore power on AC loss, boot settings
- [ ] Ubuntu Server install and base setup
- [ ] Docker and Compose
- [ ] Home Assistant container
- [ ] Backups and restore
- [ ] Telegram bot: control and alerts
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
