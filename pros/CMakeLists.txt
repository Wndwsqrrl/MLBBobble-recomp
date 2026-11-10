# bobbleheadpros - ReXGlue Recompiled Project
#
# SDK boilerplate lives in generated/rexglue.cmake.

cmake_minimum_required(VERSION 3.25)
project(bobbleheadpros LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(generated/rexglue.cmake)

# Sources
set(BOBBLEHEADPROS_SOURCES
    src/main.cpp
    src/trace_hooks.cpp
)

if(WIN32)
    add_executable(bobbleheadpros WIN32 ${BOBBLEHEADPROS_SOURCES})
elseif(ANDROID)
    # Android: the game is libmain.so, which SDL3's GameActivity loads and whose
    # SDL_main it calls (see tools/android). A shared library.
    add_library(bobbleheadpros SHARED ${BOBBLEHEADPROS_SOURCES})
    set_target_properties(bobbleheadpros PROPERTIES OUTPUT_NAME main)
    target_link_libraries(bobbleheadpros PRIVATE android log)
else()
    add_executable(bobbleheadpros ${BOBBLEHEADPROS_SOURCES})
endif()

rexglue_setup_target(bobbleheadpros GPU_PLUGINS xenos)

if(ANDROID)
    # Codegen (rexglue) is a BUILD-HOST tool that emits architecture-independent C++;
    # the rex::rexglue imported target in the android-arm64 SDK install is an arm64
    # binary the host can't run. Repoint it at the host (win-amd64) rexglue.exe so the
    # codegen custom command runs natively. The genex $<TARGET_FILE:rex::rexglue> is
    # resolved at generation time, so overriding the location here takes effect.
    set(REXGLUE_HOST_TOOL "D:/recomp-work/rexglue-sdk/out/install/win-amd64/bin/rexglue.exe"
        CACHE FILEPATH "Host rexglue codegen executable (native to the build machine)")
    if(TARGET rex::rexglue AND EXISTS "${REXGLUE_HOST_TOOL}")
        set_target_properties(rex::rexglue PROPERTIES
            IMPORTED_LOCATION "${REXGLUE_HOST_TOOL}"
            IMPORTED_LOCATION_RELEASE "${REXGLUE_HOST_TOOL}"
            IMPORTED_LOCATION_DEBUG "${REXGLUE_HOST_TOOL}")
    endif()

    # Phones: baseline is armv8.2-a (LSE atomics, RCpc, dot product); every Snapdragon
    # 845 (2018) and newer has them. Bind recompiled calls locally (no PLT hop).
    set(BOBBLEHEADPROS_ARM64_MARCH "armv8.2-a+lse+rcpc+dotprod" CACHE STRING "-march for Android game code")
    foreach(_t bobbleheadpros bobbleheadpros_recomp)
        if(TARGET ${_t})
            target_compile_options(${_t} PRIVATE -march=${BOBBLEHEADPROS_ARM64_MARCH} -fno-semantic-interposition)
        endif()
    endforeach()
    target_link_options(bobbleheadpros PRIVATE -Wl,-Bsymbolic-functions)
    # The generated registration function (one call per game function) is slow to optimize
    # on clang's arm64 backend and runs once at startup: build it unoptimized.
    set_source_files_properties(${CMAKE_CURRENT_SOURCE_DIR}/generated/default/bobbleheadpros_register.cpp
        PROPERTIES COMPILE_OPTIONS "-O0;-fno-global-isel" SKIP_PRECOMPILE_HEADERS ON)
endif()

# Default settings, read by the runtime from the executable's folder.
add_custom_command(TARGET bobbleheadpros POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/bobbleheadpros.toml
        $<TARGET_FILE_DIR:bobbleheadpros>/bobbleheadpros.toml
    VERBATIM
)
