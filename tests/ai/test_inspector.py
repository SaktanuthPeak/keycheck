"""ai.inference.Inspector end-to-end on synthetic photos with a fake OCR (contract §1/§2.1, web plan W1/W4)."""
from __future__ import annotations

import json

import cv2
import numpy as np
import pytest
from conftest import BASELINE_BUNDLE, SYN_REF_PX, FakeDetector, FakeReader, synth_keyboard, write_bundle
from PIL import Image

from ai.inference import BundleError, Inspector, InvalidReferencePoints, load_bundle_meta
from ai.inference.images import load_oriented_bgr

SLOT_KEYS = {"slot_id", "row", "col", "expected_label", "observed_label", "candidate_label", "status", "reason", "reason_codes", "detector_score",
             "ocr_score", "assignment_distance", "polygon", "polygon_source", "is_reference"}
TOP_KEYS = {"status", "error_code", "layout_id", "layout_version", "model_bundle_id", "coordinate_system", "summary", "slots",
            "suggestions", "warnings", "timings_ms", "fit"}


@pytest.fixture
def insp():
    return Inspector(BASELINE_BUNDLE, reader=FakeReader())


def counts(r):
    s = r["summary"]
    return s["correct"], s["incorrect"], s["uncertain"]


def poly_px(slot, wh):
    return (np.array(slot["polygon"]) * np.array(wh, float)).astype(np.float32)


def assert_contract(r, layout):
    assert set(r) == TOP_KEYS
    json.dumps(r, allow_nan=False)                     # JSON-native, no NaN / numpy scalars
    assert r["coordinate_system"] == "original_oriented_normalized"
    assert isinstance(r["layout_version"], int)
    if r["status"] == "completed":
        assert [s["slot_id"] for s in r["slots"]] == list(layout.slot_ids)
        s = r["summary"]
        assert s["total_slots"] == 26 == len(r["slots"]) == s["correct"] + s["incorrect"] + s["uncertain"]
        for k in ("correct", "incorrect", "uncertain"):
            assert s[k] == sum(1 for x in r["slots"] if x["status"] == k)
        assert sum(x["is_reference"] for x in r["slots"]) == 4
        for x in r["slots"]:
            assert set(x) == SLOT_KEYS
            assert x["reason"] == x["reason_codes"][0]
            p = np.array(x["polygon"])
            assert p.shape == (4, 2) and (p >= 0).all() and (p <= 1).all()
    t = r["timings_ms"]
    assert set(t) == {"rectify", "detect", "read", "match", "total"} and all(type(v) is int and v >= 0 for v in t.values())


def test_load_bundle_meta():
    m = load_bundle_meta(BASELINE_BUNDLE)
    assert m["bundle_id"] == "baseline_dev_v0" and m["detector"] == "baseline" and m["weights_file"] is None
    assert m["thresholds"]["skip_layout_fit"] is True


def test_attributes(insp):
    assert insp.bundle_id == "baseline_dev_v0" and insp.layout_id == "qwerty_stagger_letters_v1" and insp.layout_version == 1
    assert insp.detector is None and insp.params.skip_layout_fit


def test_all_correct_baseline(insp, layout):
    img = synth_keyboard(layout)
    stages = []
    r = insp.inspect(img, SYN_REF_PX, on_stage=stages.append)
    assert stages == ["rectifying", "detecting", "reading", "matching"]
    assert r["status"] == "completed" and r["error_code"] is None
    assert counts(r) == (26, 0, 0)
    assert_contract(r, layout)
    assert r["model_bundle_id"] == "baseline_dev_v0"
    assert "layout_fit_not_checked" in r["warnings"] and "proxy_model" in r["warnings"]
    assert "image_quality_low" not in r["warnings"]
    for s in r["slots"]:
        assert s["detector_score"] is None and s["polygon_source"] == "layout"
        assert s["observed_label"] == s["expected_label"] and s["ocr_score"] == pytest.approx(0.9, abs=0.02)
    assert insp.reader.n_crops == 26


