# 0005. Monitoring: VictoriaMetrics + Grafana, everything in Docker is scraped

- **Status:** accepted
- **Date:** 2026-11-24

## Context

The server runs unattended. Problems (a full disk, a hot or worn-out SSD, a container eating memory, a flaky Wi-Fi
link, an integration that went unavailable) should be visible before they cause an outage. The owner also wants an
estimate of the server's electricity cost.

## Decision

- **Storage and scraping:** single-node [VictoriaMetrics](https://docs.victoriametrics.com/). It scrapes targets
  itself (Prometheus-compatible config), so no separate Prometheus or vmagent is needed. Retention is **1 year**.
  It's light on RAM and disk.
- **Dashboards:** [Grafana](https://grafana.com/), **anonymous read-only access inside the home network**. Viewers may
  use Explore. Changes need the admin login.
- **Exporters:** node_exporter (host, Wi-Fi, temperatures, RAPL energy), smartctl_exporter (SSD), cAdvisor
  (containers), plus the `/metrics` endpoints of the services themselves (VictoriaMetrics, Grafana, Home Assistant).
- **Home Assistant:** an **allow-list** of entities only (health, updates, batteries, climate). Everything else stays
  in HA's own history and isn't duplicated.
- **Energy cost** is an **estimate** from Intel RAPL (CPU package power) × factor + offset × price, adjustable in
  Grafana. No smart plug.
- **Alerts** come later, together with the Telegram bot.

### Rule: everything in Docker is monitored

Every service in `stack/compose.yaml` must be covered:

1. **Container metrics** (CPU, memory, network, disk I/O, restarts) come automatically from cAdvisor for every
   container. Nothing to do, but check that the new container shows up in the *Server overview* dashboard.
2. **Service metrics:** if the service exposes a metrics endpoint (or has a standard exporter), add a scrape job to
   `stack/monitoring/scrape.yaml` in the same change that adds the service.
3. A new service without both is **incomplete**.

### Exposure

All exporters and VictoriaMetrics listen on `127.0.0.1` only (host network, no published ports, so the firewall rules
stay meaningful). Only Grafana is reachable from the LAN.

**cAdvisor reads the Docker socket** (read-only mount of `/var/run`) to name containers. Docker socket access is
effectively root. That's acceptable for this one trusted, widely used infrastructure exporter. Application and agent
containers must never get it ([0001](0001-docker-on-single-host.md#other-workloads-on-the-same-host)).

## Consequences

- Six more containers. Together they use a few hundred MB of RAM and about 1–2 GB of disk per year.
- Community dashboards are downloaded from grafana.com at pinned revisions and not committed (third-party content).
  Custom dashboards are committed as JSON.
