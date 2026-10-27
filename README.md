# commit-glow

Your GitHub contribution graph, on your keyboard.

Each key column is a week, each row a weekday. Green keys are days you shipped (darker = more), red keys are days you didn't. Today's key stays red until your first commit. Mice and other single-color devices show today only: red that brightens through the day, green once you've committed.

```
        Esc F1  F2  F3  ...                newest week ->  PrtSc
Mon     ■   ■   □   ■   ...                                  ■
Tue     ■   ■   ■   □   ...                                  ■
Wed     □   ■   ■   ■   ...                        today ->  □  (red until you commit)
...
■ green = contributions   □ red = zero
```

## Install

```sh
pip install git+https://github.com/herin7/commit-glow
commit-glow devices     # what it found
commit-glow demo        # today shown as a missed day for 15 s
commit-glow autostart   # run at login (Windows; prints the command elsewhere)
```

GitHub access comes from the `gh` CLI (`gh auth login`), or set `GITHUB_TOKEN` to a token with `read:user`. Private-repo contributions count if your profile shows them.

## Supported hardware

| Device | How |
|---|---|
| EvoFox Ronin TKL (wired) | native driver, no extra app |
| Logitech G102 / G203 LIGHTSYNC | native driver, works even without G HUB |
| Anything [OpenRGB supports](https://openrgb.org/devices.html) (Razer, Corsair, SteelSeries, ASUS, HyperX, Redragon, ...) | start OpenRGB, enable **SDK Server**, leave it running |

Keyboards get the per-key heatmap when the driver knows their layout (OpenRGB "matrix" zones). Other devices get today's single color.

Close the vendor app (EvoFox, G HUB lighting, Synapse, iCUE...) if it fights over the lights.

## Commands

| | |
|---|---|
| `commit-glow run` | the loop: check GitHub every 5 min, repaint on change |
| `commit-glow demo` | preview a zero-commit day |
| `commit-glow devices` | list detected devices |
| `commit-glow restore` | put native devices back how they were before the first run |
| `commit-glow autostart [--remove]` | start `run` at login |

## Going back to normal

1. `commit-glow autostart --remove`, then stop the running `pythonw`/`python -m commit_glow run`.
2. `commit-glow restore`. EvoFox: the settings saved on first run (`%APPDATA%\commit-glow\` or `~/.config/commit-glow/`) are written back. G102: unplug and replug. OpenRGB devices: pick a profile in OpenRGB.
3. Or just open the vendor app and pick any mode.

## Claude Code

This repo is a Claude Code plugin with a setup skill:

```
/plugin marketplace add herin7/commit-glow
/plugin install commit-glow@commit-glow
```

Then ask "put my GitHub streak on my keyboard". The skill installs, detects, demos and sets up autostart.

## Adding a keyboard

If OpenRGB supports it, you're done. If not, [PROTOCOLS.md](PROTOCOLS.md) shows how the EvoFox driver was built: trace the vendor app's HID writes, find the per-key color command and the LED index layout, then add a class next to `EVision` in `commit_glow/backends.py`. PRs welcome.

## Tests

```sh
python -m pytest tests   # or: python tests/test_core.py
```

MIT licensed.
