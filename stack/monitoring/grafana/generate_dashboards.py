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

def ts(title, targets, x, y, w=12, h=8, unit="none", stack=False, desc=None, decimals=None, soft_min=0, soft_max=None):
    # Axes start at 0 by default: auto-scaled axes make tiny changes (23 -> 24 C) look like cliffs.
    # soft_min/soft_max only widen the axis; values outside still show (e.g. negative dBm).
    p = {"id": nid(), "type": "timeseries", "title": title, "datasource": DS,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": l} for i, (e, l) in enumerate(targets)],
         "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True}, "tooltip": {"mode": "multi", "sort": "desc"}},
         "fieldConfig": {"defaults": {"unit": unit, "custom": {"lineWidth": 1, "fillOpacity": 15 if not stack else 40, "showPoints": "never", "stacking": {"mode": "normal" if stack else "none", "group": "A"}}}, "overrides": []}}
    custom = p["fieldConfig"]["defaults"]["custom"]
    if soft_min is not None: custom["axisSoftMin"] = soft_min
    if soft_max is not None: custom["axisSoftMax"] = soft_max
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
P += [ts("CPU usage", [(f'100 * sum by (mode) (rate(node_cpu_seconds_total{{mode!="idle"}}[$__rate_interval])) / scalar(count(node_cpu_seconds_total{{mode="idle"}}))', "{{mode}}")], 0, y, unit="percent", stack=True, soft_max=100),
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
         desc="1 = available, 0 = unavailable (per exported entity).", soft_max=1),
      ts("HA process", [('rate(process_cpu_seconds_total{job="homeassistant"}[$__rate_interval])', "CPU (cores)"), ('process_resident_memory_bytes{job="homeassistant"} / 1e9', "memory (GB)")], 12, y)]
y += 8
H.append(row("Home", y)); y += 1
H += [ts("Temperature", [('hass_sensor_temperature_celsius{entity!~"sensor.outdoor_.*"}', "{{friendly_name}}")], 0, y, unit="celsius", decimals=1),
      ts("Humidity", [("hass_sensor_humidity_percent", "{{friendly_name}}"), ("hass_humidifier_target_humidity_percent", "{{friendly_name}} target")], 12, y, unit="percent", decimals=0, soft_max=100)]
y += 8
H += [ts("Batteries", [("hass_sensor_battery_percent", "{{friendly_name}}")], 0, y, unit="percent", decimals=0, soft_max=100),
      ts("Dehumidifiers on/off", [("hass_humidifier_state", "{{friendly_name}}")], 12, y, decimals=0, soft_max=1)]
y += 8
H.append(row("Indoor air", y)); y += 1
# Indoor air monitors (e.g. Qingping CGS2 over private MQTT). Metric names follow HA's device class and unit.
CO2 = "hass_sensor_carbon_dioxide_ppm"
CO2_TH = th(GREEN, (1000, "yellow"), (1500, ORANGE), (2000, RED))   # same bounds as the indoor index (stack/ha-packages/indoor_air.yaml)
NOT_OUT = 'entity!~"sensor.outdoor_.*"'
H += [stat("CO₂ now", CO2, 0, y, w=6, unit="ppm", decimals=0, thresholds=CO2_TH, color_mode="background", legend="{{friendly_name}}",
           desc="Below 1000 ppm fine, 1000-1500 ventilate, 1500-2000 stuffy, from 2000 bad (German Environment Agency: above 2000 unacceptable)."),
      stat("PM2.5 indoors now", f"hass_sensor_pm25_u0xb5g_per_mu0xb3{{{NOT_OUT}}}", 6, y, w=6, unit="conµgm3", decimals=0,
           thresholds=th(GREEN, (15, "yellow"), (25, ORANGE), (50, RED)), color_mode="background", legend="{{friendly_name}}",
           desc="WHO 24-hour guideline: 15 μg/m³."),
      stat("Noise now", "hass_sensor_sound_pressure_db", 12, y, w=6, unit="dB", decimals=0, legend="{{friendly_name}}"),
      stat("Monitor data age", f"time() - max by (friendly_name) ({{__name__=\"hass_last_updated_time_seconds\", entity=~\"sensor.*_co2\"}})",
           18, y, w=6, unit="s", decimals=0, thresholds=th(GREEN, (900, ORANGE), (3600, RED)), legend="{{friendly_name}}",
           desc="Time since the CO₂ value last changed. The monitor reports every few minutes; long gaps mean it lost Wi-Fi or the MQTT broker.")]
y += 4
H += [ts("CO₂", [(CO2, "{{friendly_name}}")], 0, y, unit="ppm", decimals=0, desc="Below 1000 ppm fine, 1000-1500 ventilate, 1500-2000 stuffy, from 2000 bad."),
      ts("Particles indoors", [(f"hass_sensor_pm25_u0xb5g_per_mu0xb3{{{NOT_OUT}}}", "{{friendly_name}}"),
                               (f"hass_sensor_pm10_u0xb5g_per_mu0xb3{{{NOT_OUT}}}", "{{friendly_name}}")], 12, y, unit="conµgm3", decimals=0)]
