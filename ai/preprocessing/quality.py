"""Image quality heuristics on the rectified letter block (Spec §7.1). Warn only; never reject on these.

Blur: variance of the Laplacian of the grey letter block, measured on the rectified canvas so the value does not depend
on the photo resolution (canvas scale is fixed by `px_per_unit`). Exposure: fraction of near-black / near-white pixels.
Thresholds are deliberately conservative dev values, set from the Kaggle validation canvases (gt points, 226 images):
Var(Laplacian) at ppu 64 had min 10 / p1 59 / median 593, and a Gaussian blur of sigma 2 brings the median to ~15.
Product photos with pure black / white keycaps reach dark 0.97 / bright 0.77 clipped fractions while still readable, so
exposure only flags near-total clipping. Re-check on our own phone photos (implementation plan P3.D).
"""
from __future__ import annotations

import cv2
import numpy as np

REF_PPU = 64                    # blur threshold below is defined at this canvas scale
BLUR_VAR_MIN = 20.0             # Var(Laplacian) at REF_PPU; lower -> blurred / out of focus
BLUR_PPU_EXP = 2.5              # measured: the variance falls ~ ppu^-2.5 between ppu 64 and 128 on the same canvases
DARK_LEVEL = 8                  # grey <= this counts as clipped dark
BRIGHT_LEVEL = 247              # grey >= this counts as clipped bright
DARK_FRAC_MAX = 0.98            # black keycaps are legitimately dark; only near-total under-exposure
BRIGHT_FRAC_MAX = 0.90


def block_roi_px(regions_u: np.ndarray, ppu: int, origin_u, pad_u: float = 0.0) -> tuple[int, int, int, int]:
    """Bounding box (canvas px, xyxy) around all layout slot regions."""
    r = np.asarray(regions_u, float)
    x0, y0 = r[:, 0].min() - pad_u, r[:, 1].min() - pad_u
    x1, y1 = r[:, 2].max() + pad_u, r[:, 3].max() + pad_u
    ox, oy = origin_u
    return (int(round((x0 - ox) * ppu)), int(round((y0 - oy) * ppu)), int(round((x1 - ox) * ppu)), int(round((y1 - oy) * ppu)))


def quality_stats(image_bgr: np.ndarray, roi_xyxy: tuple[int, int, int, int] | None = None) -> dict:
    im = image_bgr
    if roi_xyxy is not None:
        h, w = im.shape[:2]
        x0, y0, x1, y1 = roi_xyxy
        im = im[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    if im.size == 0:
        return {"blur_var": 0.0, "dark_frac": 0.0, "bright_frac": 0.0}
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    lap = cv2.Laplacian(g, cv2.CV_64F)
    n = float(g.size)
    return {"blur_var": float(lap.var()), "dark_frac": float((g <= DARK_LEVEL).sum() / n), "bright_frac": float((g >= BRIGHT_LEVEL).sum() / n)}


def assess(stats: dict, ppu: int = REF_PPU) -> list[str]:
    """-> flags: blurry / underexposed / overexposed (empty = fine)."""
    flags = []
    if stats["blur_var"] < BLUR_VAR_MIN * (REF_PPU / ppu) ** BLUR_PPU_EXP:
        flags.append("blurry")
    if stats["dark_frac"] > DARK_FRAC_MAX:
        flags.append("underexposed")
    if stats["bright_frac"] > BRIGHT_FRAC_MAX:
        flags.append("overexposed")
    return flags
