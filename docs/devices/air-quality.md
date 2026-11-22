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

## Examples

- [Qingping Air Monitor 2 (CGS2)](../../devices/air-quality/qingping-cgs2/README.md): Wi-Fi, private MQTT
