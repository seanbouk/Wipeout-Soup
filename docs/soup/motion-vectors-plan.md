# Motion vectors: plan

Goal: per-pixel motion vectors for every 3D surface Wipeout XL draws, saying
where each pixel was in the **previous game frame**. They're needed for DLSS
(any mode) and Streamline, and they replace the optical-flow guesses the ReShade
DLSS tools use today. Status: **Phase 2 done** (2026-10-16): static world and ships verified, see [phase 0](motion-vectors-phase0.md), [phase 1](motion-vectors-phase1.md) and [phase 2](motion-vectors-phase2.md). Phase 3 (edge cases) next.

## What we already have

- **Depth** for nearly every 3D vertex: the GTE's `SZ`, carried by PGXP from
  projection to the GPU packet. Uses the Scene Depth mod and the full-PGXP build.
- **Precise screen position** of each vertex (16.16), through the same path.
- **The camera.** Upstream's `src/track_distance_experimental.c` already hooks
  the scenery renderers (`0x80013C78`, `0x800140AC`, `0x80014AD4`) and reads the
  camera from guest RAM: rotation (+0), translation (+0x14) and a per-object
  `offset[3]`. Its `project()` reproduces the GTE projection exactly
  (`eye = R·(v + offset) + T`, `x = 160 + 160·eye.x/eye.z`, `y = 120 + 160·eye.y/eye.z`).
- **Frame and object hooks:** the game's frame end (`0x800684C4`) and
  `ship_begin` (`0x80021B90`) are already hooked by existing mods, and the mod
  API can hook any other function entry.

## The core idea

A motion vector is `current screen pos − previous screen pos` for the same
surface point. We get the previous position by **reprojection, not by matching
vertices across frames**:

1. At each GTE projection (RTPS/RTPT), the runtime knows the vertex's current
   view-space position (`MAC1-3 = RT·V + TR`).
2. **Static geometry** (track, scenery: most of the screen) hasn't moved in the
   world, only the camera has. So
   `view_prev = R_prev · R_curᵀ · (view_cur − T_cur) + T_prev`, using the camera
   from this frame and the last one. Then project `view_prev` with the same
   H/OFX/OFY (and widescreen squash) as the current projection.
3. **Moving objects** (ships, weapons, pickups, debris): their own transform
   changed too. Keep each object's previous `RT`/`TR`, keyed by object identity
   (see Phase 2), and compute `view_prev = RT_prev·V + TR_prev` with the same
   model-space `V`.
4. The previous screen position rides alongside the existing depth: a new field
   in PGXP's per-word shadow. SWC2 stores, ordering-table reshuffles and DMA
   then carry it to the GPU packet with no new tracking. `gpu.c` hands it to the
   renderer next to `gr_set_triangle_depth`.
5. The GL renderer interpolates it per pixel and writes motion into its own
   render target (`RG16F`) in a second, cheap pass per batch. A second pass is
   needed because the textured shader already uses dual-source blending, so it
   can't write a second colour target. Wipeout draws only ~450 primitives a
   frame, so the extra pass costs very little.

Why not match vertices across frames? Identity is fragile: the track appears to
be offset on the CPU and loaded into the GTE from registers, which loses the
source address. Repeated meshes would also collide. Reprojection needs only the
camera and object transforms, which we can read.

## Phases

### Phase 0: confirm the assumptions (1–2 days)

Using the dev build's debug server (`gte_ring_dump` already records every
projection with V, RT, TR, SXY, SZ and caller):

- **Game frame rate:** does Wipeout render every VBlank (60) or every other
  (30)? Motion must be measured per *rendered game frame*. The frame-end hook
  `0x800684C4` is the likely clock.
- **Camera per frame:** confirm the camera read by the scenery hooks equals the
  RT/TR the GTE uses for static geometry, and that it's stable within a frame.
- **Geometry classes:** group every projection in a frame by caller (`ra`) and
  matrix into static world, ships, weapons, effects and other. Record which
  are static (camera only) and which need per-object transforms.
- **2D effects:** list what's drawn as sprites with no depth (explosions,
  exhaust glows, HUD) and decide what motion they should get.

Exit: a short findings note, and a go/no-go on the reprojection approach.

### Phase 1: camera-only motion for static geometry (≈1 week)

- **Runtime:** record the camera at the game's frame clock, keeping current
  and previous.
- **GTE:** at RTPS/RTPT, compute the previous screen position for the vertex
  as static geometry, and store it in the PGXP shadow beside SXY. That's +8
  bytes per word, about 4 MB extra.
- **GPU:** `gr_set_triangle_motion(...)` alongside depth. The GL renderer adds
  a per-vertex attribute, an `RG16F` motion target at render resolution
  (canonical and widescreen surfaces), and an MV pass per depth-bearing batch.
  Fills clear motion to zero; the widescreen centre blit carries it.
- **Present:** resolve the displayed region's motion into a window-sized
  texture with the same fit as the picture (for Streamline, later).
- **Debug:** `present_shot` gains `"mv":1` (colour-wheel view), plus a
  `mv_check` command. It warps the previous frame by the motion vectors,
  compares the result with the current frame and reports the error. That gives
  an objective "are the vectors right" number, instead of eyeballing.

Exit: the track and scenery reproject with low error while driving, including
at the widescreen margins.

### Phase 2: moving objects (≈1 week)

- **Object identity:** use the hooks already found for ships (`0x80021B90`)
  and find the equivalents for weapons and pickups in Phase 0. Key the previous
  transform by game object (e.g. ship index or entity struct address), never by
  draw order.
- At projection, if the current transform belongs to a known object, use its
  previous `RT`/`TR`. Otherwise fall back to camera-only.
- New or teleported objects (respawn, first frame) get zero motion plus a
  "no history" flag.

Exit: ships and weapons reproject cleanly. That includes ships being
overtaken, which is the worst case for camera-only motion.

### Phase 3: edge cases (≈3–5 days)

- **Camera cuts** (race start, replays, attract mode, menus): detect the jump
  and flag the frame. DLSS has a "reset history" input for exactly this.
- **Pause and frame holds:** no new game frame means motion stays the same, or
  goes to zero.
- **2D sprites and effects:** zero, or inherit the motion of the depth under
  them (decided in Phase 0). The HUD stays zero.
- **FMV, menus, loading:** zero motion with a reset flag.

### Phase 4: hand-off (follow-on work)

- **Streamline stage:** a Vulkan bridge receives colour, depth, motion vectors
  and the reset flag. This is the separate DLSS/Streamline workstream.
- **ReShade (optional):** a tiny add-on that exposes the motion target in
  place of Launchpad's optical flow, so ReShade effects (and the community DLSS
  bridges, if ever used) get real vectors.
- **DLSS upscaling (later):** needs sub-pixel camera jitter. PGXP's precise
  positions make that possible (offset every projected vertex by the jitter),
  but it's not part of this plan.

## Risks

- **Two camera models:** the camera the scenery hooks read might not be the
  only one (cockpit view, replays). Phase 0 checks this.
- **Objects we can't identify** fall back to camera-only. That's wrong but
  stable: those pixels would smear rather than break.
- **Integer GTE maths:** previous positions are computed in floats from the
  same inputs, so tiny sub-pixel differences from the game's integer path are
  expected. They're below what the motion checks can see.
- **Upstream drift:** all of this lives in `psxrecomp-soup.patch`, plus game
  hooks in `src/`. Keeping the framework part small (a PGXP field, a GTE hook,
  a renderer target) keeps rebases cheap.
