"""Detector + OCR evidence for rectified canvases, cached so thresholds can be tuned without re-running models."""
from __future__ import annotations

import numpy as np

from ai.matching.decision import Evidence
from ai.preprocessing.geometry import CANVAS_U
from ai.recognition.ocr import crop_box_px

ORIGIN = np.array(CANVAS_U[:2], float)


def px_to_u(boxes_px: np.ndarray, ppu: int) -> np.ndarray:
    if len(boxes_px) == 0:
        return np.zeros((0, 4))
    return np.asarray(boxes_px, float) / ppu + np.tile(ORIGIN, 2)


def u_to_px(boxes_u: np.ndarray, ppu: int) -> np.ndarray:
    return (np.asarray(boxes_u, float) - np.tile(ORIGIN, 2)) * ppu


def collect_evidence(canvases: list, detections: list, layout, ppu: int, reader, crop_mode: str, evidence_gating_u: float,
                     det_floor: float, ocr_batch: int = 64) -> list[Evidence]:
    """detections[i] = (boxes_px (N,4), scores (N,)). OCR runs only on detections near some slot (<= evidence_gating_u)."""
    todo, evs = [], []
    for k, (canvas, (bx, sc)) in enumerate(zip(canvases, detections)):
        bx, sc = np.asarray(bx, float).reshape(-1, 4), np.asarray(sc, float).reshape(-1)
        sel = sc >= det_floor
        bx, sc = bx[sel], sc[sel]
        bu = px_to_u(bx, ppu)
        ctr = np.c_[(bu[:, 0] + bu[:, 2]) / 2, (bu[:, 1] + bu[:, 3]) / 2] if len(bu) else np.zeros((0, 2))
        near = (np.linalg.norm(ctr[:, None, :] - layout.centers_u[None], axis=2).min(axis=1) <= evidence_gating_u) if len(bu) else np.zeros(0, bool)
        ev = Evidence(box_u=bu, score=sc, letter=[None] * len(bu), ocr_score=np.full(len(bu), np.nan), raw=[None] * len(bu))
        evs.append(ev)
        for i in np.where(near)[0]:
            todo.append((k, int(i), crop_box_px(canvas, bx[i], crop_mode)))
    for s in range(0, len(todo), ocr_batch * 8):
        chunk = todo[s:s + ocr_batch * 8]
        res = reader.read_labels([c for _, _, c in chunk])
        for (k, i, _), (lab, score, raw) in zip(chunk, res):
            evs[k].letter[i], evs[k].ocr_score[i], evs[k].raw[i] = lab, score, raw
    return evs
