# Motion vectors: Phase 3 results

Phase 3 of [motion-vectors-plan.md](motion-vectors-plan.md): edge cases.
**Done** (2026-10-17). Tested on five user save states: start grid, mid-pack,
holding a weapon, last lap leading, and a second track. Plus the attract demo.

## What changed

- **Camera cuts → reset.** At each render's first projection the camera is
  compared with the previous render's. A jump beyond 1536 world units, or a
  rotation element change beyond 1024/4096, is a cut. The render gets no
  motion and is flagged as a history reset (`psx_mv_last_render_was_reset()`,
  DLSS's "reset" input). Measured: normal racing moves ≤ ~300 units and turns
  ≤ ~270 per render; the race-start cut was (1029, 3754), and finish/replay
  cuts turn 2300–5972. Zero false cuts in racing.
- **Renders without 3D** (menus, FMV, loading) break the history: the next 3D
  render is a reset, and object transforms are dropped.
- **Reset flag timing.** Wipeout shows a render one display flip after the
  flip that completes it, so the flag waits one flip. Verified: the frames on
  screen with reset = 1 are exactly the ones with no motion.
- **Unbiased motion.** The delta used to be "GTE's projection minus my exact
  projection of the previous position", and the GTE's approximate
  reciprocal divide leaked up to 0.5 px of fake motion everywhere. Both
  positions now go through the same exact projection, and the camera is undone
  with its exact inverse rather than its (nearly orthonormal) transpose.
  **A paused game now gives exactly 0.00000 px.**
- **Test driving** (`tools/soup/drive.py`): load a state, unpause, hold
  thrust, fire. The debug server's button word is active-low, and its NeGcon
  override only applies under a persistent button override.

## Results (final build)

| Footage | Best k = 1 | Error, still → motion |
|---|---|---|
| Slot 1, mid-pack race | 8 of 9 | 36.8 → 23.6 |
| Slot 2, weapon state (24 frames) | 23 of 23 | 30.4 → 19.5 |
| Slot 4, second track | 9 of 9 | 32.7 → 19.1 |
| Post-race orbit (outside the results panel) | every frame | ~20 → 3–5 |
| Paused | — | motion exactly 0 |

Objects without history are rare in real races (21 of 12,713 object
projections); the "~2 per render" seen in Phase 2 was a demo-footage quirk.

## Decisions

- **Semi-transparent geometry** (ship shadow, glows, exhaust ribbons) and **2D
  sprites** (flares, explosions) don't write motion; they keep the motion of
  what's behind them. This is the usual practice for DLSS-style consumers,
  which treat transparency and particles separately, and avoids trading
  correct background motion for a translucent layer's.
- **HUD and overlays** keep the motion underneath. They'll be passed to
  Streamline as separate UI (Phase 4).

## Open items

- **Far scenery alternation:** in the top half of chase-cam frames (distant
  mountains/sky), best k alternates ~0.8 / 1.25 between pairs. That looks like
  something updated every other render. About 10% of error there; not yet
  explained.
- **Check-tool limitation:** large static overlays (results panel, HUD text)
  skew `mv_check.py` towards "assume still"; score a region clear of the
  overlay instead.
- **Weapons and explosions:** the weapon fired in slot 2 produced no visible
  projectile in the captured frames, so effect coverage is still untested.
- **Speed classes:** cut thresholds were measured in this class; faster
  classes move further per render (still far below 1536 at ~300 now).
