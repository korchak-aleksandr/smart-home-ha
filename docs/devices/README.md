# Devices

Generic guides per device class live in this directory (`docs/devices/<class>.md`). Concrete, tested models live in
[`devices/<class>/<model>/`](../../devices/).

## Before buying or adding a device: check support

| Resource | Use it for |
|----------|-----------|
| [Home Assistant integrations](https://www.home-assistant.io/integrations/) | Every official integration: which brands and devices HA supports, how (local or cloud), and setup notes. Search by brand or model. |
| [Zigbee2MQTT supported devices](https://www.zigbee2mqtt.io/supported-devices/) | Zigbee devices officially supported by Zigbee2MQTT, with exposed features (sensors, switches, settings) and pairing instructions per model. |

## Prefer local control

Each HA integration page shows an **IoT class** that tells you how HA talks to the device:

| IoT class | Meaning | Verdict |
|-----------|---------|---------|
| **Local Push** | The device reports changes to HA instantly over the LAN | Best |
| **Local Polling** | HA asks the device over the LAN every few seconds | Good |
| **Cloud Push / Cloud Polling** | Everything goes through the vendor's cloud | Avoid if possible: it breaks when the internet or the vendor's cloud is down, adds latency, and depends on the vendor keeping the API |

Zigbee, Matter and Thread devices are local by design: they talk to the server's radio stick or the LAN, not to a
vendor cloud.

## Guides

- [Presence: who is home](presence.md) (iPhones, no location data)
- [Air quality monitors](air-quality.md)
- [Dehumidifiers](dehumidifier.md)
- [Robot vacuums](robot-vacuum.md)

## Adding a device to this repo

See [AGENTS.md → Adding a device](../../AGENTS.md#adding-a-device).
