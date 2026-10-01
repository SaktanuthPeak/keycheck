"""Box-level detection metrics (AP at IoU thresholds, precision/recall/F1 at a score operating point)."""
from __future__ import annotations

import numpy as np


def _iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x0 = np.maximum(a[:, None, 0], b[None, :, 0]); y0 = np.maximum(a[:, None, 1], b[None, :, 1])
    x1 = np.minimum(a[:, None, 2], b[None, :, 2]); y1 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]); ab = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + ab[None] - inter + 1e-9)


def _match(preds, gts, iou_thr):
    """preds: list of (boxes, scores) ; gts: list of boxes. Returns (tp flags sorted by score desc, n_gt)."""
    recs, n_gt = [], 0
    for (pb, ps), gb in zip(preds, gts):
        pb, ps, gb = np.asarray(pb).reshape(-1, 4), np.asarray(ps), np.asarray(gb).reshape(-1, 4)
        n_gt += len(gb)
        order = np.argsort(-ps)
        iou = _iou_matrix(pb[order], gb)
        used = np.zeros(len(gb), bool)
        for r, i in enumerate(order):
            ok = False
            if len(gb):
                cand = np.where(~used)[0]
                if len(cand):
                    j = cand[np.argmax(iou[r, cand])]
                    if iou[r, j] >= iou_thr:
                        used[j], ok = True, True
            recs.append((ps[i], ok))
    recs.sort(key=lambda t: -t[0])
    return np.array([ok for _, ok in recs], bool), np.array([s for s, _ in recs]), n_gt


def average_precision(preds, gts, iou_thr: float) -> float:
    tp, _, n_gt = _match(preds, gts, iou_thr)
    if n_gt == 0:
        return float("nan")
    if len(tp) == 0:
        return 0.0
    ctp = np.cumsum(tp); cfp = np.cumsum(~tp)
    rec = ctp / n_gt; prec = ctp / np.maximum(ctp + cfp, 1)
    mrec = np.r_[0.0, rec, 1.0]; mpre = np.r_[1.0, prec, 0.0]
    mpre = np.maximum.accumulate(mpre[::-1])[::-1]
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def detection_summary(preds, gts, score_thr: float = 0.25) -> dict:
    ap50 = average_precision(preds, gts, 0.5)
    aps = [average_precision(preds, gts, t) for t in np.arange(0.5, 0.96, 0.05)]
    f = [(np.asarray(b).reshape(-1, 4)[np.asarray(s) >= score_thr], np.asarray(s)[np.asarray(s) >= score_thr]) for b, s in preds]
    tp, _, n_gt = _match(f, gts, 0.5)
    ntp, npred = int(tp.sum()), len(tp)
    p = ntp / npred if npred else float("nan"); r = ntp / n_gt if n_gt else float("nan")
    f1 = 2 * p * r / (p + r) if npred and n_gt and (p + r) > 0 else float("nan")
    return {"map50": ap50, "map50_95": float(np.nanmean(aps)), "precision": p, "recall": r, "f1": f1, "score_thr": score_thr, "n_gt": n_gt, "n_pred": npred}
