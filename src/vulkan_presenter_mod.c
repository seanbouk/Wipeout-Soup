/* Wipeout Soup presentation plugin: present through Vulkan instead of OpenGL's
 * own swap (the groundwork for Streamline/DLSS, docs/soup/streamline-plan.md).
 * The renderer does the work (gl_renderer_set_vulkan_presenter); it falls back
 * to OpenGL by itself if Vulkan can't start. */
#include "mod_plugins.h"
#include "gpu_gl_renderer.h"
#include <string.h>

void soup_arm_scene_motion(void);   /* scene_depth_mod.c */

static void activate_vulkan_presenter(void) {
    gl_renderer_set_vulkan_presenter(1);
    /* DLSS needs the scene's depth and motion vectors (and their camera
     * hooks), whether or not Scene Depth itself is selected. */
    char dlss[16] = "false";
    psx_mod_option_value("soup.presentation.vulkan", "vulkan-presenter", "dlss", dlss, sizeof dlss);
    if (!strcmp(dlss, "true")) {
        soup_arm_scene_motion();
        gl_renderer_set_dlss(1);
    }
}
PSX_MOD_CONSTRUCTOR(register_soup_vulkan_presenter) {
    psx_mod_register_activation_plugin("soup.vulkan-presenter", activate_vulkan_presenter);
}
