"""Own QWERTY dataset tooling (plan P2.A/P2.C/P2.D) on synthetic data: schema, templates, schedule, manifest, convert."""
from __future__ import annotations

import shutil

import numpy as np
import pytest
from PIL import Image, ImageEnhance

from ai.data.keyboard_dataset import arrangement as A
from ai.data.keyboard_dataset import convert as C
from ai.data.keyboard_dataset import manifest as M
from ai.data.keyboard_dataset import schema as SC
from ai.data.keyboard_dataset.cli import main as cli_main
from ai.data.keyboard_dataset.synthetic import make_dataset
from ai.data.keyboard_dataset.templates import prefill_slots, write_templates
from ai.layouts import load_layout
from ai.preprocessing import geometry as g


@pytest.fixture(scope="module")
def layout():
    return load_layout("qwerty_stagger_letters_v1")


@pytest.fixture(scope="module")
def synth_root(tmp_path_factory, layout):
    root = tmp_path_factory.mktemp("kbds") / "dataset"
    make_dataset(root, layout, seed=1, sessions=2, arrangements_per_session=2, shots=2)
    return root


# ---- schema ---------------------------------------------------------------------------------------------------------
def _img_row(**kw):
    r = {"image_id": "i1", "file_name": "a.jpg", "keyboard_id": "kb1", "capture_session_id": "s1", "arrangement_id": "a1",
         "source": "own_capture", "width": "100", "height": "100",
         **dict(zip(SC.REF_COLS, ["10", "10", "90", "10", "80", "60", "20", "60"]))}
    r.update(kw)
    return r


def _codes(probs):
    return {p.code for p in probs}


def test_parse_images_ok_and_errors():
    ims, probs = SC.parse_images([_img_row()])
    assert not [p for p in probs if p.severity == "error"]
    assert ims[0].ref_px.shape == (4, 2) and ims[0].group_key == "s1|a1"
    _, probs = SC.parse_images([_img_row(), _img_row()])
    assert "duplicate_image_id" in _codes(probs)
    _, probs = SC.parse_images([_img_row(**{c: "" for c in SC.REF_COLS})])
    assert "missing_ref_points" in _codes(probs)
    _, probs = SC.parse_images([_img_row(ref_tl_x="95", ref_tr_x="10")])          # crossing quad
    assert "bad_ref_points" in _codes(probs)
    _, probs = SC.parse_images([_img_row(source="web_cc", keyboard_id="")])
    assert "missing_license" in _codes(probs)
    _, probs = SC.parse_images([_img_row(source="scraped")])
    assert "bad_source" in _codes(probs)
    _, probs = SC.parse_images([_img_row(capture_session_id="")])
    assert "missing_capture_session_id" in _codes(probs)


def test_parse_keyboards_and_slots(layout):
    kbs, probs = SC.parse_keyboards([{"keyboard_id": "kb1", "legend_style": "th_en", "role": "unseen_test", "removable_keycaps": "1"},
                                     {"keyboard_id": "kb2", "legend_style": "thai", "role": "test"}])
    assert kbs["kb1"].removable_keycaps is True
    assert {"bad_role", "bad_legend_style"} <= _codes(probs)
    rows = [{"image_id": "i1", "slot_id": s, "expected_label": e, "actual_label": e, "readable": "1", "ground_truth_status": "verified"}
            for s, e in zip(layout.slot_ids, layout.labels)]
    slots, probs = SC.parse_slots(rows)
    assert not probs and len(slots["i1"]) == 26
    assert not [p for p in SC.check_slots_vs_layout(slots["i1"], layout, "i1") if p.severity == "error"]
    bad = rows[:-1] + [{**rows[0], "actual_label": "1"}]
    slots, probs = SC.parse_slots(bad)
    assert {"bad_actual_label", "duplicate_slot"} <= _codes(probs)
    assert "slot_count" in _codes(SC.check_slots_vs_layout(slots["i1"], layout, "i1"))


