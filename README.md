# commit-glow

Your GitHub contribution history, lit up on your keyboard. Every key is a day: green if you shipped, red if you didn't. Today's key stays red until your first commit. Mice and other single-color devices show today only.

**Use it as a Claude Code skill, not a template.** Every keyboard is different: the brand, the layout, how many LEDs it has, the order the firmware numbers them in, and whether a vendor app is fighting over the lights. Copying someone's config won't light up your board correctly. The skill makes your agent work it out for your hardware:

- detects what you have plugged in
- uses a built-in driver or OpenRGB when one fits
- when nothing fits, reverse-engineers the lighting protocol from your vendor's app, maps which LED is which key, and writes a driver for your device

The first native driver, for the EvoFox Ronin 75%, was built exactly this way.

```
/plugin marketplace add herin7/commit-glow
/plugin install commit-glow@commit-glow
```

Then tell Claude: **"put my GitHub streak on my keyboard"**.

## What it looks like

On a one-key-per-day keyboard you read it like text: left to right, row by row. The first key is the oldest day and the last key is today.

```
Esc F1  F2  F3  ...  F12 Del        <- oldest days
`   1   2   3   ...  =   Bksp
...
Ctrl Win Alt  Space  Alt Fn  ← ↓ →  <- → is today
```

Keyboards that OpenRGB knows the layout of get a weekly grid instead: each column is a week, each row a weekday.

## Without Claude Code

```sh
pip install git+https://github.com/herin7/commit-glow
commit-glow devices     # what it found
commit-glow demo        # today shown as a missed day for 15 s
commit-glow map         # which key is which date
commit-glow autostart   # run at login
```

GitHub access comes from the `gh` CLI (`gh auth login`), or set `GITHUB_TOKEN` to a token with `read:user`. Private-repo contributions count if your profile shows them.

## Hardware

| Device | Support |
|---|---|
| EvoFox Ronin 75% (wired) | native driver, one key per day |
| Logitech G102 / G203 LIGHTSYNC | native driver, today's color |
| Anything [OpenRGB supports](https://openrgb.org/devices.html) | run OpenRGB with **SDK Server** on |
| Anything else with per-key RGB and a Windows vendor app | ask the skill to build a driver ([how](PROTOCOLS.md#adding-a-new-device)) |

Close the vendor app (EvoFox, G HUB lighting, Synapse, iCUE...) while commit-glow runs, or it will overwrite the colors.

## Commands

| | |
|---|---|
| `commit-glow run` | the loop: check GitHub every 5 min, repaint on change |
| `commit-glow demo` | preview a zero-commit day |
| `commit-glow devices` | list detected devices |
| `commit-glow map` | which key shows which date |
| `commit-glow probe` | every HID device and interface as JSON (start here for new hardware) |
| `commit-glow restore` | put native devices back how they were before the first run |
| `commit-glow autostart [--remove]` | start `run` at login: Windows Startup shortcut, macOS LaunchAgent, Linux systemd user service |

Works on Windows, macOS and Linux. On Linux, give your user access to the device's hidraw node with a udev rule (the skill does this for you).

## Going back to normal

1. `commit-glow autostart --remove`, then stop the running `python -m commit_glow run`.
2. `commit-glow restore`. EvoFox: the settings saved on first run (`%APPDATA%\commit-glow\` or `~/.config/commit-glow/`) are written back. G102: unplug and replug. OpenRGB devices: pick a profile in OpenRGB.
3. Or open the vendor app and pick any mode.

## Contributing a driver

If the skill built a driver for your device, send it back as a PR (a class in `commit_glow/backends.py` plus its notes in `PROTOCOLS.md`), so the next person with that keyboard gets it on the first try.

## Tests

```sh
python -m pytest tests   # or: python tests/test_core.py
```

MIT licensed.
