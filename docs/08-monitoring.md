# 08. Monitoring

Host, disk, Wi-Fi, container and Home Assistant metrics in **VictoriaMetrics**, dashboards in **Grafana**. Why and
the rules: [0005. Monitoring](decisions/0005-monitoring.md).

```
 node_exporter      ─┐  host: CPU, memory, disks, filesystems, network, Wi-Fi, temperatures, RAPL energy
 smartctl_exporter  ─┤  SSD health (SMART)
 cAdvisor           ─┤  every container: CPU, memory, network, disk I/O
 HA /api/prometheus ─┤  allow-listed HA entities (health, updates, batteries, climate)
 VM, Grafana        ─┤  their own /metrics
                     ▼
        VictoriaMetrics (scrapes every 30 s, keeps 1 year)  ── 127.0.0.1:8428
                     ▼
        Grafana  ── http://homeserver.local:3000  (LAN, view without login)
```

| Service | Image | Listens on |
|---------|-------|-----------|
| VictoriaMetrics | `victoriametrics/victoria-metrics` | `127.0.0.1:8428` |
| node_exporter | `prom/node-exporter` | `127.0.0.1:9100` |
| smartctl_exporter | `prometheuscommunity/smartctl-exporter` | `127.0.0.1:9633` |
| cAdvisor | `ghcr.io/google/cadvisor` | `127.0.0.1:8081` |
| Grafana | `grafana/grafana` | `0.0.0.0:3000` (LAN via ufw) |

All services use the host network. Exporters bind to localhost, so nothing but Grafana is reachable from other
machines. Versions are pinned in [`stack/compose.yaml`](../stack/compose.yaml).

## Files

```
stack/compose.yaml                              # services (monitoring section)
stack/monitoring/scrape.yaml                    # what VictoriaMetrics scrapes
stack/monitoring/grafana/provisioning/          # datasource + dashboard providers (as code)
stack/monitoring/grafana/generate_dashboards.py # generates our dashboards: edit this, not the JSON
stack/monitoring/grafana/dashboards/custom/     # our dashboards (generated JSON, committed)
stack/monitoring/grafana/dashboards/community/  # grafana.com dashboards (downloaded, git-ignored)
stack/ha-packages/monitoring.yaml               # HA: Prometheus export allow-list + "unavailable entities" sensor
scripts/fetch-grafana-dashboards.sh             # downloads community dashboards at pinned revisions
```

## 1. Prepare the server

```bash
cd /opt/smart-home
mkdir -p victoriametrics grafana secrets && chmod 700 secrets
sudo chown 472:472 grafana                               # Grafana runs as uid 472 in its container
sudo install -d -m 755 /var/lib/node_exporter/textfile    # custom metrics (backup status, ...) as *.prom files

# Grafana admin password, stored only in .env (mode 600, git-ignored)
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-28)" >> .env
chmod 600 .env

# Grafana from the LAN (and over IPv6 if names resolve to IPv6, see 04-base-setup.md#ipv6)
sudo ufw allow from 192.168.0.0/16 to any port 3000 proto tcp comment "Grafana from LAN"
```

To read the admin password later, run on the server in your own terminal (not in an AI chat):
`grep GRAFANA_ADMIN_PASSWORD /opt/smart-home/.env`. The variable is only used on Grafana's **first** start. To change
the password later, use Grafana's UI, or reset it:
`docker exec grafana grafana cli admin reset-admin-password '<new password>'`.

## 2. Deploy

From your workstation:

```bash
rsync -a stack/compose.yaml stack/.env.example stack/monitoring homeserver:/opt/smart-home/
ssh homeserver 'cd /opt/smart-home && docker compose up -d'
ssh homeserver 'bash -s' < scripts/fetch-grafana-dashboards.sh      # community dashboards
```

Check that every target is up:

```bash
ssh homeserver "curl -s 127.0.0.1:8428/api/v1/targets | python3 -c \"import sys,json; [print(t['labels']['job'], t['health'], t.get('lastError','')) for t in json.load(sys.stdin)['data']['activeTargets']]\""
```

VictoriaMetrics re-reads `scrape.yaml` every 30 seconds, and Grafana re-reads dashboards every 30 seconds. Neither
needs a restart after `rsync`.

## 3. Home Assistant metrics

