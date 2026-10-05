"""`python -m ai.data.keyboard_dataset <command>` — dataset tooling entry points (docs/dataset-format.md §CLI)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai.data.keyboard_dataset import arrangement as A
from ai.data.keyboard_dataset import manifest as M
from ai.data.keyboard_dataset import split as S
from ai.data.keyboard_dataset import validate as V
from ai.data.keyboard_dataset.schema import (ARRANGEMENTS_CSV, KEYBOARDS_CSV, MANIFEST_JSON, SPLIT_MANIFEST_JSON,
                                             DEFAULT_LAYOUT_ID, load_dataset, parse_keyboards, read_csv)
from ai.layouts import load_layout


def _schedule(root: Path, path: str | None):
    p = Path(path) if path else root / ARRANGEMENTS_CSV
    return A.load_schedule(p) if p.exists() and p.stat().st_size and read_csv(p) else None


def _json_or_none(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def cmd_init(a):
    from ai.data.keyboard_dataset.templates import write_templates
    for f in write_templates(a.root, overwrite=a.overwrite):
        print("wrote", Path(a.root) / f)
    return 0


def cmd_schedule(a):
    layout = load_layout(a.layout)
    kbs = None
    if a.keyboards:
        kmap, probs = parse_keyboards(read_csv(a.keyboards))
        kbs = [(k, v.role) for k, v in kmap.items()]
    sched = A.generate_schedule(layout, seed=a.seed, n_correct=a.n_correct, n_one_pair=a.n_one_pair, n_multi=a.n_multi,
                                cycle_fraction=a.cycle_fraction, cross_row_fraction=a.cross_row_fraction,
                                n_reserved_pairs=a.reserved_pairs, test_only_fraction=a.test_only_fraction,
                                keyboards=kbs, planned_shots=a.shots)
    A.write_schedule(sched, layout, a.out)
    cov = A.coverage(sched, layout)
    print(json.dumps({k: v for k, v in cov.items() if k != "per_slot"}, indent=1))
    return 0


def cmd_prefill(a):
    from ai.data.keyboard_dataset.templates import append_prefilled_slots
    n = append_prefilled_slots(a.root, load_layout(a.layout), _schedule(Path(a.root), a.schedule))
    print(f"added {n} slot rows (ground_truth_status=pending_review)")
    return 0


def cmd_manifest(a):
    root = Path(a.root)
    ds = load_dataset(root)
    sm = _json_or_none(root / SPLIT_MANIFEST_JSON)
    split_of = {k: v["split"] for k, v in sm["images"].items()} if sm else None
    man = M.build_manifest(root, ds.images, dataset_version=a.version, split_of=split_of,
                           dhash_max=a.dhash_max, phash_max=a.phash_max)
    out = Path(a.out) if a.out else root / MANIFEST_JSON
    M.write_manifest(man, out)
    print(f"{out}: {man['n_images']} images, {len(man['exact_duplicates'])} exact dup groups, "
          f"{len(man['near_duplicates'])} near-dup pairs ({man['cross_split_near']} across splits), missing {len(man['missing_files'])}")
    return 0


def cmd_split(a):
    root = Path(a.root)
    ds = load_dataset(root)
    man = _json_or_none(Path(a.manifest) if a.manifest else root / MANIFEST_JSON)
    sched = _schedule(root, a.schedule)
    fr = dict(zip(("train", "val", "test"), (float(x) for x in a.fractions.split(","))))
    res = S.assign_splits(ds.images, ds.keyboards, seed=a.seed, fractions=fr,
                          test_only_arrangements={k for k, v in (sched or {}).items() if v.test_only},
                          dup_pairs=M.duplicate_pairs(man) if man else None)
    sm = S.build_split_manifest(res, dataset_version=a.version, manifest=man)
    out = Path(a.out) if a.out else root / SPLIT_MANIFEST_JSON
    S.write_split_manifest(sm, out)
    if a.write_csv:
        S.write_splits_to_csv(root, res["assign"])
    print(json.dumps(sm["counts"], indent=1))
    print("split_manifest_hash", sm["split_manifest_hash"])
    if man is None:
        print("warning: no manifest.json — run `manifest` first so duplicates stay in one split", file=sys.stderr)
    return 0


def cmd_validate(a):
    root = Path(a.root)
    ds = load_dataset(root)
    sm = _json_or_none(Path(a.split_manifest) if a.split_manifest else root / SPLIT_MANIFEST_JSON)
    man = _json_or_none(Path(a.manifest) if a.manifest else root / MANIFEST_JSON)
    probs = V.validate(ds, load_layout(a.layout), split_manifest=sm, manifest=man, schedule=_schedule(root, a.schedule))
    print(V.report(probs))
    code = V.exit_code(probs)
    if a.strict and any(p.severity == "warning" for p in probs):
        code = 1
    return code


def cmd_to_yolo(a):
    from ai.data.keyboard_dataset.convert import coco_to_yolo
    root = Path(a.root)
    ds = load_dataset(root)
    sm = _json_or_none(Path(a.split_manifest) if a.split_manifest else root / SPLIT_MANIFEST_JSON)
    split_of = {k: v["split"] for k, v in sm["images"].items()} if sm else None
    jit = [(n, float(s)) for n, s in (x.split(":") for x in a.train_jitter.split(","))] if a.train_jitter else None
    idx = coco_to_yolo(ds, load_layout(a.layout), a.out, split_of=split_of, ppu=a.ppu, train_jitter=jit)
    print(f"{a.out}: {len(idx['items'])} canvases, skipped {len(idx['skipped'])}")
    return 0


def cmd_demo(a):
    """Synthetic end-to-end run: dataset -> manifest -> split -> validate -> YOLO -> pilot (fake OCR)."""
    from ai.data.keyboard_dataset.convert import coco_to_yolo
    from ai.data.keyboard_dataset.synthetic import CodeReader, make_dataset
    from ai.evaluation.pilot import run_pilot, write_report
    layout = load_layout(a.layout)
    root = Path(a.out) / "dataset"
    make_dataset(root, layout, seed=a.seed)
    ds = load_dataset(root)
    man = M.build_manifest(root, ds.images, dataset_version="synthetic_demo")
    M.write_manifest(man, root / MANIFEST_JSON)
    sched = A.load_schedule(root / ARRANGEMENTS_CSV)
    res = S.assign_splits(ds.images, ds.keyboards, seed=a.seed, test_only_arrangements={k for k, v in sched.items() if v.test_only},
                          dup_pairs=M.duplicate_pairs(man))
    sm = S.build_split_manifest(res, dataset_version="synthetic_demo", manifest=man)
    S.write_split_manifest(sm, root / SPLIT_MANIFEST_JSON)
    probs = V.validate(ds, layout, split_manifest=sm, manifest=man, schedule=sched)
    print(V.report(probs))
    split_of = {k: v["split"] for k, v in sm["images"].items()}
    coco_to_yolo(ds, layout, Path(a.out) / "yolo", split_of=split_of, ppu=48)
    rep = run_pilot(ds, layout, CodeReader())
    write_report(rep, Path(a.out) / "pilot")
    print(json.dumps(sm["counts"], indent=1))
    print("pilot overall:", json.dumps(rep["overall"]["fixed_errors"]))
    return V.exit_code(probs)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m ai.data.keyboard_dataset", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def p(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(fn=fn)
        sp.add_argument("--layout", default=DEFAULT_LAYOUT_ID)
        return sp

    sp = p("init", cmd_init, "create empty dataset skeleton + CSV templates")
    sp.add_argument("root")
    sp.add_argument("--overwrite", action="store_true")

    sp = p("schedule", cmd_schedule, "generate the arrangement schedule CSV (P2.A)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--seed", type=int, required=True)
    sp.add_argument("--n-correct", type=int, default=100)
    sp.add_argument("--n-one-pair", type=int, default=200)
    sp.add_argument("--n-multi", type=int, default=100)
    sp.add_argument("--cycle-fraction", type=float, default=0.25)
    sp.add_argument("--cross-row-fraction", type=float, default=0.5)
    sp.add_argument("--reserved-pairs", type=int, default=8)
    sp.add_argument("--test-only-fraction", type=float, default=0.10)
    sp.add_argument("--keyboards", help=f"keyboards CSV ({KEYBOARDS_CSV}) to assign rows to keyboards")
    sp.add_argument("--shots", type=int, default=1)

    sp = p("prefill-slots", cmd_prefill, "add 26 pending slot rows per image from the schedule")
    sp.add_argument("root")
    sp.add_argument("--schedule")

    sp = p("manifest", cmd_manifest, "SHA-256 + perceptual hashes + duplicate report")
    sp.add_argument("root")
    sp.add_argument("--version", required=True, help="dataset_version, e.g. keyboard_qwerty_v1")
    sp.add_argument("--out")
    sp.add_argument("--dhash-max", type=int, default=M.NEAR_DHASH_MAX)
    sp.add_argument("--phash-max", type=int, default=M.NEAR_PHASH_MAX)

    sp = p("split", cmd_split, "leave-keyboard-out + group split, writes split_manifest.json")
    sp.add_argument("root")
    sp.add_argument("--version", required=True)
    sp.add_argument("--seed", type=int, required=True)
    sp.add_argument("--fractions", default="0.70,0.15,0.15")
    sp.add_argument("--manifest")
    sp.add_argument("--schedule")
    sp.add_argument("--out")
    sp.add_argument("--write-csv", action="store_true", help="also fill the split column of metadata/images.csv")

    sp = p("validate", cmd_validate, "check labels and split rules; exit 1 on errors")
    sp.add_argument("root")
    sp.add_argument("--split-manifest")
    sp.add_argument("--manifest")
    sp.add_argument("--schedule")
    sp.add_argument("--strict", action="store_true", help="warnings also fail")

    sp = p("to-yolo", cmd_to_yolo, "COCO -> YOLO on rectified canvases")
    sp.add_argument("root")
    sp.add_argument("--out", required=True)
    sp.add_argument("--ppu", type=int)
    sp.add_argument("--split-manifest")
    sp.add_argument("--train-jitter", help="e.g. gt:0,j1:0.08,j2:0.15 (sigma in u, Train only)")

    sp = p("demo", cmd_demo, "synthetic end-to-end smoke run (no real photos, no OCR model)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--seed", type=int, default=0)
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
