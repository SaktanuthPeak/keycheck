"""Stages Q6 (Validation eval + tuning + dev bundle) and Q7 (locked Proxy Test) — plan §5."""
from __future__ import annotations

import inspect
import json
import shutil
import subprocess
from pathlib import Path

import yaml

from ai.bundle import build_bundle
from ai.colab.bootstrap import free_memory
from ai.detection.detectors import FrcnnDetector, YoloDetector
from ai.evaluation import pipeline_eval as PE
from ai.layouts import load_layout
from ai.matching.decision import Evidence, Params
from ai.pipeline.stage import code_version, file_sha256, fingerprint, read_done
from ai.classification.keycls import make_reader

ALL_LAYOUTS = ("qwertz_letters_eval_v1", "qwerty_stagger_letters_v1")
PROXY_HEADER = "> **Proxy: Kaggle QWERTZ, ภาพสินค้า/เว็บ — ไม่ใช่ผล Test หลัก** (ข้อจำกัด: plan §7)\n"
AI = Path(__file__).resolve().parents[1]
# Code that shapes the evidence itself; tuning/objective/report code is deliberately left out so re-tuning reuses the cache.
EVIDENCE_CODE = (AI / "pipeline" / "evidence.py", AI / "recognition", AI / "detection")


def _git_head(repo: Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def make_detect(name: str, *, ppu: int, layouts: dict, q4_dir: Path | None, q5_dir: Path | None, cfg: dict):
    """-> (detect_fn, weights_path, detector_config, close_fn) or None when that detector has no result."""
    if name == "baseline":
        return PE.baseline_detect(layouts["qwertz_letters_eval_v1"], ppu), None, None, (lambda: None)
    if name == "yolo":
        w = Path(q4_dir) / "best.pt" if q4_dir else None
        if not w or not w.exists():
            return None
        det = YoloDetector(str(w), imgsz=cfg["q4"]["train"]["imgsz"], max_det=cfg["q4"]["train"]["max_det"])
        return det.predict, w, {"imgsz": cfg["q4"]["train"]["imgsz"]}, (lambda: None)
    if name == "frcnn":
        w = Path(q5_dir) / "checkpoints" / "best.pt" if q5_dir else None
        if not w or not w.exists():
            return None
        det = FrcnnDetector(str(w), cfg["q5"]["model"])
        return det.predict, w, cfg["q5"]["model"], (lambda: None)
    raise ValueError(name)


def evidence_key(name: str, *, weights: Path | None, det_cfg, chosen: dict, q2_dir: Path, scen: dict, ppu: int, q6: dict) -> str:
    """Everything the Validation evidence depends on. A cached pkl is reused only when this matches."""
    q2_done = read_done(Path(q2_dir)) or {}
    return fingerprint({
        "detector": name, "weights_sha256": file_sha256(weights) if weights else None, "det_cfg": det_cfg,
        "recognizer": chosen["recognizer"], "crop_mode": chosen["crop_mode"], "ppu": ppu, "q2": q2_done.get("fingerprint"),
        "canvases": PE.unique_canvases(scen), "gating_u": q6["evidence_gating_u"], "det_floor": q6["evidence_det_floor"],
    }, code_version=code_version(*EVIDENCE_CODE) + fingerprint([inspect.getsource(PE.build_evidence), inspect.getsource(Evidence)]))


def _setup(chosen_yaml: Path, cfg: dict, *, q3b_dir: Path | None = None, recognizer: dict | None = None):
    """Q3 choice of px_per_unit/crop, with the recognizer swapped for the Q3b classifier when q6.recognizer is 'keycls'
    (Q6), or for the frozen spec from thresholds.yaml (Q7)."""
    chosen = yaml.safe_load(Path(chosen_yaml).read_text())
    layouts = {i: load_layout(i) for i in ALL_LAYOUTS}
    if recognizer is None and cfg["q6"].get("recognizer", "q3") == "keycls":
        w = Path(q3b_dir) / "checkpoints" / "best.pt"
        recognizer = {"id": "keycls", "mode": "keycls", "weights": str(w), "weights_sha256": file_sha256(w)}
    if recognizer is not None:
        if recognizer.get("weights_sha256") and file_sha256(recognizer["weights"]) != recognizer["weights_sha256"]:
            raise RuntimeError(f"recognizer weights changed since they were frozen: {recognizer['weights']}")
        chosen = {**chosen, "recognizer": recognizer}
    keycls = chosen["recognizer"].get("mode") == "keycls"
    return chosen, layouts, make_reader(chosen["recognizer"], device=cfg["q3b"]["device"] if keycls else cfg["q3"]["device"])


def run_q6(out_dir: Path, *, q1_dir: Path, q2_dir: Path, q3_dir: Path, q4_dir: Path | None, q5_dir: Path | None, cfg: dict, repo_dir: Path,
           q3b_dir: Path | None = None, smoke: bool = False, manifest_dir: Path | None = None) -> dict:
    q6 = cfg["q6"]
    chosen, layouts, reader = _setup(Path(q3_dir) / "chosen_config.yaml", cfg, q3b_dir=q3b_dir)
    rec_suffix = "__keycls" if chosen["recognizer"].get("mode") == "keycls" else ""   # Paddle caches keep their old names
    ppu = chosen["px_per_unit"]
    scen = PE.load_scenarios(Path(q2_dir), "val", 6 if smoke else q6["max_items_per_scenario"])
    split_hash = json.loads((Path(q1_dir) / "split_manifest.json").read_text())["split_manifest_hash"]
    out_dir.mkdir(parents=True, exist_ok=True)
    thresholds, summaries, md = {}, {}, ["# Q6 — Validation report", "", PROXY_HEADER, f"px_per_unit={ppu}, crop=`{chosen['crop_mode']}`, OCR=`{chosen['recognizer']['id']}`", ""]
    weights, dcfg = {}, {}
    for name in q6["detectors"]:
        made = make_detect(name, ppu=ppu, layouts=layouts, q4_dir=q4_dir, q5_dir=q5_dir, cfg=cfg)
        if made is None:
            md += [f"## {name}", "", "ไม่มีผลการฝึก — ข้าม", ""]
            continue
        detect, w, dc, _ = made
        weights[name], dcfg[name] = w, dc
        cache_p, key_p = out_dir / f"evidence_val_{name}{rec_suffix}.pkl", out_dir / f"evidence_val_{name}{rec_suffix}.key"
        key = evidence_key(name, weights=w, det_cfg=dc, chosen=chosen, q2_dir=q2_dir, scen=scen, ppu=ppu, q6=q6)
        if cache_p.exists() and key_p.exists() and key_p.read_text().strip() == key:
            print(f"[q6] evidence: {name} — reusing cache ({key[:8]})")
            cache = PE.load_cache(cache_p)
        else:
            print(f"[q6] evidence: {name}")
            key_p.unlink(missing_ok=True)
            cache = PE.build_evidence(Path(q2_dir), "val", scen, ppu, detect, reader, layouts["qwertz_letters_eval_v1"], chosen["crop_mode"],
                                      q6["evidence_gating_u"], q6["evidence_det_floor"])
            PE.save_cache(cache_p, cache)
            key_p.write_text(key)  # written last: a crash mid-save leaves no key, so the pkl is rebuilt
        is_base = name == "baseline"
        base = dict(q6["default_params"])
        rep0, _ = PE.evaluate(scen, cache, layouts, PE.make_params(base, None, is_base))
        grid_cfg = {**q6["tuning"]}
        if smoke:
            grid_cfg["grid"] = {k: v[:2] for k, v in grid_cfg["grid"].items()}
        best, best_s, hist = PE.tune(scen, cache, layouts, base, grid_cfg, restrict=["ocr_score_min", "ref_invalid_max", "mismatch_min_wrong"] if is_base else None, skip_layout_fit=is_base)
        params = PE.make_params(base, best, is_base)
        rep1, _ = PE.evaluate(scen, cache, layouts, params)
        thresholds[name] = {**params.to_dict(), "objective": best_s}
        summaries[name] = {"default": rep0["overall"], "tuned": rep1["overall"], "objective_default": PE.objective(rep0["overall"], q6["tuning"]), "objective_tuned": best_s}
        (out_dir / f"val_{name}.json").write_text(json.dumps({"default": rep0, "tuned": rep1, "tuning_history": hist}, default=str))
        md += [f"## {name}", "", "### ค่าเริ่มต้น", "", PE.report_tables(rep0), "", f"### หลังปรับบน Validation (objective {best_s:.4f})", "", PE.report_tables(rep1), "",
               "```yaml", yaml.safe_dump(thresholds[name], sort_keys=False).strip(), "```", ""]
        del cache
        free_memory()
    reader.close()
    learned = [n for n in thresholds if n != "baseline"]
    selected = max(learned, key=lambda n: thresholds[n]["objective"]) if learned else "baseline"
    thresholds_doc = {"selected_detector": selected, "px_per_unit": ppu, "crop_mode": chosen["crop_mode"], "recognizer": chosen["recognizer"],
                      "detectors": thresholds}
    (out_dir / "thresholds.yaml").write_text(yaml.safe_dump(thresholds_doc, sort_keys=False))
    bundle_chosen, extra = chosen, {}
    if chosen["recognizer"].get("mode") == "keycls":    # the bundle carries its own copy of the classifier
        extra = {"recognizer_keycls.pt": Path(chosen["recognizer"]["weights"])}
        bundle_chosen = {**chosen, "recognizer": {**chosen["recognizer"], "weights": "recognizer_keycls.pt"}}
    bundle = build_bundle(out_dir / "bundle" / "keycheck_qwertz_dev_v1", bundle_id="keycheck_qwertz_dev_v1", detector=selected, weights=weights.get(selected),
                          imgsz_or_model_cfg=dcfg.get(selected), chosen=bundle_chosen, thresholds=thresholds[selected], layouts=list(ALL_LAYOUTS),
                          split_manifest_hash=split_hash, commit=_git_head(Path(repo_dir)), extra_files=extra)
    frozen = {"split_manifest_hash": split_hash, "thresholds_sha256": file_sha256(out_dir / "thresholds.yaml"), "bundle_sha256": bundle["bundle_sha256"]}
    (out_dir / "frozen_hashes.json").write_text(json.dumps(frozen, indent=1))
    md += ["## เลือก", "", f"Detector ที่เลือก: **{selected}**", "", "Commit ไฟล์เหล่านี้ก่อนรัน Q7:", "- `experiments/configs/qwertz/thresholds.yaml`", "- `data/manifests/kaggle_qwertz_v1/frozen_hashes.json`", "", "```json", json.dumps(frozen, indent=1), "```", ""]
    (out_dir / "val_report.md").write_text("\n".join(md))
    if manifest_dir and not smoke:
        Path(manifest_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(out_dir / "frozen_hashes.json", Path(manifest_dir) / "frozen_hashes.json")
        shutil.copy(out_dir / "thresholds.yaml", Path(repo_dir) / "experiments/configs/qwertz/thresholds.yaml")
    return {"selected": selected, "frozen": frozen, "summaries": {k: {"objective_default": v["objective_default"], "objective_tuned": v["objective_tuned"]} for k, v in summaries.items()}}


def run_q7(out_dir: Path, *, q1_dir: Path, q2_dir: Path, q3_dir: Path, q4_dir: Path | None, q5_dir: Path | None, q6_dir: Path, cfg: dict) -> dict:
    """Runs every available detector once on Test with its frozen Validation thresholds."""
    thr = yaml.safe_load((Path(q6_dir) / "thresholds.yaml").read_text())
    chosen, layouts, reader = _setup(Path(q3_dir) / "chosen_config.yaml", cfg, recognizer=thr.get("recognizer"))
    ppu = thr["px_per_unit"]
    scen = PE.load_scenarios(Path(q2_dir), "test")
    out_dir.mkdir(parents=True, exist_ok=True)
    md = ["# Q7 — Proxy Test report", "", PROXY_HEADER, f"selected on Validation: **{thr['selected_detector']}** · px_per_unit={ppu} · crop=`{thr['crop_mode']}`",
          f"split_manifest_hash: `{json.loads((Path(q1_dir) / 'split_manifest.json').read_text())['split_manifest_hash']}`", ""]
    summary = {}
    for name, params_d in thr["detectors"].items():
        made = make_detect(name, ppu=ppu, layouts=layouts, q4_dir=q4_dir, q5_dir=q5_dir, cfg=cfg)
        if made is None:
            continue
        detect = made[0]
        cache = PE.build_evidence(Path(q2_dir), "test", scen, ppu, detect, reader, layouts["qwertz_letters_eval_v1"], chosen["crop_mode"],
                                  cfg["q6"]["evidence_gating_u"], cfg["q6"]["evidence_det_floor"])
        params = PE.make_params({k: v for k, v in params_d.items() if k != "objective"}, None, name == "baseline")
        rep, _ = PE.evaluate(scen, cache, layouts, params)
        (out_dir / f"test_{name}.json").write_text(json.dumps(rep, default=str))
        md += [f"## {name}", "", PE.report_tables(rep), ""]
        s2 = rep["overall"].get("S2", {})
        if s2.get("fp_examples") is not None:
            md += ["**ตัวอย่าง FP (S2):** " + json.dumps(s2["fp_examples"][:8], ensure_ascii=False), "", "**ตัวอย่าง FN (S2):** " + json.dumps(s2["fn_examples"][:8], ensure_ascii=False), "",
                   "**Letter confusion (S1+S2, ผู้อ่านเห็นเฉพาะที่ผิด):** " + ", ".join(f"{a}→{b}:{c}" for a, b, c in rep["overall"].get("S1", {}).get("confusion", []) if a != b)[:600], ""]
        summary[name] = {s: {k: v for k, v in m.items() if not isinstance(v, (list, dict))} for s, m in rep["overall"].items()}
        del cache
        free_memory()
    reader.close()
    md += ["## ข้อจำกัด", "", "ผลนี้เป็น Proxy จากภาพ QWERTZ สินค้า/เว็บ ไม่ใช้อ้างความแม่นยำบนภาพมือถือของผู้ใช้ QWERTY (plan §7)", ""]
    (out_dir / "test_report.md").write_text("\n".join(md))
    return summary
