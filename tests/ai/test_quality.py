"""Image quality heuristics (Spec §7.1): warn on blur / clipped exposure, never on ordinary photos."""
from __future__ import annotations

import cv2
import numpy as np

from ai.preprocessing import quality as Q
from ai.preprocessing.geometry import CANVAS_U


def _texture(seed=0, shape=(320, 768)):
    rng = np.random.default_rng(seed)
    g = rng.integers(40, 200, shape).astype(np.uint8)
    return cv2.cvtColor(cv2.resize(cv2.resize(g, (shape[1] // 4, shape[0] // 4)), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)


def test_sharp_texture_ok():
    st = Q.quality_stats(_texture())
    assert Q.assess(st, 64) == []


def test_blur_flagged():
    st = Q.quality_stats(cv2.GaussianBlur(_texture(), (0, 0), 6))
    assert "blurry" in Q.assess(st, 64)


def test_exposure_flags():
    black = np.zeros((100, 100, 3), np.uint8)
    white = np.full((100, 100, 3), 255, np.uint8)
    assert "underexposed" in Q.assess(Q.quality_stats(black), 64)
    assert "overexposed" in Q.assess(Q.quality_stats(white), 64)
    half = _texture()
    half[:, : half.shape[1] // 2] = 0                  # black keyboard half: not a warning by itself
    assert "underexposed" not in Q.assess(Q.quality_stats(half), 64)


def test_roi_and_scale(layout):
    roi = Q.block_roi_px(layout.regions_u, 64, CANVAS_U[:2])
    assert roi == (67, 67, 701, 253)                   # x: -0.45..9.45u, y: -0.45..2.45u, origin (-1.5, -1.5)u
    assert Q.quality_stats(np.zeros((0, 0, 3), np.uint8))["blur_var"] == 0.0
    # the blur bound is looser at higher ppu, where the same photo has smoother pixels
    st = {"blur_var": 10.0, "dark_frac": 0.0, "bright_frac": 0.0}
    assert Q.assess(st, 64) == ["blurry"] and Q.assess(st, 128) == []
