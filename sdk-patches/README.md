# ReXGlue SDK local patches

`rexglue-sdk-local.patch` holds the local modifications to the ReXGlue SDK
(based on upstream tag `v0.10.0`, commit `c94f5eb`) that this recomp needs to
boot and play. The SDK lives in a separate tree (`F:\tools\rexglue-sdk`); these
changes are not part of its upstream.

Apply from the SDK root:

    cd F:\tools\rexglue-sdk
    git apply /path/to/rexglue-sdk-local.patch

Then rebuild + reinstall the SDK and rebuild the app:

    cmake --build  out/build/win-amd64 --config Release
    cmake --install out/build/win-amd64 --config Release
    cmake --build --preset win-amd64-release   # from this repo

## What each change does
- `src/kernel/xboxkrnl/xboxkrnl_video.cpp`, `src/input/input_system.*`,
  `src/codegen/builders/vector.cpp` — pre-existing setup fixes (input lock,
  vector builder) carried from SDK install.
- `src/ui/rex_app.cpp` — adds a `gpu_backend` cvar (any/d3d12/vulkan).
- `src/kernel/xam/xam_content.cpp`, `xam_content_aggregate.cpp` — report one
  dummy savegame when none exists so the game stops looping the storage
  selector at the splash and reaches the main menu.
- `src/kernel/xam/xam_ui.cpp` — implement `XamShowAchievementsUI` as a headless
  open/close so the Achievements menu item no longer freezes.
- `src/ui/presenter.cpp` — a debug guest-output screenshot triggered by the
  sentinel file `F:/bobblehead-recomp/out/SHOOT` (writes `out/guest.bmp`).
  Diagnostic only; safe to drop.

## Critical runtime setting (not an SDK patch)
On this NVIDIA GPU the game renders black on the default RTV path. The fix lives
in `bobbleheadpros.toml`: `render_target_path_d3d12 = "rov"`.
