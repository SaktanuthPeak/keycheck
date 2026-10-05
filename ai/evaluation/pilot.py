"""OCR / geometry pilot on our own photos (plan P1.C–P1.D, Gate G1).

For every image with 4 reference points and slot ground truth:
  (a) `manual`: OCR on the annotated keycap box (COCO, mapped to the rectified canvas) -> OCR quality on a correct crop.
  (b) `fixed`:  OCR on the fixed layout crop (Baseline, Spec §6.4) -> what the pipeline would actually read.
Each fixed-crop error is attributed to geometry (key centre offset from the Generic layout > tolerance), crop (offset
within tolerance but the annotated crop read correctly) or OCR (wrong letter / rejected on a crop that is fine).
Also reports the Generic-layout fit residual per keyboard (plan 1.A). The reader is injected (`read_labels(crops)`).
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from ai.data.keyboard_dataset.imaging import load_oriented_bgr
from ai.data.keyboard_dataset.schema import Dataset, ann_slot_id, coco_index, coco_xyxy, load_dataset, write_csv
from ai.detection.fixed_layout import fixed_layout_boxes
from ai.layouts import Layout, load_layout
from ai.preprocessing import geometry as g
from ai.recognition.ocr import crop_box_px

OCR_ERRORS = ("ocr_wrong", "ocr_reject")
GEOMETRY_ERRORS = ("geometry", "crop")
SLOT_COLS = ("image_id", "keyboard_id", "legend_style", "slot_id", "expected_label", "actual_label", "has_box", "offset_u",
             "dx_u", "dy_u", "manual_pred", "manual_score", "manual_outcome", "fixed_pred", "fixed_score", "fixed_outcome")


@dataclass
class PilotConfig:
    px_per_unit: int | None = None          # None -> layout.px_per_unit
    crop_mode: str = "key_full"             # fixed-layout crops
    manual_crop_mode: str = "key_full"      # annotated-box crops
    geometry_tol_u: float | None = None     # None -> layout fit gating_u
    ocr_score_min: float = 0.5
    max_assign_u: float = 1.0               # box -> slot by nearest centre when no `slot_id` attribute
    subsets: tuple[str, ...] = ("main",)
    splits: tuple[str, ...] | None = None   # None -> every split (pilot photos usually have none yet)


def slot_boxes_for_image(anns: list[dict], Hu: np.ndarray, layout: Layout, max_assign_u: float) -> dict[str, np.ndarray]:
    """slot_id -> annotated xyxy on original_oriented. `attributes.slot_id` wins; the rest by nearest centre (one-to-one)."""
    out: dict[str, np.ndarray] = {}
    rest = []
    for a in anns:
        sid = ann_slot_id(a)
        if sid in layout.slot_ids and sid not in out:
            out[sid] = coco_xyxy(a)
        elif sid is None:
            rest.append(coco_xyxy(a))
    free = [j for j, s in enumerate(layout.slot_ids) if s not in out]
    if rest and free:
        ctr = g.apply_H(Hu, np.array([g.box_center(b) for b in rest]))
        D = np.linalg.norm(ctr[:, None, :] - layout.centers_u[free][None], axis=2)
        r, c = linear_sum_assignment(np.where(D <= max_assign_u, D, 1e6))
        for i, j in zip(r, c):
            if D[i, j] <= max_assign_u:
                out[layout.slot_ids[free[j]]] = rest[i]
    return out


def _valid(pred, score, smin):
    return pred is not None and score is not None and score >= smin


def evaluate_image(img: np.ndarray, ref_px: np.ndarray, truth: dict, anns: list[dict], layout: Layout, reader,
                   cfg: PilotConfig) -> list[dict]:
    """truth: slot_id -> SlotTruth. Returns one row per slot (unreadable GT slots are marked and not scored)."""
    ppu = cfg.px_per_unit or layout.px_per_unit
    tol = cfg.geometry_tol_u if cfg.geometry_tol_u is not None else float(layout.fit["gating_u"])
    H = g.original_to_canvas_H(ref_px, layout.ref_points_u, ppu)
    Hu = g.homography(ref_px, layout.ref_points_u)
    canvas = g.warp(img, H, g.canvas_size(ppu))
    gt_boxes = slot_boxes_for_image(anns, Hu, layout, cfg.max_assign_u)
    fixed_px, _ = fixed_layout_boxes(layout, ppu)
    rows, crops, refs = [], [], []
    for j, sid in enumerate(layout.slot_ids):
        t = truth.get(sid)
        r = {"slot_id": sid, "expected_label": layout.labels[j], "actual_label": t.actual_label if t else None,
             "readable": bool(t and t.readable and t.actual_label), "has_box": sid in gt_boxes,
             "offset_u": None, "dx_u": None, "dy_u": None, "manual_pred": None, "manual_score": None, "manual_outcome": None,
             "fixed_pred": None, "fixed_score": None, "fixed_outcome": None}
        if sid in gt_boxes:
            c = g.apply_H(Hu, g.box_center(gt_boxes[sid]))[0]
            d = c - layout.centers_u[j]
            r["dx_u"], r["dy_u"], r["offset_u"] = float(d[0]), float(d[1]), float(np.hypot(*d))
        rows.append(r)
        if not r["readable"]:
            continue
        if sid in gt_boxes:
            crops.append(crop_box_px(canvas, g.transform_box(H, gt_boxes[sid]), cfg.manual_crop_mode))
            refs.append((len(rows) - 1, "manual"))
        crops.append(crop_box_px(canvas, fixed_px[j], cfg.crop_mode))
        refs.append((len(rows) - 1, "fixed"))
    res = reader.read_labels(crops) if crops else []
    for (k, mode), (lab, score, _raw) in zip(refs, res):
        rows[k][f"{mode}_pred"], rows[k][f"{mode}_score"] = lab, None if score is None else float(score)
    for r in rows:
        if not r["readable"]:
            continue
        act = r["actual_label"]
        if r["has_box"]:
            mp, ms = r["manual_pred"], r["manual_score"]
            r["manual_outcome"] = "correct" if _valid(mp, ms, cfg.ocr_score_min) and mp == act else (
                "ocr_wrong" if _valid(mp, ms, cfg.ocr_score_min) else "ocr_reject")
        fp, fs = r["fixed_pred"], r["fixed_score"]
        if _valid(fp, fs, cfg.ocr_score_min) and fp == act:
            r["fixed_outcome"] = "correct"
        elif r["offset_u"] is not None and r["offset_u"] > tol:
            r["fixed_outcome"] = "geometry"
        elif r["manual_outcome"] == "correct":
            r["fixed_outcome"] = "crop"
        else:
            r["fixed_outcome"] = "ocr_wrong" if _valid(fp, fs, cfg.ocr_score_min) else "ocr_reject"
    return rows


def _div(a, b):
    return a / b if b else None


def aggregate(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["readable"]]
    man = Counter(r["manual_outcome"] for r in scored if r["manual_outcome"])
    fix = Counter(r["fixed_outcome"] for r in scored if r["fixed_outcome"])
    n_man, n_fix = sum(man.values()), sum(fix.values())
    ocr_e = sum(fix[k] for k in OCR_ERRORS)
    geo_e = sum(fix[k] for k in GEOMETRY_ERRORS)
    dominant = "none" if ocr_e + geo_e == 0 else ("ocr" if ocr_e > geo_e else "geometry" if geo_e > ocr_e else "tie")
    return {"n_slots": len(rows), "n_unreadable_gt": len(rows) - len(scored),
            "manual": {"n": n_man, **{k: man[k] for k in ("correct", *OCR_ERRORS)}, "accuracy": _div(man["correct"], n_man),
                       "reject_rate": _div(man["ocr_reject"], n_man)},
            "fixed": {"n": n_fix, **{k: fix[k] for k in ("correct", *GEOMETRY_ERRORS, *OCR_ERRORS)}, "accuracy": _div(fix["correct"], n_fix)},
            "fixed_errors": {"ocr": ocr_e, "geometry": geo_e, "ocr_share": _div(ocr_e, ocr_e + geo_e),
                             "geometry_share": _div(geo_e, ocr_e + geo_e), "dominant": dominant}}


def fit_residual(rows: list[dict], tol: float) -> dict:
    off = np.array([r["offset_u"] for r in rows if r["offset_u"] is not None], float)
    if not len(off):
        return {"n": 0, "mean_u": None, "p90_u": None, "max_u": None, "frac_over_tol": None, "exceeds_tol": None, "worst_slots": []}
    per_slot = defaultdict(list)
    for r in rows:
        if r["offset_u"] is not None:
            per_slot[r["slot_id"]].append(r["offset_u"])
    worst = sorted(((s, float(np.mean(v))) for s, v in per_slot.items()), key=lambda x: -x[1])[:3]
    return {"n": int(len(off)), "mean_u": float(off.mean()), "p90_u": float(np.percentile(off, 90)), "max_u": float(off.max()),
            "frac_over_tol": float((off > tol).mean()), "exceeds_tol": bool(off.max() > tol),
            "worst_slots": [{"slot_id": s, "mean_offset_u": v} for s, v in worst]}


def confusions(rows: list[dict], mode: str, top: int = 10) -> list[list]:
    c = Counter((r["actual_label"], r[f"{mode}_pred"] or "∅") for r in rows
                if r[f"{mode}_outcome"] in OCR_ERRORS or (mode == "fixed" and r["fixed_outcome"] in GEOMETRY_ERRORS))
    return [[a, b, n] for (a, b), n in c.most_common(top)]


def run_pilot(ds: Dataset, layout: Layout, reader, cfg: PilotConfig | None = None, image_ids: list[str] | None = None) -> dict:
    cfg = cfg or PilotConfig()
    tol = cfg.geometry_tol_u if cfg.geometry_tol_u is not None else float(layout.fit["gating_u"])
    idx = coco_index(ds.coco, ds.images)
    rows, skipped, n_img = [], [], 0
    for im in sorted(ds.images, key=lambda i: i.image_id):
        if image_ids is not None and im.image_id not in image_ids:
            continue
        if im.subset not in cfg.subsets or (cfg.splits is not None and im.split not in cfg.splits):
            continue
        why = ("no_ref_points" if im.ref_px is None else "no_slot_gt" if im.image_id not in ds.slots
               else "missing_file" if not ds.image_path(im).exists() else None)
        if why:
            skipped.append({"image_id": im.image_id, "reason": why})
            continue
        kb = ds.keyboards.get(im.keyboard_id)
        img = load_oriented_bgr(ds.image_path(im))
        anns = idx.get(im.image_id, {}).get("anns", [])
        for r in evaluate_image(img, im.ref_px, ds.slots[im.image_id], anns, layout, reader, cfg):
            rows.append({"image_id": im.image_id, "keyboard_id": im.keyboard_id,
                         "legend_style": kb.legend_style if kb else "unknown", **r})
        n_img += 1
    by_kb, by_style = defaultdict(list), defaultdict(list)
    for r in rows:
        by_kb[r["keyboard_id"]].append(r)
        by_style[r["legend_style"]].append(r)
    report = {
        "config": {**asdict(cfg), "px_per_unit": cfg.px_per_unit or layout.px_per_unit, "geometry_tol_u": tol,
                   "layout_id": layout.layout_id},
        "n_images": n_img, "skipped": skipped,
        "overall": aggregate(rows),
        "by_legend_style": {k: {**aggregate(v), "manual_confusions": confusions(v, "manual")} for k, v in sorted(by_style.items())},
        "by_keyboard": {k: {**aggregate(v), "legend_style": v[0]["legend_style"], "n_images": len({r["image_id"] for r in v}),
                            "fit": fit_residual(v, tol)} for k, v in sorted(by_kb.items())},
        "confusions": {"manual": confusions(rows, "manual"), "fixed": confusions(rows, "fixed")},
        "slots": rows,
    }
    return report


def _pct(x):
    return "N/A" if x is None else f"{x:.1%}"


def _u(x):
    return "N/A" if x is None else f"{x:.3f}"


def report_md(rep: dict) -> str:
    c = rep["config"]
    L = ["# Pilot Report — OCR และ Geometry (P1.C–P1.D)", "",
         f"สร้างโดย `ai/evaluation/pilot.py` · layout `{c['layout_id']}` · px_per_unit={c['px_per_unit']} · "
         f"crop (fixed/manual) = `{c['crop_mode']}` / `{c['manual_crop_mode']}` · tol={c['geometry_tol_u']}u · ocr_score_min={c['ocr_score_min']}", "",
         f"ภาพที่ประเมิน {rep['n_images']} ภาพ · ข้าม {len(rep['skipped'])} ภาพ", "",
         "**นิยาม:** `manual` = OCR บนกรอบคีย์แคปที่ Annotate (Crop ถูกต้อง → วัดเฉพาะ OCR) · `fixed` = OCR บน Fixed layout crop (Baseline) · "
         "ข้อผิดพลาดของ `fixed` แยกเป็น `geometry` (กึ่งกลางปุ่มจริงคลาดจาก Generic layout เกิน tol), `crop` (คลาดไม่เกิน tol แต่ Crop จากกรอบจริงอ่านถูก), "
         "`ocr_wrong` (อ่านเป็นตัวอื่น) และ `ocr_reject` (อ่านไม่ออก/คะแนนต่ำ/ไม่ใช่ A–Z ตัวเดียว)", ""]

    def table(title, groups):
        out = [f"## {title}", "", "| กลุ่ม | manual acc | manual reject | fixed acc | geometry | crop | ocr_wrong | ocr_reject | สาเหตุหลัก |",
               "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for k, a in groups:
            m, f, e = a["manual"], a["fixed"], a["fixed_errors"]
            out.append(f"| {k} | {_pct(m['accuracy'])} (n={m['n']}) | {_pct(m['reject_rate'])} | {_pct(f['accuracy'])} (n={f['n']}) | "
                       f"{f['geometry']} | {f['crop']} | {f['ocr_wrong']} | {f['ocr_reject']} | {e['dominant']} |")
        return out + [""]

    L += table("ภาพรวม", [("ทั้งหมด", rep["overall"])])
    L += table("แยกตาม legend_style", list(rep["by_legend_style"].items()))
    L += table("แยกตามคีย์บอร์ด", [(f"{k} ({v['legend_style']})", v) for k, v in rep["by_keyboard"].items()])
    L += ["## Generic layout fit ต่อคีย์บอร์ด (แผน 1.A)", "",
          f"ระยะจากกึ่งกลางกรอบที่ Annotate (หลัง Rectify ด้วยจุดอ้างอิง 4 จุด) ถึงกึ่งกลางช่องใน Layout หน่วย u · tol = {c['geometry_tol_u']}u", "",
          "| คีย์บอร์ด | n | mean | p90 | max | > tol | เกิน tol | ช่องที่คลาดมากสุด |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for k, v in rep["by_keyboard"].items():
        f = v["fit"]
        worst = ", ".join(f"{w['slot_id']} {w['mean_offset_u']:.2f}" for w in f["worst_slots"])
        flag = "N/A" if f["exceeds_tol"] is None else ("**ใช่**" if f["exceeds_tol"] else "ไม่")
        L.append(f"| {k} | {f['n']} | {_u(f['mean_u'])} | {_u(f['p90_u'])} | {_u(f['max_u'])} | {_pct(f['frac_over_tol'])} | {flag} | {worst} |")
    L += ["", "## ตัวอักษรที่สับสนบ่อย (จริง → อ่านได้)", ""]
    for style, v in rep["by_legend_style"].items():
        L.append(f"- `{style}` (manual): " + (", ".join(f"{a}→{b} ×{n}" for a, b, n in v["manual_confusions"]) or "-"))
    L.append("- ทั้งหมด (fixed): " + (", ".join(f"{a}→{b} ×{n}" for a, b, n in rep["confusions"]["fixed"]) or "-"))
    o = rep["overall"]
    styles = rep["by_legend_style"]
    bad_fit = [k for k, v in rep["by_keyboard"].items() if v["fit"]["exceeds_tol"]]
    L += ["", "## ข้อมูลประกอบ Gate G1", "",
          f"- OCR บน Crop ที่ถูกต้อง (manual): ทั้งหมด {_pct(o['manual']['accuracy'])}"
          + "".join(f" · `{s}` {_pct(v['manual']['accuracy'])}" for s, v in styles.items()),
          f"- สาเหตุหลักของความผิดพลาดใน Baseline (fixed): **{o['fixed_errors']['dominant']}** "
          f"(OCR {o['fixed_errors']['ocr']} · Geometry/Crop {o['fixed_errors']['geometry']})",
          "- คีย์บอร์ดที่ Generic layout คลาดเกิน tol: " + (", ".join(bad_fit) if bad_fit else "ไม่มี"),
          "- การตัดสินใจตามตาราง Gate G1 ใน `docs/implementation-plan.md` เป็นของผู้ทำโครงงาน รายงานนี้ให้เฉพาะตัวเลข"]
    if rep["skipped"]:
        reasons = Counter(s["reason"] for s in rep["skipped"])
        L += ["", "ภาพที่ข้าม: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items()))]
    return "\n".join(L) + "\n"


def write_report(rep: dict, out_dir: str | Path):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pilot_report.json").write_text(json.dumps({k: v for k, v in rep.items() if k != "slots"}, indent=1, ensure_ascii=False))
    (out / "pilot_report.md").write_text(report_md(rep), encoding="utf-8")
    write_csv(out / "pilot_slots.csv", SLOT_COLS, rep["slots"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="KeyCheck OCR/geometry pilot (P1.C–P1.D)")
    ap.add_argument("--root", required=True, help="dataset root (docs/dataset-format.md)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--layout", default="qwerty_stagger_letters_v1")
    ap.add_argument("--reader", choices=("paddle", "synthetic"), default="paddle")
    ap.add_argument("--rec-model", default="PP-OCRv5_server_rec")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--ppu", type=int)
    ap.add_argument("--crop-mode", default="key_full")
    ap.add_argument("--manual-crop-mode", default="key_full")
    ap.add_argument("--tol-u", type=float)
    ap.add_argument("--ocr-score-min", type=float, default=0.5)
    a = ap.parse_args(argv)
    layout = load_layout(a.layout)
    ds = load_dataset(a.root)
    if a.reader == "synthetic":
        from ai.data.keyboard_dataset.synthetic import CodeReader
        reader = CodeReader()
    else:
        if a.device == "cpu":
            os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        from ai.recognition.ocr import OcrSpec, PaddleReader
        reader = PaddleReader(OcrSpec(id=a.rec_model, rec_model=a.rec_model, device=a.device))
    cfg = PilotConfig(px_per_unit=a.ppu, crop_mode=a.crop_mode, manual_crop_mode=a.manual_crop_mode,
                      geometry_tol_u=a.tol_u, ocr_score_min=a.ocr_score_min)
    rep = run_pilot(ds, layout, reader, cfg)
    write_report(rep, a.out)
    print(report_md(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
