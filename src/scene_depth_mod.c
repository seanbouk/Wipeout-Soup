/* Wipeout Soup presentation plugin: scene depth and motion vectors for
 * post-process tools. The renderer and GTE do the work; this arms them and,
 * for motion, tells the framework where Wipeout's camera lives (the render
 * clock is the display flip, in the framework; docs/soup/motion-vectors-phase0.md). */
#include "mod_plugins.h"
#include "cpu_state.h"
#include "gpu_gl_renderer.h"
#include "motion_vectors.h"
#include <string.h>

#define PKG "soup.presentation.scene-depth"

static int in_ram(uint32_t address, uint32_t bytes) {
    uint32_t p = address & 0x1fffffffu;
    return p >= 0x10000u && p <= 0x200000u && bytes <= 0x200000u - p;
}

/* Scenery renderers (0x80013C78, 0x800140AC, 0x80014AD4) take the camera
 * offset node in a1; its parent (+0x44) is the root camera node. Rotation at
 * root+0, offset (= -camera position) at node+0x14. Same reading as upstream's
 * track_distance_experimental.c capture_camera. */
static void note_camera(CPUState *cpu, uint32_t address) {
    (void)address;
    uint32_t node = cpu->gpr[5];
    if (!in_ram(node, 0x48)) return;
    uint32_t root = psx_mod_read_word(node + 0x44);
    if (!in_ram(root, 0x48) || psx_mod_read_word(root + 0x44)) return;
    psx_mv_set_camera(root, node + 0x14);
}

static void activate_scene_depth(void) {
    gl_renderer_set_depth_output(1);
    char motion[16] = "false";
    psx_mod_option_value(PKG, "scene-depth", "motion", motion, sizeof motion);
    if (!strcmp(motion, "true")) {
        gl_renderer_set_motion_output(1);
        psx_mv_enable(1);
        psx_mod_register_function_entry_plugin("soup.scene-depth", 0x80013c78u, note_camera);
        psx_mod_register_function_entry_plugin("soup.scene-depth", 0x800140acu, note_camera);
        psx_mod_register_function_entry_plugin("soup.scene-depth", 0x80014ad4u, note_camera);
    }
}
PSX_MOD_CONSTRUCTOR(register_soup_scene_depth) {
    psx_mod_register_activation_plugin("soup.scene-depth", activate_scene_depth);
}