y += 8
H += [ts("VOC index", [('hass_sensor_aqi_None{entity=~"sensor.*etvoc"}', "{{friendly_name}}")], 0, y, decimals=0,
         desc="Sensirion VOC index: 100 = the room's usual level, above 100 worse than usual, up to 500."),
      ts("Noise", [("hass_sensor_sound_pressure_db", "{{friendly_name}}")], 12, y, unit="dB", decimals=0)]
y += 8
H.append(row("Outdoor", y)); y += 1
# Sensors from stack/ha-packages/outdoor.yaml: the nearest official air-quality station + Open-Meteo models.
def out(metric, entity): return f'{metric}{{entity="sensor.outdoor_{entity}"}}'
UG = "hass_sensor_unit_u0xb5g_per_mu0xb3"   # sensors in μg/m³ without a device class
aqi = stat("Air quality index", out("hass_sensor_state", "air_quality_index"), 0, y, decimals=0, color_mode="background",
           thresholds=th(GREEN, (2, "yellow"), (3, ORANGE), (4, RED)),
           desc="Index of the nearest official station: 1 low, 2 moderate, 3 high, 4 very high.")
aqi["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {str(k): {"text": f"{k} {v}"} for k, v in
                                               {1: "low", 2: "moderate", 3: "high", 4: "very high"}.items()}}]
UV_TH = th(GREEN, (3, "yellow"), (6, ORANGE), (8, RED), (11, "purple"))
H += [aqi,
      stat("UV index now", out("hass_sensor_state", "uv_index"), 4, y, decimals=1, thresholds=UV_TH, color_mode="background"),
      stat("UV index max today", out("hass_sensor_state", "uv_index_max_today"), 8, y, decimals=1, thresholds=UV_TH, color_mode="background"),
      stat("Saharan dust", out(UG, "saharan_dust"), 12, y, unit="conµgm3", decimals=0, thresholds=th(GREEN, (50, ORANGE), (100, RED)),
           desc="Open-Meteo model (CAMS). Dust events push PM10 up across the island."),
      stat("Sea temperature", out("hass_sensor_temperature_celsius", "sea_temperature"), 16, y, unit="celsius", decimals=1),
      stat("Station data age", f'time() - {out("hass_last_updated_time_seconds", "pm10")}', 20, y, unit="s", decimals=0,
           thresholds=th(GREEN, (3 * 3600, ORANGE), (6 * 3600, RED)),
           desc="Time since the station values last changed. The station reports hourly; hours without changes mean the station or the page is down.")]
y += 4
H += [ts("Particles (station) and Saharan dust (model)", [(out("hass_sensor_pm10_u0xb5g_per_mu0xb3", "pm10"), "PM10"),
                                                          (out("hass_sensor_pm25_u0xb5g_per_mu0xb3", "pm2_5"), "PM2.5"),
                                                          (out(UG, "saharan_dust"), "Saharan dust")], 0, y, unit="conµgm3", decimals=1,
         desc="Official limits (1 low / 2 moderate / 3 high / 4 very high): PM10 50/100/200, PM2.5 25/50/100 μg/m³."),
      ts("Gases (station)", [(out("hass_sensor_ozone_u0xb5g_per_mu0xb3", "ozone"), "O₃"),
                             (out("hass_sensor_nitrogen_dioxide_u0xb5g_per_mu0xb3", "no2"), "NO₂"),
                             (out("hass_sensor_nitrogen_monoxide_u0xb5g_per_mu0xb3", "no"), "NO"),
                             (out(UG, "nox"), "NOx"),
                             (out("hass_sensor_sulphur_dioxide_u0xb5g_per_mu0xb3", "so2"), "SO₂"),
                             (out(UG, "benzene"), "Benzene")], 12, y, unit="conµgm3", decimals=1,
         desc="CO is on its own panel: its values are ~10x higher.")]
y += 8
H += [ts("UV index", [(out("hass_sensor_state", "uv_index"), "now"), (out("hass_sensor_state", "uv_index_max_today"), "max today")], 0, y, decimals=1),
      ts("Sea temperature", [(out("hass_sensor_temperature_celsius", "sea_temperature"), "sea surface")], 8, y, w=8, unit="celsius", decimals=1),
      ts("CO (station)", [(out("hass_sensor_carbon_monoxide_u0xb5g_per_mu0xb3", "co"), "CO")], 16, y, w=8, unit="conµgm3", decimals=0)]
H[-3]["gridPos"]["w"] = 8
y += 8
json.dump(dashboard("home-assistant", "Home Assistant", H, desc="HA health (unavailable entities, updates, resources), allow-listed home sensors, indoor and outdoor air."),
          open(f"{OUT}/home-assistant.json", "w"), indent=1)
print("ok")