def test_templates_roundtrip(tmp_path, layout):
    written = write_templates(tmp_path)
    assert set(written) >= {SC.IMAGES_CSV, SC.KEYBOARDS_CSV, SC.SLOTS_CSV, SC.COCO_JSON}
    assert (tmp_path / SC.IMAGES_CSV).read_text().splitlines()[0].split(",") == list(SC.IMAGE_COLS)
    assert write_templates(tmp_path) == []                       # never overwrites
    ds = SC.load_dataset(tmp_path)
    assert not [p for p in ds.problems if p.severity == "error"] and ds.coco["categories"][0]["name"] == "keycap"
    arr = A.Arrangement("a1", "one_pair", A.perm_of([("r0c0", "r0c1")], []), [("r0c0", "r0c1")])
    ims, _ = SC.parse_images([_img_row()])
    rows = prefill_slots(ims, layout, {"a1": arr})
    assert len(rows) == 26 and all(r["ground_truth_status"] == "pending_review" for r in rows)
    got = {r["slot_id"]: r["actual_label"] for r in rows}
    assert got["r0c0"] == "W" and got["r0c1"] == "Q" and got["r1c0"] == "A"


# ---- arrangement schedule -------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def schedule(layout):
    kbs = [(f"kb{i}", "train") for i in range(8)] + [("kbv", "heldout_val"), ("kbt1", "unseen_test"), ("kbt2", "unseen_test")]
    return A.generate_schedule(layout, seed=7, keyboards=kbs)


def test_schedule_proportions(schedule):
    kinds = {k: sum(a.kind == k for a in schedule) for k in A.KINDS}
    assert kinds["correct"] == 100 and kinds["one_pair"] == 200 and kinds["multi_pair"] + kinds["cycle"] == 100
    assert kinds["cycle"] == 25
    for a in schedule:
        n = {"correct": (0,), "one_pair": (2,), "multi_pair": (4, 6), "cycle": (5,)}[a.kind]
        assert a.n_incorrect in n, a
        flat = [s for p in a.pairs for s in p] + [s for c in a.cycles for s in c]
        assert len(flat) == len(set(flat)) == a.n_incorrect          # disjoint pairs/cycles, no fixed points


def test_schedule_coverage(schedule, layout):
    cov = A.coverage(schedule, layout)
    assert cov["min_displaced"] >= 10
    train_cov = A.coverage(schedule, layout, include_test_only=False)
    assert train_cov["min_adjacent"] >= 1 and train_cov["min_cross_row"] >= 1
    types = [t for a in schedule for t in a.pair_types]
    assert 0.4 < types.count("cross_row") / len(types) < 0.6
    for a in schedule:
        lab = A.actual_labels(a, layout)
        assert sorted(lab.values()) == sorted(layout.labels)
        wrong = {s for s in layout.slot_ids if lab[s] != layout.labels[layout.index(s)]}
        assert wrong == set(a.perm)


def test_schedule_test_only_patterns(schedule):
    test_only = [a for a in schedule if a.test_only]
    assert 25 <= len(test_only) <= 35
    reserved = {a.pairs[0] for a in test_only}
    others = {p for a in schedule if not a.test_only for p in a.pairs}
    assert reserved and not (reserved & others)
    assert all(a.keyboard_id != "kbv" for a in test_only)          # heldout_val keyboard is Validation-only
    assert {a.keyboard_id for a in schedule} >= {f"kb{i}" for i in range(8)}


