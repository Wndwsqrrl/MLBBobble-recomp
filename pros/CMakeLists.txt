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
    # Android has no executables for apps: SDL's Java activity loads the game as
    # libmain.so and calls its SDL_main (see android/).
    add_library(bobbleheadpros SHARED ${BOBBLEHEADPROS_SOURCES})
    set_target_properties(bobbleheadpros PROPERTIES OUTPUT_NAME main)
    target_link_libraries(bobbleheadpros PRIVATE android log)
else()
    add_executable(bobbleheadpros ${BOBBLEHEADPROS_SOURCES})
endif()

rexglue_setup_target(bobbleheadpros GPU_PLUGINS xenos)

if(ANDROID)
    # The codegen step runs the rexglue tool on the build machine. The Android SDK
    # install's copy is an Android binary, so point the step at the Windows SDK's
    # rexglue.exe instead (android/build_android.ps1 passes it). The output is plain
    # C++, the same for every target.
    set(REXGLUE_HOST_TOOL "" CACHE FILEPATH "rexglue executable that runs on the build machine")
    if(NOT EXISTS "${REXGLUE_HOST_TOOL}")
        message(FATAL_ERROR "Set REXGLUE_HOST_TOOL to the Windows SDK's bin/rexglue.exe "
                            "(android/build_android.ps1 does this).")
    endif()
    set_target_properties(rex::rexglue PROPERTIES
        IMPORTED_LOCATION "${REXGLUE_HOST_TOOL}"
        IMPORTED_LOCATION_RELEASE "${REXGLUE_HOST_TOOL}"
        IMPORTED_LOCATION_DEBUG "${REXGLUE_HOST_TOOL}")
endif()

# Default settings, read by the runtime from the executable's folder.
add_custom_command(TARGET bobbleheadpros POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/bobbleheadpros.toml
        $<TARGET_FILE_DIR:bobbleheadpros>/bobbleheadpros.toml
    VERBATIM
)
