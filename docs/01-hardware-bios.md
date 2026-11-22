# 01. Hardware and BIOS

Prepare the mini PC firmware so that the machine:

1. **powers on automatically** after a power outage, so it never needs a button press;
2. **boots from the USB stick** once to install Ubuntu.

**Model-specific step-by-step:** [Beelink Mini S13](../devices/mini-pc/beelink-mini-s13/README.md)
(reference hardware). For other models, see [`devices/mini-pc/`](../devices/mini-pc/) or use the generic
steps below.

**You need:** a display with HDMI (a TV works), a USB keyboard, and the USB stick from
[02. Installation media](02-install-media.md). The display and keyboard are needed only until SSH
works.

## 1. Enter the BIOS

1. Connect the display, keyboard, Ethernet and power, then power on.
2. A new mini PC usually boots into the preinstalled Windows first-run setup wizard. That's fine: don't
   complete it, Windows is erased during the Ubuntu install anyway.
3. Reboot: hold the power button for ~5 seconds until the machine turns off, then power it on again.
4. Immediately press the BIOS key (usually `Del`, sometimes `F2` or `Esc`) about twice per second until the
   setup screen appears. Give the display ~10 seconds to show it.

**Windows shows up on the screen, but the BIOS never does?** See the next section. It's almost always the TV.

### Important: no picture in the BIOS on a TV

**Symptom:** the TV shows Windows (e.g. its setup wizard), but stays black where the BIOS should be: no
logo, no setup screen. The BIOS may actually be open, and the TV simply doesn't display that signal.

**Cause:** many TVs have an "enhanced" HDMI mode per input for 4K HDR / high refresh rate sources.
Common names are *HDMI Ultra HD Deep Colour*, *Input Signal Plus*, *HDMI Enhanced Format* and
*HDMI 2.1 mode*. With this mode on, some TVs can't display the signal the BIOS outputs. The mode often
gets turned on silently when you accept a TV prompt like *"optimize this input for gaming / low latency"*.

**Fix:**

1. Let the machine boot into Windows, so the TV has a picture. Many TVs don't let you change settings for
   an input that has no signal.
2. In the TV settings, turn the enhanced HDMI mode **off** for that HDMI input. Look under
   *Settings → General → Devices → HDMI settings* or similar.
3. Reboot (hold the power button, power on) and press `Del` again. The BIOS now appears.

Alternatives: plug the cable into another HDMI port on the TV (it keeps its own, default settings), or
use a regular computer monitor for this step.

### Keyboard

Wireless keyboards with a USB receiver (e.g. Logitech) usually work in the BIOS and the Ubuntu installer
just like wired ones. If the keyboard doesn't react before the OS loads, use any wired USB keyboard for
this step.

## 2. Power on after power loss

Find the setting that controls what happens when power returns after an outage, and set it to
**power on**. Vendors name it differently:

| Setting name | Value to choose | Example model |
|--------------|-----------------|---------------|
| State After G3 | `S0 State` | [Beelink Mini S13](../devices/mini-pc/beelink-mini-s13/README.md): *Chipset → PCH-IO Configuration* |
| Restore on AC Power Loss | `Power On` | |
| AC Power Recovery / AC Back | `Always On` / `Power On` | |
| Power On After Power Fail | `On` | |

It usually lives under *Chipset*, *Advanced → Power* or *Power Management*.

`G3` is the ACPI name for "mechanical off" (no power), `S0` is "running" and `S5` is "soft off". So
*State After G3 = S0* means "after power returns, go to the running state".

Leave **Secure Boot** as it is: Ubuntu boots with Secure Boot enabled.

Save and exit (often `F4` or `F10`, then confirm).

## 3. Boot from the USB stick

With the stick plugged in, reboot and open the **one-time boot menu**. The key is vendor-specific: `F7`,
`F11`, `F12` or `Esc`.

Choose the entry that starts with **`UEFI:`** followed by the stick's name. Then continue with
[03. Ubuntu Server install](03-ubuntu-install.md).

## 4. Verify auto power-on (optional)

After Ubuntu is installed and reachable over SSH: unplug the power cable, wait 10 seconds and plug it
back in. The machine should boot on its own, and SSH should respond about a minute later.
