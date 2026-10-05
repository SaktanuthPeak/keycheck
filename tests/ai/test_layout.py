"""Generic letter-block coordinates (Spec §7.2, plan 3.C)."""
from __future__ import annotations

import numpy as np

from ai.layouts import load_layout

ROWS = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")


def test_generic_coordinates(layout):
    assert len(layout.slot_ids) == 26 and len(set(layout.labels)) == 26
    for j, sid in enumerate(layout.slot_ids):
        r, c = layout.rows[j], layout.cols[j]
        assert sid == f"r{r}c{c}"
        assert layout.labels[j] == ROWS[r][c]
        offset = (0.0, 0.25, 0.75)[r]
        assert np.allclose(layout.centers_u[j], [c + offset, r])
        x0, y0, x1, y1 = layout.regions_u[j]
        assert x0 < layout.centers_u[j][0] < x1 and y0 < layout.centers_u[j][1] < y1
    q, p = layout.centers_u[layout.index("r0c0")], layout.centers_u[layout.index("r0c1")]
    assert np.isclose(np.linalg.norm(p - q), 1.0)


def test_reference_points(layout):
    assert layout.ref_slot_ids == ("r0c0", "r0c9", "r2c6", "r2c0")
    assert [layout.labels[layout.index(s)] for s in layout.ref_slot_ids] == ["Q", "P", "M", "Z"]
    assert np.allclose(layout.ref_points_u, [[0, 0], [9, 0], [6.75, 2], [0.75, 2]])
    for s, pt in zip(layout.ref_slot_ids, layout.ref_points_u):
        assert np.allclose(layout.centers_u[layout.index(s)], pt)


def test_metadata_fields(layout):
    assert layout.version == 1 and not layout.internal_only
    assert "ANSI" in layout.supported_form_factors
    ev = load_layout("qwertz_letters_eval_v1")
    assert ev.internal_only and ev.labels[ev.index("r0c5")] == "Z" and ev.labels[ev.index("r2c0")] == "Y"
