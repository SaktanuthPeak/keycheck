"""Per-slot decision, layout fit and suggestions (Spec §7.6–7.8, §16.1, §17.1)."""
from __future__ import annotations

import numpy as np
import pytest

from ai.matching.decision import Evidence, Params, decide
from ai.preprocessing.geometry import apply_H, homography

LETTERS = "QWERTYUIOPASDFGHJKLZXCVBNM"
DETECTOR = Params()                                   # non-baseline: layout fit on (pipeline.yaml q6.default_params)
BASELINE = Params(skip_layout_fit=True)


def ev_from(layout, letters=None, *, centers=None, ocr=None, score=None, half=0.45) -> Evidence:
    """Boxes at `centers` (default: slot centres) reading `letters` (None = invalid) with OCR scores `ocr`."""
    c = layout.centers_u if centers is None else np.asarray(centers, float)
    n = len(c)
    letters = list(layout.labels) if letters is None else list(letters)
    ocr = np.full(n, 0.95) if ocr is None else np.asarray(ocr, float)
    return Evidence(box_u=np.c_[c - half, c + half], score=np.full(n, 0.9) if score is None else np.asarray(score, float),
                    letter=letters, ocr_score=ocr, raw=list(letters))


def with_letters(layout, mapping: dict) -> list:
    out = list(layout.labels)
    for sid, v in mapping.items():
        out[layout.index(sid)] = v
    return out


def check_summary(r):
    s = r["summary"]
    assert s["total_slots"] == 26 == len(r["slots"])
    assert s["correct"] + s["incorrect"] + s["uncertain"] == 26
    for k in ("correct", "incorrect", "uncertain"):
        assert s[k] == sum(1 for v in r["slots"].values() if v["status"] == k)


@pytest.mark.parametrize("params", [DETECTOR, BASELINE])
def test_all_correct_26_0_0(layout, params):
    r = decide(ev_from(layout), layout, params)
    assert r["status"] == "completed"
    check_summary(r)
    assert (r["summary"]["correct"], r["summary"]["incorrect"], r["summary"]["uncertain"]) == (26, 0, 0)
    assert r["suggestions"] == []


def test_swap_a_s_24_2_0(layout):
    r = decide(ev_from(layout, with_letters(layout, {"r1c0": "S", "r1c1": "A"})), layout, DETECTOR)
    check_summary(r)
    assert (r["summary"]["correct"], r["summary"]["incorrect"], r["summary"]["uncertain"]) == (24, 2, 0)
    assert r["slots"]["r1c0"]["observed_label"] == "S" and r["slots"]["r1c0"]["reason"] == "label_mismatch"
    assert r["suggestions"] == [{"type": "swap_pair", "slots": ["r1c0", "r1c1"]}]


def test_two_swaps_22_4_0(layout):
    r = decide(ev_from(layout, with_letters(layout, {"r1c0": "S", "r1c1": "A", "r0c2": "R", "r0c3": "E"})), layout, DETECTOR)
    check_summary(r)
    assert (r["summary"]["correct"], r["summary"]["incorrect"], r["summary"]["uncertain"]) == (22, 4, 0)
    assert sorted(map(tuple, (s["slots"] for s in r["suggestions"]))) == [("r0c2", "r0c3"), ("r1c0", "r1c1")]


def test_one_unreadable_25_0_1(layout):
    r = decide(ev_from(layout, with_letters(layout, {"r1c4": None})), layout, DETECTOR)
    check_summary(r)
    assert (r["summary"]["correct"], r["summary"]["incorrect"], r["summary"]["uncertain"]) == (25, 0, 1)
    assert r["slots"]["r1c4"]["reason"] == "ocr_invalid_label"


@pytest.mark.parametrize("letter,score,reason", [
    (None, 0.95, "ocr_invalid_label"),               # empty text / multi-letter / symbol -> normalize_label gives None
    ("G", 0.10, "ocr_low_confidence"),
    ("G", np.nan, "ocr_invalid_label"),              # OCR never ran on that box
])
def test_ocr_problems_are_uncertain(layout, letter, score, reason):
    letters = with_letters(layout, {"r1c4": letter})
    ocr = np.full(26, 0.95)
    ocr[layout.index("r1c4")] = score
    r = decide(ev_from(layout, letters, ocr=ocr), layout, DETECTOR)
    s = r["slots"]["r1c4"]
    assert s["status"] == "uncertain" and s["reason"] == reason and s["observed_label"] is None


def test_missing_detection_is_uncertain(layout):
    keep = [j for j in range(26) if j != layout.index("r2c3")]
    ev = ev_from(layout, [layout.labels[j] for j in keep], centers=layout.centers_u[keep])
    r = decide(ev, layout, DETECTOR)
    assert r["slots"]["r2c3"]["status"] == "uncertain" and r["slots"]["r2c3"]["reason"] == "detection_unavailable"
    check_summary(r)


def test_swap_with_uncertain_partner_not_suggested(layout):
    letters = with_letters(layout, {"r1c0": "S", "r1c1": "A"})
    ocr = np.full(26, 0.95)
    ocr[layout.index("r1c1")] = 0.1                    # S slot not confirmed
    r = decide(ev_from(layout, letters, ocr=ocr), layout, DETECTOR)
    assert r["slots"]["r1c0"]["status"] == "incorrect" and r["slots"]["r1c1"]["status"] == "uncertain"
    assert r["suggestions"] == []


def test_one_way_mismatch_not_suggested(layout):
    r = decide(ev_from(layout, with_letters(layout, {"r1c0": "S"})), layout, DETECTOR)   # duplicate S, no partner
    assert r["summary"]["incorrect"] == 1 and r["suggestions"] == []


