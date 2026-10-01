"""One-to-one assignment of detections to layout slots (Spec §7.4–7.5). All geometry is in u (key pitch = 1)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

BIG = 1e6


def match(det_centers_u: np.ndarray, slot_centers_u: np.ndarray, *, gating_u: float, unmatched_cost: float,
          ambiguity_margin_u: float) -> dict:
    """Returns {slot_index: {"det": i, "dist": d, "ambiguous": bool}}.

    Rows = detections + one dummy per slot; columns = slots + one dummy per detection, so any slot may stay
    unmatched (cost `unmatched_cost`) and extra detections (keys outside A–Z) are free of consequence.
    The expected letter is never used here.
    """
    n, m = len(det_centers_u), len(slot_centers_u)
    if n == 0:
        return {}
    D = np.linalg.norm(det_centers_u[:, None, :] - slot_centers_u[None, :, :], axis=2)      # (n, m)
    C = np.full((n + m, m + n), BIG)
    C[:n, :m] = np.where(D <= gating_u, D, BIG)
    C[np.arange(n), m + np.arange(n)] = gating_u + 1e-3                                       # det left unmatched
    C[n + np.arange(m), np.arange(m)] = unmatched_cost                                        # slot left unmatched
    C[n:, m:] = 0.0
    rows, cols = linear_sum_assignment(C)
    out = {}
    for r, c in zip(rows, cols):
        if r < n and c < m and D[r, c] <= gating_u:
            others_slot = np.delete(D[r], c)
            others_det = np.delete(D[:, c], r)
            d2 = min([x for x in list(others_slot) + list(others_det) if x <= gating_u] or [np.inf])
            out[int(c)] = {"det": int(r), "dist": float(D[r, c]), "ambiguous": bool(d2 - D[r, c] < ambiguity_margin_u)}
    return out
