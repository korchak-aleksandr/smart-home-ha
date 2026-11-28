# Qingping Air Monitor 2 (CGS2)

Wi-Fi air quality monitor with a touch screen. It's also sold as "Qingping Air Detector 2", and the
[qingping_cgs1](https://github.com/mash2k3/qingping_cgs1) integration calls it "Air Monitor Pro 2". The model code
is **CGS2** (on the label and in the app). The Qingping developer portal lists it as **Qingping Air Monitor**.

**Status:** ✅ works locally over private MQTT. Tested with firmware `4.5.6_0167`, qingping_cgs1 `v1.3.1`, Home
Assistant 2026.11.

Measures temperature, humidity, CO₂ (NDIR), PM2.5, PM10, eTVOC (VOC index) and noise. Battery-backed.

## Integration options

| Option | Verdict |
|--------|---------|
| Official HA [Qingping](https://www.home-assistant.io/integrations/qingping) integration | ❌ Bluetooth models only, and CGS2 isn't supported |
| **Private MQTT + [qingping_cgs1](https://github.com/mash2k3/qingping_cgs1) (community, via Marketplace)** | ✅ chosen: local, real-time, CGS2 explicitly supported |
| De-cloud via ADB ([cgs2_decloud](https://github.com/ea/cgs2_decloud)) | Not needed: it modifies the device's Android system |

With **private MQTT**, the device sends its readings straight to your own MQTT broker on the LAN instead of
Qingping's cloud. The cloud is used once, to push the broker settings to the device.

## Prerequisites

1. **A fixed server IP.** The device stores the broker's IP address (it can't resolve `.local` names). If the
   server's IP changes, the device loses the broker, and changing its settings requires a **factory reset**.
   Reserve the server's IP on the router ([03, DHCP reservation](../../../docs/03-ubuntu-install.md#fallback-reserve-the-ip-address-on-the-router)).
   The device's own IP doesn't need a reservation: it connects to the broker, and HA identifies it by MAC.
2. **Mosquitto** with a dedicated `qingping` user limited to `qingping/#`, port 1883 open to the LAN, and HA's
   **MQTT** integration connected to it: [06, MQTT broker](../../../docs/06-home-assistant.md#9-mqtt-broker-mosquitto).
3. The device paired in the **Qingping+** app, with the **latest firmware** (app → device → ⚙ → firmware update).
   Update before switching: whether updates still arrive in private mode isn't documented. The firmware version and
   the Wi-Fi MAC are on the device: *Settings → About*.
4. A login at [developer.qingping.co](https://developer.qingping.co) with the **same account** as the app. If you
   signed up in the app with Google or Apple, first link an email in the app, then log in on the site with an email
   code.

## Setup

1. **Install the integration:** HA → *Marketplace* → search **Qingping** (by mash2k3) → download. If it isn't
   found: ⋮ → *Add by link* → `https://github.com/mash2k3/qingping_cgs1`, type *Integration*. Don't configure it
   yet: it finds devices only while they send data.
2. **Check the account:** developer portal → *Private Configuration* → tab **Unsent**: your device is listed with
   its MAC. (Older guides mention a separate *Device* page; the 2026 portal has these tabs instead.)
3. **Add Configuration:** a name, *Device Model* **Qingping Air Monitor**, *Private Type* **Self-built MQTT** →
   *Network configuration* → **Edit**:

   | Field | Value |
   |-------|-------|
   | MQTT Type | **MQTT** (not MQTTS: the device rejects self-signed certificates) |
   | Host / Port | the server's fixed IP / `1883` |
   | User Name / Password | `qingping` / its password (read it in your own terminal, see 06) |
   | Client ID | `qingping-{mac}` |
   | Up Topic | `qingping/{mac}/up` |
   | Down Topic | `qingping/{mac}/down` |

   Type `{mac}` literally: the portal substitutes each device's MAC. The integration expects exactly these values.
   **Test** fails, and that's expected: the cloud can't reach a LAN address. Leave *Custom Config* empty. Check the
   password before saving: password managers like to autofill these fields. **Confirm** twice: this only saves the
   configuration on the portal.
4. **Push it:** tab **Unsent** → select the device → send the configuration. ⚠️ From now on, changing the broker
   settings needs a **factory reset** of the device.
5. **Restart the device** (long press on the power button → restart): it applies the configuration on reboot. The
   broker log shows it: `docker logs mosquitto` → `New client connected ... as qingping-<MAC> (... u'qingping')`.
6. **Make it send data now.** Until the integration is set up, the device reports rarely, and the integration only
   discovers devices that are sending. Ask for real-time reports (every 15 s for 30 min), the same command the
   integration sends later:
   ```bash
   ssh homeserver 'cd /opt/smart-home; P=$(cat mosquitto/credentials/homeassistant)
     docker exec mosquitto mosquitto_pub -h 127.0.0.1 -u homeassistant -P "$P" \
       -t qingping/<MAC>/down -m "{\"type\":\"12\",\"up_itvl\":\"15\",\"duration\":\"1800\"}"'
   ```
   `<MAC>` is the MAC without colons, as on the portal (`AABBCCDDEEFF`). The readings arrive on
   `qingping/<MAC>/up` as JSON.
7. **Add the device in HA:** *Settings → Devices & services → Add integration →* **Qingping** with the purple
   "qingping +" icon and the Marketplace badge (not the built-in Bluetooth one). The device appears in the list →
   model **CGS2**, a name, an area. The device doesn't show up under *Discovered*: discovery runs only inside this
   dialog. If it isn't found, add it manually with the MAC (no colons) while data is flowing.

After that, the integration keeps the device in real-time mode itself and updates every 5 minutes
(`number.<name>_update_interval`).

## What you get

| Entity | Notes |
|--------|-------|
| CO₂ (ppm), PM2.5, PM10 (μg/m³), temperature, humidity, noise (dB), eTVOC (VOC index, 100 = the room's usual level) | Main sensors |
| Battery, charging state, status (online/offline after 5 min without data), firmware, MAC | Diagnostic |
| Offsets per sensor, update interval, eTVOC unit | Configuration |

The [indoor air quality index](../../../docs/devices/air-quality.md#indoor-air-quality-index) picks up its
CO₂, PM and VOC readings automatically.

Metrics: the allow-list in `stack/ha-packages/monitoring.yaml` covers CO₂, particles, VOC, noise, temperature,
humidity and battery. Grafana → **Home Assistant** → row **Indoor air**, including **monitor data age**.

## Gotchas

- Changing the broker settings later requires a **factory reset** of the device. See
  [moving to a new network](../../../docs/03-ubuntu-install.md#moving-to-a-new-network) to avoid it.
- Plain MQTT (no TLS) on port 1883: acceptable inside the home network. Keep the port closed to anything but the LAN.
- HA logs a warning that qingping_cgs1 doesn't specify `mean_type` for its statistics ("will stop working in
  2026.11"). On 2026.11.2 it still works. Check the integration after HA updates.
- The Qingping+ app **keeps showing the readings** after switching to private MQTT.

Guides: [CGS2 step by step (Homey forum)](https://community.homey.app/t/qingping-air-monitor-2-local-integration-through-mqtt/160916),
[enabling MQTT (qingping_cgs1)](https://github.com/mash2k3/qingping_cgs1/blob/main/enableMQTT.md),
[HA forum thread](https://community.home-assistant.io/t/qingping-air-quality-monitor-2-getting-it-to-work-on-mqtt/1013826).