def test_cycle_listed(layout):
    r = decide(ev_from(layout, with_letters(layout, {"r1c0": "S", "r1c1": "D", "r1c2": "A"})), layout, DETECTOR)
    assert r["suggestions"] == [{"type": "cycle", "slots": ["r1c0", "r1c1", "r1c2"]}]


def test_incomplete_image_rejected(layout):
    keep = list(range(10))                            # only the Q row is in the photo
    ev = ev_from(layout, [layout.labels[j] for j in keep], centers=layout.centers_u[keep])
    r = decide(ev, layout, DETECTOR)
    assert r["status"] == "rejected" and r["error_code"] == "LAYOUT_MISMATCH"
    assert r["summary"] is None and r["slots"] == {} and r["suggestions"] == []


def _ortholinear_letters_in_u(layout):
    """Ortholinear board (Z row under Q row, no stagger) after the user correctly taps Q, P, M, Z."""
    phys = np.array([(c, r) for r, n in enumerate((10, 9, 7)) for c in range(n)], float)
    taps = np.array([[0, 0], [9, 0], [6, 2], [0, 2]], float)
    return apply_H(homography(taps, layout.ref_points_u), phys)


@pytest.mark.xfail(strict=True, reason=(
    "Known gap (Spec §7.8): with correct taps the 4-point homography absorbs an ortholinear grid; only the A row is off "
    "(0.125u), mean residual 0.04u, so matched-fraction/mean-residual cannot reject it. A per-row stagger check would "
    "need |dx| > 0.125u but valid Kaggle boards already reach 0.12u (p99, GT points), so it is not added here."))
def test_ortholinear_with_correct_taps_rejected(layout):
    r = decide(ev_from(layout, centers=_ortholinear_letters_in_u(layout)), layout, DETECTOR)
    assert r["error_code"] == "LAYOUT_MISMATCH"


def _full_keyboard_physical():
    """Key centres (u) of a staggered board incl. keys around the letters, with their legends (None = not A-Z)."""
    rows = [("QWERTYUIOP[]", 0.0, 0), ("ASDFGHJKL;'", 0.25, 1), ("ZXCVBNM,./", 0.75, 2), ("1234567890-=", -0.5, -1)]
    pts, labs = [], []
    for chars, off, y in rows:
        for i, ch in enumerate(chars):
            pts.append((i + off, y))
            labs.append(ch if ch.isalpha() else None)
    return np.array(pts, float), labs


def test_reference_points_shifted_one_slot_rejected(layout):
    phys, labs = _full_keyboard_physical()
    taps = layout.ref_points_u + [1.0, 0.0]           # user tapped W, [, comma, X instead of Q, P, M, Z
    to_u = homography(taps, layout.ref_points_u)
    r = decide(ev_from(layout, labs, centers=apply_H(to_u, phys), ocr=np.full(len(labs), 0.95)), layout, DETECTOR)
    assert r["status"] == "rejected" and r["error_code"] == "LAYOUT_MISMATCH"


def test_correct_taps_on_full_keyboard_accepted(layout):
    phys, labs = _full_keyboard_physical()
    r = decide(ev_from(layout, labs, centers=phys, ocr=np.full(len(labs), 0.95)), layout, DETECTOR)
    assert r["status"] == "completed" and r["summary"]["correct"] == 26


def test_mostly_wrong_reads_rejected_as_layout_mismatch(layout):
    # every slot reads its right-hand neighbour, as when the taps sit one key off but the grid still fits
    shifted = [layout.labels[(j + 1) % 26] for j in range(26)]
    p = Params(ref_invalid_max=None, mismatch_min_wrong=3)
    r = decide(ev_from(layout, shifted), layout, p)
    assert r["status"] == "rejected" and r["error_code"] == "LAYOUT_MISMATCH" and r["fit"]["wrong_reads"] == 26
    assert decide(ev_from(layout, shifted), layout, Params(ref_invalid_max=None))["status"] == "completed"   # rule off by default


def test_real_swaps_not_mistaken_for_layout_mismatch(layout):
    p = Params(mismatch_min_wrong=3)
    r = decide(ev_from(layout, with_letters(layout, {"r1c0": "S", "r1c1": "A", "r0c2": "R", "r0c3": "E"})), layout, p)
    assert r["status"] == "completed" and r["summary"]["incorrect"] == 4
    # few confident reads: 3 wrong of 4 read is a majority, 2 wrong is below the count floor
    few = [None] * 26
    for sid, ch in {"r0c0": "W", "r0c1": "Q", "r0c2": "T", "r0c4": "T"}.items():
        few[layout.index(sid)] = ch
    assert decide(ev_from(layout, few), layout, Params(ref_invalid_max=None, mismatch_min_wrong=3))["error_code"] == "LAYOUT_MISMATCH"
    assert decide(ev_from(layout, few), layout, Params(ref_invalid_max=None, mismatch_min_wrong=4))["status"] == "completed"


def test_baseline_skips_fit_but_keeps_reference_check(layout):
    ev = ev_from(layout, with_letters(layout, {"r0c0": None, "r0c9": None}))
    assert decide(ev, layout, BASELINE)["error_code"] == "LAYOUT_MISMATCH"
    assert decide(ev, layout, Params(skip_layout_fit=True, ref_invalid_max=None))["status"] == "completed"


def test_low_detector_score_dropped(layout):
    sc = np.full(26, 0.9)
    sc[layout.index("r0c4")] = 0.1
    r = decide(ev_from(layout, score=sc), layout, DETECTOR)
    assert r["slots"]["r0c4"]["reason"] == "detection_unavailable"
