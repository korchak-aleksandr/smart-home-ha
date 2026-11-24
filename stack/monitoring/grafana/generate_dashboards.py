"""Generate the custom Grafana dashboards (JSON) of this repo.

Edit this file, not the JSON:  python3 stack/monitoring/grafana/generate_dashboards.py
Output: stack/monitoring/grafana/dashboards/custom/*.json (committed, provisioned into Grafana).
"""
import json, os, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "dashboards", "custom")
OFFSET_W = "6"   # default wall-power offset: an Intel N150 mini PC idles at ~6 W at the wall, see docs/08-monitoring.md
DS = {"type": "prometheus", "uid": "victoriametrics"}
_id = [0]
def nid():
    _id[0] += 1; return _id[0]

def stat(title, expr, x, y, w=4, h=4, unit="none", decimals=None, thresholds=None, legend=None, color_mode="value", desc=None):
    p = {"id": nid(), "type": "stat", "title": title, "datasource": DS,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [{"refId": "A", "expr": expr, "instant": True, "legendFormat": legend or "__auto"}],
         "options": {"colorMode": color_mode, "graphMode": "none", "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "textMode": "value"},
         "fieldConfig": {"defaults": {"unit": unit, "thresholds": {"mode": "absolute", "steps": thresholds or [{"color": "green", "value": None}]}}, "overrides": []}}
    if decimals is not None: p["fieldConfig"]["defaults"]["decimals"] = decimals
    if desc: p["description"] = desc
    return p

def ts(title, targets, x, y, w=12, h=8, unit="none", stack=False, desc=None, decimals=None):
    p = {"id": nid(), "type": "timeseries", "title": title, "datasource": DS,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": l} for i, (e, l) in enumerate(targets)],
         "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True}, "tooltip": {"mode": "multi", "sort": "desc"}},
         "fieldConfig": {"defaults": {"unit": unit, "custom": {"lineWidth": 1, "fillOpacity": 15 if not stack else 40, "showPoints": "never", "stacking": {"mode": "normal" if stack else "none", "group": "A"}}}, "overrides": []}}
    if decimals is not None: p["fieldConfig"]["defaults"]["decimals"] = decimals
    if desc: p["description"] = desc
    return p

def row(title, y):
    return {"id": nid(), "type": "row", "title": title, "collapsed": False, "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}

def dashboard(uid, title, panels, templating=None, time_from="now-24h", desc=""):
    return {"uid": uid, "title": title, "description": desc, "tags": ["home-server"], "timezone": "browser", "editable": False,
            "schemaVersion": 41, "refresh": "1m", "time": {"from": time_from, "to": "now"},
            "templating": {"list": templating or []}, "panels": panels, "annotations": {"list": []}}

GREEN, ORANGE, RED = "green", "orange", "red"
def th(*steps):  # th(GREEN, (70, ORANGE), (90, RED))
    out = [{"color": steps[0], "value": None}]
    for v, c in steps[1:]: out.append({"color": c, "value": v})
    return out

POWER = "(sum(rate(node_rapl_package_joules_total[5m])) * $factor + $offset)"

# ---------------- Server overview ----------------
cpu = '100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval])))'
mem = '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)'
root = '100 * (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})'
backup = '100 * (1 - node_filesystem_avail_bytes{mountpoint="/mnt/backup"} / node_filesystem_size_bytes{mountpoint="/mnt/backup"})'
P = [row("Now", 0)]
y = 1
P += [stat("Uptime", "time() - node_boot_time_seconds", 0, y, unit="s", decimals=0),
      stat("CPU", cpu.replace("$__rate_interval", "5m"), 4, y, unit="percent", decimals=0, thresholds=th(GREEN, (70, ORANGE), (90, RED))),
      stat("Memory", mem, 8, y, unit="percent", decimals=0, thresholds=th(GREEN, (80, ORANGE), (90, RED))),
      stat("System disk", root, 12, y, unit="percent", decimals=0, thresholds=th(GREEN, (80, ORANGE), (90, RED))),
      stat("Backup drive", backup, 16, y, unit="percent", decimals=0, thresholds=th(GREEN, (80, ORANGE), (90, RED)), desc="Fill level of /mnt/backup. No value = drive not mounted."),
      stat("Containers", 'count(max by (name) (container_last_seen{name!=""} > time() - 60))', 20, y, decimals=0)]
y += 4
P += [stat("CPU temperature", 'max(node_hwmon_temp_celsius{chip=~"platform_coretemp.*"})', 0, y, unit="celsius", decimals=0, thresholds=th(GREEN, (75, ORANGE), (90, RED))),
      stat("SSD temperature", 'max(smartctl_device_temperature{temperature_type="current"})', 4, y, unit="celsius", decimals=0, thresholds=th(GREEN, (55, ORANGE), (65, RED))),
      stat("SSD health", "min(smartctl_device_smart_status)", 8, y, thresholds=th(RED, (1, GREEN)), color_mode="background",
           desc="SMART overall health self-assessment: 1 = PASSED."),
      stat("Wi-Fi signal", "max(node_wifi_station_signal_dbm)", 12, y, unit="dBm", decimals=0, thresholds=th(RED, (-75, ORANGE), (-65, GREEN))),
      stat("Power (estimate)", POWER, 16, y, unit="watt", decimals=1, desc="CPU package power from Intel RAPL × factor + offset (see the Energy & cost dashboard). Not a wall-socket measurement."),
      stat("Scrape targets up", 'sum(up) / count(up)', 20, y, unit="percentunit", decimals=0, thresholds=th(RED, (0.99, GREEN)), color_mode="background")]
y += 4
P.append(row("Backups", y)); y += 1
P += [stat("Last successful backup", "time() - max(smart_home_backup_last_success_timestamp_seconds)", 0, y, unit="s", decimals=0,
           thresholds=th(GREEN, (26 * 3600, RED)), color_mode="background",
           desc="Time since the last successful daily backup. Red after 26 h: the 03:00 run failed or didn't happen. Details: journalctl -u backup.service"),
      stat("Last run", "max(smart_home_backup_last_run_success)", 4, y, thresholds=th(RED, (1, GREEN)), color_mode="background",
           desc="1 = the last run succeeded. On failure, the failed step is in smart_home_backup_last_failed_step{step=...}."),
      stat("Archives on drive", "max(smart_home_backup_archives)", 8, y, decimals=0, thresholds=th(RED, (1, GREEN))),
      stat("Last archive size", "max(smart_home_backup_last_size_bytes)", 12, y, unit="bytes", decimals=1),
      stat("Weekly verification", "min(smart_home_backup_verify_success)", 16, y, thresholds=th(RED, (1, GREEN)), color_mode="background",
           desc="1 = every archive passed the checksum and zstd checks, read back from the drive."),
      stat("Last verification", "time() - max(smart_home_backup_verify_timestamp_seconds)", 20, y, unit="s", decimals=0,
           thresholds=th(GREEN, (8 * 86400, RED)))]
y += 4
P.append(row("Host", y)); y += 1
P += [ts("CPU usage", [(f'100 * sum by (mode) (rate(node_cpu_seconds_total{{mode!="idle"}}[$__rate_interval])) / scalar(count(node_cpu_seconds_total{{mode="idle"}}))', "{{mode}}")], 0, y, unit="percent", stack=True),
      ts("Memory", [("node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes", "used"), ("node_memory_Cached_bytes + node_memory_Buffers_bytes", "cache/buffers"), ("node_memory_MemTotal_bytes", "total")], 12, y, unit="bytes")]
y += 8
P += [ts("Temperatures", [('node_hwmon_temp_celsius{chip=~"platform_coretemp.*", sensor="temp1"}', "CPU package"), ('smartctl_device_temperature{temperature_type="current"}', "SSD"), ('node_hwmon_temp_celsius{chip="thermal_thermal_zone0", sensor="temp0"}', "ACPI")], 0, y, unit="celsius"),
      ts("Disk I/O", [('sum by (device) (rate(node_disk_read_bytes_total{device=~"sd[a-z]"}[$__rate_interval]))', "read {{device}}"), ('sum by (device) (rate(node_disk_written_bytes_total{device=~"sd[a-z]"}[$__rate_interval]))', "write {{device}}")], 12, y, unit="Bps")]
y += 8
P += [ts("Network", [('rate(node_network_receive_bytes_total{device=~"wl.*|en.*"}[$__rate_interval])', "in {{device}}"), ('rate(node_network_transmit_bytes_total{device=~"wl.*|en.*"}[$__rate_interval])', "out {{device}}")], 0, y, unit="Bps"),
      ts("Wi-Fi", [("node_wifi_station_signal_dbm", "signal (dBm)"), ("node_wifi_station_transmit_bits_per_second / 1e6", "tx bitrate (Mbit/s)"), ("node_wifi_station_receive_bits_per_second / 1e6", "rx bitrate (Mbit/s)")], 12, y,
         desc="Signal: -30 excellent, -67 good for streaming, below -75 unreliable.")]
y += 8
P.append(row("Containers", y)); y += 1
P += [ts("CPU by container", [('sum by (container) (rate(container_cpu_usage_seconds_total{container!=""}[$__rate_interval]))', "{{container}}")], 0, y, unit="percentunit", stack=True),
      ts("Memory by container", [('sum by (container) (container_memory_working_set_bytes{container!=""})', "{{container}}")], 12, y, unit="bytes", stack=True)]
y += 8
json.dump(dashboard("server-overview", "Server overview", P, desc="One screen: host health, temperatures, Wi-Fi, containers.",
                    templating=[{"name": "factor", "type": "constant", "query": "1.3", "hide": 2}, {"name": "offset", "type": "constant", "query": OFFSET_W, "hide": 2}]),
          open(f"{OUT}/server-overview.json", "w"), indent=1)

# ---------------- Energy & cost ----------------
_id[0] = 0
tv = [
 {"name": "price", "label": "Price, €/kWh", "type": "textbox", "query": "0.337", "current": {"text": "0.337", "value": "0.337"},
  "description": "Marginal electricity price incl. VAT (Cyprus EAC tariff 01 example: generation + network + fuel adjustment + PSO, ×1.05 VAT, + RES fund). Update when the fuel adjustment changes."},
 {"name": "factor", "label": "RAPL factor", "type": "textbox", "query": "1.3", "current": {"text": "1.3", "value": "1.3"},
  "description": "Wall power ≈ CPU package power (RAPL) × factor + offset. RAPL covers the CPU package only."},
 {"name": "offset", "label": "Offset, W", "type": "textbox", "query": OFFSET_W, "current": {"text": OFFSET_W, "value": OFFSET_W},
  "description": "Constant watts added for SSD, Wi-Fi, PSU losses. Calibrate with a wall power meter if you have one."},
]
KWH_RANGE = "(sum(increase(node_rapl_package_joules_total[$__range])) * $factor / 3.6e6 + $offset * $__range_s / 3600 / 1000)"
AVG7D_W = "(sum(rate(node_rapl_package_joules_total[7d])) * $factor + $offset)"
E = [row("Now", 0)]
y = 1
E += [stat("Power now", POWER, 0, y, w=6, unit="watt", decimals=1),
      stat("Energy in selected range", KWH_RANGE, 6, y, w=6, unit="kwatth", decimals=3),
      stat("Cost in selected range", f"{KWH_RANGE} * $price", 12, y, w=6, unit="currencyEUR", decimals=2),
      stat("Projected cost per year", f"{AVG7D_W} * 8760 / 1000 * $price", 18, y, w=6, unit="currencyEUR", decimals=0,
           desc="Average power of the last 7 days (or since monitoring started) × 8760 h × price.")]
y += 4
E += [stat("Projected per month", f"{AVG7D_W} * 730 / 1000 * $price", 0, y, w=6, unit="currencyEUR", decimals=2),
      stat("Projected kWh per year", f"{AVG7D_W} * 8760 / 1000", 6, y, w=6, unit="kwatth", decimals=0),
      stat("CPU package (raw RAPL)", "sum(rate(node_rapl_package_joules_total[5m]))", 12, y, w=6, unit="watt", decimals=2),
      stat("Price used", "$price", 18, y, w=6, unit="currencyEUR", decimals=3)]
y += 4
E.append(row("History", y)); y += 1
E += [ts("Power (estimate)", [(POWER, "estimated wall power"), ("sum(rate(node_rapl_package_joules_total[5m]))", "CPU package (RAPL)"), ("sum(rate(node_rapl_core_joules_total[5m]))", "CPU cores (RAPL)")], 0, y, w=24, unit="watt", decimals=1)]
y += 8
E += [{"id": nid(), "type": "barchart", "title": "Cost per day", "datasource": DS, "gridPos": {"x": 0, "y": y, "w": 24, "h": 8},
       "targets": [{"refId": "A", "expr": "(sum(increase(node_rapl_package_joules_total[1d])) * $factor / 3.6e6 + $offset * 24 / 1000) * $price", "legendFormat": "€ per day", "interval": "1d", "range": True}],
       "options": {"xTickLabelRotation": -45, "showValue": "auto", "legend": {"showLegend": False}},
       "fieldConfig": {"defaults": {"unit": "currencyEUR", "decimals": 2}, "overrides": []}}]
json.dump(dashboard("energy-cost", "Energy & cost", E, templating=tv, time_from="now-7d",
                    desc="Estimated electricity use and cost of the server, from Intel RAPL. Edit price/factor/offset in the variables."),
          open(f"{OUT}/energy-cost.json", "w"), indent=1)
# ---------------- Home Assistant ----------------
_id[0] = 0
H = [row("Health", 0)]
y = 1
H += [stat("Home Assistant", 'max(up{job="homeassistant"})', 0, y, thresholds=th(RED, (1, GREEN)), color_mode="background",
           desc="1 = metrics endpoint answers (HA is running)."),
      stat("Unavailable entities", 'count(hass_entity_available == 0) or vector(0)', 4, y, decimals=0,
           thresholds=th(GREEN, (1, ORANGE), (5, RED)), color_mode="background",
           desc="Exported entities that HA reports as unavailable (hass_entity_available = 0): a device or integration is down."),
      stat("Updates available", 'sum(hass_update_state)', 8, y, decimals=0, thresholds=th(GREEN, (1, ORANGE)), color_mode="background",
           desc="Pending updates of HA core and integrations (update.* entities)."),
      stat("HA uptime", 'time() - max(process_start_time_seconds{job="homeassistant"})', 12, y, unit="s", decimals=0),
      stat("HA memory", 'max(process_resident_memory_bytes{job="homeassistant"})', 16, y, unit="bytes", decimals=0),
      stat("HA CPU", 'sum(rate(container_cpu_usage_seconds_total{container="homeassistant"}[5m]))', 20, y, unit="percentunit", decimals=1)]
y += 4
H += [ts("Entity availability", [('hass_entity_available', "{{friendly_name}}")], 0, y, unit="none", decimals=0,
         desc="1 = available, 0 = unavailable (per exported entity)."),
      ts("HA process", [('rate(process_cpu_seconds_total{job="homeassistant"}[$__rate_interval])', "CPU (cores)"), ('process_resident_memory_bytes{job="homeassistant"} / 1e9', "memory (GB)")], 12, y)]
y += 8
H.append(row("Home", y)); y += 1
H += [ts("Temperature", [("hass_sensor_temperature_celsius", "{{friendly_name}}")], 0, y, unit="celsius", decimals=1),
      ts("Humidity", [("hass_sensor_humidity_percent", "{{friendly_name}}"), ("hass_humidifier_target_humidity_percent", "{{friendly_name}} target")], 12, y, unit="percent", decimals=0)]
y += 8
H += [ts("Batteries", [("hass_sensor_battery_percent", "{{friendly_name}}")], 0, y, unit="percent", decimals=0),
      ts("Dehumidifiers on/off", [("hass_humidifier_state", "{{friendly_name}}")], 12, y, decimals=0)]
y += 8
json.dump(dashboard("home-assistant", "Home Assistant", H, desc="HA health (unavailable entities, updates, resources) and allow-listed home sensors."),
          open(f"{OUT}/home-assistant.json", "w"), indent=1)
print("ok")
