# Motion vectors: Phase 1 results

Phase 1 of [motion-vectors-plan.md](motion-vectors-plan.md): per-pixel motion
for static geometry (track and scenery). **Done and verified.** Measured in
the attract-mode race, full-PGXP dev build, widescreen 43:18, 4× scale
(2026-10-16).

## How it works

1. **Camera:** the Scene Depth mod's *Motion vectors* option hooks the scenery
   renderers (as upstream's track-distance mod does) and tells the framework
   where the camera lives: root rotation and the offset node (`= −position`).
   See [motion-vectors-phase0.md](motion-vectors-phase0.md).
2. **Clock:** the render, not game logic. `gpu.c` calls
   `psx_mv_render_boundary()` whenever the game flips its display buffer. The
   camera latched at a render's first projection becomes "previous" for the
   next.
3. **GTE** (`gte.cpp`): for each projection whose rotation is the camera's
   (static world), compute where the point was last render,
   `view' = R'·(Rᵀ·view − off + off')`, project it with the same H/OFX/OFY and
   widescreen X factor, and attach the **delta** (current − previous screen
   position) to the vertex's PGXP shadow value. A delta rather than a position,
   so anything the game adds to screen coordinates after projection cancels.
4. **GPU** (`gpu.c`): every vertex looks up its delta by packet address,
   validated against the packet word like the rest of PGXP. This deliberately
   doesn't depend on PGXP's precise-position tier (see below).
5. **Renderer** (`gpu_gl_renderer.c`): a second colour attachment (RGBA16F) on
   the main and widescreen targets. Each opaque batch with motion is drawn again
   into it (`u_mvpass`), with the same shaders, so coverage and cutout discards
   match the colour. Fills and widescreen band clears reset it, and the
   widescreen centre blit carries it. Value: `xy` = motion in native pixels,
   `z` = 1 where written.

Everything is opt-in (mod option, default off) and presentation-only.

## Results

`tools/soup/mv_check.py` warps the previous frame by `k × motion` and scores
it against the current frame, on textured pixels that changed. Correct vectors
win at `k = 1`; `k = 0` is "assume nothing moved".

| Segment | Pairs where best k = 1 | Error, still → with motion |
|---|---|---|
| Chase cam at race speed | **7 of 7** | 19.9 → **10.8** (−46%) |
| Trackside cam, gentle sway | 5 of 6 (other 0.8) | 7.4 → 5.6 (−25%) |

Also: the motion layer's mean vector in the trackside clip was −4.0 px against
a measured image shift of −4 px. Against the projection log, the formula
predicts true track-vertex positions to within 0.8 px (integer rounding of the
log). Coverage is ~99% of the frame and 88% of triangles. Frame time is
unchanged (locked 16.68 ms). Present GPU time rose ~1 → 2.6 ms, mostly the
full-height motion copy for the widescreen centre, which can be trimmed to the
display band later.

## Things learned the hard way

- **PGXP's precise tier rejects most of Wipeout's vertices.** About 70% of
  lookups fail its half-pixel tolerance check in this build. Motion first rode
  on that tier and reached only 1 in 30 triangles. It now has its own
  packet-validated lookup. (This may also matter for how much PGXP's wobble fix
  actually applies in this game; worth a look separately.)
- **The game-logic frame hook isn't a render clock.** The display flip is.
- **HUD text fools naïve checks.** A static overlay on moving scenery inherits
  the scenery's motion, so "assume still" wins on its pixels. The check
  excludes pixels that didn't change. For DLSS, the HUD is fed separately
  anyway.

## Known gaps (later phases)

- **Moving objects** have no motion of their own yet; they inherit what's
  behind them. The player's ship is the visible case (Phase 2).
- **Camera cuts** aren't flagged (Phase 3).
- **2D sprites** (the ship's exhaust flare, glows) keep the motion underneath
  (Phase 3 decides).
- **Window resolve:** the motion layer isn't yet copied to a window-sized
  target for Streamline. Moved to Phase 4, which is the only consumer.

## Running the check

On a `-DPSX_DEBUG_TOOLS=ON` build with Scene Depth and Motion vectors enabled
(save states in `build-dev/saves-dev`, see Phase 0):

```python
from dbg import race, cmd                     # tools/soup/dbg.py
p = race(exe)                                 # straight to the race
cmd({"cmd": "mv_capture", "dir": out, "count": 8})
# poll cmd({"cmd": "mv_stats"})["capture_left"] until 0
```
then `python tools/soup/mv_check.py <out> --images`.
