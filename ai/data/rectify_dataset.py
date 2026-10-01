"""Stage Q2: rectified detector dataset + evaluation scenarios S1–S4 (plan §5 Q2).

Rectified canvas = u ∈ [-1.5,10.5]×[-1.5,3.5] at `px_per_unit` pixels per u. Boxes for eval scenarios are stored in
canonical u (canvas_px = (u - origin_u) * ppu), so they are valid for every ppu.
"""
from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from ai.data.synthetic_swap import make_swaps
from ai.layouts import Layout, load_layout
from ai.preprocessing import geometry as g

ORIGIN_U = np.array(g.CANVAS_U[:2], float)


def _rng(*parts) -> np.random.Generator:
    h = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def jitter_points(ref_px: np.ndarray, sigma_u: float, rng) -> np.ndarray:
    """Gaussian tap noise; σ is in key pitches, converted to px with the local pitch |P-Q|/9."""
    pitch = np.linalg.norm(ref_px[1] - ref_px[0]) / 9.0
    return ref_px + rng.normal(0.0, sigma_u * pitch, ref_px.shape)


def shift_points(ref_px: np.ndarray, slots: float = 1.0) -> np.ndarray:
    """S4a: every tapped point moved one key along the row direction."""
    return ref_px + (ref_px[1] - ref_px[0]) / 9.0 * slots


def rectify_boxes(boxes_xyxy, H, w, h, min_visible):
    out = []
    for b in boxes_xyxy:
        tb = g.transform_box(H, b)
        c = g.box_center(tb)
        if not (0 <= c[0] < w and 0 <= c[1] < h):
            continue
        cb, vis = g.clip_box(tb, w, h)
        if vis < min_visible or cb[2] - cb[0] < 2 or cb[3] - cb[1] < 2:
            continue
        out.append(cb)
    return out


def _yolo_line(b, w, h):
    return f"0 {(b[0] + b[2]) / 2 / w:.6f} {(b[1] + b[3]) / 2 / h:.6f} {(b[2] - b[0]) / w:.6f} {(b[3] - b[1]) / h:.6f}"


