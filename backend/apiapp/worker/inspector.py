"""Inspector loading. `ai.inference` (and with it paddle) is imported only here, lazily, inside the worker."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.config import Settings

# layout_id -> object with .inspect(image_bgr, ref_points_px, on_stage=...), .bundle_id, .layout_id, .layout_version
InspectorFactory = Callable[[str], Any]


def default_inspector_factory(settings: Settings) -> InspectorFactory:
    def factory(layout_id: str) -> Any:
        from ai.inference import Inspector

        return Inspector(settings.MODEL_BUNDLE_DIR, layout_id=layout_id, ocr_device=settings.OCR_DEVICE)

    return factory


def is_invalid_reference_points(exc: BaseException) -> bool:
    """ai.inference.InvalidReferencePoints, matched by name so the API never has to import ai.inference."""
    return any(t.__name__ == "InvalidReferencePoints" for t in type(exc).__mro__)


def read_bundle_meta(bundle_dir: Path) -> dict | None:
    try:
        d = json.loads((Path(bundle_dir) / "bundle.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) else None
