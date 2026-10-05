"""Leave-keyboard-out split invariants and the P2.D validator (one test per violation)."""
from __future__ import annotations

import copy
from collections import defaultdict

import pytest

from ai.data.keyboard_dataset import manifest as M
from ai.data.keyboard_dataset import schema as SC
from ai.data.keyboard_dataset import split as S
from ai.data.keyboard_dataset import validate as V
from ai.data.keyboard_dataset.arrangement import load_schedule
from ai.data.keyboard_dataset.cli import main as cli_main
from ai.data.keyboard_dataset.synthetic import make_dataset
from ai.layouts import load_layout


@pytest.fixture(scope="module")
def layout():
    return load_layout("qwerty_stagger_letters_v1")


# ---- split (metadata only, no image files) --------------------------------------------------------------------------
def _kbs():
    roles = {**{f"kb{i}": "train" for i in range(1, 9)}, "kbv": "heldout_val", "kbt1": "unseen_test", "kbt2": "unseen_test"}
    return {k: SC.KeyboardMeta(k, legend_style="th_en" if k in ("kbt1", "kb2") else "en_only", role=r) for k, r in roles.items()}


def _images():
    ims = []
    for i, kid in enumerate(_kbs()):
        for s in range(4):
            for a in range(5):
                for shot in range(3):
                    ims.append(SC.ImageMeta(f"{kid}_s{s}_a{a}_{shot}", f"{kid}/{s}_{a}_{shot}.jpg", kid, f"{kid}_s{s}",
                                            f"arr{(i * 7 + s * 5 + a) % 40:03d}"))
    ims.append(SC.ImageMeta("pilot_kb1", "p1.jpg", "kb1", "kb1_pilot", "arr000", source="own_pilot"))
    ims.append(SC.ImageMeta("pilot_kbt1", "p2.jpg", "kbt1", "kbt1_pilot", "arr000", source="own_pilot"))
    ims.append(SC.ImageMeta("pilot_kbv", "p3.jpg", "kbv", "kbv_pilot", "arr000", source="own_pilot"))
    for i in range(6):
        ims.append(SC.ImageMeta(f"web{i}", f"web/{i}.jpg", "", "", "", source="web_cc", source_url="http://x", license="CC-BY-4.0"))
    return ims


TEST_ONLY = {"arr033", "arr034"}


@pytest.fixture(scope="module")
def split_res():
    return S.assign_splits(_images(), _kbs(), seed=11, test_only_arrangements=TEST_ONLY)


def test_leave_keyboard_out(split_res):
    a = split_res["assign"]
    for iid, v in a.items():
        kid = v["keyboard_id"]
        if iid.startswith("pilot_"):
            continue
        if kid in ("kbt1", "kbt2"):
            assert v["split"] == "test" and v["test_subset"] == "unseen_keyboard"
        elif kid == "kbv":
            assert v["split"] == "val"
    assert a["pilot_kb1"]["split"] == "train"
    assert a["pilot_kbt1"]["split"] == "excluded"
    assert a["pilot_kbv"]["split"] == "val"
    assert all(a[f"web{i}"]["split"] == "train" for i in range(6))
    assert split_res["unseen_test_keyboards"] == ["kbt1", "kbt2"] and split_res["heldout_val_keyboards"] == ["kbv"]


def test_groups_and_ratios(split_res):
    a = split_res["assign"]
    by_group = defaultdict(set)
    for v in a.values():
        if v["reason"] not in ("train_only_source",):
            by_group[v["group"]].add(v["split"])
    assert all(len(s) == 1 for s in by_group.values())             # burst / same arrangement never split
    seen = [v for v in a.values() if v["reason"] in ("group_split", "test_only_arrangement")]
    n = len(seen)
    frac = {s: sum(v["split"] == s for v in seen) / n for s in ("train", "val", "test")}
    assert abs(frac["train"] - 0.70) < 0.05 and abs(frac["val"] - 0.15) < 0.05 and abs(frac["test"] - 0.15) < 0.05
    for iid, v in a.items():
        if v["split"] == "test" and v["keyboard_id"].startswith("kb") and v["keyboard_id"][2:].isdigit():
            assert v["test_subset"] == "seen_keyboard"
    for v in a.values():
        if v["group"].split("|")[1] in TEST_ONLY and v["keyboard_id"] != "kbv" and not v["group"].endswith("pilot|arr000"):
            assert v["split"] in ("test", "excluded")
    assert split_res["test_only_arrangements"] and set(split_res["test_only_arrangements"]) <= TEST_ONLY


