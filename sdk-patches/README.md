# ReXGlue SDK local patches

`rexglue-sdk-local.patch` holds the local modifications to the ReXGlue SDK
(based on upstream tag `v0.10.0`, commit `c94f5eb`) that this recomp needs to
boot and play. The SDK lives in a separate tree (clone `rexglue/rexglue-sdk` at
`c94f5eb`); these changes are not part of its upstream.

Apply from the SDK root:

    cd <your rexglue-sdk checkout>
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
- `src/ui/d3d12/d3d12_provider.cpp` — when no adapter is forced (`d3d12_adapter`
  = -1, the default), pick the system's **high-performance** GPU via DXGI 1.6
  (`EnumAdapterByGpuPreference`) so hybrid laptops render on the discrete GPU
  instead of the integrated one. (The matching NvOptimus/AMD exports live in
  each game's `src/main.cpp`, because they are only honored from the exe.)
- `src/kernel/xam/xam_content.cpp`, `xam_content_aggregate.cpp` — report one
  dummy savegame when none exists so the game stops looping the storage
  selector at the splash and reaches the main menu.
- `src/kernel/xam/xam_ui.cpp` — implement `XamShowAchievementsUI` as a headless
  open/close so the Achievements menu item no longer freezes.
- `cmake/rexglue_install.cmake` — skip the CMake user-package-registry entry for
  cross-compiled installs (Android/iOS). Otherwise a later Windows configure can
  find the Android prefix and fail; cross builds pass `rexglue_DIR` explicitly.

## Critical runtime setting (not an SDK patch)
On this NVIDIA GPU the game renders black on the default RTV path. The fix lives
in `bobbleheadpros.toml`: `render_target_path_d3d12 = "rov"`.
