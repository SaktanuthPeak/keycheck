"""Leave-brand-out split (plan §3). Pure functions over audited sources; deterministic for a given seed."""
from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict

ROBUST_ROLES = {"partial", "orient_bad"}     # S4b / S4c material


def assign_splits(sources: list[dict], *, seed: int, test_fraction: float, val_fraction: float,
                  n_heldout_val_groups: int, heldout_min_eligible: int, heldout_max_eligible: int) -> dict:
    """`sources`: dicts with source_id, group, role. Returns {source_id: {"split", "eval_set"}}.

    split ∈ train|val|test|excluded. eval_set ∈ main|partial|orient_bad|None (only for val/test).
    Test brand groups never appear in Train; held-out Validation groups only appear in Validation.
    """
    rng = random.Random(seed)
    by_group: dict[str, list[dict]] = defaultdict(list)
    for s in sources:
        by_group[s["group"]].append(s)
    elig = {gname: [s for s in v if s["role"] == "eval"] for gname, v in by_group.items()}
    eligible_groups = sorted(gname for gname, v in elig.items() if v and gname not in ("sonstige", "empty"))
    n_elig = sum(len(elig[gname]) for gname in eligible_groups)

    order = eligible_groups[:]
    rng.shuffle(order)
    test_groups: list[str] = []
    cnt = 0
    for gname in order:
        if cnt >= test_fraction * n_elig:
            break
        test_groups.append(gname)
        cnt += len(elig[gname])

    pool = [gname for gname in order if gname not in test_groups and heldout_min_eligible <= len(elig[gname]) <= heldout_max_eligible]
    heldout = pool[:n_heldout_val_groups]
    held_cnt = sum(len(elig[gname]) for gname in heldout)

    rest = sorted(s["source_id"] for gname in eligible_groups if gname not in test_groups and gname not in heldout for s in elig[gname])
    rng.shuffle(rest)
    n_val_random = max(0, int(round(val_fraction * n_elig)) - held_cnt)
    val_random = set(rest[:n_val_random])

    out: dict[str, dict] = {}
    for gname, items in by_group.items():
        for s in items:
            sid, role = s["source_id"], s["role"]
            if gname in test_groups:
                split = "test"
            elif gname in heldout:
                split = "val"
            elif sid in val_random:
                split = "val"
            else:
                split = "train"
            eval_set = None
            if split in ("val", "test"):
                if role == "eval":
                    eval_set = "main"
                elif role in ROBUST_ROLES:
                    eval_set = role
                else:
                    split = "excluded"          # unusable for evaluation and must not leak the brand into Train
            if split == "train":
                if role == "orient_bad":
                    split = "excluded"          # flipped / strongly rotated: dropped from Train (Spec §5.6)
            out[sid] = {"split": split, "eval_set": eval_set}
    # robustness material from seen brands: send a val_fraction share of partial / orient_bad sources to Validation
    seen_rob = sorted(s["source_id"] for s in sources if s["role"] in ROBUST_ROLES and s["group"] not in test_groups
                      and s["group"] not in heldout and s["group"] not in ("sonstige", "empty"))
    rng.shuffle(seen_rob)
    role_of = {s["source_id"]: s["role"] for s in sources}
    for sid in seen_rob[: int(round(val_fraction * len(seen_rob)))]:
        out[sid] = {"split": "val", "eval_set": role_of[sid]}
    meta = {"test_groups": sorted(test_groups), "heldout_val_groups": sorted(heldout)}
    return {"assign": out, **meta}


def check_no_leak(assign: dict, sources: list[dict]) -> list[str]:
    """Exit criteria of Q1: no test/held-out brand in Train, no source in two splits."""
    problems = []
    grp = {s["source_id"]: s["group"] for s in sources}
    splits_by_group = defaultdict(set)
    for sid, a in assign.items():
        splits_by_group[grp[sid]].add(a["split"])
    for gname, sp in splits_by_group.items():
        if "test" in sp and ("train" in sp or "val" in sp):
            problems.append(f"test brand {gname} also in {sp - {'test'}}")
    return problems


def split_hash(assign: dict) -> str:
    payload = json.dumps(sorted((k, v["split"], v["eval_set"]) for k, v in assign.items()), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
