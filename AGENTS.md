# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, and others) working in this repository.

## Purpose

This repo is a reproducible guide and config set for a self-hosted smart home: Home Assistant in Docker
on Ubuntu Server, running on an x86 mini PC (reference: Beelink Mini S13, Intel N150, 16 GB RAM, 500 GB SSD).

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
   Before every commit, review the diff for anything that looks like a secret.
2. **English only.** All files, comments, commit messages and docs are in English, even if the user
   talks to you in another language.
3. **Generic first, specific separately.**
   - `docs/` and `docs/devices/<class>.md` describe a *class* of devices or a general procedure.
   - Model-specific configs and notes go to `devices/<class>/<vendor-model>/` (e.g.
     `devices/vacuum/roborock-q7-max/`). A model may be mentioned in generic docs only as an example.
   - Never hard-code one user's specific devices into shared configs in `stack/`.
4. **Explain every command.** Each shell command in docs gets a short explanation of what it does and
   why. Mark commands that are destructive or need `sudo`.
5. **Configs are complete and copy-pasteable.** Every compose file and config referenced in docs exists
   in the repo. Pin image versions (no `latest`) so a commit fully describes a working state.

## Repository layout

```
docs/                       # numbered step-by-step guides
docs/devices/<class>.md     # generic guide per device class
stack/                      # docker-compose files, service configs, .env.example
devices/<class>/<model>/    # model-specific examples: README.md + configs
scripts/                    # helper scripts (backups, maintenance)
```

## Adding a device

- **New class** (e.g. robot vacuum, Zigbee sensor, IP camera): create `docs/devices/<class>.md`
  covering what the class is, integration options (official, HACS, MQTT, ...), trade-offs, and a
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
