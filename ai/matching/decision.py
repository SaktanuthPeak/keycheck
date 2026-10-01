"""Per-slot decision, layout fit and swap/cycle suggestions (Spec §7.6–7.8). Pure functions over cached evidence."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

from ai.layouts import Layout
from ai.matching.assign import match


@dataclass
class Params:
    det_score_min: float = 0.25
    ocr_score_min: float = 0.50
    gating_u: float = 0.50
    unmatched_cost: float = 0.60
    ambiguity_margin_u: float = 0.10
    fit_min_matched_fraction: float | None = None      # None -> layout fit_thresholds
    fit_max_mean_residual_u: float | None = None
    ref_invalid_max: int | None = 2                    # reject when this many of the 4 tapped slots read as non-letters
    skip_layout_fit: bool = False                      # Baseline (fixed crops) cannot test the key grid

    def to_dict(self):
        return asdict(self)


@dataclass
class Evidence:
    """What the detector and OCR produced for one canvas, independent of thresholds."""
    box_u: np.ndarray                 # (N,4) detection boxes in u
    score: np.ndarray                 # (N,) detector score (1.0 for fixed crops)
    letter: list                      # per detection: normalised letter or None
    ocr_score: np.ndarray             # (N,) NaN when no OCR was run for that detection
    raw: list = field(default_factory=list)

    @property
    def centers(self) -> np.ndarray:
        if len(self.box_u) == 0:
            return np.zeros((0, 2))
        return np.c_[(self.box_u[:, 0] + self.box_u[:, 2]) / 2, (self.box_u[:, 1] + self.box_u[:, 3]) / 2]


def decide(ev: Evidence, layout: Layout, p: Params) -> dict:
    keep = np.where(ev.score >= p.det_score_min)[0] if len(ev.score) else np.array([], int)
    centers = ev.centers[keep]
    m = match(centers, layout.centers_u, gating_u=p.gating_u, unmatched_cost=p.unmatched_cost, ambiguity_margin_u=p.ambiguity_margin_u)
    ref_idx = [layout.index(s) for s in layout.ref_slot_ids]
    ref_invalid = sum(1 for j in ref_idx if j not in m or ev.letter[keep[m[j]["det"]]] is None)

    fit_min = p.fit_min_matched_fraction if p.fit_min_matched_fraction is not None else layout.fit["min_matched_fraction"]
    fit_res = p.fit_max_mean_residual_u if p.fit_max_mean_residual_u is not None else layout.fit["max_mean_residual_u"]
    n = len(layout.slot_ids)
    matched_fraction = len(m) / n
    mean_res = float(np.mean([v["dist"] for v in m.values()])) if m else float("inf")
    fit = {"matched_fraction": matched_fraction, "mean_residual_u": mean_res, "ref_invalid": ref_invalid}

    reject = None
    if not p.skip_layout_fit and (matched_fraction < fit_min or mean_res > fit_res):
        reject = "LAYOUT_MISMATCH"
    if p.ref_invalid_max is not None and ref_invalid >= p.ref_invalid_max:
        reject = "LAYOUT_MISMATCH"
    if reject:
        return {"status": "rejected", "error_code": reject, "fit": fit, "slots": {}, "summary": None, "suggestions": []}

    slots = {}
    for j, sid in enumerate(layout.slot_ids):
        s = {"slot_id": sid, "expected_label": layout.labels[j], "observed_label": None, "status": "uncertain", "reason": None,
             "det": None, "assignment_distance": None, "detector_score": None, "ocr_score": None}
        if j not in m:
            s["reason"] = "detection_unavailable"
        else:
            di = int(keep[m[j]["det"]])
            s.update(det=di, assignment_distance=m[j]["dist"], detector_score=float(ev.score[di]))
            sc = ev.ocr_score[di]
            s["ocr_score"] = None if np.isnan(sc) else float(sc)
            if m[j]["ambiguous"]:
                s["reason"] = "mapping_ambiguous"
            elif np.isnan(sc) or ev.letter[di] is None:
                s["reason"] = "ocr_invalid_label"
            elif sc < p.ocr_score_min:
                s["reason"] = "ocr_low_confidence"
            else:
                s["observed_label"] = ev.letter[di]
                s["status"] = "correct" if ev.letter[di] == layout.labels[j] else "incorrect"
                s["reason"] = "label_match" if s["status"] == "correct" else "label_mismatch"
        slots[sid] = s
    summary = {k: sum(1 for s in slots.values() if s["status"] == k) for k in ("correct", "incorrect", "uncertain")}
    summary["total_slots"] = n
    return {"status": "completed", "error_code": None, "fit": fit, "slots": slots, "summary": summary,
            "suggestions": suggest(slots, layout)}


def suggest(slots: dict, layout: Layout) -> list[dict]:
    """Swap pairs and cycles, only when every slot involved is confirmed (Spec §7.7)."""
    l2s = layout.label_to_slot()
    # edge: slot X shows the letter that belongs to slot Y
    edge = {}
    for sid, s in slots.items():
        if s["status"] == "incorrect" and s["observed_label"] in l2s:
            edge[sid] = l2s[s["observed_label"]]
    out, seen = [], set()
    for a, b in edge.items():
        if a in seen:
            continue
        if edge.get(b) == a and a != b:
            out.append({"type": "swap_pair", "slots": sorted([a, b])})
            seen |= {a, b}
    for start in sorted(edge):
        if start in seen:
            continue
        path, cur = [start], edge.get(start)
        while cur is not None and cur not in path and cur not in seen:
            path.append(cur)
            cur = edge.get(cur)
        if cur == start and len(path) >= 3:
            out.append({"type": "cycle", "slots": sorted(path)})
            seen |= set(path)
    return out
