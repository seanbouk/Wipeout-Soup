# Motion vectors: Phase 0 findings

Phase 0 of [motion-vectors-plan.md](motion-vectors-plan.md): confirm the
assumptions before building. Measured on the dev build (full PGXP, widescreen
43:18) in the attract-mode race, 2026-10-16. **Verdict: go.** The reprojection
approach holds, and the static-world case is exact.

## 1. Frame rate: 30 fps game frames, not 60

In chase-cam view, host frames alternate between ~1,650 projections and
~100–450. Both halves use the same camera rotation, so one game frame is
rendered across two 60 Hz host frames. Motion must be measured per **game
frame**, not per VBlank. In the trackside-camera view every host frame is a
full render, so the cadence isn't even fixed. The clock must come from the game
(the frame-end function `0x800684C4`, already hooked by upstream mods) and be
checked first thing in Phase 1.

## 2. The camera model (static world), confirmed exactly

The scene graph (upstream's `track_distance_experimental.c` worked it out):
model → node (`+0x30`) → camera-offset node (`node+0x44`) → root camera node
(`+0x44`). In this race:

| Node | Address | Field |
|---|---|---|
| root camera | `0x801164D4` | rotation 3×3 int16 at `+0`, translation at `+0x14` (always 0) |
| camera offset | `0x8011653C` | `int32[3]` at `+0x14` = **−camera position** |

- **Rotation:** the root rotation equals the GTE's `RT` for all world geometry,
  bit for bit, in every sampled frame.
- **Position:** the track is not transformed by the GTE translation (`TR` = 0).
  Its vertices are computed on the CPU as `world point + offset`, so between
  game frames every track vertex shifts by the offset's change. Across 49
  consecutive game-frame pairs at race speed, the dominant vertex shift equalled
  the offset change **exactly, every time**, e.g. (2, −11, −255) both ways.
  About 330–355 of ~355 vertices per frame follow it; the rest are vertices
  entering or leaving view.
- **Scenery objects** (renderer `0x8001004C`) use the camera rotation with a
  per-object `TR` (camera-relative object position).

So for anything static in the world, the previous frame's view position is:

```
view_prev = Rf_prev · ( Rfᵀ · (view − TR) − off + off_prev ) + TR'
```

with the camera's rotation `Rf` (/4096) and offset `off` from this frame and the
last. For the track `TR = TR' = 0`. For scenery, `TR` folds in the object's
fixed position. No guessing and no vertex matching are needed.

## 3. What's in a frame

A heavy chase-cam frame has ~1,650 projections and only ~16 distinct transforms:

| Renderer (`ra`) | Per frame | Transform | What |
|---|---|---|---|
| `0x80013CE0`, `0x800152C4`, `0x800140F4`, `0x80012F20`, `0x80014B20`, `0x80015xxx`, `0x8001615C` | ~1,100 | camera rotation, one matrix | track and track-side geometry |
| `0x8001004C` | ~340 | camera rotation, ~12 translations | static scenery objects |
| `0x8001004C` | 30–75 each | **own rotation** | other racers (depth 20,000–30,000) |
| `0x80011E38` | ~60 | **own rotation**, `TR ≈ (0, 0, 760)` | **the player's ship**, just ahead of the chase camera |
| `0x8007173C`, `0x80071524` | ~7 | — | small; light half-frame (identify in Phase 2) |

About 94% of projections are static world. The actors are the player's ship
plus at most a few racers. Note that **the player's ship barely moves on
screen** (it's tied to the chase camera), so camera-only motion would be badly
wrong for it. Phase 2 has to handle it first.

## 4. Camera modes and cuts

The attract demo cuts between a **chase camera** (moving with the ship) and
**trackside cameras** (fixed position, panning to follow the ship). In
trackside view the offset doesn't change at all; only the rotation does.
Both cases fall out of the same formula. The cuts between them are
discontinuities, so Phase 3's cut detection (reset history) is required, not
optional. A cut shows up as a jump in the offset or rotation far beyond one
frame's motion.

## 5. Still open (folded into Phase 1/2)

- **Frame clock:** verify that `0x800684C4` fires exactly once per game frame in
  both camera modes, and that the camera is final by the first projection.
- **2D effects:** sprites with no depth (the blue weapon/exhaust flare, glows,
  HUD). Inventory them in Phase 1 with the motion-vector debug view, then
  decide zero motion or inherit.
- **The `0x8007173C` renderer** in the light half-frame: identify it.

## Tooling added

- `gte_ring_dump` takes `offset`, so a whole frame (more than 512 projections)
  can be paged out (`psxrecomp-soup.patch`).
- **Save states for testing:** the dev build keeps its own cards and states in
  `build-dev/saves-dev`. Slot 8 is chase-cam mid-race, slot 9 trackside at the
  race start. A test reaches the race in ~5 s instead of ~145 s. The states are
  local game RAM and are not committed.
- `tools/soup/dbg.py`: debug-server helpers (`cmd`, `launch`, `race`, `shot`).
