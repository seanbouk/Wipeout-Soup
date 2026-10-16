# Motion vectors: Phase 2 results

Phase 2 of [motion-vectors-plan.md](motion-vectors-plan.md): moving objects
get their own motion. **Done for ships**, the only moving 3D objects in the
footage available (2026-10-16).

## How it works

- **Identity:** the Scene Depth mod hooks the two object renderers and tells
  the framework which object is being drawn (`psx_mv_object(key)`):
  - `0x80011DE8`, the ship mesh renderer. The dispatcher `0x80021B90` calls it
    once per near ship with the ship's model in `a0` (15 ships, 15 models).
    Newly added to `game.toml`'s entry hooks, so the game code was regenerated.
  - `0x80010000`, the general model renderer (same `a0` convention, as in
    upstream's `note_model`).
  - The track/scenery renderers reset the key to "none".
- **Motion:** a projection inside an object whose rotation isn't the camera's
  uses that object's previous-render transform on the same model-space vertex:
  `view' = RT'·V + TR'`. This is exact for any rigid object, whatever moved
  (object, camera or both). Transforms live in two small tables (this render,
  last render), keyed by object and by which of the object's matrices it is,
  and swapped at each display flip.
- **Static path unchanged:** anything drawn with the camera rotation still uses
  the camera-only formula. A stale object key can never affect the track.

## Results

Same deterministic save-state footage as Phase 1 (chase cam, the player's ship
in view, another ship ahead). Object pixels were found by diffing the Phase 1
and Phase 2 motion layers for identical frames.

| Ship pixels, error | Frame 154 | 155 | 156 | 157 | 158 |
|---|---|---|---|---|---|
| Assume still | 33.5 | 38.9 | 38.7 | 38.0 | 39.0 |
| Phase 1 (borrowed track motion) | 34.8 | 39.1 | 39.2 | 37.8 | 39.7 |
| **Phase 2 (own transform)** | **25.1** | **19.8** | **9.6** | **12.8** | **10.6** |

The ship's error drops 3–4× once more of it is in view. Phase 1's borrowed
motion was no better than nothing. Whole-frame scores stay correct (best scale
k = 1 in 7 of 7 pairs; error 19.7 → 10.2). About 98.5% of object projections
find their previous transform; the rest belong to objects that just appeared.

## Still open (Phase 3)

- **Ship shadow and exhaust flare:** the shadow is semi-transparent and the
  flare is a 2D sprite, so both keep the track's motion. Their outlines are
  the main remaining error around the ship.
- **Weapons, pickups, explosions:** not in this footage. Mesh weapons drawn
  through `0x80010000` are covered by the same path; sprite effects aren't.
- **~2 objects per render** start without a previous transform. Likely
  objects drawn every other render, or the light half-frame; worth a look.
- **Camera cuts** (reset history) are still Phase 3.
- **More footage:** the save state has ~10 s of race. Overtakes, weapons and
  replays need a longer recording or a user save state.
