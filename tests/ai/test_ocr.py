"""Label normalisation (plan P3.B, Spec §6.2, §16.1): one Latin A–Z letter, Thai ignored, no lookalike repairs."""
from __future__ import annotations

import pytest

from ai.recognition.ocr import crop_box_px, normalize_label


@pytest.mark.parametrize("raw,expected", [
    ("A", "A"), ("a", "A"), (" q ", "Q"), ("M\n", "M"),
    ("Aฟ", "A"), ("ฟA", "A"), ("A ฟ", "A"), ("ก ข A", "A"), ("ฤa", "A"),        # Thai-English keycaps
    ("AS", None), ("A S", None), ("Aฟ S", None),                                 # two Latin letters -> uncertain
    ("", None), (None, None), ("   ", None), ("ฟ", None), ("ฟห", None),          # nothing Latin
    ("0", None), ("1", None), ("Q@", None), ("Mµ", None), ("E€", None), ("[", None),   # no 0->O, no symbol stripping
    ("ı", None), ("ſ", None), ("Ä", None), ("Ａ", None),        # non-ASCII lookalikes
])
def test_normalize_label(raw, expected):
    assert normalize_label(raw) == expected


def test_crop_modes_inside_canvas():
    import numpy as np
    canvas = np.zeros((100, 200, 3), np.uint8)
    full = crop_box_px(canvas, (10, 10, 50, 50), "key_full")
    assert full.shape[:2] == (40, 40)
    assert crop_box_px(canvas, (10, 10, 50, 50), "key_center_0.5").shape[:2] == (20, 20)
    assert crop_box_px(canvas, (-30, -30, -10, -10), "key_full").shape[:2] == (1, 1)     # fully outside -> 1 px stub
