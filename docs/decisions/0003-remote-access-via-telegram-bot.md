# 0003. Remote access through a Telegram bot

- **Status:** accepted
- **Date:** 2026-11-22

## Context

When away from home, the owner wants to:

- read the overall status of the house (are things on, temperatures, alerts);
- run a **small number of predefined scenarios**, e.g. "heat the water before I arrive".

The full Home Assistant UI is **not** needed remotely.

Constraints:

- No public ("white") IPv4 address, and no wish to pay the ISP for one. No port forwarding on the router.
- Inbound connections from the internet are blocked by the router (IPv4: NAT, IPv6: the router's firewall),
  and should stay that way ([04. Base server setup](../04-base-setup.md#3-firewall-ufw)).
- No extra apps or "connect first" steps on the phone.

Options considered:

| Option | Verdict |
|--------|---------|
| **Telegram bot** | ✅ chosen |
| Tailscale / WireGuard VPN | Fallback, see below |
| Nabu Casa (Home Assistant Cloud) | Works with zero setup, but it's a paid subscription for the full UI, which isn't needed |
| Exposing Home Assistant directly (port forwarding, or opening inbound IPv6 on the router) | Rejected: puts the HA login page on the public internet |

## Decision

Remote access goes through a **Telegram bot** that runs on the server.

- The bot connects **outbound** to Telegram's API (long polling) and receives commands over that connection. It needs
  no public IP, no open ports, and no firewall changes.
- It exposes only what was deliberately implemented: a status summary and a short list of scenario commands
  (buttons). It doesn't proxy the full Home Assistant UI.
- The same bot delivers **alerts** (backup failures, disk health, device problems), so it's one component for both
  jobs.
- Only whitelisted Telegram user IDs may use it. The bot token and user IDs live in a git-ignored `.env`, never in
  this repository.

## Consequences

- Each remote action must be implemented as a bot command or scenario. That's a feature: the remote attack surface
  is a handful of known commands instead of a full admin UI.
- The bot depends on Telegram being reachable from the server. If Telegram is down, remote control and alerts are
  unavailable until it's back. Local control at home is unaffected.
- Telegram stores the messages. Don't send secrets through the bot.

## Fallback: Tailscale VPN

If full remote access to the Home Assistant UI is ever needed, [Tailscale](https://tailscale.com/) (a WireGuard-based
VPN) works without a public IP or port forwarding. The server and the phone both connect outbound to Tailscale's
coordination servers and then talk to each other directly. The Home Assistant app then works remotely as if at home,
and no ports are opened to the internet. Trade-offs: an extra service on the server, the Tailscale app on the phone,
and a third-party coordination service. Not set up in this repository.
