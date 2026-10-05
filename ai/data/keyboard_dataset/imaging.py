"""Image loading in the `original_oriented` frame (EXIF transpose applied, Spec §7.2) and perceptual hashes (numpy + PIL)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

EXIF_ORIENTATION = 0x0112


def open_oriented(path: str | Path) -> tuple[Image.Image, int]:
    """-> (RGB image after EXIF transpose, original EXIF orientation tag or 1)."""
    with Image.open(path) as im:
        try:
            orient = int(im.getexif().get(EXIF_ORIENTATION, 1))
        except Exception:                  # noqa: BLE001 - broken EXIF must not stop a manifest run
            orient = 1
        out = ImageOps.exif_transpose(im).convert("RGB")
    return out, orient


def load_oriented_bgr(path: str | Path) -> np.ndarray:
    im, _ = open_oriented(path)
    return np.asarray(im)[:, :, ::-1].copy()


def _gray(im: Image.Image, size: tuple[int, int]) -> np.ndarray:
    return np.asarray(im.convert("L").resize(size, Image.Resampling.LANCZOS), float)


def dhash(im: Image.Image, n: int = 8) -> int:
    """Difference hash: n×n bits comparing horizontally adjacent pixels of an (n+1)×n thumbnail."""
    g = _gray(im, (n + 1, n))
    return _bits_to_int((g[:, 1:] > g[:, :-1]).ravel())


def _dct_matrix(n: int) -> np.ndarray:
    k = np.arange(n)[:, None]
    m = np.cos(np.pi * (2 * np.arange(n)[None, :] + 1) * k / (2 * n))
    m[0] *= 1 / np.sqrt(2)
    return m * np.sqrt(2 / n)


def phash(im: Image.Image, n: int = 8, scale: int = 4) -> int:
    """DCT perceptual hash: low n×n DCT block of a (n·scale)² thumbnail compared with its median (DC excluded)."""
    s = n * scale
    g = _gray(im, (s, s))
    D = _dct_matrix(s)
    low = (D @ g @ D.T)[:n, :n].ravel()
    med = np.median(low[1:])
    return _bits_to_int(low > med)


def _bits_to_int(bits: np.ndarray) -> int:
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def hamming_matrix(hashes: list[int]) -> np.ndarray:
    """Pairwise Hamming distances of 64-bit hashes (n×n, uint8)."""
    h = np.array(hashes, dtype=np.uint64)
    if len(h) == 0:
        return np.zeros((0, 0), np.uint8)
    x = h[:, None] ^ h[None, :]
    b = x.view(np.uint8).reshape(len(h), len(h), 8)
    return np.unpackbits(b, axis=2).sum(axis=2).astype(np.uint8)