def test_split_deterministic_and_hash(split_res):
    again = S.assign_splits(_images(), _kbs(), seed=11, test_only_arrangements=TEST_ONLY)
    assert again["assign"] == split_res["assign"]
    other = S.assign_splits(_images(), _kbs(), seed=12, test_only_arrangements=TEST_ONLY)
    h1 = S.split_manifest_hash(split_res["assign"])
    assert h1 == S.split_manifest_hash(again["assign"]) and h1 != S.split_manifest_hash(other["assign"])
    sm = S.build_split_manifest(split_res, dataset_version="v_test")
    assert sm["split_manifest_hash"] == h1 and sm["seed"] == 11 and sm["counts"]["test"]["images"] > 0
    assert set(sm["counts"]["train"]["keyboards"]).isdisjoint({"kbt1", "kbt2", "kbv"})


def test_split_duplicates_merge():
    ims = [SC.ImageMeta(f"k1_{g}", f"{g}.jpg", "kb1", f"s{g}", "a") for g in range(40)]
    ims.append(SC.ImageMeta("t_dup", "t.jpg", "kbt", "st", "a"))
    kbs = {"kb1": SC.KeyboardMeta("kb1", legend_style="en_only"), "kbt": SC.KeyboardMeta("kbt", legend_style="th_en", role="unseen_test"),
           "kb2": SC.KeyboardMeta("kb2", legend_style="en_only")}
    ims.append(SC.ImageMeta("k2_x", "x.jpg", "kb2", "sx", "a"))
    pairs = [("k1_0", "k1_1", "near"), ("k1_1", "k1_2", "near"), ("k1_5", "t_dup", "exact"), ("k1_7", "k2_x", "near")]
    for seed in range(5):
        a = S.assign_splits(ims, kbs, seed=seed, dup_pairs=pairs)["assign"]
        assert a["k1_0"]["split"] == a["k1_1"]["split"] == a["k1_2"]["split"]
        assert a["k1_5"]["split"] == "test"                         # exact copy of an unseen-test photo stays out of train
        assert a["k1_5"]["reason"] == "merged_with_forced_group"
    # near-duplicates of different keyboards are not merged (perceptual-hash false positive)
    diff = [s for s in range(20) if (lambda r: r["k1_7"]["split"] != r["k2_x"]["split"])(S.assign_splits(ims, kbs, seed=s, dup_pairs=pairs)["assign"])]
    assert diff


# ---- validator ------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def clean(tmp_path_factory, layout):
    root = tmp_path_factory.mktemp("val") / "dataset"
    make_dataset(root, layout, seed=3, sessions=2, arrangements_per_session=2, shots=2)
    ds = SC.load_dataset(root)
    man = M.build_manifest(root, ds.images, dataset_version="t")
    sched = load_schedule(root / SC.ARRANGEMENTS_CSV)
    res = S.assign_splits(ds.images, ds.keyboards, seed=0, test_only_arrangements={k for k, v in sched.items() if v.test_only},
                          dup_pairs=M.duplicate_pairs(man))
    sm = S.build_split_manifest(res, dataset_version="t", manifest=man)
    M.write_manifest(man, root / SC.MANIFEST_JSON)
    S.write_split_manifest(sm, root / SC.SPLIT_MANIFEST_JSON)
    return {"root": root, "ds": ds, "man": man, "sm": sm, "sched": sched}


def _run(c, ds=None, sm=None, man=None, layout=None):
    return V.validate(ds or c["ds"], layout or load_layout("qwerty_stagger_letters_v1"), split_manifest=sm or c["sm"],
                      manifest=man or c["man"], schedule=c["sched"])


def _errors(probs):
    return {p.code for p in probs if p.severity == "error"}


def test_clean_dataset_passes(clean):
    probs = _run(clean)
    assert not _errors(probs), V.report(probs)
    assert V.exit_code(probs) == 0
    assert cli_main(["validate", str(clean["root"])]) == 0


def _first(c, split, keyboard_role=None):
    for iid, v in c["sm"]["images"].items():
        kb = c["ds"].keyboards.get(v["keyboard_id"])
        if v["split"] == split and (keyboard_role is None or kb.role == keyboard_role):
            return iid
    raise AssertionError(split)


def _move(c, iid, new_split):
    """Move a whole capture group (so only the targeted rule fires) and re-hash like the tool would."""
    sm = copy.deepcopy(c["sm"])
    g = sm["images"][iid]["group"]
    for v in sm["images"].values():
        if v["group"] == g:
            v["split"] = new_split
    sm["split_manifest_hash"] = S.split_manifest_hash(sm["images"], {k: v["sha256"] for k, v in sm["images"].items()})
    return sm


def test_box_outside_image(clean):
    ds = copy.deepcopy(clean["ds"])
    ds.coco["annotations"][0]["bbox"] = [790.0, 10.0, 30.0, 20.0]
    probs = _run(clean, ds=ds)
    assert "box_outside_image" in _errors(probs) and V.exit_code(probs) == 1


