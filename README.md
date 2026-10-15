# MLB Bobblehead Recomp

Native PC (Windows) ports of the two Xbox 360 **MLB Bobblehead** games, produced by
**static recompilation** with [ReXGlue](#acknowledgements) — the original PowerPC game code
is translated ahead-of-time into C++ and compiled to a native x64 executable that runs on a
Xenia‑derived runtime. No emulator and no original game binary are needed at run time.

| Game | Title ID | Status |
|------|----------|--------|
| **MLB Bobblehead Pros** | `58410B7B` | ▶️ Playable — boots to the main menu and into a full game, full (non‑trial) version, keyboard controls, **with audio** |
| **MLB Bobblehead Battle** | `58410B7C` | ▶️ Playable — boots to the main menu and into a full game, full (non‑trial) version, keyboard controls. **Known issue: no audio** (see [Known issues](#known-issues)) |

> ⚠️ **This is a work‑in‑progress preservation/research project.** Expect rough edges:
> placeholder‑quality distant player faces, occasional crowd lighting artifacts, and the
> Battle audio gap noted below.

---

## ❗ You must provide your own game files

This repository contains **only the recompilation project** — manifests, the list of
manually‑recovered functions, runtime settings, SDK patches, and build glue. It contains
**no game code and no game assets**. To build and play you need your own legally‑obtained
copy of each title, dumped from your Xbox 360.

Nothing here distributes Konami/MLB copyrighted content, and none of it should ever be
committed to this repo (see `.gitignore`).

---

## Requirements

**To run:**
- Windows 10/11, 64‑bit
- A Direct3D 12‑capable GPU
  - On **NVIDIA** GPUs the default render path renders black — the included configs already
    select the ROV path (`render_target_path_d3d12 = "rov"`); keep it.
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
`--game_data_root` (below). If you also own the **roster update** and **DLC** add‑ons, extract
their data files into the same `cdvdroot` tree.

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
- an options panel (vsync, keyboard mode, fullscreen, resolution scale) that writes straight
  into each game's `.toml`.

Build it with the .NET Framework compiler (no CMake needed):

```bash
# from launcher/
csc -target:winexe -out:"MLB Bobblehead Launcher.exe" Launcher.cs
```

The cards use box art from `launcher/art/<game>.png` if present and otherwise fall back to the
game's own `TitleIcon.png`. The art is **not** included here (it's copyrighted store artwork) —
drop your own `pros.png` / `battle.png` into `launcher/art/` if you want it. The launcher
remembers your game locations in a local `launcher.cfg`.

## Known issues

These are the rough edges in this first release. None of them prevent getting into and
playing a full game; most are either cosmetic or affect secondary features (online, saves,
achievements).

### Audio

- **Battle has no audio at all** (menu music, SFX, crowd — nothing). This is fully diagnosed.
  The audio stack works end to end: the sound banks load, the voice object is created and
  passes its own integrity checks, and the audio engine runs every frame. The gap is purely
  that Battle's high‑level game logic **never issues a "play" request** — the voice sits idle
  with an empty request queue, so it never spins up the XMA decoder and never produces sound.
  Pros, which runs on the same engine, triggers playback normally, so this is specific to how
  Battle's recompiled game code drives its sound manager. On real hardware Battle *does* have
  music, so this is a bug to fix, not intended behavior. Investigation is paused, not abandoned.
- **Pros audio works** (menu music, SFX, commentary).

### Graphics

- **NVIDIA GPUs need the ROV render path.** On NVIDIA the default render target path renders a
  black screen; the shipped configs already set `render_target_path_d3d12 = "rov"`, which fixes
  it. Leave that setting in place. AMD/Intel GPUs have had less testing — if you get a black
  frontend, try toggling that setting.
- **Distant player models look low quality** and faces can appear blurry/placeholder‑ish when
  the camera is far away.
- **Crowd lighting can look off** (flat or oddly lit spectators) in some stadiums.
- Vulkan is **not** available — only the Direct3D 12 backend is built.

### Input

- **Menu navigation can need a firm, slightly held key press.** Very quick taps (especially
  Start/Enter and the A button) are sometimes missed by the frontend; hold the key for a beat.
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
- **DLC / roster updates are data‑only.** The add‑on files can be dropped into the game's
  `cdvdroot` tree, but they have not been fully wired into the loading flow and are untested in
  this release.

### Performance

- Rendering resolution is controlled per game by `resolution_scale` in the `.toml` (Pros ships
  at `2`, Battle at `1`). Raising it sharpens the image but costs performance; if a match runs
  slow or stutters, lower it. Running with `--log_level=debug` also slows things down (per‑frame
  disk writes) — only use it for troubleshooting.

## Repository layout

```
pros/           ReXGlue project for MLB Bobblehead Pros   (manifest, functions, .toml, src/)
battle/         ReXGlue project for MLB Bobblehead Battle
launcher/       Windows launcher (C# / WinForms) + box art
sdk-patches/    Local patches to the ReXGlue SDK required to boot and play
```

Not tracked (regenerated or user‑supplied): `generated/`, build output under `out/`/`build/`,
any `game/` data, and every `*.xex`.

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
