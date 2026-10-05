"""Decode an uploaded/stored photo into the `original_oriented` frame (EXIF orientation applied, Spec §7.2)."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def load_oriented_bgr(src: str | Path | bytes) -> np.ndarray:
    """File path or bytes -> HxWx3 uint8 BGR with EXIF orientation applied."""
    im = Image.open(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
    im = ImageOps.exif_transpose(im)
    rgb = np.asarray(im.convert("RGB"))
    return np.ascontiguousarray(rgb[:, :, ::-1])
