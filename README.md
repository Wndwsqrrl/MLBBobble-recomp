# MLB Bobblehead Recomp

[![Download](https://img.shields.io/github/v/release/Wndwsqrrl/MLBBobble-recomp?label=Download&color=6d4bd6)](https://github.com/Wndwsqrrl/MLBBobble-recomp/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Wndwsqrrl/MLBBobble-recomp/total?label=Downloads&color=6d4bd6)](https://github.com/Wndwsqrrl/MLBBobble-recomp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-6d4bd6)](LICENSE)

Native Windows PC ports of the two Xbox 360 **MLB Bobblehead** games, made by **static
recompilation** with [ReXGlue](#acknowledgements): the original PowerPC game code is translated
ahead of time into C++ and compiled into a native x64 program that runs on a Xenia-derived
runtime. No emulator is involved. You supply the game data from your own copy.

| Game | Title ID | Status |
|------|----------|--------|
| **MLB Bobblehead Pros** | `58410B7B` | ▶️ Playable: menus to full matches, full version, keyboard or controller. Rosters for any season ([details](#rosters-and-seasons)) |
| **MLB Bobblehead Battle** | `58410B7C` | ▶️ Playable: menus to full matches · ⚠️ **no audio** ([details](#known-issues)) |
| Pros on Android | | 🧪 Experimental: builds and boots to the loading screen, not playable yet ([details](#android-pros-only-experimental)) |

> ⚠️ **v0.1.0 is an early release.** Both games play full matches, but expect rough edges; see
> [Known issues](#known-issues).

## Contents

- [Quick start](#quick-start) · [What's in the download](#whats-in-the-download)
- [Requirements](#requirements) · [Getting your game files](#getting-your-game-files)
- [Controls](#controls) · [Launcher](#launcher) · [Rosters and seasons](#rosters-and-seasons)
- [Building from source](#building-from-source) · [Android](#android-pros-only-experimental)
- [Known issues](#known-issues) · [Repository layout](#repository-layout)
- [Acknowledgements](#acknowledgements) · [Legal](#legal)

---

## Quick start

1. **Get your game files.** Extract your own Xbox 360 copy of each game (see
   [Getting your game files](#getting-your-game-files)).
2. **Download** `MLB-Bobblehead-Recomp-0.1.0-setup.exe` (or the portable zip) from
   [Releases](https://github.com/Wndwsqrrl/MLBBobble-recomp/releases) and install it.
3. **Start MLB Bobblehead Pros or Battle** from the Start menu. The first time, the launcher's
   Setup screen asks you to locate each game's folder (the one containing `default.xex`) and
   checks that it is the version these builds were made from (it shows **Verified**).
4. Play. Optional: in **Setup → Pros roster**, install the Oct 2011 roster update or a roster
   for another season.

## What's in the download

- **Included:** the launcher, both games' recompiled executables (`bobbleheadpros.exe`,
  `bobbleheadbattle.exe`) with the ReXGlue runtime (`rexruntime.dll`, `rexgpu-xenos.dll`) and
  their settings files, app icons and the launcher's box art.
- **Not included:** any game data. Models, textures, stadiums, audio, rosters and everything
  else the games load come from your own copy. The executables do nothing without it.

## Requirements

- Windows 10 or 11, 64-bit
- A Direct3D 12 GPU
  - **NVIDIA:** the default render path shows a black screen; the included settings already
    select the ROV path (`render_target_path_d3d12 = "rov"`). Leave it as it is.
  - **Laptops with two GPUs:** the games pick the high-performance (discrete) GPU
    automatically. To force a particular adapter, set `d3d12_adapter` (0-based) in the game's
    `.toml`.
- Your own extracted game files (below)

## Getting your game files

Each game is an Xbox Live Arcade package (STFS/CON). Extract it with any STFS extractor so you
end up with the game's `default.xex` and its `data\` folder:

```
<your game folder>\
 ├─ default.xex
 └─ data\xbox360_us\...     (models, textures, sound, ...)
```

These builds were recompiled from the **World** XBLA release of each game. The launcher checks
your `default.xex` against that version when you locate a folder; another version or a
modified file may not work (you can still choose to use it).

## Controls

A standard XInput controller works. With keyboard mode on (`mnk_mode = true`, the default), the
Xbox pad maps to the keyboard. Menu inputs sometimes need a firm, slightly longer press.

| Xbox pad | Keyboard |
|----------|----------|
| Start | Enter |
| A | Space |
| B | Backspace |
| X | L |
| Y | P |
| Left stick / move | W A S D |
| D-pad | Shift + arrow keys |
| Back | Z or Tab |

## Launcher

The launcher (`MLB Bobblehead Launcher.exe`) ties both games together:

- **Game cards** with box art, greyed out until a game is set up. The Start menu shortcuts
  run `--play pros` / `--play battle`, which start that game directly once it is set up.
- **Setup:** locate each game's folder, with the version check described above, and pick the
  **Pros roster** (next section).
- **Options:** V-Sync, keyboard controls, fullscreen and resolution (720p, 1080p, 1440p or 4K;
  a preset above your screen's resolution renders higher and scales down for a sharper image).
  The options are written into each game's `.toml`.

It remembers your game folders in `launcher.cfg` next to the launcher.

## Rosters and seasons

**Setup → Pros roster** switches between every roster in the Pros game folder's roster library
(`<game folder>\_rosters\`):

- **2011 Opening Day (original):** the rosters the game shipped with.
- **2011 End of season (Oct 2011 update):** the game's official roster update. Choose
  **Import… → Roster update package** and select the file inside `58410B7B\00000002\` of the
  extracted update download (extract the `.7z` first). The launcher reads the Xbox content
  package itself; with this roster in use the game shows the update icon on the splash screen.
- **Any other season** you add with **Import… → Roster folder** (a folder holding
  `PLAYER_DATA.CHK` and `SEASON_PLAYER_DATA.CHK`, such as one made with the season builder
  below).

Switching writes the roster into the game folder **and into your Pros save**: the game keeps
its own copy of every player in the save and reads names, ratings and looks from there. Close
the game before switching. Before the first switch, each save is backed up to
`Documents\bobbleheadpros\_save_backups\`, and the roster already in the game folder is kept in
the library, so nothing is lost. Switching replaces any players you edited in-game.

### Building a season's roster

`tools/roster/` builds a roster for a real season from public data. It needs Python 3.11 or
newer and your own original roster file as the template:

```powershell
cd tools\roster
python fetch_mlb.py 2026          # rosters, bios and stats from the MLB Stats API
python fetch_show.py 26           # optional: MLB The Show 26 player ratings
python build_season.py --base "<game folder>\_rosters\original\PLAYER_DATA.CHK" `
       --mlb cache\mlb_2026.json --show cache\show26_live.json `
       --name "2026 End of season" --out out\2026
python check_roster.py out\2026
```

Then import `out\2026` in the launcher. How it works:

- **Players:** each club gets 25 (5 starters, 5 relievers, a setup man and a closer, and 13
  position players, picked by playing time), plus both All-Star squads, with real names,
  jersey numbers, positions, handedness, birth dates and the season's stat lines.
- **Ratings** are put on the game's own Power Pros scales two ways: formulas reproduced from
  the original 2011 roster applied to the season's stats, and The Show's ratings converted by
  rank. The two are blended by sample size, and `report.txt` lists players where the sources
  disagree a lot.
- **Limits:** each new player borrows a similar 2011 player's look and pitch types (those
  fields are not decoded yet). Team names, logos and leagues are built into the game, so
  Houston stays in the NL and Miami appears as Florida. Rosters are taken from the last day of
  the regular season, so injured players are missing.

The downloaded data and the generated rosters stay on your PC (`cache\` and `out\` are not
part of the repository). If MLB The Show's site answers 403 Forbidden, turn off any VPN.

## Building from source

You need:

- The [ReXGlue SDK](#acknowledgements) v0.10.0 (commit `c94f5eb`) with this project's patch
  applied: `sdk-patches/rexglue-sdk-local.patch` (see [`sdk-patches/`](sdk-patches/)). Build
  and install it.
- Visual Studio 2022 or newer with Clang/LLVM, CMake and Ninja
- Your own `default.xex` for each game, placed at `pros\game\extracted\default.xex` and
  `battle\game\extracted\default.xex` (these folders are git-ignored)

From a Visual Studio developer shell:

```powershell
cd pros
cmake --preset win-amd64-release
cmake --build --preset win-amd64-release
cd ..\battle
cmake --preset win-amd64-release
cmake --build --preset win-amd64-release
```

The first build step recompiles the game code (PowerPC to C++) into `generated\`, which is
never committed. Each build produces `bobblehead<pros|battle>.exe` with `rexruntime.dll`,
`rexgpu-xenos.dll` and the `.toml` in `out\build\win-amd64-release\`. To run a build directly,
pass the game folder (the engine reads it before the `.toml`):

```powershell
bobbleheadpros.exe   --game_data_root="D:\path\to\MLB Bobblehead Pros (World) (XBLA)"
bobbleheadbattle.exe --game_data_root="D:\path\to\MLB Bobblehead Battle (World) (XBLA)\extracted"
```

**Launcher:** `csc -target:winexe -out:"MLB Bobblehead Launcher.exe" -r:System.Windows.Forms.dll -r:System.Drawing.dll Launcher.cs`
from `launcher\` (the .NET Framework compiler that comes with Windows).

**Installer:** with both games and the launcher built and
[Inno Setup 6](https://jrsoftware.org/isinfo.php) installed (`winget install JRSoftware.InnoSetup`):

```powershell
installer\build-installer.ps1 -Version 0.1.0   # setup.exe, portable zip, SHA256SUMS.txt in installer\dist\
```

## Android (Pros only, experimental)

Pros can also be built as an Android app (arm64, Android 11+, Vulkan) from your own copy of the
game. **Status:** it builds, installs and boots to the game's loading screen on a test tablet,
but is not playable yet.

1. Apply **both** SDK patches (`sdk-patches/rexglue-sdk-local.patch`, then
   `sdk-patches/rexglue-sdk-android.patch`), build and install the SDK for Windows, and build
   the Windows version of Pros once (that runs the code generator).
2. Install Android Studio and, in its SDK Manager, an **NDK**, **CMake**, build-tools and a
   platform.
3. Build the Android runtime, the game and the APK in one go:

   ```powershell
   powershell -ExecutionPolicy Bypass -File pros\android\build_android.ps1 -SdkSource <rexglue-sdk>
   ```

   This produces `pros\android\out\MLBBobbleheadPros.apk` (`-Install` also runs `adb install`).
4. Install it, open it once, then copy your game files into the app's folder:

   ```powershell
   adb push "<game folder>\default.xex" /sdcard/Android/data/com.mlbbobblehead.pros/files/game/
   adb push "<game folder>\data"        /sdcard/Android/data/com.mlbbobblehead.pros/files/game/
   ```

   Saves go to `files/user` and the log to `files/logs/bobbleheadpros.log`.

Use a Bluetooth or USB controller; there are no touch controls yet. The APK is not part of the
releases: build it yourself.

## Known issues

### Audio

- **Battle has no audio** (no music, sound effects or crowd). The audio is decoded correctly
  but never reaches the final mix: the fault is in Battle's own sound-mixing setup inside the
  recompiled code, which still has to be traced. Battle has audio on real hardware, so this is
  a bug, not intended.
- **Pros audio works** (music, sound effects, commentary).

### Graphics

- **NVIDIA needs the ROV render path** (already set in the included `.toml`; see
  [Requirements](#requirements)). AMD and Intel GPUs have had less testing; if you get a black
  screen, try changing `render_target_path_d3d12`.
- **Crowd lighting can look off** in some stadiums.
- Only the Direct3D 12 backend is built on Windows.

### Online, saves, achievements and DLC

- **No online play.** There are no Xbox Live services behind these ports; the network is
  reported as connected only so the games don't wait for it. Online modes, leaderboards and
  the marketplace don't work.
- **Saves** are written to `Documents\bobbleheadpros\` and have had little testing beyond
  normal play; keep a copy of that folder if your progress matters to you.
- **Achievements:** the Achievements screen opens and closes immediately (it is stubbed to
  avoid a freeze), and nothing is tracked.
- **Bobblehead Stars DLC doesn't load.** The game finds the installed package but never opens
  it; the check that decides this is in the recompiled code and hasn't been found yet. (The Oct
  2011 roster update does work, through the launcher.)

### Performance

- Higher resolution presets cost performance; if a match stutters, choose a lower one in
  Options. Running with `--log_level=debug` also slows the games down (it writes to disk every
  frame), so use it only for troubleshooting.

## Repository layout

```
pros/            ReXGlue project for MLB Bobblehead Pros (manifest, .toml, src/)
pros/android/    Android app shell and build_android.ps1
battle/          ReXGlue project for MLB Bobblehead Battle
launcher/        Windows launcher (Launcher.cs) and box art
installer/       Inno Setup script, icons and build-installer.ps1
tools/roster/    Pros roster format, season builder, data fetchers and research scripts
sdk-patches/     Patches to the ReXGlue SDK this project needs
```

## Acknowledgements

- **ReXGlue**: the static PowerPC-to-C++ recompiler and runtime this project is built on.
- **[Xenia](https://xenia.jp/)** (Ben Vanik and contributors): the kernel, GPU (Xenos) and XMA
  audio implementations the runtime derives from, under the BSD license.
- **[SABR's Lahman Baseball Database](https://sabr.org/lahman-database/)**: used to decode and
  calibrate the roster format.
- The season builder reads public data from the **MLB Stats API** and **MLB The Show**'s player
  ratings site on your own PC; that data belongs to its owners and is not redistributed here.
- **Konami**: the original *MLB Bobblehead Pros* and *MLB Bobblehead Battle* (2011).

## Legal

This is an unofficial fan project for preservation and research. It is **not affiliated with,
endorsed by or sponsored by** Konami, Major League Baseball, MLB Players, Sony Interactive
Entertainment or Microsoft.

The release executables contain program code automatically recompiled from each game's
original `default.xex`. They contain **no game data**: graphics, models, audio, text and
rosters are loaded from the copy you supply, and the executables do nothing without it. To use
this project you need your own legally obtained copy of each game. The source repository
contains no game code or data. If you are a rights holder with a concern, please open an issue.

MLB, team names and logos, player names and likenesses, and the games' titles and box art are
the property of their respective owners.

This project's own code (the recompilation configuration, launcher, installer, roster tools and
SDK patches) is released under the [MIT License](LICENSE). It builds on BSD-licensed code from
Xenia and the ReXGlue runtime, which remain under their own licenses.
