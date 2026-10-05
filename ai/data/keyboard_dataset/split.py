"""Leave-keyboard-out + group split of the own QWERTY dataset (plan P2.D, Spec §5.5, decision D10).

Order of rules (first match wins):
1. Train-only sources (public_dataset / web_cc / augment) -> train (excluded if tagged with a held-out keyboard).
2. `unseen_test` keyboards -> test (`test_subset=unseen_keyboard`); pilot photos of them -> excluded.
3. `heldout_val` keyboard -> val.
4. Pilot photos of train keyboards -> train.
5. Everything else is grouped by (capture_session_id, arrangement_id); exact duplicates (any keyboard) and
   near-duplicates of the same keyboard are merged into one group (a merged group that contains a forced image takes
   its split). Test-only arrangements go to test; the rest is split 70/15/15 by image count with a recorded seed.
   Near-duplicates across different keyboards are perceptual-hash false positives (same layout, similar framing) and
   are only reported by the manifest.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from ai.data.keyboard_dataset.schema import (IMAGE_COLS, IMAGES_CSV, ImageMeta, KeyboardMeta, TRAIN_ONLY_SOURCES,
                                             read_csv, write_csv)

DEFAULT_FRACTIONS = {"train": 0.70, "val": 0.15, "test": 0.15}
DEFAULT_GROUP_KEYS = ("capture_session_id", "arrangement_id")
_PRIORITY = ("test", "val", "train", "excluded")       # a merged group with several forced splits keeps the strictest


class _UF:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        if a in self.p and b in self.p:
            ra, rb = self.find(a), self.find(b)
            if ra != rb:
                self.p[max(ra, rb)] = min(ra, rb)


def group_key(im: ImageMeta, keys=DEFAULT_GROUP_KEYS) -> str:
    return "|".join(str(getattr(im, k)) for k in keys)


def forced_split(im: ImageMeta, keyboards: dict[str, KeyboardMeta]) -> tuple[str | None, str]:
    kb = keyboards.get(im.keyboard_id)
    role = kb.role if kb else None
    if im.source in TRAIN_ONLY_SOURCES:
        if role in ("unseen_test", "heldout_val"):
            return "excluded", "train_only_source_on_heldout_keyboard"
        return "train", "train_only_source"
    if kb is None:
        return "excluded", "unknown_keyboard"
    if role == "unseen_test":
        if im.source == "own_pilot":
            return "excluded", "pilot_on_unseen_test_keyboard"
        return "test", "unseen_test_keyboard"
    if role == "heldout_val":
        return "val", "heldout_val_keyboard"
    if im.source == "own_pilot":
        return "train", "pilot"
    return None, ""


def assign_splits(images: list[ImageMeta], keyboards: dict[str, KeyboardMeta], *, seed: int,
                  fractions: dict[str, float] | None = None, group_keys=DEFAULT_GROUP_KEYS,
                  test_only_arrangements: set[str] | None = None, dup_pairs: list[tuple] | None = None) -> dict:
    """-> {"assign": {image_id: {split, test_subset, group, keyboard_id, reason}}, meta...}. Deterministic for a seed."""
    fr = dict(fractions or DEFAULT_FRACTIONS)
    tot = sum(fr.values())
    fr = {k: fr.get(k, 0.0) / tot for k in ("train", "val", "test")}
    test_only = set(test_only_arrangements or ())
    by_id = {im.image_id: im for im in images}
    uf = _UF(by_id)
    gk = {iid: group_key(im, group_keys) for iid, im in by_id.items()}
    first_of_group: dict[str, str] = {}
    for iid in sorted(by_id):
        k = gk[iid]
        if by_id[iid].source not in TRAIN_ONLY_SOURCES:
            if k in first_of_group:
                uf.union(first_of_group[k], iid)
            else:
                first_of_group[k] = iid
    for a, b, *kind in dup_pairs or ():
        if a not in by_id or b not in by_id:
            continue
        if (kind[0] if kind else "exact") == "exact" or by_id[a].keyboard_id == by_id[b].keyboard_id:
            uf.union(a, b)

    forced = {iid: forced_split(im, keyboards) for iid, im in by_id.items()}
    comps: dict[str, list[str]] = defaultdict(list)
    for iid in sorted(by_id):
        comps[uf.find(iid)].append(iid)

    assign: dict[str, dict] = {}
    pool: list[tuple[str, list[str]]] = []
    for root, ids in sorted(comps.items()):
        fs = {forced[i][0] for i in ids if forced[i][0] is not None}
        free = [i for i in ids if forced[i][0] is None]
        for i in ids:
            if forced[i][0] is not None:
                assign[i] = {"split": forced[i][0], "reason": forced[i][1]}
        if not free:
            continue
        if fs:
            sp = next(s for s in _PRIORITY if s in fs)
            for i in free:
                assign[i] = {"split": sp, "reason": "merged_with_forced_group"}
        elif any(by_id[i].arrangement_id in test_only for i in free):
            for i in free:
                assign[i] = {"split": "test", "reason": "test_only_arrangement"}
        else:
            pool.append((root, free))

    n_seen = sum(len(f) for _, f in pool) + sum(1 for i, a in assign.items() if a["reason"] == "test_only_arrangement")
    target = {s: fr[s] * n_seen for s in fr}
    cur = {s: float(sum(1 for a in assign.values() if a["reason"] == "test_only_arrangement" and s == "test")) for s in fr}
    rng = random.Random(seed)
    rng.shuffle(pool)
    pool.sort(key=lambda g: -len(g[1]))                                  # stable: big groups first, random among equals
    for _, ids in pool:
        s = max(("train", "val", "test"), key=lambda s: (target[s] - cur[s]) / max(target[s], 1e-9) if target[s] > 0 else -1e9)
        cur[s] += len(ids)
        for i in ids:
            assign[i] = {"split": s, "reason": "group_split"}

    for iid, a in assign.items():
        im = by_id[iid]
        kb = keyboards.get(im.keyboard_id)
        a["test_subset"] = ("unseen_keyboard" if kb and kb.role == "unseen_test" else "seen_keyboard") if a["split"] == "test" else None
        a["group"] = gk[iid]
        a["keyboard_id"] = im.keyboard_id
    roles = defaultdict(list)
    for k, kb in keyboards.items():
        roles[kb.role].append(k)
    used_test_only = sorted({by_id[i].arrangement_id for i, a in assign.items() if a["reason"] == "test_only_arrangement"})
    return {"assign": dict(sorted(assign.items())), "seed": seed, "fractions": fr, "group_keys": list(group_keys),
            "unseen_test_keyboards": sorted(roles["unseen_test"]), "heldout_val_keyboards": sorted(roles["heldout_val"]),
            "test_only_arrangements": used_test_only}


def split_counts(assign: dict[str, dict]) -> dict:
    out: dict = {}
    for a in assign.values():
        d = out.setdefault(a["split"], {"images": 0, "keyboards": set(), "groups": set()})
        d["images"] += 1
        if a["keyboard_id"]:
            d["keyboards"].add(a["keyboard_id"])
        d["groups"].add(a["group"])
    return {k: {"images": v["images"], "groups": len(v["groups"]), "keyboards": sorted(v["keyboards"])} for k, v in sorted(out.items())}


def split_manifest_hash(assign: dict[str, dict], sha_of: dict[str, str] | None = None) -> str:
    sha_of = sha_of or {}
    payload = json.dumps(sorted((k, v["split"], v.get("test_subset"), sha_of.get(k, "")) for k, v in assign.items()),
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def build_split_manifest(result: dict, *, dataset_version: str, manifest: dict | None = None) -> dict:
    sha_of = {e["image_id"]: e["sha256"] for e in (manifest or {}).get("images", [])}
    assign = result["assign"]
    imgs = {k: {**v, "sha256": sha_of.get(k)} for k, v in assign.items()}
    out = {"dataset_version": dataset_version, "seed": result["seed"], "fractions": result["fractions"],
           "group_keys": result["group_keys"], "unseen_test_keyboards": result["unseen_test_keyboards"],
           "heldout_val_keyboards": result["heldout_val_keyboards"], "test_only_arrangements": result["test_only_arrangements"],
           "image_manifest_sha256": hashlib.sha256(json.dumps(manifest["images"], sort_keys=True).encode()).hexdigest() if manifest else None,
           "counts": split_counts(assign), "images": imgs}
    out["split_manifest_hash"] = split_manifest_hash(assign, sha_of)
    return out


def write_split_manifest(sm: dict, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sm, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_split_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_splits_to_csv(root: str | Path, assign: dict[str, dict]):
    """Fill the `split` column of metadata/images.csv in place (other columns kept as they are)."""
    p = Path(root) / IMAGES_CSV
    rows = read_csv(p)
    cols = list(rows[0].keys()) if rows else list(IMAGE_COLS)
    if "split" not in cols:
        cols.append("split")
    for r in rows:
        if r.get("image_id") in assign:
            r["split"] = assign[r["image_id"]]["split"]
    write_csv(p, cols, rows)
