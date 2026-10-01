"""End-to-end evaluation on scenarios: evidence collection (cached), decisions, tuning, report text (plan Q6/Q7)."""
from __future__ import annotations

import itertools
import json
import pickle
import random
from dataclasses import fields
from pathlib import Path

import cv2
import numpy as np

from ai.detection.fixed_layout import fixed_layout_boxes
from ai.evaluation import metrics as M
from ai.layouts import load_layout
from ai.matching.decision import Evidence, Params, decide
from ai.pipeline.evidence import collect_evidence

SCEN = ("S1", "S2", "S3", "S4a", "S4b", "S4c")


def load_scenarios(q2_dir: Path, split: str, max_items: int | None = None) -> dict[str, list[dict]]:
    out = {}
    for s in SCEN:
        items = json.loads((Path(q2_dir) / "eval_scenarios" / split / s / "scenario.json").read_text())
        items.sort(key=lambda i: i["id"])
        if max_items and len(items) > max_items:
            items = random.Random(0).sample(items, max_items)
        out[s] = items
    return out


def canvas_path(q2_dir: Path, split: str, ppu: int, it: dict) -> Path:
    return Path(q2_dir) / "eval_scenarios" / split / f"ppu{ppu}" / it["image_dir"] / f"{it['key']}.jpg"


def unique_canvases(scen: dict[str, list[dict]]) -> list[tuple[str, str]]:
    return sorted({(i["image_dir"], i["key"]) for items in scen.values() for i in items})


def build_evidence(q2_dir: Path, split: str, scen: dict, ppu: int, detect, reader, layout, crop_mode: str, evidence_gating_u: float,
                   det_floor: float, chunk: int = 32, progress=print) -> dict:
    """detect(list_of_canvases) -> list[(boxes_px, scores)]. Returns {(image_dir,key): Evidence}."""
    keys = unique_canvases(scen)
    cache = {}
    for s in range(0, len(keys), chunk):
        part = keys[s:s + chunk]
        canv = [cv2.imread(str(Path(q2_dir) / "eval_scenarios" / split / f"ppu{ppu}" / d / f"{k}.jpg")) for d, k in part]
        keep = [(kk, c) for kk, c in zip(part, canv) if c is not None]
        if not keep:
            continue
        dets = detect([c for _, c in keep])
        evs = collect_evidence([c for _, c in keep], dets, layout, ppu, reader, crop_mode, evidence_gating_u, det_floor)
        for (kk, _), ev in zip(keep, evs):
            cache[kk] = ev
        progress(f"  evidence {min(s + chunk, len(keys))}/{len(keys)}")
    return cache


def baseline_detect(layout, ppu):
    b, sc = fixed_layout_boxes(layout, ppu)
    return lambda canvases: [(b, sc) for _ in canvases]


def run_decisions(scen: dict, cache: dict, layouts: dict, params: Params) -> dict[str, list[dict]]:
    res = {}
    for name, items in scen.items():
        rs = []
        for it in items:
            ev = cache[(it["image_dir"], it["key"])]
            r = decide(ev, layouts[it["layout_id"]], params)
            rs.append(M.attach_assignment_check(r, ev, it))
        res[name] = rs
    return res


def evaluate(scen: dict, cache: dict, layouts: dict, params: Params) -> tuple[dict, dict]:
    results = run_decisions(scen, cache, layouts, params)
    return M.full_report(scen, results, layouts), results


def objective(overall: dict, tcfg: dict) -> float:
    s1, s2, s3, s4a = (overall.get(k, {}) for k in ("S1", "S2", "S3", "S4a"))
    fa = s1.get("false_alarm_image_rate", 0.0)
    frj = s1.get("rejection_rate", 0.0)
    nz = lambda x: 0.0 if x != x else x
    pen = max(0.0, nz(fa) - tcfg["max_false_alarm"]) + max(0.0, nz(frj) - tcfg["max_false_rejection"])
    f1 = np.mean([nz(s2.get("incorrect_f1", 0.0)), nz(s3.get("incorrect_f1", 0.0))])
    val = f1 + tcfg["w_layout"] * nz(s4a.get("layout_mismatch_rate", 0.0)) + 0.1 * nz(s1.get("coverage", 0.0))
    return float(val - 10.0 * pen)


def make_params(base: dict, over: dict | None = None, skip_layout_fit: bool = False) -> Params:
    d = {**base, **(over or {})}
    names = {f.name for f in fields(Params)}
    return Params(**{k: v for k, v in d.items() if k in names}, **({"skip_layout_fit": True} if skip_layout_fit else {}))


