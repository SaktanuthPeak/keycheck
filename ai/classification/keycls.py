"""Closed-set keycap classifier (A–Z + OTHER), a drop-in for PaddleReader (plan Q3b).

Reads a crop of one key and returns its printed letter. Like the OCR wrapper it never sees the expected label, and it
does no `0→O` style repair: an O keycap is learnt from O keycaps, a `0` key falls in OTHER.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

LETTERS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
OTHER = "OTHER"
CLASSES = LETTERS + (OTHER,)
MEAN = np.array([0.485, 0.456, 0.406], np.float32)
STD = np.array([0.229, 0.224, 0.225], np.float32)


def build_model(arch: str, n_classes: int = len(CLASSES), pretrained: bool = False):
    import torch.nn as nn
    import torchvision
    if arch == "resnet18":
        m = torchvision.models.resnet18(weights="DEFAULT" if pretrained else None)
        m.fc = nn.Linear(m.fc.in_features, n_classes)
    elif arch == "mobilenet_v3_small":
        m = torchvision.models.mobilenet_v3_small(weights="DEFAULT" if pretrained else None)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, n_classes)
    else:
        raise ValueError(arch)
    return m


def to_tensor_batch(crops_rgb: list[np.ndarray], size: int):
    """uint8 RGB crops (any size) -> normalised float tensor (N,3,size,size)."""
    import cv2
    import torch
    x = np.stack([cv2.resize(c, (size, size), interpolation=cv2.INTER_AREA if min(c.shape[:2]) > size else cv2.INTER_LINEAR)
                  for c in crops_rgb]).astype(np.float32) / 255.0
    x = (x - MEAN) / STD
    return torch.from_numpy(x.transpose(0, 3, 1, 2).copy())


def _torch_device(device: str | None) -> str:
    import torch
    if not device:
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device.startswith("gpu"):                      # Paddle style "gpu:0"
        device = "cuda" + device[3:]
    return device if device == "cpu" or torch.cuda.is_available() else "cpu"


class KeyClassifier:
    """read_labels(BGR crops) -> [(letter or None, softmax score, predicted class)], same contract as PaddleReader."""

    def __init__(self, weights: str | Path, device: str | None = "cpu", batch: int = 256):
        import torch
        self.device = _torch_device(device)
        ck = torch.load(str(weights), map_location="cpu", weights_only=False)
        self.meta = ck["meta"]
        assert tuple(self.meta["classes"]) == CLASSES, "classifier classes differ from this code"
        self.size = int(self.meta["input"])
        self.model = build_model(self.meta["arch"]).eval().to(self.device)
        self.model.load_state_dict(ck["model"])
        self.batch = batch

    def probs(self, crops_bgr: list[np.ndarray]) -> np.ndarray:
        import torch
        out = []
        with torch.no_grad():
            for i in range(0, len(crops_bgr), self.batch):
                x = to_tensor_batch([c[:, :, ::-1] for c in crops_bgr[i:i + self.batch]], self.size).to(self.device)
                out.append(torch.softmax(self.model(x).float(), 1).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, len(CLASSES)), np.float32)

    def read_labels(self, crops: list[np.ndarray]) -> list[tuple[str | None, float, str]]:
        res = []
        for p in self.probs(crops):
            k = int(np.argmax(p))
            res.append((None if CLASSES[k] == OTHER else CLASSES[k], float(p[k]), CLASSES[k]))
        return res

    def close(self):
        self.model = None
        from ai.colab.bootstrap import free_memory
        free_memory()


def make_reader(spec: dict, *, device: str | None = "cpu", base_dir: str | Path | None = None):
    """Reader from a recognizer spec: mode 'keycls' -> KeyClassifier (weights relative to base_dir), else PaddleReader."""
    if spec.get("mode") == "keycls":
        w = Path(spec["weights"])
        if not w.is_absolute() and base_dir is not None:
            w = Path(base_dir) / w
        return KeyClassifier(w, device=device)
    from dataclasses import fields
    from ai.recognition.ocr import OcrSpec, PaddleReader
    names = {f.name for f in fields(OcrSpec)}
    return PaddleReader(OcrSpec(**{**{k: v for k, v in spec.items() if k in names}, "device": device or "cpu"}))
