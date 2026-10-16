/* Wipeout Soup presentation plugin: scene depth for post-process tools.
 * The renderer does the work (gl_renderer_set_depth_output); this only arms it. */
#include "mod_plugins.h"
#include "gpu_gl_renderer.h"
static void activate_scene_depth(void) {
    gl_renderer_set_depth_output(1);
}
PSX_MOD_CONSTRUCTOR(register_soup_scene_depth) {
    psx_mod_register_activation_plugin("soup.scene-depth", activate_scene_depth);
}