def test_swap_detected_with_suggestion(insp, layout):
    img = synth_keyboard(layout, {"r1c0": "S", "r1c1": "A"})
    r = insp.inspect(img, SYN_REF_PX)
    assert counts(r) == (24, 2, 0)
    assert r["suggestions"] == [{"type": "swap_pair", "slots": ["r1c0", "r1c1"]}]
    a = r["slots"][layout.index("r1c0")]
    assert a["status"] == "incorrect" and a["observed_label"] == "S" and a["reason_codes"] == ["label_mismatch"]


def test_unreadable_and_low_score_are_uncertain(insp, layout):
    img = synth_keyboard(layout, {"r1c4": "?"}, scores={"r2c2": 0.2})
    r = insp.inspect(img, SYN_REF_PX)
    assert counts(r) == (24, 0, 2)
    assert r["slots"][layout.index("r1c4")]["reason"] == "ocr_invalid_label"
    assert r["slots"][layout.index("r2c2")]["reason"] == "ocr_low_confidence"


def test_thai_english_keycaps(layout):
    reader = FakeReader(raw_override={"A": "Aฟ", "S": "หS", "D": "DS"})
    r = Inspector(BASELINE_BUNDLE, reader=reader).inspect(synth_keyboard(layout), SYN_REF_PX)
    sl = {s["slot_id"]: s for s in r["slots"]}
    assert sl["r1c0"]["status"] == "correct" and sl["r1c0"]["observed_label"] == "A"
    assert sl["r1c1"]["status"] == "correct"
    assert sl["r1c2"]["status"] == "uncertain" and sl["r1c2"]["reason"] == "ocr_invalid_label"


def test_tapped_points_inside_reference_polygons(insp, layout):
    img = synth_keyboard(layout)
    r = insp.inspect(img, SYN_REF_PX)
    wh = (img.shape[1], img.shape[0])
    for sid, pt in zip(layout.ref_slot_ids, SYN_REF_PX):
        s = r["slots"][layout.index(sid)]
        assert s["is_reference"]
        assert cv2.pointPolygonTest(poly_px(s, wh), (float(pt[0]), float(pt[1])), False) > 0
    # polygons of neighbouring slots do not contain the Q point
    w = r["slots"][layout.index("r0c1")]
    assert cv2.pointPolygonTest(poly_px(w, wh), (float(SYN_REF_PX[0][0]), float(SYN_REF_PX[0][1])), False) < 0


def test_overlay_stable_after_resize(insp, layout):
    img = synth_keyboard(layout)
    r1 = insp.inspect(img, SYN_REF_PX)
    for scale in (0.5, 1.7):
        small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        sx, sy = small.shape[1] / img.shape[1], small.shape[0] / img.shape[0]
        r2 = insp.inspect(small, SYN_REF_PX * [sx, sy])
        assert counts(r2) == counts(r1)
        p1 = np.array([s["polygon"] for s in r1["slots"]])
        p2 = np.array([s["polygon"] for s in r2["slots"]])
        assert np.abs(p1 - p2).max() < 2e-3


def test_exif_rotated_upload_same_result(insp, layout, tmp_path):
    img = synth_keyboard(layout, {"r1c0": "S", "r1c1": "A"})
    pil = Image.fromarray(img[:, :, ::-1])
    pil.save(tmp_path / "up.jpg", quality=95)
    exif = Image.Exif()
    exif[0x0112] = 6
    pil.transpose(Image.Transpose.ROTATE_90).save(tmp_path / "rot.jpg", quality=95, exif=exif.tobytes())
    norm = SYN_REF_PX / [img.shape[1], img.shape[0]]                       # what the browser sends
    out = []
    for name in ("up.jpg", "rot.jpg"):
        im = load_oriented_bgr(tmp_path / name)
        assert im.shape == img.shape
        out.append(insp.inspect(im, norm * [im.shape[1], im.shape[0]]))
    assert counts(out[0]) == counts(out[1]) == (24, 2, 0)
    assert np.abs(np.array([s["polygon"] for s in out[0]["slots"]]) - np.array([s["polygon"] for s in out[1]["slots"]])).max() < 1e-6


