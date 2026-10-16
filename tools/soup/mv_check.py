"""Motion-vector accuracy check for captures from the debug server's
"mv_capture" (see docs/soup/motion-vectors-plan.md, Phase 1).

For each pair of consecutive frames A -> B, pixels of B that have a motion
vector are looked up in A at (position - k * motion) and the colour difference
is averaged, for several scales k. Correct vectors give the lowest error at
k = 1; k = 0 is the assume-nothing-moved baseline. Scored pixels are textured
(local contrast) and changed between A and B, which drops static overlays
such as HUD text: they sit on top of moving scenery and inherit its motion.
--images also writes, per frame: colour | motion (hue = direction,
brightness = speed, black = none) | warp error at k = 1.

usage: python mv_check.py <capture dir> [--images]
"""
import glob, os, sys
import numpy as np

def load(base):
    f = list(map(int, open(base + ".txt").read().split()))
    w, h, s, frame = f[:4]
    reset = f[4] if len(f) > 4 else 0
    rgb = np.fromfile(base + ".rgba", np.uint8).reshape(h, w, 4)[..., :3].astype(np.float32)
    mv = np.fromfile(base + ".mv", np.float32).reshape(h, w, 4)
    return {"w": w, "h": h, "s": s, "frame": frame, "reset": reset, "rgb": rgb, "mv": mv}

def sample(img, x, y):
    """Bilinear lookup; returns values and an in-bounds mask."""
    h, w = img.shape[:2]
    ok = (x >= 0) & (y >= 0) & (x <= w - 1) & (y <= h - 1)
    x = np.clip(x, 0, w - 1.001); y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    v = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) +
         img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
    return v, ok

def motion_picture(mv):
    m = mv[..., :2]; has = mv[..., 2] > 0.5
    ang = np.arctan2(m[..., 1], m[..., 0]); mag = np.hypot(m[..., 0], m[..., 1])
    hue = (ang + np.pi) / (2 * np.pi)
    val = np.clip(mag / 8.0, 0, 1) * has          # 8 native px/frame = full bright
    i = np.floor(hue * 6).astype(int) % 6; f = hue * 6 - np.floor(hue * 6)
    p, q, t = 0 * val, val * (1 - f), val * f
    r = np.choose(i, [val, q, p, p, t, val]); g = np.choose(i, [t, val, val, q, p, p])
    b = np.choose(i, [p, p, t, val, val, q])
    return (np.stack([r, g, b], -1) * 255).astype(np.uint8)

def main():
    d = sys.argv[1]; images = "--images" in sys.argv
    frames = [load(p[:-4]) for p in sorted(glob.glob(os.path.join(d, "f*.txt")))]
    ks = [-1, 0, 0.5, 0.8, 1, 1.25, 1.5, 2]
    rows, resets = [], []
    for a, b in zip(frames, frames[1:]):
        if b["frame"] != a["frame"] + 1 or a["rgb"].shape != b["rgb"].shape:
            continue
        if b["reset"]:                     # history reset (camera cut): not scored
            resets.append((b["frame"], (b["mv"][..., 2] > 0.5).mean() * 100,
                           float(np.abs(b["mv"][..., :2]).max())))
            continue
        s = b["s"]; h, w = b["h"], b["w"]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        gy, gx = np.gradient(b["rgb"].mean(-1))
        scored = ((b["mv"][..., 2] > 0.5) & (np.abs(gx) + np.abs(gy) > 4) &
                  (np.abs(a["rgb"] - b["rgb"]).sum(-1) > 0))
        errs = []
        for k in ks:
            warped, ok = sample(a["rgb"], xx - k * b["mv"][..., 0] * s, yy - k * b["mv"][..., 1] * s)
            e = np.abs(warped - b["rgb"]).mean(-1)
            errs.append(e[scored & ok].mean() if (scored & ok).any() else float("nan"))
            if k == 1:
                e1, ok1 = e, ok
        speed = np.hypot(b["mv"][..., 0], b["mv"][..., 1])[scored]
        cover = (b["mv"][..., 2] > 0.5).mean() * 100
        rows.append((a["frame"], b["frame"], cover, float(np.median(speed)) if speed.size else 0.0, errs))
        if images:
            from PIL import Image
            err = np.clip(e1 * 4, 0, 255) * (scored & ok1)
            pic = np.concatenate([b["rgb"].astype(np.uint8), motion_picture(b["mv"]),
                                  np.repeat(err[..., None], 3, -1).astype(np.uint8)], 1)
            Image.fromarray(pic).resize((pic.shape[1] // 4, pic.shape[0] // 4)).save(
                os.path.join(d, "check_%d.png" % b["frame"]))
    print("frames      motion   median speed  best   error at k=0 (still) / k=1 (motion)")
    print("            cover    (native px)   k")
    for fa, fb, cov, spd, errs in rows:
        if np.all(np.isnan(errs)):
            print("%4d->%-4d  %5.1f%%   nothing to score (no textured pixel changed)" % (fa, fb, cov))
            continue
        best = ks[int(np.nanargmin(errs))]
        print("%4d->%-4d  %5.1f%%   %6.2f        %-5g  %6.2f / %6.2f" % (fa, fb, cov, spd, best, errs[1], errs[4]))
    for fr, cov, mx in resets:
        print("%4d       reset (camera cut / no history): motion on %.1f%% of pixels, max %.2f px" % (fr, cov, mx))
    if rows:
        rows = [r for r in rows if not np.all(np.isnan(r[4]))]
        print("best k=1 in %d of %d pairs; mean error still %.2f, motion %.2f" % (
            sum(1 for r in rows if ks[int(np.nanargmin(r[4]))] == 1), len(rows),
            np.nanmean([r[4][1] for r in rows]), np.nanmean([r[4][4] for r in rows])))

if __name__ == "__main__":
    main()
