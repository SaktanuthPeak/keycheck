"""Dataset validator (plan P2.D): labels, slot ground truth and split rules. Returns problems; CLI exit code 1 on errors."""
from __future__ import annotations

from collections import defaultdict

from ai.data.keyboard_dataset.arrangement import Arrangement, actual_labels
from ai.data.keyboard_dataset.manifest import sha256_file
from ai.data.keyboard_dataset.schema import (COCO_JSON, COCO_KEYCAP_ID, COCO_KEYCAP_NAME, OWN_SOURCES, SLOT_GT_SOURCES,
                                             TRAIN_ONLY_SOURCES, Dataset, Problem, ann_slot_id, check_slots_vs_layout,
                                             coco_index)
from ai.data.keyboard_dataset.split import split_manifest_hash
from ai.layouts import Layout
from ai.preprocessing.geometry import validate_reference_points

BOX_TOL_PX = 1.0


def _e(code, msg, where=""):
    return Problem("error", code, msg, where)


def _w(code, msg, where=""):
    return Problem("warning", code, msg, where)


def check_keyboards(ds: Dataset) -> list[Problem]:
    p = []
    kbs = ds.keyboards
    for im in ds.images:
        if im.source in OWN_SOURCES and im.keyboard_id and im.keyboard_id not in kbs:
            p.append(_e("unknown_keyboard", f"{im.image_id}: keyboard_id {im.keyboard_id} not in keyboards.csv"))
    unseen = [k for k in kbs.values() if k.role == "unseen_test"]
    held = [k for k in kbs.values() if k.role == "heldout_val"]
    if len(unseen) < 2:
        p.append(_w("d10_unseen_count", f"{len(unseen)} unseen_test keyboards (D10 asks for 2–3)"))
    if unseen and not any(k.legend_style == "th_en" for k in unseen):
        p.append(_w("d10_unseen_th_en", "no th_en keyboard among unseen_test keyboards (D10)"))
    if len(held) > 1:
        p.append(_w("d10_heldout_count", f"{len(held)} heldout_val keyboards (D10 expects 1)"))
    return p


def check_files(ds: Dataset, manifest: dict | None) -> tuple[list[Problem], dict[str, tuple[int, int]]]:
    """Files exist; returns oriented sizes from the manifest (or the CSV) for the box/ref-point checks."""
    p, size = [], {}
    man = {e["image_id"]: e for e in (manifest or {}).get("images", [])}
    for im in ds.images:
        if not ds.image_path(im).exists():
            p.append(_e("missing_image_file", f"{im.image_id}: {ds.image_path(im)} not found"))
        m = man.get(im.image_id)
        if m:
            size[im.image_id] = (m["width"], m["height"])
            if im.width and im.height and (im.width, im.height) != (m["width"], m["height"]):
                p.append(_e("size_mismatch", f"{im.image_id}: images.csv {im.width}x{im.height} != oriented file {m['width']}x{m['height']} (EXIF?)"))
        elif im.width and im.height:
            size[im.image_id] = (im.width, im.height)
    for im in ds.images:
        if im.ref_px is not None and im.image_id in size and not (im.width and im.height):
            err = validate_reference_points(im.ref_px, size[im.image_id])
            if err:
                p.append(_e("bad_ref_points", f"{im.image_id}: {err}"))
    return p, size


