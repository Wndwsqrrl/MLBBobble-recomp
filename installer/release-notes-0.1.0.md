Native Windows PC ports of the Xbox 360 games **MLB Bobblehead Pros** and **MLB Bobblehead
Battle**, made by static recompilation. This first release covers the base games: both play
full matches with their original rosters.

> **You need your own copy of each game.** These downloads contain the launcher and the
> recompiled game programs but no game data. See the
> [README](https://github.com/Wndwsqrrl/MLBBobble-recomp#getting-your-game-files) for how to
> extract your game files.

## Downloads

| File | What it is |
|------|------------|
| `MLB-Bobblehead-Recomp-0.1.0-setup.exe` | Installer: adds both games to the Start menu (and optionally the desktop) and to Installed apps |
| `MLB-Bobblehead-Recomp-0.1.0-portable.zip` | The same files without installing: unzip anywhere and run `MLB Bobblehead Launcher.exe` |
| `SHA256SUMS.txt` | Checksums for both |

## Getting started

1. Extract your own copy of each game so you have its `default.xex` and `data\` folder.
2. Install (or unzip) and start **MLB Bobblehead Pros** or **Battle**.
3. On first launch, point the launcher at each game's folder. It checks that your
   `default.xex` is the version these builds were made from and shows **Verified**.

## What's in this release

- **MLB Bobblehead Pros** and **MLB Bobblehead Battle**, playable from the menus through full
  matches, full version, with keyboard or an XInput controller.
- **Launcher** with game cards, first-run setup with the version check, and options for
  V-Sync, keyboard controls, fullscreen and resolution (720p to 4K).
- **Report a problem:** one click saves a zip with your recent logs, a short system summary
  and the games' settings (your user name removed) to attach to an issue. Logs are kept in
  `Documents\bobbleheadpros\logs\`.
- Picks the discrete GPU on laptops with two GPUs.

## Known issues

- **Battle has no audio.**
- No online play, and achievements are not tracked.
- NVIDIA GPUs need the ROV render path, which the included settings already select.
- Roster updates and DLC (the Oct 2011 roster update, Bobblehead Stars) are not supported yet.

See the README's [Known issues](https://github.com/Wndwsqrrl/MLBBobble-recomp#known-issues)
for details.

## Found a problem?

Click **Report a problem** in the launcher and attach the zip to a new
[issue](https://github.com/Wndwsqrrl/MLBBobble-recomp/issues), with which game, what you were
doing and what happened.
