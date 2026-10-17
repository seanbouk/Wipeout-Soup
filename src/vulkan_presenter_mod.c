/* Wipeout Soup presentation plugin: present through Vulkan instead of OpenGL's
 * own swap (the groundwork for Streamline/DLSS, docs/soup/streamline-plan.md).
 * The renderer does the work (gl_renderer_set_vulkan_presenter); it falls back
 * to OpenGL by itself if Vulkan can't start. */
#include "mod_plugins.h"
#include "gpu_gl_renderer.h"
static void activate_vulkan_presenter(void) {
    gl_renderer_set_vulkan_presenter(1);
}
PSX_MOD_CONSTRUCTOR(register_soup_vulkan_presenter) {
    psx_mod_register_activation_plugin("soup.vulkan-presenter", activate_vulkan_presenter);
}
