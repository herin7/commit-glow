---
name: commit-glow
description: Show the user's GitHub contribution history on their keyboard/mouse RGB (green = days with commits, red = missed days) on any OS and any hardware, including writing a new driver for an unsupported keyboard or mouse. Use when the user wants their GitHub streak, commits or contribution graph on keyboard or mouse lighting, or wants commit-glow installed, fixed, extended to a new device, or removed.
---

# commit-glow

**Goal:** the user's own devices correctly showing their GitHub history.

- **Keyboard:** one key per day, read left to right and row by row. The first key is the oldest day, the last key is today.
- **Mouse and other single-color devices:** today only. Red that brightens through the day, then green after the first commit.
- **Colors:** green means contributions (darker = more), red means zero.

Every user has different hardware. Don't stop at "unsupported": extend the tool. You can't see the desk, so after every visual step ask the user what the device actually shows, naming specific keys and colors.

## 0. Ground rules

- Read `PROTOCOLS.md` before touching any device protocol.
- Never send a config or mode write you haven't seen the vendor app send. A wrong mode byte can switch the lights off (on EvoFox, `0x14` is Off).
- Per-key colors often live in flash. Write them only when they change, never on every poll.
- Back up the device's settings before the first write (native drivers do this automatically).
- Ask before removing vendor apps from startup, and keep a backup of what you remove.

## 1. Install

1. Python 3.9+: `pip install git+https://github.com/herin7/commit-glow`. If you might add a driver, clone the repo and `pip install -e .`
   - pip can't build (no setuptools, offline): run from the clone with `python -m commit_glow ...` from the repo root.
2. GitHub: `gh auth status` must show a login. Otherwise ask the user to run `! gh auth login`, or set `GITHUB_TOKEN` (scope `read:user`).
3. OS prerequisites:
   - **Linux:** hidraw needs permission. Add a udev rule for each device, then replug:
     `echo 'KERNEL=="hidraw*", ATTRS{idVendor}=="320f", MODE="0660", TAG+="uaccess"' | sudo tee /etc/udev/rules.d/70-commit-glow.rules && sudo udevadm control --reload && sudo udevadm trigger`
     (one line per vendor ID; ask before using sudo).
   - **macOS:** grant the terminal Input Monitoring if HID opens fail.
   - **Windows:** nothing extra.

## 2. Detect

- Run `commit-glow devices`. Each device shows as `N keys, one per day`, `RxC grid`, or `single color`.
- Run `commit-glow probe` for the raw HID inventory: vid/pid, interfaces, usage pages, and `vendor_defined` collections.

Decide per device:

| Situation | Path |
|---|---|
| Listed as one key per day or a grid | step 3 |
| Not listed, and on https://openrgb.org/devices.html | user installs OpenRGB, enables SDK Server (start at launch), re-run `devices` |
| Keyboard listed as `single color` | OpenRGB lacks its layout; build a native driver (step 5) for per-key |
| Not supported anywhere | build a driver (step 5) |

Also check:
- **Wireless devices:** lighting control is often only available over the cable or the 2.4 GHz dongle. If `probe` shows no vendor-defined collection in Bluetooth mode, ask the user to plug in the cable.
- **Two tools on one device:** don't run OpenRGB and a native driver on the same device. `discover()` skips OpenRGB devices a native driver already claimed.

## 3. Show and verify

1. Ask the user to fully close vendor lighting software (EvoFox, Synapse, iCUE, G HUB lighting, Armoury Crate...), including the tray icon. Otherwise it overwrites the colors.
2. Run `commit-glow demo`. Today shows as missed (red) for 15 s, then the real picture returns. Ask: "did the last key / the mouse turn red, then back?"
3. Run `commit-glow map`. Pick 3-4 specific keys from its output: one known red day, one green, and the first and last key. Ask whether exactly those keys show those colors.
4. If keys are scrambled or dark, the LED order is wrong. Fix it (step 5.4) before anything else. Never infer a layout from a product name: one brand's "TKL" and "75%" number their LEDs differently.

## 4. Autostart

Run `commit-glow autostart`. It installs a Windows Startup shortcut, a macOS LaunchAgent, or a Linux systemd user service, and starts it. On Windows, also start it now: `pythonw -m commit_glow run`. Confirm the process is running.

## 5. Build a driver for a new device

The EvoFox driver was built exactly this way.

1. **Interface.** From `probe`, take the device's `vendor_defined` collections (usage page `0xFFxx`). Lighting is almost always one of them. Note the input and output report sizes. On Windows, call `HidP_GetCaps` via ctypes; elsewhere, read the report descriptor.
2. **Record the vendor app.**
   - Windows, 32-bit app: `python tools/hid_tracer.py <app pid> trace.log <seconds>` logs every HID packet the app sends.
   - Otherwise: USBPcap + Wireshark (Windows), or `usbmon` + Wireshark (Linux). macOS: run the vendor app in a Windows VM with USB passthrough and capture there.
   - Have the user change **one** setting at a time while you note the order: e.g. "static mode", "max brightness", "custom mode", "paint Esc red".
3. **Decode.** Find these, then copy the app's packets byte for byte (firmware often ignores "equivalent" packets):
   - report ID, header, checksum
   - read and write commands, with offset and size fields
   - the mode/config block and the per-key color command
   - whether the device answers each command, and with which status byte
4. **Map LEDs to keys.**
   - Record while the user paints keys in the app's per-key editor, **one at a time, in an order you give them**. The order the new LED indices appear in is the mapping.
   - Cover every key: list them by row and ask the user to paint row by row.
   - Vendor data files (layout JSON, key images) are often generic templates for other models. Don't trust them.
5. **Implement** in `commit_glow/backends.py`, then add it to `NATIVE` as `(MyKeyboard, usage_page, usage_or_None)`:

   ```python
   class MyKeyboard:
       KNOWN = {(0xVVVV, 0xPPPP): 'Brand Model'}
       keys = [...]    # LED indices in reading order, first key = oldest day, last key = today
       labels = [...]  # same length: printed key names, for `commit-glow map`

       def __init__(self, vid, pid, path):
           import hid
           self.name, self.h, self.last = self.KNOWN[vid, pid], hid.device(), None
           self.h.open_path(path)
           # back up current settings to STATE / f'mydevice-{vid:04x}-{pid:04x}.json' if not there yet,
           # then switch to the per-key / custom mode exactly as the vendor app does

       def show_days(self, colors):  # list of (r, g, b), oldest first
           buf = ...  # per-key buffer built from zip(self.keys[-len(colors):], colors[-len(self.keys):])
           if buf != self.last:  # write only on change
               ...  # send it the way the vendor app does
               self.last = buf

       def restore(self):
           ...  # write the backup back
   ```

   - Single-color devices (mice) implement `show_color(rgb)` instead of `keys` / `show_days`.
   - Grid devices implement `rows`, `cols`, `show_grid(cells)`.
6. **Verify** with step 3. Add the protocol notes to `PROTOCOLS.md` and a test to `tests/test_core.py` (`len(keys) == len(labels)`, no duplicate indices), then offer the user a PR to herin7/commit-glow so the next person with that device gets it on the first try.

## Undo

`commit-glow autostart --remove`, then `commit-glow restore`. Native devices get their pre-install settings back. For other devices, pick a mode in the vendor app or OpenRGB.
