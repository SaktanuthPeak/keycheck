"""Glue between the notebook and the stage functions. The notebook only builds a Context and calls q1..q7."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ai.pipeline.stage import StageError, StageResult, check_q7_guard, code_version, run_stage

REPO = Path(__file__).resolve().parents[2]
AI = REPO / "ai"


@dataclass
class Context:
    cfg: dict
    root: Path                       # <OUTPUT_ROOT>/<PIPELINE_ID>[_smoke]
    dataset_root: Path
    mode: str = "full"
    seed: int = 0
    repo_ref: str = ""
    force: set = field(default_factory=set)
    run: dict = field(default_factory=lambda: {k: True for k in ("q1", "q2", "q3", "q4", "q5", "q6")})
    run_final_test: bool = False
    results: dict = field(default_factory=dict)

    @property
    def smoke(self) -> bool:
        return self.mode == "smoke"

    @property
    def manifest_dir(self) -> Path:
        return REPO / "data" / "manifests" / self.cfg["dataset_version"]

    def d(self, name: str) -> Path:
        return self.root / name


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _res(ctx: Context, key: str) -> StageResult | None:
    return ctx.results.get(key)


def q1(ctx: Context):
    from ai.data.q1_ingest import run_q1
    cfg = {**ctx.cfg["q1"], "layout_id": ctx.cfg["layout_id"], "dataset_version": ctx.cfg["dataset_version"]}
    ms = ctx.cfg["smoke"]["max_sources"] if ctx.smoke else None
    r = run_stage("q1_ingest", lambda out: run_q1(out, dataset_root=ctx.dataset_root, cfg=cfg, max_sources=ms,
                                                  manifest_dir=None if ctx.smoke else ctx.manifest_dir),
                  root=ctx.root, config={"cfg": cfg, "max_sources": ms}, code_version=code_version(AI / "data", AI / "layouts.py", AI / "preprocessing"),
                  force=ctx.force, enabled=ctx.run["q1"])
    ctx.results["q1"] = r
    return r


def q2(ctx: Context):
    from ai.data.rectify_dataset import run_q2
    ppus = tuple(ctx.cfg["q2"]["ppus"])
    r = run_stage("q2_rectified", lambda out: run_q2(out, q1_dir=_res(ctx, "q1").out_dir, dataset_root=ctx.dataset_root, cfg=ctx.cfg, ppus=ppus, seed=ctx.seed),
                  root=ctx.root, config={"q2": ctx.cfg["q2"], "layouts": [ctx.cfg["layout_id"], ctx.cfg["swap_layout_id"]]}, upstream=[_res(ctx, "q1")],
                  code_version=code_version(AI / "data", AI / "preprocessing", AI / "layouts.py"), force=ctx.force, enabled=ctx.run["q2"])
    ctx.results["q2"] = r
    return r


def q3(ctx: Context):
    from ai.evaluation.ocr_eval import run_q3
    r = run_stage("q3_ocr", lambda out: run_q3(out, q2_dir=_res(ctx, "q2").out_dir, cfg=ctx.cfg, ppus=tuple(ctx.cfg["q2"]["ppus"]), smoke=ctx.smoke),
                  root=ctx.root, config={"q3": ctx.cfg["q3"], "smoke": ctx.smoke}, upstream=[_res(ctx, "q2")],
                  code_version=code_version(AI / "recognition", AI / "evaluation" / "ocr_eval.py"), force=ctx.force, enabled=ctx.run["q3"])
    ctx.results["q3"] = r
    return r


def chosen_ppu(ctx: Context) -> int:
    return yaml.safe_load((_res(ctx, "q3").out_dir / "chosen_config.yaml").read_text())["px_per_unit"]


def q4(ctx: Context):
    from ai.training.train_yolo import train_yolo
    ppu = chosen_ppu(ctx)
    data = _res(ctx, "q2").out_dir / f"rectified_ppu{ppu}" / "data.yaml"
    r = run_stage("q4_yolo", lambda out: train_yolo(out, data_yaml=data, cfg=ctx.cfg["q4"], seed=ctx.seed, smoke=ctx.smoke),
                  root=ctx.root, config={"q4": ctx.cfg["q4"], "ppu": ppu, "seed": ctx.seed, "smoke": ctx.smoke}, upstream=[_res(ctx, "q2"), _res(ctx, "q3")],
                  code_version=code_version(AI / "training" / "train_yolo.py"), force=ctx.force, enabled=ctx.run["q4"])
    ctx.results["q4"] = r
    return r


def q5(ctx: Context):
    from ai.training.train_frcnn import train_frcnn
    ppu = chosen_ppu(ctx)
    root = _res(ctx, "q2").out_dir / f"rectified_ppu{ppu}"
    r = run_stage("q5_frcnn", lambda out: train_frcnn(out, data_root=root, cfg=ctx.cfg["q5"], seed=ctx.seed, smoke=ctx.smoke),
                  root=ctx.root, config={"q5": ctx.cfg["q5"], "ppu": ppu, "seed": ctx.seed, "smoke": ctx.smoke}, upstream=[_res(ctx, "q2"), _res(ctx, "q3")],
                  code_version=code_version(AI / "training" / "train_frcnn.py", AI / "detection" / "detectors.py"), force=ctx.force, enabled=ctx.run["q5"])
    ctx.results["q5"] = r
    return r


def _maybe_dir(ctx: Context, key: str, dirname: str):
    r = _res(ctx, key)
    if r is not None:
        return r.out_dir
    d = ctx.d(dirname)
    return d if (d / "_DONE.json").exists() else None


def q6(ctx: Context):
    from ai.evaluation.q6_eval import run_q6
    q4d, q5d = _maybe_dir(ctx, "q4", "q4_yolo"), _maybe_dir(ctx, "q5", "q5_frcnn")
    ups = [_res(ctx, "q2"), _res(ctx, "q3")] + [x for x in (_res(ctx, "q4"), _res(ctx, "q5")) if x]
    ups += [f"q4:{(q4d / '_DONE.json').read_text()}" if q4d else "q4:none", f"q5:{(q5d / '_DONE.json').read_text()}" if q5d else "q5:none"]
    r = run_stage("q6_eval", lambda out: run_q6(out, q1_dir=_res(ctx, "q1").out_dir, q2_dir=_res(ctx, "q2").out_dir, q3_dir=_res(ctx, "q3").out_dir,
                                              q4_dir=q4d, q5_dir=q5d, cfg=ctx.cfg, repo_dir=REPO, smoke=ctx.smoke, manifest_dir=ctx.manifest_dir),
                  root=ctx.root, config={"q6": ctx.cfg["q6"], "smoke": ctx.smoke}, upstream=ups,
                  code_version=code_version(AI / "evaluation", AI / "matching", AI / "bundle.py", AI / "pipeline" / "evidence.py", AI / "detection"),
                  force=ctx.force, enabled=ctx.run["q6"])
    ctx.results["q6"] = r
    return r


def q7_problems(ctx: Context) -> list[str]:
    q6d = ctx.d("q6_eval")
    q6_hashes, committed = {}, {}
    if (q6d / "frozen_hashes.json").exists():
        from ai.pipeline.stage import file_sha256
        fz = json.loads((q6d / "frozen_hashes.json").read_text())
        q6_hashes = {"split_manifest_hash": json.loads((ctx.d("q1_ingest") / "split_manifest.json").read_text())["split_manifest_hash"],
                     "thresholds_sha256": file_sha256(q6d / "thresholds.yaml"), "bundle_sha256": fz["bundle_sha256"]}
    cf = ctx.manifest_dir / "frozen_hashes.json"
    if cf.exists():
        committed = json.loads(cf.read_text())
    else:
        q6_hashes = q6_hashes or {"missing": "q6"}
    p = check_q7_guard(run_final_test=ctx.run_final_test, mode=ctx.mode, repo_dir=REPO, repo_ref=ctx.repo_ref, q6_hashes=q6_hashes,
                       committed_hashes=committed, q7_dir=ctx.d("q7_test"))
    if not (q6d / "_DONE.json").exists():
        p.append("Q6 has not finished")
    # the committed manifest + thresholds must be what git has, not just on disk
    import subprocess
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(cf.relative_to(REPO)), "experiments/configs/qwertz/thresholds.yaml"],
                             cwd=REPO, capture_output=True, text=True)
    if tracked.returncode != 0:
        p.append("frozen_hashes.json / thresholds.yaml are not committed to git")
    return p


def q7(ctx: Context):
    from ai.evaluation.q6_eval import run_q7
    problems = q7_problems(ctx)
    if problems:
        print("Q7 locked:\n - " + "\n - ".join(problems))
        return None
    q4d, q5d = _maybe_dir(ctx, "q4", "q4_yolo"), _maybe_dir(ctx, "q5", "q5_frcnn")
    r = run_stage("q7_test", lambda out: run_q7(out, q1_dir=ctx.d("q1_ingest"), q2_dir=ctx.d("q2_rectified"), q3_dir=ctx.d("q3_ocr"), q4_dir=q4d, q5_dir=q5d,
                                              q6_dir=ctx.d("q6_eval"), cfg=ctx.cfg),
                  root=ctx.root, config={"final": True}, upstream=[(ctx.d("q6_eval") / "frozen_hashes.json").read_text()],
                  code_version=code_version(AI / "evaluation"), force=ctx.force, enabled=True)
    ctx.results["q7"] = r
    return r
