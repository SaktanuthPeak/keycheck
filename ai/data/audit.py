"""Per-image audit of the Kaggle data against the QWERTZ eval layout (plan Q1, §1)."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np

from ai.data.kaggle_voc import EMPTY_BRAND, UNBRANDED, Record, letter_boxes
from ai.layouts import Layout
from ai.preprocessing import geometry as g

MAX_ROW_ANGLE_DEG = 15.0
LAYOUT_ERR_REVIEW_U = 0.25


def group_of(rec: Record) -> str:
    return "sonstige" if rec.brand_group in UNBRANDED else rec.brand_group


def audit_record(rec: Record, layout: Layout) -> dict:
    """Return facts about one image. Slot GT is keyed by position (slot_id), matched by the labelled letter."""
    lb = letter_boxes(rec)
    l2s = layout.label_to_slot()
    letters = sorted(lb)
    dup = sorted(k for k, v in lb.items() if len(v) > 1)
    n_kb = sum(b.name == "keyboard" for b in rec.boxes)
    out = {
        "n_boxes": len(rec.boxes), "n_keyboard": n_kb, "n_letters": len(letters), "dup_letters": dup,
        "has_all_refs": False, "orient_bad": False, "flags": [],
        "out_of_image": sum(1 for b in rec.boxes if b.xyxy[0] < 0 or b.xyxy[1] < 0 or b.xyxy[2] > rec.width or b.xyxy[3] > rec.height),
        "slot_gt": {}, "ref_px": None, "angle_deg": None, "max_err_u": None,
    }
    ref_labels = [layout.labels[layout.index(s)] for s in layout.ref_slot_ids]   # TL TR BR BL -> Q P M Y
    if not all(l in lb and len(lb[l]) == 1 for l in ref_labels):
        return out
    out["has_all_refs"] = True
    ref_px = np.array([g.box_center(lb[l][0]) for l in ref_labels])
    out["ref_px"] = ref_px.tolist()
    q, p, m, y = ref_px
    cross = (p[0] - q[0]) * (m[1] - p[1]) - (p[1] - q[1]) * (m[0] - p[0])
    angle = math.degrees(math.atan2(p[1] - q[1], p[0] - q[0]))
    out["angle_deg"] = angle
    if cross < 0:
        out["flags"].append("mirrored")
    if q[0] > p[0]:
        out["flags"].append("flip_lr")
    if y[1] < q[1]:
        out["flags"].append("flip_ud")
    if abs(angle) > MAX_ROW_ANGLE_DEG:
        out["flags"].append("rotated")
    out["orient_bad"] = bool(out["flags"])
    ids = [l for l in letters if l not in dup]
    gt_px = np.array([g.box_center(lb[l][0]) for l in ids])
    gt_u = np.array([layout.centers_u[layout.index(l2s[l])] for l in ids])
    if len(ids) > 4:
        err = g.generic_letterblock_error(ref_px, layout.ref_points_u, gt_px, gt_u)
        out["max_err_u"] = float(err.max())
    out["slot_gt"] = {l2s[l]: list(lb[l][0]) for l in ids}
    return out


def classify(rec: Record, a: dict) -> str:
    """Role of a source for splitting: eval | partial | orient_bad | review | dup | noletters | unbranded."""
    if group_of(rec) in ("sonstige", EMPTY_BRAND):
        return "unbranded"
    if a["dup_letters"]:
        return "dup"
    if a["n_letters"] == 0:
        return "noletters"
    if not a["has_all_refs"]:
        return "partial_noref" if a["n_letters"] < 26 else "noref"
    if a["orient_bad"]:
        return "orient_bad"
    if a["n_letters"] < 26:
        return "partial"
    if a["max_err_u"] is not None and a["max_err_u"] > LAYOUT_ERR_REVIEW_U:
        return "review"
    return "eval"


def summarize(recs: list[Record], audits: dict[str, dict], roles: dict[str, str]) -> dict:
    srcs = {r.source_id: r for r in recs if r.copy_index == 0}
    s = {"images": len(recs), "sources": len(srcs)}
    s["roles"] = dict(Counter(roles[k] for k in srcs))
    s["letters_hist"] = dict(sorted(Counter(audits[r.file_name]["n_letters"] for r in srcs.values()).items()))
    s["complete_26"] = sum(audits[r.file_name]["n_letters"] == 26 for r in srcs.values())
    s["partial_21_25"] = sum(21 <= audits[r.file_name]["n_letters"] <= 25 for r in srcs.values())
    s["no_letters"] = sum(audits[r.file_name]["n_letters"] == 0 for r in srcs.values())
    s["dup_sources"] = sum(bool(audits[r.file_name]["dup_letters"]) for r in srcs.values())
    flagc: Counter = Counter()
    for r in recs:
        for f in audits[r.file_name]["flags"]:
            flagc[f] += 1
    s["flag_images"] = dict(flagc)
    s["images_with_all_refs"] = sum(audits[r.file_name]["has_all_refs"] for r in recs)
    s["images_no_boxes"] = sum(audits[r.file_name]["n_boxes"] == 0 for r in recs)
    errs = np.array([a["max_err_u"] for r in srcs.values() if (a := audits[r.file_name])["max_err_u"] is not None])
    if len(errs):
        s["letterblock_max_err_u"] = {"n": int(len(errs)), "p50": float(np.percentile(errs, 50)), "p90": float(np.percentile(errs, 90)),
                                      "frac_below_0.25": float((errs < 0.25).mean())}
    cg = defaultdict(set)
    for r in srcs.values():
        if roles[r.source_id] == "eval":
            cg[group_of(r)].add(r.source_id)
    s["eval_brand_groups"] = len(cg)
    return s


def report_md(summary: dict, split_counts: dict) -> str:
    L = ["# Audit Report — Kaggle QWERTZ (Proxy)", "", "สร้างโดย `ai/data/audit.py` (Q1) ตัวเลขทั้งหมดวัดจากไฟล์จริง", "",
         "| รายการ | ค่า |", "| --- | --- |"]
    for k in ("images", "sources", "complete_26", "partial_21_25", "no_letters", "dup_sources", "images_with_all_refs", "images_no_boxes", "eval_brand_groups"):
        L.append(f"| {k} | {summary[k]} |")
    L += ["", "## บทบาทของต้นฉบับ", "", "| role | sources |", "| --- | --- |"]
    L += [f"| {k} | {v} |" for k, v in sorted(summary["roles"].items())]
    L += ["", f"flags (images): `{summary['flag_images']}`", ""]
    if "letterblock_max_err_u" in summary:
        e = summary["letterblock_max_err_u"]
        L += ["## Generic letter-block", "", f"n={e['n']}  p50={e['p50']:.3f}u  p90={e['p90']:.3f}u  <0.25u: {e['frac_below_0.25']:.1%}", ""]
    L += ["## Split", "", "| split / role | sources | images |", "| --- | --- | --- |"]
    L += [f"| {k} | {v['sources']} | {v['images']} |" for k, v in sorted(split_counts.items())]
    return "\n".join(L) + "\n"
