"""Stage Q5: Faster R-CNN ResNet50-FPN V2 (background + keycap). Checkpoints every epoch; resumes from last.pt (plan Q5)."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import cv2
import numpy as np


class CocoBoxes:
    """Rectified keycap COCO -> torch tensors. Train augmentation: colour/noise/blur and a tiny affine; never flips."""

    def __init__(self, root: Path, split: str, aug: dict | None, seed: int):
        d = json.loads((root / "annotations" / f"{split}.json").read_text())
        self.root, self.aug = root, aug
        self.images = d["images"]
        self.boxes: dict[int, list] = {}
        for a in d["annotations"]:
            x, y, w, h = a["bbox"]
            self.boxes.setdefault(a["image_id"], []).append([x, y, x + w, y + h])
        self.rng = np.random.default_rng(seed)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, i):
        import torch
        im = self.images[i]
        img = cv2.imread(str(self.root / im["file_name"]))
        bx = np.array(self.boxes.get(im["id"], []), np.float32).reshape(-1, 4)
        if self.aug:
            a, r = self.aug, self.rng
            img = img.astype(np.float32)
            img = img * (1 + r.uniform(-a["contrast"], a["contrast"])) + 255 * r.uniform(-a["brightness"], a["brightness"])
            if a["noise_std"]:
                img += r.normal(0, a["noise_std"] * 255, img.shape)
            img = np.clip(img, 0, 255).astype(np.uint8)
            if r.random() < a["blur_prob"]:
                img = cv2.GaussianBlur(img, (3, 3), 0)
            h, w = img.shape[:2]
            s = 1 + r.uniform(-a["scale"], a["scale"]); ang = r.uniform(-a["rotate_deg"], a["rotate_deg"])
            tx, ty = r.uniform(-a["translate"], a["translate"]) * w, r.uniform(-a["translate"], a["translate"]) * h
            M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, s); M[:, 2] += (tx, ty)
            img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            if len(bx):
                pts = np.stack([bx[:, [0, 1]], bx[:, [2, 1]], bx[:, [2, 3]], bx[:, [0, 3]]], 1)
                pts = pts @ M[:, :2].T + M[:, 2]
                nb = np.c_[pts[..., 0].min(1), pts[..., 1].min(1), pts[..., 0].max(1), pts[..., 1].max(1)]
                nb[:, [0, 2]] = nb[:, [0, 2]].clip(0, w); nb[:, [1, 3]] = nb[:, [1, 3]].clip(0, h)
                bx = nb[((nb[:, 2] - nb[:, 0]) > 2) & ((nb[:, 3] - nb[:, 1]) > 2)].astype(np.float32)
        t = torch.from_numpy(img[:, :, ::-1].copy()).permute(2, 0, 1).float() / 255
        return t, {"boxes": torch.from_numpy(bx), "labels": torch.ones(len(bx), dtype=torch.int64)}


def _collate(b):
    return tuple(zip(*b))


def evaluate(model, loader, device, score_thr):
    import torch
    from ai.evaluation.detection_metrics import detection_summary
    model.eval()
    preds, gts = [], []
    with torch.no_grad():
        for imgs, tg in loader:
            for r, t in zip(model([i.to(device) for i in imgs]), tg):
                preds.append((r["boxes"].cpu().numpy(), r["scores"].cpu().numpy()))
                gts.append(t["boxes"].numpy())
    return detection_summary(preds, gts, score_thr)


def train_frcnn(out_dir: Path, *, data_root: str | Path, cfg: dict, seed: int = 0, smoke: bool = False) -> dict:
    import torch
    from ai.detection.detectors import build_frcnn
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_dir = out_dir / "checkpoints"
    ck_dir.mkdir(exist_ok=True)
    mc, tc = cfg["model"], cfg["train"]
    torch.manual_seed(seed); np.random.seed(seed)
    device = torch.device(tc.get("device") or ("cuda" if torch.cuda.is_available() else "cpu"))
    amp = bool(tc["amp"]) and device.type == "cuda"
    root = Path(data_root)
    ds_tr, ds_va = CocoBoxes(root, "train", cfg["augment"], seed), CocoBoxes(root, "val", None, seed)
    if smoke:
        ds_tr.images, ds_va.images = ds_tr.images[:16], ds_va.images[:8]
    g = torch.Generator().manual_seed(seed)
    dl_tr = torch.utils.data.DataLoader(ds_tr, batch_size=tc["batch"], shuffle=True, num_workers=tc["workers"], collate_fn=_collate, generator=g, drop_last=True)
    dl_va = torch.utils.data.DataLoader(ds_va, batch_size=tc["batch"], shuffle=False, num_workers=tc["workers"], collate_fn=_collate)
    model = build_frcnn(mc["min_size"], mc["max_size"], mc["box_detections_per_img"], mc["box_score_thresh"], mc["box_nms_thresh"], mc["pretrained"]).to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    opt = (torch.optim.SGD(params, lr=tc["lr"], momentum=tc["momentum"], weight_decay=tc["weight_decay"]) if tc["optimizer"] == "sgd"
           else torch.optim.AdamW(params, lr=tc["lr"], weight_decay=tc["weight_decay"]))
    epochs = 1 if smoke else tc["epochs"]
    acc = tc["accumulate"]
    steps_total = max(1, epochs * math.ceil(len(dl_tr) / acc))
    warm = min(tc["warmup_iters"], steps_total // 2)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, steps_total - warm))))
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    state = {"epoch": 0, "best": -1.0, "bad": 0, "history": []}
    last = ck_dir / "last.pt"
    if last.exists():
        ck = torch.load(last, map_location="cpu", weights_only=False)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["optimizer"]); sched.load_state_dict(ck["scheduler"]); scaler.load_state_dict(ck["scaler"])
        state = ck["state"]
        print(f"[q5] resumed at epoch {state['epoch']}")
    monitor = tc["monitor"]
    t0 = time.time()
    while state["epoch"] < epochs and state["bad"] < tc["patience"]:
        model.train()
        comp: dict[str, float] = {}
        n = 0
        opt.zero_grad(set_to_none=True)
        for it, (imgs, tg) in enumerate(dl_tr):
            imgs = [i.to(device) for i in imgs]
            tg = [{k: v.to(device) for k, v in t.items()} for t in tg]
            with torch.autocast(device_type=device.type, enabled=amp):
                losses = model(imgs, tg)
                loss = sum(losses.values()) / acc
            scaler.scale(loss).backward()
            for k, v in losses.items():
                comp[k] = comp.get(k, 0.0) + float(v)
            n += 1
            if (it + 1) % acc == 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(params, tc["grad_clip"])
                scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step()
        val = evaluate(model, dl_va, device, tc["val_score_thr"])
        state["epoch"] += 1
        score = val[monitor] if val[monitor] == val[monitor] else 0.0
        if score > state["best"]:
            state["best"], state["bad"] = score, 0
            torch.save({"model": model.state_dict(), "epoch": state["epoch"], "val": val}, ck_dir / "best.pt")
        else:
            state["bad"] += 1
        state["history"].append({"epoch": state["epoch"], "loss_components": {k: v / max(n, 1) for k, v in comp.items()}, "val": val,
                                 "lr": opt.param_groups[0]["lr"]})
        torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(), "scheduler": sched.state_dict(), "scaler": scaler.state_dict(), "state": state}, last)
        print(f"[q5] epoch {state['epoch']}/{epochs} loss={sum(comp.values())/max(n,1):.4f} {monitor}={score:.4f}")
    best = torch.load(ck_dir / "best.pt", map_location="cpu", weights_only=False)
    metrics = {**best["val"], "best_epoch": best["epoch"], "epochs_run": state["epoch"], "epochs_budget": epochs, "effective_batch": tc["batch"] * acc,
               "min_size": mc["min_size"], "max_size": mc["max_size"], "box_detections_per_img": mc["box_detections_per_img"], "amp": amp,
               "device": str(device), "train_seconds_this_session": round(time.time() - t0, 1), "seed": seed, "weights": str(ck_dir / "best.pt"),
               "history": state["history"]}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=1))
    return metrics
