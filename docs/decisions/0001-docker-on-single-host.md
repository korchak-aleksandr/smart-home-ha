# 0001. Docker on a single host instead of Proxmox / Home Assistant OS

- **Status:** accepted
- **Date:** 2026-11-22

## Context

A popular way to run Home Assistant on a mini PC is to install a hypervisor (Proxmox VE), run
Home Assistant OS (HAOS) in its own VM, and add separate VMs or containers for everything else.
This gives strong isolation, whole-VM snapshots and the Home Assistant add-on store.

The goals of this repository are different:

- every piece of configuration lives in git, so any state can be reviewed and rolled back;
- an AI agent working over SSH can read, change and deploy everything as plain text files;
- the setup is simple enough for a friend to reproduce on similar hardware.

The reference hardware (Intel N150, 16 GB RAM) runs any of these options comfortably, so resources
are not the deciding factor.

## Decision

Run **Ubuntu Server LTS directly on the hardware** with **Docker Compose**, and run every service as a
container on that single OS:

- Home Assistant uses the official **Home Assistant Container** installation method.
- Things that HAOS ships as add-ons (MQTT broker, Zigbee2MQTT, ESPHome, ...) are regular services in
  `stack/` compose files.
- Other workloads, such as automation agents, also run as containers on the same host
  (see [Other workloads](#other-workloads-on-the-same-host)).

No hypervisor layer is used.

## Consequences

### Benefits

- **Everything is text in git.** Compose files and configs define the system. Rolling back is
  `git checkout <commit>` plus `docker compose up -d`.
- **Agent-friendly.** No UI-only configuration steps for the infrastructure layer.
- **Officially supported.** Home Assistant supports two installation methods: Home Assistant OS and
  Home Assistant Container. (The "Supervised" and "Core" methods are deprecated and must not be used.)
- **Simpler hardware access.** USB devices (e.g. a Zigbee coordinator) are passed to a container with
  one `devices:` line instead of hypervisor USB passthrough.
- **Fewer moving parts.** One OS to update and monitor, no hypervisor overhead.

### Trade-offs and mitigations

| Trade-off | Mitigation |
|-----------|------------|
| No add-on store | Add-ons are containers anyway: run the same upstream images via compose. Guides that say "install the add-on" must be translated to a compose service. |
| No whole-system snapshot before upgrades | Pin every image to an explicit version (never `latest`), no unattended container auto-updates. Rollback = restore the previous tag from git. Back up data volumes before upgrades. |
| Single OS is a single point of failure | Keep the host minimal (Ubuntu + Docker + SSH), enable only automatic security updates. Disaster recovery = reinstall Ubuntu following `docs/`, deploy `stack/`, restore the latest backup. |
| Weaker isolation than separate VMs | Containers are sufficient for a home server, provided the guardrails below are followed. |

### Technical notes

- Home Assistant runs with `network_mode: host`; device discovery (mDNS, SSDP), HomeKit and
  Bluetooth require it.
- USB devices are referenced by stable paths: `/dev/serial/by-id/...`, never `/dev/ttyUSB0`.

## Other workloads on the same host

Additional containers (for example, AI agents such as Codex that run automations) share the host
with Home Assistant. A container is a sufficient sandbox only when these guardrails hold:

- **Never mount the Docker socket** (`/var/run/docker.sock`) and never use `privileged: true`.
  Either one gives the container root access to the whole host.
- **Mount only what is needed**, read-only where possible. Never mount the Home Assistant config
  directory or other services' data into an agent container.
- **Talk to Home Assistant through its API** with a token of a dedicated, **non-admin** Home Assistant
  user created for that agent, so its access can be revoked independently.
- **Set resource limits** (`mem_limit`, `cpus`) so a runaway job cannot starve Home Assistant.
- **Secrets via env files** that are git-ignored; commit only `.env.example`.

## Revisiting

If stronger isolation or whole-system snapshots become necessary, a VM (including HAOS) can be run on
the same Ubuntu host with KVM/libvirt without reinstalling the machine.
