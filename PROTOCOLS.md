# Protocols

Notes for the native drivers, and how to find a new one.

## EvoFox Ronin TKL (EVision chip, USB `320F:5055`)

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
- **LED index** = `row * 21 + column` (Esc = 0, F1 = 1, Tab = 42, LShift = 84).
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