def test_schedule_deterministic_and_csv_roundtrip(tmp_path, schedule, layout):
    again = A.generate_schedule(layout, seed=7, keyboards=[(f"kb{i}", "train") for i in range(8)] + [("kbv", "heldout_val"), ("kbt1", "unseen_test"), ("kbt2", "unseen_test")])
    assert [A.to_row(a, layout) for a in again] == [A.to_row(a, layout) for a in schedule]
    other = A.generate_schedule(layout, seed=8)
    assert [a.perm for a in other] != [a.perm for a in schedule]
    A.write_schedule(schedule, layout, tmp_path / "s.csv")
    back = A.load_schedule(tmp_path / "s.csv")
    for a in schedule:
        b = back[a.arrangement_id]
        assert b.perm == a.perm and b.test_only == a.test_only and b.kind == a.kind
        assert sorted(b.pairs) == sorted(a.pairs) and len(b.cycles) == len(a.cycles)
        assert A.perm_of(b.pairs, b.cycles) == a.perm


# ---- manifest / duplicates ------------------------------------------------------------------------------------------
def test_manifest_exact_and_near_duplicates(tmp_path):
    rng = np.random.default_rng(0)
    imgs = tmp_path / "images"
    imgs.mkdir()
    base = Image.fromarray((rng.random((120, 200, 3)) * 255).astype(np.uint8)).resize((400, 240))
    base.save(imgs / "a.png")
    shutil.copy(imgs / "a.png", imgs / "a_copy.png")
    ImageEnhance.Brightness(base.resize((380, 228))).enhance(1.08).save(imgs / "a_near.jpg", quality=85)
    Image.fromarray((rng.random((120, 200, 3)) * 255).astype(np.uint8)).resize((400, 240)).save(imgs / "b.png")
    ims = [SC.ImageMeta(i, f) for i, f in (("a", "a.png"), ("a_copy", "a_copy.png"), ("a_near", "a_near.jpg"), ("b", "b.png"))]
    man = M.build_manifest(tmp_path, ims, dataset_version="t", split_of={"a": "train", "a_copy": "test", "a_near": "val", "b": "train"})
    assert man["n_images"] == 4 and all(len(e["sha256"]) == 64 for e in man["images"])
    assert man["exact_duplicates"][0]["image_ids"] == ["a", "a_copy"] and man["exact_duplicates"][0]["cross_split"]
    near = {(n["a"], n["b"]) for n in man["near_duplicates"]}
    assert ("a", "a_near") in near and ("a_copy", "a_near") in near
    assert not any("b" in p for p in near)
    assert man["cross_split_exact"] == 1 and man["cross_split_near"] >= 1
    assert ("a", "a_copy", "exact") in M.duplicate_pairs(man)


def test_manifest_exif_orientation(tmp_path):
    imgs = tmp_path / "images"
    imgs.mkdir()
    im = Image.new("RGB", (200, 100), (50, 60, 70))
    exif = im.getexif()
    exif[0x0112] = 6                                             # rotate 90° on display
    im.save(imgs / "r.jpg", exif=exif)
    man = M.build_manifest(tmp_path, [SC.ImageMeta("r", "r.jpg")], dataset_version="t")
    e = man["images"][0]
    assert (e["width"], e["height"], e["exif_orientation"]) == (100, 200, 6)


# ---- converter ------------------------------------------------------------------------------------------------------
def test_yolo_roundtrip_affine(layout):
    ppu = 64
    s, t = 50.0, np.array([120.0, 80.0])
    ref_px = layout.ref_points_u * s + t                        # axis-aligned: original = u * s + t
    H = C.image_H(ref_px, layout, ppu)
    w, h = g.canvas_size(ppu)
    box = np.array([200.0, 90.0, 245.0, 131.0])
    cb = g.transform_box(H, box)
    expect = ((box.reshape(2, 2) - t) / s - np.array(g.CANVAS_U[:2])) * ppu
    assert np.allclose(cb, expect.ravel(), atol=1e-6)
    cls, back = C.yolo_to_xyxy(C.xyxy_to_yolo(cb, w, h), w, h)
    assert cls == 0 and np.allclose(back, cb, atol=1e-3 * ppu)
    poly = C.canvas_box_to_original(H, back)
    assert np.allclose(poly, [[box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]], atol=0.05)


