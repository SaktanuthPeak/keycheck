"""Display helpers for the notebook (tables, plots, eyeball-check images). No pipeline logic here."""
from __future__ import annotations

import json
import random
from pathlib import Path

import cv2
import numpy as np


def _md(text: str):
    from IPython.display import Markdown, display
    display(Markdown(text))


def _df(rows, **kw):
    import pandas as pd
    from IPython.display import display
    display(pd.DataFrame(rows, **kw))


def _show(img_bgr, title="", figsize=(14, 6)):
    import matplotlib.pyplot as plt
    plt.figure(figsize=figsize)
    plt.imshow(img_bgr[:, :, ::-1])
    plt.title(title)
    plt.axis("off")
    plt.show()


def show_q1(res, dataset_root: Path):
    s = res.summary
    _md(f"**split_manifest_hash** `{s['split_manifest_hash']}`  \nTest brands: {', '.join(s['test_groups'])}  \nHeld-out Val brands: {', '.join(s['heldout_val_groups'])}")
    a = s["audit"]
    _df([{"รายการ": k, "ค่า": a[k]} for k in ("images", "sources", "complete_26", "partial_21_25", "no_letters", "dup_sources", "images_with_all_refs", "images_no_boxes", "eval_brand_groups")])
    _md("เทียบกับแผน §1 (ภาพ 5,254 · ต้นฉบับ 1,884 · ครบ 26 ตัว 1,608 · 21–25 ตัว 48 · ซ้ำ 22)")
    _df([{"role": k, "sources": v} for k, v in sorted(a["roles"].items())])
    _df([{"split/eval_set": k, **v} for k, v in sorted(s["counts"].items())])
    if "letterblock_max_err_u" in a:
        e = a["letterblock_max_err_u"]
        _md(f"Generic letter-block: n={e['n']} p50={e['p50']:.3f}u p90={e['p90']:.3f}u <0.25u = {e['frac_below_0.25']:.1%} (แผน: 96.2%)")
    pi = json.loads((res.out_dir / "audit.json").read_text())["per_image"]
    errs = [v["max_err_u"] for v in pi.values() if v.get("max_err_u") is not None]
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 3)); plt.hist(np.clip(errs, 0, 1), bins=60); plt.axvline(0.25, color="r"); plt.xlabel("max letter-block error (u)"); plt.show()
    m = json.loads((res.out_dir / "manifest.json").read_text())
    ex = [x for x in m if x["split"] == "excluded"]
    random.Random(0).shuffle(ex)
    tiles = [cv2.resize(cv2.imread(str(dataset_root / x["file_name"])), (320, 220)) for x in ex[:8]]
    if tiles:
        _show(np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:8])]) if len(tiles) >= 8 else np.hstack(tiles), "ตัวอย่างภาพที่ถูกคัดออก (excluded)")


def show_q2(res, ppu: int = 96, n: int = 3):
    d = res.out_dir
    _md("จำนวนภาพ"); _df([{"set": k, **(v if isinstance(v, dict) else {"n": v})} for k, v in res.summary["counts"].items()])
    ann = json.loads((d / f"rectified_ppu{ppu}" / "annotations" / "train.json").read_text())
    boxes = {}
    for a in ann["annotations"]:
        boxes.setdefault(a["image_id"], []).append(a["bbox"])
    tiles = []
    for im in random.Random(1).sample(ann["images"], min(n, len(ann["images"]))):
        img = cv2.imread(str(d / f"rectified_ppu{ppu}" / im["file_name"]))
        for x, y, w, h in boxes.get(im["id"], []):
            cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 1)
        tiles.append(img)
    _show(np.vstack(tiles), f"Rectified train + keycap boxes (ppu {ppu}) — กรอบต้องตรงปุ่ม", figsize=(12, 4 * len(tiles)))
    sc = json.loads((d / "eval_scenarios" / "val" / "S3" / "scenario.json").read_text())
    for it in random.Random(2).sample(sc, min(2, len(sc))):
        before = cv2.imread(str(d / "eval_scenarios" / "val" / f"ppu{ppu}" / "gt" / f"{it['key']}.jpg"))
        after = cv2.imread(str(d / "eval_scenarios" / "val" / f"ppu{ppu}" / it["image_dir"] / f"{it['key']}.jpg"))
        _show(np.vstack([before, after]), f"S3 {it['swap_kind']}: ก่อน/หลังสลับ — incorrect = {it['expect']['incorrect']}", figsize=(12, 7))


def show_q3(res):
    _df(res.summary["sweep"])
    _md("chosen: " + json.dumps(res.summary["chosen"], ensure_ascii=False))
    pl = res.summary["per_letter_acc"]
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 3)); plt.bar(list(pl), list(pl.values())); plt.ylim(0, 1); plt.title("OCR accuracy per letter (chosen config)"); plt.show()


def show_train(res):
    m = res.summary
    _df([{k: v for k, v in m.items() if not isinstance(v, (list, dict))}])
    if "history" in m:
        import matplotlib.pyplot as plt
        h = m["history"]
        plt.figure(figsize=(9, 3))
        plt.plot([x["epoch"] for x in h], [sum(x["loss_components"].values()) for x in h], label="train loss")
        plt.plot([x["epoch"] for x in h], [x["val"]["map50_95"] for x in h], label="val mAP50-95"); plt.legend(); plt.show()


def show_keycls(res):
    m = res.summary
    _df([{k: v for k, v in m.items() if not isinstance(v, (list, dict))}])
    _df([{"conf ≥": t, **v} for t, v in m["at_conf"].items()])
    _df([{"letter": k, "acc": v} for k, v in sorted(m["per_letter_acc"].items(), key=lambda kv: kv[1])[:8]])
    import matplotlib.pyplot as plt
    h = m["history"]
    plt.figure(figsize=(9, 3))
    plt.plot([x["epoch"] for x in h], [x["loss"] for x in h], label="train loss")
    plt.plot([x["epoch"] for x in h], [x["val"]["acc"] for x in h], label="val acc"); plt.legend(); plt.show()


def show_q6(res):
    _md(f"Detector ที่เลือก: **{res.summary['selected']}**")
    _df([{"detector": k, **v} for k, v in res.summary["summaries"].items()])
    _md((res.out_dir / "val_report.md").read_text())


def show_summary(ctx):
    rows = []
    for name in ("q1_ingest", "q2_rectified", "q3_ocr", "q4_yolo", "q5_frcnn", "q6_eval", "q7_test"):
        d = ctx.d(name)
        done = d / "_DONE.json"
        rows.append({"stage": name, "done": done.exists(), "path": str(d), **({"finished": json.loads(done.read_text())["finished"]} if done.exists() else {})})
    _df(rows)
    t = ctx.d("q7_test") / "test_report.md"
    if t.exists():
        _md(t.read_text())
