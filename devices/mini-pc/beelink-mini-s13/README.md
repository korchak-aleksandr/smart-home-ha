# Beelink Mini S13

Reference hardware for this repository. Generic background: [01. Hardware and BIOS](../../../docs/01-hardware-bios.md).

| Component | Value |
|-----------|-------|
| CPU | Intel N150 (4C/4T, up to 3.6 GHz) |
| RAM | 16 GB DDR4 |
| Storage | 500 GB NVMe SSD |
| Network | 1 GbE (shows up in Ubuntu as `enp2s0`) |
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
- Ubuntu Server 26.04.1 LTS installs without extra drivers. Ethernet works out of the box.

## Status

| Item | Status |
|------|--------|
| Ubuntu Server 26.04.1 LTS install | ✅ tested |
| State After G3 = S0 set | ✅ set |
| Auto power-on after unplugging | ⏳ not tested yet |