def _train_job(args):
    (img_path, stem, split, ref_px, boxes, ppu, variants, out_root, min_visible, file_name) = args
    img = cv2.imread(str(img_path))
    if img is None:
        return []
    w, h = g.canvas_size(ppu)
    lay_ref = np.array([[0, 0], [9, 0], [6.75, 2], [0.75, 2]], float)
    rows = []
    for vname, sigma in variants:
        pts = ref_px if sigma == 0 else jitter_points(ref_px, sigma, _rng(file_name, vname))
        H = g.original_to_canvas_H(pts, lay_ref, ppu)
        canvas = g.warp(img, H, (w, h))
        rb = rectify_boxes(boxes, H, w, h, min_visible)
        name = f"{stem}__{vname}"
        d = Path(out_root)
        cv2.imwrite(str(d / "images" / split / f"{name}.jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
        (d / "labels" / split / f"{name}.txt").write_text("\n".join(_yolo_line(b, w, h) for b in rb))
        rows.append({"file_name": f"images/{split}/{name}.jpg", "width": w, "height": h, "source_id": stem,
                     "boxes": [b.tolist() for b in rb], "variant": vname})
    return rows


def _eval_job(args):
    (img_path, key, ref_sets, slot_boxes, ppus, out_root, min_visible) = args
    img = cv2.imread(str(img_path))
    if img is None:
        return None
    lay_ref = np.array([[0, 0], [9, 0], [6.75, 2], [0.75, 2]], float)
    boxes_u: dict[str, dict] = {}
    for pname, pts in ref_sets.items():
        pts = np.array(pts, float)
        Hu = g.u_to_canvas_matrix(1) @ g.homography(pts, lay_ref)        # original px -> (u - origin)
        boxes_u[pname] = {s: (g.transform_box(Hu, b) + np.tile(ORIGIN_U, 2)).tolist() for s, b in slot_boxes.items()}
        for ppu in ppus:
            H = g.original_to_canvas_H(pts, lay_ref, ppu)
            canvas = g.warp(img, H, g.canvas_size(ppu))
            p = Path(out_root) / f"ppu{ppu}" / pname / f"{key}.jpg"
            cv2.imwrite(str(p), canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return boxes_u


def _synth_job(args):
    (key, split, ppus, out_root, boxes_u, swaps) = args
    res = {}
    for ppu in ppus:
        src = cv2.imread(str(Path(out_root) / f"ppu{ppu}" / "gt" / f"{key}.jpg"))
        if src is None:
            continue
        for kind, perm in swaps.items():
            out = src.copy()
            for dst_slot, src_slot in perm.items():
                s = (np.array(boxes_u[src_slot]).reshape(2, 2) - ORIGIN_U) * ppu
                d = (np.array(boxes_u[dst_slot]).reshape(2, 2) - ORIGIN_U) * ppu
                sx0, sy0, sx1, sy1 = [int(round(v)) for v in (s[0, 0], s[0, 1], s[1, 0], s[1, 1])]
                dx0, dy0, dx1, dy1 = [int(round(v)) for v in (d[0, 0], d[0, 1], d[1, 0], d[1, 1])]
                crop = src[max(0, sy0):sy1, max(0, sx0):sx1]
                if crop.size == 0 or dx1 <= dx0 or dy1 <= dy0:
                    continue
                out[max(0, dy0):dy1, max(0, dx0):dx1] = cv2.resize(crop, (min(dx1, out.shape[1]) - max(0, dx0), min(dy1, out.shape[0]) - max(0, dy0)))
            p = Path(out_root) / f"ppu{ppu}" / f"synth_{kind}" / f"{key}.jpg"
            p.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(p), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return key


def run_q2(out_dir: Path, *, q1_dir: Path, dataset_root: str | Path, cfg: dict, ppus=(64, 96, 128), max_workers: int | None = None, seed: int = 0) -> dict:
    q1_dir, dataset_root = Path(q1_dir), Path(dataset_root)
    coco = json.loads((q1_dir / "coco.json").read_text())
    slot_gt = json.loads((q1_dir / "slot_gt.json").read_text())
    split_m = json.loads((q1_dir / "split_manifest.json").read_text())
    seen_brand = {}
    layout = load_layout(cfg["layout_id"])
    lay_swap = load_layout(cfg["swap_layout_id"])
    q2c = cfg["q2"]
    boxes_by_img: dict[int, list] = {}
    for a in coco["annotations"]:
        if a["category_id"] == 1:
            x, y, w, h = a["bbox"]
            boxes_by_img.setdefault(a["image_id"], []).append((x, y, x + w, y + h))
    imgs = [i for i in coco["images"] if i["split"] in ("train", "val", "test")]
    train_groups = {i["brand_group"] for i in imgs if i["split"] == "train"}
    workers = max_workers or min(8, os.cpu_count() or 2)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {"ppus": list(ppus), "counts": {}}

    # ---- detector datasets: original (reference) and rectified_ppu<N>
    for ppu in ppus:
        root = out_dir / f"rectified_ppu{ppu}"
        for s in ("train", "val", "test"):
            (root / "images" / s).mkdir(parents=True, exist_ok=True)
            (root / "labels" / s).mkdir(parents=True, exist_ok=True)
        (root / "annotations").mkdir(exist_ok=True)
    orig = out_dir / "original"
    for s in ("train", "val", "test"):
        (orig / "images" / s).mkdir(parents=True, exist_ok=True)
        (orig / "labels" / s).mkdir(parents=True, exist_ok=True)
    (orig / "annotations").mkdir(exist_ok=True)

    train_variants = [("gt", 0.0)] + [(f"j{k}", q2c["jitter_sigmas_u"][k % len(q2c["jitter_sigmas_u"])]) for k in range(q2c["train_jitter_variants"])]
    eval_variants = [("gt", 0.0)]
    jobs = {ppu: [] for ppu in ppus}
    orig_coco = {s: {"images": [], "annotations": [], "categories": [{"id": 1, "name": "keycap"}]} for s in ("train", "val", "test")}
    for im in imgs:
        s = im["split"]
        stem = Path(im["file_name"]).stem
        src = dataset_root / im["file_name"]
        bx = boxes_by_img.get(im["id"], [])
        if not bx:
            continue
        # original-image reference set (symlink + YOLO labels)
        link = orig / "images" / s / src.name
        if not link.exists():
            try:
                os.symlink(src.resolve(), link)
            except OSError:
                import shutil
                shutil.copy(src, link)
        (orig / "labels" / s / f"{src.stem}.txt").write_text("\n".join(
            f"0 {(b[0]+b[2])/2/im['width']:.6f} {(b[1]+b[3])/2/im['height']:.6f} {(b[2]-b[0])/im['width']:.6f} {(b[3]-b[1])/im['height']:.6f}" for b in bx))
        orig_coco[s]["images"].append({"id": im["id"], "file_name": f"images/{s}/{src.name}", "width": im["width"], "height": im["height"]})
        for b in bx:
            orig_coco[s]["annotations"].append({"id": len(orig_coco[s]["annotations"]) + 1, "image_id": im["id"], "category_id": 1,
                                                "bbox": [b[0], b[1], b[2] - b[0], b[3] - b[1]], "iscrowd": 0, "area": (b[2] - b[0]) * (b[3] - b[1])})
        sg = slot_gt.get(im["file_name"])
        if sg is None or (s != "train" and im["eval_set"] not in ("main",)):
            continue            # rectified detector set needs the 4 GT reference points; val/test detector data = main eval images
        for ppu in ppus:
            jobs[ppu].append((src, stem, s, np.array(sg["ref_px"], float), bx, ppu, train_variants if s == "train" else eval_variants,
                              str(out_dir / f"rectified_ppu{ppu}"), q2c["min_visible"], im["file_name"]))
    for s in orig_coco:
        (orig / "annotations" / f"{s}.json").write_text(json.dumps(orig_coco[s]))
    (orig / "data.yaml").write_text(f"path: {orig.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: keycap\n")
    for ppu in ppus:
        root = out_dir / f"rectified_ppu{ppu}"
        coco_out = {s: {"images": [], "annotations": [], "categories": [{"id": 1, "name": "keycap"}]} for s in ("train", "val", "test")}
        with ProcessPoolExecutor(workers) as ex:
            for rows in ex.map(_train_job, jobs[ppu], chunksize=16):
                for r in rows:
                    s = r["file_name"].split("/")[1]
                    iid = len(coco_out[s]["images"]) + 1
                    coco_out[s]["images"].append({"id": iid, **{k: r[k] for k in ("file_name", "width", "height", "source_id", "variant")}})
                    for b in r["boxes"]:
                        coco_out[s]["annotations"].append({"id": len(coco_out[s]["annotations"]) + 1, "image_id": iid, "category_id": 1,
                                                           "bbox": [b[0], b[1], b[2] - b[0], b[3] - b[1]], "iscrowd": 0, "area": (b[2] - b[0]) * (b[3] - b[1])})
        for s, d in coco_out.items():
            (root / "annotations" / f"{s}.json").write_text(json.dumps(d))
        (root / "data.yaml").write_text(f"path: {root.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: keycap\n")
        summary["counts"][f"ppu{ppu}"] = {s: len(d["images"]) for s, d in coco_out.items()}

    # ---- evaluation scenarios
    ev_root = out_dir / "eval_scenarios"
    scen: dict[str, dict[str, list]] = {s: {k: [] for k in ("S1", "S2", "S3", "S4a", "S4b", "S4c")} for s in ("val", "test")}
    eval_jobs, meta = [], []
    for im in imgs:
        if im["split"] not in ("val", "test") or im["file_name"] not in slot_gt:
            continue
        sg = slot_gt[im["file_name"]]
        key = f"{im['split']}__{Path(im['file_name']).stem}"
        ref = np.array(sg["ref_px"], float)
        sets = {"gt": ref, "jit": jitter_points(ref, q2c["eval_jitter_sigma_u"], _rng(key, "evaljit"))}
        if im["eval_set"] == "main":
            sets["shift"] = shift_points(ref)
        for pname in sets:
            for ppu in ppus:
                (ev_root / im["split"] / f"ppu{ppu}" / pname).mkdir(parents=True, exist_ok=True)
        eval_jobs.append((dataset_root / im["file_name"], key, {k: v.tolist() for k, v in sets.items()}, {s: b for s, b in sg["slots"].items()}, ppus,
                          str(ev_root / im["split"]), q2c["min_visible"]))
        meta.append((im, key, sets, sg))
    with ProcessPoolExecutor(workers) as ex:
        results = list(ex.map(_eval_job, eval_jobs, chunksize=8))
    synth_jobs = []
    for (im, key, sets, sg), bu in zip(meta, results):
        if bu is None:
            continue
        sp = im["split"]
        present = set(sg["slots"])
        obs = {s: layout.labels[layout.index(s)] for s in layout.slot_ids if s in present}
        base = {"key": key, "source_id": im["source_id"], "brand_group": im["brand_group"], "seen_brand": im["brand_group"] in train_groups,
                "original_file": im["file_name"], "gt_boxes_u": bu, "n_letters": im["n_letters"]}
        if im["eval_set"] == "main":
            for pname in ("gt", "jit"):
                scen[sp]["S1"].append({**base, "id": f"{key}:S1:{pname}", "layout_id": layout.layout_id, "point_set": pname, "image_dir": pname,
                                       "observed": obs, "expect": {"reject": None, "incorrect": [], "uncertain": [], "suggestions": []}})
                swap_obs = dict(obs)
                zs = layout.label_to_slot()["Z"]
                ys = layout.label_to_slot()["Y"]
                s2_expected = {lay_swap.slot_ids[i]: lay_swap.labels[i] for i in range(26)}
                inc = [s for s in obs if obs[s] != s2_expected[s]]
                scen[sp]["S2"].append({**base, "id": f"{key}:S2:{pname}", "layout_id": lay_swap.layout_id, "point_set": pname, "image_dir": pname,
                                       "observed": obs, "expect": {"reject": None, "incorrect": sorted(inc), "uncertain": [], "suggestions": [{"type": "swap_pair", "slots": sorted([zs, ys])}]}})
            scen[sp]["S4a"].append({**base, "id": f"{key}:S4a", "layout_id": layout.layout_id, "point_set": "shift", "image_dir": "shift", "observed": obs,
                                    "expect": {"reject": "LAYOUT_MISMATCH", "incorrect": [], "uncertain": [], "suggestions": []}})
            swaps = make_swaps(layout, rng=_rng(key, "swap"), kinds=q2c["swap_kinds"])
            synth_jobs.append((key, sp, ppus, str(ev_root / sp), bu["gt"], {k: v["perm"] for k, v in swaps.items()}))
            for kind, sw in swaps.items():
                o2 = {dst: obs[srcs] for dst, srcs in sw["perm"].items()}
                o2 = {**obs, **o2}
                scen[sp]["S3"].append({**base, "id": f"{key}:S3:{kind}", "layout_id": layout.layout_id, "point_set": "gt", "image_dir": f"synth_{kind}",
                                       "synthetic": True, "swap_kind": kind, "observed": o2,
                                       "expect": {"reject": None, "incorrect": sorted(sw["incorrect"]), "uncertain": [], "suggestions": sw["suggestions"]}})
        elif im["eval_set"] == "partial":
            missing = sorted(s for s in layout.slot_ids if s not in present)
            scen[sp]["S4b"].append({**base, "id": f"{key}:S4b", "layout_id": layout.layout_id, "point_set": "gt", "image_dir": "gt", "observed": obs,
                                    "expect": {"reject": None, "incorrect": [], "uncertain": missing, "suggestions": []}})
        elif im["eval_set"] == "orient_bad":
            scen[sp]["S4c"].append({**base, "id": f"{key}:S4c", "layout_id": layout.layout_id, "point_set": "gt", "image_dir": "gt", "observed": obs,
                                    "expect": {"reject": "ANY", "incorrect": [], "uncertain": "ALL", "suggestions": []}})
    with ProcessPoolExecutor(workers) as ex:
        list(ex.map(_synth_job, synth_jobs, chunksize=8))
    for sp, d in scen.items():
        for sc, items in d.items():
            p = ev_root / sp / sc
            p.mkdir(parents=True, exist_ok=True)
            (p / "scenario.json").write_text(json.dumps(items))
        summary["counts"][f"eval_{sp}"] = {sc: len(v) for sc, v in d.items()}
    (out_dir / "report.md").write_text("# Q2 — Rectified dataset + scenarios\n\n```json\n" + json.dumps(summary, indent=1) + "\n```\n")
    return summary
