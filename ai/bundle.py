"""Dev model bundle (Spec §12.4): weights + thresholds + OCR/crop config + layout ids, with a content hash."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ai.pipeline.stage import file_sha256


def dir_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(file_sha256(p).encode())
    return h.hexdigest()


def build_bundle(out_dir: Path, *, bundle_id: str, detector: str, weights: Path | None, imgsz_or_model_cfg: dict | None, chosen: dict,
                 thresholds: dict, layouts: list[str], split_manifest_hash: str, commit: str, extra_files: dict[str, Path] | None = None) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    wname = None
    if weights is not None and Path(weights).exists():
        wname = f"weights_{detector}{Path(weights).suffix}"
        shutil.copy(weights, out_dir / wname)
    for name, src in (extra_files or {}).items():       # e.g. the Q3b keycap classifier named by chosen["recognizer"]["weights"]
        shutil.copy(src, out_dir / name)
    meta = {"bundle_id": bundle_id, "detector": detector, "weights_file": wname, "detector_config": imgsz_or_model_cfg, "px_per_unit": chosen["px_per_unit"],
            "crop_mode": chosen["crop_mode"], "ocr": chosen["recognizer"], "thresholds": thresholds, "layouts": layouts,
            "split_manifest_hash": split_manifest_hash, "commit": commit, "proxy": "Kaggle QWERTZ (dev bundle, not a production model)"}
    (out_dir / "bundle.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    meta["bundle_sha256"] = dir_hash(out_dir)
    return meta