@pytest.mark.parametrize("pts", [
    SYN_REF_PX[[0, 2, 1, 3]],                          # crossing
    SYN_REF_PX[[1, 0, 3, 2]],                          # mirrored order
    SYN_REF_PX + [0, 600],                             # outside image
    SYN_REF_PX[:3],                                    # 3 points
    np.array([[10, 10], [14, 10], [14, 14], [10, 14]], float),   # too small
    [[1, 2], [3, "x"], [5, 6], [7, 8]],
])
def test_invalid_points(insp, layout, pts):
    stages = []
    with pytest.raises(InvalidReferencePoints):
        insp.inspect(synth_keyboard(layout), pts, on_stage=stages.append)
    assert stages == []
    assert insp.reader.calls == 0


def test_bad_image_rejected(insp):
    with pytest.raises(ValueError):
        insp.inspect(np.zeros((10, 10), np.uint8), SYN_REF_PX)


def test_reference_slots_unreadable_rejected(insp, layout):
    """Baseline keeps the OCR reference check: Q and P unreadable -> LAYOUT_MISMATCH, no summary."""
    r = insp.inspect(synth_keyboard(layout, {"r0c0": "?", "r0c9": "?"}), SYN_REF_PX)
    assert r["status"] == "rejected" and r["error_code"] == "LAYOUT_MISMATCH"
    assert r["summary"] is None and r["slots"] == [] and r["suggestions"] == []
    assert_contract(r, layout)


def test_blurred_photo_warns(insp, layout):
    r = insp.inspect(synth_keyboard(layout, noise=0.0, blur=6.0), SYN_REF_PX)
    assert "image_quality_low" in r["warnings"]
    assert r["fit"]["image_quality"] == ["blurry"]


# ---- detector bundles (W4) with an injected fake detector


DET_THRESHOLDS = {"det_score_min": 0.25, "ocr_score_min": 0.3, "gating_u": 0.4, "unmatched_cost": 0.5, "ambiguity_margin_u": 0.1,
                  "fit_min_matched_fraction": 0.6, "fit_max_mean_residual_u": 0.15, "ref_invalid_max": None, "skip_layout_fit": False,
                  "objective": -1.0}                    # shape of a Q6 bundle (unknown 'objective' must be ignored)


def _detector_bundle(tmp_path, **over):
    meta = {"bundle_id": "det_test", "detector": "frcnn", "weights_file": "weights_frcnn.pt", "detector_config": {"min_size": 480},
            "thresholds": DET_THRESHOLDS, **over}
    root = write_bundle(tmp_path / "det", **meta)
    (root / "weights_frcnn.pt").write_bytes(b"not a real checkpoint")
    return root


def _staggered_boxes(layout, jitter=0.03, seed=0):
    rng = np.random.default_rng(seed)
    c = layout.centers_u + rng.normal(0, jitter, layout.centers_u.shape)
    extra = np.array([[10.0, 0.0], [9.25, 1.0], [7.75, 2.0], [0.0, -1.0], [5.0, -1.0]])            # [ ; , and number row
    c = np.vstack([c, extra])
    return np.c_[c - 0.44, c + 0.44]


def test_detector_bundle_polygons_from_detections(tmp_path, layout):
    insp = Inspector(_detector_bundle(tmp_path), reader=FakeReader(), detector=FakeDetector(_staggered_boxes(layout), 64))
    assert not insp.params.skip_layout_fit
    img = synth_keyboard(layout)
    r = insp.inspect(img, SYN_REF_PX)
    assert_contract(r, layout)
    assert r["status"] == "completed" and counts(r) == (26, 0, 0)
    assert "layout_fit_not_checked" not in r["warnings"] and r["fit"]["checked"]
    for s in r["slots"]:
        assert s["polygon_source"] == "detection" and s["detector_score"] == pytest.approx(0.9)
        assert 0 <= s["assignment_distance"] < 0.2
    q = r["slots"][layout.index("r0c0")]
    assert cv2.pointPolygonTest(poly_px(q, (img.shape[1], img.shape[0])), tuple(map(float, SYN_REF_PX[0])), False) > 0


def test_detector_bundle_missing_key_falls_back_to_layout_polygon(tmp_path, layout):
    boxes = np.delete(_staggered_boxes(layout), layout.index("r1c3"), axis=0)
    r = Inspector(_detector_bundle(tmp_path), reader=FakeReader(), detector=FakeDetector(boxes, 64)).inspect(synth_keyboard(layout), SYN_REF_PX)
    s = r["slots"][layout.index("r1c3")]
    assert s["status"] == "uncertain" and s["reason"] == "detection_unavailable"
    assert s["polygon_source"] == "layout" and s["detector_score"] is None and s["assignment_distance"] is None


