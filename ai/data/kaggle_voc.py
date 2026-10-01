"""Kaggle `keyboard-key-detection` (Pascal VOC, German QWERTZ) reader (plan Q1)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

LETTERS = [chr(c) for c in range(ord("a"), ord("z") + 1)]
KEYBOARD_CLASS = "keyboard"
IMG_EXT = (".jpg", ".jpeg", ".png")
_RF = re.compile(r"\.rf\.[0-9a-f]+$")
_SUFFIX = re.compile(r"_(jpg|jpeg|png)$", re.I)
_TRAIL_DIGITS = re.compile(r"\d+$")
UNBRANDED = {"sonstige", "sonstiges"}
EMPTY_BRAND = "empty"


@dataclass
class Box:
    name: str
    xyxy: tuple[float, float, float, float]


@dataclass
class Record:
    file_name: str
    split_dir: str            # original Kaggle split: train / test
    width: int
    height: int
    boxes: list[Box] = field(default_factory=list)
    source_id: str = ""
    brand_token: str = ""     # e.g. microsoft_pc
    brand_group: str = ""    # e.g. microsoft  (x and x_pc share a group)
    copy_index: int = 0


def source_id_of(stem: str) -> str:
    return _RF.sub("", stem)


def brand_of(source_id: str) -> tuple[str, str]:
    base = _TRAIL_DIGITS.sub("", _SUFFIX.sub("", source_id))
    base = base.rstrip("_") or source_id
    group = base[:-3] if base.endswith("_pc") and len(base) > 3 else base
    return base, group


def parse_xml(path: Path) -> tuple[str, int, int, list[Box]]:
    root = ET.parse(path).getroot()
    fn = root.findtext("filename") or path.with_suffix(".jpg").name
    w = int(float(root.findtext("size/width") or 0))
    h = int(float(root.findtext("size/height") or 0))
    boxes = []
    for o in root.findall("object"):
        bb = o.find("bndbox")
        if bb is None:
            continue
        xyxy = tuple(float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
        boxes.append(Box((o.findtext("name") or "").strip().lower(), xyxy))
    return fn, w, h, boxes


def load_dataset(root: str | Path, max_sources: int | None = None) -> list[Record]:
    """Read every XML under root/{train,test,valid}. `max_sources` keeps a deterministic prefix (smoke mode)."""
    root = Path(root)
    recs: list[Record] = []
    for split_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for xml in sorted(split_dir.glob("*.xml")):
            fn, w, h, boxes = parse_xml(xml)
            img = next((xml.with_suffix(e) for e in IMG_EXT if xml.with_suffix(e).exists()), None)
            if img is None:
                continue
            sid = source_id_of(xml.stem)
            tok, grp = brand_of(sid)
            recs.append(Record(f"{split_dir.name}/{img.name}", split_dir.name, w, h, boxes, sid, tok, grp))
    seen: dict[tuple[str, str], int] = {}
    for r in recs:
        k = (r.split_dir, r.source_id)
        r.copy_index = seen.get(k, 0)
        seen[k] = r.copy_index + 1
    if max_sources:
        keep = sorted({r.source_id for r in recs})
        keep = set(keep[:: max(1, len(keep) // max_sources)][:max_sources])
        recs = [r for r in recs if r.source_id in keep]
    return recs


def class_names(recs: list[Record]) -> list[str]:
    return sorted({b.name for r in recs for b in r.boxes})


def to_detector_class(name: str) -> str | None:
    """59 key classes -> `keycap`; `keyboard` is kept separate (returned as 'keyboard')."""
    if name == KEYBOARD_CLASS:
        return KEYBOARD_CLASS
    return "keycap"


def letter_boxes(rec: Record) -> dict[str, list[tuple]]:
    out: dict[str, list[tuple]] = {}
    for b in rec.boxes:
        if b.name in LETTERS:
            out.setdefault(b.name.upper(), []).append(b.xyxy)
    return out
