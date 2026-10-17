cmake_minimum_required(VERSION 3.20)
set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH
    "Path to psxrecomp")
if(NOT EXISTS "${PSXRECOMP_ROOT}/runtime/runtime.cmake")
    message(FATAL_ERROR
        "PSXRecomp runtime is missing: ${PSXRECOMP_ROOT}/runtime/runtime.cmake\n"
        "This project expects the psxrecomp framework checkout at ${PSXRECOMP_ROOT}.\n"
        "Run: git submodule update --init --recursive\n"
        "If psxrecomp/ is not a submodule, set -DPSXRECOMP_ROOT=<path-to-psxrecomp>.")
endif()

project(Wipeout2K97XL LANGUAGES C CXX)

# --- Opt-in product surfaces (OFF by default in the framework) -------------
# Scaffold prompts / flags fill these. Without recomp-ui, PSX_RECOMP_UI is OFF.
# Setup-host CI requires WIZARD_CMAKE_BLOCK / ENABLE_SETUP_WIZARD (FORCE_SETUP_HOST
# alone does not open first-run / Generate & rebuild).
# recomp-ui submodule present (PSX_RECOMP_UI defaults ON).
# Full netplay UI -- enable after adding recomp-ui + testing:
# if(EXISTS "${PSXRECOMP_ROOT}/lib/recomp-net/CMakeLists.txt")
#     set(PSX_NETPLAY ON CACHE BOOL "..." FORCE)
# endif()
set(PSX_SETUP_WIZARD ON CACHE BOOL
    "Advertise first-run setup wizard + Generate & rebuild in recomp-ui" FORCE)
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

# This project's own mod catalog. The FRAMEWORK stages it -- together with its
# builtin psx.* packages -- into <exe-dir>/mods/bundled, and refuses to
# configure if a catalog exists here but is not declared. Never copy it by
# hand: five titles did, and framework 4cc04be3's rename of the staged
# directory broke all five silently (bead beads-eio.3.101).
set(PSX_PRELOADED_MODS "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded")
if(NOT IS_DIRECTORY "${PSX_PRELOADED_MODS}")
    set(PSX_PRELOADED_MODS "NONE")
endif()

# Wipeout Soup: compile the game with the PGXP hooks (-DPSX_PGXP=1). The base
# build only catches ~10% of vertices for PGXP; this one tracks nearly all of
# them, which Scene Depth needs and the PGXP Precision mod benefits from.
# Measured at no frame-time cost. The PGXP mods stay opt-in either way.
option(SOUP_FULL_PGXP "Build the game with full PGXP coverage" ON)
set(_soup_pgxp_arg)
if(SOUP_FULL_PGXP)
    set(_soup_pgxp_arg PGXP)
endif()

psxrecomp_add_game_runtime(psx-runtime
    ${_soup_pgxp_arg}
    PRELOADED_MODS_DIR "${PSX_PRELOADED_MODS}"
    # ENABLE_NETPLAY_IF_PRESENT
    # NETPLAY_LOBBY_URL "ws://netplay.retcomm.net:8765"
    ENABLE_SETUP_WIZARD
    WINDOW_TITLE "Wipeout2K97XL"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 1
    APP_ICON "${CMAKE_CURRENT_SOURCE_DIR}/assets/psxrecomp.ico"
    GEN_MARKER "generated/SCUS_943.51_dispatch.c"
    GEN_FULL_GLOB "generated/SCUS_943.51_full_*.c"
    CODEGEN_SETUP_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/codegen_setup.c"
)

# Stage runtime configs next to the exe for direct build/ launches. Only copy
# files that exist â€” never fail POST_BUILD when game_options.toml is absent.
foreach(_PSX_RUNTIME_CONFIG game.toml game_options.toml)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}")
        add_custom_command(TARGET psx-runtime POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}"
                "$<TARGET_FILE_DIR:psx-runtime>/${_PSX_RUNTIME_CONFIG}"
            COMMENT "Staging ${_PSX_RUNTIME_CONFIG}"
            VERBATIM)
    endif()
endforeach()

# Seed input preferences only once; preserve player rebindings on rebuild.
add_custom_command(TARGET psx-runtime POST_BUILD
    COMMAND ${CMAKE_COMMAND}
        "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}"
        "-DDESTINATION=$<TARGET_FILE_DIR:psx-runtime>"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/tools/stage_input_defaults.cmake"
    VERBATIM)

# Trusted presentation-only plugin; the launcher selects its preset.
target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/crt_mod.c")

target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/widescreen_mod.c")

# Wipeout Soup: scene depth for post-process tools (ReShade).
target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/scene_depth_mod.c")

# Wipeout Soup: Vulkan presenter (Windows). The framework's vk_presenter.c is
# inert unless PSX_VK_PRESENTER is defined; it needs only the vendored Vulkan
# headers (the loader comes with the driver).
if(WIN32)
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/vulkan_presenter_mod.c")
    target_include_directories(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/third_party/vulkan-headers/include")
    target_compile_definitions(psx-runtime PRIVATE PSX_VK_PRESENTER=1)
endif()

target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/track_distance_experimental.c")

target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/ship_distance_mod.c")

target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/negcon_mod.c")

# Wipeout Soup: -DPSX_PGXP_VARIANT=ON clones psx-runtime as psx-runtime-pgxp
# (full PGXP coverage, which Scene Depth needs). Give it the same plugins, or it
# refuses to launch with any of these mods selected.
if(TARGET psx-runtime-pgxp)
    target_sources(psx-runtime-pgxp PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src/crt_mod.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/widescreen_mod.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/scene_depth_mod.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/track_distance_experimental.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/ship_distance_mod.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/negcon_mod.c")
    if(WIN32)
        target_sources(psx-runtime-pgxp PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src/vulkan_presenter_mod.c")
        target_include_directories(psx-runtime-pgxp PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/third_party/vulkan-headers/include")
        target_compile_definitions(psx-runtime-pgxp PRIVATE PSX_VK_PRESENTER=1)
    endif()
endif()
