# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, and others) working in this repository.

## Purpose

This repo is a reproducible guide and config set for a self-hosted smart home: Home Assistant in Docker
on Ubuntu Server, running on an x86 mini PC (reference: Beelink Mini S13, Intel N150, 16 GB RAM, 512 GB SSD).

Two audiences:
1. **The owner** — uses git history to track and roll back any config.
2. **Other people and their agents** — clone the repo and use it to set up their own smart home.

When a user asks you to help set up their system, follow the guides in `docs/` in numeric order and
adapt them to the user's hardware and devices. Ask which devices they own before configuring integrations.

## Hard rules

1. **No secrets, ever.** Never commit passwords, API tokens, Telegram bot tokens, chat IDs, cloud
   credentials, Wi-Fi passwords, real IP addresses, hostnames, MAC addresses, serial numbers or
   geolocation. Use placeholders (`<YOUR_BOT_TOKEN>`, `192.168.1.10`, `homeassistant.local`) and
   `*.example` files. Real values live only in git-ignored files (`.env`, `secrets.yaml`).
   Vendor or ISP **default** addresses that are the same for every customer (e.g. a router's factory
   admin IP) are fine to document.
   Before every commit, review the diff for anything that looks like a secret.
2. **No paths or names from the owner's machines.** Local paths (home directories, usernames, working
   folders, disk identifiers seen during a session) must never end up in the repo. Use generic examples
   instead: `~/Downloads`, `/opt/smart-home`, `/dev/diskN`, `/dev/sdX`, `<user>`. When you turn
   commands you ran into docs, rewrite them with variables or placeholders, and mark values the reader
   must replace (`# ← REPLACE`).
3. **No personal or presence data.** The repo is public and tied to a real person. Never commit anything that
   reveals where the owner lives or when the home is empty:
   - home coordinates, zones and addresses (e.g. `homeassistant: latitude/longitude`, `zone:` entries);
   - schedules and presence logic tied to real routines (when nobody is home, vacation mode dates, work hours);
   - names of household members, phone or person entities, notification targets, Telegram chat/user IDs;
   - floor plans or vacuum maps, room layouts beyond generic examples, camera names, streams or locations.
   Write automations and docs with generic examples instead (`zone.home`, "when everyone leaves", `<CHAT_ID>`).
4. **English only.** All files, comments, commit messages and docs are in English, even if the user
   talks to you in another language.
5. **Generic first, specific separately.**
   - `docs/` and `docs/devices/<class>.md` describe a *class* of devices or a general procedure.
   - Model-specific configs and notes go to `devices/<class>/<vendor-model>/` (e.g.
     `devices/vacuum/roborock-q7-max/`). A model may be mentioned in generic docs only as an example.
   - Never hard-code one user's specific devices into shared configs in `stack/`.
6. **Explain every command.** Each shell command in docs gets a short explanation of what it does and
   why. Mark commands that are destructive or need `sudo`.
7. **Backups are verified and monitored.** Every backup job follows
   [0002. Backup principles](docs/decisions/0002-backup-principles.md): a separate physical device, an
   integrity check after every run, a health check of the target (mounted, read/write test, free space,
   filesystem errors), and alerts on failure *and* on missing runs.
8. **Everything in Docker is monitored.** Every container gets cAdvisor metrics automatically. Every service with a
   metrics endpoint gets a scrape job in `stack/monitoring/scrape.yaml` in the same change
   ([0005. Monitoring](docs/decisions/0005-monitoring.md)).
9. **Host configs live in `configs/`.** When you change a non-obvious config file on the server, update its copy
   in `configs/` (with placeholders for machine-specific values) and the table in `configs/README.md`.
   **Exception:** never publish the live security settings (firewall exceptions, IPv6 policy, fail2ban thresholds,
   SSH authentication state). Document them as principles and options with example values that differ from the
   real ones ([configs/security.md](configs/security.md)). After changing any config on the server, run
   `scripts/backup-private-configs.sh <host>` so the owner's local, git-ignored `private-configs/` stays current.
10. **Configs are complete and copy-pasteable.** Every compose file and config referenced in docs exists
   in the repo. Pin image versions (no `latest`) so a commit fully describes a working state.

## Repository layout

```
docs/                       # numbered step-by-step guides
docs/devices/<class>.md     # generic guide per device class
docs/decisions/NNNN-*.md    # architecture decision records; read before proposing structural changes
stack/                      # docker-compose files, service configs, .env.example
configs/<component>/        # verified host config files (fail2ban, docker, netplan, ...), see configs/README.md
devices/<class>/<model>/    # model-specific examples: README.md + configs
scripts/                    # helper scripts (backups, maintenance)
private-configs/            # git-ignored, local only: live configs with real values (never commit)
```

## Adding a device

First check support and the integration's IoT class (prefer local) using the resources in
[docs/devices/README.md](docs/devices/README.md).

- **New class** (e.g. robot vacuum, Zigbee sensor, IP camera): create `docs/devices/<class>.md`
  covering what the class is, integration options (official, community via Marketplace/HACS, MQTT, ...), trade-offs, and a
  generic setup procedure.
- **New model**: create `devices/<class>/<vendor-model>/README.md` with the tested model, firmware or
  integration version, setup steps that differ from the generic guide, and example configs with
  placeholders. Link it from the class guide's "Examples" section.

## Git workflow

- Commit and push directly to `master`. **Do not create branches or pull requests** — this is a
  single-owner repo.
- Use Conventional Commits: `docs: ...`, `feat(stack): ...`, `fix(backup): ...`, `chore: ...`.
- One logical change per commit so any config can be found and rolled back via history.
- Never rewrite published history (no force push to `master`).

## Style

- Markdown, one H1 per file, short sections, numbered steps for procedures.
- Code blocks with language tags (`bash`, `yaml`).
- Use relative links between docs.
