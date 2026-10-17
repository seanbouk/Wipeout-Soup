# Vulkan headers (vendored subset)

The C headers the Vulkan presenter (`psxrecomp/runtime/src/vk_presenter.c`)
compiles against, from [KhronosGroup/Vulkan-Headers](https://github.com/KhronosGroup/Vulkan-Headers)
tag `v1.4.304`, unmodified: `include/vulkan/{vulkan.h, vulkan_core.h,
vk_platform.h, vulkan_win32.h}` and `include/vk_video/*.h` (included by
`vulkan_core.h`). Licensed Apache-2.0 OR MIT (see `LICENSE.md`, `LICENSES/`).

Headers only: the Vulkan loader (`vulkan-1.dll`) comes with the graphics
driver and is loaded at runtime.
