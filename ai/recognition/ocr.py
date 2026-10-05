"""PP-OCRv5 recognition wrapper + label normalisation (plan Q3, Spec §6.2).

The expected label is never an input here. `0→O` / `1→I` style repairs are deliberately not done.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

_LATIN_A_Z = re.compile(r"^[A-Za-z]$")         # ASCII only: "ı".upper() == "I" must not count
_THAI_OR_SPACE = re.compile(r"[\u0E00-\u0E7F\s]+")


def normalize_label(text: str | None) -> str | None:
    """Drop Thai characters and whitespace, uppercase; return a single Latin A–Z letter or None (invalid).

    Thai-English keycaps read as e.g. "Aฟ" -> "A". Two Latin letters ("AS") or any other symbol ("Q@", "0") -> None.
    """
    if not text:
        return None
    t = _THAI_OR_SPACE.sub("", text)
    return t.upper() if _LATIN_A_Z.fullmatch(t) else None


def crop_box_px(canvas: np.ndarray, box_px, mode: str) -> np.ndarray:
    """mode: key_full | key_full_pad<frac> | key_center_<frac> (fraction of the key box kept around its centre)."""
    x0, y0, x1, y1 = box_px
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if mode == "key_full":
        pad, keep = 0.0, 1.0
    elif mode.startswith("key_full_pad"):
        pad, keep = float(mode[len("key_full_pad"):]), 1.0
    elif mode.startswith("key_center_"):
        pad, keep = 0.0, float(mode[len("key_center_"):])
    else:
        raise ValueError(mode)
    hw, hh = w * keep / 2 * (1 + 2 * pad), h * keep / 2 * (1 + 2 * pad)
    H, W = canvas.shape[:2]
    a, b, c, d = int(max(0, round(cx - hw))), int(max(0, round(cy - hh))), int(min(W, round(cx + hw))), int(min(H, round(cy + hh)))
    if c <= a or d <= b:
        return canvas[0:1, 0:1]
    return canvas[b:d, a:c]


@dataclass
class OcrSpec:
    id: str = "rec_server"
    mode: str = "rec"                       # rec: recognition only | auto: detection + recognition
    rec_model: str = "PP-OCRv5_server_rec"
    det_model: str | None = None
    pad_px: int = 8
    device: str = "cpu"                     # "cpu" | "gpu:0"


class PaddleReader:
    """Reads a list of BGR crops -> [(raw_text, score)]. Loads Paddle lazily (paddleocr 3.x API)."""

    def __init__(self, spec: OcrSpec):
        self.spec = spec
        self._rec = None
        self._ocr = None

    def _load(self):
        if self._rec is not None or self._ocr is not None:
            return
        if self.spec.mode == "rec":
            from paddleocr import TextRecognition
            self._rec = TextRecognition(model_name=self.spec.rec_model, device=self.spec.device, enable_mkldnn=False)
        else:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(text_detection_model_name=self.spec.det_model, text_recognition_model_name=self.spec.rec_model,
                                  use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
                                  device=self.spec.device, enable_mkldnn=False)
            self._rec_only = None

    def _pad(self, im: np.ndarray) -> np.ndarray:
        import cv2
        p = self.spec.pad_px
        if p:
            im = cv2.copyMakeBorder(im, p, p, p, p, cv2.BORDER_REPLICATE)
        return im

    def read(self, crops: list[np.ndarray], batch: int = 64) -> list[tuple[str, float]]:
        self._load()
        out: list[tuple[str, float]] = []
        for i in range(0, len(crops), batch):
            chunk = [self._pad(c) for c in crops[i:i + batch]]
            if self._rec is not None:
                for r in self._rec.predict(chunk, batch_size=len(chunk)):
                    out.append((str(r["rec_text"]), float(r["rec_score"])))
            else:
                for im in chunk:
                    res = self._ocr.predict(im)
                    texts, scores = (res[0].get("rec_texts", []), res[0].get("rec_scores", [])) if res else ([], [])
                    if texts:
                        j = int(np.argmax(scores))
                        out.append((str(texts[j]), float(scores[j])))
                    else:                                  # nothing found -> recognition only on the whole crop
                        if self._rec_only is None:
                            from paddleocr import TextRecognition
                            self._rec_only = TextRecognition(model_name=self.spec.rec_model, device=self.spec.device, enable_mkldnn=False)
                        r = next(iter(self._rec_only.predict([im])))
                        out.append((str(r["rec_text"]), float(r["rec_score"])))
        return out

    def read_labels(self, crops: list[np.ndarray]) -> list[tuple[str | None, float, str]]:
        """-> [(normalised letter or None, score, raw text)]"""
        return [(normalize_label(t), s, t) for t, s in self.read(crops)]

    def close(self):
        self._rec = self._ocr = None
        from ai.colab.bootstrap import free_memory
        free_memory()
