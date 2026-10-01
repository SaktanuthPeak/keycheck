"""S3: synthetic key swaps on rectified images (plan Q2). Evaluation only — never used for training."""
from __future__ import annotations

from ai.layouts import Layout


def _sw(pairs):
    perm = {}
    for a, b in pairs:
        perm[a], perm[b] = b, a
    return perm


def make_swaps(layout: Layout, *, rng, kinds: list[str]) -> dict[str, dict]:
    """Return {kind: {perm: {dst_slot: src_slot}, incorrect: [...], suggestions: [...]}}.

    `perm[dst] = src` means the key shown at `src` is pasted onto slot `dst`. Slot ids are positional.
    """
    rows: dict[int, list[str]] = {}
    for sid in layout.slot_ids:
        rows.setdefault(int(sid[1]), []).append(sid)
    out: dict[str, dict] = {}
    used: set[str] = set()

    def pick_adjacent():
        r = int(rng.integers(0, 3))
        cols = rows[r]
        i = int(rng.integers(0, len(cols) - 1))
        return cols[i], cols[i + 1]

    def pick_cross():
        r1, r2 = (int(x) for x in rng.choice(3, 2, replace=False))
        return rows[r1][int(rng.integers(0, len(rows[r1])))], rows[r2][int(rng.integers(0, len(rows[r2])))]

    def fresh(fn):
        for _ in range(50):
            res = fn()
            flat = {x for x in (res if isinstance(res[0], str) else [y for p in res for y in p])}
            if not (flat & used):
                used.update(flat)
                return res
        return fn()

    for kind in kinds:
        if kind == "adjacent":
            a, b = fresh(pick_adjacent)
            perm, sug = _sw([(a, b)]), [{"type": "swap_pair", "slots": sorted([a, b])}]
        elif kind == "cross_row":
            a, b = fresh(pick_cross)
            perm, sug = _sw([(a, b)]), [{"type": "swap_pair", "slots": sorted([a, b])}]
        elif kind == "multi_pairs":
            n = int(rng.integers(2, 4))
            pairs = [fresh(pick_adjacent if i % 2 == 0 else pick_cross) for i in range(n)]
            perm = _sw(pairs)
            sug = [{"type": "swap_pair", "slots": sorted(p)} for p in pairs]
        elif kind == "cycle3":
            r = int(rng.integers(0, 3))
            cols = rows[r]
            i = int(rng.integers(0, len(cols) - 2))
            a, b, c = cols[i], cols[i + 1], cols[i + 2]
            perm = {a: b, b: c, c: a}               # a shows b's key, b shows c's key, c shows a's key
            sug = [{"type": "cycle", "slots": sorted([a, b, c])}]
        else:
            raise ValueError(kind)
        out[kind] = {"perm": perm, "incorrect": sorted(perm), "suggestions": sug}
    return out
