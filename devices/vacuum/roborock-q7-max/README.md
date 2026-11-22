# Roborock Q7 Max

Robot vacuum with mopping, Wi-Fi. Model ID in Home Assistant: `roborock.vacuum.a38`.

**Status:** ✅ tested with Home Assistant 2026.11.2.

## Integration

Official [Roborock](https://www.home-assistant.io/integrations/roborock) integration (IoT class **Local Polling**).
No community integrations, no extra containers.

1. The vacuum is set up in the **Roborock** app (not Mi Home).
2. HA: **Settings → Devices & services → Add integration → Roborock**.
3. Enter the Roborock account email, then the code sent to that email.
4. HA creates two devices: the vacuum (~36 entities: state, battery, cleaning modes, rooms, consumables, map) and
   the dock.

The Roborock cloud is used for login and to fetch the device's local key. After that, HA talks to the vacuum directly
over the LAN (TCP port **58867**). Check with `sudo ss -tnp | grep 58867` on the server: there should be an
established connection to the vacuum's IP.

## Notes

- No firewall changes needed: HA opens the connection to the vacuum (outgoing).
- Optional: reserve the vacuum's IP on the router. The integration can look up a new IP via the cloud, but a fixed
  IP keeps it fully local.
