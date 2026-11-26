# Presence: who is home

Goal: a reliable **home / not home** status per person, **without location data**. No GPS coordinates on the server,
no app required on the phone.

## How: iPhone Device Tracker (iphonedetect)

[iphonedetect](https://github.com/mudape/iphonedetect) (in the default Marketplace catalog as *iPhone Device
Tracker*, IoT class Local Polling):

1. Every few seconds, Home Assistant sends a tiny UDP packet (mDNS, port 5353) to each phone's IP address.
2. An iPhone answers on the network level **even in deep sleep**, so the server's neighbor (ARP) table gets a
   `REACHABLE` entry for it.
3. The integration reads that table: entry present → **home**; absent longer than *consider home* → **not home**.

Plain `ping` doesn't work for this: sleeping iPhones ignore ICMP. On the reference server, a phone at home showed 0/3
pings answered, yet `ip neigh` reported it `REACHABLE`.

Requirements: Home Assistant with `network_mode: host` (it must see the host's neighbor table). No firewall changes:
the probe is outgoing, and ARP isn't filtered.

## Setup

**On each iPhone:** *Settings → Wi-Fi → (i) next to the home network → Private Wi-Fi Address → **Fixed***, not
*Rotating* (iOS 18+). Rotating changes the MAC address, and the reserved IP stops matching. On the same screen, note the
**IP address** and the **Wi-Fi address** (MAC).

**On the router:** reserve each phone's IP for its MAC ([03, DHCP reservation](../03-ubuntu-install.md#fallback-reserve-the-ip-address-on-the-router)).
Use one SSID for both bands, so that each phone has one MAC.

**In Home Assistant:**

1. *Marketplace* → *iPhone Device Tracker* → download → restart HA.
2. *Settings → Devices & services → Add integration → iPhone Device Tracker* → a name and the phone's IP. Repeat per phone.
3. Device options → **consider home: 180 s**. The default of 24 s turns short Wi-Fi gaps (night-time updates, far
   corners of the flat) into false "left home" events.
4. *Settings → People*: one person per household member, **tracking only the iphonedetect tracker**. If the HA app
   is installed, remove the app's tracker from the person: mixing sources makes the person flap when they disagree.

The household member doesn't need a Home Assistant login or the app.

**Show it:** dashboard → edit → *Add badge* (or a *Tile* card) → `person.<name>`. Upload photos under *Settings →
People*, and badges dim them when the person isn't home.

## Privacy

| Source | What the server stores |
|--------|------------------------|
| iphonedetect | `home` / `not_home` only |
| HA Companion app with location permission | **GPS coordinates** (latitude, longitude, accuracy) in the tracker's attributes and in HA's history, and therefore also in backups |

To keep coordinates off the server, set *iPhone Settings → Home Assistant → Location → **Never***. The app keeps
working for the UI and notifications. The app's tracker keeps its **last** coordinates as attributes until the entity
is removed, and the history keeps past points until it's purged. The home location in *Settings → System → General*
can be approximate: sun-based automations only need the rough area.

Never commit person names, phone IPs/MACs or schedules derived from presence ([AGENTS.md](../../AGENTS.md)).

## Limitations

- It detects the phone **on the home Wi-Fi**. Wi-Fi off or airplane mode reads as `not_home`.
- Arrival is noticed within seconds (phones join Wi-Fi near the door). Departure takes *consider home*.
- Phones updating at night can briefly drop off. The 180 s timeout absorbs most of it.
- Only phones with a reserved IP are tracked. Guests are invisible.
