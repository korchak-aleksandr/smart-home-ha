# Qingping Air Monitor 2 (CGS2)

Wi-Fi air quality monitor with a touch screen. It's also sold as "Qingping Air Detector 2", and the
[qingping_cgs1](https://github.com/mash2k3/qingping_cgs1) integration calls it "Air Monitor Pro 2". The model code
is **CGS2** (on the label and in the app).

**Status:** ⏳ planned, not tested yet.

Measures temperature, humidity, CO₂, PM2.5, PM10, eTVOC and noise. Battery-backed.

## Integration options

| Option | Verdict |
|--------|---------|
| Official HA [Qingping](https://www.home-assistant.io/integrations/qingping) integration | ❌ Bluetooth models only, and CGS2 isn't supported |
| **Private MQTT + [qingping_cgs1](https://github.com/mash2k3/qingping_cgs1) (community, via Marketplace)** | ✅ chosen: local, real-time, CGS2 explicitly supported |
| De-cloud via ADB ([cgs2_decloud](https://github.com/ea/cgs2_decloud)) | Not needed: it modifies the device's Android system |

With **private MQTT**, the device sends its readings straight to your own MQTT broker on the LAN instead of
Qingping's cloud. The cloud is used once, to push the broker settings to the device.

## Prerequisites

1. **A fixed server IP.** The device stores the broker's IP address. It usually can't resolve `.local` names. If the
   server's IP changes, the device loses the broker, and changing its settings requires a **factory reset**.
   Reserve the server's IP on the router ([03, DHCP reservation](../../../docs/03-ubuntu-install.md#fallback-reserve-the-ip-address-on-the-router)).
2. **Mosquitto** MQTT broker in the stack: `network_mode: host` so ufw applies, port 1883 open to the LAN only,
   username/password auth. Planned in [06, components](../../../docs/06-home-assistant.md#6-planned-components).
3. Home Assistant **MQTT** integration connected to Mosquitto.
4. The [qingping_cgs1](https://github.com/mash2k3/qingping_cgs1) integration, installed from HA's built-in **Marketplace** (formerly HACS).
5. The device paired in the **Qingping+ / Qingping Home** app, with the **latest firmware**. The CGS1 guide requires
   at least `4.1.8`. The minimum for CGS2 isn't documented, so just update. One user reported that the app only
   found the device with the region set to **China**.

## Plan

1. Deploy Mosquitto, connect HA's MQTT integration, install `qingping_cgs1` from the Marketplace.
2. Log in at [developer.qingping.co](https://developer.qingping.co) with the Qingping app account.
3. **Private Configuration** (or *Private Access Config*) → **Add** MQTT configuration:
   - device type: *Qingping Air Monitor*, private type: **Self-built MQTT**;
   - protocol **MQTT** (not MQTTS: the device rejects self-signed certificates), host = the server's fixed IP,
     port **1883**, the MQTT username and password.
4. **Push Configuration** → select the device → Confirm.
5. On the device: **Settings → (bottom) Privatization / Private Cloud** → check the connection, *Refresh Connection*.
6. In HA: **Add Integration → Qingping**. The integration listens on `qingping/#` and discovers the device.

Guides: [CGS2 step by step (Homey forum)](https://community.homey.app/t/qingping-air-monitor-2-local-integration-through-mqtt/160916),
[enabling MQTT (qingping_cgs1)](https://github.com/mash2k3/qingping_cgs1/blob/main/enableMQTT.md),
[HA forum thread](https://community.home-assistant.io/t/qingping-air-quality-monitor-2-getting-it-to-work-on-mqtt/1013826).

## Gotchas

- Changing the broker settings later requires a **factory reset** of the device. See
  [moving to a new network](../../../docs/03-ubuntu-install.md#moving-to-a-new-network) to avoid it.
- Plain MQTT (no TLS) on port 1883: acceptable inside the home network. Keep the port closed to anything but the LAN.
- Whether the Qingping app keeps showing data after switching to private MQTT isn't documented. Note the result here
  after testing.
