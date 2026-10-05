"""Stage Q3b: train the keycap classifier (A–Z + OTHER) on rectified key crops (plan Q3b).

Crops come from the Q1 COCO boxes (which carry `letter`) warped with the same canvas homography as Q2, so a training crop
looks like what Q6/inference cut from the canvas. Non-letter keycaps (Esc, digits, umlauts, …) become OTHER.
Train split only for fitting; Val is used for model selection, as for the detectors.
"""
from __future__ import annotations

import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from ai.classification.keycls import CLASSES, OTHER, build_model, to_tensor_batch
from ai.classification.thai_legend import draw_thai
from ai.data.rectify_dataset import _rng, jitter_points
from ai.layouts import load_layout
from ai.pipeline.stage import code_version, fingerprint
from ai.preprocessing import geometry as g

CTX = 1.4          # stored context crop = key box × CTX, so box jitter at train time stays inside the stored pixels


def crop_factor(crop_mode: str) -> float:
    """Side of the inference crop relative to the key box (mirrors ai.recognition.ocr.crop_box_px)."""
    if crop_mode == "key_full":
        return 1.0
    if crop_mode.startswith("key_full_pad"):
        return 1.0 + 2 * float(crop_mode[len("key_full_pad"):])
    if crop_mode.startswith("key_center_"):
        return float(crop_mode[len("key_center_"):])
    raise ValueError(crop_mode)


def _context_crop(canvas: np.ndarray, box, size: int) -> np.ndarray:
    x0, y0, x1, y1 = box
    cx, cy, hw, hh = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * CTX / 2, (y1 - y0) * CTX / 2
    M = np.array([[size / (2 * hw), 0, -(cx - hw) * size / (2 * hw)], [0, size / (2 * hh), -(cy - hh) * size / (2 * hh)]], np.float32)
    return cv2.warpAffine(canvas, M, (size, size), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)


def _extract_job(args):
    img_path, file_name, ref_px, ref_u, anns, ppu, size, min_visible, sigma = args
    img = cv2.imread(str(img_path))
    if img is None:
        return [], []
    pts = ref_px if sigma == 0 else jitter_points(ref_px, sigma, _rng(file_name, "keycls"))
    w, h = g.canvas_size(ppu)
    H = g.original_to_canvas_H(pts, ref_u, ppu)
    canvas = cv2.cvtColor(g.warp(img, H, (w, h)), cv2.COLOR_BGR2RGB)
    crops, labels = [], []
    for b, lab in anns:
        tb = g.transform_box(H, b)
        c = g.box_center(tb)
        if not (0 <= c[0] < w and 0 <= c[1] < h):
            continue
        cb, vis = g.clip_box(tb, w, h)
        if vis < min_visible or cb[2] - cb[0] < 4 or cb[3] - cb[1] < 4:
            continue
        crops.append(_context_crop(canvas, tb, size))
        labels.append(lab)
    return crops, labels


