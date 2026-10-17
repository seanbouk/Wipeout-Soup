# Phase 4 plan: Streamline / DLSS hand-off

Status: **4a done** (2026-10-17, [vulkan-presenter.md](vulkan-presenter.md)); **4b done** (2026-10-17, [dlss.md](dlss.md)); 4c optional. Follows motion-vector Phases 0–3
([plan](motion-vectors-plan.md)), which produced everything DLSS consumes:
per-pixel depth, motion vectors and a history-reset flag.

## Constraints

- **Streamline has no OpenGL support.** It takes D3D11, D3D12 or Vulkan (1.2+).
  Vulkan integration either goes through `sl.interposer.dll` (load it instead of
  `vulkan-1.dll`, use its `vkCreateInstance`/`vkCreateDevice` proxies) or creates
  the device natively and calls `slSetVulkanInfo`.
- **Features by API.** DLSS Super Resolution (incl. DLAA) runs on all three. DLSS
  Frame Generation needs D3D12 or Vulkan. Public Streamline (2.14.16, 16 Oct
  2026) has **no DLSS 5 / neural-rendering module**. Its exact API isn't known
  yet; Vulkan is the safest bet for it.
- **DLSS-SR inputs:** `kBufferTypeScalingInputColor` (render resolution),
  `kBufferTypeScalingOutputColor`, `kBufferTypeDepth`, `kBufferTypeMvec`, and
  optionally `kBufferTypeExposure`. Per frame: jitter (pixel space),
  `mvecScale`, reset, and matrices (row-major, no jitter). Tagged depth with
  stencil needs a depth-only view.
- **Our renderer is OpenGL** and the framework's Vulkan renderer is unfinished
  (geometry aborts). Rewriting rendering is out of scope.

## Approach: OpenGL renders, a small Vulkan presenter owns the screen

```
 game ─► GL renderer ─► shared images (colour, depth, motion) ─► Vulkan presenter
                         (GL_EXT_memory_object_win32 +          ├─ Streamline/DLSS
                          GL_EXT_semaphore_win32)                └─ swapchain ─► window
```

- **Shared images:** Vulkan allocates them with exportable memory, and GL imports them
  (`glImportMemoryWin32HandleEXT`, `glTexStorageMem2DEXT`). GL draws into them; a
  shared semaphore pair hands each frame over. No copies through the CPU.
  NVIDIA supports these extensions; without them the game keeps today's GL
  presenter.
- **Window:** the visible window becomes a Vulkan surface. GL keeps rendering to
  its offscreen targets, as it already does.
- **Why not D3D11?** GL→D3D11 interop (`WGL_NV_DX_interop2`) is simpler and mature,
  but D3D11 caps us at upscaling: no frame generation, and probably no DLSS 5.
- **Why not finish the Vulkan renderer?** That's weeks of renderer work in
  someone else's framework before any DLSS does anything.
- **Where it lives:** new source files (`vk_presenter`, `sl_bridge`) added by
  `psxrecomp-soup.patch`, plus small hooks in the GL present path. That keeps
  upstream rebases cheap.

## Phases

### 4a. Vulkan presenter, no DLSS (~1–1.5 weeks)

- **Presenter:** Vulkan instance/device/swapchain on the game window. Shared
  colour image at window size. GL's final present pass (letterbox, bezel,
  CRT/scanlines, OSD) draws into it instead of the default framebuffer.
- **Present modes:** FIFO (vsync), MAILBOX and immediate. This is also where the
  75 Hz tearing item gets fixed properly, by pacing to the panel or switching
  fullscreen to 60 Hz.
- **Setting:** `Presenter: OpenGL | Vulkan`, default OpenGL until proven.
- **Verify:** pixel-identical frames against the GL presenter (debug readback),
  the same frame time, and no tearing at 60 Hz.

### 4b. Streamline + DLSS Super Resolution / DLAA (~1–1.5 weeks)

- **Integration:** Streamline initialised before Vulkan (interposer route).
  Tags:
  - **Input colour:** the displayed region at render resolution. Today's 4×
    widescreen surface is 2296×960, exactly DLSS "Quality" for a 3440×1440
    window.
  - **Depth:** a depth-only image filled from the scene depth (the same data
    ReShade gets).
  - **Motion:** RG16F. Ours is current − previous in native pixels, so the scale
    and sign are set in `mvecScale` or the copy.
  - **Reset:** from `psx_mv_last_render_was_reset()`.
  - **Output:** a window-sized image, then present.
- **Jitter:** sub-pixel camera jitter (Halton) on 3D primitives only, applied in
  the GL vertex shaders (2D/HUD unjittered), and reported to Streamline. Without
  jitter DLSS can't resolve detail.
- **HUD:** DLSS would smear the HUD if it carries the background's motion. First
  step: opaque 2D primitives (text, HUD sprites) write zero motion instead of
  keeping what's underneath. Later, if needed: route the HUD to a separate UI
  layer composited after DLSS.
- **Rate:** DLSS evaluates once per new game frame (30 fps); repeated presents
  reuse its output.
- **Verify:** A/B screenshots (off / DLAA / Quality); a paused game must be
  temporally stable (no shimmer); no ghosting behind ships at speed, checked
  with `mv_check`-style warps on DLSS output; frame time.

### 4c. Frame Generation (optional, ~1 week)

DLSS-G needs Reflex, Streamline's swapchain handling, HUD-less colour and
camera matrices (which we can build from the known camera). The game logic runs
at 30 fps, so generating frames could genuinely smooth it. But on a 75 Hz
non-VRR display the pacing benefit is uncertain. Decide after 4b.

### 4d. DLSS 5 (when NVIDIA publishes it)

Plug the neural-rendering module in on the same bridge: the inputs it is
reported to take (frame plus motion vectors, maybe depth) all exist. Until then,
the community route remains possible on top, and now with real depth and
motion.

## Prerequisites and risks

- **SDK binaries:** Streamline release binaries (NVIDIA-signed) and
  `nvngx_dlss.dll` are downloaded by a script, not committed. Development builds
  of Streamline are unsigned and for local use only. No NVIDIA application ID is
  needed for development (`engine` type + version instead).
- **Interop gaps:** if the GL/Vulkan extensions are missing (other GPUs), the
  Vulkan presenter is unavailable and the GL presenter stays.
- **ReShade:** with a Vulkan presenter, ReShade attaches as a Vulkan layer. The
  presenter has to expose depth to it the way the GL path does now.
- **Jitter vs PS1 look:** jitter moves 3D geometry by under a pixel per frame at
  render resolution. DLSS resolves it, but with DLSS off it must be disabled.
- **Upstream drift:** the presenter and bridge are new files. Only the
  present-path hooks touch upstream code.

## Order of work

4a first: it's useful on its own (tearing fix, a clean swapchain) and is the
foundation. Then 4b, which delivers the first visible DLSS result. 4c and 4d are
decided later.
