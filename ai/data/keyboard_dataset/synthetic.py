"""Synthetic stand-in for the own QWERTY dataset: flat "keycaps" whose grey level encodes the letter.

Used by the unit tests and `cli demo` to exercise manifest / split / validator / converter / pilot end to end before
real photos exist. `CodeReader` is the matching fake OCR (same `read_labels` interface as PaddleReader).
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import cv2
import numpy as np

from ai.data.keyboard_dataset import arrangement as A
from ai.data.keyboard_dataset.schema import (ARRANGEMENTS_CSV, COCO_JSON, COCO_KEYCAP_ID, COCO_KEYCAP_NAME, IMAGE_COLS,
                                             IMAGES_CSV, IMAGES_DIR, KEYBOARD_COLS, KEYBOARDS_CSV, REF_COLS, SLOT_COLS,
                                             SLOTS_CSV, write_csv)
from ai.layouts import Layout
from ai.preprocessing import geometry as g

LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
CODE = {L: 30 + 7 * k for k, L in enumerate(LETTERS)}          # grey level per letter
NONLETTER_CODE = 245
BG = 8
KEY_HALF_U = 0.42
EXTRA_KEYS_U = ((10.0, 0.0), (9.25, 1.0), (7.75, 2.0))           # [ ; / -like keys right of the letter block
BASE_REF = np.array([[100, 110], [640, 110], [505, 230], [145, 230]], float)


def _random_view(rng: random.Random) -> np.ndarray:
    """New camera pose per arrangement: rotation, scale, shift and a little perspective."""
    ang = np.radians(rng.uniform(-8, 8))
    sc = rng.uniform(0.75, 1.05)
    R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]]) * sc
    c = BASE_REF.mean(0)
    pts = (BASE_REF - c) @ R.T + c + [rng.uniform(-35, 35), rng.uniform(-30, 30)]
    return pts + np.array([rng.uniform(-8, 8) for _ in range(8)]).reshape(4, 2)


def render(layout: Layout, ref_px: np.ndarray, actual: dict[str, str], wh=(800, 400), *, row_offset_u: dict | None = None,
           unreadable: set | None = None, misprint: dict | None = None):
    """-> (BGR image, [(xyxy, slot_id | None)]). `row_offset_u` shifts whole rows in x (non-generic geometry)."""
    W, Hh = wh
    img = np.full((Hh, W, 3), BG, np.uint8)
    H = g.homography(layout.ref_points_u, ref_px)                      # u -> original px
    row_offset_u, unreadable, misprint = row_offset_u or {}, unreadable or set(), misprint or {}
    boxes = []

    def key(c_u, val, sid):
        c = np.asarray(c_u, float)
        corners = np.array([c + [-KEY_HALF_U, -KEY_HALF_U], c + [KEY_HALF_U, -KEY_HALF_U], c + [KEY_HALF_U, KEY_HALF_U], c + [-KEY_HALF_U, KEY_HALF_U]])
        poly = g.apply_H(H, corners)
        cv2.fillConvexPoly(img, np.round(poly).astype(np.int32), (val, val, val), lineType=cv2.LINE_8)
        x0, y0 = poly.min(0)
        x1, y1 = poly.max(0)
        boxes.append(([float(x0), float(y0), float(x1), float(y1)], sid))

    for j, sid in enumerate(layout.slot_ids):
        row = A.row_of(sid)
        c = layout.centers_u[j] + [row_offset_u.get(row, 0.0), 0.0]
        val = CODE[misprint.get(sid, actual[sid])] + (3.5 if sid in unreadable else 0)
        key(c, int(round(val)), sid)
    for c in EXTRA_KEYS_U:
        key(c, NONLETTER_CODE, None)
    return img, boxes


class CodeReader:
    """Fake OCR for `render` images: median grey of the crop centre -> nearest letter code (None if ambiguous)."""

    def __init__(self, tol: float = 2.0, keep: float = 0.4):
        self.tol, self.keep, self.calls = tol, keep, 0

    def read_labels(self, crops):
        out = []
        for c in crops:
            self.calls += 1
            h, w = c.shape[:2]
            a, b = int(h * (1 - self.keep) / 2), int(w * (1 - self.keep) / 2)
            core = c[a:max(a + 1, h - a), b:max(b + 1, w - b)]
            v = float(np.median(core.reshape(-1, c.shape[2]).mean(axis=1))) if core.size else 0.0
            L = min(LETTERS, key=lambda x: abs(CODE[x] - v))
            if abs(CODE[L] - v) <= self.tol:
                out.append((L, 0.99, L))
            else:
                out.append((None, 0.2, f"~{v:.0f}"))
        return out


DEFAULT_KEYBOARDS = [
    {"keyboard_id": "kb01", "legend_style": "en_only", "role": "train"},
    {"keyboard_id": "kb02", "legend_style": "th_en", "role": "train", "unreadable": ["r1c3", "r1c4"]},
    {"keyboard_id": "kb03", "legend_style": "en_only", "role": "train", "row_offset_u": {1: 0.6}},
    {"keyboard_id": "kb04", "legend_style": "en_only", "role": "train"},
    {"keyboard_id": "kb05", "legend_style": "th_en", "role": "heldout_val"},
    {"keyboard_id": "kb06", "legend_style": "th_en", "role": "unseen_test"},
    {"keyboard_id": "kb07", "legend_style": "en_only", "role": "unseen_test"},
]


def make_dataset(root: str | Path, layout: Layout, *, seed: int = 0, keyboards=None, sessions: int = 2,
                 arrangements_per_session: int = 3, shots: int = 2, wh=(800, 400), with_coco: bool = True) -> dict:
    """Write a complete synthetic dataset (images, metadata CSVs, COCO with `slot_id` attributes, schedule)."""
    root = Path(root)
    rng = random.Random(seed)
    keyboards = keyboards or DEFAULT_KEYBOARDS
    n_arr = len(keyboards) * sessions * arrangements_per_session
    sched = A.generate_schedule(layout, seed=seed, n_correct=max(1, n_arr // 4), n_one_pair=max(1, n_arr // 2),
                                n_multi=max(1, n_arr - n_arr // 4 - n_arr // 2), n_reserved_pairs=2, test_only_fraction=0.1)
    pool = list(sched)
    by_kb: dict[str, list] = {}
    for kb in keyboards:                       # every keyboard gets sessions × arrangements_per_session distinct rows
        need, mine = sessions * arrangements_per_session, []
        for a in list(pool):
            if len(mine) == need:
                break
            if a.test_only and kb["role"] == "heldout_val":
                continue
            mine.append(a)
            pool.remove(a)
            a.keyboard_id = kb["keyboard_id"]
        by_kb[kb["keyboard_id"]] = mine
    A.write_schedule(sched, layout, root / ARRANGEMENTS_CSV)
    (root / IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    img_rows, slot_rows, coco_imgs, coco_anns = [], [], [], []
    for kb in keyboards:
        kid = kb["keyboard_id"]
        arrs = by_kb.get(kid, [])
        k = 0
        for s in range(sessions):
            sess = f"{kid}_s{s + 1:02d}"
            for _ in range(arrangements_per_session):
                if k >= len(arrs):
                    break
                arr = arrs[k]
                k += 1
                actual = A.actual_labels(arr, layout)
                ref0 = _random_view(rng)
                for shot in range(shots):
                    ref = ref0 + (shot * 0.5)                    # burst: almost the same frame
                    img, boxes = render(layout, ref, actual, wh, row_offset_u=kb.get("row_offset_u"),
                                        unreadable=set(kb.get("unreadable", [])), misprint=kb.get("misprint"))
                    iid = f"{sess}_{arr.arrangement_id}_{shot}"
                    fn = f"{kid}/{iid}.png"
                    (root / IMAGES_DIR / kid).mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(root / IMAGES_DIR / fn), img)
                    row = {"image_id": iid, "file_name": fn, "keyboard_id": kid, "capture_session_id": sess,
                           "arrangement_id": arr.arrangement_id, "device": "synthetic", "lighting": "indoor_cool",
                           "source": "own_capture", "license": "own", "width": wh[0], "height": wh[1], "subset": "main"}
                    row.update(dict(zip(REF_COLS, np.round(ref, 2).ravel().tolist())))
                    img_rows.append(row)
                    for sid in layout.slot_ids:
                        slot_rows.append({"image_id": iid, "slot_id": sid, "expected_label": layout.labels[layout.index(sid)],
                                          "actual_label": actual[sid], "readable": 1, "ground_truth_status": "verified"})
                    cid = len(coco_imgs) + 1
                    coco_imgs.append({"id": cid, "file_name": fn, "width": wh[0], "height": wh[1]})
                    for b, sid in boxes:
                        ann = {"id": len(coco_anns) + 1, "image_id": cid, "category_id": COCO_KEYCAP_ID,
                               "bbox": [b[0], b[1], b[2] - b[0], b[3] - b[1]], "area": (b[2] - b[0]) * (b[3] - b[1]), "iscrowd": 0}
                        if sid:
                            ann["attributes"] = {"slot_id": sid}
                        coco_anns.append(ann)
    write_csv(root / IMAGES_CSV, IMAGE_COLS, img_rows)
    write_csv(root / SLOTS_CSV, SLOT_COLS, slot_rows)
    write_csv(root / KEYBOARDS_CSV, KEYBOARD_COLS, [{"keyboard_id": k["keyboard_id"], "form_factor": "ANSI-TKL",
                                                     "legend_style": k["legend_style"], "legend_position": "top_left",
                                                     "keycap_color": "black", "legend_color": "white", "profile": "OEM",
                                                     "removable_keycaps": 1, "role": k["role"]} for k in keyboards])
    if with_coco:
        coco = {"info": {"description": "synthetic"}, "images": coco_imgs, "annotations": coco_anns,
                "categories": [{"id": COCO_KEYCAP_ID, "name": COCO_KEYCAP_NAME}]}
        (root / COCO_JSON).parent.mkdir(parents=True, exist_ok=True)
        (root / COCO_JSON).write_text(json.dumps(coco))
    return {"n_images": len(img_rows), "schedule": sched}
