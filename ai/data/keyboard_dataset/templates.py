"""Empty dataset skeleton + CSV templates (plan P2.C). Never overwrites existing files unless `overwrite=True`."""
from __future__ import annotations

import json
from pathlib import Path

from ai.data.keyboard_dataset.arrangement import Arrangement, actual_labels
from ai.data.keyboard_dataset.schema import (ARRANGEMENTS_CSV, COCO_JSON, COCO_KEYCAP_ID, COCO_KEYCAP_NAME, IMAGE_COLS,
                                             IMAGES_CSV, IMAGES_DIR, KEYBOARD_COLS, KEYBOARDS_CSV, SLOT_COLS, SLOTS_CSV,
                                             SLOT_GT_SOURCES, ImageMeta, read_csv, parse_images, write_csv)
from ai.data.keyboard_dataset.arrangement import SCHEDULE_COLS
from ai.layouts import Layout


def empty_coco() -> dict:
    return {"info": {"description": "KeyCheck own QWERTY keycaps (original_oriented pixels)"}, "licenses": [],
            "images": [], "annotations": [], "categories": [{"id": COCO_KEYCAP_ID, "name": COCO_KEYCAP_NAME, "supercategory": "key"}]}


def write_templates(root: str | Path, *, overwrite: bool = False) -> list[str]:
    """Create the directory layout with header-only CSVs and an empty COCO file. Returns the files written."""
    root = Path(root)
    (root / IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    written = []
    for rel, cols in ((IMAGES_CSV, IMAGE_COLS), (KEYBOARDS_CSV, KEYBOARD_COLS), (SLOTS_CSV, SLOT_COLS),
                      (ARRANGEMENTS_CSV, SCHEDULE_COLS)):
        if overwrite or not (root / rel).exists():
            write_csv(root / rel, cols, [])
            written.append(rel)
    if overwrite or not (root / COCO_JSON).exists():
        (root / COCO_JSON).parent.mkdir(parents=True, exist_ok=True)
        (root / COCO_JSON).write_text(json.dumps(empty_coco(), indent=1) + "\n")
        written.append(COCO_JSON)
    (root / "manifests").mkdir(exist_ok=True)
    return written


def prefill_slots(images: list[ImageMeta], layout: Layout, schedule: dict[str, Arrangement] | None = None,
                  existing: set[str] | None = None) -> list[dict]:
    """26 rows per image with expected labels, `actual_label` from the planned arrangement (if known) and
    `ground_truth_status=pending_review`: an annotator must confirm each row against the photo."""
    rows = []
    existing = existing or set()
    for im in images:
        if im.source not in SLOT_GT_SOURCES or im.image_id in existing:
            continue
        arr = (schedule or {}).get(im.arrangement_id)
        act = actual_labels(arr, layout) if arr is not None else {}
        for sid, exp in zip(layout.slot_ids, layout.labels):
            rows.append({"image_id": im.image_id, "slot_id": sid, "expected_label": exp, "actual_label": act.get(sid, ""),
                         "readable": 1, "ground_truth_status": "pending_review",
                         "note": "" if arr is not None else "arrangement unknown: fill actual_label"})
    return rows


def append_prefilled_slots(root: str | Path, layout: Layout, schedule: dict[str, Arrangement] | None = None) -> int:
    """Add pending rows to metadata/slots.csv for images that have none yet. Returns the number of rows added."""
    root = Path(root)
    images, _ = parse_images(read_csv(root / IMAGES_CSV))
    old = read_csv(root / SLOTS_CSV) if (root / SLOTS_CSV).exists() else []
    new = prefill_slots(images, layout, schedule, existing={r["image_id"] for r in old})
    write_csv(root / SLOTS_CSV, SLOT_COLS, old + new)
    return len(new)
