# Huawei HG8245X6-10 (fiber ONT)

A fiber optical network terminal with a built-in router and Wi-Fi. ISPs supply it, e.g. Cyta in
Cyprus (ISP-branded web UI).

## Web admin

- Address: `http://192.168.10.254` (Cyta default; check the sticker on the device)
- Login: the user name and password are printed on the sticker on the device. With an ISP account you
  get access to LAN settings, not to the ISP's WAN/PON provisioning.
- On the first login, a **setup wizard** (Wi-Fi configuration → Account management → Completion)
  opens. Click **Exit** to leave it without changing anything.

> ⚠️ Don't press **Reset** or restore factory defaults. On an ISP fiber terminal this can erase the
> ISP's provisioning, and internet stays down until the ISP restores it. Don't change *WAN*, *PON* or
> *VoIP* settings either.

## DHCP reservation

**LAN → DHCP Static IP → New** → enter *MAC Address* (`AA:BB:CC:DD:EE:FF` format) and *IP Address* →
**Apply**. The entry appears in the table. No reboot is needed.

The DHCP pool range is visible under **LAN → DHCP Server**.