def extract_crops(out_dir: Path, *, q1_dir: Path, dataset_root: Path, layout_id: str, ppu: int, cfg: dict, seed: int, smoke: bool) -> dict:
    """Writes crops_<split>.npy (N,S,S,3 uint8 RGB) + labels_<split>.npy + groups_<split>.json. Returns counts."""
    coco = json.loads((q1_dir / "coco.json").read_text())
    slot_gt = json.loads((q1_dir / "slot_gt.json").read_text())
    ref_u = load_layout(layout_id).ref_points_u
    size = int(round(cfg["input"] * CTX))
    cls = {c: i for i, c in enumerate(CLASSES)}
    by_img: dict[int, list] = {}
    for a in coco["annotations"]:
        if a["category_id"] == 1:
            x, y, bw, bh = a["bbox"]
            lab = a.get("letter")
            by_img.setdefault(a["image_id"], []).append(((x, y, x + bw, y + bh), cls[lab] if lab in cls else cls[OTHER]))
    sigmas = [0.0] + list(cfg["jitter_sigmas_u"])
    counts = {}
    for split in ("train", "val"):
        imgs = [i for i in coco["images"] if i["split"] == split and i["file_name"] in slot_gt and i["id"] in by_img]
        if smoke:
            imgs = imgs[: 30 if split == "train" else 10]
        jobs, groups = [], []
        for i in imgs:
            rng = _rng(seed, i["file_name"], "keycls-sample")
            anns = by_img[i["id"]]
            letters = [a for a in anns if a[1] != cls[OTHER]]
            others = [a for a in anns if a[1] == cls[OTHER]]
            if len(others) > cfg["other_per_image"]:
                others = [others[k] for k in sorted(rng.choice(len(others), cfg["other_per_image"], replace=False))]
            sigma = 0.0 if split != "train" else float(sigmas[int(rng.integers(len(sigmas)))])
            jobs.append((Path(dataset_root) / i["file_name"], i["file_name"], np.array(slot_gt[i["file_name"]]["ref_px"], float), ref_u,
                         letters + others, ppu, size, cfg["min_visible"], sigma))
            groups.append(i.get("brand_group", ""))
        X = np.lib.format.open_memmap(out_dir / f"crops_{split}.npy", mode="w+", dtype=np.uint8,
                                      shape=(sum(len(j[4]) for j in jobs), size, size, 3))
        y, grp, n = [], [], 0
        with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as ex:
            for (crops, labs), gname in zip(ex.map(_extract_job, jobs, chunksize=8), groups):
                for c, lab in zip(crops, labs):
                    X[n] = c
                    n += 1
                y += labs
                grp += [gname] * len(labs)
        X.flush()
        del X
        if n < sum(len(j[4]) for j in jobs):      # boxes dropped off-canvas: shrink the memmap file to n rows
            full = np.load(out_dir / f"crops_{split}.npy", mmap_mode="r")
            np.save(out_dir / f"crops_{split}.tmp.npy", np.asarray(full[:n]))
            del full
            os.replace(out_dir / f"crops_{split}.tmp.npy", out_dir / f"crops_{split}.npy")
        np.save(out_dir / f"labels_{split}.npy", np.array(y, np.int16))
        (out_dir / f"groups_{split}.json").write_text(json.dumps(grp))
        counts[split] = {"n": n, "letters": int(sum(1 for v in y if v != cls[OTHER])), "other": int(sum(1 for v in y if v == cls[OTHER]))}
    return counts


