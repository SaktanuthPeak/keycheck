"""Image manifest (plan P2.D): SHA-256 per image, exact duplicates and near-duplicates (dHash + pHash), across splits."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ai.data.keyboard_dataset.imaging import dhash, hamming_matrix, open_oriented, phash
from ai.data.keyboard_dataset.schema import IMAGES_DIR, ImageMeta

# Both distances must be within the limit (64-bit hashes). Tuned to catch re-encodes / resizes / small brightness
# changes of the same frame, not two separate photos of the same keyboard; check the report by eye.
NEAR_DHASH_MAX = 10
NEAR_PHASH_MAX = 8


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def image_entry(path: Path, image_id: str, file_name: str) -> dict:
    im, orient = open_oriented(path)
    return {"image_id": image_id, "file_name": file_name, "sha256": sha256_file(path), "bytes": path.stat().st_size,
            "width": im.width, "height": im.height, "exif_orientation": orient,
            "dhash": f"{dhash(im):016x}", "phash": f"{phash(im):016x}"}


def find_duplicates(entries: list[dict], split_of: dict[str, str] | None = None, *, dhash_max: int = NEAR_DHASH_MAX,
                    phash_max: int = NEAR_PHASH_MAX) -> tuple[list[dict], list[dict]]:
    """-> (exact groups, near-duplicate pairs). Exact = same SHA-256. Near = both hash distances within limits."""
    split_of = split_of or {}
    by_sha: dict[str, list[str]] = defaultdict(list)
    for e in entries:
        by_sha[e["sha256"]].append(e["image_id"])
    exact = []
    for sha, ids in sorted(by_sha.items()):
        if len(ids) > 1:
            sp = sorted({split_of.get(i, "") for i in ids})
            exact.append({"sha256": sha, "image_ids": sorted(ids), "splits": sp, "cross_split": len(set(sp) - {""}) > 1})
    ids = [e["image_id"] for e in entries]
    dm = hamming_matrix([int(e["dhash"], 16) for e in entries])
    pm = hamming_matrix([int(e["phash"], 16) for e in entries])
    near = []
    shas = [e["sha256"] for e in entries]
    for a, b in zip(*np.where(np.triu((dm <= dhash_max) & (pm <= phash_max), k=1))):
        if shas[a] == shas[b]:
            continue                                  # already an exact duplicate
        sa, sb = split_of.get(ids[a], ""), split_of.get(ids[b], "")
        near.append({"a": ids[a], "b": ids[b], "dhash_dist": int(dm[a, b]), "phash_dist": int(pm[a, b]),
                     "split_a": sa, "split_b": sb, "cross_split": bool(sa and sb and sa != sb)})
    near.sort(key=lambda d: (d["a"], d["b"]))
    return exact, near


def build_manifest(root: str | Path, images: list[ImageMeta], *, dataset_version: str,
                   split_of: dict[str, str] | None = None, dhash_max: int = NEAR_DHASH_MAX, phash_max: int = NEAR_PHASH_MAX) -> dict:
    root = Path(root)
    entries, missing = [], []
    for im in sorted(images, key=lambda i: i.image_id):
        p = root / IMAGES_DIR / im.file_name
        if not p.exists():
            missing.append(im.image_id)
            continue
        entries.append(image_entry(p, im.image_id, im.file_name))
    split_of = split_of if split_of is not None else {i.image_id: i.split for i in images if i.split}
    exact, near = find_duplicates(entries, split_of, dhash_max=dhash_max, phash_max=phash_max)
    return {"dataset_version": dataset_version, "n_images": len(entries), "missing_files": missing,
            "near_duplicate_thresholds": {"dhash_max": dhash_max, "phash_max": phash_max},
            "images": entries, "exact_duplicates": exact, "near_duplicates": near,
            "cross_split_exact": sum(e["cross_split"] for e in exact), "cross_split_near": sum(n["cross_split"] for n in near)}


def write_manifest(manifest: dict, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def duplicate_pairs(manifest: dict) -> list[tuple[str, str, str]]:
    """(a, b, kind) pairs the splitter keeps together; kind = exact (chained within a SHA group) | near."""
    out = []
    for g in manifest.get("exact_duplicates", []):
        ids = g["image_ids"]
        out += [(ids[0], x, "exact") for x in ids[1:]]
    out += [(n["a"], n["b"], "near") for n in manifest.get("near_duplicates", [])]
    return out
