"""Run one inspection from the command line and draw the result (web plan W1 §3.4).

    python -m ai.inference.demo photo.jpg --points "x1,y1 x2,y2 x3,y3 x4,y4" [--normalized] [--bundle DIR] [--layout ID] [--out PNG]

Points are the centres of the Q, P, M, Z slots by position (TL, TR, BR, BL) on the EXIF-oriented photo.
Prints status, summary, warnings and per-stage timings as JSON; --json writes the full result.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from ai.inference.images import load_oriented_bgr
from ai.inference.inspector import DEFAULT_LAYOUT_ID, Inspector, InvalidReferencePoints

DEFAULT_BUNDLE = Path(__file__).resolve().parents[2] / "bundles" / "baseline_dev_v0"
COLORS = {"correct": (60, 180, 60), "incorrect": (40, 40, 230), "uncertain": (0, 190, 250)}     # BGR
MARK = {"correct": "", "incorrect": ">", "uncertain": "?"}      # "A>S" = slot A shows S


def parse_points(s: str) -> np.ndarray:
    pts = [tuple(float(v) for v in p.split(",")) for p in s.replace(";", " ").split()]
    if len(pts) != 4 or any(len(p) != 2 for p in pts):
        raise argparse.ArgumentTypeError('need 4 points "x1,y1 x2,y2 x3,y3 x4,y4"')
    return np.array(pts, float)


def draw(image: np.ndarray, result: dict, ref_px: np.ndarray) -> np.ndarray:
    out = image.copy()
    h, w = out.shape[:2]
    th = max(1, round(max(w, h) / 600))
    fs = max(0.4, max(w, h) / 2000)
    for s in result["slots"]:
        poly = np.round(np.array(s["polygon"]) * [w, h]).astype(np.int32)
        col = COLORS[s["status"]]
        cv2.polylines(out, [poly], True, col, th + (1 if s["is_reference"] else 0), cv2.LINE_AA)
        txt = s["expected_label"] if s["status"] == "correct" else f"{s['expected_label']}{MARK[s['status']]}{s['observed_label'] or ''}"
        x, y = poly[:, 0].min() + th, poly[:, 1].min() - th
        cv2.putText(out, txt, (int(x), int(max(12, y))), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), th + 2, cv2.LINE_AA)
        cv2.putText(out, txt, (int(x), int(max(12, y))), cv2.FONT_HERSHEY_SIMPLEX, fs, col, th, cv2.LINE_AA)
    for (x, y), name in zip(ref_px, ("TL", "TR", "BR", "BL")):
        cv2.circle(out, (int(round(x)), int(round(y))), 3 * th, (255, 0, 255), -1, cv2.LINE_AA)
    head = result["status"] if result["summary"] is None else "correct {correct} / incorrect {incorrect} / uncertain {uncertain}".format(**result["summary"])
    if result["error_code"]:
        head += f" ({result['error_code']})"
    (tw, tth), base = cv2.getTextSize(head, cv2.FONT_HERSHEY_SIMPLEX, fs * 1.2, th)
    cv2.rectangle(out, (0, 0), (tw + 20, tth + base + 20), (0, 0, 0), -1)
    cv2.putText(out, head, (10, tth + 10), cv2.FONT_HERSHEY_SIMPLEX, fs * 1.2, (255, 255, 255), th, cv2.LINE_AA)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--points", required=True, type=parse_points, help='"x1,y1 x2,y2 x3,y3 x4,y4" = Q, P, M, Z slot centres')
    ap.add_argument("--normalized", action="store_true", help="points are 0..1 fractions of width/height")
    ap.add_argument("--bundle", default=str(DEFAULT_BUNDLE))
    ap.add_argument("--layout", default=DEFAULT_LAYOUT_ID)
    ap.add_argument("--ocr-device", default="cpu")
    ap.add_argument("--detector-device", default="cpu")
    ap.add_argument("--out", help="write the overlay image here")
    ap.add_argument("--json", dest="json_out", help="write the full result JSON here")
    ap.add_argument("--repeat", type=int, default=1, help="run N times to see warm latency (models load lazily on the first run)")
    a = ap.parse_args(argv)

    image = load_oriented_bgr(a.image)
    h, w = image.shape[:2]
    pts = a.points * [w, h] if a.normalized else a.points
    t0 = time.perf_counter()
    insp = Inspector(a.bundle, layout_id=a.layout, ocr_device=a.ocr_device, detector_device=a.detector_device)
    load_ms = int(round((time.perf_counter() - t0) * 1000))
    runs = []
    try:
        for _ in range(max(1, a.repeat)):
            result, dbg = insp.inspect_with_debug(image, pts, on_stage=lambda s: print(f"[stage] {s}", file=sys.stderr))
            runs.append(result["timings_ms"])
    except InvalidReferencePoints as e:
        print(json.dumps({"error": "INVALID_CORNERS", "message": str(e)}))
        return 2
    report = {"image": str(a.image), "image_wh": [w, h], "bundle": insp.bundle_id, "detector": insp.detector_name, "layout": insp.layout_id,
              "status": result["status"], "error_code": result["error_code"], "summary": result["summary"], "warnings": result["warnings"],
              "suggestions": result["suggestions"], "fit": result["fit"], "n_detections": dbg["n_detections"], "n_ocr": dbg["n_ocr"],
              "quality": {k: round(v, 4) if isinstance(v, float) else v for k, v in dbg["quality"].items()},
              "timings_ms": {"load_models": load_ms, **result["timings_ms"]}, "timings_ms_runs": runs,
              "slots": [f"{s['slot_id']}:{s['expected_label']}->{s['observed_label'] or '-'}:{s['status']}:{s['reason']}" for s in result["slots"]]}
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(result, indent=1, ensure_ascii=False, allow_nan=False))
    if a.out:
        cv2.imwrite(a.out, draw(image, result, pts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
