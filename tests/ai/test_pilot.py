"""Pilot report (plan P1.C–P1.D): error attribution OCR vs geometry vs crop, per keyboard / legend_style, fit residual."""
from __future__ import annotations

import json

import numpy as np
import pytest

from ai.data.keyboard_dataset import schema as SC
from ai.data.keyboard_dataset.synthetic import CodeReader, make_dataset
from ai.evaluation import pilot as P
from ai.layouts import load_layout

KEYBOARDS = [
    {"keyboard_id": "clean", "legend_style": "en_only", "role": "train"},
    {"keyboard_id": "thai", "legend_style": "th_en", "role": "train", "unreadable": ["r1c3", "r1c4"]},
    {"keyboard_id": "offset", "legend_style": "en_only", "role": "train", "row_offset_u": {1: 0.6}},
    {"keyboard_id": "misprint", "legend_style": "th_en", "role": "unseen_test", "misprint": {"r0c1": "X"}},
]


@pytest.fixture(scope="module")
def layout():
    return load_layout("qwerty_stagger_letters_v1")


@pytest.fixture(scope="module")
def ds(tmp_path_factory, layout):
    root = tmp_path_factory.mktemp("pilot") / "dataset"
    make_dataset(root, layout, seed=5, keyboards=KEYBOARDS, sessions=1, arrangements_per_session=2, shots=1)
    return SC.load_dataset(root)


CFG = P.PilotConfig(px_per_unit=48)


@pytest.fixture(scope="module")
def rep(ds, layout):
    return P.run_pilot(ds, layout, CodeReader(), CFG)


def test_clean_keyboard_all_correct(rep):
    k = rep["by_keyboard"]["clean"]
    assert k["manual"]["accuracy"] == 1.0 and k["fixed"]["accuracy"] == 1.0
    assert k["fixed_errors"]["dominant"] == "none"
    assert k["fit"]["exceeds_tol"] is False and k["fit"]["max_u"] < 0.05
    assert rep["n_images"] == 8 and not rep["skipped"]


def test_geometry_errors_attributed(rep):
    k = rep["by_keyboard"]["offset"]
    rows = [r for r in rep["slots"] if r["keyboard_id"] == "offset"]
    row1 = [r for r in rows if r["slot_id"].startswith("r1")]
    assert all(abs(r["dx_u"] - 0.6) < 0.05 for r in row1)
    assert all(r["fixed_outcome"] == "geometry" for r in row1)
    assert all(r["manual_outcome"] == "correct" for r in row1 if r["slot_id"] != "r1c8")   # r1c8 is covered by an extra key
    assert k["fixed_errors"]["dominant"] == "geometry"
    assert k["fixed"]["geometry"] == 9 * 2 and k["fixed_errors"]["ocr"] == 0
    assert k["fit"]["exceeds_tol"] is True and k["fit"]["worst_slots"][0]["slot_id"].startswith("r1")


def test_ocr_reject_on_thai_keyboard(rep):
    k = rep["by_keyboard"]["thai"]
    rows = [r for r in rep["slots"] if r["keyboard_id"] == "thai" and r["slot_id"] in ("r1c3", "r1c4")]
    assert all(r["manual_outcome"] == "ocr_reject" and r["fixed_outcome"] == "ocr_reject" for r in rows)
    assert k["fixed"]["geometry"] == 0 and k["fixed"]["ocr_reject"] == 4 and k["fixed_errors"]["dominant"] == "ocr"


def test_ocr_wrong_and_legend_style(rep):
    rows = [r for r in rep["slots"] if r["keyboard_id"] == "misprint" and r["slot_id"] == "r0c1"]
    assert rows and all(r["manual_outcome"] == "ocr_wrong" and r["manual_pred"] == "X" and r["fixed_outcome"] == "ocr_wrong" for r in rows)
    th = rep["by_legend_style"]["th_en"]
    en = rep["by_legend_style"]["en_only"]
    assert th["fixed_errors"]["ocr"] == 4 + 2 and th["fixed_errors"]["geometry"] == 0
    assert en["fixed_errors"]["ocr"] == 0 and en["fixed_errors"]["geometry"] == 18
    assert any(c[1] == "X" for c in th["manual_confusions"])


def test_crop_attribution_when_offset_within_tol(ds, layout):
    """Same offset keyboard but tolerance 1u: the annotated crop reads fine, so the fixed-crop miss is a crop error."""
    cfg = P.PilotConfig(px_per_unit=48, geometry_tol_u=1.0)
    rep = P.run_pilot(ds, layout, CodeReader(), cfg, image_ids=[i.image_id for i in ds.images if i.keyboard_id == "offset"])
    k = rep["by_keyboard"]["offset"]
    assert k["fixed"]["geometry"] == 0 and k["fixed"]["crop"] >= 16 and k["fit"]["exceeds_tol"] is False


def test_low_score_is_reject(ds, layout):
    class Doubtful(CodeReader):
        def read_labels(self, crops):
            return [(lab, 0.3, raw) for lab, _, raw in super().read_labels(crops)]

    rep = P.run_pilot(ds, layout, Doubtful(), CFG, image_ids=[ds.images[0].image_id])
    assert rep["overall"]["manual"]["accuracy"] == 0.0 and rep["overall"]["manual"]["reject_rate"] == 1.0


def test_slot_boxes_without_attributes(ds, layout):
    """Boxes without `slot_id` attributes are attributed by nearest layout centre (one-to-one)."""
    im = next(i for i in ds.images if i.keyboard_id == "clean")
    anns = SC.coco_index(ds.coco, ds.images)[im.image_id]["anns"]
    stripped = [{k: v for k, v in a.items() if k != "attributes"} for a in anns]
    from ai.preprocessing import geometry as g
    Hu = g.homography(im.ref_px, layout.ref_points_u)
    with_attr = P.slot_boxes_for_image(anns, Hu, layout, 1.0)
    without = P.slot_boxes_for_image(stripped, Hu, layout, 1.0)
    assert set(with_attr) == set(without) == set(layout.slot_ids)
    assert all(np.allclose(with_attr[s], without[s]) for s in layout.slot_ids)


def test_no_boxes_still_runs_fixed(ds, layout):
    ds2 = SC.Dataset(ds.root, ds.images, ds.keyboards, ds.slots, None)
    rep = P.run_pilot(ds2, layout, CodeReader(), CFG, image_ids=[i.image_id for i in ds.images if i.keyboard_id == "offset"])
    k = rep["by_keyboard"]["offset"]
    assert k["manual"]["n"] == 0 and k["fit"]["n"] == 0 and k["fit"]["exceeds_tol"] is None
    assert k["fixed"]["geometry"] == 0 and k["fixed_errors"]["ocr"] > 0      # cannot tell geometry without boxes


def test_reports_written(tmp_path, rep):
    P.write_report(rep, tmp_path)
    md = (tmp_path / "pilot_report.md").read_text(encoding="utf-8")
    assert "Generic layout fit" in md and "| offset |" in md and "th_en" in md and "Gate G1" in md
    js = json.loads((tmp_path / "pilot_report.json").read_text())
    assert "slots" not in js and set(js["by_keyboard"]) == {"clean", "thai", "offset", "misprint"}
    assert len(SC.read_csv(tmp_path / "pilot_slots.csv")) == 8 * 26
