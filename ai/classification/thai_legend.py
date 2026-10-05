"""Synthetic Thai legends for Thai-English keycaps (Kedmanee), drawn onto training crops so the A–Z classifier learns to
ignore them. Kaggle QWERTZ has no Thai keycaps; real ones print one or two Thai characters beside the Latin letter.
"""
from __future__ import annotations

import glob
from functools import lru_cache

import numpy as np

# letter -> (unshifted, shifted) on the Thai Kedmanee layout
KEDMANEE = {
    "Q": ("ๆ", "๐"), "W": ("ไ", "\""), "E": ("ำ", "ฎ"), "R": ("พ", "ฑ"), "T": ("ะ", "ธ"), "Y": ("ั", "ํ"), "U": ("ี", "๊"),
    "I": ("ร", "ณ"), "O": ("น", "ฯ"), "P": ("ย", "ญ"), "A": ("ฟ", "ฤ"), "S": ("ห", "ฆ"), "D": ("ก", "ฏ"), "F": ("ด", "โ"),
    "G": ("เ", "ฌ"), "H": ("้", "็"), "J": ("่", "๋"), "K": ("า", "ษ"), "L": ("ส", "ศ"), "Z": ("ผ", "("), "X": ("ป", ")"),
    "C": ("แ", "ฉ"), "V": ("อ", "ฮ"), "B": ("ิ", "ฺ"), "N": ("ื", "์"), "M": ("ท", "?"),
}
# what non-letter keys of a Thai keyboard carry (number row, punctuation keys)
OTHER_POOL = list("ๅ/-ภถุึคตจขชๆ๑๒๓๔๕ูฃ฿๖๗๘๙๐บลฃซวฅฝใฌฦ")
FONT_GLOB = "/usr/share/fonts/truetype/noto/Noto*Thai*.ttf"


@lru_cache(maxsize=1)
def font_files() -> tuple[str, ...]:
    return tuple(sorted(glob.glob(FONT_GLOB)))


@lru_cache(maxsize=64)
def _font(path: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(path, size)


def legend_color(crop: np.ndarray, key_box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    """Colour of the printed legends: the far end of the key's brightness from its background."""
    x0, y0, x1, y1 = key_box
    k = crop[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    lum = k.mean(axis=1)
    bg = np.median(lum)
    sel = lum >= np.percentile(lum, 97) if bg < 128 else lum <= np.percentile(lum, 3)
    return tuple(int(v) for v in k[sel].mean(axis=0)) if sel.any() else ((235,) * 3 if bg < 128 else (25,) * 3)


def draw_thai(crop: np.ndarray, label: str | None, rng: np.random.Generator, key_frac: float) -> np.ndarray:
    """crop: RGB context crop whose central `key_frac` of the side is the key. label: A–Z or None (non-letter key).
    Draws 1–2 Thai legends on the right / lower part of the key, in the key's legend colour."""
    from PIL import Image, ImageDraw
    fonts = font_files()
    if not fonts:
        return crop
    S = crop.shape[0]
    k = S * key_frac
    kx0 = ky0 = (S - k) / 2
    box = (int(kx0), int(ky0), int(kx0 + k), int(ky0 + k))
    col = legend_color(crop, box)
    if label in KEDMANEE:
        chars = list(KEDMANEE[label]) if rng.random() < 0.7 else [KEDMANEE[label][int(rng.integers(2))]]
    else:
        chars = [OTHER_POOL[int(i)] for i in rng.integers(len(OTHER_POOL), size=int(rng.integers(1, 3)))]
    im = Image.fromarray(crop)
    d = ImageDraw.Draw(im)
    font_path = fonts[int(rng.integers(len(fonts)))]
    size = max(6, int(k * rng.uniform(0.28, 0.45)))
    f = _font(font_path, size)
    # typical spots: right column (shifted above, unshifted below) or bottom row
    layout = rng.choice(["right_col", "bottom_row", "right_mid"], p=[0.6, 0.25, 0.15])
    for j, ch in enumerate(chars):
        if layout == "right_col":
            cx, cy = kx0 + k * rng.uniform(0.62, 0.8), ky0 + k * (0.3 if j == 0 and len(chars) == 2 else 0.68) + k * rng.uniform(-0.06, 0.06)
        elif layout == "bottom_row":
            cx, cy = kx0 + k * (0.3 + 0.4 * j if len(chars) == 2 else rng.uniform(0.3, 0.7)), ky0 + k * rng.uniform(0.68, 0.8)
        else:
            cx, cy = kx0 + k * rng.uniform(0.62, 0.78), ky0 + k * (0.5 + (0.22 * (j - 0.5) * 2 if len(chars) == 2 else 0))
        d.text((cx, cy), ch, font=f, fill=col, anchor="mm")
    return np.asarray(im)
