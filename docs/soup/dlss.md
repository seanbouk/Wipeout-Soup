# DLSS Super Resolution / DLAA (Phase 4b)

Status: working (2026-10-17), experimental. Opt-in as the **DLSS (experimental)**
option of the Vulkan Presenter mod. Plan: [streamline-plan.md](streamline-plan.md).
Built on the [Vulkan presenter](vulkan-presenter.md) (4a) and the
[motion vectors](motion-vectors-plan.md) (Phases 0–3).

## Setup

1. `python tools/soup/fetch_streamline.py`. This downloads NVIDIA Streamline
   v2.14.1 (pinned SHA-256) and keeps its four signed runtime DLLs in
   `third_party/streamline/bin/` (git-ignored). The build copies them next to the
   exe: `sl.interposer.dll`, `sl.common.dll`, `sl.dlss.dll` and `nvngx_dlss.dll`.
   The headers are vendored in `third_party/streamline/include/` (MIT).
2. In the launcher, turn on **Vulkan Presenter (experimental)** and its
   **DLSS (experimental)** option, plus **PGXP Precision**. DLSS arms scene
   depth and motion vectors itself; the Scene Depth mod doesn't need to be on.
3. The internal resolution must be **lower than the window** for DLSS to run.
   The mode is picked from the ratio: DLAA when they're equal, then Ultra
   Quality, Quality, Balanced, Performance and Ultra Performance. Example: 4×
   widescreen (2296×960) into 3440×1440 runs as Quality (1.5×). With the
   internal resolution above the window, DLSS idles and the normal OpenGL
   picture shows.

## How it works

- **Startup:** with DLSS wanted, `sl_bridge.cpp` loads `sl.interposer.dll` from
  the exe's folder (full path only), then calls `slInit`. The settings are
  Vulkan, the DLSS feature, frame-based tagging, no OTA updates, no downloaded
  plugins and no log files. The presenter then creates its Vulkan instance and
  device through the interposer's `vkGetInstanceProcAddr`.
  `slIsFeatureSupported` decides whether DLSS is available. If anything is
  missing, the presenter still runs, just without DLSS.
- **Per presented frame** (`dlss_composite` in the GL renderer, `vkp_dlss_run`
  in the presenter):
  1. GL draws the frame as usual.
  2. It blits the displayed region's colour (RGBA8), depth (D24S8) and motion
     (RGBA16F) into three more shared images.
  3. It hands them over with the same semaphore pair.
  4. Vulkan runs DLSS into its own output image the size of the letterbox
     rectangle, then blits it (Y-flipped) into the window image.
  5. GL gets everything back, draws the OSD on top and presents as before.

  If DLSS fails, the GL picture underneath stays.
- **Once per game render:** DLSS runs once per game render. Presents that
  repeat a render reuse the last output, since Wipeout renders at 30 fps.
- **Jitter:** a Halton(2,3) offset, changed at every display flip, applied in
  the GL vertex shaders to 3D primitives only (those with scene depth); the
  2D HUD isn't jittered. Each display buffer records its render's jitter and
  reset flag (`note_draw_buffer`), so the present hands DLSS the right values
  even though the display lags the draw. Jitter is only on while DLSS is
  actually running for the current sizes.
- **Constants:**
  - `mvecScale = (−S/w, −S/h)`: our motion is current − previous in native
    pixels, and DLSS wants previous − current, normalised.
  - Jitter is passed in render pixels with sign (+1, +1).
  - `reset` comes from the motion system (cuts, first 3D frame).
  - The colour input is LDR.
  - Depth isn't inverted. The camera matrices are identity, since motion is
    complete in 2D.

## Verified

| Check | Result |
|---|---|
| Paused-scene stability (frame-to-frame diff in 3D regions, slot 1). Lower is better; GL alone is 0. | Jitter sign (+1, +1): **0.042**. (−1, −1): 0.101. (+1, −1): 0.096. (−1, +1): 0.066. |
| Edges | Visibly smoother than both the raw input and the GL upscale (zoomed crops). |
| Driving (slot 1) | No visible ghosting on ships or track edges in stills. The HUD looks as it does without DLSS. |
| Frame time, 1920×803 window, 2× scale (1148×480 → Quality) | 16.68 ms, same as GL |
| Frame time, 3440×1440 fullscreen, 4× scale (2296×960 → Quality) | 16.68 ms, same as GL |
| Startup reliability | 10 launches without failure after the first. The first run after a build once failed to import an input image into GL. Setup now retries, and only gives up after 3 failures. |

## Debug server

- `{"cmd":"dlss"}`: status (mode, sizes, evaluations, reuses, failures) and
  whether jitter is on.
- `"on":0/1`: switches DLSS off and on at runtime, for A/B tests.
- `"jx"/"jy":±1`: sets the jitter sign.

## Known limits / next

- The CRT filter and scanlines are drawn by the GL present quad, which DLSS
  covers. With DLSS on they don't show.
- DLAA needs the internal resolution to equal the window exactly. The scale
  steps rarely land there: 6× widescreen is 3444 wide, 4 px over a 3440
  window, so DLSS idles.
- ReShade (OpenGL) doesn't see the Vulkan presenter's output.
- Not yet tested: explosions and weapon effects at speed, and long sessions.
- 4c (Frame Generation) is optional and decided after you test this. 4d
  (DLSS 5) waits for NVIDIA's public release.