def test_detector_bundle_layout_mismatch(tmp_path, layout):
    """Only the Q row is visible to the detector -> layout fit fails, no summary."""
    boxes = _staggered_boxes(layout)[:10]
    r = Inspector(_detector_bundle(tmp_path), reader=FakeReader(), detector=FakeDetector(boxes, 64)).inspect(synth_keyboard(layout), SYN_REF_PX)
    assert r["status"] == "rejected" and r["error_code"] == "LAYOUT_MISMATCH" and r["summary"] is None and r["slots"] == []
    assert_contract(r, layout)


def test_weights_outside_bundle_refused(tmp_path, layout):
    root = _detector_bundle(tmp_path, weights_file="../evil.pt")
    (tmp_path / "evil.pt").write_bytes(b"x")
    with pytest.raises(BundleError):
        Inspector(root, reader=FakeReader(), detector=FakeDetector(_staggered_boxes(layout), 64))


def test_missing_weights_refused(tmp_path, layout):
    root = _detector_bundle(tmp_path)
    (root / "weights_frcnn.pt").unlink()
    with pytest.raises(BundleError):
        Inspector(root, reader=FakeReader())


def test_unknown_layout_refused():
    with pytest.raises((ValueError, FileNotFoundError)):
        Inspector(BASELINE_BUNDLE, layout_id="../../etc/passwd", reader=FakeReader())
    with pytest.raises(ValueError):
        Inspector(BASELINE_BUNDLE, layout_id="..", reader=FakeReader())
    with pytest.raises(ValueError):
        Inspector(BASELINE_BUNDLE, layout_id="some_other_layout", reader=FakeReader())


def test_baseline_never_imports_torch():
    import subprocess
    import sys
    code = ("import sys; from conftest import FakeReader, BASELINE_BUNDLE; from ai.inference import Inspector; "
            "Inspector(BASELINE_BUNDLE, reader=FakeReader()); "
            "bad = [m for m in ('torch', 'ultralytics', 'paddle', 'paddleocr') if m in sys.modules]; assert not bad, bad")
    from pathlib import Path
    res = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_serving_evidence_equals_q6_path(tmp_path, layout):
    """OCR only on assigned detections gives the same decision as collect_evidence (all near boxes) + decide."""
    from ai.matching.decision import decide
    from ai.pipeline.evidence import collect_evidence
    rng = np.random.default_rng(3)
    boxes = _staggered_boxes(layout, jitter=0.08)
    near = boxes[:26] + np.c_[rng.normal(0, 0.15, (26, 2)), np.zeros((26, 2))].repeat(1, 0)[:, [0, 1, 0, 1]]      # duplicates
    boxes = np.vstack([boxes, near[::3]])
    scores = rng.uniform(0.1, 0.99, len(boxes))
    det = FakeDetector(boxes, 64)
    det.scores = scores
    img = synth_keyboard(layout, {"r1c0": "S", "r1c1": "A"})
    reader = FakeReader()
    insp = Inspector(_detector_bundle(tmp_path), reader=reader, detector=det)
    r, dbg = insp.inspect_with_debug(img, SYN_REF_PX)
    assert dbg["n_ocr"] <= 26 and reader.n_crops == dbg["n_ocr"] < len(boxes)
    ref_reader = FakeReader()
    ev = collect_evidence([dbg["canvas"]], [(det.boxes_px, scores)], layout, 64, ref_reader, insp.crop_mode, 0.75, insp.det_floor)[0]
    ref = decide(ev, layout, insp.params)
    assert ref_reader.n_crops > reader.n_crops
    assert r["status"] == ref["status"]
    assert r["summary"] == ref["summary"]
    for s in r["slots"]:
        e = ref["slots"][s["slot_id"]]
        assert (s["status"], s["reason"], s["observed_label"]) == (e["status"], e["reason"], e["observed_label"])
        assert s["assignment_distance"] == (None if e["assignment_distance"] is None else round(e["assignment_distance"], 4))