def check_coco(ds: Dataset, layout: Layout, size: dict[str, tuple[int, int]]) -> list[Problem]:
    if ds.coco is None:
        return [_w("no_coco", f"{COCO_JSON} not found: keycap boxes not checked")]
    p = []
    cats = {c["id"]: c.get("name") for c in ds.coco.get("categories", [])}
    if cats.get(COCO_KEYCAP_ID) != COCO_KEYCAP_NAME:
        p.append(_e("bad_categories", f"COCO categories must contain id {COCO_KEYCAP_ID} = '{COCO_KEYCAP_NAME}', got {cats}"))
    extra = {k: v for k, v in cats.items() if k != COCO_KEYCAP_ID}
    if extra:
        p.append(_e("bad_categories", f"only the single class '{COCO_KEYCAP_NAME}' is allowed, extra: {extra}"))
    names = [ci["file_name"] for ci in ds.coco.get("images", [])]
    for n in sorted({n for n in names if names.count(n) > 1}):
        p.append(_e("coco_duplicate_file", f"COCO lists {n} more than once"))
    idx = coco_index(ds.coco, ds.images)
    known = {v["coco_image"]["id"] for v in idx.values()}
    for ci in ds.coco.get("images", []):
        if ci["id"] not in known:
            p.append(_w("coco_image_unknown", f"COCO image {ci['file_name']} not in images.csv"))
    slot_set = set(layout.slot_ids)
    for im in ds.images:
        if im.image_id not in idx:
            if im.source in OWN_SOURCES:
                p.append(_w("no_boxes", f"{im.image_id}: no COCO entry (not annotated yet)"))
            continue
        ci, anns = idx[im.image_id]["coco_image"], idx[im.image_id]["anns"]
        W, H = size.get(im.image_id, (ci.get("width"), ci.get("height")))
        if (ci.get("width"), ci.get("height")) != (W, H):
            p.append(_e("coco_size_mismatch", f"{im.image_id}: COCO size {ci.get('width')}x{ci.get('height')} != original_oriented {W}x{H}"))
        seen_slot: dict[str, int] = {}
        for a in anns:
            where = f"ann {a.get('id')}"
            if a.get("category_id") not in cats or a.get("category_id") != COCO_KEYCAP_ID:
                p.append(_e("bad_class_id", f"{im.image_id}: category_id {a.get('category_id')} is not keycap ({COCO_KEYCAP_ID})", where))
            x, y, w, h = a["bbox"]
            if w <= 0 or h <= 0:
                p.append(_e("empty_box", f"{im.image_id}: bbox {a['bbox']} has no area", where))
            if W and H and (x < -BOX_TOL_PX or y < -BOX_TOL_PX or x + w > W + BOX_TOL_PX or y + h > H + BOX_TOL_PX):
                p.append(_e("box_outside_image", f"{im.image_id}: bbox {a['bbox']} outside {W}x{H}", where))
            sid = ann_slot_id(a)
            if sid is not None:
                if sid not in slot_set:
                    p.append(_e("bad_slot_attribute", f"{im.image_id}: slot_id attribute `{sid}` not in layout", where))
                elif sid in seen_slot:
                    p.append(_e("duplicate_slot_box", f"{im.image_id}: two boxes tagged {sid}", where))
                seen_slot[sid] = a.get("id")
    return p


def check_slots(ds: Dataset, layout: Layout, schedule: dict[str, Arrangement] | None) -> list[Problem]:
    p = []
    ids = {im.image_id for im in ds.images}
    for iid in sorted(set(ds.slots) - ids):
        p.append(_e("slots_unknown_image", f"slots.csv rows for unknown image_id {iid}"))
    for im in ds.images:
        if im.source not in SLOT_GT_SOURCES:
            continue
        if im.image_id not in ds.slots:
            p.append(_e("slot_count", f"{im.image_id}: 0/26 slot rows"))
            continue
        sl = ds.slots[im.image_id]
        p += check_slots_vs_layout(sl, layout, im.image_id)
        if im.source == "own_capture_fixed" and any(s.actual_label and s.actual_label != s.expected_label for s in sl.values()):
            p.append(_e("fixed_keyboard_swapped", f"{im.image_id}: non-removable keyboard must be all-correct"))
        if schedule is not None:
            arr = schedule.get(im.arrangement_id)
            if arr is None:
                p.append(_w("arrangement_unknown", f"{im.image_id}: arrangement_id {im.arrangement_id} not in the schedule"))
            else:
                want = actual_labels(arr, layout)
                bad = sorted(s for s, t in sl.items() if t.actual_label and s in want and t.actual_label != want[s])
                if bad:
                    p.append(_w("actual_vs_arrangement", f"{im.image_id}: actual_label differs from arrangement {arr.arrangement_id} at {bad}"))
                if arr.keyboard_id and im.keyboard_id and arr.keyboard_id != im.keyboard_id:
                    p.append(_w("arrangement_keyboard", f"{im.image_id}: planned on {arr.keyboard_id}, captured on {im.keyboard_id}"))
    return p


