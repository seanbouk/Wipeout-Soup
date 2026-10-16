/* Original opt-in presentation plugin. Visibility sites live in game.toml. */
#include "mod_plugins.h"
#include "gpu.h"
#include <string.h>
/* Main8001A504 enters menu4DA10; all race/attract paths enter3EA68.
 * Confirmed against Ghidra and native/Beetle executable bytes. Presentation
 * only: the menu's rotating preview is not a widescreen world scene. */
static void menu_enter(CPUState *cpu,uint32_t address) {
    (void)cpu;(void)address;gpu_ws_set_ui_mode(1);
}
static void race_enter(CPUState *cpu,uint32_t address) {
    (void)cpu;(void)address;gpu_ws_set_ui_mode(0);
}
static void activate_widescreen(void) {
    gpu_ws_set_ui_mode(0);
    psx_mod_register_function_entry_plugin("wxl.widescreen",0x8004da10u,menu_enter);
    psx_mod_register_function_entry_plugin("wxl.widescreen",0x8003ea68u,race_enter);
    gpu_ws_set_gte_game_mode(1);
    gpu_ws_set_solid_pillarbox(1);
    /* Ultrawide choices stay below the distance mods' 160-pixel margin limit
     * (43:18 adds 127 per side). "window" follows live resizes up to 43:18. */
    char aspect[16];
    if (!psx_mod_option_value("wxl.presentation.widescreen", "widescreen",
                              "aspect", aspect, sizeof aspect))
        strcpy(aspect, "16:9");
    if (!strcmp(aspect, "64:27")) {
        psx_mod_set_fixed_display_aspect(64, 27);
    } else if (!strcmp(aspect, "43:18")) {
        psx_mod_set_fixed_display_aspect(43, 18);
    } else if (!strcmp(aspect, "window")) {
        psx_mod_set_fixed_display_aspect(16, 9);
        psx_mod_set_adaptive_display_aspect(43, 18);
    } else {
        psx_mod_set_fixed_display_aspect(16, 9);
    }
}
PSX_MOD_CONSTRUCTOR(register_wxl_widescreen) {
    psx_mod_register_activation_plugin("wxl.widescreen", activate_widescreen);
}
