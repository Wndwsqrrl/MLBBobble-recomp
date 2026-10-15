# bobbleheadbattle - ReXGlue Recompiled Project
#
# SDK boilerplate lives in generated/rexglue.cmake.

cmake_minimum_required(VERSION 3.25)
project(bobbleheadbattle LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(generated/rexglue.cmake)

# Sources
set(BOBBLEHEADBATTLE_SOURCES
    src/main.cpp
)

if(WIN32)
    add_executable(bobbleheadbattle WIN32 ${BOBBLEHEADBATTLE_SOURCES})
else()
    add_executable(bobbleheadbattle ${BOBBLEHEADBATTLE_SOURCES})
endif()

rexglue_setup_target(bobbleheadbattle GPU_PLUGINS xenos)

# Default settings, read by the runtime from the executable's folder.
add_custom_command(TARGET bobbleheadbattle POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_CURRENT_SOURCE_DIR}/bobbleheadbattle.toml
        $<TARGET_FILE_DIR:bobbleheadbattle>/bobbleheadbattle.toml
    VERBATIM
)
