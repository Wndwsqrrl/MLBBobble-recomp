# MLB Bobblehead Recomp

[![Download](https://img.shields.io/github/v/release/Wndwsqrrl/MLBBobble-recomp?label=Download&color=6d4bd6)](https://github.com/Wndwsqrrl/MLBBobble-recomp/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Wndwsqrrl/MLBBobble-recomp/total?label=Downloads&color=6d4bd6)](https://github.com/Wndwsqrrl/MLBBobble-recomp/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-6d4bd6)](LICENSE)

Native PC (Windows) ports of the two Xbox 360 **MLB Bobblehead** games, produced by
**static recompilation** with [ReXGlue](#acknowledgements) — the original PowerPC game code
is translated ahead-of-time into C++ and compiled to a native x64 executable that runs on a
Xenia‑derived runtime. No emulator and no original game binary are needed at run time.

| Game | Title ID | Status |
|------|----------|--------|
| **MLB Bobblehead Pros** | `58410B7B` | ▶️ Playable — menu → full match, full version, keyboard · |
| **MLB Bobblehead Battle** | `58410B7C` | ▶️ Playable — menu → full match, full version, keyboard · ⚠️ **no audio** ([details](#known-issues)) |

> ⚠️ **Work‑in‑progress preservation/research project.** You can boot both games and play a
> full match, but expect rough edges — see [Known issues](#known-issues).

## Contents

- [Bring your own game files](#bring-your-own-game-files)
- [Requirements](#requirements)
- [Getting your game files](#getting-your-game-files)
- [Building](#building) · [Running](#running) · [Controls](#controls-keyboard)
- [Launcher](#launcher)
- [Known issues](#known-issues)
- [Repository layout](#repository-layout) · [Acknowledgements](#acknowledgements) · [Legal](#legal)

---

## Bring your own game files

This repository contains **only the recompilation project** — To build and play you need your own legally‑obtained
copy of each title, dumped from your Xbox 360.

---

## Requirements

**To run:**
- Windows 10/11, 64‑bit
- A Direct3D 12‑capable GPU
  - On **NVIDIA** GPUs the default render path renders black — the included configs already
    select the ROV path (`render_target_path_d3d12 = "rov"`); keep it.
  - On **hybrid laptops** (integrated + discrete GPU) the game now auto‑selects the
    high‑performance (discrete) GPU, so no per‑app Windows graphics preference is needed.
    To force a specific adapter anyway, set `d3d12_adapter` (0‑based index) in the `.toml`.
- Your extracted game data (below)

**To build:**
- [ReXGlue SDK](#acknowledgements) v0.10.0.x, built and installed (registers itself in CMake's
  package registry). Apply the local patches in [`sdk-patches/`](sdk-patches/) first — they are
  required to boot and play (save‑loop fix, headless achievements, full‑version license fallback,
  ROV cvar, etc.).
- Visual Studio 2022 or newer with the bundled **Clang/LLVM**, **CMake**, and **Ninja**
  (this project is developed with VS 18 / Clang 22, MSVC 14.5x, Windows SDK 10.0.26100+).

## Getting your game files

Each game ships as an Xbox Live Arcade **STFS/CON** package. Extract it so you end up with the
title's `default.xex` and its `data/` tree, e.g.:

```
<your dump>/
 ├─ default.xex
 └─ data/xbox360_us/cdvdroot/...     (models, textures, sound/, …)
```

Any STFS extractor works. Point the recomp at the folder that contains `default.xex` via
`--game_data_root` (below). If you own the **Oct 2011 roster update** for Pros, install it
from the launcher's Setup screen (see [Launcher](#launcher)) rather than copying files by hand.

## Building

Each game is an independent ReXGlue project. From a Visual Studio developer shell (so Clang,
CMake and Ninja are on `PATH`):

```bash
# Pros
cd pros
cmake --preset win-amd64-release
cmake --build --preset win-amd64-release

# Battle
cd ../battle
cmake --preset win-amd64-release
cmake --build --preset win-amd64-release
```

Code generation (PPC → C++) runs automatically as the first build step and produces the
`generated/` tree locally; it is intentionally **not** committed. The build outputs
`bobblehead<pros|battle>.exe` plus `rexruntime.dll`, `rexgpu-xenos.dll`, and the game's `.toml`
next to the exe in `out/build/win-amd64-release/`.

## Running

The engine reads the game data root **before** it loads the `.toml`, so it must be passed on the
command line:

```bash
bobbleheadpros.exe   --game_data_root="D:\path\to\MLB Bobblehead Pros (World) (XBLA)"
bobbleheadbattle.exe --game_data_root="D:\path\to\MLB Bobblehead Battle (World) (XBLA)\extracted"
```

The generated `Play MLB Bobblehead *.bat` next to each exe does this for you. All other runtime
options live in the game's `.toml` (`license_mask`, `render_target_path_d3d12`, `mnk_mode`,
`resolution_scale`, …). Logs are written to `<exe dir>/logs/`.

## Controls (keyboard)

Keyboard‑and‑mouse mode (`mnk_mode = true`) maps the Xbox pad to the keyboard. Menu inputs
sometimes need a **firm, slightly long press**.

| Xbox pad | Keyboard |
|----------|----------|
| Start | Enter |
| A | Space |
| B | Backspace |
| X | L |
| Y | P |
| Left stick / move | W A S D |
| D‑pad | Shift + Arrow keys |
| Back | Z or Tab |

A standard XInput controller also works.

## Launcher

[`launcher/`](launcher/) is a small Windows launcher (C# / WinForms) that ties both games
together:
- side‑by‑side game cards, greyed out until a game is installed,
- a first‑run setup/installed‑checker that walks you through locating each game's files,
- **Pros rosters by season:** Setup → *Pros roster* switches between every roster in the
  game folder's roster library (`<game>\_rosters\`): *2011 Opening Day (original)*, *2011 End of
  season (Oct 2011 update)*, and any custom season you add. *Import…* takes your own copy of the
  Oct 2011 roster package (extract the `.7z`, then choose the file inside `58410B7B\00000002\`;
  the launcher reads the Xbox content package itself) or a folder holding a
  `PLAYER_DATA.CHK` + `SEASON_PLAYER_DATA.CHK` pair. The roster already in the game folder is
  always saved to the library before switching, so nothing is lost. With the Oct 2011 roster in
  use, the game shows the update icon in the corner of the splash screen,
- an options panel (vsync, keyboard mode, fullscreen, and host‑side resolution — 720p/1080p/
  1440p/4k, where a preset above your panel downsamples for sharpness) that writes straight
  into each game's `.toml`.

Build it with the .NET Framework compiler (no CMake needed):

```bash
# from launcher/
csc -target:winexe -out:"MLB Bobblehead Launcher.exe" Launcher.cs
```

The cards use the box art in `launcher/art/<game>.png` (`pros.png` / `battle.png`, the games'
Xbox 360 store art), falling back to each game's own `TitleIcon.png` if a file is missing.
Swap in your own `pros.png` / `battle.png` to re-skin the cards. The launcher remembers your
game locations in a local `launcher.cfg`.

The launcher also accepts `--play pros` / `--play battle` to start a game directly (this is how
the installed shortcuts launch each title); if that game isn't set up yet it opens the launcher
so you can locate its files.

## Installer

[`installer/`](installer/) packages the launcher + both recompiled games into a Windows
installer ([Inno Setup](https://jrsoftware.org/isinfo.php)) plus a portable zip. The installer
puts everything in `Program Files`, adds **MLB Bobblehead Pros** and **MLB Bobblehead Battle**
to the Start menu (and optionally the desktop), each with its own logo, lists both in
*Settings → Installed apps* / *Programs and Features*, and registers a single uninstaller.
The games still bring their own data — on first launch each shortcut opens the launcher's
setup so you can point it at your extracted game files.

Build the release artifacts (needs the games and launcher already built, and Inno Setup 6
installed — `winget install JRSoftware.InnoSetup`):

```powershell
# from installer/ — builds setup.exe + portable.zip + SHA256SUMS.txt into installer\dist\:
.\build-installer.ps1 -Version 1.0.0
```

The app icons (`installer/assets/*.ico`) are committed. To regenerate them from your own game
data's `TitleIcon.png` instead, run `make-icons.ps1` first. Only `installer/dist/` (the built
setup.exe / zip) is git-ignored.

## Known issues

These are the rough edges in this first release. None of them prevent getting into and
playing a full game; most are either cosmetic or affect secondary features (online, saves,
achievements).

### Audio

- **Battle has no audio at all** (menu music, SFX, crowd — nothing). Root cause is now
  localized (updated 2026‑10‑30); the earlier "never issues a play request / idle voice"
  diagnosis was **wrong**. Instrumenting the audio engine shows Battle *does* kick its XMA
  context and the decoder *does* run, producing real full‑scale PCM (measured peak ~1.0, same
  as Pros), and the game *consumes* that decoded output (the XMA output ring's read offset
  tracks the write offset). Yet every frame submitted to the render driver is pure silence
  (measured peak 0.0 across thousands of frames, including during an actual match). Tracing the
  render output path in the recompiled code — `sub_8226F2A0` → `sub_8226F0C0` (de‑interleaves
  the mixed‑output buffer at `[driver+24]`, 6ch×256), then `sub_8226EE78` (ring copy, no gain),
  then `XAudioSubmitRenderDriverFrame` — shows **nothing in the output path attenuates audio**,
  so the XAudio2 mixed‑output buffer is *already silent* before submission. The fault is
  therefore upstream, in Battle's guest‑side XAudio2 voice‑mixing graph: the decoded music is
  never summed into the mastering mix (a source voice muted, never started, or not routed to the
  mastering voice). Pros, on the identical engine, mixes through normally (decoded ~1.1 → mix
  ~0.65). **Next step for a future push:** find where `[driver+24]` is written (the mastering
  mix accumulator) and work back to the source voice that should carry the decoded XMA. On real
  hardware Battle *does* have music, so this is a bug to fix, not intended behavior.
- **Pros audio works** (menu music, SFX, commentary).

### Graphics

- **NVIDIA GPUs need the ROV render path.** On NVIDIA the default render target path renders a
  black screen; the shipped configs already set `render_target_path_d3d12 = "rov"`, which fixes
  it. Leave that setting in place. AMD/Intel GPUs have had less testing — if you get a black
  frontend, try toggling that setting.
- **Crowd lighting can look off** (flat or oddly lit spectators) in some stadiums.
- Vulkan is **not** available — only the Direct3D 12 backend is built.

### Input

- A standard XInput controller works alongside the keyboard mapping.

### Online, saves, achievements, and other system features

- **No online / Xbox Live.** There are no live services behind this port; the network link is
  forced "connected" only so the games stop waiting on it at boot. Xbox LIVE menus, online
  multiplayer, leaderboards, and downloadable‑content purchases are **non‑functional**.
- **Save/load is stubbed.** The storage prompt is satisfied with a placeholder save so the
  games can reach the menu, but **persistent progression is not guaranteed** — season progress,
  created players/teams, and unlocks may not survive between sessions.
- **Achievements are headless.** The Achievements screen opens and closes immediately (it is
  stubbed to prevent a freeze that happened when the real Xbox achievements blade was invoked),
  so there is no achievement UI and nothing is unlocked/tracked.
- **Bobblehead Stars DLC doesn't load yet.** The game lists the installed package but never
  opens it; the check that decides this is inside the recompiled game code and hasn't been
  found yet. (The Oct 2011 **roster update** works — install it from the launcher.)

### Performance

- Rendering resolution is controlled per game by `resolution_scale` in the `.toml` (Pros ships
  at `2`, Battle at `1`). Raising it sharpens the image but costs performance; if a match runs
  slow or stutters, lower it. Running with `--log_level=debug` also slows things down (per‑frame
  disk writes) — only use it for troubleshooting.

## Repository layout

```
pros/           ReXGlue project for MLB Bobblehead Pros   (manifest, functions, .toml, src/)
battle/         ReXGlue project for MLB Bobblehead Battle
launcher/       Windows launcher (C# / WinForms) — Launcher.cs
sdk-patches/    Local patches to the ReXGlue SDK required to boot and play
```

## Acknowledgements

- **ReXGlue** — the static PowerPC→C++ recompiler and runtime this project is built on.
- **[Xenia](https://xenia.jp/)** (Ben Vanik and contributors) — the kernel, GPU (Xenos) and
  XMA audio implementations the runtime derives from, under the BSD license.
- **Konami / PowerPros** — the original *MLB Bobblehead Pros* and *MLB Bobblehead Battle* (2011).

## Legal

This project is for game preservation and research. It is **not affiliated with, endorsed by,
or sponsored by** Konami, Major League Baseball, or Microsoft. It distributes no copyrighted
game code or assets — you must supply your own legally‑obtained copies of the games. All
trademarks are the property of their respective owners.

The project's own code (recompilation configs, launcher, and SDK patches) is released under
the [MIT License](LICENSE). It builds on BSD‑licensed code from Xenia and the ReXGlue runtime;
those components remain under their own licenses.
