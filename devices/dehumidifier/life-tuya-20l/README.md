# LIFE Tuya Wi-Fi Dehumidifier 20L

20-litre dehumidifier sold under the LIFE brand (Greece/Cyprus retail), controlled through the **Smart Life / Tuya**
app. It's a white-label Tuya device (Tuya product ID `scpee7utfuawhrft`, protocol 3.4).

**Status:** ✅ works locally with Tuya Local, description **`eberg_rico_r12e2_dehumidifier`**: on/off, target
humidity, current humidity, temperature (°C), fan speed, timer, child lock. Known limitations are listed below.

## Integration

[Tuya Local](https://github.com/make-all/tuya-local), fully local. It isn't in the default Marketplace catalog: add
it via **Marketplace → Add by link** → `https://github.com/make-all/tuya-local`, type *Integration*, then download it.
The official Tuya integration is cloud-based (Cloud Push), so it's not used.

1. **Firewall:** Tuya devices announce themselves with UDP broadcasts. Without these rules, Tuya Local reports
   *"The Tuya cloud does not provide local IP addresses"*:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 6666:6667 proto udp comment 'Tuya local discovery broadcasts'
   sudo ufw allow from 192.168.0.0/16 to any port 7000 proto udp comment 'Tuya local discovery broadcasts (protocol 3.5)'
   ```
2. **Add integration → Tuya Local → "Set up device using the SmartLife cloud"**.
3. Enter the **User code** from the Smart Life app (*Me → ⚙ → Account and Security → User Code*), then scan the QR
   code with the app and confirm.
4. Pick the dehumidifier. Device ID, IP, **local key** and protocol are filled in automatically. Leave *poll only*
   unchecked → **Confirm**.
5. On the **next** screen (device type), choose **`Dehumidifier (eberg_rico_r12e2_dehumidifier)`**. Tuya Local
   preselects `vivosun_de0003`, which reads the temperature as °F (23 °C shows as −5 °C).
6. If the temperature sensor still shows °F (left over from a previous setup): open the entity → ⚙ → **Unit of
   measurement → °C**. Home Assistant keeps the display unit of an entity across re-adds.
7. Reserve the device's IP on the router: Tuya Local connects to the stored IP.

The cloud is used once, to fetch the local key. After that, everything goes over the LAN. The local key is a secret:
anyone on the LAN who knows it can control the device. Never commit it.

> ⚠️ **Don't hold the Timer button for 3 seconds**: on this model it resets Wi-Fi. The device leaves the Smart Life
> account and gets a **new local key**, so Home Assistant loses it. Recovery: pair it again in Smart Life, then delete
> and re-add it in Tuya Local.

## Known limitations

| Topic | Behavior |
|-------|----------|
| "Problem" sensor | Shows red while DP 19 = `32`. On this model `32` is the **filter cleaning reminder**: the app shows *"It's time to clean your Smart Dehumidifier"*. It's a real maintenance item, so it's left as a problem. |
| Filter reminder reset | Not possible over the network: DP 20 ignores writes. Not done by holding Mode or Fan either. Holding Timer resets Wi-Fi (see above). How to reset it is still unknown (manual or LIFE support). The reminder doesn't affect operation. |
| Tank full | **Not reported** over the network: DP 19 stays unchanged with a full or removed tank. Indirect sign: the device is on, but humidity keeps rising. |
| Mode selector | The description's mode names (`Continuities/Auto/Sleep`) don't match the device (`dehumidify`). Don't change the mode from HA. `dry_pury_evo_dehumidifier` has matching mode names (`dehumidify/drying/sleep`) but no timer. |

## Data points (live values from the device)

| DP | Value example | Meaning |
|----|---------------|---------|
| 1 | `true` | power |
| 2 | `40` | target humidity, % |
| 4 | `"low"` / `"high"` | fan speed 1 / 2 |
| 5 | `"dehumidify"` | mode |
| 6 | `51` | current humidity, % |
| 7 | `23` | temperature, in the unit from DP 24 |
| 10 | `true` | ionizer (assumed) |
| 16 | `false` | child lock |
| 17 | `"cancel"` | timer |
| 19 | `32` | status bitfield; `32` = filter cleaning reminder (tank state isn't reported) |
| 20 | `true` | unknown; ignores writes (not a working filter reset) |
| 24 | `"c"` | temperature unit (`c`/`f`) |
| 102 | `68` | model/client code (informational) |

Read them yourself from inside the HA container with tinytuya (bundled with Tuya Local):
`tinytuya.Device(<device_id>, <ip>, <local_key>, version=3.4).status()`.

## Possible improvement

A dedicated description for this model (temperature unit from DP 24, correct mode names, a "clean filter" sensor
instead of a generic problem, product ID for auto-matching), contributed upstream to
[tuya-local](https://github.com/make-all/tuya-local). Not done: the current setup is good enough.
