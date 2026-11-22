# LIFE Tuya Wi-Fi Dehumidifier 20L

20-litre dehumidifier sold under the LIFE brand (Greece/Cyprus retail), controlled through the **Smart Life / Tuya**
app. It's a white-label Tuya device. Its data points match the Sygonix Smarter dehumidifier (see below).

**Status:** ✅ works locally (on/off, target humidity, current humidity, mode, fan speed, tank, timer, child lock).
⏳ The device description (type) needs to be switched, see [Plan](#plan-switch-to-the-matching-device-description).

## Integration

[Tuya Local](https://github.com/make-all/tuya-local), fully local (protocol **3.4**). It isn't in the default
Marketplace catalog: add it via **Marketplace → Add by link** → `https://github.com/make-all/tuya-local`, type
*Integration*, then download it. The official Tuya integration is cloud-based (Cloud Push), so it's not used.

1. **Firewall:** Tuya devices announce themselves with UDP broadcasts. Without these rules, Tuya Local reports
   *"The Tuya cloud does not provide local IP addresses"* and can't find the device:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 6666:6667 proto udp comment 'Tuya local discovery broadcasts'
   sudo ufw allow from 192.168.0.0/16 to any port 7000 proto udp comment 'Tuya local discovery broadcasts (protocol 3.5)'
   ```
2. **Add integration → Tuya Local → "Set up device using the SmartLife cloud"**.
3. Enter the **User code** from the Smart Life app (*Me → ⚙ → Account and Security → User Code*), then scan the QR
   code with the app and confirm.
4. Pick the dehumidifier. Device ID, IP, **local key** and protocol are filled in automatically. Leave *poll only*
   unchecked.
5. **Choose the device type: `Sygonix Smarter dehumidifier`** (see below).
6. Reserve the device's IP on the router: Tuya Local connects to the stored IP.

The cloud is used once, to fetch the local key. After that, everything goes over the LAN. The local key is a
secret: anyone on the LAN who knows it can control the device. Never commit it.

## Data points (live values from the device)

| DP | Value example | Meaning |
|----|---------------|---------|
| 1 | `false` | power |
| 2 | `40` | target humidity, % |
| 4 | `"low"` | fan speed |
| 5 | `"dehumidify"` | mode |
| 6 | `51` | current humidity, % |
| 7 | `23` | temperature, in the unit from DP 24 |
| 10 | `true` | ionizer |
| 16 | `false` | child lock |
| 17 | `"cancel"` | timer |
| 19 | `32` | status/fault bitfield: 1 tank full or missing, 2 clean filter, 4 E1 temperature sensor, 8 CL too cold, 16 CH too hot, 32 LO humidity too low, 64 coil failure (per the Sygonix description) |
| 20 | `true` | filter reset |
| 24 | `"c"` | temperature unit (`c`/`f`) |
| 102 | `68` | model / client code (informational) |

Read them yourself from inside the HA container with tinytuya (bundled with Tuya Local):
`tinytuya.Device(<device_id>, <ip>, <local_key>, version=3.4).status()`.

## Plan: switch to the matching device description

Tuya Local auto-picked **`vivosun_de0003_dehumidifier`**, which is wrong for this model:

| | Device sends | Vivosun DE0003 (auto-picked) | Sygonix Smarter (correct) |
|---|---|---|---|
| Temperature | `23` + unit `"c"` | treats it as °F → **−5 °C** ❌ | uses DP 24 → **23 °C** ✅ |
| Status DP 19 | `32` | generic "Problem" | decoded descriptions (tank, filter, sensor, temperature, coil) |
| Filter reset, unit select, filter sensor | present | missing | present |
| DPs covered | 13 | 10 | **13** (all) |

Steps (the type can't be changed after setup):

1. **Settings → Devices & services → Tuya Local** → the dehumidifier entry → **⋮ → Delete**.
2. **Add integration → Tuya Local** → SmartLife cloud (the login is usually remembered) → confirm the prefilled
   connection details.
3. At the device type step, choose **`Sygonix Smarter dehumidifier`**.
4. Turn the dehumidifier on for a minute and check the *Problem* sensor and its description. Find out whether
   DP 19 = `32` ("LO: humidity too low") is a real fault or just a normal status for this model. Write the result here.
5. If the Sygonix description still doesn't fit, write a dedicated description for this model and contribute it
   upstream to [tuya-local](https://github.com/make-all/tuya-local). Local edits inside `custom_components/` are
   overwritten by updates.
