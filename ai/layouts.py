"""Layout loading. Slots are identified by position (`slot_id` = r<row>c<col>), not by letter (plan §2, Q-D1)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

LAYOUT_DIR = Path(__file__).resolve().parent.parent / "layouts"


@dataclass(frozen=True)
class Layout:
    layout_id: str
    slot_ids: tuple[str, ...]
    labels: tuple[str, ...]          # expected label per slot
    centers_u: np.ndarray            # (N,2)
    regions_u: np.ndarray            # (N,4) xyxy acceptance region per slot
    ref_slot_ids: tuple[str, ...]    # TL, TR, BR, BL
    ref_points_u: np.ndarray         # (4,2)
    px_per_unit: int
    margin_u: float
    fit: dict
    internal_only: bool

    def index(self, slot_id: str) -> int:
        return self.slot_ids.index(slot_id)

    def label_to_slot(self) -> dict[str, str]:
        return dict(zip(self.labels, self.slot_ids))


def load_layout(layout_id_or_path: str | Path) -> Layout:
    p = Path(layout_id_or_path)
    if not p.exists():
        cands = list(LAYOUT_DIR.rglob(f"{layout_id_or_path}.json"))
        if not cands:
            raise FileNotFoundError(layout_id_or_path)
        p = cands[0]
    d = json.loads(p.read_text())
    slots = d["slots"]
    ref = d["reference_points_definition"]
    return Layout(
        layout_id=d["layout_id"],
        slot_ids=tuple(s["slot_id"] for s in slots),
        labels=tuple(s["expected_label"] for s in slots),
        centers_u=np.array([s["center_u"] for s in slots], float),
        regions_u=np.array([s["region_u"] for s in slots], float),
        ref_slot_ids=tuple(ref["slot_ids"]),
        ref_points_u=np.array(ref["points_u"], float),
        px_per_unit=int(d["px_per_unit"]),
        margin_u=float(d["margin_u"]),
        fit=dict(d["fit_thresholds"]),
        internal_only=bool(d.get("internal_only", False)),
    )
