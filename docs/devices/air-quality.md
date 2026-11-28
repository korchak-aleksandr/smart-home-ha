# Air quality monitors

Sensors for temperature, humidity, CO₂, particulate matter (PM2.5/PM10), volatile organic compounds (VOC) and
sometimes noise. They're useful on their own (dashboards, history) and as triggers for automations, e.g. run the
dehumidifier above a humidity threshold, or alert on high CO₂.

## Integration options

| Connection | Typical integration | Notes |
|------------|---------------------|-------|
| Bluetooth (BLE) | Brand integration via HA's Bluetooth (e.g. [Qingping](https://www.home-assistant.io/integrations/qingping) for BLE models) | Local and passive. Needs a Bluetooth adapter in range of the sensor. |
| Zigbee | [Zigbee2MQTT](https://www.zigbee2mqtt.io/supported-devices/) | Local. Check the model in the supported devices list. |
| Wi-Fi + MQTT | MQTT integration, sometimes with a community (Marketplace) integration for discovery | Local if the device can send to your own broker |
| Wi-Fi + vendor cloud | Brand cloud integration | Avoid if a local option exists |

## What to look for

- **CO₂ via an NDIR sensor** (not "eCO₂" estimated from VOC), if CO₂ matters to you.
- A local data path: BLE, Zigbee, Matter, or MQTT to your own broker.
- Mains power or a battery that doesn't need frequent charging.

## Indoor air quality index

One number 1–4 for the home page, with the same colored circles as the
[outdoor index](outdoor-conditions.md) (1 green, 2 yellow, 3 orange, 4 red). Config:
[`stack/ha-packages/indoor_air.yaml`](../../stack/ha-packages/indoor_air.yaml), a template sensor
`sensor.indoor_air_quality_index`.

**Method.** There's no official indoor index, so it follows the method of the
[European Air Quality Index](https://airindex.eea.europa.eu/) and the Cyprus national index: a sub-index per
pollutant, and the overall index is the **worst** sub-index, never an average. One bad value isn't cancelled out by
good ones.

| Pollutant | 1 low | 2 moderate | 3 high | 4 very high | Source of the bounds |
|-----------|-------|------------|--------|-------------|----------------------|
| PM2.5, μg/m³ | < 25 | 25–50 | 50–100 | ≥ 100 | Cyprus national scale (same as the outdoor station, so both indexes compare) |
| PM10, μg/m³ | < 50 | 50–100 | 100–200 | ≥ 200 | same |
| CO₂, ppm | < 1000 | 1000–1500 | 1500–2000 | ≥ 2000 | German Environment Agency (UBA) guidance on indoor CO₂: below 1000 harmless, above 2000 unacceptable; 1500 splits the range in between |
| VOC index | < 150 | 150–250 | 250–400 | ≥ 400 | Sensirion VOC index (used by many monitors): 100 = the room's usual level of the last day. Lenient bounds: it's relative, and cooking or cleaning raises it briefly |

Noise and humidity aren't part of it: they're comfort, not pollution.

**How it works.**
- It finds its inputs by device class (`pm25`, `pm10`, `carbon_dioxide`) and by name (`*voc*`), so it has no
  entity IDs in it and picks up new monitors by itself. With several monitors, the worst room counts.
- Outdoor sensors are skipped by their object ID prefix `outdoor_`: keep that prefix for anything measured outside.
- It updates once a minute. The attribute `worst` names the pollutants that set the index (entity → *Attributes*).
- It's not exported to the metrics on purpose: Grafana shows the raw readings ([decision](../08-monitoring.md#3-home-assistant-metrics)).
- The package file name must be a slug: `indoor_air.yaml`, not `indoor-air.yaml` (HA refuses the package).

**Home page.** Favorites (home page → *Edit* → *Favorites*), in this order: the indoor index, CO₂, temperature and
humidity of the monitor in the main room, then the outdoor index, UV and sea. Rename the entities to short names in
your language (e.g. "CO₂"): the tiles also show the area. Since 2026.x, Home Assistant always puts the **device
name** in front of the entity name, even of a name you set yourself, so also give the device a short name (e.g.
"Air" → "Air CO₂"). Renaming doesn't change entity IDs, so the index, metrics and favorites keep working. CO₂ colors (same bounds as the index) are in Grafana →
*Home Assistant* → *Indoor air*.

## Examples

- [Qingping Air Monitor 2 (CGS2)](../../devices/air-quality/qingping-cgs2/README.md): Wi-Fi, private MQTT to your own Mosquitto ✅
