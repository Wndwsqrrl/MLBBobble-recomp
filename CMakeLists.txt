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
)

if(WIN32)
    add_executable(bobbleheadpros WIN32 ${BOBBLEHEADPROS_SOURCES})
else()
    add_executable(bobbleheadpros ${BOBBLEHEADPROS_SOURCES})
endif()

rexglue_setup_target(bobbleheadpros GPU_PLUGINS xenos)

# Default settings, read by the runtime from the executable's folder.
add_custom_command(TARGET bobbleheadpros POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/bobbleheadpros.toml
        $<TARGET_FILE_DIR:bobbleheadpros>/bobbleheadpros.toml
    VERBATIM
)
