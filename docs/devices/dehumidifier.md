# Dehumidifiers

## Integration options

| Ecosystem | Integration | IoT class |
|-----------|-------------|-----------|
| Tuya / Smart Life (most white-label models) | [Tuya Local](https://github.com/make-all/tuya-local) (community, via Marketplace "Add by link") | Local Push |
| Tuya / Smart Life | Official [Tuya](https://www.home-assistant.io/integrations/tuya) | Cloud Push: avoid if Tuya Local works |
| Others | Search [HA integrations](https://www.home-assistant.io/integrations/) for the brand | varies |

## Tuya Local tips

- Open **UDP 6666–6667 and 7000** from the LAN in the firewall, otherwise device discovery fails
  ([04, firewall](../04-base-setup.md#3-firewall-ufw)).
- Tuya Local auto-picks a device description by matching data points. With white-label devices it can pick a
  similar but wrong one (e.g. temperature in °F instead of °C). Compare the entities with the device's display, and
  if something is off, re-add the device and choose another description on the **device type** screen. That screen
  comes after the connection details, and it only lists descriptions whose data points fit the device.
- After switching descriptions, Home Assistant may keep the old **display unit** of an entity (e.g. °F). Fix it in
  the entity settings → *Unit of measurement*.
- Long-pressing buttons on Tuya devices can **reset Wi-Fi**. The device then gets a new local key and must be
  re-added in Tuya Local.
- Reserve the device's IP on the router.

## What you get

Power, target humidity, current humidity, mode, fan speed, tank full, timer, child lock, often temperature and filter
status. Typical automations: run when humidity rises above a threshold (from the device's own sensor or an air quality
monitor), notify when the tank is full.

## Examples

- [LIFE Tuya Wi-Fi Dehumidifier 20L](../../devices/dehumidifier/life-tuya-20l/README.md): Tuya Local, local (`eberg_rico_r12e2` description)