def tune(scen: dict, cache: dict, layouts: dict, base: dict, tcfg: dict, *, restrict: list[str] | None = None, skip_layout_fit: bool = False,
         progress=print) -> tuple[dict, float, list]:
    """Full grid when small, else coordinate descent (3 passes). Validation data only."""
    grid = {k: v for k, v in tcfg["grid"].items() if restrict is None or k in restrict}
    names = list(grid)
    total = 1
    for v in grid.values():
        total *= len(v)

    def score(over):
        rep, _ = evaluate(scen, cache, layouts, make_params(base, over, skip_layout_fit))
        return objective(rep["overall"], tcfg)

    history = []
    if total <= tcfg["max_combos"]:
        best, best_s = {}, -1e9
        for combo in itertools.product(*grid.values()):
            over = dict(zip(names, combo))
            s = score(over)
            history.append({**over, "objective": s})
            if s > best_s:
                best, best_s = over, s
    else:
        best = {k: base.get(k, grid[k][0]) for k in names}
        for k in names:
            if best[k] not in grid[k]:
                best[k] = grid[k][0]
        best_s = score(best)
        for _ in range(3):
            changed = False
            for k in names:
                for v in grid[k]:
                    if v == best[k]:
                        continue
                    cand = {**best, k: v}
                    s = score(cand)
                    history.append({**cand, "objective": s})
                    if s > best_s + 1e-9:
                        best, best_s, changed = cand, s, True
            progress(f"  tune pass objective={best_s:.4f}")
            if not changed:
                break
    return best, best_s, history


def fmt(x, pct=False):
    if x is None or (isinstance(x, float) and x != x):
        return "N/A"
    return f"{x:.1%}" if pct else (f"{x:.3f}" if isinstance(x, float) else str(x))


def report_tables(rep: dict) -> str:
    o = rep["overall"]
    L = ["| Scenario | n | rejected | incorrect P | incorrect R | incorrect F1 | label acc | assign acc | coverage | uncertain | strict board | false-alarm img | sugg P | sugg R |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in ("S1", "S2", "S3"):
        if s in o:
            m = o[s]
            L.append(f"| {s} | {m['n_items']} | {fmt(m['rejection_rate'], True)} | {fmt(m['incorrect_precision'])} | {fmt(m['incorrect_recall'])} | {fmt(m['incorrect_f1'])} | "
                     f"{fmt(m['observed_label_acc'])} | {fmt(m['slot_assignment_acc'])} | {fmt(m['coverage'])} | {fmt(m['uncertain_rate'])} | {fmt(m['strict_full_board'])} | "
                     f"{fmt(m['false_alarm_image_rate'])} | {fmt(m['suggestion_precision'])} | {fmt(m['suggestion_recall'])} |")
    if "S4a" in o:
        L += ["", f"S4a (reference points shifted one key): n={o['S4a']['n_items']}, LAYOUT_MISMATCH rate = {fmt(o['S4a']['layout_mismatch_rate'], True)}"]
    if "S4b" in o:
        m = o["S4b"]
        L += [f"S4b (21–25 letters visible): n={m['n_items']}, missing-slot uncertain rate = {fmt(m.get('missing_slot_uncertain_rate'), True)}, false-claim rate = {fmt(m.get('missing_slot_false_claim_rate'), True)}"]
    if "S4c" in o:
        m = o["S4c"]
        L += [f"S4c (strong rotation/flip): n={m['n_items']}, safe rate = {fmt(m['safe_rate'], True)}, false-alarm = {fmt(m['false_alarm_rate'], True)}, rejected = {fmt(m['rejection_rate'], True)}"]
    if "S3" in o and o["S3"].get("per_kind"):
        L += ["", "S3 recall of `incorrect` per swap kind: " + ", ".join(f"{k}: {fmt(v['recall'])} (tp {v['tp']}, fn {v['fn']})" for k, v in o["S3"]["per_kind"].items())]
    for grp in ("by_brand_type", "by_point_set"):
        for g, sc in rep[grp].items():
            parts = []
            for s in ("S1", "S2", "S3"):
                if s in sc:
                    parts.append(f"{s}: F1 {fmt(sc[s]['incorrect_f1'])}, false-alarm {fmt(sc[s]['false_alarm_image_rate'])}, n={sc[s]['n_items']}")
            if parts:
                L.append(f"- `{g}` — " + "; ".join(parts))
    return "\n".join(L)


def save_cache(path: Path, cache: dict):
    with open(path, "wb") as f:
        pickle.dump(cache, f)


def load_cache(path: Path) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)