1. Enable packages in `homeassistant/config/configuration.yaml`, once:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Install the package and restart HA:
   ```bash
   scp stack/ha-packages/monitoring.yaml homeserver:/tmp/ && ssh homeserver \
     'sudo install -D -m 644 /tmp/monitoring.yaml /opt/smart-home/homeassistant/config/packages/monitoring.yaml && cd /opt/smart-home && docker compose restart homeassistant'
   ```
   It enables HA's [Prometheus integration](https://www.home-assistant.io/integrations/prometheus/) with an
   **allow-list**: updates, batteries, humidity/temperature sensors, dehumidifiers, vacuums, outdoor sensors
   ([outdoor conditions](devices/outdoor-conditions.md)). Only what HA exports
   natively goes to Grafana: entity states and availability (`hass_entity_available`), plus HA's process metrics.
   Nothing is computed or added on the HA side. Everything else (e.g. attributes that aren't exported) is viewed in HA
   itself.
3. Create a token for VictoriaMetrics: HA → your profile → **Security → Long-lived access tokens → Create**, name it
   `victoriametrics`. Save it on the server **without pasting it anywhere else** (it asks for the token, hidden):
   ```bash
   ssh -t homeserver 'read -rsp "HA token: " T; echo; umask 077; printf "%s" "$T" > /opt/smart-home/secrets/ha-prometheus-token'
   ```
4. Add the scrape job (it's already in `scrape.yaml` if you deploy from this repo):
   ```yaml
   - job_name: homeassistant
     metrics_path: /api/prometheus
     authorization:
       credentials_file: /etc/secrets/ha-prometheus-token
     static_configs:
       - targets: ["127.0.0.1:8123"]
   ```

## 4. Dashboards

| Folder | Dashboard | Source |
|--------|-----------|--------|
| Home server | **Server overview** (home page): now-values, host, temperatures, Wi-Fi, containers | this repo |
| Home server | **Energy & cost**: power, kWh and € for the selected range, projections per month and year | this repo |
| Home server | **Home Assistant**: HA up, unavailable exported entities, pending updates, HA CPU/memory, temperature, humidity, batteries; **Outdoor**: air-quality index, UV, dust, sea, pollutants, station data age | this repo |
| Community | Node Exporter Full (1860) | grafana.com, pinned revision |
| Community | Docker monitoring (15798) | grafana.com, pinned revision |
| Community | SMARTctl Exporter Dashboard (22604) | grafana.com, pinned revision |
| Community | VictoriaMetrics single-node (10229) | grafana.com, pinned revision |

Any metric can be explored ad hoc in **Explore** (left menu), even without logging in.

### Energy and cost estimate

The server can't measure its wall-socket power. Intel **RAPL** reports the energy of the **CPU package** only (no SSD,
Wi-Fi, PSU losses). The dashboard computes:

```
power ≈ RAPL package power × factor + offset          (variables "RAPL factor", "Offset, W")
cost  = energy (kWh) × price                          (variable "Price, €/kWh")
```

Set the variables at the top of the dashboard. On an Intel N-series mini PC, the CPU package idles at **~0.5 W**
(measured on the reference server) while the whole box draws several watts at the wall, so `factor` alone
underestimates about tenfold. The default **offset is 6 W**: the near-identical Beelink EQ14 (same N150) was
[measured at ~6.2 W idle at the wall](https://minipclab.com/blog/mini-pc-power-consumption-guide). Calibrate it with a
plug-in power meter if you have one. With the defaults (factor 1.3, offset 6 W, €0.337/kWh), the reference server comes
out at roughly **6.7 W, ~60 kWh and ~€20 per year**.

**Price** = the *marginal* price per kWh from your bill (the server doesn't change fixed charges). Example for Cyprus
EAC tariff 01 (Domestic): generation €0.1789 + network €0.0393 + fuel adjustment (changes every bill, e.g. €0.0973)
+ PSO €0.00051, × 1.05 VAT, + RES fund €0.005 ≈ **€0.337/kWh**.

## 5. Gotchas found during setup

| Symptom | Cause | Fix |
|---------|-------|-----|
| No `node_rapl_*` metrics, although the RAPL collector reports success | Docker masks `/sys/devices/virtual/powercap` inside containers (Platypus side-channel mitigation) | `--path.sysfs=/host/sys` (host's sysfs via the `/:/host` mount). RAPL files are root-only, so run node_exporter as `user: root` |
| `scrape.yaml` changes never apply | Single-file bind mount: `rsync` replaces the file, and the container keeps seeing the old inode | Mount the **directory** (`./monitoring:/etc/monitoring:ro`) |
| VictoriaMetrics restarts: `flag provided but not defined` | Wrong flag name | It's `-promscrape.configCheckInterval` |
| Docker dashboard shows no containers | cAdvisor labels are `name` and `container_label_com_docker_compose_service` | `metric_relabel_configs` copies them to `container` and `service` |
| `node_scrape_collector_success == 0` for zfs, nfs, nvme, ... | Hardware/features the server doesn't have | Disable those collectors (`--no-collector.<name>`) |
