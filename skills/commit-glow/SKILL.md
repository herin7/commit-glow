---
name: commit-glow
description: Set up commit-glow, which shows the user's GitHub contribution graph on their keyboard/mouse RGB (green = days with commits, red = missed days). Use when the user wants their GitHub streak, commits or contribution graph on keyboard or mouse lighting, or wants commit-glow installed, fixed, or removed.
---

# commit-glow setup

Work through these in order. Stop and tell the user if a step fails; don't guess past it.

1. **Python + package.** Needs Python 3.9+. Run `pip install git+https://github.com/herin7/commit-glow` (or `pip install -e .` from a clone).
2. **GitHub access.** `gh auth status` must show a login. If not, ask the user to run `! gh auth login`. A `GITHUB_TOKEN` env var also works.
3. **Detect.** Run `commit-glow devices`.
   - Nothing listed, or their keyboard missing: their hardware needs OpenRGB.
     - Point them to https://openrgb.org.
     - Have them enable **SDK Server** (SDK Server tab → Start server; tick "start at launch").
     - Re-run `commit-glow devices`.
   - Keyboard listed as `single color`: OpenRGB has no layout for it, so it can only show today's color. Say so.
   - Wireless keyboards: some (EvoFox) only take lighting over the cable.
4. **Vendor apps.** Close vendor lighting software (EvoFox, Synapse, iCUE, G HUB lighting...) if colors flicker or get overwritten. Ask before removing anything from startup.
5. **Show it.** Run `commit-glow demo`. Today's key goes red for 15 s, then the real heatmap returns. Ask the user what they see.
6. **Autostart.** Run `commit-glow autostart`. On Windows this adds a Startup shortcut. Elsewhere it prints a command to add as a login item or systemd user service. Then start `commit-glow run` (background) so it's live now.

## Reading the board

- Key columns are weeks, with the newest on the right.
- Rows are Mon..Fri, then the weekend (Sat + Sun share one row on 6-row keyboards).
- Green = contributions, darker = more. Red = zero.
- Today's key is red until the first commit.

## Undo

`commit-glow autostart --remove`, stop the running process, then `commit-glow restore`. EvoFox gets its pre-install settings back. For other devices, the user picks a mode in the vendor app or OpenRGB.

## Never

- On EvoFox/EVision boards, never write mode `0x14`. It's Off on that firmware.
- Never send partial config writes; they are ignored.
- See `PROTOCOLS.md` before touching driver code.
