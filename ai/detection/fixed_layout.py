"""Baseline 'detector': fixed layout crops (Spec §6.4). Boxes are the layout slot regions, score 1."""
from __future__ import annotations

import numpy as np

from ai.pipeline.evidence import u_to_px


def fixed_layout_boxes(layout, ppu: int):
    return u_to_px(layout.regions_u, ppu), np.ones(len(layout.slot_ids))
