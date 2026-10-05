"""FakeInspector: the ai.inference.Inspector interface without paddle (api-contract §1)."""

import io
import json
import threading
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYOUTS_DIR = REPO_ROOT / "layouts"
LAYOUT_ID = "qwerty_stagger_letters_v1"
GOOD_POINTS = [[0.1, 0.2], [0.9, 0.2], [0.72, 0.8], [0.18, 0.8]]


class InvalidReferencePoints(ValueError):
    """Same name as ai.inference.InvalidReferencePoints; the worker matches by name."""


def completed_result(layout_id: str = LAYOUT_ID, swap: tuple[str, str] | None = None) -> dict:
    d = json.loads((LAYOUTS_DIR / f"{layout_id}.json").read_text())
    refs = set(d["reference_points_definition"]["slot_ids"])
    labels = {s["slot_id"]: s["expected_label"] for s in d["slots"]}
    if swap:
        a, b = swap
        labels[a], labels[b] = labels[b], labels[a]
    slots = []
    for s in d["slots"]:
        cx, cy = (s["center_u"][0] + 1.5) / 12, (s["center_u"][1] + 1.5) / 5
        ok = labels[s["slot_id"]] == s["expected_label"]
        slots.append({
            "slot_id": s["slot_id"], "row": s["row"], "col": s["col"], "expected_label": s["expected_label"],
            "observed_label": labels[s["slot_id"]], "status": "correct" if ok else "incorrect",
            "reason": "label_match" if ok else "label_mismatch",
            "reason_codes": ["label_match" if ok else "label_mismatch"],
            "detector_score": None, "ocr_score": 0.9, "assignment_distance": 0.05,
            "polygon": [[cx - 0.03, cy - 0.07], [cx + 0.03, cy - 0.07], [cx + 0.03, cy + 0.07], [cx - 0.03, cy + 0.07]],
            "polygon_source": "layout", "is_reference": s["slot_id"] in refs,
        })
    wrong = sum(s["status"] == "incorrect" for s in slots)
    return {
        "status": "completed", "error_code": None, "layout_id": layout_id, "layout_version": d["version"],
        "model_bundle_id": "fake_bundle_v0", "coordinate_system": "original_oriented_normalized",
        "summary": {"total_slots": 26, "correct": 26 - wrong, "incorrect": wrong, "uncertain": 0},
        "slots": slots,
        "suggestions": [{"type": "swap_pair", "slots": list(swap)}] if swap else [],
        "warnings": ["layout_fit_not_checked"],
        "timings_ms": {"rectify": 1, "detect": 0, "read": 5, "match": 1, "total": 7},
        "fit": None,
        "homography": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    }


class FakeInspector:
    """mode: complete | swap | reject | invalid | error. `gate` blocks inside inspect() (after `block_after` stage)."""

    bundle_id = "fake_bundle_v0"
    layout_id = LAYOUT_ID
    layout_version = 1

    def __init__(self, mode: str = "complete") -> None:
        self.mode = mode
        self.calls: list[tuple[tuple[int, int], list[list[float]]]] = []
        self.gate: threading.Event | None = None
        self.block_after = "reading"
        self.entered = threading.Event()
        self._lock = threading.Lock()

    def block(self) -> threading.Event:
        self.gate = threading.Event()
        return self.gate

    def release(self) -> None:
        if self.gate is not None:
            self.gate.set()

    def inspect(self, image_bgr, ref_points_px, on_stage=None) -> dict:
        with self._lock:
            self.calls.append((image_bgr.shape[:2], [list(map(float, p)) for p in ref_points_px]))
        for stage in ("rectifying", "detecting", "reading", "matching"):
            if on_stage:
                on_stage(stage)
            if stage == self.block_after and self.gate is not None:
                self.entered.set()
                self.gate.wait(30)
        if self.mode == "invalid":
            raise InvalidReferencePoints("not convex / crossing")
        if self.mode == "error":
            raise RuntimeError("boom")
        if self.mode == "reject":
            r = completed_result()
            return {**r, "status": "rejected", "error_code": "LAYOUT_MISMATCH", "summary": None, "slots": []}
        if self.mode == "swap":
            return completed_result(swap=("r1c0", "r1c1"))
        return completed_result()


def image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (400, 200), exif=None, color="white") -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGB", size, color)
    kw = {"exif": exif} if exif is not None else {}
    im.save(buf, fmt, **kw)
    return buf.getvalue()