class CropSet:
    """Context crops -> model-input crops. Train: random box jitter / rotation / colour / Thai legends; eval: the exact
    key box (with `thai_seed`, every crop gets a fixed synthetic Thai legend: the Thai-English stand-in for Val)."""

    def __init__(self, path: Path, labels: np.ndarray, *, input_size: int, crop_mode: str, aug: dict | None, thai_seed: int | None = None):
        self.path, self.labels, self.size, self.aug, self.thai_seed = str(path), labels, input_size, aug, thai_seed
        self.f = crop_factor(crop_mode)
        self.X = None

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        import torch
        if self.X is None:                       # opened per DataLoader worker
            self.X = np.load(self.path, mmap_mode="r")
        im = np.asarray(self.X[i])
        lab = CLASSES[int(self.labels[i])]
        lab = None if lab == OTHER else lab
        if self.thai_seed is not None:
            im = draw_thai(np.ascontiguousarray(im), lab, np.random.default_rng((self.thai_seed, i)), 1 / CTX)
        elif self.aug and np.random.random() < self.aug.get("thai_p", 0.0):
            im = draw_thai(np.ascontiguousarray(im), lab, np.random.default_rng(), 1 / CTX)
        S = im.shape[0]
        key = S / CTX                            # key box side in the stored crop
        side, cx, cy, ang = key * self.f, S / 2, S / 2, 0.0
        if self.aug:
            a, rng = self.aug, np.random.default_rng()
            side_x = side * rng.uniform(1 - a["scale"], 1 + a["scale"])
            side_y = side_x * rng.uniform(1 - a["aspect"], 1 + a["aspect"])
            cx += rng.uniform(-a["shift"], a["shift"]) * key
            cy += rng.uniform(-a["shift"], a["shift"]) * key
            ang = rng.uniform(-a["rotate_deg"], a["rotate_deg"])
        else:
            side_x = side_y = side
        n = self.size
        # rotate about (cx,cy), then map the (side_x × side_y) window centred there onto the n×n output
        T = np.array([[n / side_x, 0, n / 2 - cx * n / side_x], [0, n / side_y, n / 2 - cy * n / side_y]], np.float32)
        R = cv2.getRotationMatrix2D((cx, cy), ang, 1.0)
        A = T @ np.vstack([R, [0, 0, 1]])
        out = cv2.warpAffine(im, A.astype(np.float32), (n, n), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if self.aug:
            a = self.aug
            out = out.astype(np.float32)
            out = (out - out.mean()) * rng.uniform(1 - a["contrast"], 1 + a["contrast"]) + out.mean() * rng.uniform(1 - a["brightness"], 1 + a["brightness"])
            if rng.random() < a["gray_p"]:
                out[:] = out.mean(axis=2, keepdims=True)
            out = np.clip(out, 0, 255).astype(np.uint8)
            if rng.random() < a["blur_p"]:
                out = cv2.GaussianBlur(out, (3, 3), 0)
        x = to_tensor_batch([out], n)[0]
        return x, int(self.labels[i])


def _worker_init(wid):
    import torch
    np.random.seed((torch.initial_seed() + wid) % 2**32)


def evaluate(model, loader, device) -> tuple[dict, np.ndarray, np.ndarray]:
    import torch
    model.eval()
    P, Y = [], []
    with torch.no_grad():
        for x, y in loader:
            P.append(torch.softmax(model(x.to(device, non_blocking=True)).float(), 1).cpu().numpy())
            Y.append(y.numpy())
    P, Y = np.concatenate(P), np.concatenate(Y)
    return summarize(P, Y), P, Y


def summarize(P: np.ndarray, Y: np.ndarray) -> dict:
    other = CLASSES.index(OTHER)
    pred, conf = P.argmax(1), P.max(1)
    let = Y != other
    nll = float(-np.mean(np.log(np.clip(P[np.arange(len(Y)), Y], 1e-8, 1))))
    out = {"acc": float(np.mean(pred == Y)), "letter_acc": float(np.mean(pred[let] == Y[let])) if let.any() else float("nan"),
           "other_recall": float(np.mean(pred[~let] == other)) if (~let).any() else float("nan"),
           # an OTHER key read as a letter is what could turn into a false `incorrect`
           "other_as_letter": float(np.mean(pred[~let] != other)) if (~let).any() else float("nan"), "nll": nll, "at_conf": {}}
    for t in (0.5, 0.8, 0.9, 0.95, 0.98, 0.99):
        take = let & (conf >= t) & (pred != other)
        out["at_conf"][str(t)] = {"letter_coverage": float(take.sum() / max(let.sum(), 1)),
                                  "letter_error": float(np.mean(pred[take] != Y[take])) if take.any() else 0.0}
    out["per_letter_acc"] = {CLASSES[k]: float(np.mean(pred[Y == k] == k)) for k in range(len(CLASSES) - 1) if (Y == k).any()}
    return out


def train_keycls(out_dir: Path, *, q1_dir: Path, dataset_root: str | Path, layout_id: str, ppu: int, crop_mode: str, cfg: dict,
                 seed: int = 0, smoke: bool = False) -> dict:
    import torch
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_dir = out_dir / "checkpoints"
    ck_dir.mkdir(exist_ok=True)
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device(cfg.get("device") or ("cuda" if torch.cuda.is_available() else "cpu"))
    t0 = time.time()
    marker = out_dir / "crops.json"
    want = {"ppu": ppu, "input": cfg["input"], "ctx": CTX, "other_per_image": cfg["other_per_image"], "jitter": cfg["jitter_sigmas_u"],
            "min_visible": cfg["min_visible"], "seed": seed, "smoke": smoke, "q1": json.loads((Path(q1_dir) / "_DONE.json").read_text())["fingerprint"]}
    if marker.exists() and json.loads(marker.read_text()).get("params") == want:
        counts = json.loads(marker.read_text())["counts"]
        print(f"[q3b] crops reused: {counts}")
    else:
        counts = extract_crops(out_dir, q1_dir=Path(q1_dir), dataset_root=Path(dataset_root), layout_id=layout_id, ppu=ppu, cfg=cfg, seed=seed, smoke=smoke)
        marker.write_text(json.dumps({"params": want, "counts": counts}))
        print(f"[q3b] crops extracted in {time.time() - t0:.0f}s: {counts}")
    y_tr, y_va = np.load(out_dir / "labels_train.npy").astype(np.int64), np.load(out_dir / "labels_val.npy").astype(np.int64)
    ds_tr = CropSet(out_dir / "crops_train.npy", y_tr, input_size=cfg["input"], crop_mode=crop_mode, aug=cfg["augment"])
    ds_va = CropSet(out_dir / "crops_val.npy", y_va, input_size=cfg["input"], crop_mode=crop_mode, aug=None)
    g_ = torch.Generator().manual_seed(seed)
    kw = dict(num_workers=cfg["workers"], pin_memory=device.type == "cuda", persistent_workers=cfg["workers"] > 0, worker_init_fn=_worker_init)
    dl_tr = torch.utils.data.DataLoader(ds_tr, batch_size=cfg["batch"], shuffle=True, drop_last=True, generator=g_, **kw)
    dl_va = torch.utils.data.DataLoader(ds_va, batch_size=cfg["batch"] * 2, shuffle=False, **kw)
    ds_vt = CropSet(out_dir / "crops_val.npy", y_va, input_size=cfg["input"], crop_mode=crop_mode, aug=None, thai_seed=seed)
    dl_vt = torch.utils.data.DataLoader(ds_vt, batch_size=cfg["batch"] * 2, shuffle=False, **kw)

    model = build_model(cfg["arch"], pretrained=cfg["pretrained"]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    epochs = 1 if smoke else cfg["epochs"]
    steps_total = max(1, epochs * len(dl_tr))
    warm = min(len(dl_tr), steps_total // 2)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, steps_total - warm))))
    amp = bool(cfg["amp"]) and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    lossf = torch.nn.CrossEntropyLoss(label_smoothing=cfg["label_smoothing"])
    meta = {"classes": list(CLASSES), "arch": cfg["arch"], "input": cfg["input"], "crop_mode": crop_mode, "ppu": ppu}
    state = {"epoch": 0, "best": -1.0, "bad": 0, "history": []}
    last = ck_dir / "last.pt"
    # resume only the same run: a changed config or training code starts over instead of finishing an old run
    run_key = fingerprint({"cfg": cfg, "crop_mode": crop_mode, "ppu": ppu, "seed": seed, "smoke": smoke, "crops": want},
                          code_version=code_version(Path(__file__), Path(__file__).parents[1] / "classification"))
    if last.exists():
        ck = torch.load(last, map_location="cpu", weights_only=False)
        if ck.get("run_key") == run_key:
            model.load_state_dict(ck["model"]); opt.load_state_dict(ck["optimizer"]); sched.load_state_dict(ck["scheduler"]); scaler.load_state_dict(ck["scaler"])
            state = ck["state"]
            print(f"[q3b] resumed at epoch {state['epoch']}")
        else:
            print("[q3b] checkpoint is from a different config/code — training from scratch")
            for f in ("last.pt", "best.pt"):
                (ck_dir / f).unlink(missing_ok=True)
    while state["epoch"] < epochs and state["bad"] < cfg["patience"]:
        model.train()
        tl, n, te = 0.0, 0, time.time()
        for x, y in dl_tr:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, enabled=amp):
                loss = lossf(model(x), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt); scaler.update(); sched.step()
            tl += loss.detach() * len(y)
            n += len(y)
        val, _, _ = evaluate(model, dl_va, device)
        val["thai"] = {k: v for k, v in evaluate(model, dl_vt, device)[0].items() if k != "per_letter_acc"}
        val["acc_with_thai"] = (val["acc"] + val["thai"]["acc"]) / 2
        state["epoch"] += 1
        score = val[cfg["monitor"]]
        if score > state["best"]:
            state["best"], state["bad"] = score, 0
            torch.save({"model": model.state_dict(), "meta": meta, "epoch": state["epoch"], "val": val}, ck_dir / "best.pt")
        else:
            state["bad"] += 1
        state["history"].append({"epoch": state["epoch"], "loss": float(tl) / max(n, 1), "val": {k: v for k, v in val.items() if k != "per_letter_acc"},
                                 "lr": opt.param_groups[0]["lr"], "seconds": round(time.time() - te, 1)})
        torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(), "scheduler": sched.state_dict(), "scaler": scaler.state_dict(),
                    "state": state, "run_key": run_key}, last)
        a95 = val["at_conf"]["0.95"]
        print(f"[q3b] epoch {state['epoch']}/{epochs} loss={float(tl) / max(n, 1):.4f} val_acc={val['acc']:.4f} letter_acc={val['letter_acc']:.4f} "
              f"other_as_letter={val['other_as_letter']:.4f} cov@0.95={a95['letter_coverage']:.3f} err@0.95={a95['letter_error']:.4f} "
              f"| thai: letter_acc={val['thai']['letter_acc']:.4f} cov@0.95={val['thai']['at_conf']['0.95']['letter_coverage']:.3f} ({time.time() - te:.0f}s)")
    best = torch.load(ck_dir / "best.pt", map_location="cpu", weights_only=False)
    metrics = {**best["val"], "best_epoch": best["epoch"], "epochs_run": state["epoch"], "counts": counts, "meta": meta, "device": str(device),
               "train_seconds_this_session": round(time.time() - t0, 1), "seed": seed, "weights": str(ck_dir / "best.pt"), "history": state["history"]}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=1))
    return metrics
