"""Shared fixtures for the fast AI tests: no Paddle / Torch, synthetic keyboards with colour-coded keycaps.

A synthetic keycap's colour encodes what a fake OCR would read: B = 30 + 8*k for letter k (A=0 .. Z=25),
R = 255 * ocr score, G = 250 marks an unreadable key (OCR returns empty text).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ai.layouts import load_layout  # noqa: E402
from ai.preprocessing.geometry import CANVAS_U, apply_H, homography  # noqa: E402
from ai.recognition.ocr import normalize_label  # noqa: E402

BASELINE_BUNDLE = REPO / "bundles" / "baseline_dev_v0"
UNREADABLE = "?"
# image positions of the Q, P, M, Z slot centres in the synthetic photo (mild perspective)
SYN_REF_PX = np.array([[210.0, 260.0], [1010.0, 240.0], [805.0, 525.0], [262.0, 545.0]])
SYN_WH = (1200, 800)


def key_color(letter: str | None, score: float = 0.9) -> tuple[int, int, int]:
    if letter is None or letter == UNREADABLE:
        return (128, 250, 40)
    k = ord(letter) - 65
    return (30 + 8 * k, 90, int(round(255 * score)))


class FakeReader:
    """Stands in for PaddleReader: decodes the colour code from the centre of each crop."""

    def __init__(self, raw_override: dict | None = None):
        self.calls = 0
        self.n_crops = 0
        self.raw_override = raw_override or {}           # letter -> raw OCR text to return instead (e.g. "Aฟ", "AS")

    def read_labels(self, crops):
        self.calls += 1
        self.n_crops += len(crops)
        out = []
        for c in crops:
            h, w = c.shape[:2]
            core = c[h // 4: max(h // 4 + 1, 3 * h // 4), w // 4: max(w // 4 + 1, 3 * w // 4)].reshape(-1, 3)
            b, g, r = np.median(core, axis=0)
            if g > 200:
                out.append((None, 0.0, ""))
                continue
            k = int(round((b - 30) / 8))
            if not 0 <= k < 26:
                out.append((None, 0.0, ""))
                continue
            raw = self.raw_override.get(chr(65 + k), chr(65 + k))
            out.append((normalize_label(raw), round(float(r) / 255, 3), raw))
        return out


def synth_keyboard(layout, keys: dict | None = None, *, scores: dict | None = None, wh=SYN_WH, ref_px=SYN_REF_PX, noise=12.0, seed=0,
                   blur: float = 0.0) -> np.ndarray:
    """Photo-like BGR image; `keys` maps slot_id -> letter shown on that keycap (default: the expected label)."""
    rng = np.random.default_rng(seed)
    w, h = wh
    img = np.clip(rng.normal(120, noise, (h, w, 3)), 0, 255).astype(np.uint8)
    G = homography(layout.ref_points_u, ref_px)            # u -> image px
    for j, sid in enumerate(layout.slot_ids):
        letter = (keys or {}).get(sid, layout.labels[j])
        cx, cy = layout.centers_u[j]
        quad_u = np.array([[cx - 0.42, cy - 0.42], [cx + 0.42, cy - 0.42], [cx + 0.42, cy + 0.42], [cx - 0.42, cy + 0.42]])
        quad = np.round(apply_H(G, quad_u)).astype(np.int32)
        cv2.fillPoly(img, [quad], key_color(letter, (scores or {}).get(sid, 0.9)))
    if noise:
        img = np.clip(img.astype(float) + rng.normal(0, noise / 2, img.shape), 0, 255).astype(np.uint8)
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    return img


def u_boxes_to_canvas_px(boxes_u: np.ndarray, ppu: int) -> np.ndarray:
    return (np.asarray(boxes_u, float) - np.tile(np.array(CANVAS_U[:2]), 2)) * ppu


class FakeDetector:
    """predict(canvases) -> [(boxes_px, scores)] from fixed u boxes (a stand-in for YOLO / Faster R-CNN)."""

    def __init__(self, boxes_u: np.ndarray, ppu: int, score: float = 0.9):
        self.boxes_px = u_boxes_to_canvas_px(boxes_u, ppu)
        self.scores = np.full(len(self.boxes_px), score)

    def predict(self, canvases):
        return [(self.boxes_px.copy(), self.scores.copy()) for _ in canvases]


def write_bundle(root: Path, **over) -> Path:
    meta = json.loads((BASELINE_BUNDLE / "bundle.json").read_text())
    meta.update(over)
    root.mkdir(parents=True, exist_ok=True)
    (root / "bundle.json").write_text(json.dumps(meta))
    return root


@pytest.fixture(scope="session")
def layout():
    return load_layout("qwerty_stagger_letters_v1")


@pytest.fixture
def fake_reader():
    return FakeReader()
