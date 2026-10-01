"""Homography and coordinate helpers (Spec §7.2). Coordinates: `original` px, `rectified` px, canonical `u`."""
from __future__ import annotations

import cv2
import numpy as np

# Default canvas extent in u for the letter block: x in [-1.5, 10.5], y in [-1.5, 3.5] (plan Q2).
CANVAS_U = (-1.5, -1.5, 10.5, 3.5)


def canvas_size(px_per_unit: int, extent_u=CANVAS_U) -> tuple[int, int]:
    x0, y0, x1, y1 = extent_u
    return int(round((x1 - x0) * px_per_unit)), int(round((y1 - y0) * px_per_unit))


def u_to_canvas_matrix(px_per_unit: int, extent_u=CANVAS_U) -> np.ndarray:
    x0, y0, _, _ = extent_u
    s = float(px_per_unit)
    return np.array([[s, 0, -x0 * s], [0, s, -y0 * s], [0, 0, 1.0]])


def validate_reference_points(pts: np.ndarray, image_wh: tuple[int, int] | None = None, min_area_frac=0.002) -> str | None:
    """Return an error string or None. Order TL, TR, BR, BL; convex, non-crossing, in-image, large enough."""
    pts = np.asarray(pts, float)
    if pts.shape != (4, 2) or not np.all(np.isfinite(pts)):
        return "bad shape"
    if image_wh is not None:
        w, h = image_wh
        if (pts[:, 0] < 0).any() or (pts[:, 1] < 0).any() or (pts[:, 0] > w).any() or (pts[:, 1] > h).any():
            return "outside image"
    cross = []
    for i in range(4):
        a, b, c = pts[i], pts[(i + 1) % 4], pts[(i + 2) % 4]
        cross.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
    cross = np.array(cross)
    if not (np.all(cross > 0) or np.all(cross < 0)):
        return "not convex / crossing"
    area = 0.5 * abs(sum(pts[i, 0] * pts[(i + 1) % 4, 1] - pts[(i + 1) % 4, 0] * pts[i, 1] for i in range(4)))
    if image_wh is not None and area < min_area_frac * image_wh[0] * image_wh[1]:
        return "area too small"
    return None


def homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    return cv2.getPerspectiveTransform(np.asarray(src, np.float32), np.asarray(dst, np.float32)).astype(float)


def original_to_canvas_H(ref_px: np.ndarray, ref_u: np.ndarray, px_per_unit: int, extent_u=CANVAS_U) -> np.ndarray:
    """H mapping original pixels -> rectified canvas pixels, from 4 tapped points and their canonical u coords."""
    return u_to_canvas_matrix(px_per_unit, extent_u) @ homography(ref_px, ref_u)


def apply_H(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, float).reshape(-1, 2)
    ph = np.c_[pts, np.ones(len(pts))] @ H.T
    return ph[:, :2] / ph[:, 2:3]


def invert_H(H: np.ndarray) -> np.ndarray:
    return np.linalg.inv(H)


def warp(image: np.ndarray, H: np.ndarray, size_wh: tuple[int, int]) -> np.ndarray:
    return cv2.warpPerspective(image, H, size_wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def transform_box(H: np.ndarray, box_xyxy) -> np.ndarray:
    """Map all four corners through H and return the axis-aligned xyxy bound."""
    x0, y0, x1, y1 = box_xyxy
    p = apply_H(H, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
    return np.array([p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()])


def box_center(b) -> np.ndarray:
    return np.array([(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0])


def clip_box(b, w: int, h: int):
    """Clip xyxy to canvas; return (clipped, visible_fraction)."""
    area = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    c = np.array([max(0.0, b[0]), max(0.0, b[1]), min(float(w), b[2]), min(float(h), b[3])])
    ca = max(0.0, c[2] - c[0]) * max(0.0, c[3] - c[1])
    return c, (ca / area if area > 0 else 0.0)


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def generic_letterblock_error(ref_px: np.ndarray, ref_u: np.ndarray, gt_centers_px: np.ndarray, gt_centers_u: np.ndarray) -> np.ndarray:
    """Per-slot error (in u) when predicting letter positions from the 4 reference points alone."""
    H = homography(ref_px, ref_u)            # original px -> u
    pred_u = apply_H(H, gt_centers_px)
    return np.linalg.norm(pred_u - gt_centers_u, axis=1)
