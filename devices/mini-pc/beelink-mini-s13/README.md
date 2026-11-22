# Beelink Mini S13

Reference hardware for this repository. Generic background: [01. Hardware and BIOS](../../../docs/01-hardware-bios.md).

| Component | Value |
|-----------|-------|
| CPU | Intel N150 (4C/4T, up to 3.6 GHz) |
| RAM | 16 GB DDR4 |
| Storage | 512 GB SATA SSD |
| Ethernet | 2 × 2.5 GbE, Intel I226-V (`enp1s0`, `enp2s0` in Ubuntu) |
| Wi-Fi / Bluetooth | Intel CNVi Wi-Fi (`wlo1`), Intel AX201 Bluetooth |
| Preinstalled OS | Windows 11 (erased during install) |

## Keys

| Action | Key |
|--------|-----|
| Enter BIOS setup | `Del` (press repeatedly right after power on) |
| One-time boot menu | `F7` |
| Save and exit | `F4` → `Yes` |

## Step by step

### 1. Enter the BIOS

1. Connect the TV/monitor (HDMI), keyboard, Ethernet and power. Power on.
2. The machine boots into the Windows 11 setup wizard. Don't complete it.
3. **On a TV:** while the Windows wizard is on screen, turn off the TV's enhanced HDMI mode for this
   input (e.g. *HDMI Ultra HD Deep Colour*). Otherwise the TV shows no picture in the BIOS. Details:
   [no picture in the BIOS on a TV](../../../docs/01-hardware-bios.md#important-no-picture-in-the-bios-on-a-tv).
4. Hold the power button for ~5 seconds to turn the machine off. Power it on and press `Del` repeatedly
   until the BIOS appears.

### 2. Power on after power loss

1. Go to the **Chipset** tab.
2. Open **PCH-IO Configuration**.
3. Find **State After G3**.
4. Change it from `S5 State` to **`S0 State`**.
5. Press `F4` and confirm with **Yes**.

| Value | Meaning |
|-------|---------|
| `S0 State` | The machine powers on automatically when power returns. |
| `S5 State` (default) | The machine stays off until the power button is pressed. |

### 3. Boot from the USB stick

With the stick plugged in, press `F7` repeatedly right after power on and choose the entry
**`UEFI: <stick name>`**. Continue with [03. Ubuntu Server install](../../../docs/03-ubuntu-install.md).

## Notes

- A Logitech USB receiver keyboard works in the BIOS and the installer.
- Ubuntu Server 26.04.1 LTS installs without extra drivers. Ethernet, Wi-Fi and Bluetooth are detected out of the box.
- There are two Ethernet ports with different MAC addresses. A DHCP reservation on the router is bound to one of
  them, so always plug the cable into the same port (label it).
- The installer adds both Ethernet ports to netplan. Mark the unused one `optional: true`, otherwise boot waits
  ~2 minutes for it (see [03. Ubuntu install, step 9](../../../docs/03-ubuntu-install.md#9-network-optional-interfaces-and-wi-fi-readiness)).
- Wi-Fi (`wlo1`) works with the in-kernel driver. Only `wpasupplicant` is missing after a wired install.

- Hardware watchdog: Intel TCO (`iTCO_wdt`) works, but Ubuntu deny-lists it. Load it with the boot service from
  [04. Base server setup](../../../docs/04-base-setup.md#5-hardware-watchdog-auto-reboot-on-hangs).
- The SSD (`SSD 512GB`, firmware `Y1224A0`) supports SMART. `fwupd`: no BIOS/SSD updates on LVFS, only the UEFI dbx.
- Secure Boot is **disabled** out of the box (`mokutil --sb-state`). Left as is, so the UEFI dbx update is skipped.

## Status

| Item | Status |
|------|--------|
| Ubuntu Server 26.04.1 LTS install | ✅ tested |
| State After G3 = S0 set | ✅ set |
| Wi-Fi connection (WPA2/WPA3, regulatory domain, power save off) | ✅ tested |
| Auto power-on after unplugging | ✅ tested |
| Hardware watchdog (`iTCO_wdt`, 30 s) | ✅ tested |
| Docker 29 + Compose v5 (official repo, `resolute`) | ✅ tested |
| Home Assistant 2026.11.2 container, built-in Bluetooth (BlueZ via D-Bus) | ✅ tested |
| Boot time (power on → SSH ready) | ~23 s (12.7 s firmware, 3.5 s userspace) |
