"""Q3b keycap classifier: reader contract, crop geometry shared with inference, bundle loading."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torchvision")

from conftest import write_bundle
from ai.classification.keycls import CLASSES, OTHER, KeyClassifier, build_model, make_reader
from ai.inference.inspector import BundleError, Inspector
from ai.recognition.ocr import crop_box_px
from ai.training.train_keycls import CropSet, _context_crop, crop_factor


def _weights(path, favour: str, arch="resnet18", size=32):
    """Untrained model whose fc bias makes `favour` win for every input."""
    m = build_model(arch)
    with torch.no_grad():
        m.fc.weight.zero_()
        m.fc.bias.fill_(-5.0)
        m.fc.bias[CLASSES.index(favour)] = 5.0
    torch.save({"model": m.state_dict(), "meta": {"classes": list(CLASSES), "arch": arch, "input": size}}, path)
    return path


def _crops(n=3):
    rng = np.random.default_rng(0)
    return [rng.integers(0, 255, (40 + 5 * i, 50, 3), dtype=np.uint8) for i in range(n)]


def test_reader_contract_letter(tmp_path):
    r = KeyClassifier(_weights(tmp_path / "w.pt", "Q"), device="cpu")
    out = r.read_labels(_crops())
    assert len(out) == 3
    for lab, score, raw in out:
        assert lab == "Q" and raw == "Q" and 0.9 < score <= 1.0


def test_other_is_unreadable_not_a_letter(tmp_path):
    r = KeyClassifier(_weights(tmp_path / "w.pt", OTHER), device="cpu")
    assert all(lab is None and raw == OTHER for lab, _, raw in r.read_labels(_crops()))
    assert r.read_labels([]) == []


def test_make_reader_resolves_relative_weights(tmp_path):
    _weights(tmp_path / "cls.pt", "Z")
    r = make_reader({"id": "keycls", "mode": "keycls", "weights": "cls.pt"}, device="gpu:0", base_dir=tmp_path)
    assert isinstance(r, KeyClassifier) and r.read_labels(_crops(1))[0][0] == "Z"


@pytest.mark.parametrize("mode", ["key_full", "key_full_pad0.1", "key_center_0.7"])
def test_eval_crop_matches_inference_crop(mode):
    """With augmentation off, the training crop is the same pixels inference cuts with crop_box_px."""
    rng = np.random.default_rng(1)
    canvas = cv2_blur(rng.integers(0, 255, (320, 768, 3), dtype=np.uint8))
    box = np.array([300.0, 120.0, 356.0, 174.0])
    n = 48
    stored = _context_crop(canvas, box, int(round(n * 1.4)))
    ds = CropSet.__new__(CropSet)
    ds.X, ds.labels, ds.size, ds.aug, ds.f = stored[None], np.array([0]), n, None, crop_factor(mode)
    x, _ = ds[0]
    from ai.classification.keycls import to_tensor_batch
    ref = to_tensor_batch([crop_box_px(canvas, box, mode)], n)[0]
    assert float((x - ref).abs().mean()) < 0.12


def cv2_blur(im):
    import cv2
    return cv2.GaussianBlur(im, (9, 9), 0)


def test_inspector_loads_classifier_from_bundle(tmp_path):
    root = tmp_path / "b"
    root.mkdir()
    _weights(root / "recognizer_keycls.pt", "A")
    write_bundle(root, ocr={"id": "keycls", "mode": "keycls", "weights": "recognizer_keycls.pt"})
    insp = Inspector(root)
    assert isinstance(insp.reader, KeyClassifier)
    write_bundle(root, ocr={"id": "keycls", "mode": "keycls", "weights": "../outside.pt"})
    with pytest.raises(BundleError):
        Inspector(root)
