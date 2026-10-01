"""Stage Q1: ingest Kaggle VOC, audit, split (plan §5 Q1). Writes coco/manifest/slot_gt/audit + split manifest."""
from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

from ai.data import audit as A
from ai.data import split as S
from ai.data.kaggle_voc import KEYBOARD_CLASS, LETTERS, Record, load_dataset
from ai.layouts import load_layout

CATS = [{"id": 1, "name": "keycap"}, {"id": 2, "name": KEYBOARD_CLASS}]


def run_q1(out_dir: Path, *, dataset_root: str | Path, cfg: dict, manifest_dir: str | Path | None = None, max_sources: int | None = None) -> dict:
    layout = load_layout(cfg["layout_id"])
    recs = load_dataset(dataset_root, max_sources=max_sources)
    audits = {r.file_name: A.audit_record(r, layout) for r in recs}
    src0 = [r for r in recs if r.copy_index == 0]
    roles = {r.source_id: A.classify(r, audits[r.file_name]) for r in src0}
    sources = [{"source_id": r.source_id, "group": A.group_of(r), "role": roles[r.source_id]} for r in src0]
    res = S.assign_splits(sources, seed=cfg["seed"], test_fraction=cfg["test_fraction"], val_fraction=cfg["val_fraction"],
                          n_heldout_val_groups=cfg["n_heldout_val_groups"], heldout_min_eligible=cfg["heldout_min_eligible"],
                          heldout_max_eligible=cfg["heldout_max_eligible"])
    assign = res["assign"]
    problems = S.check_no_leak(assign, sources)
    grp = {s["source_id"]: s["group"] for s in sources}
    for sid, a in assign.items():
        if a["split"] == "train" and grp[sid] in res["test_groups"] + res["heldout_val_groups"]:
            problems.append(f"{sid}: held-out brand in train")
    if problems:
        raise RuntimeError("split leak: " + "; ".join(problems[:5]))

    images, anns, manifest, slot_gt = [], [], [], {}
    counts: dict[str, dict] = {}
    for i, r in enumerate(recs, 1):
        a = assign[r.source_id]
        use = a["split"] if (a["split"] in ("train", "excluded") or r.copy_index == 0) else "excluded"
        key = use if use in ("train", "excluded") else f"{use}/{a['eval_set']}"
        c = counts.setdefault(key, {"images": 0, "sources": set()})
        c["images"] += 1
        c["sources"].add(r.source_id)
        au = audits[r.file_name]
        meta = {"id": i, "file_name": r.file_name, "width": r.width, "height": r.height, "source_id": r.source_id,
                "brand_token": r.brand_token, "brand_group": A.group_of(r), "copy_index": r.copy_index, "original_split": r.split_dir,
                "role": roles[r.source_id], "split": use, "eval_set": a["eval_set"] if use in ("val", "test") else None,
                "flags": au["flags"], "n_letters": au["n_letters"], "max_err_u": au["max_err_u"]}
        images.append(meta)
        manifest.append(meta)
        for b in r.boxes:
            cat = 2 if b.name == KEYBOARD_CLASS else 1
            x0, y0, x1, y1 = b.xyxy
            anns.append({"id": len(anns) + 1, "image_id": i, "category_id": cat, "bbox": [x0, y0, x1 - x0, y1 - y0], "area": (x1 - x0) * (y1 - y0),
                         "iscrowd": 0, "letter": b.name.upper() if b.name in LETTERS else None})
        if au["ref_px"] is not None:
            slot_gt[r.file_name] = {"ref_px": au["ref_px"], "slots": au["slot_gt"]}

    summary = A.summarize(recs, audits, roles)
    split_counts = {k: {"images": v["images"], "sources": len(v["sources"])} for k, v in counts.items()}
    sh = S.split_hash(assign)
    split_manifest = {"dataset_version": cfg.get("dataset_version", "kaggle_qwertz_v1"), "split_manifest_hash": sh, "seed": cfg["seed"],
                      "params": {k: cfg[k] for k in ("test_fraction", "val_fraction", "n_heldout_val_groups", "heldout_min_eligible", "heldout_max_eligible")},
                      "test_groups": res["test_groups"], "heldout_val_groups": res["heldout_val_groups"], "counts": split_counts,
                      "assign": {k: [v["split"], v["eval_set"]] for k, v in sorted(assign.items())}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "coco.json").write_text(json.dumps({"images": images, "annotations": anns, "categories": CATS}))
    (out_dir / "manifest.json").write_text(json.dumps(manifest))
    (out_dir / "slot_gt.json").write_text(json.dumps(slot_gt))
    (out_dir / "audit.json").write_text(json.dumps({"summary": summary, "per_image": audits}, default=str))
    (out_dir / "split_manifest.json").write_text(json.dumps(split_manifest, indent=1))
    (out_dir / "audit_report.md").write_text(A.report_md(summary, split_counts))
    if manifest_dir:
        Path(manifest_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(out_dir / "split_manifest.json", Path(manifest_dir) / "split_manifest.json")
    return {"split_manifest_hash": sh, "counts": split_counts, "test_groups": res["test_groups"],
            "heldout_val_groups": res["heldout_val_groups"], "audit": summary}
