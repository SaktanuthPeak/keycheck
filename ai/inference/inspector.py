"""Single-image inspection for the web worker (docs/api-contract.md §1, web plan W1/W4).

One `Inspector` per process: the bundle, layout, OCR reader and detector are loaded once in `__init__`.
`inspect()` = validate 4 points -> rectify -> detect -> read -> match, then maps every slot polygon back onto the
oriented original image (normalised 0..1). The detector path is chosen by `bundle.json` (`baseline | yolo | frcnn`);
the baseline never imports torch.

Serving reads only the detections that the (label-free) assignment gives a slot: `decide()` never looks at the letters
of unmatched detections, so the result equals `collect_evidence` + `decide` used in Q6, with <= 26 OCR crops instead of
every box near the letter block (an untrained detector can return ~300 boxes -> ~15 s of CPU OCR).
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import fields
from pathlib import Path
from typing import Callable

import numpy as np

from ai.detection.fixed_layout import fixed_layout_boxes
from ai.layouts import Layout, load_layout
from ai.matching.assign import match
from ai.matching.decision import Evidence, Params, decide
from ai.pipeline.evidence import px_to_u
from ai.preprocessing import quality as Q
from ai.preprocessing.geometry import CANVAS_U, apply_H, canvas_size, invert_H, original_to_canvas_H, u_to_canvas_matrix, validate_reference_points, warp
from ai.recognition.ocr import OcrSpec, PaddleReader, crop_box_px

DEFAULT_LAYOUT_ID = "qwerty_stagger_letters_v1"
COORDINATE_SYSTEM = "original_oriented_normalized"
DETECTORS = ("baseline", "yolo", "frcnn")
STAGES = ("rectifying", "detecting", "reading", "matching")
EVIDENCE_DET_FLOOR = 0.05         # detections below this never enter the evidence (pipeline.yaml q6.evidence_det_floor)
OCR_REASONS = ("ocr_low_confidence", "ocr_invalid_label")
_LAYOUT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class InvalidReferencePoints(ValueError):
    """The 4 tapped points fail validate_reference_points (backend maps this to INVALID_CORNERS)."""


class BundleError(ValueError):
    """bundle.json is missing, malformed or points outside its directory (backend maps this to MODEL_UNAVAILABLE)."""


def load_bundle_meta(bundle_dir: str | Path) -> dict:
    """Read and check `<bundle_dir>/bundle.json` without loading any model."""
    p = Path(bundle_dir) / "bundle.json"
    try:
        meta = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise BundleError(f"cannot read {p}: {e}") from e
    if not isinstance(meta, dict):
        raise BundleError("bundle.json must be an object")
    for k in ("bundle_id", "detector", "px_per_unit", "crop_mode", "ocr", "thresholds"):
        if k not in meta:
            raise BundleError(f"bundle.json: missing '{k}'")
    if meta["detector"] not in DETECTORS:
        raise BundleError(f"bundle.json: unknown detector '{meta['detector']}'")
    if meta["detector"] != "baseline" and not meta.get("weights_file"):
        raise BundleError(f"bundle.json: detector '{meta['detector']}' needs weights_file")
    return meta


def _weights_path(bundle_dir: Path, name: str) -> Path:
    root = bundle_dir.resolve()
    w = (root / name).resolve()
    if not w.is_relative_to(root) or w == root:
        raise BundleError(f"weights_file escapes the bundle directory: {name!r}")
    if not w.is_file():
        raise BundleError(f"weights_file not found: {w}")
    return w


def make_params(thresholds: dict, *, baseline: bool) -> Params:
    """Params from bundle thresholds; unknown keys (e.g. 'objective', evidence_*) are ignored."""
    names = {f.name for f in fields(Params)}
    p = Params(**{k: v for k, v in (thresholds or {}).items() if k in names})
    if baseline:
        p.skip_layout_fit = True          # fixed crops cannot test the key grid (Spec §7.8)
    return p


def _json_num(x, nd: int = 4):
    """float -> rounded JSON-native float; NaN / inf / None -> None."""
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def _signed_area(p: np.ndarray) -> float:
    p = np.asarray(p, float)
    return 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))


def _ms(t0: float, t1: float) -> int:
    return int(round((t1 - t0) * 1000))


class Inspector:
    def __init__(self, bundle_dir: str | Path, *, layout_id: str = DEFAULT_LAYOUT_ID, ocr_device: str = "cpu", reader=None,
                 detector=None, detector_device: str = "cpu"):
        """`reader`: object with read_labels(crops) -> [(letter|None, score, raw)] (tests inject a fake; default PaddleReader).
        `detector`: object with predict(canvases) -> [(boxes_px, scores)], overrides the bundle's weights (tests only)."""
        self.bundle_dir = Path(bundle_dir)
        self.meta = load_bundle_meta(self.bundle_dir)
        if not _LAYOUT_ID_RE.match(layout_id or ""):
            raise ValueError(f"bad layout_id {layout_id!r}")
        allowed = self.meta.get("layouts")
        if allowed and layout_id not in allowed:
            raise ValueError(f"layout {layout_id!r} is not supported by bundle {self.meta['bundle_id']!r} ({allowed})")
        self.layout: Layout = load_layout(layout_id)
        self.bundle_id: str = str(self.meta["bundle_id"])
        self.layout_id: str = self.layout.layout_id
        self.layout_version: int = int(self.layout.version)
        self.detector_name: str = self.meta["detector"]
        self.is_baseline = self.detector_name == "baseline"
        self.ppu = int(self.meta["px_per_unit"])
        self.crop_mode = str(self.meta["crop_mode"])
        th = dict(self.meta.get("thresholds") or {})
        ev = dict(self.meta.get("evidence") or {})
        self.det_floor = float(ev.get("det_floor", th.get("evidence_det_floor", EVIDENCE_DET_FLOOR)))
        self.params = make_params(th, baseline=self.is_baseline)
        self.proxy = bool(self.meta.get("proxy"))
        self.canvas_wh = canvas_size(self.ppu)
        self.u2c = u_to_canvas_matrix(self.ppu)
        self.block_roi = Q.block_roi_px(self.layout.regions_u, self.ppu, CANVAS_U[:2])
        self._ref_idx = {self.layout.index(s) for s in self.layout.ref_slot_ids}

        if reader is None:
            ocr = dict(self.meta["ocr"])
            if ocr.get("mode") == "keycls":           # Q3b keycap classifier shipped inside the bundle
                from ai.classification.keycls import KeyClassifier
                reader = KeyClassifier(_weights_path(self.bundle_dir, str(ocr["weights"])), device=ocr_device)
            else:
                names = {f.name for f in fields(OcrSpec)}
                reader = PaddleReader(OcrSpec(**{**{k: v for k, v in ocr.items() if k in names}, "device": ocr_device}))
        self.reader = reader
        self.weights_path = None if self.is_baseline else _weights_path(self.bundle_dir, str(self.meta["weights_file"]))
        self.detector = detector if detector is not None or self.is_baseline else self._load_detector(self.weights_path, detector_device)
        self._fixed = fixed_layout_boxes(self.layout, self.ppu) if self.is_baseline else None

    def _load_detector(self, w: Path, device: str):
        cfg = dict(self.meta.get("detector_config") or {})
        if self.detector_name == "yolo":
            from ai.detection.detectors import YoloDetector
            return YoloDetector(str(w), imgsz=int(cfg.get("imgsz", 640)), device=device, max_det=int(cfg.get("max_det", 300)), conf_floor=self.det_floor)
        from ai.detection.detectors import FrcnnDetector
        return FrcnnDetector(str(w), cfg, device=device)

    # ---- public
    def inspect(self, image_bgr: np.ndarray, ref_points_px, on_stage: Callable[[str], None] | None = None) -> dict:
        return self.inspect_with_debug(image_bgr, ref_points_px, on_stage)[0]

    def inspect_with_debug(self, image_bgr: np.ndarray, ref_points_px, on_stage: Callable[[str], None] | None = None) -> tuple[dict, dict]:
        """-> (result per contract §1/§2.1, debug dict with H, canvas, evidence, quality) — debug is for tools only."""
        t_start = time.perf_counter()
        img = np.asarray(image_bgr)
        if img.ndim != 3 or img.shape[2] not in (3, 4) or img.dtype != np.uint8 or img.shape[0] < 2 or img.shape[1] < 2:
            raise ValueError(f"image_bgr must be HxWx3 uint8, got {img.shape} {img.dtype}")
        if img.shape[2] == 4:
            img = np.ascontiguousarray(img[:, :, :3])
        h, w = img.shape[:2]
        try:
            pts = np.asarray(ref_points_px, dtype=float)
        except (TypeError, ValueError) as e:
            raise InvalidReferencePoints("reference points must be numbers") from e
        err = validate_reference_points(pts, (w, h))
        if err:
            raise InvalidReferencePoints(err)
        if np.sign(_signed_area(pts)) != np.sign(_signed_area(self.layout.ref_points_u)):
            raise InvalidReferencePoints("wrong order (mirrored): expected TL, TR, BR, BL")
        stage = on_stage or (lambda _s: None)
        L = self.layout

        stage("rectifying")
        t0 = time.perf_counter()
        H = original_to_canvas_H(pts, L.ref_points_u, self.ppu)
        if not np.all(np.isfinite(H)) or abs(np.linalg.det(H)) < 1e-12:
            raise InvalidReferencePoints("degenerate reference points")
        canvas = warp(img, H, self.canvas_wh)
        qstats = Q.quality_stats(canvas, self.block_roi)
        qflags = Q.assess(qstats, self.ppu)
        t1 = time.perf_counter()

        stage("detecting")
        if self.detector is None:
            boxes, scores = self._fixed
        else:
            boxes, scores = self.detector.predict([canvas])[0]
        t2 = time.perf_counter()

        stage("reading")
        ev, n_ocr = self._evidence(canvas, boxes, scores)
        t3 = time.perf_counter()

        stage("matching")
        dec = decide(ev, L, self.params)
        result = self._result(dec, ev, H, (w, h), qflags)
        t4 = time.perf_counter()
        result["timings_ms"] = {"rectify": _ms(t0, t1), "detect": _ms(t1, t2), "read": _ms(t2, t3), "match": _ms(t3, t4), "total": _ms(t_start, t4)}
        debug = {"H": H, "canvas": canvas, "evidence": ev, "quality": {**qstats, "flags": qflags}, "decision": dec, "n_detections": int(len(ev.score)), "n_ocr": n_ocr}
        return result, debug

    # ---- evidence
    def _ocr_targets(self, ev: Evidence) -> list[int]:
        """Indices of detections that decide() will assign to a slot (same filter and matcher, labels not used)."""
        p = self.params
        keep = np.where(ev.score >= p.det_score_min)[0]
        m = match(ev.centers[keep], self.layout.centers_u, gating_u=p.gating_u, unmatched_cost=p.unmatched_cost,
                  ambiguity_margin_u=p.ambiguity_margin_u)
        return sorted(int(keep[v["det"]]) for v in m.values())

    def _evidence(self, canvas: np.ndarray, boxes, scores) -> tuple[Evidence, int]:
        bx = np.asarray(boxes, float).reshape(-1, 4)
        sc = np.asarray(scores, float).reshape(-1)
        sel = sc >= self.det_floor
        bx, sc = bx[sel], sc[sel]
        n = len(bx)
        ev = Evidence(box_u=px_to_u(bx, self.ppu), score=sc, letter=[None] * n, ocr_score=np.full(n, np.nan), raw=[None] * n)
        todo = self._ocr_targets(ev) if n else []
        if todo:
            res = self.reader.read_labels([crop_box_px(canvas, bx[i], self.crop_mode) for i in todo])
            for i, (lab, score, raw) in zip(todo, res):
                ev.letter[i], ev.ocr_score[i], ev.raw[i] = lab, score, raw
        return ev, len(todo)

    # ---- result assembly
    def _polygon(self, box_u, Hinv: np.ndarray, wh: tuple[int, int]) -> list[list[float]]:
        x0, y0, x1, y1 = (float(v) for v in box_u)
        corners_u = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
        orig = apply_H(Hinv @ self.u2c, corners_u)                     # u -> canvas px -> original px
        norm = orig / np.array(wh, float)
        norm = np.clip(np.nan_to_num(norm, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
        return [[round(float(x), 5), round(float(y), 5)] for x, y in norm]

    def _result(self, dec: dict, ev, H: np.ndarray, wh: tuple[int, int], qflags: list[str]) -> dict:
        L = self.layout
        warnings = []
        if self.params.skip_layout_fit:
            warnings.append("layout_fit_not_checked")
        if self.proxy:
            warnings.append("proxy_model")
        if qflags:
            warnings.append("image_quality_low")
        fit = {"checked": not self.params.skip_layout_fit, "matched_fraction": _json_num(dec["fit"]["matched_fraction"]),
               "mean_residual_u": _json_num(dec["fit"]["mean_residual_u"]), "ref_invalid": int(dec["fit"]["ref_invalid"]),
               "image_quality": list(qflags)}
        out = {"status": dec["status"], "error_code": dec["error_code"], "layout_id": self.layout_id, "layout_version": self.layout_version,
               "model_bundle_id": self.bundle_id, "coordinate_system": COORDINATE_SYSTEM, "summary": None, "slots": [], "suggestions": [],
               "warnings": warnings, "timings_ms": None, "fit": fit}
        if dec["status"] != "completed":
            return out
        Hinv = invert_H(H)
        slots = []
        for j, sid in enumerate(L.slot_ids):
            s = dec["slots"][sid]
            det = s["det"]
            from_det = det is not None and not self.is_baseline
            box_u = ev.box_u[det] if from_det else L.regions_u[j]
            reason = s["reason"]
            codes = [reason]
            if qflags and s["status"] == "uncertain" and reason in OCR_REASONS:
                codes.append("crop_quality_low")
            slots.append({
                "slot_id": sid, "row": int(L.rows[j]), "col": int(L.cols[j]), "expected_label": L.labels[j],
                "observed_label": s["observed_label"], "status": s["status"], "reason": reason, "reason_codes": codes,
                "detector_score": None if self.is_baseline else _json_num(s["detector_score"]),
                "ocr_score": _json_num(s["ocr_score"]), "assignment_distance": _json_num(s["assignment_distance"]),
                "polygon": self._polygon(box_u, Hinv, wh), "polygon_source": "detection" if from_det else "layout",
                "is_reference": j in self._ref_idx,
            })
        summary = {"total_slots": len(slots), **{k: sum(1 for s in slots if s["status"] == k) for k in ("correct", "incorrect", "uncertain")}}
        out.update(summary=summary, slots=slots, suggestions=[{"type": g["type"], "slots": list(g["slots"])} for g in dec["suggestions"]])
        return out
