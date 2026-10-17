# Phase 4a: Vulkan presenter

Step 4a of the [Streamline plan](streamline-plan.md). **Done** (2026-10-17). The
OpenGL renderer still draws everything; each finished frame is handed to
Vulkan, which puts it on screen. That's the path Streamline/DLSS will hook
into (4b). Opt-in: Mods → **Vulkan Presenter (experimental)**. It falls back
to OpenGL by itself if Vulkan can't start.

## How it works

- **Shared image:** a window-sized RGBA8 image is allocated by Vulkan in
  exportable memory and imported into GL (`GL_EXT_memory_object_win32`).
  GL's final present pass (letterbox, bezel, CRT, OSD) draws into it through
  an FBO instead of the default framebuffer.
- **Hand-off:** two exported binary semaphores
  (`GL_EXT_semaphore_win32`). GL signals when the frame is done; Vulkan waits,
  blits the image (Y-flipped) to its swapchain, presents, and signals back;
  GL waits before reusing the image. Every GL signal is matched by one Vulkan
  wait, even when no swapchain image could be acquired.
- **Child window:** Vulkan presents to a child window laid over the game
  window's client area, not to the game window. On NVIDIA one window can't
  carry both: with GL's context first, the swapchain fails
  (`VK_ERROR_NATIVE_WINDOW_IN_USE_KHR`); with the swapchain first,
  `wglMakeCurrent` fails. The child is input-transparent (`HTTRANSPARENT`,
  disabled) and resized to the client area on every present.
- **Renderer hook:** `gpu_gl_renderer.c` binds a "window framebuffer"
  variable everywhere it used to bind framebuffer 0 (35 places). It's 0 under
  GL and the shared image's FBO under Vulkan, so the GL path is untouched.
- **Present modes:** vsync on → FIFO; vsync off → **MAILBOX** (no waiting, no
  tearing), immediate only if mailbox is missing. On a 75 Hz panel the runtime
  turns vsync off, which tears under GL; mailbox doesn't.
- **Code:** `psxrecomp/runtime/src/vk_presenter.c` and
  `include/vk_presenter.h` (in `psxrecomp-soup.patch`), `src/vulkan_presenter_mod.c`,
  and the vendored Khronos headers in `third_party/vulkan-headers/` (the
  loader comes with the driver). Debug: the `presenter` command reports the
  live presenter, mode and size.

## Verification (dev build, RTX 5060 Ti, driver 596.36)

- **Pixel-identical:** on a paused save state, the renderer's output (read
  back through GL) and a Windows capture of the screen (Vulkan's output)
  differ only in the pause menu's pulsing highlight and the window's rounded
  corners. No row shift and no colour change.
- **Frame time unchanged:** 16.68 ms (60 fps) windowed, 16.70 ms fullscreen at
  3440×1440. Present GPU time 1.75 ms at 1920×803, 3.4 ms at 3440×1440.
- **Resizes:** three live window resizes; the image and swapchain follow
  (1264×561, 1584×861, 884×661) and the game keeps running.
- **Fullscreen 3440×1440:** works, and the window can now be screen-captured
  (GL's exclusive fullscreen captured black).
- **Startup:** 5 of 5 starts came up on Vulkan.

## Known issues and notes

- **Unexplained init sensitivity:** the shared-image import failed
  (`GL_OUT_OF_MEMORY`, incomplete FBO) until per-step `glGetError` checks were
  added, and has worked every time since. The checks stay (they run once at
  startup), but the root cause isn't understood. If it ever falls back to
  OpenGL, the log says which step failed.
- **ReShade:** its OpenGL install stops working with this presenter on (GL
  never presents). ReShade would need its Vulkan install.
- **Other GPUs:** without the GL memory/semaphore interop extensions it falls
  back to OpenGL.