def test_coco_to_yolo_and_torchvision(tmp_path, synth_root, layout):
    ds = SC.load_dataset(synth_root)
    split_of = {im.image_id: ("train" if i % 2 else "val") for i, im in enumerate(ds.images)}
    idx = C.coco_to_yolo(ds, layout, tmp_path / "yolo", split_of=split_of, ppu=32, train_jitter=[("gt", 0.0), ("j1", 0.1)])
    n_train = sum(v == "train" for v in split_of.values())
    assert len(idx["items"]) == n_train * 2 + (len(ds.images) - n_train) and not idx["skipped"]
    assert not any(r["variant"] == "j1" for r in idx["items"] if r["split"] == "val")
    w, h = g.canvas_size(32)
    item = idx["items"][0]
    lines = (tmp_path / "yolo" / "labels" / item["split"] / f"{item['name']}.txt").read_text().split("\n")
    lines = [ln for ln in lines if ln]
    assert len(lines) == item["n_boxes_out"] >= 26
    for ln in lines:
        c, b = C.yolo_to_xyxy(ln, w, h)
        assert c == 0 and 0 <= b[0] < b[2] <= w + 1e-3 and 0 <= b[1] < b[3] <= h + 1e-3
    img = Image.open(tmp_path / "yolo" / "images" / item["split"] / f"{item['name']}.jpg")
    assert img.size == (w, h)
    assert "names:" in (tmp_path / "yolo" / "data.yaml").read_text()
    # the 26 letter boxes land on their layout slots after rectification (gt points, no jitter)
    gt_items = [r for r in idx["items"] if r["variant"] == "gt"]
    H = np.array(gt_items[0]["H"])
    im = ds.image(gt_items[0]["image_id"])
    anns = SC.coco_index(ds.coco, ds.images)[im.image_id]["anns"]
    for a in anns:
        sid = SC.ann_slot_id(a)
        if sid:
            c = g.box_center(g.transform_box(H, SC.coco_xyxy(a))) / 32 + np.array(g.CANVAS_U[:2])
            assert np.linalg.norm(c - layout.centers_u[layout.index(sid)]) < 0.05 or im.keyboard_id == "kb03"

    tv = C.coco_to_torchvision(ds, split_of=split_of, splits=("val",))
    assert len(tv) == len(ds.images) - n_train
    t0 = tv[0]
    assert t0["boxes"].dtype == np.float32 and t0["boxes"].shape[1] == 4
    assert set(t0["labels"].tolist()) == {C.TV_KEYCAP} and C.TV_BACKGROUND not in t0["labels"]
    assert np.all(t0["area"] > 0) and np.all(t0["iscrowd"] == 0)
    tvr = C.coco_to_torchvision(ds, split_of=split_of, splits=("val",), layout=layout, ppu=32)
    assert tvr[0]["canvas_wh"] == (w, h) and np.all(tvr[0]["boxes"][:, 2] <= w + 1e-3)


# ---- CLI ------------------------------------------------------------------------------------------------------------
def test_cli_schedule_and_init(tmp_path, capsys):
    assert cli_main(["schedule", "--out", str(tmp_path / "arr.csv"), "--seed", "3", "--n-correct", "4",
                     "--n-one-pair", "8", "--n-multi", "4", "--reserved-pairs", "2"]) == 0
    rows = SC.read_csv(tmp_path / "arr.csv")
    assert len(rows) == 16 and list(rows[0]) == list(A.SCHEDULE_COLS)
    assert cli_main(["init", str(tmp_path / "ds")]) == 0
    assert (tmp_path / "ds" / SC.COCO_JSON).exists()


@pytest.mark.parametrize("seed", range(6))
def test_schedule_coverage_any_seed(layout, seed):
    sched = A.generate_schedule(layout, seed=seed)
    cov, train_cov = A.coverage(sched, layout), A.coverage(sched, layout, include_test_only=False)
    assert cov["min_displaced"] >= 30
    assert train_cov["min_adjacent"] >= 1 and train_cov["min_cross_row"] >= 1
