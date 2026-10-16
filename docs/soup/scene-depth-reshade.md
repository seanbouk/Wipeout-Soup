# Scene depth and ReShade

Wipeout Soup can give the game a real depth buffer, so ReShade's depth-based
effects (depth of field, ambient occlusion, motion vectors) work. This is also
the groundwork for any later DLSS / neural-rendering experiment, which needs
depth and motion vectors.

## How it works

- PlayStation games have no depth buffer; they draw back to front. PGXP already
  tracks each projected vertex's view depth (the GTE's `SZ`) to fix wobble and
  texture warping.
- With the **Scene Depth (ReShade)** mod on, the OpenGL renderer writes that
  depth for every 3D triangle into the free depth half of its existing
  depth/stencil buffers. It uses `GL_ALWAYS`, so the last-drawn triangle wins,
  the same as the colour. Draw order and game behaviour are unchanged.
- At present, the displayed region's depth is blitted into the window's depth
  buffer with the same fit as the picture (letterbox, widescreen margins).
  ReShade reads it from there.
- Depth uses a standard perspective curve, near 1 / far 65536 in GTE units.
- 2D sprites, HUD, text, lines and FMVs carry no depth. Fills reset it to far.

Code: `patches/psxrecomp-soup.patch` (renderer) and `src/scene_depth_mod.c` (mod).

## Coverage needs the full-PGXP build

PGXP can only attach depth to vertices it tracked. On the framework's base
build that's about 10% of vertices in Wipeout XL, so most of the track has no
depth. This project therefore builds with `SOUP_FULL_PGXP=ON` (the default),
which compiles the game with the PGXP hooks (`-DPSX_PGXP=1`). Coverage is
then near-complete. In the attract demo it measured the same 16.68 ms frame
time as the base build.

Turn on **PGXP Precision** as well as Scene Depth: the depth comes from the
PGXP engine.

## Setting up ReShade (manual, official build)

1. Download ReShade from <https://reshade.me> (tested: 6.8.0).
2. Either run its installer on `build-release\Wipeout2K97XL.exe` and pick
   OpenGL, or extract `ReShade64.dll` from the installer (it is a zip) and
   copy it next to the exe as `opengl32.dll`.
3. Put shaders in `reshade-shaders\Shaders` (e.g. `DisplayDepth.fx` with
   `ReShade.fxh`, `ReShadeUI.fxh`, `DisplayDepth_L10N.fxh` from
   crosire/reshade-shaders `slim`; iMMERSE's `MartysMods_LAUNCHPAD.fx` for
   motion vectors).
4. In the launcher's Mods page, enable **PGXP Precision** and **Scene Depth (ReShade)**.
5. In game, press **Home** for the ReShade overlay. Generic Depth picks the
   window depth automatically; DisplayDepth should show the track receding.
   Depth is not upside down, reversed or logarithmic. Raise
   `RESHADE_DEPTH_LINEARIZATION_FAR_PLANE` if distant scenery looks flat.

To remove ReShade, delete `opengl32.dll`, `ReShade.ini`, `ReShadePreset.ini`,
`ReShade.log` and `reshade-shaders`.

### Why there's a 6-vertex invisible draw at present

ReShade 6.8's Generic Depth add-on ignores any depth buffer that had 3 or fewer
vertices drawn into it in a frame. The window's only real draw is the 3-vertex
present triangle, and its depth arrives by blit. So the renderer issues one
6-vertex draw with all writes masked off. It changes no pixel and no depth
value; it just makes the window depth a detection candidate.

## Motion vectors (experimental)

The Scene Depth mod has a *Motion vectors* option: a per-pixel motion layer
for the track and scenery, groundwork for DLSS. It isn't exposed to ReShade
yet. See [motion-vectors-phase1.md](motion-vectors-phase1.md).

## Debug

On a `-DPSX_DEBUG_TOOLS=ON` build, `{"cmd":"present_shot","path":"d.png","depth":1}`
saves the window depth as a grey image (log scale, near white, far black).
