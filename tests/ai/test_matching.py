"""One-to-one assignment (Spec §7.4–7.5, §16.1)."""
from __future__ import annotations

import numpy as np

from ai.matching.assign import match

KW = dict(gating_u=0.5, unmatched_cost=0.6, ambiguity_margin_u=0.1)


def _slots(m):
    return [v["det"] for v in m.values()]


def test_exact_grid_matches_everything(layout):
    m = match(layout.centers_u.copy(), layout.centers_u, **KW)
    assert sorted(m) == list(range(26))
    assert all(m[j]["det"] == j and m[j]["dist"] == 0 for j in m)


def test_two_detections_never_share_a_slot(layout):
    c = layout.centers_u
    dets = np.vstack([c[0] + [0.05, 0], c[0] + [-0.05, 0.02], c[1:]])      # two boxes on slot Q
    m = match(dets, c, **KW)
    used = _slots(m)
    assert len(used) == len(set(used))
    assert len(m) == 26 and m[0]["det"] in (0, 1)


def test_missing_boxes_leave_slots_unmatched(layout):
    c = layout.centers_u
    keep = [j for j in range(26) if j not in (3, 11, 20)]
    m = match(c[keep], c, **KW)
    assert set(range(26)) - set(m) == {3, 11, 20}
    assert all(keep[m[j]["det"]] == j for j in m)


def test_far_and_extra_boxes_are_not_forced(layout):
    c = layout.centers_u
    far = np.array([[c[5][0] + 0.8, c[5][1]], [20.0, 20.0], [-3.0, 1.0], [4.0, -1.0], [10.0, 0.0]])   # number row, keys outside A-Z
    dets = np.vstack([np.delete(c, 5, axis=0), far])
    m = match(dets, c, **KW)
    assert 5 not in m                                 # the only box near slot 5 is 0.8u away (> gating)
    assert len(m) == 25
    assert all(m[j]["dist"] <= KW["gating_u"] for j in m)
    assert all(m[j]["det"] < 25 for j in m)          # extra boxes never matched


def test_empty_detections(layout):
    assert match(np.zeros((0, 2)), layout.centers_u, **KW) == {}


def test_expected_label_not_used(layout):
    """Assignment is purely geometric: shuffling which letter a box shows cannot change it (no labels are passed)."""
    c = layout.centers_u + np.random.default_rng(1).normal(0, 0.05, layout.centers_u.shape)
    m1 = match(c, layout.centers_u, **KW)
    assert all(m1[j]["det"] == j for j in m1) and len(m1) == 26


def test_ambiguous_between_two_slots(layout):
    c = layout.centers_u
    mid = (c[0] + c[1]) / 2                           # halfway between Q and W, 0.5u from both
    dets = np.vstack([mid, c[2:]])
    m = match(dets, c, gating_u=0.55, unmatched_cost=0.6, ambiguity_margin_u=0.1)
    hit = [j for j in (0, 1) if j in m]
    assert len(hit) == 1 and m[hit[0]]["ambiguous"]
