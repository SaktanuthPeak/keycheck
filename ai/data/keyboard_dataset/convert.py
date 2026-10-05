"""COCO (original_oriented, decision D6) -> YOLO on rectified canvases, and -> torchvision detection targets (plan P2.D).

Class ids: COCO `keycap` = 1 -> YOLO class 0 -> torchvision label 1 (0 is background in torchvision detection models).
Boxes are mapped to the canvas with the image's 4 reference points (ai.preprocessing.geometry); training copies can
use jittered points to imitate tap error (val/test always use the annotated points).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from ai.data.keyboard_dataset.imaging import load_oriented_bgr
from ai.data.keyboard_dataset.schema import COCO_KEYCAP_ID, Dataset, ImageMeta, coco_index, coco_xyxy
from ai.data.rectify_dataset import jitter_points, rectify_boxes
from ai.layouts import Layout
from ai.preprocessing import geometry as g

YOLO_CLASS = 0
TV_BACKGROUND = 0
TV_KEYCAP = 1
MIN_VISIBLE = 0.5


def _rng(*parts) -> np.random.Generator:
    h = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def image_H(ref_px: np.ndarray, layout: Layout, ppu: int, extent_u=g.CANVAS_U) -> np.ndarray:
    """original_oriented px -> rectified canvas px."""
    return g.original_to_canvas_H(np.asarray(ref_px, float), layout.ref_points_u, ppu, extent_u)


def xyxy_to_yolo(b, w: int, h: int, cls: int = YOLO_CLASS) -> str:
    return f"{cls} {(b[0] + b[2]) / 2 / w:.6f} {(b[1] + b[3]) / 2 / h:.6f} {(b[2] - b[0]) / w:.6f} {(b[3] - b[1]) / h:.6f}"


def yolo_to_xyxy(line: str, w: int, h: int) -> tuple[int, np.ndarray]:
    c, cx, cy, bw, bh = line.split()
    cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
    return int(c), np.array([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2])


def canvas_box_to_original(H: np.ndarray, box_xyxy) -> np.ndarray:
    """Canvas box -> 4-corner polygon on original_oriented (TL TR BR BL), via H inverse (Spec §7.2)."""
    x0, y0, x1, y1 = box_xyxy
    return g.apply_H(g.invert_H(H), np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float))


def keycap_boxes(entry: dict | None) -> np.ndarray:
    if not entry:
        return np.zeros((0, 4))
    bx = [coco_xyxy(a) for a in entry["anns"] if a.get("category_id") == COCO_KEYCAP_ID]
    return np.array(bx, float).reshape(-1, 4)


def _splits(ds: Dataset, split_of: dict[str, str] | None) -> dict[str, str]:
    return split_of if split_of is not None else {im.image_id: im.split for im in ds.images if im.split}


def coco_to_yolo(ds: Dataset, layout: Layout, out_dir: str | Path, *, split_of: dict[str, str] | None = None,
                 ppu: int | None = None, train_jitter: list[tuple[str, float]] | None = None,
                 min_visible: float = MIN_VISIBLE, write_images: bool = True, jpeg_quality: int = 92) -> dict:
    """Write `images/<split>/*.jpg`, `labels/<split>/*.txt`, `data.yaml`, `index.json`. Returns the index.

    `train_jitter`: [(variant_name, sigma_u)] for Train; default only the annotated points ("gt", 0).
    Images without reference points (e.g. web photos) are skipped and listed under `skipped`.
    """
    ppu = ppu or layout.px_per_unit
    out = Path(out_dir)
    split_of = _splits(ds, split_of)
    w, h = g.canvas_size(ppu)
    idx = coco_index(ds.coco, ds.images)
    rows, skipped = [], []
    for im in sorted(ds.images, key=lambda i: i.image_id):
        sp = split_of.get(im.image_id)
        if sp not in ("train", "val", "test"):
            continue
        if im.ref_px is None:
            skipped.append({"image_id": im.image_id, "reason": "no_ref_points"})
            continue
        if im.image_id not in idx:
            skipped.append({"image_id": im.image_id, "reason": "no_annotation"})
            continue
        boxes = keycap_boxes(idx[im.image_id])
        variants = (train_jitter or [("gt", 0.0)]) if sp == "train" else [("gt", 0.0)]
        img = load_oriented_bgr(ds.image_path(im)) if write_images else None
        (out / "images" / sp).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sp).mkdir(parents=True, exist_ok=True)
        for vname, sigma in variants:
            pts = im.ref_px if sigma == 0 else jitter_points(im.ref_px, sigma, _rng(im.image_id, vname))
            H = image_H(pts, layout, ppu)
            rb = rectify_boxes(boxes, H, w, h, min_visible)
            name = f"{im.image_id}__{vname}"
            if img is not None:
                cv2.imwrite(str(out / "images" / sp / f"{name}.jpg"), g.warp(img, H, (w, h)), [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            (out / "labels" / sp / f"{name}.txt").write_text("\n".join(xyxy_to_yolo(b, w, h) for b in rb) + ("\n" if rb else ""))
            rows.append({"name": name, "image_id": im.image_id, "split": sp, "variant": vname, "H": H.tolist(),
                         "n_boxes_in": int(len(boxes)), "n_boxes_out": len(rb)})
    names = sorted({r["split"] for r in rows})
    yaml_lines = [f"path: {out.resolve()}"] + [f"{s}: images/{s}" for s in names] + ["names:", f"  {YOLO_CLASS}: keycap"]
    (out / "data.yaml").write_text("\n".join(yaml_lines) + "\n")
    index = {"layout_id": layout.layout_id, "px_per_unit": ppu, "canvas_wh": [w, h], "extent_u": list(g.CANVAS_U),
             "min_visible": min_visible, "items": rows, "skipped": skipped}
    (out / "index.json").write_text(json.dumps(index, indent=1))
    return index


def coco_to_torchvision(ds: Dataset, *, split_of: dict[str, str] | None = None, splits=("train", "val", "test"),
                        layout: Layout | None = None, ppu: int | None = None, min_visible: float = MIN_VISIBLE) -> list[dict]:
    """Per image: {"image_id", "path", "split", "boxes" (N,4 float32 xyxy), "labels" (N int64, all 1), "area", "iscrowd",
    "H" (only when rectified)}. With `layout` the boxes are on the rectified canvas, otherwise on original_oriented."""
    split_of = _splits(ds, split_of)
    idx = coco_index(ds.coco, ds.images)
    out = []
    for im in sorted(ds.images, key=lambda i: i.image_id):
        sp = split_of.get(im.image_id)
        if sp not in splits or im.image_id not in idx:
            continue
        bx = keycap_boxes(idx[im.image_id])
        item: dict = {"image_id": im.image_id, "path": str(ds.image_path(im)), "split": sp}
        if layout is not None:
            if im.ref_px is None:
                continue
            p = ppu or layout.px_per_unit
            H = image_H(im.ref_px, layout, p)
            bx = np.array(rectify_boxes(bx, H, *g.canvas_size(p), min_visible), float).reshape(-1, 4)
            item["H"] = H
            item["canvas_wh"] = g.canvas_size(p)
        item["boxes"] = bx.astype(np.float32)
        item["labels"] = np.full(len(bx), TV_KEYCAP, np.int64)
        item["area"] = ((bx[:, 2] - bx[:, 0]) * (bx[:, 3] - bx[:, 1])).astype(np.float32)
        item["iscrowd"] = np.zeros(len(bx), np.int64)
        out.append(item)
    return out


class TorchvisionKeycaps:
    """Minimal map-style dataset for torchvision detection models: (image tensor CHW float [0,1] RGB, target dict).

    torch is imported lazily so the rest of this module works without the `detector` extra.
    """

    def __init__(self, items: list[dict], transforms=None):
        self.items = items
        self.transforms = transforms

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        import torch
        it = self.items[i]
        img = load_oriented_bgr(it["path"])
        if "H" in it:
            img = g.warp(img, it["H"], tuple(it["canvas_wh"]))
        t = torch.from_numpy(img[:, :, ::-1].copy()).permute(2, 0, 1).float() / 255.0
        target = {"boxes": torch.as_tensor(it["boxes"]).reshape(-1, 4), "labels": torch.as_tensor(it["labels"]),
                  "image_id": i, "area": torch.as_tensor(it["area"]), "iscrowd": torch.as_tensor(it["iscrowd"])}
        if self.transforms is not None:
            t, target = self.transforms(t, target)
        return t, target


def image_meta_H(im: ImageMeta, layout: Layout, ppu: int | None = None) -> np.ndarray:
    return image_H(im.ref_px, layout, ppu or layout.px_per_unit)
