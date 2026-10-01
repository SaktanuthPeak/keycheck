"""Stage Q3: OCR sweep on GT key crops of Validation S1 (plan Q3). Picks recognizer + crop mode + px_per_unit."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml

from ai.pipeline.evidence import u_to_px
from ai.recognition.ocr import OcrSpec, PaddleReader, crop_box_px


def load_items(q2_dir: Path, max_items: int | None) -> list[dict]:
    items = json.loads((q2_dir / "eval_scenarios" / "val" / "S1" / "scenario.json").read_text())
    items = [i for i in items if i["point_set"] == "gt"]
    items.sort(key=lambda i: i["key"])
    if max_items and len(items) > max_items:
        step = len(items) / max_items
        items = [items[int(k * step)] for k in range(max_items)]
    return items


def gather_crops(q2_dir: Path, items: list[dict], ppu: int, mode: str):
    crops, truth = [], []
    for it in items:
        img = cv2.imread(str(q2_dir / "eval_scenarios" / "val" / f"ppu{ppu}" / "gt" / f"{it['key']}.jpg"))
        if img is None:
            continue
        for slot, letter in it["observed"].items():
            b = u_to_px(np.array(it["gt_boxes_u"]["gt"][slot]), ppu)
            crops.append(crop_box_px(img, b, mode))
            truth.append(letter)
    return crops, truth


def score(reader: PaddleReader, crops, truth) -> dict:
    res = reader.read_labels(crops)
    n = len(truth)
    valid = [(t, r[0]) for t, r in zip(truth, res) if r[0] is not None]
    correct = sum(1 for t, p in valid if t == p)
    return {"n": n, "accuracy": correct / n if n else float("nan"), "reject_rate": 1 - len(valid) / n if n else float("nan"),
            "acc_when_valid": correct / len(valid) if valid else float("nan"), "preds": [r[0] for r in res], "raw": [r[2] for r in res]}


def pick(rows: list[dict], max_reject: float) -> dict:
    ok = [r for r in rows if r["reject_rate"] <= max_reject] or rows
    return max(ok, key=lambda r: (r["accuracy"], -r["reject_rate"]))


def run_q3(out_dir: Path, *, q2_dir: Path, cfg: dict, ppus=(64, 96, 128), smoke: bool = False) -> dict:
    q3 = cfg["q3"]
    items = load_items(Path(q2_dir), 5 if smoke else q3["max_items"])
    specs = {r["id"]: OcrSpec(**{**r, "device": q3["device"]}) for r in q3["recognizers"]}
    modes = q3["crop_modes"][:2] if smoke else q3["crop_modes"]
    mid_ppu = 96 if 96 in ppus else ppus[len(ppus) // 2]
    rows: list[dict] = []
    # stage 1: recognizers at the middle ppu, full-key crop
    crops, truth = gather_crops(Path(q2_dir), items, mid_ppu, "key_full")
    for rid, spec in (list(specs.items())[:1] if smoke else specs.items()):
        rd = PaddleReader(spec)
        r = score(rd, crops, truth)
        rd.close()
        rows.append({"stage": 1, "recognizer": rid, "ppu": mid_ppu, "crop_mode": "key_full", **{k: r[k] for k in ("n", "accuracy", "reject_rate", "acc_when_valid")}})
        print(f"[q3] {rid}@{mid_ppu}/key_full acc={r['accuracy']:.3f} reject={r['reject_rate']:.3f}")
    best_rec = pick([r for r in rows if r["stage"] == 1], q3["max_reject_rate"])["recognizer"]
    # stage 2: ppu x crop mode with the best recognizer
    rd = PaddleReader(specs[best_rec])
    best_detail = None
    for ppu in ppus:
        for mode in modes:
            crops, truth = gather_crops(Path(q2_dir), items, ppu, mode)
            r = score(rd, crops, truth)
            row = {"stage": 2, "recognizer": best_rec, "ppu": ppu, "crop_mode": mode, **{k: r[k] for k in ("n", "accuracy", "reject_rate", "acc_when_valid")}}
            rows.append(row)
            print(f"[q3] {best_rec}@{ppu}/{mode} acc={r['accuracy']:.3f} reject={r['reject_rate']:.3f}")
            if best_detail is None or (row["reject_rate"] <= q3["max_reject_rate"] and row["accuracy"] > best_detail[0]["accuracy"]):
                best_detail = (row, truth, r["preds"], r["raw"])
    rd.close()
    chosen_row, truth, preds, raws = best_detail
    chosen = {"px_per_unit": chosen_row["ppu"], "crop_mode": chosen_row["crop_mode"], "recognizer": {**q3["recognizers"][[r["id"] for r in q3["recognizers"]].index(best_rec)]},
              "val_accuracy": chosen_row["accuracy"], "val_reject_rate": chosen_row["reject_rate"]}
    (out_dir / "chosen_config.yaml").write_text(yaml.safe_dump(chosen, sort_keys=False))
    per = {}
    for t, p in zip(truth, preds):
        d = per.setdefault(t, [0, 0])
        d[1] += 1
        d[0] += int(t == p)
    conf = Counter((t, p or "∅") for t, p in zip(truth, preds) if t != p)
    L = ["# Q3 — OCR evaluation (Validation S1, GT key crops)", "", f"items: {len(items)} source images. Chosen: `{chosen['recognizer']['id']}` ppu={chosen['px_per_unit']} crop=`{chosen['crop_mode']}`", "",
         "| stage | recognizer | ppu | crop | n | accuracy | reject | acc (valid only) |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    L += [f"| {r['stage']} | {r['recognizer']} | {r['ppu']} | {r['crop_mode']} | {r['n']} | {r['accuracy']:.3f} | {r['reject_rate']:.3f} | {r['acc_when_valid']:.3f} |" for r in rows]
    L += ["", "## Per letter (chosen config)", "", "| letter | n | accuracy |", "| --- | --- | --- |"]
    L += [f"| {k} | {v[1]} | {v[0] / v[1]:.3f} |" for k, v in sorted(per.items())]
    L += ["", "Special keys: Q (`@`), E (`€`), M (`µ`) — see rows above.", "", "## Top confusions (true → predicted)", ""]
    L += [f"- {t} → {p}: {c}" for (t, p), c in conf.most_common(15)]
    (out_dir / "ocr_report.md").write_text("\n".join(L) + "\n")
    (out_dir / "ocr_sweep.json").write_text(json.dumps({"rows": rows, "per_letter": per, "confusions": [[t, p, c] for (t, p), c in conf.items()]}))
    return {"chosen": chosen, "sweep": rows, "per_letter_acc": {k: v[0] / v[1] for k, v in per.items()}}