def check_splits(ds: Dataset, *, split_manifest: dict | None, manifest: dict | None,
                 schedule: dict[str, Arrangement] | None) -> list[Problem]:
    p = []
    split_of: dict[str, str] = {}
    if split_manifest is not None:
        for iid, a in split_manifest["images"].items():
            split_of[iid] = a["split"]
        for im in ds.images:
            if im.split and im.image_id in split_of and im.split != split_of[im.image_id]:
                p.append(_e("split_csv_mismatch", f"{im.image_id}: images.csv split {im.split} != split manifest {split_of[im.image_id]}"))
        sha_of = {k: v.get("sha256") or "" for k, v in split_manifest["images"].items()}
        if split_manifest.get("split_manifest_hash") and split_manifest_hash(split_manifest["images"], sha_of) != split_manifest["split_manifest_hash"]:
            p.append(_e("split_hash_mismatch", "split_manifest_hash does not match its content (edited by hand?)"))
    else:
        split_of = {im.image_id: im.split for im in ds.images if im.split}
    if not split_of:
        return [_w("no_split", "no split assigned yet: split rules not checked")]
    for im in ds.images:
        if im.image_id not in split_of:
            p.append(_w("no_split", f"{im.image_id}: no split"))
    kbs = ds.keyboards
    test_only = set(split_manifest.get("test_only_arrangements", []) if split_manifest else [])
    if schedule:
        test_only |= {k for k, a in schedule.items() if a.test_only}
    groups: dict[str, set] = defaultdict(set)
    group_kb: dict[str, set] = defaultdict(set)
    for im in ds.images:
        sp = split_of.get(im.image_id)
        if sp is None:
            continue
        kb = kbs.get(im.keyboard_id)
        role = kb.role if kb else None
        if role == "unseen_test" and sp in ("train", "val"):
            p.append(_e("unseen_keyboard_leak", f"{im.image_id}: unseen_test keyboard {im.keyboard_id} in {sp}"))
        if role == "heldout_val" and sp == "train":
            p.append(_e("heldout_keyboard_leak", f"{im.image_id}: heldout_val keyboard {im.keyboard_id} in train"))
        if im.source in TRAIN_ONLY_SOURCES and sp in ("val", "test"):
            p.append(_e("train_only_source_leak", f"{im.image_id}: source {im.source} in {sp} (Train only)"))
        if im.source == "own_pilot" and role == "unseen_test" and sp == "test":
            p.append(_e("pilot_in_unseen_test", f"{im.image_id}: pilot photo used as unseen Test"))
        if im.arrangement_id in test_only and sp in ("train", "val") and im.source not in TRAIN_ONLY_SOURCES:
            p.append(_e("test_only_arrangement_leak", f"{im.image_id}: test-only arrangement {im.arrangement_id} in {sp}"))
        if im.source not in TRAIN_ONLY_SOURCES and sp != "excluded":
            g = f"{im.capture_session_id}|{im.arrangement_id}"
            groups[g].add(sp)
            group_kb[g].add(im.keyboard_id)
    for g, sps in sorted(groups.items()):
        if len(sps) > 1:
            p.append(_e("group_split_leak", f"capture group {g} spans splits {sorted(sps)} (burst must stay together)"))
        if len(group_kb[g]) > 1:
            p.append(_w("group_multi_keyboard", f"capture group {g} has keyboards {sorted(group_kb[g])}: capture_session_id should be unique per keyboard"))
    # duplicates across splits
    if manifest is not None:
        sha = {e["image_id"]: e["sha256"] for e in manifest["images"]}
    else:
        sha = {im.image_id: sha256_file(ds.image_path(im)) for im in ds.images if ds.image_path(im).exists()}
    by_sha: dict[str, list[str]] = defaultdict(list)
    for iid, h in sha.items():
        by_sha[h].append(iid)
    for h, ids in sorted(by_sha.items()):
        sps = {split_of.get(i) for i in ids} - {None, "excluded"}
        if len(sps) > 1:
            p.append(_e("duplicate_across_splits", f"identical images {sorted(ids)} in splits {sorted(sps)}"))
    kb_of = {im.image_id: im.keyboard_id for im in ds.images}
    for n in (manifest or {}).get("near_duplicates", []):
        sa, sb = split_of.get(n["a"]), split_of.get(n["b"])
        if kb_of.get(n["a"]) != kb_of.get(n["b"]):
            continue                         # different keyboards: hash false positive, listed in the manifest only
        if sa and sb and sa != sb and "excluded" not in (sa, sb):
            p.append(_w("near_duplicate_across_splits", f"{n['a']} ({sa}) ~ {n['b']} ({sb}) dhash={n['dhash_dist']} phash={n['phash_dist']}"))
    return p


def validate(ds: Dataset, layout: Layout, *, split_manifest: dict | None = None, manifest: dict | None = None,
             schedule: dict[str, Arrangement] | None = None) -> list[Problem]:
    probs = list(ds.problems)
    probs += check_keyboards(ds)
    fp, size = check_files(ds, manifest)
    probs += fp
    probs += check_coco(ds, layout, size)
    probs += check_slots(ds, layout, schedule)
    probs += check_splits(ds, split_manifest=split_manifest, manifest=manifest, schedule=schedule)
    return probs


def exit_code(problems: list[Problem]) -> int:
    return 1 if any(p.severity == "error" for p in problems) else 0


def report(problems: list[Problem]) -> str:
    errs = [p for p in problems if p.severity == "error"]
    warns = [p for p in problems if p.severity == "warning"]
    lines = [f"errors: {len(errs)}  warnings: {len(warns)}"]
    lines += [str(p) for p in errs + warns]
    return "\n".join(lines)
