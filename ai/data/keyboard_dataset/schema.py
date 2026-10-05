"""Metadata schema of the own QWERTY dataset (plan P2.C, Spec §5.4): dataclasses, CSV loaders and row-level checks.

Coordinates of `ref_*` and COCO boxes are pixels of the `original_oriented` image (after EXIF transpose, decision D6).
Loaders never raise on bad rows: they return (records, problems) so the validator can report everything at once.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ai.layouts import Layout
from ai.preprocessing.geometry import validate_reference_points

# ---- directory layout (relative to the dataset root) -------------------------------------------------------------
IMAGES_DIR = "images"
IMAGES_CSV = "metadata/images.csv"
KEYBOARDS_CSV = "metadata/keyboards.csv"
SLOTS_CSV = "metadata/slots.csv"
ARRANGEMENTS_CSV = "metadata/arrangements.csv"
COCO_JSON = "annotations/keycaps_coco.json"
MANIFEST_JSON = "manifests/manifest.json"
SPLIT_MANIFEST_JSON = "manifests/split_manifest.json"
DEFAULT_LAYOUT_ID = "qwerty_stagger_letters_v1"

# ---- columns ------------------------------------------------------------------------------------------------------
REF_COLS = ("ref_tl_x", "ref_tl_y", "ref_tr_x", "ref_tr_y", "ref_br_x", "ref_br_y", "ref_bl_x", "ref_bl_y")
IMAGE_COLS = ("image_id", "file_name", "keyboard_id", "capture_session_id", "arrangement_id", "device", "lighting",
              "split", "source", "source_url", "license", "width", "height", *REF_COLS, "subset", "note")
IMAGE_REQUIRED = ("image_id", "file_name", "source")
KEYBOARD_COLS = ("keyboard_id", "form_factor", "legend_style", "legend_position", "keycap_color", "legend_color",
                 "profile", "removable_keycaps", "role", "note")
SLOT_COLS = ("image_id", "slot_id", "expected_label", "actual_label", "readable", "ground_truth_status", "note")

# ---- enums --------------------------------------------------------------------------------------------------------
SPLITS = ("train", "val", "test", "excluded")
ROLES = ("train", "heldout_val", "unseen_test")
LEGEND_STYLES = ("en_only", "th_en")
LEGEND_POSITIONS = ("center", "top_left", "top_center", "bottom_left", "other")
FORM_FACTOR = re.compile(r"^(ANSI|ISO)(-(60|65|75|TKL|Full|laptop|other))?$")
LIGHTINGS = ("daylight", "indoor_warm", "indoor_cool", "mixed", "low", "flash", "other")
SUBSETS = ("main", "robustness")
GT_STATUSES = ("verified", "pending_review", "disputed")
# own_capture: removable keycaps (swaps + slot GT) | own_capture_fixed: non-removable, all-correct only
# own_pilot: pilot photos (Spec §5.2: may join Train, never unseen Test)
# public_dataset / web_cc / augment: detector Train only (Spec §5.1)
OWN_SOURCES = ("own_capture", "own_capture_fixed", "own_pilot")
TRAIN_ONLY_SOURCES = ("public_dataset", "web_cc", "augment")
SOURCES = OWN_SOURCES + TRAIN_ONLY_SOURCES
SLOT_GT_SOURCES = ("own_capture", "own_capture_fixed", "own_pilot")     # need 26 slot rows

COCO_KEYCAP_ID = 1           # COCO category id; YOLO class 0; torchvision label 1 (0 = background)
COCO_KEYCAP_NAME = "keycap"
_LETTER = re.compile(r"^[A-Z]$")
_TRUE = {"1", "true", "yes", "y", "t"}
_FALSE = {"0", "false", "no", "n", "f"}


@dataclass(frozen=True)
class Problem:
    severity: str            # error | warning
    code: str
    message: str
    where: str = ""

    def __str__(self):
        return f"[{self.severity}] {self.code}: {self.message}" + (f" ({self.where})" if self.where else "")


@dataclass
class ImageMeta:
    image_id: str
    file_name: str
    keyboard_id: str = ""
    capture_session_id: str = ""
    arrangement_id: str = ""
    device: str = ""
    lighting: str = ""
    split: str = ""
    source: str = "own_capture"
    source_url: str = ""
    license: str = ""
    width: int | None = None
    height: int | None = None
    ref_px: np.ndarray | None = None        # (4,2) TL TR BR BL on original_oriented
    subset: str = "main"
    note: str = ""

    @property
    def group_key(self) -> str:
        return f"{self.capture_session_id}|{self.arrangement_id}"


@dataclass
class KeyboardMeta:
    keyboard_id: str
    form_factor: str = ""
    legend_style: str = ""
    legend_position: str = ""
    keycap_color: str = ""
    legend_color: str = ""
    profile: str = ""
    removable_keycaps: bool | None = None
    role: str = "train"
    note: str = ""


@dataclass
class SlotTruth:
    image_id: str
    slot_id: str
    expected_label: str
    actual_label: str | None
    readable: bool
    ground_truth_status: str = "verified"
    note: str = ""


@dataclass
class Dataset:
    root: Path
    images: list[ImageMeta]
    keyboards: dict[str, KeyboardMeta]
    slots: dict[str, dict[str, SlotTruth]]          # image_id -> slot_id -> truth
    coco: dict | None = None
    problems: list[Problem] = field(default_factory=list)

    def image(self, image_id: str) -> ImageMeta:
        return next(i for i in self.images if i.image_id == image_id)

    def image_path(self, im: ImageMeta) -> Path:
        return self.root / IMAGES_DIR / im.file_name


# ---- helpers ------------------------------------------------------------------------------------------------------
def read_csv(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: str | Path, cols, rows: list[dict]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cols), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})


def parse_bool(v: str) -> bool | None:
    v = (v or "").strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    return None


def _int_or_none(v: str) -> int | None:
    try:
        return int(float(v)) if v not in ("", None) else None
    except ValueError:
        return None


def _missing_cols(rows: list[dict], cols, required, where: str) -> list[Problem]:
    if not rows:
        return []
    have = set(rows[0])
    out = [Problem("error", "missing_column", f"column `{c}` missing", where) for c in required if c not in have]
    out += [Problem("warning", "unknown_column", f"column `{c}` not in schema", where) for c in sorted(have - set(cols))]
    return out


# ---- parsers ------------------------------------------------------------------------------------------------------
def parse_ref(row: dict) -> tuple[np.ndarray | None, str | None]:
    vals = [row.get(c, "") for c in REF_COLS]
    if all(v == "" for v in vals):
        return None, None
    try:
        return np.array([float(v) for v in vals], float).reshape(4, 2), None
    except ValueError:
        return None, "reference points must be 8 numbers (TL TR BR BL x,y)"


def parse_images(rows: list[dict], where: str = IMAGES_CSV) -> tuple[list[ImageMeta], list[Problem]]:
    probs = _missing_cols(rows, IMAGE_COLS, IMAGE_REQUIRED, where)
    out, seen = [], set()
    for n, r in enumerate(rows, start=2):
        loc = f"{where}:{n}"
        iid = r.get("image_id", "")
        if not iid:
            probs.append(Problem("error", "missing_image_id", "empty image_id", loc))
            continue
        if iid in seen:
            probs.append(Problem("error", "duplicate_image_id", f"image_id {iid} appears twice", loc))
            continue
        seen.add(iid)
        ref, err = parse_ref(r)
        if err:
            probs.append(Problem("error", "bad_ref_points", err, loc))
        im = ImageMeta(
            image_id=iid, file_name=r.get("file_name", ""), keyboard_id=r.get("keyboard_id", ""),
            capture_session_id=r.get("capture_session_id", ""), arrangement_id=r.get("arrangement_id", ""),
            device=r.get("device", ""), lighting=r.get("lighting", ""), split=r.get("split", ""),
            source=r.get("source", "") or "own_capture", source_url=r.get("source_url", ""), license=r.get("license", ""),
            width=_int_or_none(r.get("width", "")), height=_int_or_none(r.get("height", "")), ref_px=ref,
            subset=r.get("subset", "") or "main", note=r.get("note", ""))
        probs += check_image_row(im, loc)
        out.append(im)
    return out, probs


def check_image_row(im: ImageMeta, loc: str) -> list[Problem]:
    p = []
    if not im.file_name:
        p.append(Problem("error", "missing_file_name", f"{im.image_id}: empty file_name", loc))
    if im.source not in SOURCES:
        p.append(Problem("error", "bad_source", f"{im.image_id}: source `{im.source}` not in {SOURCES}", loc))
    if im.split and im.split not in SPLITS:
        p.append(Problem("error", "bad_split", f"{im.image_id}: split `{im.split}` not in {SPLITS}", loc))
    if im.subset not in SUBSETS:
        p.append(Problem("error", "bad_subset", f"{im.image_id}: subset `{im.subset}` not in {SUBSETS}", loc))
    if im.lighting and im.lighting not in LIGHTINGS:
        p.append(Problem("warning", "unknown_lighting", f"{im.image_id}: lighting `{im.lighting}`", loc))
    if im.source in OWN_SOURCES:
        for c in ("keyboard_id", "capture_session_id", "arrangement_id"):
            if not getattr(im, c):
                p.append(Problem("error", f"missing_{c}", f"{im.image_id}: {c} required for source {im.source}", loc))
        if im.ref_px is None:
            p.append(Problem("error", "missing_ref_points", f"{im.image_id}: 4 reference points required for own photos", loc))
    if im.source in ("web_cc", "public_dataset") and (not im.source_url or not im.license):
        p.append(Problem("error", "missing_license", f"{im.image_id}: source_url and license required for {im.source}", loc))
    if im.ref_px is not None:
        wh = (im.width, im.height) if im.width and im.height else None
        err = validate_reference_points(im.ref_px, wh)
        if err:
            p.append(Problem("error", "bad_ref_points", f"{im.image_id}: {err}", loc))
    return p


def parse_keyboards(rows: list[dict], where: str = KEYBOARDS_CSV) -> tuple[dict[str, KeyboardMeta], list[Problem]]:
    probs = _missing_cols(rows, KEYBOARD_COLS, ("keyboard_id", "legend_style", "role"), where)
    out: dict[str, KeyboardMeta] = {}
    for n, r in enumerate(rows, start=2):
        loc = f"{where}:{n}"
        kid = r.get("keyboard_id", "")
        if not kid:
            probs.append(Problem("error", "missing_keyboard_id", "empty keyboard_id", loc))
            continue
        if kid in out:
            probs.append(Problem("error", "duplicate_keyboard_id", f"keyboard_id {kid} appears twice", loc))
            continue
        kb = KeyboardMeta(kid, r.get("form_factor", ""), r.get("legend_style", ""), r.get("legend_position", ""),
                          r.get("keycap_color", ""), r.get("legend_color", ""), r.get("profile", ""),
                          parse_bool(r.get("removable_keycaps", "")), r.get("role", "") or "train", r.get("note", ""))
        if kb.role not in ROLES:
            probs.append(Problem("error", "bad_role", f"{kid}: role `{kb.role}` not in {ROLES}", loc))
        if kb.legend_style not in LEGEND_STYLES:
            probs.append(Problem("error", "bad_legend_style", f"{kid}: legend_style `{kb.legend_style}` not in {LEGEND_STYLES}", loc))
        if kb.form_factor and not FORM_FACTOR.match(kb.form_factor):
            probs.append(Problem("warning", "unknown_form_factor", f"{kid}: form_factor `{kb.form_factor}` (expected ANSI|ISO[-60|65|75|TKL|Full|laptop|other])", loc))
        if kb.legend_position and kb.legend_position not in LEGEND_POSITIONS:
            probs.append(Problem("warning", "unknown_legend_position", f"{kid}: legend_position `{kb.legend_position}`", loc))
        if r.get("removable_keycaps", "") and kb.removable_keycaps is None:
            probs.append(Problem("error", "bad_bool", f"{kid}: removable_keycaps must be 0/1", loc))
        out[kid] = kb
    return out, probs


def parse_slots(rows: list[dict], where: str = SLOTS_CSV) -> tuple[dict[str, dict[str, SlotTruth]], list[Problem]]:
    probs = _missing_cols(rows, SLOT_COLS, ("image_id", "slot_id", "expected_label", "actual_label", "readable"), where)
    out: dict[str, dict[str, SlotTruth]] = {}
    for n, r in enumerate(rows, start=2):
        loc = f"{where}:{n}"
        iid, sid = r.get("image_id", ""), r.get("slot_id", "")
        rd = parse_bool(r.get("readable", ""))
        act = r.get("actual_label", "").upper() or None
        st = r.get("ground_truth_status", "") or "verified"
        if rd is None:
            probs.append(Problem("error", "bad_bool", f"{iid}/{sid}: readable must be 0/1", loc))
            rd = False
        if act is not None and not _LETTER.match(act):
            probs.append(Problem("error", "bad_actual_label", f"{iid}/{sid}: actual_label `{act}` is not one Latin A–Z letter", loc))
        if act is None and rd:
            probs.append(Problem("error", "missing_actual_label", f"{iid}/{sid}: readable slot needs actual_label", loc))
        if st not in GT_STATUSES:
            probs.append(Problem("error", "bad_gt_status", f"{iid}/{sid}: ground_truth_status `{st}` not in {GT_STATUSES}", loc))
        d = out.setdefault(iid, {})
        if sid in d:
            probs.append(Problem("error", "duplicate_slot", f"{iid}/{sid} appears twice", loc))
            continue
        d[sid] = SlotTruth(iid, sid, r.get("expected_label", "").upper(), act, rd, st, r.get("note", ""))
    return out, probs


def check_slots_vs_layout(slots: dict[str, SlotTruth], layout: Layout, image_id: str) -> list[Problem]:
    p = []
    have, want = set(slots), set(layout.slot_ids)
    if have != want:
        miss, extra = sorted(want - have), sorted(have - want)
        p.append(Problem("error", "slot_count", f"{image_id}: {len(have & want)}/26 layout slots"
                         + (f", missing {miss}" if miss else "") + (f", unknown {extra}" if extra else ""), SLOTS_CSV))
    for sid in sorted(have & want):
        exp = layout.labels[layout.index(sid)]
        if slots[sid].expected_label != exp:
            p.append(Problem("error", "expected_label_mismatch", f"{image_id}/{sid}: expected_label {slots[sid].expected_label} != layout {exp}", SLOTS_CSV))
    acts = [s.actual_label for s in slots.values() if s.actual_label]
    if len(acts) == len(layout.slot_ids) and sorted(acts) != sorted(layout.labels):
        p.append(Problem("warning", "actual_not_permutation", f"{image_id}: actual labels are not a permutation of A–Z (keycap from another set?)", SLOTS_CSV))
    for s in slots.values():
        if s.ground_truth_status != "verified":
            p.append(Problem("warning", "gt_not_verified", f"{image_id}/{s.slot_id}: ground_truth_status={s.ground_truth_status}", SLOTS_CSV))
    return p


# ---- COCO ---------------------------------------------------------------------------------------------------------
def load_coco(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def coco_index(coco: dict | None, images: list[ImageMeta]) -> dict[str, dict]:
    """image_id -> {"coco_image": {...}, "anns": [...]}; COCO images are matched by file_name, then by unique basename."""
    if not coco:
        return {}
    by_name = {ci["file_name"]: ci for ci in coco.get("images", [])}
    base: dict[str, list] = {}
    for ci in coco.get("images", []):
        base.setdefault(Path(ci["file_name"]).name, []).append(ci)
    anns: dict[int, list] = {}
    for a in coco.get("annotations", []):
        anns.setdefault(a["image_id"], []).append(a)
    out = {}
    for im in images:
        ci = by_name.get(im.file_name)
        if ci is None:
            cands = base.get(Path(im.file_name).name, [])
            ci = cands[0] if len(cands) == 1 else None
        if ci is not None:
            out[im.image_id] = {"coco_image": ci, "anns": anns.get(ci["id"], [])}
    return out


def coco_xyxy(ann: dict) -> np.ndarray:
    x, y, w, h = ann["bbox"]
    return np.array([x, y, x + w, y + h], float)


def ann_slot_id(ann: dict) -> str | None:
    """Optional `attributes.slot_id` (CVAT/Label Studio attribute) linking a keycap box to a layout slot."""
    v = (ann.get("attributes") or {}).get("slot_id") or ann.get("slot_id")
    return str(v) if v else None


# ---- whole dataset ------------------------------------------------------------------------------------------------
def load_dataset(root: str | Path) -> Dataset:
    root = Path(root)
    probs: list[Problem] = []
    images, keyboards, slots, coco = [], {}, {}, None
    if (root / IMAGES_CSV).exists():
        images, p = parse_images(read_csv(root / IMAGES_CSV))
        probs += p
    else:
        probs.append(Problem("error", "missing_file", f"{IMAGES_CSV} not found", str(root)))
    if (root / KEYBOARDS_CSV).exists():
        keyboards, p = parse_keyboards(read_csv(root / KEYBOARDS_CSV))
        probs += p
    else:
        probs.append(Problem("error", "missing_file", f"{KEYBOARDS_CSV} not found", str(root)))
    if (root / SLOTS_CSV).exists():
        slots, p = parse_slots(read_csv(root / SLOTS_CSV))
        probs += p
    if (root / COCO_JSON).exists():
        coco = load_coco(root / COCO_JSON)
    return Dataset(root, images, keyboards, slots, coco, probs)
