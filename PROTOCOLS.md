# Protocols

Notes for the native drivers, and how to find a new one.

## EvoFox Ronin 75% (EVision chip, USB `320F:5055`, reports itself as "Ronin TKL-1")

Found by attaching a debugger to the EvoFox app and logging its `WriteFile` calls while changing settings. OpenRGB's "EVision V2" driver is close, but this firmware differs in ways that matter.

- **Interface:** HID collection with usage page `0xFF1C`, 64-byte reports. Over Bluetooth this collection isn't exposed, so the board must be wired.
- **Packet:** `[04, sumLo, sumHi, cmd, size, offLo, offHi, 00, data...]`.
  - sum is the 16-bit sum of bytes 3..63.
  - The keyboard echoes the header back; byte 7 is status (0 = OK).

| cmd | meaning |
|---|---|
| `01` / `02` | begin / end config |
| `03` | read capabilities (answers `AA 55 ...`) |
| `05` / `06` | read / write config |
| `0A` / `0B` | read / write custom colors |
| `12` | "dynamic colors" in OpenRGB. Acknowledged but **does nothing** on this firmware |

- **Config writes are silently ignored unless they are the whole 39-byte block from offset 0:** `[profile, mode, brightness, speed, direction, random, R, G, B, ...]`.
- **Modes:** 4 = Spectrum, 6 = Normal (static), **19 = Custom**, **20 = Off**. Writing OpenRGB's "custom" value (`0x14`) turns the lights off.
- **Brightness:** 0-4.
- **Per-key colors:** cmd `0B`, 384 bytes of RGB in 7 × 56-byte chunks. Only shown in Custom mode.
- **LED index** = `row * 15 + column`, following the physical 75% rows. Mapped by recording the app's per-key painter while keys were painted in a known order. The app's own `Keyboard.json` and `Skin/Kb/light` images are a generic full-size template (21 slots per row) and are wrong for this board.

  ```
  row 0:  Esc F1..F12 Del                          0-13   (14 = knob, no LED)
  row 1:  ` 1..0 - = Bksp                          15-28
  row 2:  Tab Q..] \ PgUp                          30-44
  row 3:  Caps A..' Enter PgDn                     45-56, 58, 59
  row 4:  LShift Z../ RShift Up                    60-70, 72, 73
  row 5:  LCtrl Win LAlt Space RAlt Fn Left Down Right   75 76 77 81 85 86 87 88 89
  ```
- **Flash:** custom colors are stored in flash, so the driver rewrites them only when they change.

## Logitech G102 / G203 LIGHTSYNC (USB `046D:C092`)

From OpenRGB's G203L driver.

- **Interface:** HID++ long reports (20 bytes), usage page `0xFF00`, usage `0x02`.
- **Commands:**
  - enable software control: `11 FF 0E 50 01 03 07`
  - static color: `11 FF 0E 10 00 01 R G B 02 00 00 00 00 00 00 01`
- In on-board memory mode the mouse ignores G HUB's LED SDK, but these packets still work.

## Finding a new keyboard's protocol

1. List its HID interfaces with `hid.enumerate(vid, pid)`. The vendor collection (usage page `0xFFxx`) is usually the one that carries lighting.
2. Capture what the vendor app sends while you change one setting at a time. Either:
   - USBPcap + Wireshark, or
   - Frida / a debugger hooking `WriteFile`, `HidD_SetOutputReport` and `HidD_SetFeature` in the app.
3. Diff the device's config before and after each change, if it has a read command.
4. Find the LED order: light every 6th index or so and note which keys light up.
5. Write config the exact way the app does. Firmwares often reject "equivalent" packets.
