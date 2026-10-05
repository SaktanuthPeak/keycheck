"""Arrangement schedule (plan P2.A, Spec §5.2–5.3): which keycaps to swap for each capture, deterministic per seed.

`perm[dst] = src` means slot `dst` holds the keycap that belongs to slot `src` (same convention as
ai/data/synthetic_swap.py). Slots are positional (`r<row>c<col>`); letters only appear in the human `instructions`.
Pair selection is greedy on the least displaced slots, so every letter leaves its slot many times, both in
same-row neighbour swaps (`adjacent`) and cross-row swaps (`cross_row`). Some pairs are reserved: arrangements that
use them are `test_only` and the splitter forces them into Test (Spec §5.5).
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from ai.data.keyboard_dataset.schema import read_csv, write_csv
from ai.layouts import Layout

KINDS = ("correct", "one_pair", "multi_pair", "cycle")
SCHEDULE_COLS = ("arrangement_id", "kind", "n_incorrect", "perm", "instructions", "pair_types", "test_only",
                 "keyboard_id", "planned_shots")


@dataclass
class Arrangement:
    arrangement_id: str
    kind: str
    perm: dict[str, str] = field(default_factory=dict)          # dst slot -> src slot (only displaced slots)
    pairs: list[tuple[str, str]] = field(default_factory=list)
    cycles: list[tuple[str, ...]] = field(default_factory=list)  # (a, b, c): a's keycap -> b, b's -> c, c's -> a
    pair_types: list[str] = field(default_factory=list)
    test_only: bool = False
    keyboard_id: str = ""
    planned_shots: int = 1

    @property
    def n_incorrect(self) -> int:
        return len(self.perm)


def row_of(slot_id: str) -> int:
    return int(slot_id[1:slot_id.index("c")])


def col_of(slot_id: str) -> int:
    return int(slot_id[slot_id.index("c") + 1:])


def pair_type(a: str, b: str) -> str:
    if row_of(a) != row_of(b):
        return "cross_row"
    return "adjacent" if abs(col_of(a) - col_of(b)) == 1 else "same_row"


def all_pairs(layout: Layout) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list] = {"adjacent": [], "cross_row": [], "same_row": []}
    for a, b in combinations(layout.slot_ids, 2):
        out[pair_type(a, b)].append(tuple(sorted((a, b))))
    return out


def perm_of(pairs, cycles) -> dict[str, str]:
    perm = {}
    for a, b in pairs:
        perm[a], perm[b] = b, a
    for cyc in cycles:
        for i, s in enumerate(cyc):
            perm[cyc[(i + 1) % len(cyc)]] = s      # keycap of s now sits on the next slot of the cycle
    return perm


def actual_labels(arr: Arrangement | dict[str, str] | None, layout: Layout) -> dict[str, str]:
    """slot_id -> letter of the keycap sitting there under this arrangement."""
    perm = arr.perm if isinstance(arr, Arrangement) else (arr or {})
    lab = dict(zip(layout.slot_ids, layout.labels))
    return {s: lab[perm.get(s, s)] for s in layout.slot_ids}


def instructions(arr: Arrangement, layout: Layout) -> str:
    lab = dict(zip(layout.slot_ids, layout.labels))
    parts = [f"{lab[a]}<->{lab[b]}" for a, b in arr.pairs]
    parts += ["->".join(lab[s] for s in (*c, c[0])) for c in arr.cycles]
    return "; ".join(parts) if parts else "-"


class _Picker:
    def __init__(self, layout: Layout, rng: random.Random, reserved: set):
        self.pairs = all_pairs(layout)
        self.slots = list(layout.slot_ids)
        self.rng = rng
        self.reserved = reserved
        self.cnt: Counter = Counter()
        self.cnt_type: Counter = Counter()
        self.used: Counter = Counter()
        self.n_type: Counter = Counter()

    def next_type(self, cross_frac: float) -> str:
        n = self.n_type["adjacent"] + self.n_type["cross_row"]
        if n == 0:
            return "cross_row" if cross_frac >= 0.5 else "adjacent"
        return "cross_row" if self.n_type["cross_row"] / n < cross_frac else "adjacent"

    def pair(self, ptype: str, busy: set, *, reserved_only: bool = False) -> tuple[str, str]:
        cands = [p for p in self.pairs[ptype] if not (set(p) & busy) and ((p in self.reserved) == reserved_only)]
        if not cands:                                 # fall back to the other type rather than fail
            other = "cross_row" if ptype == "adjacent" else "adjacent"
            cands = [p for p in self.pairs[other] if not (set(p) & busy) and ((p in self.reserved) == reserved_only)]
            ptype = other
        best = min(cands, key=lambda p: (self.cnt_type[(p[0], ptype)] + self.cnt_type[(p[1], ptype)],
                                         self.cnt[p[0]] + self.cnt[p[1]], self.used[p], self.rng.random()))
        for s in best:
            self.cnt[s] += 1
            self.cnt_type[(s, ptype)] += 1
        self.used[best] += 1
        self.n_type[ptype] += 1
        return best

    def cycle(self, busy: set, k: int = 3) -> tuple[str, ...]:
        out: list[str] = []
        for _ in range(k):
            rows = {row_of(s) for s in out}
            cands = [s for s in self.slots if s not in busy and s not in out]
            s = min(cands, key=lambda s: (row_of(s) in rows, self.cnt[s], self.rng.random()))   # spread over rows
            out.append(s)
        for s in out:
            self.cnt[s] += 1
            self.cnt_type[(s, "cycle")] += 1
        return tuple(out)


def generate_schedule(layout: Layout, *, seed: int, n_correct: int = 100, n_one_pair: int = 200, n_multi: int = 100,
                      cycle_fraction: float = 0.25, cross_row_fraction: float = 0.5, n_reserved_pairs: int = 8,
                      test_only_fraction: float = 0.10, keyboards: list[tuple[str, str]] | None = None,
                      planned_shots: int = 1, id_prefix: str = "arr") -> list[Arrangement]:
    """Counts follow Spec §5.2 (100 correct / 200 one pair / 100 two–three pairs); `n_multi` includes cycle
    arrangements (one 3-cycle + one pair = 5 wrong slots). `keyboards`: [(keyboard_id, role)] to assign rows round-robin;
    test-only rows never go to a `heldout_val` keyboard (it is Validation-only)."""
    rng = random.Random(seed)
    pools = all_pairs(layout)
    n_res_adj = max(1, n_reserved_pairs // 4) if n_reserved_pairs else 0
    free_adj = Counter(s for p in pools["adjacent"] for s in p)
    reserved: set = set()
    for p in rng.sample(pools["adjacent"], len(pools["adjacent"])):   # every slot keeps >= 1 unreserved neighbour swap
        if len(reserved) < n_res_adj and free_adj[p[0]] > 1 and free_adj[p[1]] > 1:
            reserved.add(p)
            free_adj.subtract(p)
    reserved |= set(rng.sample(pools["cross_row"], max(0, n_reserved_pairs - n_res_adj)))
    pk =_Picker(layout, rng, reserved)
    n_cycle = int(round(n_multi * cycle_fraction))
    plan = ["one_pair"] * n_one_pair + ["multi_pair"] * (n_multi - n_cycle) + ["cycle"] * n_cycle
    rng.shuffle(plan)
    n_test = int(round(test_only_fraction * len(plan))) if reserved else 0
    test_idx = set(rng.sample(range(len(plan)), n_test))
    swapped: list[Arrangement] = []
    for i, kind in enumerate(plan):
        t_only = i in test_idx
        busy: set = set()
        pairs, types, cycles = [], [], []
        n_pairs = {"one_pair": 1, "multi_pair": rng.randint(2, 3), "cycle": 1}[kind]
        if kind == "cycle":
            cycles.append(pk.cycle(busy))
            busy |= set(cycles[0])
        for j in range(n_pairs):
            pt = pk.next_type(cross_row_fraction)
            p = pk.pair(pt, busy, reserved_only=t_only and j == 0)
            pairs.append(p)
            types.append(pair_type(*p))
            busy |= set(p)
        swapped.append(Arrangement("", kind, perm_of(pairs, cycles), pairs, cycles, types, t_only))
    out = [Arrangement("", "correct") for _ in range(n_correct)] + swapped
    rng.shuffle(out)
    for k, a in enumerate(out, start=1):
        a.arrangement_id = f"{id_prefix}_{k:04d}"
        a.planned_shots = planned_shots
    if keyboards:
        assign_keyboards(out, keyboards, rng)
    return out


def assign_keyboards(arrs: list[Arrangement], keyboards: list[tuple[str, str]], rng: random.Random):
    """Round-robin per kind so every keyboard gets a mix; test-only rows skip heldout_val keyboards."""
    allk = [k for k, _ in keyboards]
    no_val = [k for k, r in keyboards if r != "heldout_val"] or allk
    for kind in KINDS:
        for t_only in (False, True):
            group = [a for a in arrs if a.kind == kind and a.test_only == t_only]
            ks = (no_val if t_only else allk)[:]
            rng.shuffle(ks)
            for i, a in enumerate(group):
                a.keyboard_id = ks[i % len(ks)]


# ---- I/O ----------------------------------------------------------------------------------------------------------
def to_row(a: Arrangement, layout: Layout) -> dict:
    return {"arrangement_id": a.arrangement_id, "kind": a.kind, "n_incorrect": a.n_incorrect,
            "perm": ";".join(f"{d}={s}" for d, s in sorted(a.perm.items())), "instructions": instructions(a, layout),
            "pair_types": ";".join(a.pair_types + ["cycle"] * len(a.cycles)), "test_only": int(a.test_only),
            "keyboard_id": a.keyboard_id, "planned_shots": a.planned_shots}


def from_row(r: dict) -> Arrangement:
    perm = dict(x.split("=") for x in r.get("perm", "").split(";") if x)
    pairs, seen = [], set()
    for d, s in perm.items():
        if perm.get(s) == d and d not in seen:
            pairs.append(tuple(sorted((d, s))))
            seen |= {d, s}
    rest = {d: s for d, s in perm.items() if d not in seen}
    cycles = []
    while rest:
        inv = {s: d for d, s in rest.items()}         # keycap of s sits on inv[s]
        start = min(rest)
        cyc, cur = [start], inv[start]
        while cur != start and cur in inv and cur not in cyc:
            cyc.append(cur)
            cur = inv[cur]
        cycles.append(tuple(cyc))
        for x in cyc:
            rest.pop(x, None)
    types = [t for t in r.get("pair_types", "").split(";") if t and t != "cycle"]
    return Arrangement(r["arrangement_id"], r.get("kind", "") or ("correct" if not perm else "one_pair"), perm, pairs, cycles,
                       types, r.get("test_only", "0") in ("1", "true", "True"), r.get("keyboard_id", ""),
                       int(r.get("planned_shots", "1") or 1))


def write_schedule(arrs: list[Arrangement], layout: Layout, path: str | Path):
    write_csv(path, SCHEDULE_COLS, [to_row(a, layout) for a in arrs])


def load_schedule(path: str | Path) -> dict[str, Arrangement]:
    return {a.arrangement_id: a for a in (from_row(r) for r in read_csv(path))}


def coverage(arrs: list[Arrangement], layout: Layout, *, include_test_only: bool = True) -> dict:
    """Per slot displacement counts: total and by pair type, plus kind counts."""
    tot: Counter = Counter()
    by: dict[str, Counter] = {"adjacent": Counter(), "cross_row": Counter(), "same_row": Counter(), "cycle": Counter()}
    for a in arrs:
        if a.test_only and not include_test_only:
            continue
        for p, t in zip(a.pairs, a.pair_types):
            for s in p:
                tot[s] += 1
                by[t][s] += 1
        for c in a.cycles:
            for s in c:
                tot[s] += 1
                by["cycle"][s] += 1
    return {"kinds": dict(Counter(a.kind for a in arrs)), "test_only": sum(a.test_only for a in arrs),
            "min_displaced": min(tot[s] for s in layout.slot_ids),
            "min_adjacent": min(by["adjacent"][s] for s in layout.slot_ids),
            "min_cross_row": min(by["cross_row"][s] for s in layout.slot_ids),
            "per_slot": {s: {"total": tot[s], **{k: by[k][s] for k in by}} for s in layout.slot_ids}}
