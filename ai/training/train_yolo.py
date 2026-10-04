"""Stage Q4: YOLO11n single class `keycap` (Spec §5.6, §8; plan Q4). Resumes from runs/train/weights/last.pt."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

FORCED_ZERO = ("fliplr", "flipud", "mosaic", "mixup", "cutmix", "copy_paste", "erasing", "shear", "perspective", "bgr")


def build_args(cfg: dict, data_yaml: str, project: Path, seed: int, smoke: bool) -> dict:
    t, a = cfg["train"], cfg["augment"]
    if abs(a.get("degrees", 0)) > 5:
        raise ValueError("degrees > 5 violates Spec §5.6")
    args = dict(data=str(data_yaml), epochs=1 if smoke else t["epochs"], patience=t["patience"], imgsz=t["imgsz"], batch=t["batch"],
                workers=t["workers"], rect=t["rect"], optimizer=t["optimizer"], cos_lr=t["cos_lr"], amp=t["amp"], cache=t["cache"],
                plots=t["plots"], deterministic=t["deterministic"], max_det=t["max_det"], device=t.get("device"), seed=seed,
                project=str(project), name="train", exist_ok=True, close_mosaic=0, **{k: 0.0 for k in FORCED_ZERO},
                hsv_h=a["hsv_h"], hsv_s=a["hsv_s"], hsv_v=a["hsv_v"], degrees=a["degrees"], translate=a["translate"], scale=a["scale"])
    return args


def train_yolo(out_dir: Path, *, data_yaml: str | Path, cfg: dict, seed: int = 0, smoke: bool = False) -> dict:
    from ultralytics import YOLO
    out_dir.mkdir(parents=True, exist_ok=True)
    project = (out_dir / "runs").resolve()        # Ultralytics nests a relative project under runs/<task>/
    args = build_args(cfg, str(data_yaml), project, seed, smoke)
    last = project / "train" / "weights" / "last.pt"
    t0, resumed = time.time(), False
    if last.exists():
        try:
            print(f"[q4] resuming from {last}")
            YOLO(str(last)).train(resume=True)
            resumed = True
        except Exception as e:                        # finished run (nothing to resume) or unreadable checkpoint
            print(f"[q4] resume not possible ({type(e).__name__}: {str(e)[:120]}); using existing weights")
            resumed = True
    else:
        YOLO(cfg["model"]["weights"]).train(**args)
    best = project / "train" / "weights" / "best.pt"
    if not best.exists():
        best = last
    shutil.copy(best, out_dir / "best.pt")
    m = YOLO(str(out_dir / "best.pt")).val(data=str(data_yaml), imgsz=args["imgsz"], batch=args["batch"], split="val", conf=0.001, iou=0.6,
                                           max_det=args["max_det"], device=args["device"], plots=False, verbose=False)
    metrics = {"map50": float(m.box.map50), "map50_95": float(m.box.map), "precision": float(m.box.mp), "recall": float(m.box.mr),
               "imgsz": args["imgsz"], "epochs_budget": args["epochs"], "effective_batch": args["batch"], "resumed": resumed,
               "train_seconds_this_session": round(time.time() - t0, 1), "seed": seed, "weights": str(out_dir / "best.pt")}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=1))
    return metrics
