# MLB Bobblehead Recomp v0.1.0

The first release: native Windows PC ports of the base Xbox 360 games **MLB Bobblehead Pros**
and **MLB Bobblehead Battle**, made by static recompilation. Both games play full matches with
their original rosters.

**You need your own copy of each game.** These downloads contain the launcher and the
recompiled game programs but no game data; see the README for how to extract your game files.

## Downloads

- `MLB-Bobblehead-Recomp-0.1.0-setup.exe`: installer. Adds both games to the Start menu (and
  optionally the desktop) and to Installed apps.
- `MLB-Bobblehead-Recomp-0.1.0-portable.zip`: the same files, unzip and run
  `MLB Bobblehead Launcher.exe`.
- `SHA256SUMS.txt`: checksums for both.

## What's in it

- **Both games playable** from the menus through full matches, full version, with keyboard or
  an XInput controller.
- **Launcher** with game cards, a first-run setup that checks your `default.xex` is the version
  these builds were made from, and options for V-Sync, keyboard mode, fullscreen and
  resolution (720p to 4K).
- Picks the discrete GPU on laptops with two GPUs.

## Known issues

- **Battle has no audio.**
- No online play, and achievements are not tracked.
- NVIDIA GPUs need the ROV render path, which the included settings already select.

See the README's Known issues section for details.

## Not in this release

- **Updates and DLC:** the Oct 2011 roster update, rosters for other seasons and the
  Bobblehead Stars DLC are not supported yet.
- **Android:** the Android version of Pros builds from source but is not playable yet, and no
  APK is provided.