def test_bad_class_id(clean):
    ds = copy.deepcopy(clean["ds"])
    ds.coco["annotations"][3]["category_id"] = 2
    assert "bad_class_id" in _errors(_run(clean, ds=ds))
    ds = copy.deepcopy(clean["ds"])
    ds.coco["categories"].append({"id": 2, "name": "keyboard"})
    assert "bad_categories" in _errors(_run(clean, ds=ds))


def test_coco_duplicate_file(clean):
    ds = copy.deepcopy(clean["ds"])
    ds.coco["images"].append({**ds.coco["images"][0], "id": 99999})
    assert "coco_duplicate_file" in _errors(_run(clean, ds=ds))


def test_missing_slot(clean):
    ds = copy.deepcopy(clean["ds"])
    iid = ds.images[0].image_id
    del ds.slots[iid]["r1c4"]
    assert "slot_count" in _errors(_run(clean, ds=ds))


def test_duplicate_image_across_splits(clean):
    ds = copy.deepcopy(clean["ds"])
    src = ds.image(_first(clean, "test", "unseen_test"))
    dup = copy.deepcopy(src)
    dup.image_id, dup.capture_session_id = "dup_copy", "other_session"
    ds.images.append(dup)
    ds.slots["dup_copy"] = ds.slots[src.image_id]
    sm = copy.deepcopy(clean["sm"])
    sm["images"]["dup_copy"] = {**sm["images"][src.image_id], "split": "train", "group": "other_session|x"}
    sm["split_manifest_hash"] = S.split_manifest_hash(sm["images"], {k: v["sha256"] for k, v in sm["images"].items()})
    errs = _errors(V.validate(ds, load_layout("qwerty_stagger_letters_v1"), split_manifest=sm, manifest=None, schedule=clean["sched"]))
    assert "duplicate_across_splits" in errs and "unseen_keyboard_leak" in errs


def test_unseen_keyboard_in_train(clean):
    iid = _first(clean, "test", "unseen_test")
    assert "unseen_keyboard_leak" in _errors(_run(clean, sm=_move(clean, iid, "val")))


def test_heldout_keyboard_in_train(clean):
    iid = _first(clean, "val", "heldout_val")
    errs = _errors(_run(clean, sm=_move(clean, iid, "train")))
    assert errs == {"heldout_keyboard_leak"}


def test_web_source_in_val(clean):
    ds = copy.deepcopy(clean["ds"])
    iid = _first(clean, "val", "train")
    im = ds.image(iid)
    im.source, im.source_url, im.license = "web_cc", "http://example.org/x.jpg", "CC-BY-4.0"
    assert "train_only_source_leak" in _errors(_run(clean, ds=ds))


def test_test_only_arrangement_in_train(clean):
    sched = clean["sched"]
    sm = copy.deepcopy(clean["sm"])
    hits = [k for k, v in sm["images"].items() if v["reason"] == "test_only_arrangement"]
    if not hits:                                           # make one: mark the arrangement of a train image test-only
        iid = _first(clean, "train", "train")
        arr = clean["ds"].image(iid).arrangement_id
        sched = copy.deepcopy(sched)
        sched[arr].test_only = True
        probs = V.validate(clean["ds"], load_layout("qwerty_stagger_letters_v1"), split_manifest=sm, manifest=clean["man"], schedule=sched)
    else:
        probs = _run(clean, sm=_move(clean, hits[0], "train"))
    assert "test_only_arrangement_leak" in _errors(probs)


def test_group_split_leak_and_hash_tamper(clean):
    sm = copy.deepcopy(clean["sm"])
    iid = _first(clean, "train", "train")
    sm["images"][iid]["split"] = "val"                      # one burst frame moved by hand, hash not updated
    errs = _errors(_run(clean, sm=sm))
    assert {"group_split_leak", "split_hash_mismatch"} <= errs


def test_actual_label_vs_arrangement_warning(clean):
    ds = copy.deepcopy(clean["ds"])
    iid = ds.images[0].image_id
    s = ds.slots[iid]
    s["r0c0"].actual_label, s["r0c1"].actual_label = s["r0c1"].actual_label, s["r0c0"].actual_label
    probs = _run(clean, ds=ds)
    assert "actual_vs_arrangement" in {p.code for p in probs if p.severity == "warning"}


def test_d10_warnings(clean):
    ds = copy.deepcopy(clean["ds"])
    for k in ds.keyboards.values():
        if k.role == "unseen_test":
            k.legend_style = "en_only"
    probs = _run(clean, ds=ds)
    assert "d10_unseen_th_en" in {p.code for p in probs}


def test_cli_validate_exit_code(clean, tmp_path):
    import shutil
    root = tmp_path / "ds"
    shutil.copytree(clean["root"], root)
    sm = _move(clean, _first(clean, "val", "heldout_val"), "train")
    S.write_split_manifest(sm, root / SC.SPLIT_MANIFEST_JSON)
    assert cli_main(["validate", str(root)]) == 1
