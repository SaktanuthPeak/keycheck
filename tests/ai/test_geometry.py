"""Spec §16.1: H round trip, EXIF orientation, generic reference points, point validation."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageOps

from ai.inference.images import load_oriented_bgr
from ai.preprocessing.geometry import (CANVAS_U, apply_H, canvas_size, homography, invert_H, original_to_canvas_H, transform_box,
                                       u_to_canvas_matrix, validate_reference_points)

REF_PX = np.array([[210.0, 260.0], [1010.0, 240.0], [805.0, 525.0], [262.0, 545.0]])


def test_h_round_trip(layout):
    H = original_to_canvas_H(REF_PX, layout.ref_points_u, 64)
    pts = np.random.default_rng(0).uniform([0, 0], [1200, 800], (200, 2))
    back = apply_H(invert_H(H), apply_H(H, pts))
    assert np.abs(back - pts).max() < 1e-6


def test_reference_points_land_on_canonical_u(layout):
    ppu = 64
    H = original_to_canvas_H(REF_PX, layout.ref_points_u, ppu)
    canvas_pts = apply_H(H, REF_PX)
    expect = apply_H(u_to_canvas_matrix(ppu), layout.ref_points_u)
    assert np.abs(canvas_pts - expect).max() < 1e-6
    to_u = homography(REF_PX, layout.ref_points_u)
    assert np.allclose(apply_H(to_u, REF_PX), [[0, 0], [9, 0], [6.75, 2], [0.75, 2]], atol=1e-9)


def test_canvas_covers_letter_block(layout):
    w, h = canvas_size(64)
    assert (w, h) == (768, 320)
    x0, y0, x1, y1 = CANVAS_U
    assert layout.regions_u[:, 0].min() > x0 and layout.regions_u[:, 2].max() < x1
    assert layout.regions_u[:, 1].min() > y0 and layout.regions_u[:, 3].max() < y1


def test_box_corners_round_trip_through_original(layout):
    """Detection box (canvas px) -> 4 corners on the original photo (a general quad) -> back onto the canvas."""
    H = original_to_canvas_H(REF_PX, layout.ref_points_u, 96)
    box = np.array([100.0, 120.0, 160.0, 190.0])
    corners = np.array([[box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]])
    on_photo = apply_H(invert_H(H), corners)
    assert np.abs(apply_H(H, on_photo) - corners).max() < 1e-6
    bound = transform_box(H, transform_box(invert_H(H), box))       # axis-aligned bounds only grow
    assert bound[0] <= box[0] + 1e-6 and bound[1] <= box[1] + 1e-6 and bound[2] >= box[2] - 1e-6 and bound[3] >= box[3] - 1e-6


@pytest.mark.parametrize("pts,ok", [
    (REF_PX, True),
    (REF_PX[[0, 2, 1, 3]], False),                     # crossing (bow tie)
    (REF_PX[[1, 0, 3, 2]], True),                      # mirrored but still a simple quad (orientation is checked by fit/OCR)
    (np.array([[0, 0], [5, 0], [5, 5], [0, 5]], float), False),   # too small
    (REF_PX + [0, 400], False),                        # outside image
    (REF_PX[:3], False),
    (np.array([[0, 0], [np.nan, 0], [5, 5], [0, 5]]), False),
])
def test_validate_reference_points(pts, ok):
    err = validate_reference_points(np.asarray(pts, float), (1200, 800))
    assert (err is None) == ok


def _marker_image(w=300, h=200) -> Image.Image:
    a = np.full((h, w, 3), 60, np.uint8)
    a[30:50, 220:250] = (250, 30, 30)                  # red marker near the top-right
    a[150:170, 20:40] = (30, 250, 30)                  # green marker near the bottom-left
    return Image.fromarray(a)


def _centroid(bgr: np.ndarray, channel: int) -> np.ndarray:
    m = (bgr[:, :, channel] > 200) & (bgr.max(axis=2) - bgr.min(axis=2) > 120)
    ys, xs = np.nonzero(m)
    return np.array([xs.mean() / bgr.shape[1], ys.mean() / bgr.shape[0]])


def test_exif_rotated_matches_upright(tmp_path):
    im = _marker_image()
    up = tmp_path / "upright.jpg"
    im.save(up, quality=95)
    rot = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6                                   # stored rotated; viewer must rotate 90° CW
    im.transpose(Image.Transpose.ROTATE_90).save(rot, quality=95, exif=exif.tobytes())
    raw = np.asarray(Image.open(rot))
    assert raw.shape[:2] == (300, 200)                 # stored pixels really are rotated
    assert ImageOps.exif_transpose(Image.open(rot)).size == (300, 200)
    a, b = load_oriented_bgr(up), load_oriented_bgr(rot.read_bytes())
    assert a.shape == b.shape == (200, 300, 3)
    for ch in (2, 1):                                  # BGR: red=2, green=1
        assert np.abs(_centroid(a, ch) - _centroid(b, ch)).max() < 0.01
    assert np.abs(a.astype(int) - b.astype(int)).mean() < 4
