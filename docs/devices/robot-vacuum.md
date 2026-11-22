# Robot vacuums

## Integration options

| Brand / ecosystem | Integration | IoT class |
|-------------------|-------------|-----------|
| Roborock (Roborock app) | Official [Roborock](https://www.home-assistant.io/integrations/roborock) | Local Polling (cloud only for login and keys) |
| Xiaomi / Roborock in the Mi Home app | Official [Xiaomi Miio](https://www.home-assistant.io/integrations/xiaomi_miio) (device token required) | Local Polling |
| Others | Search [HA integrations](https://www.home-assistant.io/integrations/) for the brand | varies |

## What you get

State and battery, start/stop/return to dock, suction and mop modes, cleaning of specific rooms, consumables
(filter, brushes) and often the map. Typical automations: clean when everyone has left the house, notify when
a consumable needs replacing or the bin is full.

## Examples

- [Roborock Q7 Max](../../devices/vacuum/roborock-q7-max/README.md): official Roborock integration, local
